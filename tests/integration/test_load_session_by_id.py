"""Integration test per `load_session_by_id` (CHG-2026-04-30-045).

Round-trip save → load:
- Creiamo una sessione via `save_session_result`
- La ricarichiamo via `load_session_by_id`
- Assertiamo che summary e righe corrispondano all'output originale
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import (
    LoadedSession,
    SessionSummary,
    load_session_by_id,
    save_session_result,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine


pytestmark = pytest.mark.integration


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    """Session ORM con rollback finale."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()


def _samsung_listino() -> pd.DataFrame:
    """Mini-listino realistic 4 ASIN copertura R-04/R-05/R-08/normale."""
    return pd.DataFrame(
        [
            ("LD001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("LD002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("LD003", 250.0, 240.0, 0.08, 25.0, 1, "MATCH"),  # vetoed
            ("LD004", 600.0, 350.0, 0.10, 30.0, 1, "MISMATCH"),  # killed
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_load_returns_none_for_missing_id(orm_session: Session) -> None:
    """ID inesistente -> None."""
    loaded = load_session_by_id(orm_session, 999_999)
    assert loaded is None


def test_load_invalid_id_raises(orm_session: Session) -> None:
    """ID <= 0 -> ValueError."""
    with pytest.raises(ValueError, match="session_id"):
        load_session_by_id(orm_session, 0)
    with pytest.raises(ValueError, match="session_id"):
        load_session_by_id(orm_session, -5)


def test_load_returns_loaded_session_after_save(orm_session: Session) -> None:
    """Round-trip save → load: l'oggetto ritornato e' `LoadedSession` con summary."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_by_id(orm_session, sid)
    assert loaded is not None
    assert isinstance(loaded, LoadedSession)
    assert isinstance(loaded.summary, SessionSummary)
    assert loaded.summary.id == sid
    assert loaded.summary.budget_eur == Decimal("5000.0")
    assert loaded.summary.n_cart_items == len(result.cart.allocated_items())
    assert loaded.summary.n_panchina_items == len(result.panchina)


def test_load_cart_rows_match_orchestrator_cart(orm_session: Session) -> None:
    """Cart rows ricaricati hanno asin/qty/locked corrispondenti all'output orchestrator."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        locked_in=["LD002"],
    )
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_by_id(orm_session, sid)
    assert loaded is not None
    assert len(loaded.cart_rows) == len(result.cart.allocated_items())

    # Map by asin per confronto.
    in_mem_by_asin = {item.asin: item for item in result.cart.items}
    for row in loaded.cart_rows:
        asin = str(row["asin"])
        assert asin in in_mem_by_asin
        in_mem = in_mem_by_asin[asin]
        assert row["qty"] == in_mem.qty
        assert row["locked"] == in_mem.locked
        # cost_total = unit_cost * qty (entro tolerance Decimal/float)
        assert abs(float(row["cost_total"]) - in_mem.cost_total) < 0.01


def test_load_panchina_rows_match(orm_session: Session) -> None:
    """Panchina rows ricaricati hanno gli stessi ASIN dell'output orchestrator."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=200.0)  # tight budget
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_by_id(orm_session, sid)
    assert loaded is not None

    asins_in_mem = set(result.panchina["asin"])
    asins_loaded = {str(row["asin"]) for row in loaded.panchina_rows}
    assert asins_in_mem == asins_loaded


def test_load_panchina_rows_ordered_vgp_desc(orm_session: Session) -> None:
    """Panchina rows ricaricati ordinati per vgp_score DESC."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=200.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_by_id(orm_session, sid)
    assert loaded is not None

    scores = [float(row["vgp_score"]) for row in loaded.panchina_rows]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_load_filters_by_tenant_id(orm_session: Session) -> None:
    """Sessione di tenant=1 NON viene caricata se richiesta con tenant=2."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result, tenant_id=1)

    # Carica con tenant corretto -> trovata
    loaded_t1 = load_session_by_id(orm_session, sid, tenant_id=1)
    assert loaded_t1 is not None

    # Carica con tenant sbagliato -> None (NON la mostra)
    loaded_t2 = load_session_by_id(orm_session, sid, tenant_id=2)
    assert loaded_t2 is None


def test_load_session_with_locked_in_marks_correct_row(orm_session: Session) -> None:
    """Locked-in (R-04) viene preservato nel cart_rows.locked."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        locked_in=["LD002"],
    )
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_by_id(orm_session, sid)
    assert loaded is not None
    locked_rows = [r for r in loaded.cart_rows if r["locked"]]
    assert len(locked_rows) == 1
    assert str(locked_rows[0]["asin"]) == "LD002"
