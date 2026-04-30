"""Unit test del model `PanchinaItem` — ADR-0015 Allegato A."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, Integer

from talos.persistence import AnalysisSession, Base, PanchinaItem, VgpResult

if TYPE_CHECKING:
    from sqlalchemy.schema import ForeignKey


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert PanchinaItem.__tablename__ == "panchina_items"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "panchina_items" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["panchina_items"]
    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "vgp_result_id",
        "qty_proposed",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint() -> None:
    table = Base.metadata.tables["panchina_items"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_session_id_fk_cascade_required() -> None:
    table = Base.metadata.tables["panchina_items"]
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
    table = Base.metadata.tables["panchina_items"]
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
def test_qty_proposed_int_not_null() -> None:
    table = Base.metadata.tables["panchina_items"]
    col = table.columns["qty_proposed"]
    assert isinstance(col.type, Integer)
    assert not col.nullable


@pytest.mark.unit
def test_relationship_session_back_populates_panchina_items() -> None:
    item_rel = PanchinaItem.__mapper__.relationships["session"]
    assert item_rel.mapper.class_ is AnalysisSession
    assert item_rel.back_populates == "panchina_items"

    session_rel = AnalysisSession.__mapper__.relationships["panchina_items"]
    assert session_rel.mapper.class_ is PanchinaItem
    assert session_rel.back_populates == "session"
    assert session_rel.passive_deletes is True


@pytest.mark.unit
def test_relationship_vgp_result_back_populates_panchina_items() -> None:
    item_rel = PanchinaItem.__mapper__.relationships["vgp_result"]
    assert item_rel.mapper.class_ is VgpResult
    assert item_rel.back_populates == "panchina_items"

    vgp_rel = VgpResult.__mapper__.relationships["panchina_items"]
    assert vgp_rel.mapper.class_ is PanchinaItem
    assert vgp_rel.back_populates == "vgp_result"
    assert vgp_rel.passive_deletes is True


@pytest.mark.unit
def test_construct_minimal_required_fields() -> None:
    instance = PanchinaItem(
        session_id=42,
        vgp_result_id=123,
        qty_proposed=15,
    )
    assert instance.session_id == 42
    assert instance.vgp_result_id == 123
    assert instance.qty_proposed == 15
