"""Test unit per `talos.formulas.roi` (CHG-2026-04-30-026, ADR-0018).

ROI = cash_profit / costo_fornitore. Output frazione decimale
(0.08 == 8%). Composto con cash_profit_eur di CHG-026 per coerenza
con la catena fee_fba -> cash_inflow -> cash_profit -> roi.

Tolerance 1e-4 sui ROI (precisione frazionaria; tolerance 1e-3
sarebbe insufficiente per costi grandi).
"""

from __future__ import annotations

from math import isclose

import pytest

from talos.formulas import roi

pytestmark = pytest.mark.unit

_TOL = 1e-4  # frazione decimale


def test_snapshot_low_roi() -> None:
    # cash_profit=64.5922 (CHG-026), costo=100 -> 0.6459
    assert isclose(roi(64.5922, 100.0), 0.6459, abs_tol=_TOL)


def test_snapshot_mid_roi() -> None:
    # cash_profit=84.9247 (CHG-026), costo=300 -> 0.2831
    assert isclose(roi(84.9247, 300.0), 0.2831, abs_tol=_TOL)


def test_snapshot_high_roi() -> None:
    # cash_profit=245.4788 (CHG-026), costo=600 -> 0.4091
    assert isclose(roi(245.4788, 600.0), 0.4091, abs_tol=_TOL)


def test_zero_profit_yields_zero_roi() -> None:
    """ROI di un break-even (profit=0) e' esattamente 0, non NaN."""
    assert isclose(roi(0.0, 100.0), 0.0, abs_tol=_TOL)


def test_negative_roi_allowed() -> None:
    """Loss propaga: ROI<0 e' informazione utile per R-08, non un errore.

    cash_profit=-19.4078 (CHG-026 loss-leader case), costo=200 -> -0.0970.
    """
    assert isclose(roi(-19.4078, 200.0), -0.0970, abs_tol=_TOL)


def test_boundary_at_eight_percent_threshold() -> None:
    """Soglia Veto R-08 default = 8% = 0.08 (L10 chiusa Round 5).

    Ancorare il boundary qui rende immediato il test del veto futuro:
    profit=8 / costo=100 -> ROI esattamente alla soglia.
    """
    assert isclose(roi(8.0, 100.0), 0.08, abs_tol=_TOL)


def test_raises_on_zero_costo() -> None:
    """R-01: costo=0 -> divisione-per-zero proibita, ValueError esplicito."""
    with pytest.raises(ValueError, match="costo_fornitore_eur"):
        roi(10.0, 0.0)


def test_raises_on_negative_costo() -> None:
    """R-01: costo negativo fisicamente impossibile -> ValueError."""
    with pytest.raises(ValueError, match="costo_fornitore_eur"):
        roi(10.0, -1.0)
