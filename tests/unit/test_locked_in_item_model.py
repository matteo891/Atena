"""Unit test del model `LockedInItem` — ADR-0015 Allegato A.

Standalone (no FK), RLS Zero-Trust attiva. R-04 Manual Override.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Integer, Text

from talos.persistence import Base, LockedInItem

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "e7a92c0260fa_create_locked_in_with_rls.py"
)


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert LockedInItem.__tablename__ == "locked_in"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "locked_in" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["locked_in"]
    assert set(table.columns.keys()) == {
        "id",
        "asin",
        "qty_min",
        "notes",
        "created_at",
        "tenant_id",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint() -> None:
    table = Base.metadata.tables["locked_in"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_no_foreign_keys() -> None:
    """Standalone: l'Allegato A non dichiara FK su locked_in."""
    table = Base.metadata.tables["locked_in"]
    all_fks = [fk for col in table.columns for fk in col.foreign_keys]
    assert len(all_fks) == 0


@pytest.mark.unit
def test_asin_char_10_not_null() -> None:
    table = Base.metadata.tables["locked_in"]
    col = table.columns["asin"]
    assert isinstance(col.type, CHAR)
    assert col.type.length == 10
    assert not col.nullable


@pytest.mark.unit
def test_qty_min_int_not_null() -> None:
    table = Base.metadata.tables["locked_in"]
    col = table.columns["qty_min"]
    assert isinstance(col.type, Integer)
    assert not col.nullable


@pytest.mark.unit
def test_notes_text_nullable() -> None:
    table = Base.metadata.tables["locked_in"]
    col = table.columns["notes"]
    assert isinstance(col.type, Text)
    assert col.nullable


@pytest.mark.unit
def test_created_at_timestamptz_default_now_not_null() -> None:
    table = Base.metadata.tables["locked_in"]
    col = table.columns["created_at"]
    assert isinstance(col.type, TIMESTAMP)
    assert col.type.timezone is True
    assert not col.nullable
    assert col.server_default is not None


@pytest.mark.unit
def test_tenant_id_default_1_not_null() -> None:
    table = Base.metadata.tables["locked_in"]
    col = table.columns["tenant_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    assert col.server_default is not None
    assert "1" in str(col.server_default.arg)


@pytest.mark.unit
def test_migration_file_contains_rls_enable() -> None:
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in content


@pytest.mark.unit
def test_migration_file_contains_tenant_isolation_policy() -> None:
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE POLICY tenant_isolation" in content
    assert "current_setting('talos.tenant_id'" in content


@pytest.mark.unit
def test_migration_file_downgrade_drops_policy_and_disables_rls() -> None:
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "DROP POLICY IF EXISTS tenant_isolation" in content
    assert "DISABLE ROW LEVEL SECURITY" in content


@pytest.mark.unit
def test_construct_minimal_required_fields() -> None:
    instance = LockedInItem(
        asin="B0CMDRD2QF",
        qty_min=10,
    )
    assert instance.asin == "B0CMDRD2QF"
    assert instance.qty_min == 10
    assert instance.notes is None


@pytest.mark.unit
def test_construct_with_notes() -> None:
    instance = LockedInItem(
        asin="B0CMDRD2QF",
        qty_min=25,
        notes="Cliente VIP, mantenere sempre disponibile",
    )
    assert instance.notes == "Cliente VIP, mantenere sempre disponibile"
