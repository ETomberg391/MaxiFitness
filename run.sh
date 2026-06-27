#!/usr/bin/env bash
# MaxiFitness — launch script
# Binds to 0.0.0.0:5000 so any device on your LAN can access it.
#
# Usage:
#   ./run.sh

set -e
cd "$(dirname "$0")"

# Check venv exists
if [ ! -d venv ]; then
    echo "Error: virtual environment not found. Run ./install.sh first."
    exit 1
fi

# Check .env exists
if [ ! -f .env ]; then
    echo "Error: .env not found. Run ./install.sh or copy .env.example to .env."
    exit 1
fi

# Activate venv
source venv/bin/activate

# Initialize DB (creates tables + seeds if missing)
python -c "from db import init_db, seed_settings_if_empty; init_db(); seed_settings_if_empty()"

echo "Starting MaxiFitness Workout Tracker..."
echo "  → http://$(ip route get 8.8.8.8 2>/dev/null | awk '{print \$7; exit}'):5000"
echo "  → http://127.0.0.1:5000"
echo ""

exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
