"""Test runtime della funzione PL/pgSQL `record_audit_log` e dei 3 trigger AFTER.

Verifica che ogni INSERT/UPDATE/DELETE su `config_overrides` produca
**una riga** in `audit_log` con codice op corretto, actor=session_user e
payload JSONB coerente.

Riferimenti:
- CHG-2026-04-30-018 (audit_log + triggers — funzione installata)
- CHG-2026-04-30-019 (questo test)
- ADR-0015 Allegato A (schema audit_log)
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

pytestmark = pytest.mark.integration


def _max_audit_id(conn: Connection) -> int:
    """Snapshot del MAX(id) corrente di `audit_log`."""
    result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM audit_log")).scalar()
    return int(result or 0)


def _new_audit_rows(conn: Connection, since_id: int, table_name: str) -> list[dict]:
    """Righe `audit_log` create dopo `since_id` per la tabella indicata."""
    rows = (
        conn.execute(
            text(
                "SELECT id, actor, table_name, op, row_id, before_data, after_data "
                "FROM audit_log WHERE id > :since AND table_name = :tbl ORDER BY id"
            ),
            {"since": since_id, "tbl": table_name},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def test_insert_produces_audit_op_i(pg_conn: Connection) -> None:
    snapshot = _max_audit_id(pg_conn)

    inserted = pg_conn.execute(
        text(
            "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
            "VALUES ('global', 'veto_roi_pct', 8, 1) RETURNING id"
        )
    ).scalar()

    audit = _new_audit_rows(pg_conn, snapshot, "config_overrides")
    assert len(audit) == 1
    row = audit[0]
    assert row["op"] == "I"
    assert row["actor"] == "postgres"
    assert row["row_id"] == inserted
    assert row["before_data"] is None
    assert row["after_data"] is not None
    assert row["after_data"]["key"] == "veto_roi_pct"


def test_update_produces_audit_op_u_with_before_and_after(pg_conn: Connection) -> None:
    inserted = pg_conn.execute(
        text(
            "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
            "VALUES ('global', 'veto_roi_pct', 8, 1) RETURNING id"
        )
    ).scalar()
    snapshot = _max_audit_id(pg_conn)

    pg_conn.execute(
        text("UPDATE config_overrides SET value_numeric = 12 WHERE id = :id"),
        {"id": inserted},
    )

    audit = _new_audit_rows(pg_conn, snapshot, "config_overrides")
    assert len(audit) == 1
    row = audit[0]
    assert row["op"] == "U"
    assert row["actor"] == "postgres"
    assert row["row_id"] == inserted
    assert row["before_data"] is not None
    assert row["after_data"] is not None
    assert float(row["before_data"]["value_numeric"]) == 8.0
    assert float(row["after_data"]["value_numeric"]) == 12.0


def test_delete_produces_audit_op_d_with_before_only(pg_conn: Connection) -> None:
    inserted = pg_conn.execute(
        text(
            "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
            "VALUES ('global', 'veto_roi_pct', 8, 1) RETURNING id"
        )
    ).scalar()
    snapshot = _max_audit_id(pg_conn)

    pg_conn.execute(
        text("DELETE FROM config_overrides WHERE id = :id"),
        {"id": inserted},
    )

    audit = _new_audit_rows(pg_conn, snapshot, "config_overrides")
    assert len(audit) == 1
    row = audit[0]
    assert row["op"] == "D"
    assert row["actor"] == "postgres"
    assert row["row_id"] == inserted
    assert row["before_data"] is not None
    assert row["after_data"] is None
    assert row["before_data"]["key"] == "veto_roi_pct"


def test_audit_chain_all_three_ops(pg_conn: Connection) -> None:
    """Test end-to-end: I + U + D producono 3 righe audit nell'ordine giusto."""
    snapshot = _max_audit_id(pg_conn)

    inserted = pg_conn.execute(
        text(
            "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
            "VALUES ('category', 'referral_fee_pct', 15, 1) RETURNING id"
        )
    ).scalar()
    pg_conn.execute(
        text("UPDATE config_overrides SET value_numeric = 17 WHERE id = :id"),
        {"id": inserted},
    )
    pg_conn.execute(
        text("DELETE FROM config_overrides WHERE id = :id"),
        {"id": inserted},
    )

    audit = _new_audit_rows(pg_conn, snapshot, "config_overrides")
    assert [r["op"] for r in audit] == ["I", "U", "D"]
    assert all(r["row_id"] == inserted for r in audit)
