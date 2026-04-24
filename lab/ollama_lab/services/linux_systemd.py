import subprocess
from ollama_lab.services.base import ServiceBackend
from ollama_lab.services.model_dirs import write_systemd_files, remove_systemd_files


class LinuxSystemdBackend(ServiceBackend):
    """
    Linux backend using systemd units and sockets.
    """

    def start(self, service_name):
        subprocess.run(["sudo", "systemctl", "start", f"{service_name}.service"])

    def stop(self, service_name):
        subprocess.run(["sudo", "systemctl", "stop", f"{service_name}.service"])
        subprocess.run(["sudo", "systemctl", "stop", f"{service_name}.socket"])

    def restart(self, service_name):
        subprocess.run(["sudo", "systemctl", "restart", f"{service_name}.service"])

    def is_running(self, service_name, port=None):
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", f"{service_name}.service"]
        )
        return result.returncode == 0

    def write_service_files(self, service_name, port, model_dir):
        write_systemd_files(service_name, port, model_dir)

    def remove_service_files(self, service_name):
        remove_systemd_files(service_name)

