"""Unit test per `talos.formulas.velocity` (CHG-2026-04-30-038, ADR-0018).

F4.A (Q_m), F4 (qty_target), F5 (qty_final), velocity_monthly verbatim
PROJECT-RAW.md sez. 6.2 (decisione Leader, hardcoded).
"""

from __future__ import annotations

import pytest

from talos.formulas import (
    DEFAULT_LOT_SIZE,
    DEFAULT_VELOCITY_TARGET_DAYS,
    q_m,
    qty_final,
    qty_target,
    velocity_monthly,
)

pytestmark = pytest.mark.unit


# Defaults


def test_default_velocity_target_days_is_15() -> None:
    """L05 Round 5: default 15 giorni (slider 7..30)."""
    assert DEFAULT_VELOCITY_TARGET_DAYS == 15


def test_default_lot_size_is_5() -> None:
    """Samsung MVP: lotti fornitore = 5 (PROJECT-RAW.md riga 313)."""
    assert DEFAULT_LOT_SIZE == 5


# F4.A — q_m


def test_q_m_no_competitors() -> None:
    """S_comp=0 -> Q_m = V_tot (utente solo)."""
    assert q_m(100.0, 0) == pytest.approx(100.0)


def test_q_m_one_competitor() -> None:
    """S_comp=1 -> Q_m = V_tot / 2 (utente + 1 = 2)."""
    assert q_m(100.0, 1) == pytest.approx(50.0)


def test_q_m_many_competitors() -> None:
    """S_comp=4 -> Q_m = V_tot / 5."""
    assert q_m(100.0, 4) == pytest.approx(20.0)


def test_q_m_zero_v_tot() -> None:
    """V_tot=0 -> Q_m=0 (no vendite)."""
    assert q_m(0.0, 5) == pytest.approx(0.0)


def test_q_m_negative_v_tot_raises() -> None:
    """Vendite negative -> ValueError (R-01)."""
    with pytest.raises(ValueError, match="v_tot"):
        q_m(-10.0, 0)


def test_q_m_negative_s_comp_raises() -> None:
    """Competitor negativi -> ValueError (R-01)."""
    with pytest.raises(ValueError, match="s_comp"):
        q_m(100.0, -1)


# F4 — qty_target


def test_qty_target_default_15_days() -> None:
    """Default 15 giorni: Qty_Target = Q_m * 15/30 = Q_m / 2."""
    assert qty_target(20.0) == pytest.approx(10.0)


def test_qty_target_30_days() -> None:
    """30 giorni: Qty_Target = Q_m (1 mese intero)."""
    assert qty_target(20.0, velocity_target_days=30) == pytest.approx(20.0)


def test_qty_target_7_days_min_slider() -> None:
    """7 giorni (minimo slider L05): Qty_Target = Q_m * 7/30."""
    assert qty_target(30.0, velocity_target_days=7) == pytest.approx(7.0)


def test_qty_target_zero_q_m() -> None:
    """Q_m=0 -> qty_target=0."""
    assert qty_target(0.0) == pytest.approx(0.0)


def test_qty_target_invalid_q_m_raises() -> None:
    """Q_m negativo -> ValueError."""
    with pytest.raises(ValueError, match="q_m_value"):
        qty_target(-1.0)


def test_qty_target_invalid_velocity_target_raises() -> None:
    """velocity_target_days <= 0 -> ValueError."""
    with pytest.raises(ValueError, match="velocity_target_days"):
        qty_target(10.0, velocity_target_days=0)
    with pytest.raises(ValueError, match="velocity_target_days"):
        qty_target(10.0, velocity_target_days=-5)


# F5 — qty_final


def test_qty_final_exact_multiple() -> None:
    """qty_target=10 -> 2 lotti -> 10."""
    assert qty_final(10.0) == 10


def test_qty_final_floor_to_lot() -> None:
    """qty_target=7 -> 1 lotto (Floor) -> 5."""
    assert qty_final(7.0) == 5


def test_qty_final_below_one_lot() -> None:
    """qty_target=4.9 -> 0 lotti -> 0 (cashflow protetto)."""
    assert qty_final(4.9) == 0


def test_qty_final_zero() -> None:
    """qty_target=0 -> 0."""
    assert qty_final(0.0) == 0


def test_qty_final_returns_int() -> None:
    """Output sempre int (orderable)."""
    result = qty_final(10.0)
    assert isinstance(result, int)


def test_qty_final_custom_lot_size() -> None:
    """Override lot_size: 13 con lot=4 -> 12."""
    assert qty_final(13.0, lot_size=4) == 12


def test_qty_final_invalid_lot_size_raises() -> None:
    """lot_size <= 0 -> ValueError."""
    with pytest.raises(ValueError, match="lot_size"):
        qty_final(10.0, lot_size=0)
    with pytest.raises(ValueError, match="lot_size"):
        qty_final(10.0, lot_size=-1)


def test_qty_final_invalid_qty_raises() -> None:
    """qty_target negativo -> ValueError."""
    with pytest.raises(ValueError, match="qty_target_value"):
        qty_final(-1.0)


# velocity_monthly


def test_velocity_monthly_default_15_doubles_qm() -> None:
    """target=15: ruota Q_m volte in 15gg = 2*Q_m volte in 30gg."""
    assert velocity_monthly(10.0, 15) == pytest.approx(20.0)


def test_velocity_monthly_30_equals_qm() -> None:
    """target=30: ruota Q_m volte in 30gg (1:1 con Q_m)."""
    assert velocity_monthly(10.0, 30) == pytest.approx(10.0)


def test_velocity_monthly_7_days() -> None:
    """target=7: ruota Q_m volte ogni 7gg = Q_m * 30/7 ≈ 4.29*Q_m volte in 30gg."""
    assert velocity_monthly(10.0, 7) == pytest.approx(10.0 * 30 / 7)


def test_velocity_monthly_zero_q_m() -> None:
    """Q_m=0 -> velocity=0 (ASIN morto)."""
    assert velocity_monthly(0.0, 15) == pytest.approx(0.0)


def test_velocity_monthly_invalid_raises() -> None:
    """Validazioni R-01."""
    with pytest.raises(ValueError, match="q_m_value"):
        velocity_monthly(-1.0, 15)
    with pytest.raises(ValueError, match="velocity_target_days"):
        velocity_monthly(10.0, 0)


# Composizione (catena F4.A -> F4 -> F5 + velocity_monthly)


def test_chain_q_m_to_qty_final() -> None:
    """Esempio realistico: V_tot=200, S_comp=3, target=15, lot=5.

    Q_m = 200/4 = 50
    qty_target = 50 * 15/30 = 25
    qty_final = (25 // 5) * 5 = 25
    """
    qm = q_m(200.0, 3)
    qt = qty_target(qm)
    qf = qty_final(qt)
    assert qm == pytest.approx(50.0)
    assert qt == pytest.approx(25.0)
    assert qf == 25


def test_chain_with_floor_truncation() -> None:
    """Caso con Floor effettivo: V_tot=100, S_comp=3, target=15.

    Q_m = 100/4 = 25
    qty_target = 25 * 15/30 = 12.5
    qty_final = (12.5 // 5) * 5 = 2 * 5 = 10  (Floor protegge cashflow)
    """
    qm = q_m(100.0, 3)
    qt = qty_target(qm)
    qf = qty_final(qt)
    assert qm == pytest.approx(25.0)
    assert qt == pytest.approx(12.5)
    assert qf == 10
