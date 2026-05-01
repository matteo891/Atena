"""Unit test telemetria `compute_vgp_score` (CHG-2026-04-30-049 + CHG-B1.1.a).

Verifica emissione eventi canonici ADR-0021 via `structlog.testing.LogCapture`:
- `vgp.veto_roi_failed` per ASIN sotto soglia ROI ma non killed.
- `vgp.kill_switch_zero` per ASIN con kill_mask=True.

Pattern: la fixture `log_capture` riconfigura structlog con `LogCapture` come
unico processor + `merge_contextvars` (preserva propagazione contestuale).
"""

from __future__ import annotations

import pandas as pd
import pytest
import structlog
from structlog.testing import LogCapture

from talos.vgp import compute_vgp_score

pytestmark = pytest.mark.unit


@pytest.fixture
def log_capture() -> LogCapture:
    """Cattura eventi structlog per assertion (pattern test_logging_config)."""
    capture = LogCapture()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            capture,
        ],
        cache_logger_on_first_use=False,
    )
    return capture


def _df(rows: list[tuple[str, float, float, float, bool, str]]) -> pd.DataFrame:
    """Helper rows = [(asin, roi, velocity, cash_profit, kill, match_status)]."""
    return pd.DataFrame(
        rows,
        columns=["asin", "roi", "velocity_monthly", "cash_profit_eur", "kill_mask", "match_status"],
    )


def test_veto_roi_failed_event_emitted(log_capture: LogCapture) -> None:
    """ASIN con ROI < 0.08 e non killed → emette `vgp.veto_roi_failed`."""
    df = _df(
        [
            ("A_OK", 0.20, 2.0, 100.0, False, "MATCH"),
            ("B_VETO", 0.05, 1.5, 50.0, False, "MATCH"),  # vetoed
            ("C_OK", 0.15, 1.0, 80.0, False, "MATCH"),
        ],
    )
    compute_vgp_score(df)

    veto_entries = [e for e in log_capture.entries if e["event"] == "vgp.veto_roi_failed"]
    assert len(veto_entries) == 1
    entry = veto_entries[0]
    assert entry["asin"] == "B_VETO"
    assert entry["roi_pct"] == pytest.approx(0.05)
    assert entry["threshold"] == pytest.approx(0.08)


def test_kill_switch_zero_event_emitted(log_capture: LogCapture) -> None:
    """ASIN con kill_mask=True → emette `vgp.kill_switch_zero` con match_status."""
    df = _df(
        [
            ("A_OK", 0.20, 2.0, 100.0, False, "MATCH"),
            ("B_KILL", 0.30, 1.5, 50.0, True, "MISMATCH"),  # killed
        ],
    )
    compute_vgp_score(df)

    kill_entries = [e for e in log_capture.entries if e["event"] == "vgp.kill_switch_zero"]
    assert len(kill_entries) == 1
    entry = kill_entries[0]
    assert entry["asin"] == "B_KILL"
    assert entry["match_status"] == "MISMATCH"


def test_no_telemetry_when_all_pass(log_capture: LogCapture) -> None:
    """Tutti gli ASIN passano R-05 e R-08 → nessun evento di scarto."""
    df = _df(
        [
            ("A", 0.20, 2.0, 100.0, False, "MATCH"),
            ("B", 0.15, 1.5, 50.0, False, "MATCH"),
        ],
    )
    compute_vgp_score(df)

    veto = [e for e in log_capture.entries if e["event"] == "vgp.veto_roi_failed"]
    kill = [e for e in log_capture.entries if e["event"] == "vgp.kill_switch_zero"]
    assert veto == []
    assert kill == []


def test_telemetry_skipped_when_asin_col_absent(log_capture: LogCapture) -> None:
    """Senza colonna `asin`, nessuna emissione (graceful skip, no crash)."""
    df = pd.DataFrame(
        {
            "roi": [0.05, 0.20],
            "velocity_monthly": [1.0, 2.0],
            "cash_profit_eur": [50.0, 100.0],
            "kill_mask": [False, False],
        },
    )
    compute_vgp_score(df)

    veto = [e for e in log_capture.entries if e["event"] == "vgp.veto_roi_failed"]
    assert veto == []  # asin manca → skip


def test_kill_event_uses_empty_string_when_match_status_absent(
    log_capture: LogCapture,
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
    compute_vgp_score(df)

    kill = [e for e in log_capture.entries if e["event"] == "vgp.kill_switch_zero"]
    assert len(kill) == 1
    assert kill[0]["asin"] == "X_KILL"
    assert kill[0]["match_status"] == ""
