"""Session factory + context manager per app Talos (ADR-0015).

Tre primitive pubbliche:
- `make_session_factory(engine)` → `sessionmaker[Session]` configurato.
- `session_scope(factory)` → context manager con commit/rollback/close.
- `with_tenant(session, tenant_id, *, role=None)` → context manager
  tx-scoped che imposta `talos.tenant_id` (e opzionalmente il `ROLE`).

`with_tenant` è la primitiva Zero-Trust di ADR-0015: tutte le tabelle con
RLS (`config_overrides`, `locked_in`, `storico_ordini`) usano la policy
`USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)`.
Senza un `SET LOCAL talos.tenant_id`, la policy filtra a 0 righe (NULL ≠ N).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """sessionmaker(future=True, expire_on_commit=False).

    `expire_on_commit=False`: dopo `commit()` gli oggetti restano leggibili
    senza re-fetch. Più ergonomico per UI/test; chi vuole valori "freschi"
    può chiamare `session.refresh(obj)` esplicitamente.
    """
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def session_scope(
    factory: sessionmaker[Session],
) -> Iterator[Session]:
    """Apre una sessione, commit on success, rollback on exception, close.

    Pattern atteso::

        with session_scope(SessionLocal) as session:
            session.add(obj)
            # commit automatico all'uscita

    L'oggetto `Session` SQLAlchemy 2.0 apre la transazione lazy alla prima
    esecuzione. `with_tenant` può essere innestato per impostare il tenant.
    """
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _is_safe_identifier(value: str) -> bool:
    """Whitelist anti-injection per identificatori SQL (role name).

    Accetta alfanumerico ASCII + underscore, non vuoto. Sufficiente per i
    3 ruoli previsti da ADR-0015 (`talos_app`, `talos_admin`, `talos_audit`).
    """
    return bool(value) and all(c.isalnum() or c == "_" for c in value) and value.isascii()


@contextmanager
def with_tenant(
    session: Session,
    tenant_id: int,
    *,
    role: str | None = None,
) -> Iterator[Session]:
    """Imposta `talos.tenant_id` (e opzionalmente `ROLE`) per la transazione.

    `SET LOCAL` è tx-scoped: il valore muore al commit/rollback. Il caller
    tipico userà `with_tenant` **dentro** un `session_scope`, ottenendo
    cleanup gratis. Se la sessione non ha tx aperta, la apre con
    `session.begin()`.

    `role=None` (default dev/test): non cambia ruolo. La sessione resta
    sull'utente di connessione (es. `postgres` superuser in locale, che
    bypassa RLS — vedi CHG-2026-04-30-019).
    `role='talos_app'` (uso prod, post bootstrap ruoli): switch al ruolo
    applicativo NOSUPERUSER NOBYPASSRLS, abilitando l'enforcement effettivo
    della policy `tenant_isolation`.

    `tenant_id` viene cast a `int` (anti-injection); `role` passa per
    whitelist `_is_safe_identifier`.
    """
    tid = int(tenant_id)
    if role is not None and not _is_safe_identifier(role):
        msg = f"Invalid DB role identifier: {role!r}"
        raise ValueError(msg)
    if not session.in_transaction():
        session.begin()
    session.execute(text(f"SET LOCAL talos.tenant_id = '{tid}'"))
    if role is not None:
        session.execute(text(f"SET LOCAL ROLE {role}"))
    yield session
