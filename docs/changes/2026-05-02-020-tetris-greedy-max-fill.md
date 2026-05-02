---
id: CHG-2026-05-02-020
date: 2026-05-02
adr_ref: ADR-0018, ADR-0009, ADR-0019, ADR-0014
commit: TBD
---

## What

**Errata semantica F5/R-06 ratificata Leader 2026-05-02**: `qty_final` non è
il MASSIMO ma il MINIMO (1 lotto fornitore). Pass 2 R-06 ora compra il
**MAX multiplo di lot_size** che sta nel budget residuo per ogni ASIN VGP
DESC (greedy max-fill). Ratifica esplicita Leader: "5 sono i multipli, non
il massimo".

| File | Cosa |
|---|---|
| `src/talos/tetris/allocator.py` | + costante `DEFAULT_LOT_SIZE: int = 5`. + parametro `lot_size: int = 5` in `allocate_tetris`. Pass 2 R-06 sostituisce `qty_value = qty_final` con `qty_max_lot = floor(remaining / cost_unit / lot_size) * lot_size` (greedy MAX). Skip se `qty_max_lot < lot_size` (nemmeno 1 lotto sta). Pass 1 R-04 INVARIATO (locked-in compra qty_final velocity-based). |
| `tests/unit/test_tetris_allocator.py` | 9 test riscritti per nuovo behavior + 1 test nuovo `test_residual_budget_spills_to_lower_vgp`. |
| `tests/unit/test_tetris_telemetry.py` | `test_skipped_budget_emits_canonical_event` aggiornato: ora emit con `cost = cost_unit * lot_size` (1 lotto teorico). |
| `tests/golden/test_pipeline_samsung_mini.py` | snapshot byte-exact aggiornato post-greedy: cart `["S004_GOOD","S002_HIGH","S005_LOW"]` (era `["S004_GOOD","S005_LOW","S003_MID"]`); cost 4500 (era 3600); saturation 0.9 (era 0.72); panchina `["S001_TOP","S003_MID","S010_TINY"]`; budget_t1 6658.87 (era 6187.21). |

## Why

Bug rilevato live dal Leader 2026-05-02 sul flow Demetra: cart con 1 ASIN
qty=5, saturation 19%, budget rimanente non utilizzato. Diagnosi: F5
`qty_final = floor(qty_target / 5) * 5` era usato dal Tetris come
quantità ESATTA da allocare. PROJECT-RAW.md riga 308 ("Talos dimezza la
Quota Mensile per coprire 15 giorni, **liberando l'altra metà del capitale
per il Tetris**") ammette interpretazione greedy: il Tetris usa il
capitale residuo per riempire ulteriormente i top-VGP.

Decisione Leader 2026-05-02 (ratifica esplicita): "5 sono i multipli, non
il massimo" → opzione **A** (greedy max-fill) implementata.

Effetto: nel listino Samsung-mini golden, saturation passa da 72% a 90%
(+18pp), allocazione concentrata sui top-VGP con multipli di lot_size
fino al budget residuo.

## Tests

ruff/format/mypy strict OK. **897 PASS** (743 unit/gov/golden + 154 integration).

- 9 test unit allocator riscritti + 1 nuovo test residual_spill.
- 1 test telemetry aggiornato per cost = cost_unit * lot_size.
- 5 test golden Samsung-mini snapshot aggiornati.
- 0 test integration ulteriori da aggiornare (DB-only, non testano qty greedy).

## Test di Conformità

- ADR-0018 (algoritmo VGP/Tetris): **errata corrige R-06 semantica**
  ratificata Leader. Pattern coerente con ADR-0009 (errata su ADR Active
  senza supersessione completa).
- ADR-0019 (test strategy): golden snapshot byte-exact rinnovato + 9
  test allocator espliciti sul nuovo behavior.
- R-04 PASS 1 invariato (locked-in qty_final).
- R-05 KILL-SWITCH invariato (vgp_score=0 → skip).
- R-08 VETO ROI invariato (sotto soglia → vgp_score=0 → skip).
- R-09 PANCHINA invariato (idonei scartati per cassa, ordinati VGP DESC).
- R-01 NO SILENT DROPS: `tetris.skipped_budget` emit invariato per skip
  greedy (cost 1 lotto > remaining).

## Refs

- ADR-0018, ADR-0009 (errata mechanism), ADR-0019, ADR-0014.
- PROJECT-RAW.md riga 224 (R-06), riga 308 (velocity_target + capitale liberato), riga 313 (F5 lot_size).
- Bug rilevato Leader 2026-05-02: "il bot ne compra solo 5 unità,
  saturando il budget al 19% invece che al massimo consentito".
- Decisione Leader 2026-05-02: ratifica opzione **A** (greedy max-fill).
- Predecessore CHG-041 (skip qty_final<=0 nel Pass 2, semantica
  parzialmente sovrascritta da questo CHG).
- Commit: TBD.
