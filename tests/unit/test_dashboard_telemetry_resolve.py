"""Unit test telemetria UI flow descrizione+prezzo (CHG-021/024 + CHG-B1.1.e).

Eventi coperti (catalogo ADR-0021):
- `ui.resolve_started` / `ui.resolve_confirmed` (errata CHG-021)
- `ui.override_applied` / `ui.resolve_failed` (errata CHG-024)

Verifica che gli helper di emit nel flow descrizione+prezzo (CHG-020 +
hardening A1/A2/A3 CHG-021/022/023) producano gli eventi canonici del
catalogo ADR-0021 con i campi obbligatori. Pattern
`structlog.testing.LogCapture` post-bridge B1.1.e (CHG-2026-05-01-034).
Fixture `log_capture` condivisa in `tests/conftest.py` (CHG-031).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from talos.observability import (
    bind_request_context,
    clear_request_context,
    is_request_context_bound,
)
from talos.observability.events import (
    CANONICAL_EVENTS,
    EVENT_UI_OVERRIDE_APPLIED,
    EVENT_UI_RESOLVE_CONFIRMED,
    EVENT_UI_RESOLVE_FAILED,
    EVENT_UI_RESOLVE_STARTED,
)
from talos.ui.dashboard import (
    _emit_ui_override_applied,
    _emit_ui_resolve_confirmed,
    _emit_ui_resolve_failed,
    _emit_ui_resolve_started,
)

if TYPE_CHECKING:
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


def test_resolve_started_emits_canonical_event(log_capture: LogCapture) -> None:
    """`_emit_ui_resolve_started` emette l'evento con n_rows + has_factory."""
    _emit_ui_resolve_started(n_rows=12, has_factory=True)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_STARTED]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["n_rows"] == 12
    assert entry["has_factory"] is True


def test_resolve_started_with_no_factory(log_capture: LogCapture) -> None:
    """`has_factory=False` riflette graceful degrade DB non disponibile."""
    _emit_ui_resolve_started(n_rows=0, has_factory=False)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_STARTED]
    assert len(entries) == 1
    assert entries[0]["n_rows"] == 0
    assert entries[0]["has_factory"] is False


def test_resolve_confirmed_emits_canonical_event(log_capture: LogCapture) -> None:
    """`_emit_ui_resolve_confirmed` emette evento con n_total/n_resolved/n_ambiguous."""
    _emit_ui_resolve_confirmed(n_total=10, n_resolved=8, n_ambiguous=2)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_CONFIRMED]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["n_total"] == 10
    assert entry["n_resolved"] == 8
    assert entry["n_ambiguous"] == 2


def test_resolve_confirmed_zero_resolved(log_capture: LogCapture) -> None:
    """Edge case: tutti unresolved → n_resolved=0, conversion rate 0%."""
    _emit_ui_resolve_confirmed(n_total=5, n_resolved=0, n_ambiguous=0)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_CONFIRMED]
    assert len(entries) == 1
    assert entries[0]["n_total"] == 5
    assert entries[0]["n_resolved"] == 0


def test_override_applied_emits_canonical_event(log_capture: LogCapture) -> None:
    """`_emit_ui_override_applied` emette evento con n_overrides + n_eligible."""
    _emit_ui_override_applied(n_overrides=2, n_eligible=5)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_OVERRIDE_APPLIED]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["n_overrides"] == 2
    assert entry["n_eligible"] == 5


def test_override_applied_full_adoption_edge(log_capture: LogCapture) -> None:
    """Edge case: CFO sostituisce TUTTI i top-1 ambigui (n_overrides == n_eligible)."""
    _emit_ui_override_applied(n_overrides=3, n_eligible=3)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_OVERRIDE_APPLIED]
    assert len(entries) == 1
    assert entries[0]["n_overrides"] == 3
    assert entries[0]["n_eligible"] == 3


def test_resolve_failed_keepa_key_missing(log_capture: LogCapture) -> None:
    """`_emit_ui_resolve_failed` con reason `keepa_key_missing` (path produzione attuale)."""
    _emit_ui_resolve_failed(reason="keepa_key_missing", n_rows=5)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_FAILED]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["reason"] == "keepa_key_missing"
    assert entry["n_rows"] == 5


def test_resolve_failed_open_reason_enum(log_capture: LogCapture) -> None:
    """`reason` è enum-string aperta: nuovi valori additivi non rompono il contratto."""
    _emit_ui_resolve_failed(reason="exception", n_rows=20)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_FAILED]
    assert len(entries) == 1
    assert entries[0]["reason"] == "exception"
    assert entries[0]["n_rows"] == 20


def test_ui_emit_inherits_request_context_when_bound(log_capture: LogCapture) -> None:
    """CHG-B1.3: emit UI ereditano `request_id`+`tenant_id` se bind attivo (nesting OK)."""
    rid = bind_request_context(tenant_id=1)
    try:
        _emit_ui_resolve_started(n_rows=3, has_factory=True)
    finally:
        clear_request_context()

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_STARTED]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["n_rows"] == 3
    # Context bound ereditato via merge_contextvars (ADR-0021).
    assert entry["request_id"] == rid
    assert entry["tenant_id"] == 1


def test_bind_request_context_idempotent_nesting(log_capture: LogCapture) -> None:
    """CHG-B1.3: bind annidato riusa request_id esistente (pattern is_outer)."""
    assert not is_request_context_bound()
    rid_outer = bind_request_context(tenant_id=1)
    try:
        # Caller annidato: bind riusa, NON sovrascrive.
        rid_inner = bind_request_context(tenant_id=99)  # tenant_id ignorato
        assert rid_inner == rid_outer
        assert is_request_context_bound()

        _emit_ui_resolve_started(n_rows=1, has_factory=False)
    finally:
        clear_request_context()

    assert not is_request_context_bound()  # clear pulisce tutto

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_STARTED]
    assert len(entries) == 1
    # tenant_id originale (1), non sovrascritto da nesting (99).
    assert entries[0]["tenant_id"] == 1


def test_canonical_events_catalog_contains_new_entries() -> None:
    """Il catalogo `CANONICAL_EVENTS` contiene i 4 eventi UI + bonus session.replayed."""
    assert "ui.resolve_started" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["ui.resolve_started"] == ("n_rows", "has_factory")
    assert "ui.resolve_confirmed" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["ui.resolve_confirmed"] == (
        "n_total",
        "n_resolved",
        "n_ambiguous",
    )
    # CHG-024: due nuovi eventi UI.
    assert "ui.override_applied" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["ui.override_applied"] == ("n_overrides", "n_eligible")
    assert "ui.resolve_failed" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["ui.resolve_failed"] == ("reason", "n_rows")
    # Bonus correttivo CHG-021: session.replayed allineato (era drift CHG-058).
    assert "session.replayed" in CANONICAL_EVENTS
    assert CANONICAL_EVENTS["session.replayed"] == (
        "asin_count",
        "locked_in_count",
        "budget",
        "budget_t1",
    )
