"""Test unit per `talos.formulas.cash_inflow` (CHG-2026-04-30-025, ADR-0018).

Snapshot tolerance-based (1e-3 EUR) — fissano il **comportamento osservabile**
della Formula 1 verbatim del Leader, non i bit floating-point.

Composizione con `fee_fba_manual`: i valori di `fee_fba` negli snapshot sono
quelli verificati in `test_fee_fba.py` (CHG-022), così che la chain
`fee_fba_manual → cash_inflow_eur` sia internamente coerente per costruzione.
"""

from __future__ import annotations

from itertools import pairwise
from math import isclose

import pytest

from talos.formulas import cash_inflow_eur

pytestmark = pytest.mark.unit

_TOL = 1e-3  # EUR


def test_snapshot_low_value() -> None:
    # buy_box=200, fee_fba=19.4078 (CHG-022), referral_fee=8%
    # cash_inflow = 200 - 19.4078 - (200 * 0.08) = 164.5922
    assert isclose(cash_inflow_eur(200.0, 19.4078, 0.08), 164.5922, abs_tol=_TOL)


def test_snapshot_mid_value() -> None:
    # buy_box=500, fee_fba=40.0753 (CHG-022), referral_fee=15%
    # cash_inflow = 500 - 40.0753 - 75 = 384.9247
    assert isclose(cash_inflow_eur(500.0, 40.0753, 0.15), 384.9247, abs_tol=_TOL)


def test_snapshot_high_value() -> None:
    # buy_box=1000, fee_fba=74.5212 (CHG-022), referral_fee=8%
    # cash_inflow = 1000 - 74.5212 - 80 = 845.4788
    assert isclose(cash_inflow_eur(1000.0, 74.5212, 0.08), 845.4788, abs_tol=_TOL)


def test_zero_referral_fee() -> None:
    """`referral_fee_rate=0` (boundary inclusivo) -> cash_inflow = buy_box - fee_fba."""
    assert isclose(cash_inflow_eur(200.0, 19.4078, 0.0), 180.5922, abs_tol=_TOL)


def test_negative_cash_inflow_is_allowed() -> None:
    """Vendita in perdita: `cash_inflow < 0` è un fatto economico, non un errore.

    `100 - 80 - (100 * 0.5) = -30` deve essere restituito invariato.
    Il filtro applicativo è il Veto ROI (R-08) a valle, non questa formula.
    """
    assert isclose(cash_inflow_eur(100.0, 80.0, 0.5), -30.0, abs_tol=_TOL)


def test_decreases_monotonically_with_referral_fee() -> None:
    """A parita' di `buy_box` e `fee_fba`, +`referral_fee_rate` => -`cash_inflow`."""
    rates = [0.0, 0.05, 0.10, 0.15, 0.20]
    inflows = [cash_inflow_eur(500.0, 40.0, r) for r in rates]
    for prev, curr in pairwise(inflows):
        assert curr < prev


def test_raises_on_negative_buy_box() -> None:
    with pytest.raises(ValueError, match="buy_box_eur"):
        cash_inflow_eur(-1.0, 10.0, 0.08)


def test_raises_on_negative_fee_fba() -> None:
    with pytest.raises(ValueError, match="fee_fba_eur"):
        cash_inflow_eur(200.0, -1.0, 0.08)


@pytest.mark.parametrize("rate", [-0.01, 1.01, 2.0])
def test_raises_on_referral_fee_out_of_range(rate: float) -> None:
    """R-01: aliquote fisicamente impossibili (<0 o >1) → ValueError esplicito."""
    with pytest.raises(ValueError, match="referral_fee_rate"):
        cash_inflow_eur(200.0, 19.4078, rate)
