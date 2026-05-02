"""Test unit `_build_enriched_cart_view` + `_classify_velocity_badge` (CHG-027)."""

from __future__ import annotations

import pandas as pd
import pytest

from talos.tetris.allocator import Cart, CartItem
from talos.ui.dashboard import (
    _CART_COLUMN_ORDER,
    _CART_SHELL_SENTINEL,
    _build_enriched_cart_view,
    _classify_velocity_badge,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# `_classify_velocity_badge`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("velocity", "expected"),
    [
        (100.0, "Veloce"),
        (45.0, "Veloce"),
        (30.0, "Veloce"),  # boundary inclusivo
        (29.99, "Buona"),
        (15.0, "Buona"),
        (10.0, "Buona"),  # boundary inclusivo
        (9.99, "Lento"),
        (1.0, "Lento"),
        (0.0, "Lento"),
    ],
)
def test_classify_velocity_badge_thresholds(velocity: float, expected: str) -> None:
    """Soglie classification badge (placeholder MVP, errata ADR-0018 in FASE 2)."""
    assert _classify_velocity_badge(velocity) == expected


# ---------------------------------------------------------------------------
# `_build_enriched_cart_view`
# ---------------------------------------------------------------------------


def _build_session_result_for_cart(
    cart_items: list[tuple[str, int, float, float, str]],
    enriched_rows: list[dict[str, object]],
    *,
    budget: float = 5000.0,
) -> object:
    """Construye SessionResult-like minimo: cart + enriched_df."""
    items = [
        CartItem(asin=asin, qty=qty, cost_total=cost_total, vgp_score=vgp, reason=reason)
        for asin, qty, cost_total, vgp, reason in cart_items
    ]
    cart = Cart(items=items, budget=budget)
    enriched = pd.DataFrame(enriched_rows)

    class _Result:
        def __init__(self) -> None:
            self.cart = cart
            self.enriched_df = enriched
            self.panchina = pd.DataFrame()
            self.budget_t1 = 0.0

    return _Result()


def test_build_enriched_cart_view_empty() -> None:
    """Cart vuoto → list vuota (nessun JOIN da fare)."""
    result = _build_session_result_for_cart([], [{"asin": "B0AAA", "cost_eur": 100.0}])
    out = _build_enriched_cart_view(result)  # type: ignore[arg-type]
    assert out == []


def test_build_enriched_cart_view_basic_join() -> None:
    """JOIN base: cart x enriched, 1 ASIN allocato."""
    result = _build_session_result_for_cart(
        cart_items=[("B0AAA", 5, 500.0, 0.7, "ALLOCATED")],
        enriched_rows=[
            {
                "asin": "B0AAA",
                "cost_eur": 100.0,
                "cash_inflow_eur": 130.0,
                "cash_profit_eur": 30.0,
                "roi": 0.30,
                "velocity_monthly": 45.0,
                "qty_target": 7,
            },
        ],
    )
    out = _build_enriched_cart_view(result)  # type: ignore[arg-type]
    assert len(out) == 1
    row = out[0]
    assert row["asin"] == "B0AAA"
    assert row["cst_unit"] == 100.0
    assert row["prft_unit"] == 130.0
    assert row["roi"] == 0.30
    assert row["vel"] == "Veloce"  # 45 >= 30
    assert row["q_15gg"] == 7
    assert row["qta"] == 5
    assert row["spesa_total"] == pytest.approx(500.0)
    assert row["prft_total"] == pytest.approx(150.0)  # 30 unit x 5 qty


def test_build_enriched_cart_view_qty_zero_preserved() -> None:
    """ASIN con qty=0 (vetato) deve apparire nella vista (cart exhaustive CHG-022)."""
    result = _build_session_result_for_cart(
        cart_items=[
            ("B0AAA", 5, 500.0, 0.7, "ALLOCATED"),
            ("B0BBB", 0, 0.0, 0.0, "VETO_ROI"),
        ],
        enriched_rows=[
            {
                "asin": "B0AAA",
                "cost_eur": 100.0,
                "cash_inflow_eur": 130.0,
                "cash_profit_eur": 30.0,
                "roi": 0.30,
                "velocity_monthly": 45.0,
                "qty_target": 7,
            },
            {
                "asin": "B0BBB",
                "cost_eur": 200.0,
                "cash_inflow_eur": 210.0,
                "cash_profit_eur": 10.0,
                "roi": 0.05,  # sotto veto
                "velocity_monthly": 5.0,
                "qty_target": 3,
            },
        ],
    )
    out = _build_enriched_cart_view(result)  # type: ignore[arg-type]
    assert len(out) == 2
    veto_row = next(r for r in out if r["asin"] == "B0BBB")
    assert veto_row["qta"] == 0
    assert veto_row["azioni"] == "VETO_ROI"
    assert veto_row["spesa_total"] == 0.0
    assert veto_row["prft_total"] == 0.0
    assert veto_row["vel"] == "Lento"  # 5 < 10


def test_build_enriched_cart_view_shell_sentinels_present() -> None:
    """5 colonne shell devono essere sentinel `—` (CHG-028+ wireup)."""
    result = _build_session_result_for_cart(
        cart_items=[("B0AAA", 5, 500.0, 0.7, "ALLOCATED")],
        enriched_rows=[
            {
                "asin": "B0AAA",
                "cost_eur": 100.0,
                "cash_inflow_eur": 130.0,
                "cash_profit_eur": 30.0,
                "roi": 0.30,
                "velocity_monthly": 45.0,
                "qty_target": 7,
            },
        ],
    )
    out = _build_enriched_cart_view(result)  # type: ignore[arg-type]
    row = out[0]
    for shell_col in ("hw_id", "prodotto", "fornitore", "stock", "mrg", "a_m"):
        assert row[shell_col] == _CART_SHELL_SENTINEL, (
            f"colonna {shell_col} dovrebbe essere sentinel"
        )


def test_build_enriched_cart_view_locked_flag_propagated() -> None:
    """Flag `locked` (R-04) propagato dal cart_item alla vista."""
    items = [
        CartItem(
            asin="B0AAA",
            qty=5,
            cost_total=500.0,
            vgp_score=0.7,
            locked=True,
            reason="LOCKED_IN",
        ),
    ]
    cart = Cart(items=items, budget=5000.0)
    enriched = pd.DataFrame(
        [
            {
                "asin": "B0AAA",
                "cost_eur": 100.0,
                "cash_inflow_eur": 130.0,
                "cash_profit_eur": 30.0,
                "roi": 0.30,
                "velocity_monthly": 45.0,
                "qty_target": 7,
            },
        ],
    )

    class _Result:
        def __init__(self) -> None:
            self.cart = cart
            self.enriched_df = enriched
            self.panchina = pd.DataFrame()
            self.budget_t1 = 0.0

    out = _build_enriched_cart_view(_Result())  # type: ignore[arg-type]
    assert out[0]["locked"] is True


def test_cart_column_order_constant_completeness() -> None:
    """Sentinel: la column order constant deve includere tutte le 13 colonne ScalerBot.

    Nessun typo / dimenticanza nella tupla pub.
    """
    expected_cols = {
        "asin",
        "hw_id",
        "prodotto",
        "fornitore",
        "cst_unit",
        "prft_unit",
        "vgp",
        "mrg",
        "roi",
        "vel",
        "q_15gg",
        "stock",
        "qta",
        "prft_total",
        "spesa_total",
        "a_m",
        "azioni",
    }
    assert set(_CART_COLUMN_ORDER) == expected_cols
