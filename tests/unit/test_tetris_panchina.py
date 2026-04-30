"""Unit test per `talos.tetris.panchina` (CHG-2026-04-30-037, ADR-0018).

R-09 verbatim PROJECT-RAW.md riga 227: ASIN idonei (vgp_score > 0) NON
allocati nel Cart, ordinati per VGP DESC.
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.tetris import Cart, CartItem, build_panchina

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, int, float]]) -> pd.DataFrame:
    """Helper: rows = [(asin, cost_eur, qty_final, vgp_score), ...]."""
    return pd.DataFrame(rows, columns=["asin", "cost_eur", "qty_final", "vgp_score"])


def _cart_with(asins: list[str]) -> Cart:
    """Cart popolato con item dummy (cost_total irrilevante per panchina)."""
    cart = Cart(budget=1000.0)
    for asin in asins:
        cart.add(CartItem(asin=asin, cost_total=100.0, qty=1, vgp_score=0.5))
    return cart


def test_panchina_excludes_in_cart_asins() -> None:
    """ASIN gia' nel cart non figurano in panchina."""
    df = _df(
        [
            ("A", 100.0, 1, 0.9),
            ("B", 100.0, 1, 0.7),
            ("C", 100.0, 1, 0.5),
        ],
    )
    cart = _cart_with(["A"])
    panchina = build_panchina(df, cart)
    assert list(panchina["asin"]) == ["B", "C"]


def test_panchina_excludes_zero_score() -> None:
    """ASIN con vgp_score=0 (R-05/R-08 esclusi) non figurano in panchina."""
    df = _df(
        [
            ("A_KILL", 100.0, 1, 0.0),
            ("B_VETO", 100.0, 1, 0.0),
            ("C_OK", 100.0, 1, 0.5),
        ],
    )
    cart = _cart_with([])
    panchina = build_panchina(df, cart)
    assert list(panchina["asin"]) == ["C_OK"]


def test_panchina_ordered_by_score_desc() -> None:
    """Output ordinato per vgp_score decrescente (R-09 verbatim)."""
    df = _df(
        [
            ("LOW", 100.0, 1, 0.3),
            ("HIGH", 100.0, 1, 0.9),
            ("MID", 100.0, 1, 0.6),
        ],
    )
    cart = _cart_with([])
    panchina = build_panchina(df, cart)
    assert list(panchina["asin"]) == ["HIGH", "MID", "LOW"]
    # Score decrescente
    scores = list(panchina["vgp_score"])
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_panchina_empty_when_all_in_cart() -> None:
    """Tutti gli idonei in cart -> panchina vuota."""
    df = _df([("A", 100.0, 1, 0.9), ("B", 100.0, 1, 0.5)])
    cart = _cart_with(["A", "B"])
    panchina = build_panchina(df, cart)
    assert len(panchina) == 0


def test_panchina_empty_when_all_vetoed_or_killed() -> None:
    """Tutti vgp_score=0 -> panchina vuota."""
    df = _df([("A", 100.0, 1, 0.0), ("B", 100.0, 1, 0.0)])
    cart = _cart_with([])
    panchina = build_panchina(df, cart)
    assert len(panchina) == 0


def test_panchina_empty_when_df_empty() -> None:
    """DataFrame vuoto -> panchina vuota."""
    df = pd.DataFrame(columns=["asin", "cost_eur", "qty_final", "vgp_score"])
    cart = _cart_with([])
    panchina = build_panchina(df, cart)
    assert len(panchina) == 0


def test_panchina_preserves_other_columns() -> None:
    """Le colonne extra di vgp_df sono preservate in panchina (utili per UI)."""
    df = _df([("A", 50.0, 2, 0.7), ("B", 30.0, 3, 0.5)])
    cart = _cart_with([])
    panchina = build_panchina(df, cart)
    assert "cost_eur" in panchina.columns
    assert "qty_final" in panchina.columns
    assert panchina.iloc[0]["cost_eur"] == 50.0  # A e' top per score


def test_panchina_realistic_cart_partial_overlap() -> None:
    """Scenario realistico: cart contiene 2 top, 3 idonei restano in panchina."""
    df = _df(
        [
            ("TOP_1", 100.0, 1, 0.9),  # in cart
            ("TOP_2", 100.0, 1, 0.8),  # in cart
            ("MID_1", 100.0, 1, 0.6),
            ("MID_2", 100.0, 1, 0.5),
            ("LOW", 100.0, 1, 0.3),
            ("DEAD", 100.0, 1, 0.0),  # killed/vetato
        ],
    )
    cart = _cart_with(["TOP_1", "TOP_2"])
    panchina = build_panchina(df, cart)
    assert list(panchina["asin"]) == ["MID_1", "MID_2", "LOW"]


def test_missing_columns_raises() -> None:
    """Colonne attese mancanti -> ValueError."""
    df = pd.DataFrame({"asin": ["A"]})  # manca vgp_score
    cart = _cart_with([])
    with pytest.raises(ValueError, match="colonne richieste mancanti"):
        build_panchina(df, cart)


def test_custom_column_names() -> None:
    """Override colonne via kwargs."""
    df = pd.DataFrame({"id": ["A", "B"], "score": [0.9, 0.5]})
    cart = _cart_with([])
    panchina = build_panchina(df, cart, asin_col="id", score_col="score")
    assert list(panchina["id"]) == ["A", "B"]
