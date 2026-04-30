"""Integration test per `fetch_existing_session_for_listino` (CHG-2026-04-30-048).

UI helper che integra `find_session_by_hash` per il pre-save warning
duplicate nella dashboard Streamlit.
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import save_session_result
from talos.ui.dashboard import (
    fetch_existing_session_for_listino,
    get_session_factory_or_none,
)

pytestmark = pytest.mark.integration


def _samsung_listino(prefix: str = "DUP") -> pd.DataFrame:
    return pd.DataFrame(
        [
            (f"{prefix}001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            (f"{prefix}002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_returns_none_for_unsaved_listino(pg_engine) -> None:  # noqa: ARG001
    """Listino mai persistito → None (graceful)."""
    factory = get_session_factory_or_none()
    assert factory is not None
    listino = _samsung_listino(prefix="UNSAVED")
    existing = fetch_existing_session_for_listino(factory, listino)
    assert existing is None


def test_returns_summary_for_existing_listino(pg_engine) -> None:  # noqa: ARG001
    """Salvato il listino → fetch_existing ritorna SessionSummary."""
    factory = get_session_factory_or_none()
    assert factory is not None
    listino = _samsung_listino(prefix="EXIST")
    inp = SessionInput(listino_raw=listino, budget=2000.0)
    result = run_session(inp)

    # Salviamo via session_scope (commit reale - cleanup manuale alla fine).
    from talos.persistence import session_scope  # noqa: PLC0415

    with session_scope(factory) as db:
        sid = save_session_result(db, session_input=inp, result=result, tenant_id=1)

    try:
        existing = fetch_existing_session_for_listino(factory, listino)
        assert existing is not None
        assert existing.id == sid
        assert existing.n_cart_items >= 0
    finally:
        # Cleanup: rimuoviamo la riga creata (test integration sporca dal DB).
        from talos.persistence import AnalysisSession  # noqa: PLC0415

        with session_scope(factory) as db:
            obj = db.get(AnalysisSession, sid)
            if obj is not None:
                db.delete(obj)


def test_filters_by_tenant_id(pg_engine) -> None:  # noqa: ARG001
    """Salvato per tenant=1 → fetch_existing con tenant=2 → None."""
    factory = get_session_factory_or_none()
    assert factory is not None
    listino = _samsung_listino(prefix="TFLT")
    inp = SessionInput(listino_raw=listino, budget=2000.0)
    result = run_session(inp)

    from talos.persistence import session_scope  # noqa: PLC0415

    with session_scope(factory) as db:
        sid = save_session_result(db, session_input=inp, result=result, tenant_id=1)

    try:
        # Tenant 1 → trovato
        e1 = fetch_existing_session_for_listino(factory, listino, tenant_id=1)
        assert e1 is not None
        # Tenant 2 → NON trovato (isolamento)
        e2 = fetch_existing_session_for_listino(factory, listino, tenant_id=2)
        assert e2 is None
    finally:
        from talos.persistence import AnalysisSession  # noqa: PLC0415

        with session_scope(factory) as db:
            obj = db.get(AnalysisSession, sid)
            if obj is not None:
                db.delete(obj)


def test_re_export_in_init(pg_engine) -> None:  # noqa: ARG001
    """`talos.ui` re-esporta `fetch_existing_session_for_listino`."""
    from talos import ui  # noqa: PLC0415

    assert hasattr(ui, "fetch_existing_session_for_listino")
