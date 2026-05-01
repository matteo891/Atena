---
id: CHG-2026-05-02-010
date: 2026-05-02
adr_ref: ADR-0021, ADR-0015, ADR-0016, ADR-0019
commit: TBD
---

## What

Telemetry catalog extension: evento `session.persisted` post-save.

| File | Cosa |
|---|---|
| `src/talos/observability/events.py` | + `session.persisted` con tupla `(session_id, n_cart_items, n_panchina_items)` + costante `EVENT_SESSION_PERSISTED`. Catalogo: 18→19 voci. |
| `src/talos/ui/dashboard.py` | + emit `_logger.debug("session.persisted", ...)` in `try_persist_session` post-save (success path). Audit aggregato: distribuzione cart size, frequenza salvataggi. |
| `tests/unit/test_events_catalog.py` | + voce in `_EXPECTED_EVENTS` (lock contract). |

## Tests

ruff/format/mypy strict OK. **874 PASS** (736 unit/gov/golden + 138 integration). Risk LOW.

## Refs

- ADR-0021 (catalogo eventi), ADR-0015 (persistenza), ADR-0016 (UI), ADR-0019.
- Pattern: errata catalogo additiva (coerente con CHG-005, CHG-024/025/037).
- Commit: TBD.
