"""Unit test telemetria cache `description_resolutions` (CHG-025 + B1.1.e + B1.4).

Verifica che gli helper di emit nel caller `resolve_listino_with_cache`
(CHG-019 + CHG-020) producano gli eventi canonici `cache.hit` /
`cache.miss` del catalogo ADR-0021 con i campi obbligatori. Pattern
`structlog.testing.LogCapture` post-bridge B1.1.e (CHG-2026-05-01-034).
Fixture `log_capture` condivisa in `tests/conftest.py` (CHG-031).

CHG-2026-05-01-037 (B1.4): `tenant_id` rimosso dalla firma degli
helper `_emit_cache_*` e dalla tupla obbligatoria del catalogo.
Ora ereditato dal bind UI (`bind_request_context(tenant_id=...)`).
I test post-CHG-037 bindano manualmente per simulare lo scope UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from talos.observability import bind_request_context, clear_request_context
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
    """`_emit_cache_hit` emette evento con `table`; `tenant_id` ereditato dal bind."""
    bind_request_context(tenant_id=1)
    try:
        _emit_cache_hit(table="description_resolutions")
    finally:
        clear_request_context()

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_HIT]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["table"] == "description_resolutions"
    # tenant_id ora context-bound (ereditato), non più kwarg esplicito.
    assert entry["tenant_id"] == 1


def test_cache_hit_open_table_enum(log_capture: LogCapture) -> None:
    """`table` è enum-string aperta: future cache (es. bsr.cache) additive."""
    bind_request_context(tenant_id=42)
    try:
        _emit_cache_hit(table="bsr_cache")
    finally:
        clear_request_context()

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_HIT]
    assert len(entries) == 1
    assert entries[0]["table"] == "bsr_cache"
    assert entries[0]["tenant_id"] == 42


def test_cache_miss_emits_canonical_event(log_capture: LogCapture) -> None:
    """`_emit_cache_miss` emette evento con `table`; `tenant_id` ereditato dal bind."""
    bind_request_context(tenant_id=1)
    try:
        _emit_cache_miss(table="description_resolutions")
    finally:
        clear_request_context()

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_MISS]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["table"] == "description_resolutions"
    assert entry["tenant_id"] == 1


def test_cache_miss_multi_tenant(log_capture: LogCapture) -> None:
    """Edge case: tenant_id != DEFAULT_TENANT_ID per scenario multi-tenant futuro."""
    bind_request_context(tenant_id=99)
    try:
        _emit_cache_miss(table="description_resolutions")
    finally:
        clear_request_context()

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_MISS]
    assert len(entries) == 1
    assert entries[0]["tenant_id"] == 99


def test_cache_emit_without_bind_omits_tenant_id(log_capture: LogCapture) -> None:
    """CHG-B1.4: senza bind, evento ha `table` ma NO `tenant_id` (no auto-fallback)."""
    # NB: nessun bind_request_context. Pattern atteso solo da chi salta la
    # entry-point UI (es. test isolato). In produzione il bind è sempre attivo.
    _emit_cache_hit(table="description_resolutions")

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_HIT]
    assert len(entries) == 1
    assert entries[0]["table"] == "description_resolutions"
    assert "tenant_id" not in entries[0], (
        "tenant_id ora context-bound: deve mancare se nessun bind attivo"
    )


def test_canonical_events_catalog_contains_cache_entries() -> None:
    """Il catalogo `CANONICAL_EVENTS` ha cache.hit/miss con tupla aggiornata B1.4."""
    assert "cache.hit" in CANONICAL_EVENTS
    # CHG-B1.4: tupla ridotta a `("table",)`; tenant_id context-bound.
    assert CANONICAL_EVENTS["cache.hit"] == ("table",)
    assert "cache.miss" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["cache.miss"] == ("table",)
