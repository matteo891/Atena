---
id: CHG-2026-05-02-018
date: 2026-05-02
adr_ref: ADR-0015, ADR-0016, ADR-0019
commit: TBD
---

## What

Storico ordini visibilità CFO: `list_recent_orders` repository + UI
expander "Storico ordini · registro permanente" con tabella + export CSV.

| File | Cosa |
|---|---|
| `src/talos/persistence/storico_ordini_repository.py` | + `OrderSummary` dataclass (id, session_id, cart_item_id, asin, qty, unit_cost_eur, total_cost_eur, ordered_at). + `list_recent_orders(db, *, limit, tenant_id) -> list[OrderSummary]` con ORDER BY `ordered_at DESC, id DESC`. ValueError su limit≤0. |
| `src/talos/persistence/__init__.py` | re-export `OrderSummary` + `list_recent_orders`. |
| `src/talos/ui/dashboard.py` | + helper `fetch_recent_orders_or_empty` graceful + `_render_orders_history` con expander, dataframe, download_button CSV. Caption "N ordini più recenti (limit X)". Wired in flow Demetra dopo `_render_history` sessioni. |
| `tests/integration/test_storico_ordini_repository.py` | + 3 test (empty / post-record / invalid limit raise). Totale 8 test. |

## Tests

ruff/format/mypy strict OK. **888 PASS** (742 unit/gov/golden + 146 integration).

## Refs

- ADR-0015 (R-03 ORDER-DRIVEN MEMORY), ADR-0016 (UI), ADR-0019.
- Predecessore CHG-017 (record wiring).
- Commit: TBD.
