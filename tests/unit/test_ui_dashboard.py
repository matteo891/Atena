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


def test_get_session_factory_returns_none_without_db_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza `TALOS_DB_URL`, `get_session_factory_or_none` ritorna None (graceful)."""
    from talos.config import get_settings  # noqa: PLC0415
    from talos.ui.dashboard import get_session_factory_or_none  # noqa: PLC0415

    monkeypatch.delenv("TALOS_DB_URL", raising=False)
    # Invalida la cache lru_cache su get_settings per forzare reload con env modificato.
    get_settings.cache_clear()

    factory = get_session_factory_or_none()
    assert factory is None


# ---------------------------------------------------------------------------
# `_pct_column_config` (CHG-2026-05-01-040)
# ---------------------------------------------------------------------------


def test_pct_column_config_maps_known_percentage_columns() -> None:
    """Helper ritorna entry per ogni colonna in `_PERCENTAGE_COLUMNS`."""
    from talos.ui.dashboard import _pct_column_config  # noqa: PLC0415

    cols = ["asin", "roi", "vgp_score", "cost_eur", "referral_fee_pct"]
    cfg = _pct_column_config(cols)
    assert set(cfg.keys()) == {"roi", "vgp_score", "referral_fee_pct"}


def test_pct_column_config_empty_when_no_percentage_columns() -> None:
    """DataFrame senza colonne percentuali -> dict vuoto (no-op safe)."""
    from talos.ui.dashboard import _pct_column_config  # noqa: PLC0415

    cfg = _pct_column_config(["asin", "buy_box_eur", "cost_eur", "qty"])
    assert cfg == {}


def test_pct_column_config_includes_norm_intermediates() -> None:
    """Colonne intermedie *_norm e vgp_score_raw vanno in display percentuale."""
    from talos.ui.dashboard import _pct_column_config  # noqa: PLC0415

    cols = ["roi_norm", "velocity_norm", "cash_profit_norm", "vgp_score_raw"]
    cfg = _pct_column_config(cols)
    assert set(cfg.keys()) == {
        "roi_norm",
        "velocity_norm",
        "cash_profit_norm",
        "vgp_score_raw",
    }


def test_pct_column_config_excludes_confidence_pct() -> None:
    """`confidence_pct` è già 0-100 (compute_confidence) -> NON formattare come %."""
    from talos.ui.dashboard import _pct_column_config  # noqa: PLC0415

    cfg = _pct_column_config(["confidence_pct", "asin"])
    assert "confidence_pct" not in cfg


def test_persistence_helpers_re_exported() -> None:
    """`talos.ui` re-esporta `get_session_factory_or_none`, `try_persist_session`."""
    from talos import ui  # noqa: PLC0415

    assert hasattr(ui, "get_session_factory_or_none")
    assert hasattr(ui, "try_persist_session")
    assert hasattr(ui, "DEFAULT_TENANT_ID")
    assert ui.DEFAULT_TENANT_ID == 1
