"""Integration test per `try_replay_session` UI helper (CHG-2026-04-30-057).

Verifica il graceful wrapping su:
- sessione inesistente → (None, error_msg).
- locked-in over-budget → (None, "R-04 fallito: ...").
- successo → (SessionResult, None) con cart ricalcolato.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, SessionResult, run_session
from talos.persistence import save_session_result
from talos.persistence.models import AnalysisSession
from talos.ui import try_replay_session

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine


pytestmark = pytest.mark.integration


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()


def _samsung_listino() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("RU01", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("RU02", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("RU03", 400.0, 200.0, 0.10, 25.0, 1, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_try_replay_session_success(pg_engine: Engine) -> None:
    """Successo: sessione salvata → replay → SessionResult tornato, no error."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)

    # Setup: salva una sessione.
    sess = factory()
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    result = run_session(inp)
    sid = save_session_result(sess, session_input=inp, result=result)
    sess.commit()
    sess.close()

    try:
        replayed, err = try_replay_session(factory, sid, budget_override=2000.0)
        assert err is None
        assert isinstance(replayed, SessionResult)
        assert replayed.cart.budget == 2000.0
        assert replayed.cart.total_cost <= 2000.0
    finally:
        # Cleanup: cancella la sessione + child via cascade FK.
        sess2 = factory()
        try:
            asession = sess2.get(AnalysisSession, sid)
            if asession is not None:
                sess2.delete(asession)
                sess2.commit()
        finally:
            sess2.close()


def test_try_replay_session_missing_id_returns_error(pg_engine: Engine) -> None:
    """ID inesistente → (None, error_msg)."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    replayed, err = try_replay_session(factory, 9_999_999)
    assert replayed is None
    assert err is not None
    assert "non trovata" in err


def test_try_replay_session_insufficient_budget_returns_error(pg_engine: Engine) -> None:
    """Locked-in over-budget → (None, 'R-04 fallito: ...')."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)

    sess = factory()
    inp = SessionInput(listino_raw=_samsung_listino(), budget=10_000.0)
    result = run_session(inp)
    sid = save_session_result(sess, session_input=inp, result=result)
    sess.commit()
    sess.close()

    try:
        # RU01 costo totale > 100 EUR → R-04 fail.
        replayed, err = try_replay_session(
            factory,
            sid,
            locked_in_override=["RU01"],
            budget_override=100.0,
        )
        assert replayed is None
        assert err is not None
        assert "R-04" in err
    finally:
        sess2 = factory()
        try:
            asession = sess2.get(AnalysisSession, sid)
            if asession is not None:
                sess2.delete(asession)
                sess2.commit()
        finally:
            sess2.close()
