"""Unit test skeleton persistence (ADR-0015).

Verifiche di base sulla declarative base SQLAlchemy 2.0. I modelli concreti
saranno aggiunti uno alla volta in CHG dedicati con la corrispondente
revision Alembic.
"""

from __future__ import annotations

import pytest
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from talos.persistence import Base


@pytest.mark.unit
def test_base_subclasses_declarative_base() -> None:
    assert issubclass(Base, DeclarativeBase)


@pytest.mark.unit
def test_base_has_metadata() -> None:
    assert isinstance(Base.metadata, MetaData)


@pytest.mark.unit
def test_base_metadata_has_registered_tables() -> None:
    # CHG-2026-04-30-008 introduce il primo modello concreto (`sessions`).
    # La soglia minima di tabelle registrate cresce con ogni CHG modello.
    assert len(Base.metadata.tables) >= 1
    assert "sessions" in Base.metadata.tables
