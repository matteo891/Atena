"""Unit test telemetria `tetris/allocator.py` (CHG-2026-04-30-046 + CHG-B1.1.b).

Verifica che `allocate_tetris` emette `tetris.skipped_budget` quando una
riga ha `cost_total > cart.remaining` nel Pass 2 (R-06 letterale). Campi
del log conformi al catalogo ADR-0021: `asin`, `cost`, `budget_remaining`.

Fixture `log_capture` condivisa in `tests/conftest.py` (CHG-031).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from talos.tetris import allocate_tetris

if TYPE_CHECKING:
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


def _df(rows: list[tuple[str, float, int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["asin", "cost_eur", "qty_final", "vgp_score"])


def test_skipped_budget_emits_canonical_event(log_capture: LogCapture) -> None:
    """CHG-2026-05-02-020 greedy: emit `tetris.skipped_budget` quando 1 lotto > remaining."""
    vgp_df = _df(
        [
            ("A_FILL", 50.0, 5, 0.9),  # 1 lotto = 250, budget 300 → max_lot=5, cost=250 (entra)
            ("B_TOO_BIG", 100.0, 5, 0.7),  # 1 lotto=500 > remaining=50 → skip
        ],
    )
    cart = allocate_tetris(vgp_df, budget=300.0, locked_in=[])
    assert cart.asin_list() == ["A_FILL"]

    skipped = [e for e in log_capture.entries if e["event"] == "tetris.skipped_budget"]
    assert len(skipped) == 1
    entry = skipped[0]
    assert entry["asin"] == "B_TOO_BIG"
    # Greedy emit: cost = cost_unit * lot_size (1 lotto) anziché cost_total qty_final.
    assert entry["cost"] == pytest.approx(500.0)
    assert entry["budget_remaining"] == pytest.approx(50.0)


def test_no_skipped_budget_event_when_all_fit(log_capture: LogCapture) -> None:
    """Quando nessuna riga supera il budget, niente `tetris.skipped_budget`."""
    vgp_df = _df(
        [
            ("A", 100.0, 1, 0.9),
            ("B", 50.0, 1, 0.7),
        ],
    )
    allocate_tetris(vgp_df, budget=10000.0, locked_in=[])

    skipped = [e for e in log_capture.entries if e["event"] == "tetris.skipped_budget"]
    assert skipped == []


def test_skipped_budget_event_does_not_trigger_for_score_zero(
    log_capture: LogCapture,
) -> None:
    """Skip per `vgp_score==0` NON emette `tetris.skipped_budget` (motivo diverso)."""
    vgp_df = _df(
        [
            ("A_OK", 100.0, 1, 0.9),
            ("B_DEAD", 50.0, 1, 0.0),  # score=0 -> skip silenzioso (R-05/R-08 a monte)
        ],
    )
    allocate_tetris(vgp_df, budget=1000.0, locked_in=[])

    # tetris.skipped_budget riguarda SOLO over-budget, non kill/veto.
    skipped = [e for e in log_capture.entries if e["event"] == "tetris.skipped_budget"]
    assert skipped == []
