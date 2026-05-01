"""Unit test telemetria `build_panchina` (CHG-2026-04-30-049 + CHG-B1.1.b).

Verifica emissione `panchina.archived` per ogni riga in panchina via
`structlog.testing.LogCapture`. Fixture `log_capture` condivisa in
`tests/conftest.py` (CHG-031).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from talos.tetris import Cart, CartItem, build_panchina

if TYPE_CHECKING:
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["asin", "cost_eur", "qty_final", "vgp_score"])


def _cart_with(asins: list[str]) -> Cart:
    cart = Cart(budget=1000.0)
    for asin in asins:
        cart.add(CartItem(asin=asin, cost_total=100.0, qty=1, vgp_score=0.5))
    return cart


def test_panchina_archived_event_per_row(log_capture: LogCapture) -> None:
    """Ogni riga in panchina genera 1 evento `panchina.archived`."""
    df = _df(
        [
            ("A_TOP", 100.0, 1, 0.9),
            ("B_MID", 50.0, 1, 0.5),
            ("C_LOW", 30.0, 1, 0.3),
        ],
    )
    cart = _cart_with([])  # cart vuoto -> tutti in panchina
    out = build_panchina(df, cart)

    assert len(out) == 3
    archived = [e for e in log_capture.entries if e["event"] == "panchina.archived"]
    assert len(archived) == 3
    asins = {e["asin"] for e in archived}
    assert asins == {"A_TOP", "B_MID", "C_LOW"}


def test_panchina_archived_event_carries_vgp_score(log_capture: LogCapture) -> None:
    """Ogni record include `vgp_score` (campo richiesto dal catalogo)."""
    df = _df([("X", 100.0, 1, 0.7)])
    cart = _cart_with([])
    build_panchina(df, cart)

    archived = [e for e in log_capture.entries if e["event"] == "panchina.archived"]
    assert len(archived) == 1
    assert archived[0]["vgp_score"] == pytest.approx(0.7)


def test_no_panchina_event_when_panchina_empty(log_capture: LogCapture) -> None:
    """Nessun evento se panchina e' vuota (tutti in cart o tutti vetati)."""
    df = _df([("A", 100.0, 1, 0.0)])  # vgp=0 -> non in panchina
    cart = _cart_with([])
    build_panchina(df, cart)

    archived = [e for e in log_capture.entries if e["event"] == "panchina.archived"]
    assert archived == []
