#!/usr/bin/env bash
# setup.sh — First-time project setup helper
# Usage:  bash infrastructure/scripts/setup.sh

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> Stock Agent System — setup"

# ── .env ──────────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[+] Created .env from .env.example — fill in your API keys."
else
    echo "[=] .env already exists, skipping."
fi

# ── Conda environment ─────────────────────────────────────────────────────────
if conda env list | grep -q "^stock-agent "; then
    echo "[=] Conda env 'stock-agent' already exists."
    echo "    To update: conda env update -f environment.yml --prune"
else
    echo "[+] Creating conda environment..."
    conda env create -f environment.yml
fi

# ── Node / frontend ───────────────────────────────────────────────────────────
if [ -d apps/frontend/node_modules ]; then
    echo "[=] node_modules already present."
else
    echo "[+] Installing frontend dependencies..."
    (cd apps/frontend && npm install)
fi

# ── Docker services ───────────────────────────────────────────────────────────
if command -v docker compose &>/dev/null; then
    echo "[+] Starting postgres and redis containers..."
    docker compose up -d postgres redis
    echo "[=] Waiting for postgres to be ready..."
    sleep 3
else
    echo "[!] docker compose not found — start postgres and redis manually."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit .env and add your OPENAI_API_KEY"
echo "  2. conda activate stock-agent"
echo "  3. uvicorn apps.api.app.main:app --reload"
echo "  4. cd apps/frontend && npm run dev"
