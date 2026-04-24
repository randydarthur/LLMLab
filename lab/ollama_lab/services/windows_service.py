import os
import subprocess
from ollama_lab.services.base import ServiceBackend
psutil = None
try:
    import psutil
except ImportError:
    pass


class WindowsServiceBackend(ServiceBackend):
    """
    Windows backend using a detached process model.

    Models live in the shared Ollama directory:
      %LOCALAPPDATA%\\Ollama\\models
    """

    def _env(self, port, model_dir):
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
        env["OLLAMA_MODELS"] = os.path.join(model_dir, "models")
        return env

    def start(self, service_name):
        from ollama_lab.services.registry import get_service

        svc = get_service(service_name)
        if not svc:
            return

        port = svc.get("port")
        model_dir = svc.get("model_dir")
        if not port or not model_dir:
            return

        subprocess.Popen(
            ["ollama", "serve"],
            env=self._env(port, model_dir),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    def stop(self, service_name):
        from ollama_lab.services.registry import get_service

        svc = get_service(service_name)
        if not svc:
            return

        port = svc.get("port")
        if not port:
            return

        for proc in psutil.process_iter(["pid", "name", "connections"]):
            try:
                conns = proc.info.get("connections") or []
                for c in conns:
                    if c.laddr and c.laddr.port == port:
                        proc.terminate()
                        break
            except Exception:
                continue

    def restart(self, service_name):
        self.stop(service_name)
        self.start(service_name)

    def is_running(self, service_name, port=None):
        from ollama_lab.services.registry import get_service

        svc = get_service(service_name)
        if not svc:
            return False

        port = port or svc.get("port")
        if not port:
            return False

        for c in psutil.net_connections(kind="inet"):
            if c.laddr and c.laddr.port == port:
                return True
        return False

    def write_service_files(self, service_name, port, model_dir):
        # No persistent SCM integration in this minimal backend.
        pass

    def remove_service_files(self, service_name):
        # Nothing to remove.
        pass

