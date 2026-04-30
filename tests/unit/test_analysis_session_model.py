"""Unit test del model `AnalysisSession` — ADR-0015 Allegato A."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Integer, Numeric

from talos.persistence import AnalysisSession, Base


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert AnalysisSession.__tablename__ == "sessions"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "sessions" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["sessions"]
    assert set(table.columns.keys()) == {
        "id",
        "started_at",
        "ended_at",
        "budget_eur",
        "velocity_target",
        "listino_hash",
        "tenant_id",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint_autoincrement() -> None:
    table = Base.metadata.tables["sessions"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_listino_hash_is_char_64() -> None:
    table = Base.metadata.tables["sessions"]
    col = table.columns["listino_hash"]
    assert isinstance(col.type, CHAR)
    assert col.type.length == 64
    assert not col.nullable


@pytest.mark.unit
def test_budget_eur_is_numeric_12_2_required() -> None:
    table = Base.metadata.tables["sessions"]
    col = table.columns["budget_eur"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 12
    assert col.type.scale == 2
    assert not col.nullable


@pytest.mark.unit
def test_velocity_target_default_15() -> None:
    table = Base.metadata.tables["sessions"]
    col = table.columns["velocity_target"]
    assert isinstance(col.type, Integer)
    assert not col.nullable
    # `server_default` è oggetto Alembic-friendly: confronto su .arg.text
    assert col.server_default is not None
    assert "15" in str(col.server_default.arg)


@pytest.mark.unit
def test_tenant_id_default_1_for_mvp_single_tenant() -> None:
    table = Base.metadata.tables["sessions"]
    col = table.columns["tenant_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    assert col.server_default is not None
    assert "1" in str(col.server_default.arg)


@pytest.mark.unit
def test_ended_at_nullable() -> None:
    table = Base.metadata.tables["sessions"]
    col = table.columns["ended_at"]
    assert isinstance(col.type, TIMESTAMP)
    assert col.type.timezone is True
    assert col.nullable


@pytest.mark.unit
def test_decimal_type_compatibility() -> None:
    """Verifica che mypy + runtime accettino Decimal su budget_eur."""
    # Solo verifica di tipo runtime: non istanzia il model con engine,
    # ma controlla che assegnare un Decimal non sollevi a costruzione attributo.
    instance = AnalysisSession(
        budget_eur=Decimal("10000.00"),
        listino_hash="a" * 64,
    )
    assert instance.budget_eur == Decimal("10000.00")
    assert instance.listino_hash == "a" * 64
