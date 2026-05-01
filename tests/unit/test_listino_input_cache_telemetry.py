"""Unit test telemetria cache `description_resolutions` (CHG-2026-05-01-025).

Verifica che gli helper di emit nel caller `resolve_listino_with_cache`
(CHG-019 + CHG-020) producano gli eventi canonici `cache.hit` /
`cache.miss` del catalogo ADR-0021 con i campi obbligatori. Pattern
coerente con `test_dashboard_telemetry_resolve.py` (CHG-021/024).
"""

from __future__ import annotations

import logging

import pytest

from talos.observability.events import (
    CANONICAL_EVENTS,
    EVENT_CACHE_HIT,
    EVENT_CACHE_MISS,
)
from talos.ui.listino_input import (
    _emit_cache_hit,
    _emit_cache_miss,
)

pytestmark = pytest.mark.unit


def test_cache_hit_emits_canonical_event(caplog: pytest.LogCaptureFixture) -> None:
    """`_emit_cache_hit` emette evento con table + tenant_id."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.listino_input"):
        _emit_cache_hit(table="description_resolutions", tenant_id=1)

    records = [r for r in caplog.records if r.message == EVENT_CACHE_HIT]
    assert len(records) == 1
    record = records[0]
    assert hasattr(record, "table")
    assert hasattr(record, "tenant_id")
    assert record.table == "description_resolutions"
    assert record.tenant_id == 1


def test_cache_hit_open_table_enum(caplog: pytest.LogCaptureFixture) -> None:
    """`table` è enum-string aperta: future cache (es. bsr.cache) additive."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.listino_input"):
        _emit_cache_hit(table="bsr_cache", tenant_id=42)

    records = [r for r in caplog.records if r.message == EVENT_CACHE_HIT]
    assert len(records) == 1
    assert records[0].table == "bsr_cache"
    assert records[0].tenant_id == 42


def test_cache_miss_emits_canonical_event(caplog: pytest.LogCaptureFixture) -> None:
    """`_emit_cache_miss` emette evento con table + tenant_id."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.listino_input"):
        _emit_cache_miss(table="description_resolutions", tenant_id=1)

    records = [r for r in caplog.records if r.message == EVENT_CACHE_MISS]
    assert len(records) == 1
    record = records[0]
    assert hasattr(record, "table")
    assert hasattr(record, "tenant_id")
    assert record.table == "description_resolutions"
    assert record.tenant_id == 1


def test_cache_miss_multi_tenant(caplog: pytest.LogCaptureFixture) -> None:
    """Edge case: tenant_id != DEFAULT_TENANT_ID per scenario multi-tenant futuro."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.listino_input"):
        _emit_cache_miss(table="description_resolutions", tenant_id=99)

    records = [r for r in caplog.records if r.message == EVENT_CACHE_MISS]
    assert len(records) == 1
    assert records[0].tenant_id == 99


def test_canonical_events_catalog_contains_cache_entries() -> None:
    """Il catalogo `CANONICAL_EVENTS` contiene cache.hit e cache.miss con i campi attesi."""
    assert "cache.hit" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["cache.hit"] == ("table", "tenant_id")
    assert "cache.miss" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["cache.miss"] == ("table", "tenant_id")
