#!/usr/bin/env bash
# MaxiFitness — one-shot install script
# Creates a venv and installs all Python dependencies.
#
# Usage:
#   ./install.sh

set -e
cd "$(dirname "$0")"

echo "→ Creating virtual environment..."
python3 -m venv venv

echo "→ Installing dependencies..."
./venv/bin/pip install -r requirements.txt

# Create .env if it doesn't exist yet
if [ ! -f .env ]; then
    echo "→ Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠  Edit .env and fill in CHOW_API_KEY and SECRET_KEY before running."
fi

echo ""
echo "Done. To start the server: ./run.sh"
