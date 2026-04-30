"""Unit test per `talos.ui.dashboard` (CHG-2026-04-30-040, ADR-0016).

Test minimali: import smoke + helper testabili (`parse_locked_in`).
Render Streamlit + interazione UI sono out-of-scope (richiederebbe
`streamlit.testing.v1.AppTest` + ambiente test dedicato — scope CHG futuro).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_dashboard_module_imports() -> None:
    """Smoke test: il modulo si importa senza errori (no streamlit runtime)."""
    from talos.ui.dashboard import (  # noqa: PLC0415
        DEFAULT_BUDGET_EUR,
        main,
        parse_locked_in,
    )

    assert callable(main)
    assert callable(parse_locked_in)
    assert pytest.approx(10_000.0) == DEFAULT_BUDGET_EUR


def test_parse_locked_in_simple() -> None:
    """Caso base: 3 ASIN comma-separated."""
    from talos.ui.dashboard import parse_locked_in  # noqa: PLC0415

    assert parse_locked_in("AAA, BBB,CCC") == ["AAA", "BBB", "CCC"]


def test_parse_locked_in_empty_string() -> None:
    """Stringa vuota -> lista vuota."""
    from talos.ui.dashboard import parse_locked_in  # noqa: PLC0415

    assert parse_locked_in("") == []


def test_parse_locked_in_only_commas() -> None:
    """Solo virgole/spazi -> lista vuota."""
    from talos.ui.dashboard import parse_locked_in  # noqa: PLC0415

    assert parse_locked_in(",,, , ,") == []


def test_parse_locked_in_strip_whitespace() -> None:
    """Spazi multipli e tab vengono strippati."""
    from talos.ui.dashboard import parse_locked_in  # noqa: PLC0415

    assert parse_locked_in("  AAA  ,\tBBB\n,  CCC") == ["AAA", "BBB", "CCC"]


def test_parse_locked_in_filters_empty() -> None:
    """Token vuoti tra virgole vengono filtrati."""
    from talos.ui.dashboard import parse_locked_in  # noqa: PLC0415

    assert parse_locked_in(",,,A,, B, ") == ["A", "B"]


def test_parse_locked_in_single_asin() -> None:
    """Un solo ASIN, no virgola."""
    from talos.ui.dashboard import parse_locked_in  # noqa: PLC0415

    assert parse_locked_in("XYZ123") == ["XYZ123"]


def test_dashboard_re_exports_in_init() -> None:
    """`talos.ui` re-esporta `parse_locked_in` e `DEFAULT_BUDGET_EUR`."""
    from talos import ui  # noqa: PLC0415

    assert hasattr(ui, "parse_locked_in")
    assert hasattr(ui, "DEFAULT_BUDGET_EUR")
