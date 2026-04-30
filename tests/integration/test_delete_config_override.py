"""Integration test per `delete_config_override` (CHG-2026-04-30-054).

Verifica:
- Cancellazione effettiva di un override esistente.
- Idempotenza: cancellare un override inesistente ritorna False, no errore.
- Round-trip set → delete → get == None.
- Filtro tenant: cancella solo il tenant richiesto.
- Filtro scope_key: NULL vs valore-string distinti.
- Scope invalido → ValueError.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.persistence import (
    KEY_REFERRAL_FEE_PCT,
    SCOPE_CATEGORY,
    SCOPE_GLOBAL,
    delete_config_override,
    get_config_override_numeric,
    set_config_override_numeric,
)
from talos.ui import (
    try_delete_category_referral_fee,
    try_delete_veto_roi_threshold,
    try_persist_category_referral_fee,
    try_persist_veto_roi_threshold,
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


def test_delete_missing_key_returns_false(orm_session: Session) -> None:
    """Cancellare un override non esistente → False, no errore."""
    deleted = delete_config_override(orm_session, key="never_set_key", tenant_id=1)
    assert deleted is False


def test_delete_existing_returns_true_and_get_returns_none(orm_session: Session) -> None:
    """Round-trip: set → delete → get == None."""
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=Decimal("0.10"),
        tenant_id=1,
    )
    assert get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=1) == Decimal(
        "0.10",
    )

    deleted = delete_config_override(orm_session, key="veto_roi_pct", tenant_id=1)
    assert deleted is True

    assert get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=1) is None


def test_delete_filters_by_tenant_id(orm_session: Session) -> None:
    """Cancellazione di tenant=1 NON tocca tenant=2."""
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=Decimal("0.10"),
        tenant_id=1,
    )
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=Decimal("0.12"),
        tenant_id=2,
    )

    delete_config_override(orm_session, key="veto_roi_pct", tenant_id=1)

    assert get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=1) is None
    # Tenant 2 invariato.
    assert get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=2) == Decimal(
        "0.12",
    )


def test_delete_filters_by_scope_key(orm_session: Session) -> None:
    """Cancellare `scope=category, scope_key="Books"` NON tocca `scope_key="Electronics"`."""
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=Decimal("0.05"),
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Books",
    )
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=Decimal("0.20"),
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Electronics",
    )

    deleted = delete_config_override(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Books",
    )
    assert deleted is True

    # Books cancellata.
    assert (
        get_config_override_numeric(
            orm_session,
            key=KEY_REFERRAL_FEE_PCT,
            tenant_id=1,
            scope=SCOPE_CATEGORY,
            scope_key="Books",
        )
        is None
    )
    # Electronics intatta.
    assert get_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Electronics",
    ) == Decimal("0.20")


def test_delete_does_not_touch_global_when_category_targeted(orm_session: Session) -> None:
    """`scope=category, scope_key=NULL` differente da `scope=global, scope_key=NULL`."""
    # Set global con stesso key (caso ipotetico)
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=Decimal("0.10"),
        tenant_id=1,
        scope=SCOPE_GLOBAL,
    )
    set_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        value=Decimal("0.05"),
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Books",
    )

    # Cancella solo la category.
    delete_config_override(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        tenant_id=1,
        scope=SCOPE_CATEGORY,
        scope_key="Books",
    )

    # Global intatta.
    assert get_config_override_numeric(
        orm_session,
        key=KEY_REFERRAL_FEE_PCT,
        tenant_id=1,
        scope=SCOPE_GLOBAL,
    ) == Decimal("0.10")


def test_delete_invalid_scope_raises(orm_session: Session) -> None:
    """scope non ammesso → ValueError."""
    with pytest.raises(ValueError, match="scope invalido"):
        delete_config_override(orm_session, key="x", scope="invalid_scope", tenant_id=1)


def test_ui_helper_try_delete_veto_roi_threshold(pg_engine: Engine) -> None:
    """UI helper `try_delete_veto_roi_threshold` rimuove l'override."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)

    # Crea override (commit interno via session_scope).
    ok_save, _ = try_persist_veto_roi_threshold(factory, threshold=0.11, tenant_id=99)
    assert ok_save is True

    # Reset.
    ok_del, err_del = try_delete_veto_roi_threshold(factory, tenant_id=99)
    assert ok_del is True
    assert err_del is None

    # Verifica via API base.
    sess = factory()
    try:
        assert get_config_override_numeric(sess, key="veto_roi_pct", tenant_id=99) is None
    finally:
        # Cleanup paranoid (in caso di re-run con stato precedente).
        delete_config_override(sess, key="veto_roi_pct", tenant_id=99)
        sess.commit()
        sess.close()


def test_ui_helper_try_delete_category_referral_fee(pg_engine: Engine) -> None:
    """UI helper `try_delete_category_referral_fee` rimuove un override per categoria."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)

    ok_save, _ = try_persist_category_referral_fee(
        factory,
        category_node="TestCategoryDeletable",
        referral_fee_pct=0.07,
        tenant_id=99,
    )
    assert ok_save is True

    ok_del, err_del = try_delete_category_referral_fee(
        factory,
        category_node="TestCategoryDeletable",
        tenant_id=99,
    )
    assert ok_del is True
    assert err_del is None

    sess = factory()
    try:
        # Verifica + cleanup paranoid.
        assert (
            get_config_override_numeric(
                sess,
                key=KEY_REFERRAL_FEE_PCT,
                tenant_id=99,
                scope=SCOPE_CATEGORY,
                scope_key="TestCategoryDeletable",
            )
            is None
        )
    finally:
        delete_config_override(
            sess,
            key=KEY_REFERRAL_FEE_PCT,
            tenant_id=99,
            scope=SCOPE_CATEGORY,
            scope_key="TestCategoryDeletable",
        )
        sess.commit()
        sess.close()
