#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -a
source "${BASE_DIR}/.env"
set +a

MODEL="${1:-${DEFAULT_MODEL}}"

echo "Baixando modelo: ${MODEL}"
OLLAMA_HOST="${OLLAMA_HOST}" /home/abel-aguiar/.local/bin/ollama pull "${MODEL}"
