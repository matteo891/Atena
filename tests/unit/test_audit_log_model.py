"""Unit test del model `AuditLog` — ADR-0015 Allegato A.

Append-only registry. Trigger AFTER su `storico_ordini`, `locked_in`,
`config_overrides` definiti nella migration `6e03f2a4f5a3`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Text
from sqlalchemy.dialects.postgresql import JSONB

from talos.persistence import AuditLog, Base

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "6e03f2a4f5a3_create_audit_log_with_triggers.py"
)


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert AuditLog.__tablename__ == "audit_log"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "audit_log" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["audit_log"]
    assert set(table.columns.keys()) == {
        "id",
        "actor",
        "table_name",
        "op",
        "row_id",
        "before_data",
        "after_data",
        "at",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint() -> None:
    table = Base.metadata.tables["audit_log"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_no_foreign_keys() -> None:
    """Append-only: no FK formali (lookup via table_name + row_id non vincolato)."""
    table = Base.metadata.tables["audit_log"]
    all_fks = [fk for col in table.columns for fk in col.foreign_keys]
    assert len(all_fks) == 0


@pytest.mark.unit
def test_actor_text_not_null() -> None:
    table = Base.metadata.tables["audit_log"]
    col = table.columns["actor"]
    assert isinstance(col.type, Text)
    assert not col.nullable


@pytest.mark.unit
def test_table_name_text_not_null() -> None:
    table = Base.metadata.tables["audit_log"]
    col = table.columns["table_name"]
    assert isinstance(col.type, Text)
    assert not col.nullable


@pytest.mark.unit
def test_op_char_1_not_null() -> None:
    table = Base.metadata.tables["audit_log"]
    col = table.columns["op"]
    assert isinstance(col.type, CHAR)
    assert col.type.length == 1
    assert not col.nullable


@pytest.mark.unit
def test_row_id_bigint_nullable() -> None:
    table = Base.metadata.tables["audit_log"]
    col = table.columns["row_id"]
    assert isinstance(col.type, BigInteger)
    assert col.nullable


@pytest.mark.unit
def test_before_data_jsonb_nullable() -> None:
    table = Base.metadata.tables["audit_log"]
    col = table.columns["before_data"]
    assert isinstance(col.type, JSONB)
    assert col.nullable


@pytest.mark.unit
def test_after_data_jsonb_nullable() -> None:
    table = Base.metadata.tables["audit_log"]
    col = table.columns["after_data"]
    assert isinstance(col.type, JSONB)
    assert col.nullable


@pytest.mark.unit
def test_at_timestamptz_default_now_not_null() -> None:
    table = Base.metadata.tables["audit_log"]
    col = table.columns["at"]
    assert isinstance(col.type, TIMESTAMP)
    assert col.type.timezone is True
    assert not col.nullable
    assert col.server_default is not None


@pytest.mark.unit
def test_migration_creates_record_audit_log_function() -> None:
    """La migration definisce la funzione PL/pgSQL `record_audit_log()`."""
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE OR REPLACE FUNCTION record_audit_log" in content
    assert "LANGUAGE plpgsql" in content


@pytest.mark.unit
def test_migration_function_handles_three_op_codes() -> None:
    """La funzione mappa TG_OP su 'I'/'U'/'D' come da Allegato A."""
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "WHEN 'INSERT' THEN 'I'" in content
    assert "WHEN 'UPDATE' THEN 'U'" in content
    assert "WHEN 'DELETE' THEN 'D'" in content


@pytest.mark.unit
def test_migration_creates_triggers_on_three_critical_tables() -> None:
    """Trigger AFTER definiti per: storico_ordini, locked_in, config_overrides.

    La migration usa un loop f-string sul tuple `_AUDITED_TABLES`. Verifichiamo
    sia che le 3 tabelle siano elencate nel tuple sia che il pattern del
    CREATE TRIGGER sia presente.
    """
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    for table_name in ("storico_ordini", "locked_in", "config_overrides"):
        assert f'"{table_name}"' in content, (
            f"{table_name} non e' presente in _AUDITED_TABLES nella migration"
        )
    assert "CREATE TRIGGER trg_audit_{table_name}" in content
    assert "AFTER INSERT OR UPDATE OR DELETE ON {table_name}" in content
    assert "EXECUTE FUNCTION record_audit_log()" in content


@pytest.mark.unit
def test_migration_downgrade_drops_triggers_and_function() -> None:
    """Downgrade simmetrico: rimuove trigger + funzione + tabella."""
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "DROP TRIGGER IF EXISTS trg_audit_{table_name}" in content
    assert "DROP FUNCTION IF EXISTS record_audit_log" in content
    # Il loop downgrade itera sullo stesso _AUDITED_TABLES dell'upgrade
    for table_name in ("storico_ordini", "locked_in", "config_overrides"):
        assert f'"{table_name}"' in content


@pytest.mark.unit
def test_construct_minimal_required_fields() -> None:
    instance = AuditLog(
        actor="talos_app",
        table_name="storico_ordini",
        op="I",
    )
    assert instance.actor == "talos_app"
    assert instance.table_name == "storico_ordini"
    assert instance.op == "I"
    assert instance.row_id is None
    assert instance.before_data is None
    assert instance.after_data is None


@pytest.mark.unit
def test_construct_with_jsonb_payload() -> None:
    payload_after = {"id": 123, "asin": "B0CMDRD2QF", "qty": 25}
    instance = AuditLog(
        actor="talos_app",
        table_name="storico_ordini",
        op="I",
        row_id=123,
        before_data=None,
        after_data=payload_after,
    )
    assert instance.row_id == 123
    assert instance.after_data == payload_after
    assert instance.before_data is None


@pytest.mark.unit
def test_construct_update_with_before_and_after() -> None:
    before = {"id": 7, "qty_min": 10}
    after = {"id": 7, "qty_min": 25}
    instance = AuditLog(
        actor="talos_app",
        table_name="locked_in",
        op="U",
        row_id=7,
        before_data=before,
        after_data=after,
    )
    assert instance.op == "U"
    assert instance.before_data == before
    assert instance.after_data == after
