"""Unit test del model `CartItem` — ADR-0015 Allegato A."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, Boolean, Integer, Numeric

from talos.persistence import AnalysisSession, Base, CartItem, VgpResult

if TYPE_CHECKING:
    from sqlalchemy.schema import ForeignKey


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert CartItem.__tablename__ == "cart_items"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "cart_items" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["cart_items"]
    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "vgp_result_id",
        "qty",
        "unit_cost_eur",
        "locked_in",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint() -> None:
    table = Base.metadata.tables["cart_items"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_session_id_fk_cascade_required() -> None:
    table = Base.metadata.tables["cart_items"]
    col = table.columns["session_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk: ForeignKey = fks[0]
    assert fk.column.table.name == "sessions"
    assert fk.column.name == "id"
    assert fk.ondelete == "CASCADE"


@pytest.mark.unit
def test_vgp_result_id_fk_cascade_required() -> None:
    table = Base.metadata.tables["cart_items"]
    col = table.columns["vgp_result_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk: ForeignKey = fks[0]
    assert fk.column.table.name == "vgp_results"
    assert fk.column.name == "id"
    assert fk.ondelete == "CASCADE"


@pytest.mark.unit
def test_qty_int_not_null() -> None:
    table = Base.metadata.tables["cart_items"]
    col = table.columns["qty"]
    assert isinstance(col.type, Integer)
    assert not col.nullable


@pytest.mark.unit
def test_unit_cost_eur_numeric_12_2_not_null() -> None:
    table = Base.metadata.tables["cart_items"]
    col = table.columns["unit_cost_eur"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 12
    assert col.type.scale == 2
    assert not col.nullable


@pytest.mark.unit
def test_locked_in_boolean_default_false_not_null() -> None:
    """R-04 Manual Override: default false, NOT NULL (regola CHG-010)."""
    table = Base.metadata.tables["cart_items"]
    col = table.columns["locked_in"]
    assert isinstance(col.type, Boolean)
    assert not col.nullable
    assert col.server_default is not None
    assert "false" in str(col.server_default.arg).lower()


@pytest.mark.unit
def test_relationship_session_back_populates_cart_items() -> None:
    item_rel = CartItem.__mapper__.relationships["session"]
    assert item_rel.mapper.class_ is AnalysisSession
    assert item_rel.back_populates == "cart_items"

    session_rel = AnalysisSession.__mapper__.relationships["cart_items"]
    assert session_rel.mapper.class_ is CartItem
    assert session_rel.back_populates == "session"
    assert session_rel.passive_deletes is True


@pytest.mark.unit
def test_relationship_vgp_result_back_populates_cart_items() -> None:
    item_rel = CartItem.__mapper__.relationships["vgp_result"]
    assert item_rel.mapper.class_ is VgpResult
    assert item_rel.back_populates == "cart_items"

    vgp_rel = VgpResult.__mapper__.relationships["cart_items"]
    assert vgp_rel.mapper.class_ is CartItem
    assert vgp_rel.back_populates == "vgp_result"
    assert vgp_rel.passive_deletes is True


@pytest.mark.unit
def test_construct_minimal_required_fields() -> None:
    instance = CartItem(
        session_id=42,
        vgp_result_id=123,
        qty=25,
        unit_cost_eur=Decimal("450.00"),
    )
    assert instance.session_id == 42
    assert instance.vgp_result_id == 123
    assert instance.qty == 25
    assert instance.unit_cost_eur == Decimal("450.00")


@pytest.mark.unit
def test_construct_with_locked_in_true() -> None:
    """R-04: lock-in manuale del CFO."""
    instance = CartItem(
        session_id=42,
        vgp_result_id=123,
        qty=10,
        unit_cost_eur=Decimal("450.00"),
        locked_in=True,
    )
    assert instance.locked_in is True
