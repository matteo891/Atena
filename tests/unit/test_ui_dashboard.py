"""Unit test per `talos.ui.dashboard` (CHG-2026-04-30-040, ADR-0016).

Test minimali: import smoke + helper testabili (`parse_locked_in`).
Render Streamlit + interazione UI sono out-of-scope (richiederebbe
`streamlit.testing.v1.AppTest` + ambiente test dedicato — scope CHG futuro).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AAA, BBB,CCC", ["AAA", "BBB", "CCC"]),
        ("", []),
        (",,, , ,", []),
        ("  AAA  ,\tBBB\n,  CCC", ["AAA", "BBB", "CCC"]),
        (",,,A,, B, ", ["A", "B"]),
        ("XYZ123", ["XYZ123"]),
    ],
)
def test_parse_locked_in_parametric(raw: str, expected: list[str]) -> None:
    """Parser comma-separated: strip + filter empty + edge cases.

    Sostituisce 6 test single-case con un parametrico (CHG-2026-05-02-004
    snellimento: rule-of-three + dispersion via parametrize).
    """
    from talos.ui.dashboard import parse_locked_in  # noqa: PLC0415

    assert parse_locked_in(raw) == expected


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


# ---------------------------------------------------------------------------
# `_percentage_view` (CHG-2026-05-02-002 fix d3-format → printf x100)
# ---------------------------------------------------------------------------


def test_percentage_view_multiplies_by_100_only_pct_columns() -> None:
    """`_percentage_view` moltiplica x100 solo le colonne in _PERCENTAGE_COLUMNS."""
    import pandas as pd  # noqa: PLC0415

    from talos.ui.dashboard import _percentage_view  # noqa: PLC0415

    df = pd.DataFrame(
        {
            "asin": ["B0AAA", "B0BBB"],
            "cost_eur": [100.0, 200.0],  # NON percentage
            "roi": [0.225, 0.182],  # percentage
            "vgp_score": [0.85, 0.42],  # percentage
        },
    )
    df_view, cfg = _percentage_view(df)
    assert df_view["asin"].tolist() == ["B0AAA", "B0BBB"]
    assert df_view["cost_eur"].tolist() == [100.0, 200.0]  # invariato
    assert df_view["roi"].tolist() == [22.5, 18.2]  # x100 con tolerance
    assert df_view["vgp_score"].tolist() == [85.0, 42.0]
    assert set(cfg.keys()) == {"roi", "vgp_score"}


def test_percentage_view_no_pct_columns_returns_original_no_copy() -> None:
    """Df senza colonne percentage -> ritorna originale (no copy), cfg vuoto."""
    import pandas as pd  # noqa: PLC0415

    from talos.ui.dashboard import _percentage_view  # noqa: PLC0415

    df = pd.DataFrame({"asin": ["B0AAA"], "cost_eur": [100.0], "qty": [3]})
    df_view, cfg = _percentage_view(df)
    assert df_view is df  # no copy se nessuna colonna percentage
    assert cfg == {}


def test_percentage_view_does_not_mutate_input() -> None:
    """Anche con colonne percentage, il df originale non deve essere modificato."""
    import pandas as pd  # noqa: PLC0415

    from talos.ui.dashboard import _percentage_view  # noqa: PLC0415

    df = pd.DataFrame({"roi": [0.225, 0.182], "asin": ["B0AAA", "B0BBB"]})
    df_view, _cfg = _percentage_view(df)
    # Originale invariato (frazione)
    assert df["roi"].tolist() == [0.225, 0.182]
    # View moltiplicata
    assert df_view["roi"].tolist() == [22.5, 18.2]
