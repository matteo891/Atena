"""Integration test per `replay_session` (CHG-2026-04-30-056).

`replay_session` consuma `SessionResult` ricaricato (load_session_full)
e ri-applica Tetris+panchina+compounding con eventuali override di
`locked_in` o `budget`. Pensato per "what-if" interattivo del CFO.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import (
    REQUIRED_INPUT_COLUMNS,
    SessionInput,
    replay_session,
    run_session,
)
from talos.persistence import (
    load_session_full,
    save_session_result,
)
from talos.tetris import InsufficientBudgetError

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
    """Mini-listino con 5 ASIN (mix score per stress su allocator)."""
    return pd.DataFrame(
        [
            ("RP01", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("RP02", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("RP03", 400.0, 200.0, 0.10, 25.0, 1, "MATCH"),
            ("RP04", 300.0, 250.0, 0.08, 20.0, 1, "MATCH"),
            ("RP05", 600.0, 350.0, 0.10, 30.0, 1, "MISMATCH"),  # killed
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def _save_and_reload(orm_session: Session, inp: SessionInput) -> tuple[int, object]:
    """Helper: run + save + load_full."""
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)
    orm_session.flush()
    loaded = load_session_full(orm_session, sid)
    assert loaded is not None
    return sid, loaded


def test_replay_no_overrides_equivalent_to_loaded(orm_session: Session) -> None:
    """`replay_session(loaded)` senza override → cart equivalente al loaded."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    _, loaded = _save_and_reload(orm_session, inp)

    replay = replay_session(loaded)
    # CHG-022: confronto solo allocated_items (qty>0), no exhaustive items.
    assert replay.cart.budget == loaded.cart.budget
    rep_alloc = {item.asin for item in replay.cart.allocated_items()}
    load_alloc = {item.asin for item in loaded.cart.allocated_items()}
    assert rep_alloc == load_alloc
    qty_by_asin = {item.asin: item.qty for item in replay.cart.allocated_items()}
    qty_loaded = {item.asin: item.qty for item in loaded.cart.allocated_items()}
    assert qty_by_asin == qty_loaded


def test_replay_with_locked_in_override(orm_session: Session) -> None:
    """Override locked_in → l'ASIN scelto entra nel cart con `locked=True`."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    _, loaded = _save_and_reload(orm_session, inp)

    replay = replay_session(loaded, locked_in_override=["RP04"])
    locked_items = [item for item in replay.cart.items if item.locked]
    assert len(locked_items) == 1
    assert locked_items[0].asin == "RP04"


def test_replay_with_empty_locked_in_removes_locks(orm_session: Session) -> None:
    """`locked_in_override=[]` → tutti i locked-in originali rimossi."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        locked_in=["RP02"],
    )
    _, loaded = _save_and_reload(orm_session, inp)

    replay = replay_session(loaded, locked_in_override=[])
    assert all(not item.locked for item in replay.cart.items)


def test_replay_with_lower_budget_shrinks_cart(orm_session: Session) -> None:
    """Budget piu' basso → meno item nel cart (o stessi ma costo totale ridotto)."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=10_000.0)
    _, loaded = _save_and_reload(orm_session, inp)

    # Budget ridotto a 1000 EUR
    replay = replay_session(loaded, budget_override=1000.0)
    assert replay.cart.budget == 1000.0
    assert replay.cart.total_cost <= 1000.0


def test_replay_with_locked_in_over_budget_raises(orm_session: Session) -> None:
    """Locked-in che supera il nuovo budget → InsufficientBudgetError (R-04)."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=10_000.0)
    _, loaded = _save_and_reload(orm_session, inp)

    # RP01 costa 600 * 60 (qty_target) > 100 EUR
    with pytest.raises(InsufficientBudgetError):
        replay_session(
            loaded,
            locked_in_override=["RP01"],
            budget_override=100.0,
        )


def test_replay_recomputes_budget_t1(orm_session: Session) -> None:
    """Budget_T+1 ricalcolato sul nuovo cart (no riuso del valore loaded)."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=5000.0)
    _, loaded = _save_and_reload(orm_session, inp)

    # Replay con budget piu' basso → budget_t1 piu' basso (meno cart_profits).
    replay_low = replay_session(loaded, budget_override=500.0)
    assert replay_low.budget_t1 < loaded.budget_t1
