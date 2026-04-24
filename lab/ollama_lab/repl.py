# repl.py
#
# Standalone interactive chat REPL for LLMLab.
# This script is launched in a new OS terminal window and provides
# a streaming, chat-style interface to any installed model.

from __future__ import annotations

import sys
import readline  # Optional on Windows; harmless if missing
from ollama_lab.services.llm_backend_factory import get_llm_backend
from ollama_lab.services.registry import get_model


def main():
    if len(sys.argv) < 2:
        print("Usage: python repl.py <repo>")
        sys.exit(1)

    repo = sys.argv[1].strip().lower()
    entry = get_model(repo)

    if not entry:
        print(f"Model '{repo}' not found in registry.")
        sys.exit(1)

    full_tag = entry["full_tag"]
    backend = get_llm_backend()

    print(f"LLMLab Interactive Terminal — {full_tag}")
    print("Chat-style conversation. Commands: /exit, /reset, /history")
    print("-" * 60)

    conversation = []  # Chat-style history

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        # ------------------------------------------------------------
        # NEW: Reset conversation context
        # ------------------------------------------------------------
        if user_input == "/reset":
            conversation = []
            print("Context reset. Starting a new conversation.")
            continue

        # ------------------------------------------------------------
        # NEW: Show scrollback history
        # ------------------------------------------------------------
        if user_input == "/history":
            print("\n--- Conversation History ---")
            if not conversation:
                print("<empty>")
            else:
                for msg in conversation:
                    role = msg["role"].capitalize()
                    print(f"{role}: {msg['content']}")
            print("----------------------------\n")
            continue

        if user_input == "/exit":
            print("Goodbye.")
            break

        # Add user message to conversation
        conversation.append({"role": "user", "content": user_input})

        print("< ", end="", flush=True)
        assistant_reply = ""

        try:
            # Stream the assistant response
            for token in backend.generate_stream(full_tag, conversation):
                assistant_reply += token
                print(token, end="", flush=True)

        except Exception as e:
            print(f"\n[ERROR] {e}")
            continue

        print("")  # Newline after streaming completes

        # Add assistant reply to conversation
        conversation.append({"role": "assistant", "content": assistant_reply})


if __name__ == "__main__":
    main()

