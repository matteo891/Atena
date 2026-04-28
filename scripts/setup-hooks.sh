#!/bin/bash
# Setup git hooks per questo repository.
# Eseguire una volta dopo ogni clone: bash scripts/setup-hooks.sh
# ADR-0006: Git Hooks Enforcement

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/hooks"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

if [ -z "$REPO_ROOT" ]; then
    echo "ERROR: Non sei in un repository git."
    exit 1
fi

echo "Configurando git hooks per: $REPO_ROOT"
echo ""

# Configura il path degli hook (relativo alla root del repo)
git config core.hooksPath scripts/hooks

# Imposta i permessi di esecuzione (Linux/Mac/Git Bash)
chmod +x "$HOOKS_DIR/pre-commit" 2>/dev/null || true
chmod +x "$HOOKS_DIR/commit-msg" 2>/dev/null || true

# Imposta l'executable bit in git index (necessario su Windows)
cd "$REPO_ROOT"
git update-index --chmod=+x scripts/hooks/pre-commit 2>/dev/null || true
git update-index --chmod=+x scripts/hooks/commit-msg 2>/dev/null || true

echo "✓ core.hooksPath = $(git config core.hooksPath)"
echo "✓ scripts/hooks/pre-commit  [executable]"
echo "✓ scripts/hooks/commit-msg  [executable]"
echo ""
echo "Hook attivi:"
echo "  pre-commit  → verifica change document (ADR-0002, ADR-0004)"
echo "              → verifica struttura ADR (ADR-0001)"
echo "  commit-msg  → verifica CHG-ID nel message (ADR-0005)"
echo ""
echo "Per disattivare: git config --unset core.hooksPath"
