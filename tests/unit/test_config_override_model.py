"""Unit test del model `ConfigOverride` — ADR-0015 Allegato A.

Prima tabella con RLS Zero-Trust + indice UNIQUE composito a 4 colonne.
Le verifiche sulla policy RLS effettiva (filtro per `current_setting`)
richiedono Postgres reale e saranno aggiunte in `tests/integration/`
quando arriverà Docker.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import TIMESTAMP, BigInteger, Numeric, Text

from talos.persistence import Base, ConfigOverride

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "027a145f76a8_create_config_overrides_with_rls.py"
)


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert ConfigOverride.__tablename__ == "config_overrides"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "config_overrides" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["config_overrides"]
    assert set(table.columns.keys()) == {
        "id",
        "scope",
        "scope_key",
        "key",
        "value_numeric",
        "value_text",
        "updated_at",
        "tenant_id",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint_autoincrement() -> None:
    table = Base.metadata.tables["config_overrides"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_scope_and_key_text_not_null() -> None:
    table = Base.metadata.tables["config_overrides"]
    for col_name in ("scope", "key"):
        col = table.columns[col_name]
        assert isinstance(col.type, Text), f"{col_name} type"
        assert not col.nullable, f"{col_name} should be NOT NULL"


@pytest.mark.unit
def test_value_columns_nullable() -> None:
    table = Base.metadata.tables["config_overrides"]
    col_text = table.columns["value_text"]
    assert isinstance(col_text.type, Text)
    assert col_text.nullable

    col_num = table.columns["value_numeric"]
    assert isinstance(col_num.type, Numeric)
    assert col_num.type.precision == 12
    assert col_num.type.scale == 4
    assert col_num.nullable


@pytest.mark.unit
def test_scope_key_nullable_text() -> None:
    table = Base.metadata.tables["config_overrides"]
    col = table.columns["scope_key"]
    assert isinstance(col.type, Text)
    assert col.nullable


@pytest.mark.unit
def test_updated_at_timestamptz_default_now_not_null() -> None:
    table = Base.metadata.tables["config_overrides"]
    col = table.columns["updated_at"]
    assert isinstance(col.type, TIMESTAMP)
    assert col.type.timezone is True
    assert not col.nullable
    assert col.server_default is not None


@pytest.mark.unit
def test_tenant_id_default_1_not_null() -> None:
    table = Base.metadata.tables["config_overrides"]
    col = table.columns["tenant_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    assert col.server_default is not None
    assert "1" in str(col.server_default.arg)


@pytest.mark.unit
def test_unique_composite_index_present() -> None:
    """idx_config_unique deve essere UNIQUE su (tenant_id, scope, scope_key, key)."""
    table = Base.metadata.tables["config_overrides"]
    indexes = {idx.name: idx for idx in table.indexes}
    assert "idx_config_unique" in indexes
    idx = indexes["idx_config_unique"]
    assert idx.unique is True, "indice deve essere UNIQUE (Allegato A)"
    cols = [c.name for c in idx.columns]
    assert cols == ["tenant_id", "scope", "scope_key", "key"], (
        "ordine colonne dell'indice deve combaciare con Allegato A"
    )


@pytest.mark.unit
def test_construct_with_global_scope_numeric_value() -> None:
    instance = ConfigOverride(
        scope="global",
        key="veto_roi_pct",
        value_numeric=Decimal("0.0800"),
    )
    assert instance.scope == "global"
    assert instance.key == "veto_roi_pct"
    assert instance.value_numeric == Decimal("0.0800")
    assert instance.scope_key is None
    assert instance.value_text is None


@pytest.mark.unit
def test_construct_with_asin_scope() -> None:
    instance = ConfigOverride(
        scope="asin",
        scope_key="B0CMDRD2QF",
        key="referral_fee_pct",
        value_numeric=Decimal("0.0850"),
    )
    assert instance.scope == "asin"
    assert instance.scope_key == "B0CMDRD2QF"
    assert instance.key == "referral_fee_pct"


@pytest.mark.unit
def test_migration_file_contains_rls_enable() -> None:
    """Verifica statica: la migration accende RLS sulla tabella."""
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in content


@pytest.mark.unit
def test_migration_file_contains_tenant_isolation_policy() -> None:
    """Verifica statica: la policy `tenant_isolation` è definita nella migration."""
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE POLICY tenant_isolation" in content
    assert "current_setting('talos.tenant_id'" in content


@pytest.mark.unit
def test_migration_file_downgrade_drops_policy_and_disables_rls() -> None:
    """Verifica statica: il downgrade rimuove policy e RLS coerentemente."""
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "DROP POLICY IF EXISTS tenant_isolation" in content
    assert "DISABLE ROW LEVEL SECURITY" in content
