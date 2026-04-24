# services/model_dirs.py

import os
import subprocess
import platform


def create_model_dirs(service_name: str) -> str:
    """
    Ensure the model directory structure exists for this service.

    LLMLab no longer manages per‑model directories. Instead, this function
    ensures that the backend's expected model storage paths exist.

    Behavior:
      • Linux:   Creates /usr/share/<service_name>/models/{manifests,blobs}
      • macOS:   Uses ~/Library/Application Support/Ollama/models/{manifests,blobs}
      • Windows: Uses %LOCALAPPDATA%/Ollama/models/{manifests,blobs}

    Returns the base directory for the service.
    """

    system = platform.system()

    if system == "Linux":
        base = f"/usr/share/{service_name}"
        models_dir = f"{base}/models"
        manifests = f"{models_dir}/manifests/registry.ollama.ai/library"
        blobs = f"{models_dir}/blobs"

        # Create directories (caller must have permissions)
        subprocess.run(["mkdir", "-p", manifests], check=False)
        subprocess.run(["mkdir", "-p", blobs], check=False)

        # Optional: set ownership if running under sudo
        subprocess.run(["chown", "-R", "ollama:ollama", base], check=False)

        return base

    elif system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support/Ollama")
        models_dir = os.path.join(base, "models")
        manifests = os.path.join(models_dir, "manifests")
        blobs = os.path.join(models_dir, "blobs")

        os.makedirs(manifests, exist_ok=True)
        os.makedirs(blobs, exist_ok=True)

        return base

    elif system == "Windows":
        base = os.path.join(
            os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
            "Ollama",
        )
        models_dir = os.path.join(base, "models")
        manifests = os.path.join(models_dir, "manifests")
        blobs = os.path.join(models_dir, "blobs")

        os.makedirs(manifests, exist_ok=True)
        os.makedirs(blobs, exist_ok=True)

        return base

    else:
        raise RuntimeError(f"Unsupported OS for model dirs: {system}")


def write_systemd_files(service_name: str, port: int, model_dir: str) -> None:
    """
    Install systemd service + socket units for a model service on Linux.

    Caller must have appropriate permissions (typically run under sudo).
    """

    try:
        ollama_path = subprocess.check_output(["which", "ollama"]).decode().strip()
    except Exception:
        ollama_path = "/usr/local/bin/ollama"

    svc_path = f"/etc/systemd/system/{service_name}.service"
    sock_path = f"/etc/systemd/system/{service_name}.socket"

    svc_content = f"""
[Unit]
Description=Ollama Model Service: {service_name}
After=network.target

[Service]
User=ollama
Group=ollama
ExecStart={ollama_path} serve
Environment="OLLAMA_HOST=127.0.0.1:{port}"
Environment="OLLAMA_MODELS={model_dir}/models"
Restart=always

[Install]
WantedBy=multi-user.target
"""

    sock_content = f"""
[Unit]
Description=Ollama Model Socket: {service_name}

[Socket]
ListenStream=127.0.0.1:{port}

[Install]
WantedBy=sockets.target
"""

    subprocess.run(["tee", svc_path], input=svc_content.encode(), stdout=subprocess.DEVNULL)
    subprocess.run(["tee", sock_path], input=sock_content.encode(), stdout=subprocess.DEVNULL)

    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", f"{service_name}.socket"])
    subprocess.run(["systemctl", "start", f"{service_name}.socket"])


def remove_systemd_files(service_name: str) -> None:
    """
    Remove systemd service + socket units for a model service on Linux.
    """

    svc = f"{service_name}.service"
    sock = f"{service_name}.socket"

    subprocess.run(["systemctl", "stop", svc], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "disable", svc], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "disable", sock], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run(["rm", "-f", f"/etc/systemd/system/{svc}"])
    subprocess.run(["rm", "-f", f"/etc/systemd/system/{sock}"])

    subprocess.run(["systemctl", "daemon-reload"])

