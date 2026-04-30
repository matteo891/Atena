#!/bin/bash
# ADR-0013: Setup ambiente di sviluppo.
# Idempotente — eseguire dopo ogni clone, prima del primo commit di codice.

set -e

# 1) Verifica/installa uv (Astral).
if ! command -v uv >/dev/null 2>&1; then
    if ! [ -x "$HOME/.local/bin/uv" ]; then
        echo "→ Installazione uv (Astral)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "→ uv $(uv --version | awk '{print $2}')"

# 2) Verifica/installa Python 3.11.
uv python install 3.11 --quiet

# 3) Sync ambiente (genera/aggiorna .venv + uv.lock).
echo "→ uv sync --all-groups"
uv sync --all-groups

# 4) Attiva i hook governance (ADR-0006).
bash scripts/setup-hooks.sh

echo ""
echo "Setup completato. Per attivare l'ambiente:"
echo "  source .venv/bin/activate"
echo ""
echo "Comandi rapidi (con uv run):"
echo "  uv run pytest tests/unit tests/governance -q   # smoke tests"
echo "  uv run ruff check src/ tests/                  # lint"
echo "  uv run mypy src/                               # type check"
