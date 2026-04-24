import subprocess
import os
from ollama_lab.services.base import ServiceBackend

LAUNCHD_DIR = os.path.expanduser("~/Library/LaunchAgents")


class MacLaunchdBackend(ServiceBackend):
    """
    macOS backend using per-user launchd LaunchAgents.

    Models live in the shared Ollama directory:
      ~/.ollama/models
    """

    def _plist_path(self, service_name):
        return os.path.join(LAUNCHD_DIR, f"{service_name}.plist")

    def start(self, service_name):
        subprocess.run(["launchctl", "load", self._plist_path(service_name)])

    def stop(self, service_name):
        subprocess.run(["launchctl", "unload", self._plist_path(service_name)])

    def restart(self, service_name):
        self.stop(service_name)
        self.start(service_name)

    def is_running(self, service_name, port=None):
        result = subprocess.run(
            ["launchctl", "list", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.returncode == 0

    def write_service_files(self, service_name, port, model_dir):
        """
        model_dir is the *root* Ollama directory:
          ~/.ollama
        """
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{service_name}</string>

    <key>ProgramArguments</key>
    <array>
        <string>ollama</string>
        <string>serve</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>OLLAMA_HOST</key>
        <string>127.0.0.1:{port}</string>
        <key>OLLAMA_MODELS</key>
        <string>{model_dir}/models</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
        os.makedirs(LAUNCHD_DIR, exist_ok=True)
        with open(self._plist_path(service_name), "w") as f:
            f.write(plist)

    def remove_service_files(self, service_name):
        try:
            os.remove(self._plist_path(service_name))
        except FileNotFoundError:
            pass

