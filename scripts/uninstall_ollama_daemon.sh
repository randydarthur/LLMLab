#!/bin/bash

PLIST="$HOME/Library/LaunchAgents/io.llmlab.ollama.plist"

echo "Stopping Ollama daemon…"
launchctl unload "$PLIST" 2>/dev/null

echo "Removing plist…"
rm -f "$PLIST"

echo "Removing log files…"
rm -f "$HOME/Library/Logs/ollama-daemon.log"

echo "Done. The Ollama daemon has been removed."

