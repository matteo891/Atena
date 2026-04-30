"""Unit test per la telemetria emessa da `tetris/allocator.py` (CHG-2026-04-30-046).

Verifica che:
- `allocate_tetris` emette `tetris.skipped_budget` quando una riga ha
  `cost_total > cart.remaining` nel Pass 2 (R-06 letterale).
- I campi del log corrispondono al contratto ADR-0021 (catalogo eventi
  canonici): `asin`, `cost`, `budget_remaining`.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from talos.tetris import allocate_tetris

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["asin", "cost_eur", "qty_final", "vgp_score"])


def test_skipped_budget_emits_canonical_event(caplog: pytest.LogCaptureFixture) -> None:
    """Quando un ASIN viene skippato per cost > remaining, emette `tetris.skipped_budget`."""
    vgp_df = _df(
        [
            ("A_TOP", 200.0, 1, 0.9),  # entra, cost=200
            ("B_BIG", 1000.0, 1, 0.8),  # cost=1000 > remaining=300 -> skip
            ("C_FITS", 100.0, 1, 0.7),  # entra, cost=100
        ],
    )
    with caplog.at_level(logging.DEBUG, logger="talos.tetris.allocator"):
        cart = allocate_tetris(vgp_df, budget=500.0, locked_in=[])

    # Verifica esecuzione corretta
    assert cart.asin_list() == ["A_TOP", "C_FITS"]

    # Verifica emissione evento canonico per B_BIG
    skipped_records = [r for r in caplog.records if r.message == "tetris.skipped_budget"]
    assert len(skipped_records) == 1
    skipped = skipped_records[0]
    assert getattr(skipped, "asin", None) == "B_BIG"
    assert getattr(skipped, "cost", None) == pytest.approx(1000.0)
    assert getattr(skipped, "budget_remaining", None) == pytest.approx(300.0)


def test_no_skipped_budget_event_when_all_fit(caplog: pytest.LogCaptureFixture) -> None:
    """Quando nessuna riga supera il budget, niente `tetris.skipped_budget`."""
    vgp_df = _df(
        [
            ("A", 100.0, 1, 0.9),
            ("B", 50.0, 1, 0.7),
        ],
    )
    with caplog.at_level(logging.DEBUG, logger="talos.tetris.allocator"):
        allocate_tetris(vgp_df, budget=10000.0, locked_in=[])

    skipped = [r for r in caplog.records if r.message == "tetris.skipped_budget"]
    assert skipped == []


def test_skipped_budget_event_does_not_trigger_for_score_zero(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Skip per `vgp_score==0` NON emette `tetris.skipped_budget` (motivo diverso)."""
    vgp_df = _df(
        [
            ("A_OK", 100.0, 1, 0.9),
            ("B_DEAD", 50.0, 1, 0.0),  # score=0 -> skip silenzioso (R-05/R-08 a monte)
        ],
    )
    with caplog.at_level(logging.DEBUG, logger="talos.tetris.allocator"):
        allocate_tetris(vgp_df, budget=1000.0, locked_in=[])

    # tetris.skipped_budget riguarda SOLO over-budget, non kill/veto.
    skipped = [r for r in caplog.records if r.message == "tetris.skipped_budget"]
    assert skipped == []
