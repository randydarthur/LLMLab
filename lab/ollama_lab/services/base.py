class ServiceBackend:
    """
    Abstract interface for model service management.
    Each OS-specific backend must implement these methods.
    """

    def start(self, service_name):
        raise NotImplementedError

    def stop(self, service_name):
        raise NotImplementedError

    def restart(self, service_name):
        raise NotImplementedError

    def is_running(self, service_name, port=None):
        raise NotImplementedError

    def write_service_files(self, service_name, port, model_dir):
        raise NotImplementedError

    def remove_service_files(self, service_name):
        raise NotImplementedError

