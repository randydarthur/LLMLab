class ReplSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.model: str | None = None
        self.backend: str | None = None
        self.history: list[dict] = []

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.history.append({"role": "assistant", "content": content})

    def reset_history(self):
        self.history = []

