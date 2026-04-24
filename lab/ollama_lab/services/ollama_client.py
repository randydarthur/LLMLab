from __future__ import annotations

import os
import json
import subprocess
from typing import Iterator, Dict, Any, List, Optional

import requests

from ollama_lab.utils.logging import log


# ------------------------------------------------------------
# Lazy BASE_URL resolution (fixes circular import)
# ------------------------------------------------------------

BASE_URL: Optional[str] = None


def _default_base_url() -> str:
    """
    Resolve the Ollama base URL.

    Priority:
      1. LLMLab registry setting: settings["bind_ip"]
      2. OLLAMA_HOST env var
      3. Default "127.0.0.1:11434"
    """

    from ollama_lab.services.registry import get_settings  # lazy import

    settings = get_settings()
    bind_ip = settings.get("bind_ip")
    if bind_ip:
        return f"http://{bind_ip}:11434"

    host = os.environ.get("OLLAMA_HOST")
    if host:
        host = host.strip()
        if host.startswith("http://") or host.startswith("https://"):
            return host
        return f"http://{host}"

    return "http://127.0.0.1:11434"


def _get_base_url() -> str:
    global BASE_URL
    if BASE_URL is None:
        BASE_URL = _default_base_url().rstrip("/")
    return BASE_URL


# ------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------

class OllamaError(Exception):
    pass


class OllamaUnavailable(OllamaError):
    pass


class ModelNotFound(OllamaError):
    pass


class PullError(OllamaError):
    pass


class GenerationError(OllamaError):
    pass


class EmbeddingError(OllamaError):
    pass


class DeleteError(OllamaError):
    pass


# ------------------------------------------------------------
# Low-level HTTP helpers
# ------------------------------------------------------------

def _request(
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    stream: bool = False,
    timeout: float = 30.0,
) -> requests.Response:

    url = f"{_get_base_url()}{path}"

    try:
        resp = requests.request(
            method,
            url,
            json=json_body,
            stream=stream,
            timeout=timeout,
        )
        return resp
    except requests.exceptions.RequestException as e:
        log(f"[ollama_client] HTTP error contacting {url}: {e}", "ERROR")
        raise OllamaUnavailable(f"Could not reach Ollama at {url}") from e


def _check_ok(resp: requests.Response, context: str) -> None:
    if resp.status_code == 404:
        raise ModelNotFound(f"{context}: model not found (404)")
    if not resp.ok:
        try:
            data = resp.json()
            msg = data.get("error") or data
        except Exception:
            msg = resp.text
        raise OllamaError(f"{context}: HTTP {resp.status_code}: {msg}")


# ------------------------------------------------------------
# Availability
# ------------------------------------------------------------

def is_available() -> bool:
    try:
        resp = _request("GET", "/api/tags", timeout=3.0)
        return resp.ok
    except OllamaUnavailable:
        return False


def ensure_available() -> None:
    if not is_available():
        raise OllamaUnavailable(
            f"Ollama server not reachable at {_get_base_url()}. "
            "Ensure it is installed and running."
        )


# ------------------------------------------------------------
# Model management
# ------------------------------------------------------------

def list_models() -> List[Dict[str, Any]]:
    ensure_available()
    resp = _request("GET", "/api/tags")
    _check_ok(resp, "list_models")

    try:
        data = resp.json()
    except Exception as e:
        raise OllamaError(f"list_models: invalid JSON response: {e}") from e

    models = data.get("models") or []
    if not isinstance(models, list):
        raise OllamaError("list_models: unexpected response structure")
    return models


def model_exists(full_tag: str) -> bool:
    return any(m.get("name") == full_tag for m in list_models())


# ------------------------------------------------------------
# Pull model (subprocess-based, rock-solid)
# ------------------------------------------------------------

def pull_model(full_tag: str) -> None:
    """
    Pull a model using the Ollama CLI instead of the REST API.
    This avoids streaming inconsistencies in the HTTP pull endpoint.
    """

    ensure_available()

    cmd = ["ollama", "pull", full_tag]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception as e:
        raise PullError(f"Failed to start ollama pull: {e}") from e

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue

        log(f"[ollama_client] pull_model({full_tag}): {line}", "INFO")

        if "error" in line.lower():
            proc.wait()
            raise PullError(f"ollama pull error: {line}")

    proc.wait()

    if proc.returncode != 0:
        raise PullError(
            f"ollama pull {full_tag} failed with exit code {proc.returncode}"
        )

    log(f"[ollama_client] pull_model({full_tag}): completed", "INFO")


# ------------------------------------------------------------
# Delete model (tolerant of empty/non-JSON responses)
# ------------------------------------------------------------

def delete_model(full_tag: str) -> None:
    ensure_available()

    payload = {"name": full_tag}
    resp = _request("DELETE", "/api/delete", json_body=payload, timeout=120.0)

    if resp.status_code == 404:
        raise ModelNotFound(f"delete_model: model {full_tag!r} not found")

    if not resp.ok:
        _check_ok(resp, f"delete_model({full_tag})")

    text = (resp.text or "").strip()

    # Ollama often returns empty or plain text; treat both as success
    if not text:
        log(f"[ollama_client] delete_model({full_tag}): success (empty response)", "INFO")
        return

    try:
        data = resp.json()
    except Exception:
        log(
            f"[ollama_client] delete_model({full_tag}): non-JSON response {text!r}, treating as success",
            "WARN",
        )
        return

    if isinstance(data, dict) and "error" in data:
        raise DeleteError(f"delete_model error: {data['error']}")

    log(f"[ollama_client] delete_model({full_tag}): success", "INFO")


# ------------------------------------------------------------
# Text generation
# ------------------------------------------------------------

def generate_stream(
    full_tag: str,
    prompt: str,
    *,
    options: Optional[Dict[str, Any]] = None,
    system: Optional[str] = None,
    context: Optional[List[int]] = None,
) -> Iterator[str]:

    ensure_available()

    payload: Dict[str, Any] = {
        "model": full_tag,
        "prompt": prompt,
        "stream": True,
    }
    if options:
        payload["options"] = options
    if system is not None:
        payload["system"] = system
    if context is not None:
        payload["context"] = context

    resp = _request("POST", "/api/generate", json_body=payload, stream=True, timeout=600.0)

    if resp.status_code == 404:
        raise ModelNotFound(f"generate_stream: model {full_tag!r} not found")

    if not resp.ok:
        _check_ok(resp, f"generate_stream({full_tag})")

    try:
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                log(f"[ollama_client] generate_stream: non-JSON line: {line}", "WARN")
                continue

            if "error" in data:
                raise GenerationError(f"generate_stream error: {data['error']}")

            token = data.get("response")
            if token:
                yield token

            if data.get("done"):
                break

    except requests.exceptions.RequestException as e:
        raise GenerationError(f"generate_stream({full_tag}) failed: {e}") from e


def generate(
    full_tag: str,
    prompt: str,
    *,
    options: Optional[Dict[str, Any]] = None,
    system: Optional[str] = None,
    context: Optional[List[int]] = None,
) -> str:

    chunks: List[str] = []
    for token in generate_stream(
        full_tag,
        prompt,
        options=options,
        system=system,
        context=context,
    ):
        chunks.append(token)
    return "".join(chunks)


# ------------------------------------------------------------
# Embeddings
# ------------------------------------------------------------

def embed(full_tag: str, text: str) -> List[float]:
    ensure_available()

    payload = {
        "model": full_tag,
        "prompt": text,
    }

    resp = _request("POST", "/api/embeddings", json_body=payload, timeout=120.0)

    if resp.status_code == 404:
        raise ModelNotFound(f"embed: model {full_tag!r} not found")

    if not resp.ok:
        _check_ok(resp, f"embed({full_tag})")

    try:
        data = resp.json()
    except Exception as e:
        raise EmbeddingError(f"embed: invalid JSON response: {e}") from e

    vec = data.get("embedding")
    if not isinstance(vec, list):
        raise EmbeddingError("embed: unexpected response structure (no 'embedding' list)")
    return vec

