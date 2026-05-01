"""Governance test (ADR-0019 + ADR-0021) — R-01 NO SILENT DROPS dinamico.

Verifica che ogni file Python in `src/talos/` che contiene un pattern
"drop/skip/continue" abbia almeno una chiamata strutturata che usi
una costante del catalogo `CANONICAL_EVENTS`.

In fase di bootstrap (CHG-2026-04-30-006) `src/talos/` è quasi vuoto, quindi
il loop trova zero violazioni. Il test diventa significativo non appena
arrivano i moduli `vgp/`, `tetris/`, `extract/`, `io_/`, `persistence/`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from talos.observability.events import CANONICAL_EVENTS

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _PROJECT_ROOT / "src" / "talos"

# Heuristica: pattern di "scarto" che richiedono evento di log canonico.
# Volutamente permissiva: meglio falsi positivi rilevati e annotati con un
# commento esplicito (regola formale ruff può arrivare in futuro) che
# scarti silenziosi non rilevati.
# Fix CHG-2026-04-30-046: `re.MULTILINE` su `^\s*continue\b` per matchare
# l'inizio di ogni riga (prima il regex matchava solo l'inizio del file —
# bug silente che aveva esentato i moduli vgp/tetris a torto).
_DROP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.drop\("),
    re.compile(r"\.skip\("),
    re.compile(r"^\s*continue\b", re.MULTILINE),
)

# I file in cui un eventuale "continue" è benigno (es. governance/test scaffolding).
# `document_parser.py`: i `continue` skippano pagine PDF/tabelle DOCX vuote
# durante il loop interno di estrazione; il fallimento totale solleva ValueError
# esplicito (R-01 al confine del modulo). CHG-2026-05-02-007.
_EXEMPT_FILES: frozenset[str] = frozenset({"src/talos/ui/document_parser.py"})


def _file_uses_canonical_event(content: str) -> bool:
    return any(event in content for event in CANONICAL_EVENTS)


@pytest.mark.governance
def test_no_silent_drops_under_src() -> None:
    if not _SRC_ROOT.exists():
        pytest.skip("src/talos/ non esiste ancora")

    offenders: list[str] = []
    for py in _SRC_ROOT.rglob("*.py"):
        relative = str(py.relative_to(_PROJECT_ROOT))
        if relative in _EXEMPT_FILES:
            continue
        content = py.read_text(encoding="utf-8")
        has_drop_pattern = any(pat.search(content) for pat in _DROP_PATTERNS)
        if not has_drop_pattern:
            continue
        if not _file_uses_canonical_event(content):
            offenders.append(relative)

    assert not offenders, (
        "R-01 NO SILENT DROPS (ADR-0021): i seguenti file hanno pattern di "
        "scarto (.drop / .skip / continue) ma nessuna chiamata a un evento "
        "canonico del catalogo:\n" + "\n".join(offenders)
    )
