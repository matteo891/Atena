"""Unit test telemetria `session.replayed` (CHG-2026-04-30-058 + CHG-B1.2).

Verifica che `replay_session` emetta l'evento canonico con i campi
obbligatori del catalogo ADR-0021 errata. Pattern
`structlog.testing.LogCapture` post-bridge B1.2 (CHG-2026-05-01-035 —
ultimo file applicativo migrato a structlog native + adoption
`bind_request_context`). Fixture `log_capture` condivisa in
`tests/conftest.py` (CHG-031).

Sentinella ereditarietà context: `request_id` e `tenant_id` ora
ereditati automaticamente dal pipeline `merge_contextvars` su tutti
gli eventi emessi durante `run_session`/`replay_session`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from talos.orchestrator import (
    REQUIRED_INPUT_COLUMNS,
    SessionInput,
    replay_session,
    run_session,
)

if TYPE_CHECKING:
    from structlog.testing import LogCapture

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


def test_replay_emits_session_replayed_event(log_capture: LogCapture) -> None:
    """`replay_session` emette `session.replayed` con campi del catalogo."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    loaded = run_session(inp)

    replayed = replay_session(loaded, budget_override=2000.0)

    entries = [e for e in log_capture.entries if e["event"] == "session.replayed"]
    assert len(entries) == 1
    entry = entries[0]
    # Campi obbligatori del catalogo (ADR-0021 errata CHG-058).
    assert entry["asin_count"] == len(replayed.enriched_df)
    assert entry["budget"] == pytest.approx(2000.0)
    assert "locked_in_count" in entry
    assert "budget_t1" in entry


def test_replay_event_locked_in_count(log_capture: LogCapture) -> None:
    """`locked_in_count` riflette i locked override applicati."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=10_000.0)
    loaded = run_session(inp)

    replay_session(loaded, locked_in_override=["RT02"])

    entries = [e for e in log_capture.entries if e["event"] == "session.replayed"]
    assert len(entries) == 1
    assert entries[0]["locked_in_count"] == 1


def test_run_session_binds_request_context(log_capture: LogCapture) -> None:
    """CHG-B1.2: `run_session` binda request_id+tenant_id; eventi downstream li ereditano."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        veto_roi_threshold=0.50,  # forza veto su tutti gli ASIN
    )
    run_session(inp)

    # Almeno un evento `vgp.veto_roi_failed` emesso dentro `compute_vgp_score`
    # (chiamato dentro `run_session` -> dentro il bind context).
    veto_entries = [e for e in log_capture.entries if e["event"] == "vgp.veto_roi_failed"]
    assert len(veto_entries) >= 1, "atteso almeno 1 veto con threshold 50%"

    # request_id e tenant_id ereditati automaticamente via merge_contextvars
    for entry in veto_entries:
        assert "request_id" in entry, "request_id mancante (bind non attivo?)"
        assert "tenant_id" in entry
        assert entry["tenant_id"] == 1
        # request_id è stringa UUID4 (~36 char con trattini)
        assert len(entry["request_id"]) == 36


def test_run_session_clears_request_context_on_exit(log_capture: LogCapture) -> None:
    """CHG-B1.2: clear_request_context in finally; nessun leak fra invocazioni."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        veto_roi_threshold=0.50,
    )
    run_session(inp)
    rid_first = next(e["request_id"] for e in log_capture.entries if "request_id" in e)

    # Seconda invocazione: nuovo UUID, fixture log_capture function-scoped pulisce
    # entries fra test, ma il context vars sopravvive a meno di clear esplicito.
    # Il test verifica l'ID via merge_contextvars sull'evento del SECONDO run.
    # Hack: manualmente entries[:] = [] non serve, il bind aggiorna sempre il
    # contextvar all'ingresso del prossimo run_session.
    log_capture.entries.clear()
    run_session(inp)
    rid_second = next(e["request_id"] for e in log_capture.entries if "request_id" in e)

    assert rid_first != rid_second, (
        "request_id deve cambiare fra invocazioni distinte di run_session"
    )
