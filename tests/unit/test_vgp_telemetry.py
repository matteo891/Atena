"""Unit test telemetria `compute_vgp_score` (CHG-2026-04-30-049).

Verifica emissione eventi canonici ADR-0021:
- `vgp.veto_roi_failed` per ASIN sotto soglia ROI ma non killed.
- `vgp.kill_switch_zero` per ASIN con kill_mask=True.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from talos.vgp import compute_vgp_score

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, float, float, bool, str]]) -> pd.DataFrame:
    """Helper rows = [(asin, roi, velocity, cash_profit, kill, match_status)]."""
    return pd.DataFrame(
        rows,
        columns=["asin", "roi", "velocity_monthly", "cash_profit_eur", "kill_mask", "match_status"],
    )


def test_veto_roi_failed_event_emitted(caplog: pytest.LogCaptureFixture) -> None:
    """ASIN con ROI < 0.08 e non killed → emette `vgp.veto_roi_failed`."""
    df = _df(
        [
            ("A_OK", 0.20, 2.0, 100.0, False, "MATCH"),
            ("B_VETO", 0.05, 1.5, 50.0, False, "MATCH"),  # vetoed
            ("C_OK", 0.15, 1.0, 80.0, False, "MATCH"),
        ],
    )
    with caplog.at_level(logging.DEBUG, logger="talos.vgp.score"):
        compute_vgp_score(df)

    veto_records = [r for r in caplog.records if r.message == "vgp.veto_roi_failed"]
    assert len(veto_records) == 1
    rec = veto_records[0]
    assert getattr(rec, "asin", None) == "B_VETO"
    assert getattr(rec, "roi_pct", None) == pytest.approx(0.05)
    assert getattr(rec, "threshold", None) == pytest.approx(0.08)


def test_kill_switch_zero_event_emitted(caplog: pytest.LogCaptureFixture) -> None:
    """ASIN con kill_mask=True → emette `vgp.kill_switch_zero` con match_status."""
    df = _df(
        [
            ("A_OK", 0.20, 2.0, 100.0, False, "MATCH"),
            ("B_KILL", 0.30, 1.5, 50.0, True, "MISMATCH"),  # killed
        ],
    )
    with caplog.at_level(logging.DEBUG, logger="talos.vgp.score"):
        compute_vgp_score(df)

    kill_records = [r for r in caplog.records if r.message == "vgp.kill_switch_zero"]
    assert len(kill_records) == 1
    rec = kill_records[0]
    assert getattr(rec, "asin", None) == "B_KILL"
    assert getattr(rec, "match_status", None) == "MISMATCH"


def test_no_telemetry_when_all_pass(caplog: pytest.LogCaptureFixture) -> None:
    """Tutti gli ASIN passano R-05 e R-08 → nessun evento di scarto."""
    df = _df(
        [
            ("A", 0.20, 2.0, 100.0, False, "MATCH"),
            ("B", 0.15, 1.5, 50.0, False, "MATCH"),
        ],
    )
    with caplog.at_level(logging.DEBUG, logger="talos.vgp.score"):
        compute_vgp_score(df)

    veto = [r for r in caplog.records if r.message == "vgp.veto_roi_failed"]
    kill = [r for r in caplog.records if r.message == "vgp.kill_switch_zero"]
    assert veto == []
    assert kill == []


def test_telemetry_skipped_when_asin_col_absent(caplog: pytest.LogCaptureFixture) -> None:
    """Senza colonna `asin`, nessuna emissione (graceful skip, no crash)."""
    df = pd.DataFrame(
        {
            "roi": [0.05, 0.20],
            "velocity_monthly": [1.0, 2.0],
            "cash_profit_eur": [50.0, 100.0],
            "kill_mask": [False, False],
        },
    )
    with caplog.at_level(logging.DEBUG, logger="talos.vgp.score"):
        compute_vgp_score(df)

    veto = [r for r in caplog.records if r.message == "vgp.veto_roi_failed"]
    assert veto == []  # asin manca → skip


def test_kill_event_uses_empty_string_when_match_status_absent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Senza colonna `match_status`, kill event emesso con match_status=''."""
    df = pd.DataFrame(
        {
            "asin": ["X_KILL", "Y_OK"],
            "roi": [0.30, 0.15],
            "velocity_monthly": [1.0, 2.0],
            "cash_profit_eur": [50.0, 100.0],
            "kill_mask": [True, False],
        },
    )
    with caplog.at_level(logging.DEBUG, logger="talos.vgp.score"):
        compute_vgp_score(df)

    kill = [r for r in caplog.records if r.message == "vgp.kill_switch_zero"]
    assert len(kill) == 1
    assert getattr(kill[0], "asin", None) == "X_KILL"
    assert getattr(kill[0], "match_status", None) == ""
