"""Unit test del model `AsinMaster` — ADR-0015 Allegato A."""

from __future__ import annotations

import pytest
from sqlalchemy import CHAR, TIMESTAMP, Boolean, Integer, Text

from talos.persistence import AsinMaster, Base


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert AsinMaster.__tablename__ == "asin_master"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "asin_master" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["asin_master"]
    assert set(table.columns.keys()) == {
        "asin",
        "title",
        "brand",
        "model",
        "rom_gb",
        "ram_gb",
        "connectivity",
        "color_family",
        "enterprise",
        "category_node",
        "last_seen_at",
    }


@pytest.mark.unit
def test_primary_key_is_asin_char_10() -> None:
    table = Base.metadata.tables["asin_master"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "asin"
    assert isinstance(pk_cols[0].type, CHAR)
    assert pk_cols[0].type.length == 10


@pytest.mark.unit
def test_title_and_brand_not_null() -> None:
    table = Base.metadata.tables["asin_master"]
    for col_name in ("title", "brand"):
        col = table.columns[col_name]
        assert isinstance(col.type, Text), f"{col_name} type"
        assert not col.nullable, f"{col_name} should be NOT NULL"


@pytest.mark.unit
def test_optional_anagrafica_columns_nullable() -> None:
    table = Base.metadata.tables["asin_master"]
    for col_name in ("model", "connectivity", "color_family", "category_node"):
        col = table.columns[col_name]
        assert isinstance(col.type, Text), f"{col_name} type"
        assert col.nullable, f"{col_name} should be NULL"


@pytest.mark.unit
def test_rom_ram_int_nullable() -> None:
    table = Base.metadata.tables["asin_master"]
    for col_name in ("rom_gb", "ram_gb"):
        col = table.columns[col_name]
        assert isinstance(col.type, Integer), f"{col_name} type"
        assert col.nullable, f"{col_name} should be NULL"


@pytest.mark.unit
def test_enterprise_boolean_default_false_not_null() -> None:
    table = Base.metadata.tables["asin_master"]
    col = table.columns["enterprise"]
    assert isinstance(col.type, Boolean)
    assert not col.nullable
    assert col.server_default is not None
    assert "false" in str(col.server_default.arg).lower()


@pytest.mark.unit
def test_last_seen_at_timestamptz_default_now() -> None:
    table = Base.metadata.tables["asin_master"]
    col = table.columns["last_seen_at"]
    assert isinstance(col.type, TIMESTAMP)
    assert col.type.timezone is True
    assert not col.nullable
    assert col.server_default is not None


@pytest.mark.unit
def test_index_idx_asin_brand_model_exists() -> None:
    table = Base.metadata.tables["asin_master"]
    indexes = {idx.name: idx for idx in table.indexes}
    assert "idx_asin_brand_model" in indexes
    idx = indexes["idx_asin_brand_model"]
    cols = [c.name for c in idx.columns]
    assert cols == ["brand", "model"]


@pytest.mark.unit
def test_construct_minimal_required_fields() -> None:
    """Verifica costruzione runtime con i soli campi obbligatori."""
    instance = AsinMaster(
        asin="B0CMDRD2QF",
        title="Samsung Galaxy S24 5G 128GB",
        brand="Samsung",
    )
    assert instance.asin == "B0CMDRD2QF"
    assert instance.title == "Samsung Galaxy S24 5G 128GB"
    assert instance.brand == "Samsung"
