---
id: CHG-2026-05-02-017
date: 2026-05-02
adr_ref: ADR-0015, ADR-0016, ADR-0019, ADR-0014
commit: TBD
---

## What

R-03 ORDER-DRIVEN MEMORY wiring: la tabella `storico_ordini` esisteva
schema-only (CHG-2026-04-30-016) ma non era mai scritta. Questo CHG
chiude il loop CFO end-to-end: sessione salvata → bottone "Conferma
ordini → registro permanente" → riga in `storico_ordini` per ogni
`cart_item`.

| File | Cosa |
|---|---|
| `src/talos/persistence/storico_ordini_repository.py` | nuovo: `record_orders_from_session(db, *, session_id, tenant_id) -> int` (idempotente, ritorna 0 se già confermato) + `count_orders_for_session(db, *, session_id, tenant_id) -> int`. Join `CartItem ⨝ VgpResult` per ottenere `asin` (cart_item non lo memorizza direttamente). RLS `with_tenant`. |
| `src/talos/persistence/__init__.py` | re-export `count_orders_for_session` + `record_orders_from_session`. |
| `src/talos/ui/dashboard.py` | + `try_record_orders` + `_count_orders_already_recorded` graceful wrapper. UI: dopo save sessione, `st.session_state["last_saved_session_id"]` traccia ID. Bottone primary "Conferma ordini sessione #N → registro permanente" con check idempotenza (`st.info` se già nel registro). Toast feedback. |
| `tests/integration/test_storico_ordini_repository.py` | 5 test integration su Postgres reale: count zero iniziale, record N, idempotenza no-op secondo call, asin/qty/unit_cost corretti, tenant isolation no-crash. |

## Tests

ruff/format/mypy strict OK. **885 PASS** (742 unit/gov/golden + 143 integration +5).

## Refs

- ADR-0015 (persistenza R-03), ADR-0016 (UI), ADR-0019 (test), ADR-0014.
- Tabella `StoricoOrdine`: schema CHG-2026-04-30-016 (FK senza CASCADE,
  RLS Zero-Trust).
- R-03 ORDER-DRIVEN MEMORY: PROJECT-RAW.md riga 221.
- Pattern idempotente: una sessione genera ordini una sola volta; per
  ri-ordinare → nuova sessione (replay/duplicate UX esistente CHG-057).
- Commit: TBD.
