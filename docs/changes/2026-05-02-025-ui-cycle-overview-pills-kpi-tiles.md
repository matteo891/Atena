---
id: CHG-2026-05-02-025
date: 2026-05-02
adr_ref: ADR-0016, ADR-0019, ADR-0014
commit: 62c2ecc
---

## What

UI restyle FASE 1 step 1: header pillole (Saldo Banca / Margine Min /
Velocity Target) + 4 KPI tile gradient (Valore Carrello / Cash Profit
ciclo / Profitto/Costo % / # ordini ciclo) + Proiezione Annua Compound
sopra il cart attuale. Sostituisce `_render_metrics` (2 metric scarne)
con `_render_cycle_overview` (componente ricco coerente con
mockup ScalerBot 500K).

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | + helper puro `_compute_cycle_kpis(result, *, velocity_target_days) -> dict` (4 KPI calculation: cart_value/cash_profit_total/profit_cost_pct/n_orders + cycles_per_year=365/velocity_target_days + projected_annual=budget*(1+r)^N). + `_render_cycle_overview(budget, util_eur, ult_ordine_giorni, velocity_target_days, kpis)` (pillole header + 4 tile gradient + proiezione compound). + costanti `DEFAULT_CYCLES_PER_YEAR_DIVISOR=365.0` e `DEFAULT_LAST_ORDER_DAYS_FALLBACK=None`. Sostituisce la singola chiamata `_render_metrics` post-`run_session` con `_render_cycle_overview`. CSS aggiunto inline in `_render_module_header` per `.talos-pill`/`.talos-pill-value`/`.talos-pill-label`/`.talos-tile-cycle`/`.talos-tile-projection`. |
| `tests/unit/test_dashboard_cycle_overview.py` | nuovo: 8 test `_compute_cycle_kpis` puri (cart vuoto / cart con allocated / profitto negativo / cycles_per_year boundary 7-30gg / projected compound math). |

## Why

Decisione Leader 2026-05-02 round 7+: replicare UX ScalerBot 500K per
abilitare il portale TALOS Demetra con identità "ERP Arbitraggio Amazon
FBA" anche visivamente, non solo funzionalmente. Le 3 pillole header
sono **display read-only** del valore corrente (input authoritative
restano in sidebar — semantica invariata). I 4 KPI tile **calcolano
dati già nel `SessionResult`** (cart.items, enriched_df, budget_t1):
zero blast radius su pipeline/formule/DB.

Proiezione Annua Compound usa F3 `Budget_T+1 = Budget_T + Cash_Profit`
estesa a N cicli/anno: `cycles = 365 / velocity_target_days`
(es. 15gg → 24.3 cicli/anno). Formula compound `Budget·(1+r)^N` dove
`r = profitto_ciclo / costo_ciclo`. Helper puro testabile mock-only.

## Tests

ruff/format/mypy strict OK. **TBD PASS** (TBD unit/gov/golden + 160 integration).

- 8 test `_compute_cycle_kpis` puri (cart vuoto, cart con allocated, profitto negativo, cycles boundary, projected compound math, edge profit_cost ratio, n_orders count, edge cycles=0 protection).
- 1 test smoke `_render_cycle_overview` import (no Streamlit invoke).
- Test esistenti `_render_metrics` invariati (helper deprecated ma kept come backwards-compat per `_render_replay_result`).

## Test di Conformità

- ADR-0016 (UI): puro Streamlit + CSS inline, helpers puri testabili senza St dependency.
- ADR-0019 (test strategy): test parametrici cycle math + edge cases boundary.
- ADR-0014 (quality gates): ruff strict + mypy strict + format puliti.
- ADR-0018 invariato: F3 compounding originale (1 ciclo) usato; estensione N cicli/anno è proiezione UX, non formula canonica.
- R-01 NO SILENT DROPS: `n_orders=0` → projected=budget (no compound), `velocity_target=0` → ValueError esplicito.

## Refs

- ADR-0016, ADR-0019, ADR-0014.
- Predecessori: CHG-2026-04-30-039 (orchestrator F3 compounding), CHG-2026-05-02-012 (portale TALOS multi-modulo).
- Mockup riferimento: ScalerBot 500K (immagine Leader 2026-05-02).
- Decisione Leader 2026-05-02 round 7+: macina blocco UI restyle + risk-filters Arsenale.
- Commit: `62c2ecc`.
