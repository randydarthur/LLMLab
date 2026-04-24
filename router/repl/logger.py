from datetime import datetime


class ReplLogger:
    def __init__(self, path):
        self.path = path

    def write(self, text: str):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    def log(self, level: str, source: str, message: str):
        ts = datetime.now().strftime("%Y-%m-%d:%H:%M:%S.%f")[:-3]
        line = f"{ts} [{level}] {source}: {message}"
        self.write(line)

    def log_request_response(self, request_payload, status_code: int):
        ts = datetime.now().strftime("%Y-%m-%d:%H:%M:%S.%f")[:-3]
        line = {
            "timestamp": ts,
            "status": status_code,
            "request": request_payload,
        }
        self.write(str(line))

