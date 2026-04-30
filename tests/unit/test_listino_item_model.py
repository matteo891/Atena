"""Unit test del model `ListinoItem` — ADR-0015 Allegato A.

Primo modello con FK: verifica corretta integrazione SQLAlchemy 2.0
(ForeignKey + relationship bidirezionale + ON DELETE CASCADE a livello DB).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import CHAR, BigInteger, Integer, Numeric, Text

from talos.persistence import AnalysisSession, Base, ListinoItem

if TYPE_CHECKING:
    from sqlalchemy.schema import ForeignKey


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert ListinoItem.__tablename__ == "listino_items"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "listino_items" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["listino_items"]
    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "asin",
        "raw_title",
        "cost_eur",
        "qty_available",
        "match_status",
        "match_reason",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint() -> None:
    table = Base.metadata.tables["listino_items"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_session_id_is_required_foreign_key_with_cascade() -> None:
    table = Base.metadata.tables["listino_items"]
    col = table.columns["session_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    fks = list(col.foreign_keys)
    assert len(fks) == 1, "session_id deve avere esattamente una FK"
    fk: ForeignKey = fks[0]
    assert fk.column.table.name == "sessions", "FK target table"
    assert fk.column.name == "id", "FK target column"
    assert fk.ondelete == "CASCADE", "ON DELETE CASCADE richiesto da Allegato A"


@pytest.mark.unit
def test_asin_nullable_no_foreign_key() -> None:
    """Allegato A: `asin CHAR(10)` nullable senza FK (match in-flight)."""
    table = Base.metadata.tables["listino_items"]
    col = table.columns["asin"]
    assert isinstance(col.type, CHAR)
    assert col.type.length == 10
    assert col.nullable
    assert len(list(col.foreign_keys)) == 0, "asin non deve avere FK (Allegato A letterale)"


@pytest.mark.unit
def test_raw_title_text_not_null() -> None:
    table = Base.metadata.tables["listino_items"]
    col = table.columns["raw_title"]
    assert isinstance(col.type, Text)
    assert not col.nullable


@pytest.mark.unit
def test_cost_eur_numeric_12_2_not_null() -> None:
    table = Base.metadata.tables["listino_items"]
    col = table.columns["cost_eur"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 12
    assert col.type.scale == 2
    assert not col.nullable


@pytest.mark.unit
def test_optional_columns_nullable() -> None:
    table = Base.metadata.tables["listino_items"]
    for col_name in ("qty_available", "match_status", "match_reason"):
        col = table.columns[col_name]
        assert col.nullable, f"{col_name} should be NULL"
    # type spot-check
    assert isinstance(table.columns["qty_available"].type, Integer)
    assert isinstance(table.columns["match_status"].type, Text)
    assert isinstance(table.columns["match_reason"].type, Text)


@pytest.mark.unit
def test_index_idx_listino_session_exists() -> None:
    table = Base.metadata.tables["listino_items"]
    indexes = {idx.name: idx for idx in table.indexes}
    assert "idx_listino_session" in indexes
    cols = [c.name for c in indexes["idx_listino_session"].columns]
    assert cols == ["session_id"]


@pytest.mark.unit
def test_relationship_session_back_populates_listino_items() -> None:
    """Verifica relationship bidirezionale ListinoItem.session ↔ AnalysisSession.listino_items."""
    item_rel = ListinoItem.__mapper__.relationships["session"]
    assert item_rel.mapper.class_ is AnalysisSession
    assert item_rel.back_populates == "listino_items"

    session_rel = AnalysisSession.__mapper__.relationships["listino_items"]
    assert session_rel.mapper.class_ is ListinoItem
    assert session_rel.back_populates == "session"
    # Cascade DB-side: passive_deletes=True (lato ORM evita doppia logica)
    assert session_rel.passive_deletes is True


@pytest.mark.unit
def test_construct_minimal_required_fields() -> None:
    instance = ListinoItem(
        session_id=42,
        raw_title="Samsung Galaxy S24 5G 128GB Nero",
        cost_eur=Decimal("450.00"),
    )
    assert instance.session_id == 42
    assert instance.raw_title == "Samsung Galaxy S24 5G 128GB Nero"
    assert instance.cost_eur == Decimal("450.00")
    # Optional fields default a None
    assert instance.asin is None
    assert instance.qty_available is None
    assert instance.match_status is None
