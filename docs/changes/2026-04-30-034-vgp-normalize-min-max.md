---
id: CHG-2026-04-30-034
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

Inaugura la **frontiera vettoriale** di Talos: introdotte `numpy` + `pandas`
come prime dipendenze applicative pesanti, e implementata `vgp/normalize.py`
con `min_max_normalize(series, kill_mask)` — primitiva L04b verbatim ADR-0018
sez. `_min_max_normalize`. Primo modulo Talos che opera su `pd.Series`.

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | +`numpy>=2.0,<3` +`pandas>=2.2,<3` (runtime); +`pandas-stubs>=2.2` (dev, mypy strict) |
| `uv.lock` | modificato | rigenerato (`uv sync`); +8 pacchetti (numpy 2.4.4, pandas 2.3.3, pandas-stubs 3.0.0, dateutil, pytz, six, tzdata + rebuild talos) |
| `src/talos/vgp/normalize.py` | nuovo | `min_max_normalize(series, kill_mask) -> pd.Series` — esclude righe KILLED da `min`/`max` |
| `src/talos/vgp/__init__.py` | modificato | +re-export `min_max_normalize`; docstring aggiornato (cluster vettoriale) |
| `tests/unit/test_vgp_normalize.py` | nuovo | 10 snapshot/edge case + 3 property-based (Hypothesis): range `[0,1]`, `min→0`, `max→1` |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `src/talos/vgp/normalize.py`; aggiornata entry `vgp/__init__.py` |

Quality gate **verde**: ruff (all checks passed), ruff format (64 files OK),
mypy strict (30 source files, 0 issues), pytest **250 PASS** (237 + 13 nuovi).

## Why

ADR-0018 marca la pipeline VGP come **vettoriale Numpy/pandas** (vincolo 8.1:
*"vettorizzazione rigorosa per gestire 10k righe senza colli di bottiglia
RAM"*). La catena scalare F1→F2→F3 + ROI + Veto R-08 (chiusa in
`milestone/first-formula-v1.0.0`) e' il livello "building block";
`min_max_normalize` apre il livello vettoriale per il listino di sessione.

Tre motivi per inaugurare ora:
1. **Primo modulo che usa pandas**: rompe l'inerzia. Tutti i CHG futuri di
   `vgp/score.py`, `vgp/`, `tetris/` ne dipendono.
2. **Edge case L04b ratificato in Round 4** (memory `project_f1_referral_structure_confirmed.md`
   non riapre F1 ma L04b e' ortogonale): convenzione `max==min → 0.0` e
   `eligible vuoto → 0.0` documentate verbatim ADR-0018, mai implementate.
3. **Dimensione minima**: una funzione pura, una colonna alla volta. Niente
   pipeline N-righe full ancora — quella e' `vgp/score.py` (CHG successivo).

### Decisioni di design

1. **Funzione pubblica `min_max_normalize`** (no underscore). ADR-0018 la mostra
   come `_min_max_normalize` privata, ma in `normalize.py` e' l'unico simbolo:
   esposta come API del modulo per testabilita' isolata (coerente con
   `fee_fba_manual`, `cash_inflow_eur`, ecc).
2. **Validazione index parallela**: `series.index.equals(kill_mask.index)`
   con `ValueError` esplicito se disallineati. Coerente R-01 NO SILENT DROPS.
   Pandas allineerebbe per indice silenziosamente, mascherando bug a monte.
3. **Edge case `eligible` vuoto e `max==min` -> 0.0**: convenzione L04b verbatim
   ADR-0018. Il termine "non discrimina" -> contributo 0 al VGP. Stessa serie 0.0
   con `index` originale preservato.
4. **Riga killed riceve formula applicata** (puo' uscire da `[0,1]`): scelta
   coerente ADR-0018. Sara' azzerata downstream da `score.py` (R-05 hardware
   kill-switch). Test `test_kill_excluded_from_min_max` documenta il valore 33.0
   come **comportamento atteso**, non bug.
5. **Property-based tests con `st.lists(floats)`**: niente `hypothesis.extra.pandas`
   per minimizzare le dipendenze. Le serie sono costruite a partire da liste —
   stesso valore probatorio.
6. **`numpy 2.x` + `pandas 2.2+`**: range conservativi. Stack moderno (Python 3.11).
   `pandas-stubs` necessario per mypy strict (pandas non ha annotazioni inline complete).

### Out-of-scope

- **Pipeline VGP completa** (`compute_vgp_session` di ADR-0018): scope `vgp/score.py`.
- **Veto vettoriale** sul DataFrame N-righe: scope `vgp/veto.py` esteso.
- **Golden test Samsung** (`tests/golden/test_samsung_1000.py`): scope quando
  esiste l'orchestratore di sessione completo.
- **Decimal**: niente Decimal (coerente F1/F2/F3 scalari). Pandas usa float64.

## How

### `src/talos/vgp/normalize.py`

```python
def min_max_normalize(series: pd.Series, kill_mask: pd.Series) -> pd.Series:
    if not series.index.equals(kill_mask.index):
        raise ValueError("...indici devono coincidere...")
    eligible = series[~kill_mask]
    if len(eligible) == 0:
        return pd.Series(0.0, index=series.index)
    min_val = float(eligible.min())
    max_val = float(eligible.max())
    if max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)
```

### Test plan (13 test)

Snapshot (10):
1. `test_no_kill_simple_series` — [10,20,30] → [0, 0.5, 1.0]
2. `test_kill_excluded_from_min_max` — riga killed con valore fuori range eligible
3. `test_all_killed_returns_zero_series` — eligible vuoto
4. `test_max_equals_min_returns_zero_series` — tutti identici
5. `test_single_eligible_returns_zero_series` — 1 sola eligible (max==min)
6. `test_negative_values_supported` — Cash_Profit puo' essere negativo
7. `test_preserves_index` — index `["a","b","c"]` preservato
8. `test_mismatched_index_raises_value_error` — R-01 esplicito
9. `test_empty_series` — len 0 → len 0
10. `test_two_distinct_values` — caso minimo discriminante

Property-based (3) — Hypothesis su `st.lists(floats, 2..50)`:
- `test_property_no_kill_normalized_in_unit_range` — output ∈ [0,1] (assume max≠min)
- `test_property_min_maps_to_zero`
- `test_property_max_maps_to_one`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 64 files already formatted |
| Type | `uv run mypy src/` | ✅ 30 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ **250 PASS** (237 + 13) |

**Rischi residui:**
- Hypothesis `st.lists(min_value=-1e6, max_value=1e6)`: range scelto per evitare
  precisione `float64` borderline. In pratica i valori reali Talos (ROI in `[-1, 5]`,
  Cash_Profit in `[-10k, +10k]`, Velocity in `[0, +∞)`) sono dentro questo range.
- `numpy 2.4.4` (>= 2.4 introduce nuovi warning): se in CI escono `DeprecationWarning`
  pandas-related, gestiti via `pyproject.toml [tool.pytest]` se necessario.
- `pandas-stubs` puo' divergere dalla versione effettiva di pandas in futuri upgrade.
  Mitigazione: pin del minor (`>=2.2`).

## Impact

`gitnexus_detect_changes`: risk **LOW**, 4 simboli touched, 0 processi affetti.
- 3 sezioni di FILE-ADR-MAP.md (touched)
- `__all__` in `vgp/__init__.py` (re-export esteso)

I nuovi simboli (`min_max_normalize`, modulo `normalize.py`, test) non figurano
nell'indice GitNexus pre-commit (sono unstaged): saranno indicizzati al prossimo
`gitnexus analyze` post-merge (workflow `gitnexus.yml`, ADR-0020).

Il modulo `normalize.py` e' un **sink puro**: nessun caller esistente. Diventera'
caller-of `score.py` quando quello sara' implementato (CHG successivo).

## Refs

- ADR: ADR-0018 (algoritmo VGP — sez. `_min_max_normalize` + property tests),
  ADR-0014 (mypy/ruff strict + pandas-stubs), ADR-0013 (struttura `vgp/`),
  ADR-0019 (test pattern unit + Hypothesis)
- Predecessori: CHG-2026-04-30-027 (`vgp/veto.py` scalare),
  `milestone/first-formula-v1.0.0` (`cc4070e` — catena scalare chiusa)
- Vision verbatim: PROJECT-RAW.md L04b (Round 4) + ADR-0018 sez. "Decisione"
- Successore atteso: `vgp/score.py` con `compute_vgp_session(listino, config)` —
  consumatore principale di `min_max_normalize` su 3 colonne (ROI, Velocity,
  Cash_Profit)
- Commit: `[pending]`
