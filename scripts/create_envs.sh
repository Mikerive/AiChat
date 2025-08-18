#!/usr/bin/env bash
# Helper: create/update workspace + app conda envs using mamba (preferred) or conda.
# Usage: ./scripts/create_envs.sh
set -euo pipefail

if command -v mamba >/dev/null 2>&1; then
  PM="mamba"
elif command -v conda >/dev/null 2>&1; then
  PM="conda"
else
  echo "Error: neither mamba nor conda found on PATH. Install one first."
  exit 1
fi

echo "Using package manager: $PM"

echo "Creating/updating workspace environment from [`environment.yml:1`]..."
# Try create, fall back to update
$PM env create -f environment.yml || $PM env update -f environment.yml

if [ -f "envs/chat_app/environment.yml" ]; then
  echo "Creating/updating chat_app environment from [`envs/chat_app/environment.yml:1`]..."
  $PM env create -f envs/chat_app/environment.yml || $PM env update -f envs/chat_app/environment.yml
else
  echo "Warning: envs/chat_app/environment.yml not found. Skipping chat_app env."
fi

echo ""
echo "Done. To activate the workspace env, run:"
echo "  conda activate vtuber_workspace"
echo "To activate the chat app env, run:"
echo "  conda activate chat_app"