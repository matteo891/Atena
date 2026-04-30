"""Integration test per `build_session_input` (CHG-2026-04-30-055).

Verifica che la UI helper carichi gli override `referral_fee_pct` per
categoria dal DB e li propaghi a `SessionInput.referral_fee_overrides`.
Quando il listino include `category_node`, il run_session a valle deve
usare gli override (audit trail su `referral_fee_resolved`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import (
    CATEGORY_NODE_COLUMN,
    REQUIRED_INPUT_COLUMNS,
    SessionInput,
    run_session,
)
from talos.persistence import (
    KEY_REFERRAL_FEE_PCT,
    SCOPE_CATEGORY,
    delete_config_override,
    set_config_override_numeric,
)
from talos.ui import build_session_input

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


def _listino_with_category() -> pd.DataFrame:
    """Mini-listino con `category_node`."""
    cols = [*REQUIRED_INPUT_COLUMNS, CATEGORY_NODE_COLUMN]
    return pd.DataFrame(
        [
            ("BS01", 200.0, 100.0, 0.08, 50.0, 1, "MATCH", "Books"),
            ("EL02", 500.0, 300.0, 0.15, 30.0, 1, "MATCH", "Electronics"),
        ],
        columns=cols,
    )


def test_build_session_input_with_factory_none_passes_no_overrides() -> None:
    """factory=None → SessionInput.referral_fee_overrides=None (graceful)."""
    inp = build_session_input(
        None,
        _listino_with_category(),
        budget=10_000.0,
        locked_in=[],
        velocity_target_days=15,
        veto_roi_threshold=0.08,
        lot_size=5,
    )
    assert isinstance(inp, SessionInput)
    assert inp.referral_fee_overrides is None


def test_build_session_input_loads_overrides_from_db(pg_engine: Engine) -> None:
    """Con override DB salvati → SessionInput.referral_fee_overrides popolato."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    tenant_id = 77

    # Setup: salva 1 override per "Books".
    sess = factory()
    try:
        set_config_override_numeric(
            sess,
            key=KEY_REFERRAL_FEE_PCT,
            value=0.04,
            tenant_id=tenant_id,
            scope=SCOPE_CATEGORY,
            scope_key="Books",
        )
        sess.commit()
    finally:
        sess.close()

    try:
        inp = build_session_input(
            factory,
            _listino_with_category(),
            budget=10_000.0,
            locked_in=[],
            velocity_target_days=15,
            veto_roi_threshold=0.08,
            lot_size=5,
            tenant_id=tenant_id,
        )
        assert inp.referral_fee_overrides is not None
        assert "Books" in inp.referral_fee_overrides
        assert inp.referral_fee_overrides["Books"] == pytest.approx(0.04)

        # End-to-end: run_session usa l'override per "Books".
        result = run_session(inp)
        enriched = result.enriched_df.set_index("asin")
        assert enriched.loc["BS01", "referral_fee_resolved"] == pytest.approx(0.04)
        # "Electronics" non in override → fallback raw 0.15
        assert enriched.loc["EL02", "referral_fee_resolved"] == pytest.approx(0.15)
    finally:
        # Cleanup paranoid.
        sess = factory()
        try:
            delete_config_override(
                sess,
                key=KEY_REFERRAL_FEE_PCT,
                tenant_id=tenant_id,
                scope=SCOPE_CATEGORY,
                scope_key="Books",
            )
            sess.commit()
        finally:
            sess.close()


def test_build_session_input_empty_overrides_dict_normalized_to_none(pg_engine: Engine) -> None:
    """tenant senza override → DB ritorna {} → SessionInput.referral_fee_overrides=None."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    inp = build_session_input(
        factory,
        _listino_with_category(),
        budget=10_000.0,
        locked_in=[],
        velocity_target_days=15,
        veto_roi_threshold=0.08,
        lot_size=5,
        tenant_id=88_888,  # tenant inesistente, no override registrati
    )
    assert inp.referral_fee_overrides is None
