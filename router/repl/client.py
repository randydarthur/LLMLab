import aiohttp
import asyncio
import json


class RouterClient:
    def __init__(self, base_url, logger):
        self.base_url = base_url.rstrip("/")
        self.logger = logger
        self.debug = False
        self.session = aiohttp.ClientSession()

    def set_debug(self, enabled: bool):
        self.debug = enabled

    async def close(self):
        await self.session.close()

    # ------------------------------------------------------------
    # Internal GET helper with JSON parsing + error handling
    # ------------------------------------------------------------
    async def _get(self, path: str):
        url = f"{self.base_url}{path}"
        try:
            async with self.session.get(url) as resp:
                text = await resp.text()

                if self.debug:
                    self.logger.log("DEBUG", "client", f"GET {url} → {text}")

                resp.raise_for_status()
                return await resp.json()

        except Exception as e:
            self.logger.log("ERROR", "client", f"GET {url} failed: {e}")
            return None

    # ------------------------------------------------------------
    # Internal POST helper
    # ------------------------------------------------------------
    async def _post(self, path: str, payload: dict):
        url = f"{self.base_url}{path}"
        try:
            async with self.session.post(url, json=payload) as resp:
                text = await resp.text()

                if self.debug:
                    self.logger.log("DEBUG", "client", f"POST {url} → {text}")

                resp.raise_for_status()
                return await resp.json()

        except Exception as e:
            self.logger.log("ERROR", "client", f"POST {url} failed: {e}")
            return None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    async def list_models(self):
        data = await self._get("/v1/registry/models")
        if not data:
            return []

        # Case 1: router returns {"models": [...]}
        if isinstance(data, dict) and "models" in data:
            return data["models"]

        # Case 2: router returns a raw list
        if isinstance(data, list):
            return data

        return []

    async def get_health(self):
        return await self._get("/v1/health")

    async def get_stats(self):
        return await self._get("/v1/stats")

    async def get_router_logs(self):
        return await self._get("/v1/logs")

    # ------------------------------------------------------------
    # Chat (streaming)
    # ------------------------------------------------------------
    async def chat(self, session_id, model, messages):
        payload = {
            "session_id": session_id,
            "model": model,
            "messages": messages,
            "stream": True,
        }

        url = f"{self.base_url}/v1/chat/completions"
        full_text = []

        try:
            async with self.session.post(url, json=payload) as resp:
                resp.raise_for_status()

                async for line in resp.content:
                    text = line.decode("utf-8").strip()

                    if self.debug:
                        self.logger.log("DEBUG", "client", f"STREAM {text}")

                    if not text.startswith("data: "):
                        continue

                    chunk = text[6:]
                    if chunk == "[DONE]":
                        yield {"type": "done", "full_text": "".join(full_text)}
                        return

                    try:
                        obj = json.loads(chunk)
                        choices = obj.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            full_text.append(token)
                            yield {"type": "token", "text": token}
                    except Exception as e:
                        self.logger.log("ERROR", "client", f"parse chunk failed: {e}")
                        continue

        except Exception as e:
            self.logger.log("ERROR", "client", f"chat() failed: {e}")
            yield {"type": "done", "full_text": f"[error: {e}]"}

