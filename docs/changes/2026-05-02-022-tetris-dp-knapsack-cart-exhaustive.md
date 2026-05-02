---
id: CHG-2026-05-02-022
date: 2026-05-02
adr_ref: ADR-0018, ADR-0009, ADR-0019, ADR-0014
commit: TBD
---

## What

**Errata sostanziale F5/R-06 ratificata Leader 2026-05-02 (round 7)**:
greedy max-fill (CHG-020) sostituito da **DP bounded knapsack** + cart
**exhaustive con reason flag**.

Decisione Leader: *"il Tetris deve calcolare la miglior combinazione di
prodotti acquistati in lotti di quantità definita per saturare al massimo
il budget e non lasciare neanche un centesimo fermo se è utilizzabile"* +
*"il cart deve mostrare tutti i prodotti, non vengono omessi. se risultano
inidonei per qualche parametro semplicemente il parametro che li rende
inidonei viene flaggato in qualche maniera e la quantità di acquisto viene
settata su zero"*.

| File | Cosa |
|---|---|
| `src/talos/tetris/allocator.py` | Pass 2 R-06 sostituito: greedy → DP bounded knapsack 1D, granularità 1 EUR. Maximize `sum(cost*qty)` (saturazione), tie-break VGP weighted (`epsilon * vgp * qty`). + helper `_solve_knapsack_dp(items, budget, lot_size)` con backtrack via `parent[]`. + `_classify_reason(score, qty_target, *, kill_mask)` dispatcher reason. **Cart exhaustive**: contiene TUTTI gli ASIN del listino, ognuno con `qty` (0+) e `reason` flag. Costanti: `REASON_ALLOCATED/LOCKED_IN/VETO_ROI/KILL_SWITCH/ZERO_QTY_TARGET/MIN_LOT_OVER_BUDGET/BUDGET_EXHAUSTED`. Helper `cart.allocated_items()` (qty>0) + `cart.panchina_items()` (qty=0 con vgp>0 e reason BUDGET_EXHAUSTED/MIN_LOT). Pass 1 R-04 invariato (locked-in qty_final velocity). |
| `src/talos/persistence/session_repository.py` | DB persiste solo `cart.allocated_items()` (qty>0) — coerente con vincoli schema `cart_items`. Cart in-memory exhaustive resta UI-only. |
| `src/talos/ui/dashboard.py` | `_render_cart_table` ora mostra cart exhaustive sortato per qty DESC + vgp DESC. Caption con count `N/M ASIN allocati` + lista reason flags. `result.panchina` DataFrame non più renderizzato (vista derivata da cart.panchina_items() opzionale). |
| `tests/unit/test_tetris_allocator.py` | Riscrittura completa: 18 test su DP knapsack + cart exhaustive + reason classification. |
| `tests/unit/test_tetris_telemetry.py` | 2 test telemetry aggiornati. |
| `tests/golden/test_pipeline_samsung_mini.py` | snapshot rinnovato post-DP: allocated `[S004_GOOD, S005_LOW]` (era `[S004_GOOD, S002_HIGH, S005_LOW]` greedy); qty `(5, 20)` (era `(5, 5, 5)`); cost 4800; saturation 0.96 (era 0.90 greedy); panchina `[S002_HIGH, S001_TOP, S003_MID]`. |
| `tests/integration/*` | 5 test integration aggiornati per usare `cart.allocated_items()` invece di `cart.items`. |

## Why

Greedy max-fill (CHG-020) era subottimale: top VGP DESC con max lotti
"mangiava" il budget, lasciando residuo non sufficiente per altri ASIN.
Bug rilevato dal Leader 2026-05-02: con CSV demo + budget 10k, cart
allocava 1 solo ASIN saturando 95%, residuo 500 < 1 lotto altri ASIN.

DP knapsack risolve l'optimal: maximize `sum(cost*qty)` con qty in
multipli di lot_size. Tie-break VGP per scelta tra combinazioni
equivalenti. Granularità 1 EUR (budget int 10k → 10k stati).

Cart exhaustive: il Leader vuole UI con TUTTI gli ASIN del listino +
flag motivo (UX trasparente, niente "dove è finito quel prodotto?").
La panchina come tabella separata diventa vista derivata.

**Effetto golden Samsung-mini** (10 ASIN, budget 5000):
- Pre-CHG-020 greedy fisso qty_final: saturation 72% / cart 3 items
- CHG-020 greedy max-fill: saturation 90% / cart 3 items
- **CHG-022 DP knapsack**: saturation **96%** / cart **2 items** (S004 locked + S005 con qty=20 ottimo)
- Cart exhaustive: 10 items totali (8 con reason ≠ ALLOCATED).

## Tests

ruff/format/mypy strict OK. **900 PASS** (740 unit/gov/golden + 160 integration).
- 18 test allocator riscritti.
- 5 test golden rinnovati.
- 5 test integration aggiornati (`cart.allocated_items()`).

## Refs

- ADR-0018 (algoritmo VGP/Tetris) — errata sostanziale.
- ADR-0009 (errata corrige mechanism).
- PROJECT-RAW.md riga 224 (R-06 99.9% ora ottimizzato), riga 308
  ("liberando l'altra metà del capitale per il Tetris" → DP optimum).
- Decisione Leader 2026-05-02: ratifica esplicita DP + cart exhaustive.
- Predecessore: CHG-2026-05-02-020 (greedy max-fill, soppiantato).
- Commit: TBD.
