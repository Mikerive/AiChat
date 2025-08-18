#!/usr/bin/env bash
# Activate conda env and run TTS finetune script (Unix)
set -euo pipefail

ENV_NAME=tts_finetune_app

if command -v conda >/dev/null 2>&1; then
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${ENV_NAME}"
else
  echo "conda not found on PATH. Activate the ${ENV_NAME} env manually."
fi

# Example command to start training/orchestrator
python backend/tts_finetune_app/train_voice.py "$@"