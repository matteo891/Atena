---
id: CHG-2026-05-02-039
date: 2026-05-02
adr_ref: ADR-0017, ADR-0018, ADR-0019, ADR-0014
commit: 4813222
---

## What

Calibration toolkit ground truth ScalerBot500K. 7 ASIN reali Samsung
estratti dal file Leader `ordine_scaler500k (22).xlsx` (3 tab) come
fixture validazione TALOS pipeline. Documenta discrepanze scoperte
field-by-field. NON risolve (ratifica Leader necessaria).

| File | Cosa |
|---|---|
| `tests/golden/test_ground_truth_scaler500k.py` | nuovo. Fixture inline `GROUND_TRUTH_ASINS` (7 dict TypedDict) + `_implied_fee_fba_atomic` helper. 7 test: 2 sentinel discrepanze (fee_fba L11b ~6-50x atomica + 4/6 ASIN VETO_ROI) + 3 match (ROI con atomica / velocity badge / qty_target 15gg) + 2 shape integrity. |

## Why

Il Leader 2026-05-02 ha fornito ground truth reale (assente prima):
file Excel con 7 ASIN Samsung già analizzati dal sistema operativo
ScalerBot500K. Ogni ASIN ha cost/buybox/profit/roi/velocity/qty/status
calcolati e ratificati dal CFO.

**Discrepanza CRITICA scoperta**:
- ScalerBot fee_fba implicita ≈ €3 (atomica, Keepa pickAndPackFee).
- TALOS fee_fba_manual L11b ≈ €22 (totale, formula Frozen).
- Effetto: 5/6 ASIN ScalerBot CARRELLO sotto VETO_ROI 8% in TALOS L11b
  → cart vuoto. **Bot inutilizzabile in produzione finché ratifica.**

**Match conformi**:
- ROI con fee atomica: TALOS riproduce ScalerBot exact a tolerance €0.05.
- Velocity badge soglie (Veloce ≥30/m, Buona 10-30/m, Lenta <10/m):
  match perfetto su 7/7 ASIN.
- F4 qty_target_15gg: match a tolerance ±2 unità.

**Decisione Leader pendente** prima di errata ADR-0017 α'' (decisione
A2 alpha-prime invertita):
- A: mantieni L11b (TALOS più conservativo, cart magro).
- B: sostituisci L11b → atomica (allinea ScalerBot).
- C: hybrid (Keepa pickAndPackFee live, fallback L11b).

## Tests

ruff/format/mypy strict OK. **1043 test PASS** (+7 vs 1036 CHG-038).

7 test golden documentati:
1. `test_calibration_fee_fba_l11b_diverges_from_scalerbot_atomic`
2. `test_calibration_talos_vetoes_majority_of_scalerbot_carrello`
3. `test_calibration_roi_match_with_atomic_fee`
4. `test_calibration_velocity_badge_match_scalerbot`
5. `test_calibration_qty_target_match_scalerbot_15gg`
6. `test_ground_truth_dataset_has_7_rows`
7. `test_ground_truth_amazon_presence_filter_no_op`

## Test di Conformità

- ADR-0017: KeepaClient α'' policy fee_fba documentata + sentinel test
  che fallirà appena cambia (forcing errata corrige).
- ADR-0018: F1/F2/F4 formule TALOS verificate contro ground truth.
- ADR-0019: golden test pattern (snapshot byte-exact su 7 ASIN reali).
- ADR-0014: ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: discrepanze esplicite via assertion (non
  silenziate).

## Refs

- File Leader: `ordine_scaler500k (22).xlsx` (3 tab ORDINE/STRATEGIA/BLOCCATI).
- ADR-0017 (KeepaClient α'' fee_fba policy).
- ADR-0018 (F1/F2/F4 formule).
- CHG-2026-05-01-015 (decisione α'' originale: fee_fba sempre None
  → fallback L11b).
- Predecessore: CHG-038 (hotfix kwarg).
- Successore atteso: errata corrige ADR-0017 α'' post ratifica Leader
  (CHG-040+).
- Commit: `4813222`.
