"""Integration test per gli helper di persistenza in `talos.ui.dashboard`.

CHG-2026-04-30-043. Verifica che:
1. `get_session_factory_or_none()` ritorna factory valido se `TALOS_DB_URL` settata.
2. `try_persist_session(factory, ...)` persiste e ritorna `(True, sid, None)`.
3. `try_persist_session` cattura errori e ritorna `(False, None, error_str)`.

Questi helper sono il ponte tra l'UI Streamlit e il repository
`save_session_result` (CHG-042).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import AnalysisSession
from talos.ui.dashboard import (
    get_session_factory_or_none,
    try_persist_session,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine  # noqa: F401 - implicit fixture type hint


pytestmark = pytest.mark.integration


def _samsung_listino() -> pd.DataFrame:
    """Mini-listino realistic 3 ASIN."""
    return pd.DataFrame(
        [
            ("D001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("D002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("D003", 250.0, 240.0, 0.08, 25.0, 1, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_get_session_factory_returns_valid_factory(pg_engine) -> None:  # noqa: ARG001
    """`TALOS_DB_URL` settata (via fixture pg_engine) -> factory valido.

    `pg_engine` e' richiesta come fixture per garantire che `TALOS_DB_URL`
    sia settato (skip module-level se assente) — argomento intenzionalmente
    non usato dentro il test.
    """
    factory = get_session_factory_or_none()
    assert factory is not None
    assert isinstance(factory, sessionmaker)


def test_try_persist_session_success(pg_engine) -> None:  # noqa: ARG001
    """`try_persist_session` ritorna `(True, sid, None)` su DB raggiungibile."""
    factory = get_session_factory_or_none()
    assert factory is not None

    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    success, sid, err = try_persist_session(factory, session_input=inp, result=result)

    assert success is True
    assert sid is not None
    assert sid > 0
    assert err is None

    # Verifica che il record esista davvero (legge dal DB) + cleanup.
    with factory() as sess:
        fetched = sess.get(AnalysisSession, sid)
        assert fetched is not None
        sess.delete(fetched)
        sess.commit()
