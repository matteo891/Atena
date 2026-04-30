"""ADR-0013: vieta `from src.` o `import src.` nel codice e nei test.

Lo src-layout è valido solo se nessuno scavalca il pacchetto installato
e importa direttamente dalla root del repo. Questo test fallisce se
qualcuno introduce un import "magico".
"""

import re
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCAN_ROOTS = (_PROJECT_ROOT / "src", _PROJECT_ROOT / "tests")
_PATTERNS = (
    re.compile(r"^\s*from\s+src\."),
    re.compile(r"^\s*import\s+src\."),
)


@pytest.mark.governance
def test_no_root_imports() -> None:
    offenders: list[str] = [
        f"{py.relative_to(_PROJECT_ROOT)}:{lineno}: {line.strip()}"
        for root in _SCAN_ROOTS
        if root.exists()
        for py in root.rglob("*.py")
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1)
        if any(pat.match(line) for pat in _PATTERNS)
    ]
    assert not offenders, "Imports proibiti (ADR-0013):\n" + "\n".join(offenders)
