---
id: CHG-2026-05-02-021
date: 2026-05-02
adr_ref: ADR-0015, ADR-0016, ADR-0019
commit: TBD
---

## What

Aggregate analytics + KPI dashboard CFO cross-session.

| File | Cosa |
|---|---|
| `src/talos/persistence/analytics_repository.py` | nuovo: `OrdersAggregateSummary` (days_window/n_sessions/n_orders/total_qty/total_eur/avg_roi) + `AsinAggregate`. `aggregate_orders_last_days(*, days, tenant_id)` con SUM/COUNT/DISTINCT su `storico_ordini` + ROI weighted via JOIN `cart_items ⨝ vgp_results`. `top_asins_by_total_qty(*, limit, tenant_id)` GROUP BY asin ORDER BY SUM(qty) DESC. RLS Zero-Trust via `with_tenant`. |
| `src/talos/persistence/__init__.py` | re-export 4 simboli. |
| `src/talos/ui/dashboard.py` | + `_render_kpi_aggregate(factory, *, tenant_id)` expander "Riepilogo storico · KPI CFO" con selectbox window (7/30/90/180 gg) + 4 metric tile (sessioni/ordini/spesa/ROI medio) + tabella top 10 ASIN. Wired post `_render_orders_history`. |
| `tests/integration/test_analytics_repository.py` | 6 test (zero, after-seed, invalid days, top-asins empty/seeded/invalid limit). |

## Tests

ruff/format/mypy strict OK. **903 PASS** (743 unit/gov/golden + 160 integration).

## Refs

- ADR-0015 (storico_ordini schema + RLS), ADR-0016 (UI), ADR-0019.
- Predecessori: CHG-017 (storico_ordini wiring), CHG-018 (list_recent_orders).
- Pattern: SELECT con interval interpolato (f-string `days_int` int-validated, no injection).
- Commit: TBD.
