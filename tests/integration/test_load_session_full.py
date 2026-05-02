"""Integration test per `load_session_full` (CHG-2026-04-30-052).

Round-trip save → load_full: ricostruisce un `SessionResult` (cart/
panchina/budget_t1/enriched_df) da DB e verifica che corrisponda a
quello prodotto da `run_session` originale (entro tolerance Decimal→float).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, SessionResult, run_session
from talos.persistence import (
    load_session_full,
    save_session_result,
)
from talos.tetris import Cart

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
            ("LF001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("LF002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("LF003", 250.0, 240.0, 0.08, 25.0, 1, "MATCH"),  # vetoed
            ("LF004", 600.0, 350.0, 0.10, 30.0, 1, "MISMATCH"),  # killed
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_load_full_returns_none_for_missing_id(orm_session: Session) -> None:
    """ID inesistente → None."""
    assert load_session_full(orm_session, 999_999) is None


def test_load_full_invalid_id_raises(orm_session: Session) -> None:
    """ID <= 0 → ValueError."""
    with pytest.raises(ValueError, match="session_id"):
        load_session_full(orm_session, 0)
    with pytest.raises(ValueError, match="session_id"):
        load_session_full(orm_session, -3)


def test_load_full_returns_session_result_after_save(orm_session: Session) -> None:
    """Round-trip: l'oggetto è `SessionResult` con i 4 campi canonici."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_full(orm_session, sid)
    assert loaded is not None
    assert isinstance(loaded, SessionResult)
    assert isinstance(loaded.cart, Cart)
    assert isinstance(loaded.panchina, pd.DataFrame)
    assert isinstance(loaded.enriched_df, pd.DataFrame)
    assert isinstance(loaded.budget_t1, float)


def test_load_full_cart_round_trip(orm_session: Session) -> None:
    """Cart ricostruito ha asin/qty/cost_total/locked uguali all'output orchestrator."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        locked_in=["LF002"],
    )
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_full(orm_session, sid)
    assert loaded is not None
    assert loaded.cart.budget == result.cart.budget
    # CHG-022: loaded.cart.items è il subset DB (allocated only).
    assert len(loaded.cart.items) == len(result.cart.allocated_items())

    by_asin_in_mem = {item.asin: item for item in result.cart.allocated_items()}
    for li_item in loaded.cart.items:
        original = by_asin_in_mem[li_item.asin]
        assert li_item.qty == original.qty
        assert li_item.locked == original.locked
        assert abs(li_item.cost_total - original.cost_total) < 0.01
        # Numeric(12, 4) → float: drift atteso < 1e-4 sulle 4 cifre conservate.
        assert abs(li_item.vgp_score - original.vgp_score) < 1e-4


def test_load_full_enriched_df_columns_present(orm_session: Session) -> None:
    """`enriched_df` contiene le colonne canoniche persistite."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_full(orm_session, sid)
    assert loaded is not None

    expected_cols = {
        "asin",
        "cost_eur",
        "roi",
        "velocity_monthly",
        "cash_profit_eur",
        "roi_norm",
        "velocity_norm",
        "cash_profit_norm",
        "vgp_score",
        "veto_roi_passed",
        "kill_mask",
        "qty_target",
        "qty_final",
    }
    assert expected_cols.issubset(set(loaded.enriched_df.columns))
    assert len(loaded.enriched_df) == len(_samsung_listino())


def test_load_full_panchina_round_trip(orm_session: Session) -> None:
    """Panchina ha gli stessi ASIN dell'output orchestrator, ordinati per vgp_score DESC."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=200.0)  # tight budget
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_full(orm_session, sid)
    assert loaded is not None

    asins_in_mem = {str(a).strip() for a in result.panchina["asin"]}
    asins_loaded = {str(a).strip() for a in loaded.panchina["asin"]}
    assert asins_in_mem == asins_loaded

    if len(loaded.panchina) > 1:
        scores = list(loaded.panchina["vgp_score"])
        assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_load_full_budget_t1_recalculated(orm_session: Session) -> None:
    """`budget_t1` ricalcolato corrisponde all'originale entro tolerance Decimal→float."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    loaded = load_session_full(orm_session, sid)
    assert loaded is not None
    # Decimal Numeric(12, 4) → float per cash_profit, moltiplicato per qty
    # (e sommato su tutto il cart): drift atteso < 1.0 EUR su budget di
    # 5000 EUR (tolleranza ~0.02% MVP — CFO non vede differenze decimali).
    assert abs(loaded.budget_t1 - result.budget_t1) < 1.0


def test_load_full_filters_by_tenant_id(orm_session: Session) -> None:
    """Sessione di tenant=1 NON viene caricata con tenant=2."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result, tenant_id=1)

    assert load_session_full(orm_session, sid, tenant_id=1) is not None
    assert load_session_full(orm_session, sid, tenant_id=2) is None
