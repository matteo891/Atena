"""Integration test per `talos.persistence.session_repository` (CHG-2026-04-30-042).

Persiste `SessionResult` (output `run_session`) sulle 5 tabelle Allegato A:
`sessions`, `listino_items`, `vgp_results`, `cart_items`, `panchina_items`.

Test eseguono `save_session_result` poi query inversa per verificare le
righe create. Rollback finale (la fixture `orm_session` apre transazione
esterna, fa rollback alla fine: zero side-effect tra test).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import (
    AnalysisSession,
    CartItem,
    ListinoItem,
    PanchinaItem,
    VgpResult,
    save_session_result,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine


pytestmark = pytest.mark.integration


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    """Session ORM dedicata con rollback finale per test isolation."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()


def _samsung_listino() -> pd.DataFrame:
    """Mini-listino realistic, 4 ASIN coprenti R-04/R-05/R-08/normale."""
    return pd.DataFrame(
        [
            ("S001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("S002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("S003", 250.0, 240.0, 0.08, 25.0, 1, "MATCH"),  # vetoed
            ("S004", 600.0, 350.0, 0.10, 30.0, 1, "MISMATCH"),  # killed
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def _make_session() -> tuple[SessionInput, object]:
    """Genera (SessionInput, SessionResult) per scenario fissato."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        locked_in=[],
    )
    result = run_session(inp)
    return inp, result


def test_save_creates_analysis_session_row(orm_session: Session) -> None:
    """`save_session_result` crea una riga `sessions` con campi corretti."""
    inp, result = _make_session()
    sid = save_session_result(orm_session, session_input=inp, result=result)

    fetched = orm_session.get(AnalysisSession, sid)
    assert fetched is not None
    assert fetched.budget_eur == Decimal("5000.0")
    assert fetched.velocity_target == 15
    assert fetched.tenant_id == 1
    assert len(fetched.listino_hash) == 64  # sha256 hex
    assert fetched.started_at is not None
    assert fetched.ended_at is not None  # marcata conclusa


def test_save_persists_listino_items(orm_session: Session) -> None:
    """N righe `listino_items` create con FK `session_id` corretta."""
    inp, result = _make_session()
    sid = save_session_result(orm_session, session_input=inp, result=result)

    items = orm_session.scalars(
        select(ListinoItem).where(ListinoItem.session_id == sid),
    ).all()
    assert len(items) == 4
    # CHAR(10) padda con spazi: strip per confronto.
    asins = {(item.asin or "").strip() for item in items}
    assert asins == {"S001", "S002", "S003", "S004"}
    # raw_title placeholder (no padding su Text).
    for item in items:
        assert item.raw_title == f"ASIN:{(item.asin or '').strip()}"


def test_save_persists_vgp_results(orm_session: Session) -> None:
    """N righe `vgp_results` create con i 12 campi numerici/flag corretti."""
    inp, result = _make_session()
    sid = save_session_result(orm_session, session_input=inp, result=result)

    vgps = orm_session.scalars(
        select(VgpResult).where(VgpResult.session_id == sid),
    ).all()
    assert len(vgps) == 4

    # CHAR(10) padda con spazi: strip per confronto.
    s003 = next(v for v in vgps if v.asin.strip() == "S003")
    assert s003.veto_roi_passed is False  # ROI < 8%
    assert s003.kill_switch_triggered is False
    assert s003.vgp_score == Decimal("0.0000")

    s004 = next(v for v in vgps if v.asin.strip() == "S004")
    assert s004.kill_switch_triggered is True
    assert s004.vgp_score == Decimal("0.0000")


def test_save_persists_cart_items(orm_session: Session) -> None:
    """CHG-022 cart exhaustive: DB persiste solo `allocated_items()` (qty>0)."""
    inp, result = _make_session()
    sid = save_session_result(orm_session, session_input=inp, result=result)

    cart_rows = orm_session.scalars(
        select(CartItem).where(CartItem.session_id == sid),
    ).all()
    allocated = result.cart.allocated_items()
    assert len(cart_rows) == len(allocated)
    for db_row, in_mem in zip(cart_rows, allocated, strict=True):
        assert db_row.qty == in_mem.qty
        expected_unit = Decimal(str(in_mem.cost_total / in_mem.qty))
        assert db_row.unit_cost_eur == pytest.approx(expected_unit, abs=Decimal("0.01"))
        assert db_row.locked_in == in_mem.locked


def test_save_persists_panchina_items(orm_session: Session) -> None:
    """P righe `panchina_items` create con `qty_proposed` da `qty_final`."""
    inp, result = _make_session()
    sid = save_session_result(orm_session, session_input=inp, result=result)

    panch_rows = orm_session.scalars(
        select(PanchinaItem).where(PanchinaItem.session_id == sid),
    ).all()
    assert len(panch_rows) == len(result.panchina)


def test_save_listino_hash_deterministic(orm_session: Session) -> None:
    """Stesso listino → stesso hash. Listino diverso → hash diverso.

    Post CHG-047 (UNIQUE INDEX su (tenant_id, listino_hash)) testiamo
    l'helper privato `_listino_hash` direttamente per il caso "stesso →
    stesso", e usiamo tenant_id diversi per persistere due sessioni con
    listino identico (entrambe ammesse dal vincolo).
    """
    from talos.persistence.session_repository import (  # noqa: PLC0415
        _listino_hash,
    )

    inp1, result1 = _make_session()
    sid1 = save_session_result(orm_session, session_input=inp1, result=result1, tenant_id=1)
    h1 = orm_session.get(AnalysisSession, sid1).listino_hash

    # Helper deterministico (stesso input → stesso hash, isolato dal DB).
    h_helper = _listino_hash(inp1.listino_raw)
    assert h1 == h_helper

    # Stesso listino, tenant_id diverso → save ammesso, stesso hash.
    inp2, result2 = _make_session()
    sid2 = save_session_result(orm_session, session_input=inp2, result=result2, tenant_id=99)
    h2 = orm_session.get(AnalysisSession, sid2).listino_hash
    assert h1 == h2

    # Listino diverso → hash diverso (tenant=1, no conflitto col primo).
    df_modified = inp1.listino_raw.copy()
    df_modified.loc[0, "buy_box_eur"] = 1500.0
    inp3 = SessionInput(listino_raw=df_modified, budget=inp1.budget)
    result3 = run_session(inp3)
    sid3 = save_session_result(orm_session, session_input=inp3, result=result3, tenant_id=1)
    h3 = orm_session.get(AnalysisSession, sid3).listino_hash
    assert h1 != h3


def test_save_custom_tenant_id(orm_session: Session) -> None:
    """`tenant_id` personalizzato viene materializzato sulla riga session."""
    inp, result = _make_session()
    sid = save_session_result(orm_session, session_input=inp, result=result, tenant_id=42)

    fetched = orm_session.get(AnalysisSession, sid)
    assert fetched.tenant_id == 42


def test_save_returns_session_id_int(orm_session: Session) -> None:
    """Return value e' un `int` valido (non `None`, non Decimal)."""
    inp, result = _make_session()
    sid = save_session_result(orm_session, session_input=inp, result=result)
    assert isinstance(sid, int)
    assert sid > 0


def test_save_with_locked_in(orm_session: Session) -> None:
    """Locked-in viene marcato `locked_in=True` nella riga `cart_items`."""
    listino = _samsung_listino()
    inp = SessionInput(
        listino_raw=listino,
        budget=5000.0,
        locked_in=["S002"],
    )
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    cart_rows = orm_session.scalars(
        select(CartItem).where(CartItem.session_id == sid),
    ).all()
    locked_rows = [c for c in cart_rows if c.locked_in]
    assert len(locked_rows) == 1
    # Il VgpResult collegato all'unico locked-in deve essere S002 (strip CHAR(10) padding).
    locked_vgp_id = locked_rows[0].vgp_result_id
    locked_vgp = orm_session.get(VgpResult, locked_vgp_id)
    assert locked_vgp.asin.strip() == "S002"
