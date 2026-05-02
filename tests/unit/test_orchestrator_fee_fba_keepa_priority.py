"""Test CHG-2026-05-02-040: fee_fba atomica Keepa preferred over L11b fallback.

Sentinel: l'orchestrator (`_enrich_listino`) ora usa la colonna
`fee_fba_eur_keepa` quando popolata (errata alpha-prime invertita). Fallback a
`fee_fba_manual` L11b solo quando Keepa non espone il dato.
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.formulas.fee_fba import fee_fba_manual
from talos.orchestrator import SessionInput, run_session

pytestmark = pytest.mark.unit


def _build_listino_raw_with_keepa_fee(fee_keepa: float | None) -> pd.DataFrame:
    """Listino raw minimo + colonna `fee_fba_eur_keepa` opzionale."""
    return pd.DataFrame(
        [
            {
                "asin": "B0DZHNGR82",
                "buy_box_eur": 238.0,
                "cost_eur": 185.0,
                "referral_fee_pct": 0.08,
                "v_tot": 41,
                "s_comp": 0,
                "match_status": "SICURO",
                "fee_fba_eur_keepa": fee_keepa,
            },
        ],
    )


def test_orchestrator_uses_keepa_fee_when_present() -> None:
    """Quando colonna `fee_fba_eur_keepa` ha valore, orchestrator usa quello.

    Ground truth Leader: A26 con fee atomica €3.05 → ROI ~16.74%.
    """
    df = _build_listino_raw_with_keepa_fee(fee_keepa=3.05)
    inp = SessionInput(
        listino_raw=df,
        budget=10000.0,
        velocity_target_days=15,
        veto_roi_threshold=0.08,
    )
    result = run_session(inp)
    enriched = result.enriched_df
    # fee_fba_eur deve essere ~3.05, NON ~22 (L11b).
    assert enriched.iloc[0]["fee_fba_eur"] == pytest.approx(3.05, abs=0.01)
    # ROI calculation match ground truth.
    cash_inflow = 238.0 - 3.05 - 238.0 * 0.08
    cash_profit = cash_inflow - 185.0
    expected_roi = cash_profit / 185.0
    assert enriched.iloc[0]["roi"] == pytest.approx(expected_roi, abs=0.001)


def test_orchestrator_fallback_to_l11b_when_keepa_fee_none() -> None:
    """Quando colonna `fee_fba_eur_keepa` è None → fallback fee_fba_manual L11b."""
    df = _build_listino_raw_with_keepa_fee(fee_keepa=None)
    inp = SessionInput(
        listino_raw=df,
        budget=10000.0,
        velocity_target_days=15,
        veto_roi_threshold=0.08,
    )
    result = run_session(inp)
    enriched = result.enriched_df
    # fee_fba L11b per buybox 238 → ~22.03.
    expected_l11b = float(fee_fba_manual(238.0))
    assert enriched.iloc[0]["fee_fba_eur"] == pytest.approx(expected_l11b, abs=0.01)


def test_orchestrator_backwards_compat_no_keepa_column() -> None:
    """Listino raw senza colonna `fee_fba_eur_keepa` → comportamento pre-CHG-040 invariato."""
    df = pd.DataFrame(
        [
            {
                "asin": "B0DZHNGR82",
                "buy_box_eur": 238.0,
                "cost_eur": 185.0,
                "referral_fee_pct": 0.08,
                "v_tot": 41,
                "s_comp": 0,
                "match_status": "SICURO",
            },
        ],
    )
    inp = SessionInput(
        listino_raw=df,
        budget=10000.0,
        velocity_target_days=15,
        veto_roi_threshold=0.08,
    )
    result = run_session(inp)
    enriched = result.enriched_df
    expected_l11b = float(fee_fba_manual(238.0))
    assert enriched.iloc[0]["fee_fba_eur"] == pytest.approx(expected_l11b, abs=0.01)
