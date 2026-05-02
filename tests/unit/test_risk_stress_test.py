"""Test unit 90-Day Stress Test Filter (ADR-0023 / CHG-2026-05-02-032)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from talos.risk import (
    is_stress_test_failed_mask,
    passes_90d_stress_test,
)
from talos.vgp import compute_vgp_score

if TYPE_CHECKING:
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# `passes_90d_stress_test` scalare
# ---------------------------------------------------------------------------


def test_passes_break_even_simple() -> None:
    """avg90=100, cost=50, fee=4.10, ref=0.08 → cash_inflow=87.9 >= 50 → pass."""
    assert (
        passes_90d_stress_test(
            buy_box_avg90=100.0,
            cost_eur=50.0,
            fee_fba_eur=4.10,
            referral_fee_rate=0.08,
        )
        is True
    )


def test_fails_break_even_when_inflow_lt_cost() -> None:
    """avg90=50, cost=50, fee=4.10, ref=0.08 → cash_inflow=41.9 < 50 → fail."""
    assert (
        passes_90d_stress_test(
            buy_box_avg90=50.0,
            cost_eur=50.0,
            fee_fba_eur=4.10,
            referral_fee_rate=0.08,
        )
        is False
    )


def test_passes_exactly_break_even() -> None:
    """Boundary: cash_inflow == cost (boundary inclusivo: >= passa)."""
    # avg90=100, fee=8, ref=0.10 → inflow = 100 - 8 - 10 = 82.
    # Pongo cost = 82 → break-even esatto → True.
    assert (
        passes_90d_stress_test(
            buy_box_avg90=100.0,
            cost_eur=82.0,
            fee_fba_eur=8.0,
            referral_fee_rate=0.10,
        )
        is True
    )


def test_passes_when_avg90_is_none() -> None:
    """ASIN nuovi senza dato 90gg → pass (decisione Leader default)."""
    assert (
        passes_90d_stress_test(
            buy_box_avg90=None,
            cost_eur=50.0,
            fee_fba_eur=4.10,
            referral_fee_rate=0.08,
        )
        is True
    )


# ---------------------------------------------------------------------------
# `is_stress_test_failed_mask` vettoriale
# ---------------------------------------------------------------------------


def test_mask_basic() -> None:
    """Mask vettoriale: True dove FAIL, False altrove."""
    df = pd.DataFrame(
        {
            "buy_box_avg90": [100.0, 50.0, 200.0],
            "cost_eur": [50.0, 50.0, 50.0],
            "fee_fba_eur": [4.10, 4.10, 4.10],
            "referral_fee_resolved": [0.08, 0.08, 0.08],
        },
    )
    mask = is_stress_test_failed_mask(df)
    # row 0: inflow=87.9 >= 50 → False (pass)
    # row 1: inflow=41.9 < 50 → True (fail)
    # row 2: inflow=179.92 >= 50 → False (pass)
    assert mask.tolist() == [False, True, False]


def test_mask_nan_avg90_passes() -> None:
    """NaN avg90 → False (= NOT failed = pass)."""
    df = pd.DataFrame(
        {
            "buy_box_avg90": [100.0, float("nan"), 30.0],
            "cost_eur": [50.0, 50.0, 50.0],
            "fee_fba_eur": [4.10, 4.10, 4.10],
            "referral_fee_resolved": [0.08, 0.08, 0.08],
        },
    )
    mask = is_stress_test_failed_mask(df)
    # row 1: NaN → False (pass)
    # row 2: inflow=23.5 < 50 → True (fail)
    assert mask.tolist() == [False, False, True]


# ---------------------------------------------------------------------------
# Integrazione `compute_vgp_score`
# ---------------------------------------------------------------------------


def _build_listino_with_stress(
    avg90s: list[float | None] | None = None,
) -> pd.DataFrame:
    """DataFrame con colonne richieste + opzionale avg90 per stress test."""
    df = pd.DataFrame(
        {
            "asin": ["B0AAA", "B0BBB", "B0CCC", "B0DDD"],
            "roi": [0.30, 0.30, 0.30, 0.30],
            "velocity_monthly": [10.0, 20.0, 30.0, 40.0],
            "cash_profit_eur": [50.0, 60.0, 70.0, 80.0],
            "kill_mask": [False, False, False, False],
            "match_status": ["SICURO", "SICURO", "SICURO", "SICURO"],
            "cost_eur": [50.0, 50.0, 50.0, 50.0],
            "fee_fba_eur": [4.10, 4.10, 4.10, 4.10],
            "referral_fee_resolved": [0.08, 0.08, 0.08, 0.08],
        },
    )
    if avg90s is not None:
        df["buy_box_avg90"] = avg90s
    return df


def test_vgp_backwards_compat_no_stress_col() -> None:
    """Senza colonna `buy_box_avg90` → behavior invariato (970 test esistenti)."""
    df = _build_listino_with_stress(avg90s=None)
    result = compute_vgp_score(df)
    # Nessun ASIN deve essere vetato dallo stress test (colonna assente).
    assert result.loc[result["asin"] == "B0DDD", "vgp_score"].iloc[0] > 0


def test_vgp_stress_test_vetoes_low_avg90() -> None:
    """avg90 troppo basso → cash_inflow < cost → vgp_score = 0."""
    df = _build_listino_with_stress(avg90s=[100.0, 30.0, 200.0, 150.0])
    result = compute_vgp_score(df)
    # B0BBB (avg90=30, cost=50) deve fallire stress test.
    assert result.loc[result["asin"] == "B0BBB", "vgp_score"].iloc[0] == 0
    # B0DDD (avg90=150, cost=50) deve passare.
    assert result.loc[result["asin"] == "B0DDD", "vgp_score"].iloc[0] > 0


def test_vgp_stress_test_nan_passes() -> None:
    """avg90 NaN → pass (decisione Leader default)."""
    df = _build_listino_with_stress(avg90s=[float("nan"), 30.0, 100.0, 200.0])
    result = compute_vgp_score(df)
    assert result.loc[result["asin"] == "B0BBB", "vgp_score"].iloc[0] == 0  # vetato
    # B0DDD (max + avg90=200) deve passare.
    assert result.loc[result["asin"] == "B0DDD", "vgp_score"].iloc[0] > 0


# ---------------------------------------------------------------------------
# Telemetria `vgp.stress_test_failed`
# ---------------------------------------------------------------------------


def test_telemetry_stress_test_failed_emitted(log_capture: LogCapture) -> None:
    """Evento canonico per ogni ASIN che fallisce stress test."""
    df = _build_listino_with_stress(avg90s=[100.0, 30.0, 200.0, 25.0])
    compute_vgp_score(df)
    events = [e for e in log_capture.entries if e["event"] == "vgp.stress_test_failed"]
    # 2 ASIN devono triggerare (B0BBB avg90=30 + B0DDD avg90=25).
    assert len(events) == 2
    asins = {e["asin"] for e in events}
    assert asins == {"B0BBB", "B0DDD"}


def test_telemetry_no_stress_event_if_all_pass(log_capture: LogCapture) -> None:
    """Nessun evento se tutti passano lo stress test."""
    df = _build_listino_with_stress(avg90s=[100.0, 150.0, 200.0, 250.0])
    compute_vgp_score(df)
    events = [e for e in log_capture.entries if e["event"] == "vgp.stress_test_failed"]
    assert events == []


def test_telemetry_no_stress_event_if_col_missing(log_capture: LogCapture) -> None:
    """Nessun evento se la colonna avg90 manca (graceful skip)."""
    df = _build_listino_with_stress(avg90s=None)
    compute_vgp_score(df)
    events = [e for e in log_capture.entries if e["event"] == "vgp.stress_test_failed"]
    assert events == []


def test_telemetry_event_includes_avg90_and_cost(log_capture: LogCapture) -> None:
    """Sentinel: extra dict contiene `buy_box_avg90` + `cost`."""
    df = _build_listino_with_stress(avg90s=[100.0, 30.0, 200.0, 150.0])
    compute_vgp_score(df)
    events = [e for e in log_capture.entries if e["event"] == "vgp.stress_test_failed"]
    assert len(events) == 1
    assert events[0]["asin"] == "B0BBB"
    assert events[0]["buy_box_avg90"] == 30.0
    assert events[0]["cost"] == 50.0
