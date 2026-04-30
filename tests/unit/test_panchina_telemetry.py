"""Unit test telemetria `build_panchina` (CHG-2026-04-30-049).

Verifica emissione `panchina.archived` per ogni riga in panchina.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from talos.tetris import Cart, CartItem, build_panchina

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["asin", "cost_eur", "qty_final", "vgp_score"])


def _cart_with(asins: list[str]) -> Cart:
    cart = Cart(budget=1000.0)
    for asin in asins:
        cart.add(CartItem(asin=asin, cost_total=100.0, qty=1, vgp_score=0.5))
    return cart


def test_panchina_archived_event_per_row(caplog: pytest.LogCaptureFixture) -> None:
    """Ogni riga in panchina genera 1 evento `panchina.archived`."""
    df = _df(
        [
            ("A_TOP", 100.0, 1, 0.9),
            ("B_MID", 50.0, 1, 0.5),
            ("C_LOW", 30.0, 1, 0.3),
        ],
    )
    cart = _cart_with([])  # cart vuoto -> tutti in panchina
    with caplog.at_level(logging.DEBUG, logger="talos.tetris.panchina"):
        out = build_panchina(df, cart)

    assert len(out) == 3
    archived = [r for r in caplog.records if r.message == "panchina.archived"]
    assert len(archived) == 3
    asins = {getattr(r, "asin", None) for r in archived}
    assert asins == {"A_TOP", "B_MID", "C_LOW"}


def test_panchina_archived_event_carries_vgp_score(caplog: pytest.LogCaptureFixture) -> None:
    """Ogni record include `vgp_score` (campo richiesto dal catalogo)."""
    df = _df([("X", 100.0, 1, 0.7)])
    cart = _cart_with([])
    with caplog.at_level(logging.DEBUG, logger="talos.tetris.panchina"):
        build_panchina(df, cart)

    archived = [r for r in caplog.records if r.message == "panchina.archived"]
    assert len(archived) == 1
    assert getattr(archived[0], "vgp_score", None) == pytest.approx(0.7)


def test_no_panchina_event_when_panchina_empty(caplog: pytest.LogCaptureFixture) -> None:
    """Nessun evento se panchina e' vuota (tutti in cart o tutti vetati)."""
    df = _df([("A", 100.0, 1, 0.0)])  # vgp=0 -> non in panchina
    cart = _cart_with([])
    with caplog.at_level(logging.DEBUG, logger="talos.tetris.panchina"):
        build_panchina(df, cart)

    archived = [r for r in caplog.records if r.message == "panchina.archived"]
    assert archived == []
