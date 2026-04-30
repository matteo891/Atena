"""Unit test telemetria `session.replayed` (CHG-2026-04-30-058).

Verifica che `replay_session` emetta l'evento canonico con i campi
obbligatori del catalogo ADR-0021 errata.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from talos.orchestrator import (
    REQUIRED_INPUT_COLUMNS,
    SessionInput,
    replay_session,
    run_session,
)

pytestmark = pytest.mark.unit


def _samsung_listino() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("RT01", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("RT02", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("RT03", 400.0, 200.0, 0.10, 25.0, 1, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_replay_emits_session_replayed_event(caplog: pytest.LogCaptureFixture) -> None:
    """`replay_session` emette `session.replayed` con campi del catalogo."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    loaded = run_session(inp)

    with caplog.at_level(logging.DEBUG, logger="talos.orchestrator"):
        replayed = replay_session(loaded, budget_override=2000.0)

    records = [r for r in caplog.records if r.message == "session.replayed"]
    assert len(records) == 1
    record = records[0]
    # Campi obbligatori del catalogo (ADR-0021 errata CHG-058).
    assert hasattr(record, "asin_count")
    assert hasattr(record, "locked_in_count")
    assert hasattr(record, "budget")
    assert hasattr(record, "budget_t1")
    assert record.asin_count == len(replayed.enriched_df)
    assert record.budget == pytest.approx(2000.0)


def test_replay_event_locked_in_count(caplog: pytest.LogCaptureFixture) -> None:
    """`locked_in_count` riflette i locked override applicati."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=10_000.0)
    loaded = run_session(inp)

    with caplog.at_level(logging.DEBUG, logger="talos.orchestrator"):
        replay_session(loaded, locked_in_override=["RT02"])

    records = [r for r in caplog.records if r.message == "session.replayed"]
    assert len(records) == 1
    assert records[0].locked_in_count == 1
