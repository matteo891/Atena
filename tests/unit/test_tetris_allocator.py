"""Unit test per `talos.tetris.allocator` (CHG-2026-04-30-036, ADR-0018).

R-06 saturazione 99.9% (PROJECT-RAW.md riga 224) + R-04 locked-in
priorita' infinita (sez. 4.1.13). InsufficientBudgetError fail-fast
per locked-in con cost > budget residuo (R-01 NO SILENT DROPS).
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.tetris import (
    SATURATION_THRESHOLD,
    Cart,
    CartItem,
    InsufficientBudgetError,
    allocate_tetris,
)

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, int, float]]) -> pd.DataFrame:
    """Helper: rows = [(asin, cost_eur, qty_final, vgp_score), ...]."""
    return pd.DataFrame(rows, columns=["asin", "cost_eur", "qty_final", "vgp_score"])


# Cart dataclass


def test_cart_remaining_starts_at_budget() -> None:
    """Cart vuoto: remaining == budget, saturation == 0."""
    cart = Cart(budget=1000.0)
    assert cart.remaining == pytest.approx(1000.0)
    assert cart.saturation == pytest.approx(0.0)
    assert cart.asin_list() == []


def test_cart_add_updates_total_cost_and_remaining() -> None:
    """Add aggiorna total_cost; remaining e saturation derivati."""
    cart = Cart(budget=1000.0)
    cart.add(CartItem(asin="A1", cost_total=300.0, qty=3, vgp_score=0.8))
    assert cart.total_cost == pytest.approx(300.0)
    assert cart.remaining == pytest.approx(700.0)
    assert cart.saturation == pytest.approx(0.3)


def test_cart_saturation_clamped_to_one() -> None:
    """Anche se total_cost > budget (bug), saturation max 1.0."""
    cart = Cart(budget=100.0)
    cart.add(CartItem(asin="X", cost_total=200.0, qty=1, vgp_score=0.5))
    assert cart.saturation == pytest.approx(1.0)


# allocate_tetris snapshot


def test_basic_allocation_top_vgp_first() -> None:
    """CHG-2026-05-02-020 greedy: top VGP compra MAX multiplo lot=5, satura budget."""
    vgp_df = _df(
        [
            ("A_TOP", 100.0, 5, 0.9),
            ("B_MID", 50.0, 5, 0.6),
            ("C_LOW", 10.0, 5, 0.3),
        ],
    )
    # budget=1000 → A_TOP greedy: floor(1000/100/5)*5 = 10 → cost_total=1000 → break.
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=[])
    assert cart.asin_list() == ["A_TOP"]
    assert cart.items[0].qty == 10
    assert cart.total_cost == pytest.approx(1000.0)


def test_skip_zero_vgp_score() -> None:
    """ASIN con vgp_score=0 (gia' R-05/R-08 esclusi) saltati."""
    vgp_df = _df(
        [
            ("A", 100.0, 5, 0.9),
            ("B_DEAD", 50.0, 5, 0.0),  # killed
            ("C", 30.0, 5, 0.5),
        ],
    )
    # budget 5000: A greedy floor(5000/100/5)*5 = 50 → cost=5000 → break.
    cart = allocate_tetris(vgp_df, budget=5000.0, locked_in=[])
    assert "B_DEAD" not in cart.asin_list()


def test_skip_zero_qty_final_in_pass_2() -> None:
    """ASIN con qty_final=0 (F5 azzera per v_tot piccolo) skippati."""
    vgp_df = _df(
        [
            ("A_OK", 100.0, 5, 0.9),
            ("B_NO_QTY", 50.0, 0, 0.6),  # qty_target=0 -> skip
            ("C_OK", 30.0, 5, 0.4),
        ],
    )
    cart = allocate_tetris(vgp_df, budget=10_000.0, locked_in=[])
    assert "B_NO_QTY" not in cart.asin_list()


def test_skip_when_min_lot_over_budget() -> None:
    """CHG-020: greedy salta ASIN il cui costo 1-lotto > budget residuo."""
    vgp_df = _df(
        [
            ("A_TOP", 200.0, 5, 0.9),  # 1 lotto = 1000 > budget 500 → SKIP
            ("B_FITS", 50.0, 5, 0.7),  # 1 lotto = 250 ≤ 500 → entra
        ],
    )
    cart = allocate_tetris(vgp_df, budget=500.0, locked_in=[])
    assert cart.asin_list() == ["B_FITS"]
    # B_FITS: floor(500/50/5)*5 = 10 → cost=500 → break sat 100%.
    assert cart.items[0].qty == 10


def test_break_on_saturation() -> None:
    """R-06: break quando saturation >= 0.999."""
    vgp_df = _df(
        [
            ("A", 100.0, 5, 0.9),
            ("B", 1.0, 5, 0.8),
        ],
    )
    # budget=1000: A greedy floor(1000/100/5)*5 = 10, cost=1000 → break.
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=[])
    assert cart.asin_list() == ["A"]
    assert cart.saturation >= SATURATION_THRESHOLD


def test_partial_saturation_when_top_too_expensive_for_full() -> None:
    """Top VGP riempie max possibile, residuo viene allocato a item successivi."""
    vgp_df = _df(
        [
            ("A", 100.0, 5, 0.9),  # max_lot = floor(1000/100/5)*5 = 10, cost=1000 → break
            ("B", 1.0, 5, 0.5),
        ],
    )
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=[])
    # A satura; break → B mai allocato.
    assert cart.asin_list() == ["A"]


def test_residual_budget_spills_to_lower_vgp() -> None:
    """CHG-020: top VGP mangia parte del budget; residuo va al successivo."""
    vgp_df = _df(
        [
            ("A_TOP", 300.0, 5, 0.9),  # 1 lotto=1500, budget=2000, greedy=5 cost=1500
            ("B_FILL", 100.0, 5, 0.5),  # residuo=500, greedy=5 cost=500 → break
        ],
    )
    cart = allocate_tetris(vgp_df, budget=2000.0, locked_in=[])
    assert cart.asin_list() == ["A_TOP", "B_FILL"]
    assert cart.items[0].qty == 5
    assert cart.items[1].qty == 5
    assert cart.total_cost == pytest.approx(2000.0)


# R-04 locked-in priorita' infinita


def test_r04_locked_in_added_first() -> None:
    """Locked-in entra prima del Pass 2 con qty_final velocity-based."""
    vgp_df = _df(
        [
            ("A_TOP", 100.0, 5, 0.9),
            ("B_LOCKED", 50.0, 5, 0.3),  # basso VGP ma locked
            ("C_MID", 30.0, 5, 0.6),
        ],
    )
    # B_LOCKED: cost qty_final fisso = 50*5=250. budget 5000-250=4750.
    # Pass 2 greedy: A_TOP first (vgp 0.9): max_lot floor(4750/100/5)*5 = 45.
    # cost=4500, residuo 250. Saturation = 4750/5000 = 95% no break.
    # C_MID: max_lot floor(250/30/5)*5 = floor(1.66/5)*5 = 0 → skip (1 lotto=150 ≤ 250 OK
    #   wait: floor(250/30/5)*5 = floor(1.666)*5 = 1*5 = 5. cost=150. saturation=4900/5000=98%.
    cart = allocate_tetris(vgp_df, budget=5000.0, locked_in=["B_LOCKED"])
    assert cart.items[0].asin == "B_LOCKED"
    assert cart.items[0].locked is True
    assert cart.items[0].qty == 5  # qty_final velocity-based per locked
    assert "A_TOP" in cart.asin_list()


def test_r04_locked_in_with_zero_vgp_score_still_allocated() -> None:
    """Locked-in entra anche con vgp_score=0 (priorita' infinita ignora R-05/R-08)."""
    vgp_df = _df([("LOCKED_KILL", 100.0, 1, 0.0), ("A", 50.0, 1, 0.9)])
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=["LOCKED_KILL"])
    assert cart.items[0].asin == "LOCKED_KILL"
    assert cart.items[0].locked is True


def test_r04_locked_in_skipped_in_pass_2() -> None:
    """Locked-in non viene riallocato nel Pass 2 (set semantics)."""
    vgp_df = _df([("A", 100.0, 1, 0.9), ("B_LOCKED", 50.0, 1, 0.5)])
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=["B_LOCKED"])
    # B_LOCKED appare una sola volta
    assert cart.asin_list().count("B_LOCKED") == 1


def test_r04_insufficient_budget_for_locked_in_raises() -> None:
    """Locked-in con cost > budget residuo -> InsufficientBudgetError."""
    vgp_df = _df([("BIG_LOCKED", 2000.0, 1, 0.5)])
    with pytest.raises(InsufficientBudgetError, match="BIG_LOCKED"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=["BIG_LOCKED"])


def test_r04_two_locked_in_second_too_expensive_raises() -> None:
    """Primo locked-in entra, secondo non sta -> raise sul secondo."""
    vgp_df = _df([("L1", 600.0, 1, 0.5), ("L2", 600.0, 1, 0.5)])
    with pytest.raises(InsufficientBudgetError, match="L2"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=["L1", "L2"])


def test_r04_locked_in_not_in_df_raises() -> None:
    """Locked-in non presente nel listino -> ValueError esplicito."""
    vgp_df = _df([("A", 100.0, 1, 0.9)])
    with pytest.raises(ValueError, match="MISSING"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=["MISSING"])


# Validazioni input (R-01)


def test_invalid_budget_raises() -> None:
    """budget <= 0 -> ValueError."""
    vgp_df = _df([("A", 100.0, 1, 0.9)])
    with pytest.raises(ValueError, match="budget"):
        allocate_tetris(vgp_df, budget=0.0, locked_in=[])
    with pytest.raises(ValueError, match="budget"):
        allocate_tetris(vgp_df, budget=-100.0, locked_in=[])


def test_missing_columns_raises() -> None:
    """Colonne attese mancanti -> ValueError."""
    df = pd.DataFrame({"asin": ["A"], "cost_eur": [10.0]})  # mancano qty_final, vgp_score
    with pytest.raises(ValueError, match="colonne richieste mancanti"):
        allocate_tetris(df, budget=100.0, locked_in=[])


def test_custom_column_names() -> None:
    """Override colonne via kwargs funziona end-to-end (greedy max-fill)."""
    df = pd.DataFrame(
        {
            "id": ["A"],
            "price": [50.0],
            "qty": [5],
            "score": [0.9],
        },
    )
    cart = allocate_tetris(
        df,
        budget=1000.0,
        locked_in=[],
        asin_col="id",
        cost_col="price",
        qty_col="qty",
        score_col="score",
    )
    assert cart.asin_list() == ["A"]
    # greedy: floor(1000/50/5)*5 = 20 → cost 1000 → break.
    assert cart.items[0].qty == 20
    assert cart.items[0].cost_total == pytest.approx(1000.0)


def test_empty_df_returns_empty_cart() -> None:
    """DataFrame vuoto -> Cart vuoto, saturation=0."""
    df = pd.DataFrame(columns=["asin", "cost_eur", "qty_final", "vgp_score"])
    cart = allocate_tetris(df, budget=1000.0, locked_in=[])
    assert cart.asin_list() == []
    assert cart.saturation == pytest.approx(0.0)


def test_index_does_not_affect_pass_2_order() -> None:
    """Il Pass 2 usa l'ordine di iterazione del DataFrame (caller responsabile del sort).

    Se il caller non ordina per vgp_score DESC, il pass 2 NON riordina:
    output riflette l'ordine del df. Greedy max-fill è applicato in ordine.
    """
    df = _df([("LOW", 100.0, 5, 0.3), ("HIGH", 50.0, 5, 0.9)])
    cart = allocate_tetris(df, budget=1000.0, locked_in=[])
    # LOW entra prima (ordine df, non vgp). LOW greedy: floor(1000/100/5)*5=10 cost=1000 break.
    assert cart.asin_list() == ["LOW"]
