"""Test unit per `talos.formulas.fee_fba` (CHG-2026-04-30-022, ADR-0018).

Snapshot tolerance-based (1e-3 EUR) — fissano il **comportamento osservabile**
della formula L11b verbatim del Leader, non i bit floating-point.
"""

from __future__ import annotations

from itertools import pairwise
from math import isclose

import pytest

from talos.formulas import fee_fba_manual

pytestmark = pytest.mark.unit

# Snapshot pre-calcolati (`uv run python -c '...'`):
#   buy_box=122  -> scorporato=100.00 (boundary)  -> 14.0342
#   buy_box=200  -> scorporato=163.93              -> 19.4078
#   buy_box=500  -> scorporato=409.84              -> 40.0753
#   buy_box=1000 -> scorporato=819.67              -> 74.5212

_TOL = 1e-3  # EUR


def test_snapshot_value_at_200_eur() -> None:
    assert isclose(fee_fba_manual(200.0), 19.4078, abs_tol=_TOL)


def test_snapshot_value_at_500_eur() -> None:
    assert isclose(fee_fba_manual(500.0), 40.0753, abs_tol=_TOL)


def test_snapshot_value_at_1000_eur() -> None:
    assert isclose(fee_fba_manual(1000.0), 74.5212, abs_tol=_TOL)


def test_boundary_scorporato_exactly_100() -> None:
    """`buy_box=122.0` produce `scorporato=100.0`, soglia inclusiva."""
    assert isclose(fee_fba_manual(122.0), 14.0342, abs_tol=_TOL)


def test_monotonicity_buy_box_increasing() -> None:
    """Maggiore BuyBox ⇒ maggiore Fee_FBA (la formula è lineare crescente)."""
    values = [122.0, 200.0, 350.0, 500.0, 1000.0]
    fees = [fee_fba_manual(v) for v in values]
    for prev, curr in pairwise(fees):
        assert curr > prev


def test_raises_when_scorporato_below_100() -> None:
    """R-01 NO SILENT DROPS: `buy_box=121.99` ⇒ scorporato=99.99 ⇒ ValueError."""
    with pytest.raises(ValueError, match="sotto soglia") as exc_info:
        fee_fba_manual(121.99)
    assert "scorporato" in str(exc_info.value)


def test_raises_when_buy_box_zero() -> None:
    with pytest.raises(ValueError, match="sotto soglia"):
        fee_fba_manual(0.0)


def test_raises_when_buy_box_negative() -> None:
    """Edge case esplicito: anche valori negativi falliscono prima del calcolo."""
    with pytest.raises(ValueError, match="negativo"):
        fee_fba_manual(-1.0)
