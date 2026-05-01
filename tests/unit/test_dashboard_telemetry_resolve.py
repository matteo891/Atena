"""Unit test telemetria UI flow descrizione+prezzo.

Eventi coperti (catalogo ADR-0021):
- `ui.resolve_started` / `ui.resolve_confirmed` (errata CHG-021)
- `ui.override_applied` / `ui.resolve_failed` (errata CHG-024)

Verifica che gli helper di emit nel flow descrizione+prezzo (CHG-020 +
hardening A1/A2/A3 CHG-021/022/023) producano gli eventi canonici del
catalogo ADR-0021 con i campi obbligatori. Pattern coerente con
`test_replay_session_telemetry.py` (CHG-058).
"""

from __future__ import annotations

import logging

import pytest

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

pytestmark = pytest.mark.unit


def test_resolve_started_emits_canonical_event(caplog: pytest.LogCaptureFixture) -> None:
    """`_emit_ui_resolve_started` emette l'evento con n_rows + has_factory."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_started(n_rows=12, has_factory=True)

    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_STARTED]
    assert len(records) == 1
    record = records[0]
    assert hasattr(record, "n_rows")
    assert hasattr(record, "has_factory")
    assert record.n_rows == 12
    assert record.has_factory is True


def test_resolve_started_with_no_factory(caplog: pytest.LogCaptureFixture) -> None:
    """`has_factory=False` riflette graceful degrade DB non disponibile."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_started(n_rows=0, has_factory=False)

    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_STARTED]
    assert len(records) == 1
    assert records[0].n_rows == 0
    assert records[0].has_factory is False


def test_resolve_confirmed_emits_canonical_event(caplog: pytest.LogCaptureFixture) -> None:
    """`_emit_ui_resolve_confirmed` emette evento con n_total/n_resolved/n_ambiguous."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_confirmed(n_total=10, n_resolved=8, n_ambiguous=2)

    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_CONFIRMED]
    assert len(records) == 1
    record = records[0]
    assert hasattr(record, "n_total")
    assert hasattr(record, "n_resolved")
    assert hasattr(record, "n_ambiguous")
    assert record.n_total == 10
    assert record.n_resolved == 8
    assert record.n_ambiguous == 2


def test_resolve_confirmed_zero_resolved(caplog: pytest.LogCaptureFixture) -> None:
    """Edge case: tutti unresolved → n_resolved=0, conversion rate 0%."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_confirmed(n_total=5, n_resolved=0, n_ambiguous=0)

    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_CONFIRMED]
    assert len(records) == 1
    assert records[0].n_total == 5
    assert records[0].n_resolved == 0


def test_override_applied_emits_canonical_event(caplog: pytest.LogCaptureFixture) -> None:
    """`_emit_ui_override_applied` emette evento con n_overrides + n_eligible."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_override_applied(n_overrides=2, n_eligible=5)

    records = [r for r in caplog.records if r.message == EVENT_UI_OVERRIDE_APPLIED]
    assert len(records) == 1
    record = records[0]
    assert hasattr(record, "n_overrides")
    assert hasattr(record, "n_eligible")
    assert record.n_overrides == 2
    assert record.n_eligible == 5


def test_override_applied_full_adoption_edge(caplog: pytest.LogCaptureFixture) -> None:
    """Edge case: CFO sostituisce TUTTI i top-1 ambigui (n_overrides == n_eligible)."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_override_applied(n_overrides=3, n_eligible=3)

    records = [r for r in caplog.records if r.message == EVENT_UI_OVERRIDE_APPLIED]
    assert len(records) == 1
    assert records[0].n_overrides == 3
    assert records[0].n_eligible == 3


def test_resolve_failed_keepa_key_missing(caplog: pytest.LogCaptureFixture) -> None:
    """`_emit_ui_resolve_failed` con reason `keepa_key_missing` (path produzione attuale)."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_failed(reason="keepa_key_missing", n_rows=5)

    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_FAILED]
    assert len(records) == 1
    record = records[0]
    assert hasattr(record, "reason")
    assert hasattr(record, "n_rows")
    assert record.reason == "keepa_key_missing"
    assert record.n_rows == 5


def test_resolve_failed_open_reason_enum(caplog: pytest.LogCaptureFixture) -> None:
    """`reason` è enum-string aperta: nuovi valori additivi non rompono il contratto."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_failed(reason="exception", n_rows=20)

    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_FAILED]
    assert len(records) == 1
    assert records[0].reason == "exception"
    assert records[0].n_rows == 20


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
