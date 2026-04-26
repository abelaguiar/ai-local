#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -a
source "${BASE_DIR}/.env"
set +a

mkdir -p "${OLLAMA_MODELS}" "${BASE_DIR}/open-webui-data"

systemctl --user daemon-reload
systemctl --user enable --now ollama.service

docker compose -f "${BASE_DIR}/docker-compose.yml" up -d

echo "Stack iniciada."
echo "Ollama API: http://127.0.0.1:11434"
echo "Open WebUI: http://127.0.0.1:${OPEN_WEBUI_PORT}"
echo "Modelo padrao sugerido: ${DEFAULT_MODEL}"
echo "Modelos de codigo instalados: qwen2.5-coder:14b, deepseek-coder-v2:16b, qwen2.5-coder:7b"
