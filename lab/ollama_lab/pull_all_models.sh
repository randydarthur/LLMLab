#!/bin/bash
set -e

echo "=== Starting temporary Ollama server ==="
sudo -u ollama /usr/local/bin/ollama serve &
TEMP_PID=$!

sleep 3
echo "Temporary server PID: $TEMP_PID"

# -----------------------------
# MODELS TO PULL
# -----------------------------
declare -A MODELS
MODELS=(
  ["qwen2.5"]="qwen2.5"
  ["mistral"]="mistral"
  ["deepseek"]="deepseek-r1"
  ["phi3"]="phi3"
  ["gemma2"]="gemma2"
  ["codegemma"]="codegemma"
  ["starling"]="starling-lm"
)

# -----------------------------
# DIRECTORIES
# -----------------------------
BASE="/usr/share"

declare -A DIRS
DIRS=(
  ["qwen2.5"]="$BASE/ollama-qwen/models"
  ["mistral"]="$BASE/ollama-mistral/models"
  ["deepseek-r1"]="$BASE/ollama-deepseek/models"
  ["phi3"]="$BASE/ollama-phi3/models"
  ["gemma2"]="$BASE/ollama-gemma2/models"
  ["codegemma"]="$BASE/ollama-codegemma/models"
  ["starling-lm"]="$BASE/ollama-starling/models"
)

# -----------------------------
# PULL MODELS
# -----------------------------
echo "=== Pulling models ==="

for key in "${!MODELS[@]}"; do
    MODEL="${MODELS[$key]}"
    TARGET="${DIRS[$MODEL]}"

    echo "--- Pulling $MODEL ---"
    sudo -u ollama ollama pull "$MODEL"

    echo "--- Ensuring directory exists: $TARGET ---"
    sudo mkdir -p "$TARGET"

    echo "--- Moving model files into $TARGET ---"
    sudo mv /home/ollama/.ollama/models/* "$TARGET"/ 2>/dev/null || true

    echo "--- Fixing permissions ---"
    sudo chown -R ollama:ollama "$TARGET"
done

# -----------------------------
# STOP TEMPORARY SERVER
# -----------------------------
echo "=== Stopping temporary Ollama server ==="
sudo kill "$TEMP_PID" || true
sleep 2

# -----------------------------
# RESTART SOCKETS
# -----------------------------
echo "=== Restarting all model sockets ==="

SOCKETS=(
  "ollama-qwen.socket"
  "ollama-mistral.socket"
  "ollama-deepseek.socket"
  "ollama-phi3.socket"
  "ollama-gemma2.socket"
  "ollama-codegemma.socket"
  "ollama-starling.socket"
)

for S in "${SOCKETS[@]}"; do
    echo "--- Resetting $S ---"
    sudo systemctl reset-failed "${S%.socket}"
    sudo systemctl stop "$S" || true
    sudo systemctl start "$S"
done

echo "=== All models pulled and sockets restarted ==="
echo "=== Testing readiness ==="

for key in "${!MODELS[@]}"; do
    MODEL="${MODELS[$key]}"
    PORT_FILE="/etc/systemd/system/ollama-$key.socket"

    PORT=$(grep ListenStream "$PORT_FILE" | awk -F= '{print $2}')

    echo "--- Testing $MODEL on port $PORT ---"
    curl -H "Authorization: Bearer ${MODEL}-secret-token" \
         --max-time 2 \
         "http://127.0.0.1:$PORT/api/tags" || echo "(not ready yet)"
done

echo "=== Done ==="

