"""Unit test `talos.tetris.allocator` — DP knapsack + cart exhaustive (CHG-022).

R-06 saturazione 99.9% via DP bounded knapsack (max sum cost*qty, tie-break VGP).
R-04 locked-in priorità ∞ con qty_final velocity-based.
Cart exhaustive: contiene TUTTI gli ASIN del listino con `reason` flag.
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.tetris import (
    Cart,
    CartItem,
    InsufficientBudgetError,
    allocate_tetris,
)
from talos.tetris.allocator import (
    REASON_ALLOCATED,
    REASON_BUDGET_EXHAUSTED,
    REASON_KILL_SWITCH,
    REASON_LOCKED_IN,
    REASON_MIN_LOT_OVER_BUDGET,
    REASON_VETO_ROI,
    REASON_ZERO_QTY_TARGET,
)

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, int, float]]) -> pd.DataFrame:
    """rows = [(asin, cost_eur, qty_final, vgp_score), ...]."""
    return pd.DataFrame(rows, columns=["asin", "cost_eur", "qty_final", "vgp_score"])


def _allocated(cart: Cart) -> list[str]:
    return [item.asin for item in cart.allocated_items()]


# Cart dataclass


def test_cart_remaining_starts_at_budget() -> None:
    cart = Cart(budget=1000.0)
    assert cart.remaining == pytest.approx(1000.0)
    assert cart.saturation == pytest.approx(0.0)
    assert cart.asin_list() == []


def test_cart_add_updates_total_cost_and_remaining() -> None:
    cart = Cart(budget=1000.0)
    cart.add(CartItem(asin="A1", cost_total=300.0, qty=3, vgp_score=0.8))
    assert cart.total_cost == pytest.approx(300.0)
    assert cart.remaining == pytest.approx(700.0)
    assert cart.saturation == pytest.approx(0.3)


# allocate_tetris DP knapsack


def test_dp_satures_budget_with_optimal_combination() -> None:
    """CHG-2026-05-02-022: DP trova combinazione ottimale per saturare budget.

    Caso reale Leader: 3 ASIN cost diversi, budget non multiplo di nessun cost.
    DP deve trovare miglior mix multipli di 5 vs greedy che fermava al top-VGP.
    """
    vgp_df = _df(
        [
            ("S24", 380.0, 5, 0.9),
            ("S23", 330.0, 5, 0.7),
            ("A54", 220.0, 5, 0.5),
        ],
    )
    cart = allocate_tetris(vgp_df, budget=10_000.0, locked_in=[])
    # DP saturazione massima: la migliore combinazione vicina a 10000.
    # Es. S23=20 (6600) + A54=15 (3300) = 9900 → sat 99%.
    # Verifica: saturation >= 0.95 (DP migliora il greedy 95%).
    assert cart.saturation >= 0.95
    # Cart exhaustive: 3 ASIN tutti presenti.
    assert len(cart.items) == 3


def test_cart_exhaustive_contains_all_asins() -> None:
    """CHG-022: cart contiene TUTTI gli ASIN del listino, anche qty=0."""
    vgp_df = _df(
        [
            ("A_OK", 100.0, 5, 0.9),
            ("B_VETO", 50.0, 5, 0.0),  # vgp=0 → reason VETO_ROI
            ("C_NO_QTY", 30.0, 0, 0.6),  # qty_target=0 → reason ZERO_QTY_TARGET
        ],
    )
    cart = allocate_tetris(vgp_df, budget=5000.0, locked_in=[])
    assert len(cart.items) == 3
    asins = {item.asin for item in cart.items}
    assert asins == {"A_OK", "B_VETO", "C_NO_QTY"}


def test_reason_flags_classified_correctly() -> None:
    """CHG-022: ogni qty=0 ha reason esplicito (no inference cliente)."""
    df = pd.DataFrame(
        [
            ("ALLOC", 100.0, 5, 0.9, False),
            ("VETO", 50.0, 5, 0.0, False),  # vgp=0 → VETO_ROI (kill_mask=False)
            ("KILL", 30.0, 5, 0.0, True),  # kill_mask=True → KILL_SWITCH
            ("NO_QTY", 30.0, 0, 0.6, False),  # qty_target=0 → ZERO_QTY_TARGET
        ],
        columns=["asin", "cost_eur", "qty_final", "vgp_score", "kill_mask"],
    )
    cart = allocate_tetris(df, budget=5000.0, locked_in=[])
    by_asin = {item.asin: item for item in cart.items}
    assert by_asin["ALLOC"].reason == REASON_ALLOCATED
    assert by_asin["ALLOC"].qty > 0
    # KILL ha priorita' su VETO se entrambi: kill_mask True > vgp_score 0.
    assert by_asin["KILL"].reason == REASON_KILL_SWITCH
    assert by_asin["VETO"].reason == REASON_VETO_ROI
    assert by_asin["NO_QTY"].reason == REASON_ZERO_QTY_TARGET
    for asin in ("VETO", "KILL", "NO_QTY"):
        assert by_asin[asin].qty == 0


def test_min_lot_over_budget_flag() -> None:
    """1 lotto > budget remaining → reason MIN_LOT_OVER_BUDGET."""
    vgp_df = _df(
        [
            ("BIG_LOT", 200.0, 5, 0.9),  # 1 lotto = 1000 > budget=500
            ("FITS", 50.0, 5, 0.7),  # 1 lotto = 250 ≤ 500
        ],
    )
    cart = allocate_tetris(vgp_df, budget=500.0, locked_in=[])
    by_asin = {item.asin: item for item in cart.items}
    assert by_asin["BIG_LOT"].reason == REASON_MIN_LOT_OVER_BUDGET
    assert by_asin["BIG_LOT"].qty == 0
    assert by_asin["FITS"].qty > 0
    assert by_asin["FITS"].reason == REASON_ALLOCATED


def test_budget_exhausted_flag() -> None:
    """ASIN eligible ma DP non l'ha scelto → reason BUDGET_EXHAUSTED."""
    # Setup: budget piccolo, 2 ASIN entrambi eligibili ma solo 1 entra.
    vgp_df = _df(
        [
            ("WIN", 100.0, 5, 0.9),  # cost=500, vgp=0.9
            ("LOSE", 100.0, 5, 0.5),  # cost=500, ma DP sceglie WIN per VGP tie-break
        ],
    )
    cart = allocate_tetris(vgp_df, budget=500.0, locked_in=[])
    by_asin = {item.asin: item for item in cart.items}
    # WIN ha VGP più alto: tie-break preferisce WIN nella DP.
    assert by_asin["WIN"].qty == 5
    assert by_asin["LOSE"].qty == 0
    assert by_asin["LOSE"].reason == REASON_BUDGET_EXHAUSTED


# R-04 locked-in priorita' infinita


def test_r04_locked_in_added_first() -> None:
    """Locked-in entra prima del Pass 2 con qty_final velocity-based."""
    vgp_df = _df(
        [
            ("A_TOP", 100.0, 5, 0.9),
            ("B_LOCKED", 50.0, 5, 0.3),
            ("C_MID", 30.0, 5, 0.6),
        ],
    )
    cart = allocate_tetris(vgp_df, budget=5000.0, locked_in=["B_LOCKED"])
    assert cart.items[0].asin == "B_LOCKED"
    assert cart.items[0].locked is True
    assert cart.items[0].qty == 5
    assert cart.items[0].reason == REASON_LOCKED_IN


def test_r04_locked_in_with_zero_vgp_score_still_allocated() -> None:
    """Locked-in entra anche con vgp_score=0 (priorità ∞ ignora R-05/R-08)."""
    vgp_df = _df([("LOCKED_KILL", 100.0, 5, 0.0), ("A", 50.0, 5, 0.9)])
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=["LOCKED_KILL"])
    by_asin = {item.asin: item for item in cart.items}
    assert by_asin["LOCKED_KILL"].locked is True
    assert by_asin["LOCKED_KILL"].qty == 5


def test_r04_locked_in_skipped_in_pass_2() -> None:
    """Locked-in non viene riallocato nel Pass 2 (set semantics)."""
    vgp_df = _df([("A", 100.0, 5, 0.9), ("B_LOCKED", 50.0, 5, 0.5)])
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=["B_LOCKED"])
    locked_asins = [item.asin for item in cart.items if item.locked]
    assert locked_asins.count("B_LOCKED") == 1


def test_r04_insufficient_budget_for_locked_in_raises() -> None:
    """Locked-in con cost > budget residuo → InsufficientBudgetError."""
    vgp_df = _df([("BIG_LOCKED", 2000.0, 5, 0.5)])
    with pytest.raises(InsufficientBudgetError, match="BIG_LOCKED"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=["BIG_LOCKED"])


def test_r04_two_locked_in_second_too_expensive_raises() -> None:
    """Primo locked-in entra, secondo non sta → raise sul secondo."""
    vgp_df = _df([("L1", 600.0, 1, 0.5), ("L2", 600.0, 1, 0.5)])
    with pytest.raises(InsufficientBudgetError, match="L2"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=["L1", "L2"])


def test_r04_locked_in_not_in_df_raises() -> None:
    """Locked-in non presente nel listino → ValueError esplicito."""
    vgp_df = _df([("A", 100.0, 1, 0.9)])
    with pytest.raises(ValueError, match="MISSING"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=["MISSING"])


# Validazioni input (R-01)


def test_invalid_budget_raises() -> None:
    vgp_df = _df([("A", 100.0, 5, 0.9)])
    with pytest.raises(ValueError, match="budget"):
        allocate_tetris(vgp_df, budget=0.0, locked_in=[])
    with pytest.raises(ValueError, match="budget"):
        allocate_tetris(vgp_df, budget=-100.0, locked_in=[])


def test_missing_columns_raises() -> None:
    df = pd.DataFrame({"asin": ["A"], "cost_eur": [10.0]})
    with pytest.raises(ValueError, match="colonne richieste mancanti"):
        allocate_tetris(df, budget=100.0, locked_in=[])


def test_empty_df_returns_empty_cart() -> None:
    df = pd.DataFrame(columns=["asin", "cost_eur", "qty_final", "vgp_score"])
    cart = allocate_tetris(df, budget=1000.0, locked_in=[])
    assert cart.items == []
    assert cart.saturation == pytest.approx(0.0)


def test_lot_size_invalid_raises() -> None:
    vgp_df = _df([("A", 100.0, 5, 0.9)])
    with pytest.raises(ValueError, match="lot_size"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=[], lot_size=0)


def test_panchina_view_filters_budget_exhausted() -> None:
    """`cart.panchina_items()` filtra solo BUDGET_EXHAUSTED + MIN_LOT_OVER_BUDGET."""
    vgp_df = _df(
        [
            ("WIN", 100.0, 5, 0.9),
            ("MISS", 100.0, 5, 0.5),  # non scelto da DP → BUDGET_EXHAUSTED
            ("VETO", 50.0, 5, 0.0),  # vgp=0 → VETO_ROI (NON in panchina)
        ],
    )
    cart = allocate_tetris(vgp_df, budget=500.0, locked_in=[])
    panchina_asins = {item.asin for item in cart.panchina_items()}
    assert "MISS" in panchina_asins
    assert "VETO" not in panchina_asins  # vetoed != panchina
    assert "WIN" not in panchina_asins  # allocated
