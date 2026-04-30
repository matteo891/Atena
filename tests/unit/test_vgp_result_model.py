"""Unit test del model `VgpResult` — ADR-0015 Allegato A.

Nucleo del decisore: doppia FK CASCADE + indice composito con DESC.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import CHAR, BigInteger, Boolean, Integer, Numeric

from talos.persistence import AnalysisSession, Base, ListinoItem, VgpResult

if TYPE_CHECKING:
    from sqlalchemy.schema import ForeignKey

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "c9527f017d5c_create_vgp_results.py"
)


@pytest.mark.unit
def test_table_name_matches_allegato_a() -> None:
    assert VgpResult.__tablename__ == "vgp_results"


@pytest.mark.unit
def test_table_registered_in_base_metadata() -> None:
    assert "vgp_results" in Base.metadata.tables


@pytest.mark.unit
def test_columns_are_those_of_allegato_a() -> None:
    table = Base.metadata.tables["vgp_results"]
    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "listino_item_id",
        "asin",
        "roi_pct",
        "velocity_monthly",
        "cash_profit_eur",
        "roi_norm",
        "velocity_norm",
        "cash_profit_norm",
        "vgp_score",
        "veto_roi_passed",
        "kill_switch_triggered",
        "qty_target",
        "qty_final",
    }


@pytest.mark.unit
def test_primary_key_is_id_bigint() -> None:
    table = Base.metadata.tables["vgp_results"]
    pk_cols = list(table.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"
    assert isinstance(pk_cols[0].type, BigInteger)


@pytest.mark.unit
def test_session_id_fk_cascade_required() -> None:
    table = Base.metadata.tables["vgp_results"]
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
def test_listino_item_id_fk_cascade_required() -> None:
    table = Base.metadata.tables["vgp_results"]
    col = table.columns["listino_item_id"]
    assert isinstance(col.type, BigInteger)
    assert not col.nullable
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk: ForeignKey = fks[0]
    assert fk.column.table.name == "listino_items"
    assert fk.column.name == "id"
    assert fk.ondelete == "CASCADE"


@pytest.mark.unit
def test_asin_char_10_not_null() -> None:
    table = Base.metadata.tables["vgp_results"]
    col = table.columns["asin"]
    assert isinstance(col.type, CHAR)
    assert col.type.length == 10
    assert not col.nullable


@pytest.mark.unit
def test_numeric_columns_precision_and_scale() -> None:
    table = Base.metadata.tables["vgp_results"]
    expected: dict[str, tuple[int, int]] = {
        "roi_pct": (8, 4),
        "velocity_monthly": (12, 4),
        "cash_profit_eur": (12, 2),
        "roi_norm": (6, 4),
        "velocity_norm": (6, 4),
        "cash_profit_norm": (6, 4),
        "vgp_score": (6, 4),
    }
    for col_name, (precision, scale) in expected.items():
        col = table.columns[col_name]
        assert isinstance(col.type, Numeric), f"{col_name}: type"
        assert col.type.precision == precision, f"{col_name}: precision"
        assert col.type.scale == scale, f"{col_name}: scale"
        assert col.nullable, f"{col_name}: nullable"


@pytest.mark.unit
def test_boolean_flags_nullable() -> None:
    table = Base.metadata.tables["vgp_results"]
    for col_name in ("veto_roi_passed", "kill_switch_triggered"):
        col = table.columns[col_name]
        assert isinstance(col.type, Boolean), f"{col_name}: type"
        assert col.nullable, f"{col_name}: nullable"


@pytest.mark.unit
def test_qty_target_and_qty_final_int_nullable() -> None:
    table = Base.metadata.tables["vgp_results"]
    for col_name in ("qty_target", "qty_final"):
        col = table.columns[col_name]
        assert isinstance(col.type, Integer)
        assert col.nullable


@pytest.mark.unit
def test_index_idx_vgp_session_score_exists() -> None:
    table = Base.metadata.tables["vgp_results"]
    indexes = {idx.name: idx for idx in table.indexes}
    assert "idx_vgp_session_score" in indexes
    idx = indexes["idx_vgp_session_score"]
    assert idx.unique is False, "indice di scan, non UNIQUE"
    # La prima espressione dell'indice è la colonna session_id
    cols = list(idx.expressions)
    assert len(cols) == 2
    assert cols[0].name == "session_id"


@pytest.mark.unit
def test_migration_index_uses_vgp_score_desc() -> None:
    """L'indice deve usare `vgp_score DESC` (Allegato A)."""
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "idx_vgp_session_score" in content
    assert "vgp_score DESC" in content


@pytest.mark.unit
def test_relationship_session_back_populates_vgp_results() -> None:
    item_rel = VgpResult.__mapper__.relationships["session"]
    assert item_rel.mapper.class_ is AnalysisSession
    assert item_rel.back_populates == "vgp_results"

    session_rel = AnalysisSession.__mapper__.relationships["vgp_results"]
    assert session_rel.mapper.class_ is VgpResult
    assert session_rel.back_populates == "session"
    assert session_rel.passive_deletes is True


@pytest.mark.unit
def test_relationship_listino_item_back_populates_vgp_results() -> None:
    item_rel = VgpResult.__mapper__.relationships["listino_item"]
    assert item_rel.mapper.class_ is ListinoItem
    assert item_rel.back_populates == "vgp_results"

    listino_rel = ListinoItem.__mapper__.relationships["vgp_results"]
    assert listino_rel.mapper.class_ is VgpResult
    assert listino_rel.back_populates == "listino_item"
    assert listino_rel.passive_deletes is True


@pytest.mark.unit
def test_construct_minimal_required_fields() -> None:
    instance = VgpResult(
        session_id=42,
        listino_item_id=7,
        asin="B0CMDRD2QF",
    )
    assert instance.session_id == 42
    assert instance.listino_item_id == 7
    assert instance.asin == "B0CMDRD2QF"
    # Tutti i campi numerici e flag default a None (nullable, no default)
    assert instance.roi_pct is None
    assert instance.vgp_score is None
    assert instance.veto_roi_passed is None
    assert instance.kill_switch_triggered is None


@pytest.mark.unit
def test_construct_with_all_decisor_fields() -> None:
    """Caso "fine pipeline VGP": tutti i campi popolati."""
    instance = VgpResult(
        session_id=42,
        listino_item_id=7,
        asin="B0CMDRD2QF",
        roi_pct=Decimal("0.1250"),
        velocity_monthly=Decimal("3.5000"),
        cash_profit_eur=Decimal("125.00"),
        roi_norm=Decimal("0.7500"),
        velocity_norm=Decimal("0.5000"),
        cash_profit_norm=Decimal("0.6000"),
        vgp_score=Decimal("0.6200"),
        veto_roi_passed=True,
        kill_switch_triggered=False,
        qty_target=27,
        qty_final=25,
    )
    assert instance.vgp_score == Decimal("0.6200")
    assert instance.qty_final == 25
    assert instance.veto_roi_passed is True
