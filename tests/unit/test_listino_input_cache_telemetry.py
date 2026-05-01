"""Unit test telemetria cache `description_resolutions` (CHG-2026-05-01-025
+ CHG-B1.1.e).

Verifica che gli helper di emit nel caller `resolve_listino_with_cache`
(CHG-019 + CHG-020) producano gli eventi canonici `cache.hit` /
`cache.miss` del catalogo ADR-0021 con i campi obbligatori. Pattern
`structlog.testing.LogCapture` post-bridge B1.1.e (CHG-2026-05-01-034).
Fixture `log_capture` condivisa in `tests/conftest.py` (CHG-031).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


def test_cache_hit_emits_canonical_event(log_capture: LogCapture) -> None:
    """`_emit_cache_hit` emette evento con table + tenant_id."""
    _emit_cache_hit(table="description_resolutions", tenant_id=1)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_HIT]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["table"] == "description_resolutions"
    assert entry["tenant_id"] == 1


def test_cache_hit_open_table_enum(log_capture: LogCapture) -> None:
    """`table` è enum-string aperta: future cache (es. bsr.cache) additive."""
    _emit_cache_hit(table="bsr_cache", tenant_id=42)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_HIT]
    assert len(entries) == 1
    assert entries[0]["table"] == "bsr_cache"
    assert entries[0]["tenant_id"] == 42


def test_cache_miss_emits_canonical_event(log_capture: LogCapture) -> None:
    """`_emit_cache_miss` emette evento con table + tenant_id."""
    _emit_cache_miss(table="description_resolutions", tenant_id=1)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_MISS]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["table"] == "description_resolutions"
    assert entry["tenant_id"] == 1


def test_cache_miss_multi_tenant(log_capture: LogCapture) -> None:
    """Edge case: tenant_id != DEFAULT_TENANT_ID per scenario multi-tenant futuro."""
    _emit_cache_miss(table="description_resolutions", tenant_id=99)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_MISS]
    assert len(entries) == 1
    assert entries[0]["tenant_id"] == 99


def test_canonical_events_catalog_contains_cache_entries() -> None:
    """Il catalogo `CANONICAL_EVENTS` contiene cache.hit e cache.miss con i campi attesi."""
    assert "cache.hit" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["cache.hit"] == ("table", "tenant_id")
    assert "cache.miss" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["cache.miss"] == ("table", "tenant_id")
