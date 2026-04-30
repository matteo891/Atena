"""Unit test per `talos.persistence.session` (ADR-0015, CHG-2026-04-30-020).

Test puri: usano `sqlite:///:memory:` come engine fittizio. La validazione
di `with_tenant` su `role` non richiede DB (ValueError sollevato prima
dell'execute).
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.persistence import (
    create_app_engine,
    make_session_factory,
    with_tenant,
)
from talos.persistence.session import _is_safe_identifier

pytestmark = pytest.mark.unit


def test_make_session_factory_returns_sessionmaker() -> None:
    engine = create_app_engine("sqlite:///:memory:")
    factory = make_session_factory(engine)
    assert isinstance(factory, sessionmaker)
    session = factory()
    assert isinstance(session, Session)
    assert session.bind is engine
    session.close()


def test_factory_is_expire_on_commit_false() -> None:
    engine = create_app_engine("sqlite:///:memory:")
    factory = make_session_factory(engine)
    session = factory()
    try:
        # Attribute sulla classe Session è `expire_on_commit` (kwargs di sessionmaker).
        assert session.expire_on_commit is False
    finally:
        session.close()


def test_is_safe_identifier_accepts_known_roles() -> None:
    assert _is_safe_identifier("talos_app")
    assert _is_safe_identifier("talos_admin")
    assert _is_safe_identifier("talos_audit")
    assert _is_safe_identifier("role123")


def test_is_safe_identifier_rejects_injection_attempts() -> None:
    assert not _is_safe_identifier("")
    assert not _is_safe_identifier("talos_app; DROP TABLE x")
    assert not _is_safe_identifier("talos_app--")
    assert not _is_safe_identifier("talos app")
    assert not _is_safe_identifier("talos'app")
    assert not _is_safe_identifier('talos"app')
    assert not _is_safe_identifier("rolè")  # non-ASCII


def test_with_tenant_rejects_unsafe_role() -> None:
    engine = create_app_engine("sqlite:///:memory:")
    session = make_session_factory(engine)()
    try:
        with (
            pytest.raises(ValueError, match="Invalid DB role"),
            with_tenant(session, 1, role="talos; DROP TABLE x"),
        ):
            pass  # pragma: no cover — non si arriva qui
    finally:
        session.close()


def test_with_tenant_accepts_int_tenant_id() -> None:
    """Il cast esplicito `int(tenant_id)` rifiuta input non-numerici."""
    engine = create_app_engine("sqlite:///:memory:")
    session = make_session_factory(engine)()
    try:
        with (
            pytest.raises((TypeError, ValueError)),
            with_tenant(session, "1; DROP TABLE x"),  # type: ignore[arg-type]
        ):
            pass  # pragma: no cover
    finally:
        session.close()
