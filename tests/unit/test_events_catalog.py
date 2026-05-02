"""Unit test sul catalogo eventi canonici (ADR-0021)."""

from __future__ import annotations

import pytest

from talos.observability.events import CANONICAL_EVENTS

_EXPECTED_EVENTS: frozenset[str] = frozenset(
    {
        "extract.kill_switch",
        "vgp.veto_roi_failed",
        "vgp.kill_switch_zero",
        "tetris.skipped_budget",
        "panchina.archived",
        "keepa.miss",
        "keepa.rate_limit_hit",
        "scrape.selector_fail",
        "ocr.below_confidence",
        "db.audit_log_write",
        # Errata CHG-2026-04-30-058 (drift sanato in CHG-2026-05-01-021)
        "session.replayed",
        # Errata CHG-2026-05-01-021 — UI flow descrizione+prezzo (ADR-0016)
        "ui.resolve_started",
        "ui.resolve_confirmed",
        # Errata CHG-2026-05-01-024 — copertura UI hardening A3 + fail mode
        "ui.override_applied",
        "ui.resolve_failed",
        # Errata CHG-2026-05-01-025 — cache description_resolutions (ADR-0015)
        "cache.hit",
        "cache.miss",
        # Errata CHG-2026-05-02-005 — velocity estimator MVP (ADR-0017+0018)
        "v_tot.estimated_from_bsr",
        # Errata CHG-2026-05-02-010 — persistenza sessione (ADR-0015+0016)
        "session.persisted",
        # Errata CHG-2026-05-02-031 — Amazon Presence Filter (ADR-0024)
        "vgp.amazon_dominant_seller",
        # Errata CHG-2026-05-02-032 — 90-Day Stress Test (ADR-0023)
        "vgp.stress_test_failed",
        # Errata CHG-2026-05-02-033 — Ghigliottina (ADR-0022)
        "vgp.ghigliottina_failed",
    },
)


@pytest.mark.unit
def test_catalog_matches_expected_events() -> None:
    assert set(CANONICAL_EVENTS.keys()) == _EXPECTED_EVENTS


@pytest.mark.unit
def test_catalog_each_event_has_non_empty_field_tuple() -> None:
    for event_name, fields in CANONICAL_EVENTS.items():
        assert isinstance(fields, tuple), f"{event_name}: campi non sono tupla"
        assert len(fields) > 0, f"{event_name}: tupla campi vuota"
        for field in fields:
            assert isinstance(field, str), f"{event_name}: campo non stringa {field!r}"
            assert field, f"{event_name}: campo vuoto"
