"""Unit test per `compare_session_kpis` (CHG-2026-04-30-059).

Helper puro testabile senza Streamlit: confronto KPI originale vs replay.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import pytest

from talos.orchestrator import SessionResult
from talos.persistence import LoadedSession, SessionSummary
from talos.tetris import Cart
from talos.tetris.allocator import CartItem
from talos.ui import compare_session_kpis

pytestmark = pytest.mark.unit


def _loaded(*, budget: float, cart_rows_n: int, cost_each: float) -> LoadedSession:
    cart_rows = [
        {
            "asin": f"AA{i:02d}",
            "qty": 1,
            "unit_cost_eur": cost_each,
            "cost_total": cost_each,
            "vgp_score": 0.5,
            "roi": 0.10,
            "locked": False,
        }
        for i in range(cart_rows_n)
    ]
    summary = SessionSummary(
        id=1,
        started_at=datetime.now(tz=UTC),
        ended_at=None,
        budget_eur=Decimal(str(budget)),
        velocity_target=15,
        listino_hash="x" * 64,
        n_cart_items=cart_rows_n,
        n_panchina_items=0,
    )
    return LoadedSession(summary=summary, cart_rows=cart_rows, panchina_rows=[])


def _replayed(*, budget: float, cart_items: list[CartItem], budget_t1: float) -> SessionResult:
    cart = Cart(budget=budget)
    for item in cart_items:
        cart.add(item)
    return SessionResult(
        cart=cart,
        panchina=pd.DataFrame(),
        budget_t1=budget_t1,
        enriched_df=pd.DataFrame(),
    )


def test_compare_returns_two_blocks() -> None:
    """Output ha chiavi `original` e `replayed` con i 5 KPI."""
    loaded = _loaded(budget=5000.0, cart_rows_n=2, cost_each=1000.0)
    replayed = _replayed(
        budget=3000.0,
        cart_items=[
            CartItem(asin="AA00", cost_total=1000.0, qty=1, vgp_score=0.5),
        ],
        budget_t1=3500.0,
    )
    kpis = compare_session_kpis(loaded, replayed)
    assert set(kpis) == {"original", "replayed"}
    expected_keys = {"budget", "saturation", "budget_t1", "cart_count", "panchina_count"}
    assert set(kpis["original"]) == expected_keys
    assert set(kpis["replayed"]) == expected_keys


def test_compare_original_saturation_computed_from_cart_rows() -> None:
    """`saturation = sum(cost_total) / budget` (capped a 1.0)."""
    loaded = _loaded(budget=5000.0, cart_rows_n=2, cost_each=1500.0)  # 3000/5000 = 0.6
    replayed = _replayed(budget=5000.0, cart_items=[], budget_t1=5000.0)
    kpis = compare_session_kpis(loaded, replayed)
    assert kpis["original"]["saturation"] == pytest.approx(0.6)


def test_compare_original_budget_t1_is_nan_placeholder() -> None:
    """`budget_t1` originale e' NaN (non persistito in LoadedSession)."""
    loaded = _loaded(budget=5000.0, cart_rows_n=1, cost_each=1000.0)
    replayed = _replayed(budget=5000.0, cart_items=[], budget_t1=5234.5)
    kpis = compare_session_kpis(loaded, replayed)
    assert math.isnan(kpis["original"]["budget_t1"])
    assert kpis["replayed"]["budget_t1"] == pytest.approx(5234.5)


def test_compare_replayed_uses_replayed_budget_and_saturation() -> None:
    """`replayed.budget` / `saturation` derivano dal Cart object, non dal loaded."""
    loaded = _loaded(budget=5000.0, cart_rows_n=2, cost_each=1500.0)
    replayed = _replayed(
        budget=2000.0,
        cart_items=[CartItem(asin="X", cost_total=1500.0, qty=1, vgp_score=0.4)],
        budget_t1=2200.0,
    )
    kpis = compare_session_kpis(loaded, replayed)
    assert kpis["replayed"]["budget"] == pytest.approx(2000.0)
    assert kpis["replayed"]["saturation"] == pytest.approx(0.75)
    assert kpis["replayed"]["cart_count"] == pytest.approx(1.0)


def test_compare_zero_budget_original_saturation_zero() -> None:
    """`budget=0` originale → saturation=0 (no division-by-zero)."""
    loaded = _loaded(budget=0.0, cart_rows_n=0, cost_each=0.0)
    replayed = _replayed(budget=100.0, cart_items=[], budget_t1=100.0)
    kpis = compare_session_kpis(loaded, replayed)
    assert kpis["original"]["saturation"] == pytest.approx(0.0)
