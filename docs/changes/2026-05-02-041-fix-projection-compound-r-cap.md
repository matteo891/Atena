---
id: CHG-2026-05-02-041
date: 2026-05-02
adr_ref: ADR-0016, ADR-0018, ADR-0019, ADR-0014
commit: TBD
---

## What

Hotfix proiezione annua compound esplosiva. Bug live Leader 2026-05-02:
proiezione €11M su budget €6k (con cart r=30%, 24 cicli/anno).
Cap r conservativo allineato a ScalerBot500K.

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py:_compute_cycle_kpis` | + costante `_PROJECTION_R_MAX_CAP = 0.15` (15% max per ciclo). + costante `_PROJECTION_R_DELTA_TOLERANCE = 0.001`. + nuovo kwarg `veto_roi_threshold: float = 0.08`. + nuova chiave dict `projection_r_pct` = `clamp(profit_cost_pct, [veto_threshold, MAX_CAP])`. Proiezione ora usa `(1 + projection_r_pct)^cycles_per_year` invece di `(1 + profit_cost_pct)^N`. |
| `src/talos/ui/dashboard.py:_render_cycle_overview` | Meta tile proiezione esplicita r conservativo + r effettivo del cart se differiscono ("r conservativo X% (cart effettivo Y%, capped)"). |
| `src/talos/ui/dashboard.py:main()` caller | Passa `veto_roi_threshold` a `_compute_cycle_kpis`. |
| `tests/unit/test_dashboard_cycle_overview.py` | + 3 test (high actual r capped, low actual r floor a veto, mid r passthrough). |

## Why

Bug live Leader 2026-05-02 post-deploy CHG-040 errata fee_fba atomica:
con la fee atomica corretta (~€3 invece di €22), molti ASIN ora
producono ROI 30%+ → cart con r=30% × 24 cicli/anno → proiezione
matematicamente €11M (ma irrealistica).

Diagnosi: la formula `Budget·(1+r)^N` esplode esponenzialmente per
r alti. ScalerBot500K mostra €52k su €6k (28 cicli) → r implicito ~8%
(usa la **soglia veto** come r conservativo, non il r effettivo).

Soluzione: cap r in `[veto_threshold, 15%]` per la proiezione. Il r
effettivo del cart resta visibile come KPI tile separato
("Profitto/Costo %"), ma per la proiezione annua usiamo:
- floor = veto_threshold (8% default) → realistico minimo R-08.
- cap = 15% → evita esplosioni su cart eccezionali.

Esempi proiezione post-CHG-041:
- r=30% effettivo → projection_r=15% → 6000·1.15^24.3 ≈ €165k.
- r=12% effettivo → projection_r=12% (passthrough) → 6000·1.12^24.3 ≈ €91k.
- r=5% effettivo → projection_r=8% (floor veto) → 6000·1.08^24.3 ≈ €38k.

R-01 NO SILENT DROPS: il cap NON è silente. Meta tile UI esplicita
"r conservativo X% (cart effettivo Y%, capped)" quando i due
divergono.

## Tests

ruff/format/mypy strict OK. **1052 PASS** (+3 vs 1049 CHG-040).

3 test sentinel:
- `projection_r_cap_high_actual_r`: r=30% → capped a 15%.
- `projection_r_floor_low_actual_r`: r=5% < veto 8% → floor a 8%.
- `projection_r_passthrough_in_range`: r=12% (in range) → passthrough.

## Test di Conformità

- ADR-0016 (UI): puro Streamlit + helper puro testabile.
- ADR-0018 (formule): F3 compounding invariato; il cap è solo
  visualizzazione UX, non cambia il `budget_t1` calcolato dall'orchestrator.
- ADR-0019: test parametrici boundary (veto/cap/range).
- R-01 NO SILENT DROPS: meta tile esplicita il cap.

## Refs

- ADR-0016, ADR-0018.
- Bug Leader live 2026-05-02 post-CHG-040.
- ScalerBot500K screenshot: r implicito 8% per proiezione (= soglia
  veto, allineamento ratificato).
- Predecessore: CHG-040 (errata fee_fba atomica che ha amplificato
  il problema rendendo r effettivi più alti).
- Commit: TBD.
