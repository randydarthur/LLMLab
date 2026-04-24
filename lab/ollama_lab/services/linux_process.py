import subprocess
import os
import json
from ollama_lab.services.base import ServiceBackend

PROC_DB = os.path.expanduser("~/.ollama_lab/process_services.json")


class LinuxProcessBackend(ServiceBackend):
    """
    Linux backend for environments without systemd (e.g., some LXC containers).
    Uses a simple process supervisor stored in a JSON file.
    """

    def __init__(self):
        os.makedirs(os.path.dirname(PROC_DB), exist_ok=True)
        if not os.path.exists(PROC_DB):
            with open(PROC_DB, "w") as f:
                json.dump({}, f)

    def _load_db(self):
        with open(PROC_DB) as f:
            return json.load(f)

    def _save_db(self, db):
        with open(PROC_DB, "w") as f:
            json.dump(db, f)

    def start(self, service_name):
        db = self._load_db()
        cfg = db.get(service_name)
        if not cfg:
            return

        port = cfg["port"]
        model_dir = cfg["model_dir"]

        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
        env["OLLAMA_MODELS"] = f"{model_dir}/models"

        proc = subprocess.Popen(["ollama", "serve"], env=env)
        cfg["pid"] = proc.pid
        db[service_name] = cfg
        self._save_db(db)

    def stop(self, service_name):
        db = self._load_db()
        cfg = db.get(service_name)
        if not cfg:
            return

        pid = cfg.get("pid")
        if pid:
            try:
                os.kill(pid, 9)
            except Exception:
                pass
        cfg["pid"] = None
        db[service_name] = cfg
        self._save_db(db)

    def restart(self, service_name):
        self.stop(service_name)
        self.start(service_name)

    def is_running(self, service_name, port=None):
        db = self._load_db()
        cfg = db.get(service_name)
        if not cfg or not cfg.get("pid"):
            return False
        pid = cfg["pid"]
        return os.path.exists(f"/proc/{pid}")

    def write_service_files(self, service_name, port, model_dir):
        db = self._load_db()
        db[service_name] = {"port": port, "model_dir": model_dir, "pid": None}
        self._save_db(db)

    def remove_service_files(self, service_name):
        db = self._load_db()
        db.pop(service_name, None)
        self._save_db(db)

