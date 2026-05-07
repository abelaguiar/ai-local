#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -a
source "${BASE_DIR}/.env"
set +a

mkdir -p "${OLLAMA_MODELS}" "${BASE_DIR}/open-webui-data" "/home/abel-aguiar/projects/ai-generated"

if systemctl is-active --quiet ollama.service; then
  echo "Ollama ja esta rodando como servico do sistema."
elif systemctl --user list-unit-files ollama.service --no-legend >/dev/null 2>&1; then
  systemctl --user daemon-reload
  systemctl --user enable --now ollama.service
else
  echo "Ollama nao esta rodando. Inicie o Ollama antes de subir o Open WebUI." >&2
  exit 1
fi

docker compose -f "${BASE_DIR}/docker-compose.yml" up -d

echo "Stack iniciada."
echo "Ollama API: http://127.0.0.1:11434"
echo "Open WebUI: http://127.0.0.1:${OPEN_WEBUI_PORT}"
echo "Modelo padrao sugerido: ${DEFAULT_MODEL}"
echo "Modelos recomendados: qwen2.5-coder:7b, deepseek-coder-v2:16b, codellama:latest"
