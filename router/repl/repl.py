#!/usr/bin/env python3
import asyncio
import uuid
import time
from pathlib import Path

from .ui import ReplUI
from .client import RouterClient
from .session import ReplSession
from .logger import ReplLogger


ROUTER_BASE_URL = "http://localhost:8000"


async def main():
    session_id = str(uuid.uuid4())
    ts = time.strftime("%Y%m%d-%H%M%S")
    log_dir = Path.home() / ".llmlab" / "repl"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{session_id}.{ts}.repl.log"

    logger = ReplLogger(log_path)
    client = RouterClient(ROUTER_BASE_URL, logger)
    session = ReplSession(session_id=session_id)

    loop = asyncio.get_running_loop()
    ui = ReplUI(loop)
    ui.set_status(None, None, session.session_id)

    def update_status(latency=None, tps=None):
        ui.set_status(
            session.model,
            session.backend,
            session.session_id,
            latency,
            tps,
        )

    # ------------------------------------------------------------
    # COMMAND HANDLER
    # ------------------------------------------------------------
    async def handle_command(cmd: str):
        if cmd.startswith("/model"):
            parts = cmd.split(" ", 1)

            # /model <name>
            if len(parts) == 2 and parts[1].strip():
                model_name = parts[1].strip()
                models = await client.list_models()
                descriptor = next((m for m in models if m["name"] == model_name), None)
                if not descriptor:
                    ui.add_chat_line(f"[system] unknown model: {model_name}")
                    return

                session.model = descriptor["name"]
                session.backend = descriptor.get("backend")
                update_status()
                ui.add_chat_line(f"[system] model set to {session.model}")
                return

            # /model → picker
            models = await client.list_models()
            ui.set_models([m["name"] for m in models])

            chosen = await ui.request_model_picker()
            if not chosen:
                ui.add_chat_line("[system] model selection cancelled")
                return

            descriptor = next((m for m in models if m["name"] == chosen), None)
            if not descriptor:
                ui.add_chat_line(f"[system] unknown model: {chosen}")
                return

            session.model = descriptor["name"]
            session.backend = descriptor.get("backend")
            update_status()
            ui.add_chat_line(f"[system] model set to {session.model}")
            return

        elif cmd == "/models":
            models = await client.list_models()
            if not models:
                ui.add_chat_line("[system] no models discovered")
                return

            ui.add_chat_line("[system] available models:")
            for m in models:
                ui.add_chat_line(f"  - {m['name']}")

            ui.set_models([m["name"] for m in models])
            ui.add_chat_line("[system] press F2 or /model to open picker")
            return

        elif cmd == "/history":
            for msg in session.history:
                ui.add_chat_line(f"{msg['role'].capitalize()}: {msg['content']}")
            return

        elif cmd == "/reset":
            session.reset_history()
            ui.add_chat_line("[system] history reset")
            return

        elif cmd == "/health":
            health = await client.get_health()
            ui.add_chat_line(f"[health] {health}")
            return

        elif cmd == "/stats":
            stats = await client.get_stats()
            ui.add_chat_line(f"[stats] {stats}")
            return

        elif cmd == "/logs":
            logs = await client.get_router_logs()
            ui.add_chat_line(f"[router logs] count={logs.get('count') if logs else 'none'}")
            return

        elif cmd == "/session":
            ui.add_chat_line(f"[system] session_id={session.session_id}")
            return

        elif cmd == "/debug":
            client.set_debug(not client.debug)
            ui.add_chat_line(f"[system] debug mode = {client.debug}")
            return

        elif cmd == "/help":
            ui.add_chat_line("[system] commands:")
            ui.add_chat_line("  /models          list available models")
            ui.add_chat_line("  /model <name>    set active model")
            ui.add_chat_line("  /model           open model picker (F2)")
            ui.add_chat_line("  /history         show session history")
            ui.add_chat_line("  /reset           clear history")
            ui.add_chat_line("  /health          router health")
            ui.add_chat_line("  /stats           router stats")
            ui.add_chat_line("  /logs            router logs")
            ui.add_chat_line("  /session         show session id")
            ui.add_chat_line("  /debug           toggle debug mode")
            ui.add_chat_line("  /help            show this help")
            ui.add_chat_line("  /exit            exit the REPL")
            return

        elif cmd == "/exit":
            ui.request_exit()
            return

        else:
            ui.add_chat_line(f"[system] unknown command: {cmd}")

    # ------------------------------------------------------------
    # MESSAGE HANDLER
    # ------------------------------------------------------------
    async def handle_message(text: str):
        if not session.model:
            ui.add_chat_line("[system] no model set. Use /models or /model.")
            return

        session.add_user_message(text)
        ui.add_chat_line(f"User: {text}")

        start_time = time.perf_counter()
        first_token_time = None
        token_count = 0

        async for chunk in client.chat(
            session_id=session.session_id,
            model=session.model,
            messages=session.history,
        ):
            if chunk["type"] == "token":
                token_count += 1
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                ui.append_assistant_token(chunk["text"])

            elif chunk["type"] == "done":
                end_time = time.perf_counter()

                if first_token_time:
                    latency_ms = int((first_token_time - start_time) * 1000)
                    tps = token_count / (end_time - first_token_time)
                else:
                    latency_ms = None
                    tps = None

                ui.add_json_entry(
                    f"[metrics] latency={latency_ms}ms, tps={tps:.3f}" if tps else
                    "[metrics] latency=none, tps=none"
                )

                update_status(latency_ms, tps)

                reply = chunk["full_text"]
                if reply:
                    session.add_assistant_message(reply)
                ui.finish_assistant_line()

    try:
        await ui.run(handle_command, handle_message)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

