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
def test_base_metadata_no_tables_yet() -> None:
    # In CHG-2026-04-30-007 (skeleton) nessun modello concreto e' stato ancora
    # registrato. Quando arrivera' il primo (es. sessions), questo test
    # diventera' "tables >= 1" via aggiornamento puntuale.
    assert len(Base.metadata.tables) == 0
