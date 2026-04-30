"""Unit test per `talos.formulas.compounding` (CHG-2026-04-30-032, ADR-0018).

F3 verbatim PROJECT-RAW riga 280:

    Budget_T+1 = Budget_T + Somma(Cash_Profit)

Funzione pura. Niente raise: la somma e' sempre matematicamente lecita,
budget negativo e' continuita' del compounding.
"""

from __future__ import annotations

import pytest

from talos.formulas import compounding_t1

pytestmark = pytest.mark.unit


def test_snapshot_mixed_profits() -> None:
    """Snapshot: budget 1000 + (50, 30, -10) = 1070."""
    assert compounding_t1(1000.0, [50.0, 30.0, -10.0]) == pytest.approx(1070.0, abs=1e-9)


def test_empty_iterable_returns_budget_t() -> None:
    """Lista vuota -> Budget_T+1 == Budget_T (somma vuota = 0)."""
    assert compounding_t1(1000.0, []) == pytest.approx(1000.0, abs=1e-9)


def test_only_positive_profits() -> None:
    """Compounding crescente: budget 0 + tutti positivi = somma positivi."""
    assert compounding_t1(0.0, [100.0, 200.0, 50.0]) == pytest.approx(350.0, abs=1e-9)


def test_only_negative_profits() -> None:
    """Erosione parziale: budget 500 + (-200, -100) = 200."""
    assert compounding_t1(500.0, [-200.0, -100.0]) == pytest.approx(200.0, abs=1e-9)


def test_negative_budget_t1_when_losses_exceed_budget() -> None:
    """Continuita' compounding: Budget_T+1 puo' diventare negativo."""
    assert compounding_t1(100.0, [-150.0]) == pytest.approx(-50.0, abs=1e-9)


def test_accepts_generator() -> None:
    """`Iterable[float]` accetta generator expression, non solo list."""
    profits = (x for x in [10.0, 20.0])
    assert compounding_t1(0.0, profits) == pytest.approx(30.0, abs=1e-9)


def test_single_profit() -> None:
    """Iterabile di un solo elemento."""
    assert compounding_t1(100.0, [50.0]) == pytest.approx(150.0, abs=1e-9)


def test_zero_budget_zero_profits() -> None:
    """Caso degenere: budget 0, lista vuota -> 0."""
    assert compounding_t1(0.0, []) == pytest.approx(0.0, abs=1e-9)


def test_consumes_iterable_once() -> None:
    """Generator consumato una sola volta dalla `sum()` interna.

    Verifica che il pattern non richieda di accedere all'iterabile dopo
    la chiamata (sarebbe gia' esaurito).
    """
    profits = (x for x in [1.0, 2.0, 3.0])
    result = compounding_t1(10.0, profits)
    assert result == pytest.approx(16.0, abs=1e-9)
    # Il generator e' ora esaurito: questo e' OK e atteso
    assert list(profits) == []
