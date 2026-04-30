"""Unit test per `talos.persistence.engine` (ADR-0015, CHG-2026-04-30-020).

Test puri (no I/O verso DB reale): usano `sqlite:///:memory:` come URL
test-only — `create_engine` non apre connessioni finché non serve.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text

from talos.persistence import create_app_engine

pytestmark = pytest.mark.unit


def test_explicit_url_takes_priority_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TALOS_DB_URL", "postgresql+psycopg://envvar:x@h/db")
    engine = create_app_engine("sqlite:///:memory:")
    assert isinstance(engine, Engine)
    assert engine.url.drivername == "sqlite"


def test_env_fallback_when_no_explicit_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TALOS_DB_URL", "sqlite:///:memory:")
    engine = create_app_engine()
    assert isinstance(engine, Engine)
    assert engine.url.drivername == "sqlite"


def test_raises_when_no_url_anywhere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TALOS_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="TALOS_DB_URL"):
        create_app_engine()


def test_engine_can_connect_to_sqlite_memory() -> None:
    """Smoke: l'engine prodotto è effettivamente utilizzabile."""
    engine = create_app_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
    engine.dispose()
