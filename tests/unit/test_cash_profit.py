"""Test unit per `talos.formulas.cash_profit` (CHG-2026-04-30-026, ADR-0018).

Snapshot tolerance-based (1e-3 EUR) - composti con `cash_inflow_eur`
di CHG-025 per coerenza interna della catena fee_fba -> cash_inflow ->
cash_profit.
"""

from __future__ import annotations

from itertools import pairwise
from math import isclose

import pytest

from talos.formulas import cash_profit_eur

pytestmark = pytest.mark.unit

_TOL = 1e-3  # EUR


def test_snapshot_low_value() -> None:
    # cash_inflow=164.5922 (CHG-025), costo=100
    # cash_profit = 164.5922 - 100 = 64.5922
    assert isclose(cash_profit_eur(164.5922, 100.0), 64.5922, abs_tol=_TOL)


def test_snapshot_mid_value() -> None:
    # cash_inflow=384.9247 (CHG-025), costo=300
    # cash_profit = 384.9247 - 300 = 84.9247
    assert isclose(cash_profit_eur(384.9247, 300.0), 84.9247, abs_tol=_TOL)


def test_snapshot_high_value() -> None:
    # cash_inflow=845.4788 (CHG-025), costo=600
    # cash_profit = 845.4788 - 600 = 245.4788
    assert isclose(cash_profit_eur(845.4788, 600.0), 245.4788, abs_tol=_TOL)


def test_zero_costo_fornitore_allowed() -> None:
    """Campione gratuito dal fornitore -> cash_profit == cash_inflow."""
    assert isclose(cash_profit_eur(200.0, 0.0), 200.0, abs_tol=_TOL)


def test_negative_cash_profit_allowed() -> None:
    """ASIN sotto costo (loss-leader): cash_profit<0 e' un fatto economico.

    cash_inflow=180.5922 (CHG-025 zero referral case), costo=200
    -> cash_profit = -19.4078. Nessun ValueError: il filtro e' R-08 a valle.
    """
    assert isclose(cash_profit_eur(180.5922, 200.0), -19.4078, abs_tol=_TOL)


def test_decreases_monotonically_with_costo() -> None:
    """A parita' di cash_inflow, +costo -> -cash_profit."""
    costi = [0.0, 50.0, 100.0, 200.0, 400.0]
    profits = [cash_profit_eur(500.0, c) for c in costi]
    for prev, curr in pairwise(profits):
        assert curr < prev


def test_raises_on_negative_costo() -> None:
    """R-01: spesa negativa fisicamente impossibile -> ValueError."""
    with pytest.raises(ValueError, match="costo_fornitore_eur"):
        cash_profit_eur(200.0, -1.0)
