"""Test di composizione end-to-end della catena del valore scalare.

CHG-2026-04-30-028, ADR-0019 + ADR-0018.

Verifica che le 4 funzioni applicative + il predicato veto, chiamate
in sequenza con un singolo input realistico (BuyBox + Referral +
Costo_Fornitore), producano un risultato coerente fino al boolean del
Veto R-08:

    fee_fba_manual --> cash_inflow_eur --> cash_profit_eur --> roi --> is_vetoed_by_roi

I test isolati di ogni anello (test_fee_fba.py, test_cash_inflow.py,
test_cash_profit.py, test_roi.py, test_veto.py) gia' coprono
correttezza individuale + edge case + raises. Questo file aggiunge
sentinella sulla **coerenza dei contratti tra anelli**: un cambio di
firma o di unita' di misura in un singolo anello rompe la
composizione anche se i test isolati continuassero a passare.
"""

from __future__ import annotations

from math import isclose

import pytest

from talos.formulas import cash_inflow_eur, cash_profit_eur, fee_fba_manual, roi
from talos.vgp import is_vetoed_by_roi

pytestmark = pytest.mark.unit

_TOL_EUR = 1e-3
_TOL_ROI = 1e-3


def test_chain_intermediate_values_match_snapshots() -> None:
    """Anchor: scenario 'low_value' con valori intermedi catturati.

    Numeri ancorati ai snapshot dei singoli test (CHG-022/025/026):
    BuyBox=200, Referral=8%, Costo=100 -> ROI=64.59%, NON vetato.
    """
    # CHG-022 anchor
    fee = fee_fba_manual(200.0)
    assert isclose(fee, 19.4078, abs_tol=_TOL_EUR)

    # CHG-025 anchor
    inflow = cash_inflow_eur(200.0, fee, 0.08)
    assert isclose(inflow, 164.5922, abs_tol=_TOL_EUR)

    # CHG-026 anchor (cash_profit)
    profit = cash_profit_eur(inflow, 100.0)
    assert isclose(profit, 64.5922, abs_tol=_TOL_EUR)

    # CHG-026 anchor (roi)
    roi_value = roi(profit, 100.0)
    assert isclose(roi_value, 0.6459, abs_tol=_TOL_ROI)

    # CHG-027: ROI 64.59% >> 8% soglia -> NON vetato
    assert is_vetoed_by_roi(roi_value) is False


@pytest.mark.parametrize(
    ("buy_box", "ref", "costo", "expected_vetoed", "label"),
    [
        (200.0, 0.08, 100.0, False, "low_value_passes"),
        (500.0, 0.15, 300.0, False, "mid_value_passes"),
        (1000.0, 0.08, 600.0, False, "high_value_passes"),
        (122.0, 0.15, 110.0, True, "loss_leader_vetoed"),
        (200.0, 0.08, 158.0, True, "thin_margin_vetoed"),
    ],
)
def test_chain_e2e_pass_or_veto(
    buy_box: float,
    ref: float,
    costo: float,
    expected_vetoed: bool,  # noqa: FBT001 — pytest.parametrize passa per posizione
    label: str,
) -> None:
    """Outcome end-to-end della pipeline scalare su 5 scenari realistici.

    Verifica solo il boolean finale del veto, non i valori intermedi.
    Tre happy-path + due vetoed (loss-leader R-08 negativo + thin-margin
    sotto soglia 8%).
    """
    fee = fee_fba_manual(buy_box)
    inflow = cash_inflow_eur(buy_box, fee, ref)
    profit = cash_profit_eur(inflow, costo)
    roi_value = roi(profit, costo)
    vetoed = is_vetoed_by_roi(roi_value)

    assert vetoed is expected_vetoed, (
        f"scenario '{label}': roi={roi_value:.4f}, expected_vetoed={expected_vetoed}, got={vetoed}"
    )
