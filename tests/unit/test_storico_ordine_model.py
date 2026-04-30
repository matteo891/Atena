"""Unit test del model `StoricoOrdine` — ADR-0015 Allegato A.

Registro permanente: le FK NON hanno ON DELETE CASCADE (aderenza letterale).
RLS Zero-Trust attiva tramite policy `tenant_isolation`.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Integer, Numeric

from talos.persistence import AnalysisSession, Base, CartItem, StoricoOrdine

if TYPE_CHECKING:
    from sqlalchemy.schema import ForeignKey

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "a074ee67895c_create_storico_ordini_with_rls.py"
)


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert StoricoOrdine.__tablename__ == "storico_ordini"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "storico_ordini" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["storico_ordini"]
    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "cart_item_id",
        "asin",
        "qty",
        "unit_cost_eur",
        "ordered_at",
        "tenant_id",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint() -> None:
    table = Base.metadata.tables["storico_ordini"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_session_id_fk_has_no_cascade() -> None:
    """Aderenza letterale Allegato A: NO ON DELETE CASCADE (registro permanente)."""
    table = Base.metadata.tables["storico_ordini"]
    col = table.columns["session_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk: ForeignKey = fks[0]
    assert fk.column.table.name == "sessions"
    assert fk.column.name == "id"
    assert fk.ondelete is None, "Allegato A: NO CASCADE su session_id (registro permanente)"


@pytest.mark.unit
def test_cart_item_id_fk_has_no_cascade() -> None:
    """Aderenza letterale Allegato A: NO ON DELETE CASCADE (registro permanente)."""
    table = Base.metadata.tables["storico_ordini"]
    col = table.columns["cart_item_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk: ForeignKey = fks[0]
    assert fk.column.table.name == "cart_items"
    assert fk.column.name == "id"
    assert fk.ondelete is None, "Allegato A: NO CASCADE su cart_item_id (registro permanente)"


@pytest.mark.unit
def test_asin_char_10_not_null() -> None:
    table = Base.metadata.tables["storico_ordini"]
    col = table.columns["asin"]
    assert isinstance(col.type, CHAR)
    assert col.type.length == 10
    assert not col.nullable


@pytest.mark.unit
def test_qty_int_not_null() -> None:
    table = Base.metadata.tables["storico_ordini"]
    col = table.columns["qty"]
    assert isinstance(col.type, Integer)
    assert not col.nullable


@pytest.mark.unit
def test_unit_cost_eur_numeric_12_2_not_null() -> None:
    table = Base.metadata.tables["storico_ordini"]
    col = table.columns["unit_cost_eur"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 12
    assert col.type.scale == 2
    assert not col.nullable


@pytest.mark.unit
def test_ordered_at_timestamptz_default_now_not_null() -> None:
    table = Base.metadata.tables["storico_ordini"]
    col = table.columns["ordered_at"]
    assert isinstance(col.type, TIMESTAMP)
    assert col.type.timezone is True
    assert not col.nullable
    assert col.server_default is not None


@pytest.mark.unit
def test_tenant_id_default_1_not_null() -> None:
    table = Base.metadata.tables["storico_ordini"]
    col = table.columns["tenant_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    assert col.server_default is not None
    assert "1" in str(col.server_default.arg)


@pytest.mark.unit
def test_relationship_session_no_passive_deletes() -> None:
    """Lato AnalysisSession: niente passive_deletes (registro permanente)."""
    item_rel = StoricoOrdine.__mapper__.relationships["session"]
    assert item_rel.mapper.class_ is AnalysisSession
    assert item_rel.back_populates == "storico_ordini"

    session_rel = AnalysisSession.__mapper__.relationships["storico_ordini"]
    assert session_rel.mapper.class_ is StoricoOrdine
    assert session_rel.back_populates == "session"
    assert session_rel.passive_deletes is False, (
        "storico_ordini: registro permanente, no passive_deletes"
    )


@pytest.mark.unit
def test_relationship_cart_item_no_passive_deletes() -> None:
    item_rel = StoricoOrdine.__mapper__.relationships["cart_item"]
    assert item_rel.mapper.class_ is CartItem
    assert item_rel.back_populates == "storico_ordini"

    cart_rel = CartItem.__mapper__.relationships["storico_ordini"]
    assert cart_rel.mapper.class_ is StoricoOrdine
    assert cart_rel.back_populates == "cart_item"
    assert cart_rel.passive_deletes is False


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
    instance = StoricoOrdine(
        session_id=42,
        cart_item_id=7,
        asin="B0CMDRD2QF",
        qty=25,
        unit_cost_eur=Decimal("450.00"),
    )
    assert instance.session_id == 42
    assert instance.cart_item_id == 7
    assert instance.asin == "B0CMDRD2QF"
    assert instance.qty == 25
    assert instance.unit_cost_eur == Decimal("450.00")
