"""Test unit `_compute_cycle_kpis` (CHG-2026-05-02-025).

Helper puro (no Streamlit). Testa math compound + edge cases boundary.
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.tetris.allocator import Cart, CartItem
from talos.ui.dashboard import (
    DEFAULT_CYCLES_PER_YEAR_DIVISOR,
    _compute_cycle_kpis,
)

pytestmark = pytest.mark.unit


def _build_session_result(
    *,
    budget: float,
    items: list[tuple[str, int, float, float]],
    budget_t1: float,
) -> object:
    """Costruisce un `SessionResult`-like minimale per testing _compute_cycle_kpis.

    items: list of (asin, qty, cost_total, vgp_score).
    """
    cart_items = [
        CartItem(
            asin=asin,
            qty=qty,
            cost_total=cost_total,
            vgp_score=vgp,
            reason="ALLOCATED" if qty > 0 else "BUDGET_EXHAUSTED",
        )
        for asin, qty, cost_total, vgp in items
    ]
    cart = Cart(items=cart_items, budget=budget)

    class _Result:
        def __init__(self) -> None:
            self.cart = cart
            self.budget_t1 = budget_t1
            self.enriched_df = pd.DataFrame()
            self.panchina = pd.DataFrame()

    return _Result()


def test_compute_cycle_kpis_empty_cart() -> None:
    """Cart vuoto: zero ordini, projected = budget (no compound)."""
    result = _build_session_result(budget=10000.0, items=[], budget_t1=10000.0)
    kpis = _compute_cycle_kpis(result, velocity_target_days=15)  # type: ignore[arg-type]
    assert kpis["n_orders"] == 0
    assert kpis["cart_value_eur"] == 0
    assert kpis["cash_profit_eur"] == 0
    assert kpis["projected_annual_eur"] == 10000.0  # no compound when n_orders==0


def test_compute_cycle_kpis_single_allocated_item() -> None:
    """Singolo item allocated: cart_value/n_orders/profit_cost computed.

    F3 compounding: budget_t1 = budget + cash_profit. Esempio: cost_total
    1000 + cash_profit 200 → budget_t1 = 5200, profit/cost = 20%.
    """
    result = _build_session_result(
        budget=5000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=5200.0,  # F3: budget + cash_profit (200) = 5200
    )
    kpis = _compute_cycle_kpis(result, velocity_target_days=15)  # type: ignore[arg-type]
    assert kpis["n_orders"] == 1
    assert kpis["cart_value_eur"] == 1000.0
    # cash_profit = budget_t1 - budget = 5200 - 5000 = 200 (F3 verbatim)
    assert kpis["cash_profit_eur"] == pytest.approx(200.0)
    # profit_cost = 200 / 1000 = 0.20 (20% margine ciclo)
    assert kpis["profit_cost_pct"] == pytest.approx(0.20)


def test_compute_cycle_kpis_zero_qty_items_excluded() -> None:
    """Items con qty=0 (BUDGET_EXHAUSTED/VETO) esclusi da n_orders e cart_value."""
    result = _build_session_result(
        budget=5000.0,
        items=[
            ("B0AAA", 5, 500.0, 0.5),
            ("B0BBB", 0, 0.0, 0.3),  # vetato/budget exhausted
            ("B0CCC", 3, 300.0, 0.4),
        ],
        budget_t1=5500.0,
    )
    kpis = _compute_cycle_kpis(result, velocity_target_days=15)  # type: ignore[arg-type]
    assert kpis["n_orders"] == 2  # solo i due con qty>0
    assert kpis["cart_value_eur"] == 800.0  # 500 + 300


def test_compute_cycle_kpis_cycles_per_year_15_days() -> None:
    """Velocity 15gg → 365/15 = 24.333 cicli/anno."""
    result = _build_session_result(
        budget=5000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=5100.0,
    )
    kpis = _compute_cycle_kpis(result, velocity_target_days=15)  # type: ignore[arg-type]
    assert kpis["cycles_per_year"] == pytest.approx(DEFAULT_CYCLES_PER_YEAR_DIVISOR / 15)


def test_compute_cycle_kpis_cycles_per_year_7_days_max_velocity() -> None:
    """Velocity boundary lower (7gg) → 365/7 ≈ 52.14 cicli/anno."""
    result = _build_session_result(
        budget=5000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=5100.0,
    )
    kpis = _compute_cycle_kpis(result, velocity_target_days=7)  # type: ignore[arg-type]
    assert kpis["cycles_per_year"] == pytest.approx(365.0 / 7)


def test_compute_cycle_kpis_cycles_per_year_30_days_min_velocity() -> None:
    """Velocity boundary upper (30gg) → 365/30 ≈ 12.17 cicli/anno."""
    result = _build_session_result(
        budget=5000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=5100.0,
    )
    kpis = _compute_cycle_kpis(result, velocity_target_days=30)  # type: ignore[arg-type]
    assert kpis["cycles_per_year"] == pytest.approx(365.0 / 30)


def test_compute_cycle_kpis_zero_velocity_target_raises() -> None:
    """velocity_target_days=0 → ValueError R-01 (no division-by-zero silente)."""
    result = _build_session_result(
        budget=5000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=5100.0,
    )
    with pytest.raises(ValueError, match=">= 1"):
        _compute_cycle_kpis(result, velocity_target_days=0)  # type: ignore[arg-type]


def test_compute_cycle_kpis_compound_math_simple() -> None:
    """Verifica compound: budget * (1+r)^N con valori controllati.

    F3: budget_t1 = budget + cash_profit. profit_cost = cash_profit / cart_value.
    Esempio: budget 10k, cart 1k, cash_profit 100 → r=0.10, N=365/30≈12.17.
    r=10% rientra nel range [veto=8%, cap=15%] → projection_r=10% (no clamp).
    """
    result = _build_session_result(
        budget=10000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=10100.0,  # cash_profit = 100, su cart 1000 → r = 10%
    )
    kpis = _compute_cycle_kpis(result, velocity_target_days=30)  # type: ignore[arg-type]
    cycles = 365.0 / 30
    expected = 10000.0 * (1.1**cycles)
    assert kpis["projected_annual_eur"] == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# CHG-2026-05-02-041: r-cap conservativo proiezione compound
# ---------------------------------------------------------------------------


def test_compute_cycle_kpis_projection_r_cap_high_actual_r() -> None:
    """r effettivo 30% → projection_r capped a 15% (evita esplosione 11M€).

    Bug live Leader: cart con r alto (~30%) produceva proiezione €11M
    su budget €6k. CHG-041 cap a 15% per ciclo → ~91k su 24 cicli.
    """
    result = _build_session_result(
        budget=6000.0,
        items=[("B0AAA", 5, 1000.0, 0.5)],
        budget_t1=6300.0,  # cash_profit = 300, su cart 1000 → r effettivo = 30%
    )
    kpis = _compute_cycle_kpis(result, velocity_target_days=15)  # type: ignore[arg-type]
    # r effettivo del ciclo (per KPI tile dedicato): 30%.
    assert kpis["profit_cost_pct"] == pytest.approx(0.30)
    # r conservativo per proiezione: capped a 15%.
    assert kpis["projection_r_pct"] == pytest.approx(0.15)
    # Proiezione: 6000 * 1.15^24.33 ≈ 168k (NON 11M).
    cycles = 365.0 / 15
    expected = 6000.0 * (1.15**cycles)
    assert kpis["projected_annual_eur"] == pytest.approx(expected, rel=1e-6)
    assert kpis["projected_annual_eur"] < 500_000.0  # sanity: NON 11M


def test_compute_cycle_kpis_projection_r_floor_low_actual_r() -> None:
    """r effettivo 5% (sotto veto 8%) → projection_r floor a veto_threshold.

    Allineamento ScalerBot500K: usa la soglia veto come r conservativo,
    anche se il cart ha margine inferiore.
    """
    result = _build_session_result(
        budget=10000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=10050.0,  # cash_profit = 50, su cart 1000 → r effettivo = 5%
    )
    kpis = _compute_cycle_kpis(
        result,  # type: ignore[arg-type]
        velocity_target_days=30,
        veto_roi_threshold=0.08,
    )
    assert kpis["profit_cost_pct"] == pytest.approx(0.05)
    # Floor a veto_threshold: projection usa 8% non 5%.
    assert kpis["projection_r_pct"] == pytest.approx(0.08)


def test_compute_cycle_kpis_projection_r_passthrough_in_range() -> None:
    """r effettivo 12% (dentro [veto=8%, cap=15%]) → projection_r = r effettivo."""
    result = _build_session_result(
        budget=10000.0,
        items=[("B0AAA", 10, 1000.0, 0.5)],
        budget_t1=10120.0,  # cash_profit = 120, r effettivo = 12%
    )
    kpis = _compute_cycle_kpis(
        result,  # type: ignore[arg-type]
        velocity_target_days=30,
        veto_roi_threshold=0.08,
    )
    assert kpis["profit_cost_pct"] == pytest.approx(0.12)
    assert kpis["projection_r_pct"] == pytest.approx(0.12)
