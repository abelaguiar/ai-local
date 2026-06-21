#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -a
source "${BASE_DIR}/.env"
set +a

MODEL="${1:-${DEFAULT_MODEL}}"

echo "Baixando modelo: ${MODEL}"
if OLLAMA_BIN="$(command -v ollama)"; then
  OLLAMA_HOST="${OLLAMA_HOST}" "${OLLAMA_BIN}" pull "${MODEL}"
else
  docker exec ai-local-ollama ollama pull "${MODEL}"
fi
