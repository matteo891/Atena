---
id: CHG-2026-04-30-035
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

Implementa `vgp/score.py` con `compute_vgp_score(df, ...)` — formula VGP
composita verbatim PROJECT-RAW.md sez. 6.3 (`norm(ROI)*0.4 +
norm(Velocity)*0.4 + norm(Cash_Profit)*0.2`) + applicazione vettoriale di
**R-05 KILL-SWITCH** e **R-08 VETO ROI** sul DataFrame. Pesi esposti come
costanti modulo `ROI_WEIGHT`, `VELOCITY_WEIGHT`, `CASH_PROFIT_WEIGHT`.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/vgp/score.py` | nuovo | `compute_vgp_score(df, *, roi_col, velocity_col, cash_profit_col, kill_col, veto_roi_threshold)` → DataFrame copia con 6 colonne aggiunte (`roi_norm`, `velocity_norm`, `cash_profit_norm`, `vgp_score_raw`, `veto_roi_passed`, `vgp_score`) |
| `src/talos/vgp/__init__.py` | modificato | +re-export `compute_vgp_score`, `ROI_WEIGHT`, `VELOCITY_WEIGHT`, `CASH_PROFIT_WEIGHT` |
| `tests/unit/test_vgp_score.py` | nuovo | 15 snapshot/edge case (incl. boundary R-08, override threshold, override colonne, index preserved, no mutation input) + 2 property-based Hypothesis |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `src/talos/vgp/score.py`; aggiornata entry `vgp/__init__.py` |

Quality gate **verde**: ruff (all checks passed), ruff format (66 files OK),
mypy strict (31 source files, 0 issues), pytest **267 PASS** (250 + 17 nuovi).

## Why

CHG-034 ha aperto la frontiera vettoriale con `min_max_normalize` (1 colonna).
Questo CHG ne e' il consumatore naturale: applica `min_max_normalize` su 3
colonne (ROI, Velocity, Cash_Profit) e compone il VGP Score. Senza, la
primitiva resta isolata e la "monarchia VGP" (PROJECT-RAW.md sez. 4.1.4)
non ha implementazione vettoriale.

Tre motivi per fermarsi a "scoring puro" (e non a `compute_vgp_session`
pieno di ADR-0018):
1. **Scope minimo testabile**: assumo colonne `roi`/`velocity`/`cash_profit`/
   `kill_mask` gia' calcolate dal caller. F1/F2/F4/F5 e velocity_monthly
   restano scope dell'orchestratore di sessione futuro.
2. **Tre filtri non-banali da blindare in isolato** (R-05, R-08, weighted sum):
   ognuno con boundary case dedicato (kill esclusivo, veto esclusivo, mix,
   boundary R-08 a 0.08).
3. **Sblocca Tetris** (CHG-036): `compute_vgp_score` produce il DataFrame
   ordinabile per `vgp_score` — input diretto dell'allocator R-06 + R-04.

### Decisioni di design

1. **Pesi come costanti modulo** (`ROI_WEIGHT`, `VELOCITY_WEIGHT`,
   `CASH_PROFIT_WEIGHT`): leggibili dal call site, testabili in
   `test_weights_sum_to_one`, modificabili solo via errata corrige
   ADR-0018 (regola ADR-0009).
2. **R-05 + R-08 applicati con `where(~blocked, 0.0)`** (vettoriale puro,
   no `apply` row-wise). Boundary R-08 inclusivo (`>=` come la primitiva
   scalare `is_vetoed_by_roi`).
3. **Colonna `vgp_score_raw` esposta** prima dell'azzeramento: utile per
   audit/debug. Tetris userà `vgp_score` finale.
4. **Override colonne via kwargs**: nomi default (`roi`, `velocity_monthly`,
   `cash_profit_eur`, `kill_mask`) sono i piu' probabili contratti
   downstream, ma il caller puo' sovrascriverli. Test
   `test_custom_column_names` lo verifica.
5. **`copy()` esplicita** all'ingresso: input intoccato (`test_input_dataframe_not_mutated`).
6. **`import pandas` in `TYPE_CHECKING`**: lo score usa solo metodi sui
   DataFrame (no `pd.Something` runtime), quindi lint TC002 lo permette.
   Nello `normalize.py` invece pandas era runtime per `pd.Series(0.0, ...)`.

### Out-of-scope

- `compute_vgp_session` pieno (ADR-0018) con calcolo F1/F2/F4/F5 inline.
- Telemetria evento `veto_roi_applied` (richiede primo orchestrator).
- Golden test Samsung byte-exact (richiede pipeline completa).
- Lookup `config_overrides` per soglia ROI runtime (CHG separato).

## How

### `src/talos/vgp/score.py`

```python
ROI_WEIGHT = 0.4
VELOCITY_WEIGHT = 0.4
CASH_PROFIT_WEIGHT = 0.2

def compute_vgp_score(df, *, roi_col="roi", velocity_col="velocity_monthly",
                     cash_profit_col="cash_profit_eur", kill_col="kill_mask",
                     veto_roi_threshold=DEFAULT_ROI_VETO_THRESHOLD):
    # validazioni R-01 (threshold range, colonne presenti)
    out = df.copy()
    kill_mask = out[kill_col].astype(bool)
    out["roi_norm"] = min_max_normalize(out[roi_col], kill_mask)
    out["velocity_norm"] = min_max_normalize(out[velocity_col], kill_mask)
    out["cash_profit_norm"] = min_max_normalize(out[cash_profit_col], kill_mask)
    out["vgp_score_raw"] = (out["roi_norm"]*ROI_WEIGHT
                          + out["velocity_norm"]*VELOCITY_WEIGHT
                          + out["cash_profit_norm"]*CASH_PROFIT_WEIGHT)
    out["veto_roi_passed"] = out[roi_col] >= veto_roi_threshold
    blocked = kill_mask | ~out["veto_roi_passed"]
    out["vgp_score"] = out["vgp_score_raw"].where(~blocked, 0.0)
    return out
```

### Test plan (17 test)

Snapshot deterministici (15):
1. `test_weights_sum_to_one` — invariante 0.4+0.4+0.2 == 1.0
2. `test_baseline_no_kill_no_veto` — 3 ASIN, top→1.0, bottom→0.0, middle calcolato
3. `test_input_dataframe_not_mutated`
4. `test_added_columns_present` — 6 colonne attese
5. `test_r05_kill_zeros_score` — kill esclusivo
6. `test_r08_veto_zeros_score` — veto esclusivo
7. `test_r08_boundary_inclusive` — ROI=0.08 PASSA
8. `test_all_killed_all_zero`
9. `test_all_vetoed_all_zero`
10. `test_mixed_kill_and_veto`
11. `test_threshold_override` — threshold=0.20
12. `test_threshold_invalid_raises` — soglia 0 o > 1
13. `test_missing_columns_raises`
14. `test_custom_column_names`
15. `test_index_preserved`

Property-based (2) — Hypothesis:
- `test_property_score_in_unit_range_when_active` — vgp_score ∈ [0,1] per righe attive
- `test_property_killed_row_score_zero` — kill_mask=True ⇒ vgp_score=0

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 66 files already formatted |
| Type | `uv run mypy src/` | ✅ 31 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ **267 PASS** (250 + 17) |

**Rischi residui:**
- Hypothesis range `floats(min=0.08, max=2.0)` per ROI evita boundary
  numerici a `±inf` o sotto soglia (test cover il caso passato). I test
  scenario "tutti vetati" coprono ROI < soglia.
- `pandas.Series.where(cond, other)` mantiene `cond=True`. Inversione
  `~blocked` deliberata per leggere "azzera dove blocked" (snapshot test
  conferma).
- `copy()` profonda di default in pandas 2.x: ovvio per piccoli listini
  Samsung MVP, monitorare a 10k+ righe (eventualmente `copy(deep=False)`
  in errata futura).

## Impact

`gitnexus_detect_changes`: risk **LOW**, 3 sezioni FILE-ADR-MAP touched, 0
processi affetti. I nuovi simboli (`compute_vgp_score`, costanti pesi)
saranno visti dall'indice GitNexus al prossimo `gitnexus analyze` post-merge.

`min_max_normalize` ora ha il primo caller architetturale (era sink puro
in CHG-034). `is_vetoed_by_roi` resta primitiva scalare per single-row
contexts (orchestratore, debug); la versione vettoriale e' inline in
`compute_vgp_score` per evitare overhead di `Series.apply`.

## Refs

- ADR: ADR-0018 (formula VGP + R-05 + R-08), ADR-0014 (mypy/ruff strict),
  ADR-0013 (`vgp/`), ADR-0019 (test pattern unit + Hypothesis)
- Predecessori: CHG-2026-04-30-027 (`vgp/veto.py` scalare), CHG-2026-04-30-034
  (`vgp/normalize.py`)
- Vision verbatim: PROJECT-RAW.md sez. 6.3 (formula) + righe 223 (R-05) + 226 (R-08)
- Successore atteso: `tetris/allocator.py` con R-06 saturazione 99.9% + R-04
  Locked-in priority∞ — consumatore di `compute_vgp_score`
- Commit: `[pending]`
