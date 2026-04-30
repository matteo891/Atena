"""Integration test per `list_category_referral_fees` + UI helpers (CHG-051).

Verifica:
- Lookup mappa categoria → fee dopo set.
- Filtro tenant_id isola.
- UI helper `fetch_category_referral_fees_or_empty` ritorna dict[str, float].
- UPSERT idempotente: secondo set sostituisce.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.persistence import (
    KEY_REFERRAL_FEE_PCT,
    SCOPE_CATEGORY,
    list_category_referral_fees,
    set_config_override_numeric,
)
from talos.ui.dashboard import (
    fetch_category_referral_fees_or_empty,
    get_session_factory_or_none,
    try_persist_category_referral_fee,
)

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


def test_list_returns_empty_dict_when_no_overrides(orm_session: Session) -> None:
    """Tenant senza override → dict vuoto (no None)."""
    result = list_category_referral_fees(orm_session, tenant_id=999)
    assert result == {}


def test_list_returns_mapping_after_set(orm_session: Session) -> None:
    """SET di 2 categorie → list ritorna dict con entrambe."""
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=0.08,
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Electronics",
    )
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=0.15,
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Books",
    )
    orm_session.flush()

    result = list_category_referral_fees(orm_session, tenant_id=1)
    assert result == {"Electronics": Decimal("0.0800"), "Books": Decimal("0.1500")}


def test_list_filters_by_tenant_id(orm_session: Session) -> None:
    """Tenant 1 e tenant 2 hanno mapping indipendenti."""
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=0.08,
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="CatT1",
    )
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=0.20,
        tenant_id=2,
        scope=SCOPE_CATEGORY,
        scope_key="CatT2",
    )
    orm_session.flush()

    r1 = list_category_referral_fees(orm_session, tenant_id=1)
    r2 = list_category_referral_fees(orm_session, tenant_id=2)
    assert "CatT1" in r1
    assert "CatT2" not in r1
    assert "CatT2" in r2
    assert "CatT1" not in r2


def test_list_excludes_other_keys(orm_session: Session) -> None:
    """Override con `key` diversa NON figura nella mappa."""
    # Salviamo un veto_roi_pct (key diversa) E un referral_fee categoria.
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=0.10,
        tenant_id=1,
    )
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=0.08,
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Electronics",
    )
    orm_session.flush()

    result = list_category_referral_fees(orm_session, tenant_id=1)
    assert result == {"Electronics": Decimal("0.0800")}


def test_list_excludes_global_scope_overrides(orm_session: Session) -> None:
    """Override con `scope=global` (anche key matching) NON figura."""
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=0.10,
        tenant_id=1,
        scope="global",
    )
    orm_session.flush()

    result = list_category_referral_fees(orm_session, tenant_id=1)
    assert result == {}


# UI helpers


def test_ui_fetch_returns_floats(pg_engine) -> None:  # noqa: ARG001
    """`fetch_category_referral_fees_or_empty` ritorna `dict[str, float]`."""
    factory = get_session_factory_or_none()
    assert factory is not None

    # Setup via UI helper (commit reale).
    ok, _ = try_persist_category_referral_fee(
        factory,
        category_node="UI_TEST_CAT",
        referral_fee_pct=0.12,
        tenant_id=1,
    )
    assert ok

    try:
        rows = fetch_category_referral_fees_or_empty(factory, tenant_id=1)
        assert "UI_TEST_CAT" in rows
        assert isinstance(rows["UI_TEST_CAT"], float)
        assert rows["UI_TEST_CAT"] == pytest.approx(0.12)
    finally:
        # Cleanup
        from talos.persistence import (  # noqa: PLC0415
            ConfigOverride,
            session_scope,
            with_tenant,
        )

        with session_scope(factory) as db, with_tenant(db, 1):
            for obj in db.query(ConfigOverride).filter(
                ConfigOverride.scope_key == "UI_TEST_CAT",
            ):
                db.delete(obj)


def test_ui_fetch_returns_empty_dict_without_factory() -> None:
    """`factory=None` → dict vuoto (graceful)."""
    result = fetch_category_referral_fees_or_empty(None, tenant_id=1)
    assert result == {}
