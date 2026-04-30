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
    """Listino VGP DESC, budget capiente: vengono allocati in ordine di score."""
    vgp_df = _df(
        [
            ("A_TOP", 100.0, 5, 0.9),  # cost_total = 500
            ("B_MID", 50.0, 4, 0.6),  # cost_total = 200
            ("C_LOW", 10.0, 5, 0.3),  # cost_total = 50
        ],
    )
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=[])
    assert cart.asin_list() == ["A_TOP", "B_MID", "C_LOW"]
    assert cart.total_cost == pytest.approx(750.0)


def test_skip_zero_vgp_score() -> None:
    """ASIN con vgp_score=0 (gia' R-05/R-08 esclusi) saltati."""
    vgp_df = _df(
        [
            ("A", 100.0, 1, 0.9),
            ("B_DEAD", 50.0, 1, 0.0),  # killed
            ("C", 30.0, 1, 0.5),
        ],
    )
    cart = allocate_tetris(vgp_df, budget=200.0, locked_in=[])
    assert cart.asin_list() == ["A", "C"]


def test_skip_zero_qty_final_in_pass_2() -> None:
    """ASIN con qty_final=0 (F5 sotto soglia lotto) saltati nel Pass 2.

    Caso reale: q_m piccolo + velocity_target_days basso -> qty_target < lot_size.
    F5 Floor azzera la quantita'; allocare 0 pezzi sarebbe no-op.
    """
    vgp_df = _df(
        [
            ("A_OK", 100.0, 5, 0.9),
            ("B_NO_QTY", 50.0, 0, 0.6),  # qty_final=0 -> skip
            ("C_OK", 30.0, 5, 0.4),
        ],
    )
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=[])
    assert cart.asin_list() == ["A_OK", "C_OK"]
    assert "B_NO_QTY" not in cart.asin_list()


def test_continue_on_too_expensive_not_break() -> None:
    """R-06 letterale: cost > remaining -> continue (non break)."""
    vgp_df = _df(
        [
            ("A_TOP", 200.0, 1, 0.9),  # cost_total=200, entra
            ("B_BIG", 1000.0, 1, 0.8),  # cost_total=1000 > remaining=300, SKIP
            ("C_FITS", 100.0, 1, 0.7),  # cost_total=100, entra
        ],
    )
    cart = allocate_tetris(vgp_df, budget=500.0, locked_in=[])
    assert cart.asin_list() == ["A_TOP", "C_FITS"]
    assert cart.total_cost == pytest.approx(300.0)


def test_break_on_saturation() -> None:
    """R-06: break quando saturation >= 0.999."""
    vgp_df = _df(
        [
            ("A", 999.0, 1, 0.9),  # cost_total=999, saturation=0.999 -> break
            ("B", 1.0, 1, 0.8),  # mai esaminato (break su A)
        ],
    )
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=[])
    assert cart.asin_list() == ["A"]
    assert cart.saturation >= SATURATION_THRESHOLD


def test_partial_saturation_when_listino_not_saturable() -> None:
    """Listino totale < budget: saturation < 0.999, no break, tutti allocati."""
    vgp_df = _df([("A", 100.0, 1, 0.9), ("B", 50.0, 1, 0.5)])
    cart = allocate_tetris(vgp_df, budget=1000.0, locked_in=[])
    assert cart.saturation < SATURATION_THRESHOLD
    assert len(cart.items) == 2


# R-04 locked-in priorita' infinita


def test_r04_locked_in_added_first() -> None:
    """Locked-in entra prima del Pass 2, anche se non top VGP."""
    vgp_df = _df(
        [
            ("A_TOP", 100.0, 1, 0.9),
            ("B_LOCKED", 50.0, 1, 0.3),  # basso VGP ma locked
            ("C_MID", 30.0, 1, 0.6),
        ],
    )
    cart = allocate_tetris(vgp_df, budget=200.0, locked_in=["B_LOCKED"])
    # Locked entra per primo
    assert cart.items[0].asin == "B_LOCKED"
    assert cart.items[0].locked is True
    # Poi VGP DESC tra i non-locked: A_TOP, C_MID
    assert cart.asin_list() == ["B_LOCKED", "A_TOP", "C_MID"]


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
    """Override colonne via kwargs funziona end-to-end."""
    df = pd.DataFrame(
        {
            "id": ["A"],
            "price": [50.0],
            "qty": [2],
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
    assert cart.items[0].cost_total == pytest.approx(100.0)


def test_empty_df_returns_empty_cart() -> None:
    """DataFrame vuoto -> Cart vuoto, saturation=0."""
    df = pd.DataFrame(columns=["asin", "cost_eur", "qty_final", "vgp_score"])
    cart = allocate_tetris(df, budget=1000.0, locked_in=[])
    assert cart.asin_list() == []
    assert cart.saturation == pytest.approx(0.0)


def test_index_does_not_affect_pass_2_order() -> None:
    """Il Pass 2 usa l'ordine di iterazione del DataFrame (caller responsabile del sort).

    Se il caller non ordina per vgp_score DESC, il pass 2 NON riordina:
    output riflette l'ordine del df.
    """
    # Listino non ordinato per VGP - allocator NON riordina (caller responsibility).
    df = _df([("LOW", 100.0, 1, 0.3), ("HIGH", 100.0, 1, 0.9)])
    cart = allocate_tetris(df, budget=1000.0, locked_in=[])
    # LOW entra prima di HIGH perche' iteriamo in ordine df
    assert cart.asin_list() == ["LOW", "HIGH"]
