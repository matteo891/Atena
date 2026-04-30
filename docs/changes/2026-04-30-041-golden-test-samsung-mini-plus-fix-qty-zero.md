---
id: CHG-2026-04-30-041
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 1615206
adr_ref: ADR-0019, ADR-0018, ADR-0014, ADR-0013
---

## What

Doppio risultato nello stesso CHG:

1. **Bug fix in `tetris/allocator.py` Pass 2**: rilevato dal golden smoke
   che un ASIN con `qty_final=0` (F5 azzera quando `qty_target < lot_size`)
   entrava comunque nel cart con `cost_total=0`. Il Pass 2 ora skippa
   `qty_value <= 0` con motivazione esplicita.
2. **Mini-golden test `tests/golden/test_pipeline_samsung_mini.py`**:
   scenario fissato 10 ASIN che copre tutti i casi canonici (R-04
   locked-in, R-05 kill, R-08 veto, F5 floor, saturazione parziale,
   panchina). 13 test snapshot byte-exact (tolerance 1e-6 EUR / 1e-5
   score).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/tetris/allocator.py` | modificato | Pass 2: `if qty_value <= 0: continue` (skip F5-azzerati) + noqa `C901` con motivazione (cyclomatic 11) |
| `tests/unit/test_tetris_allocator.py` | modificato | +1 test `test_skip_zero_qty_final_in_pass_2` |
| `tests/golden/__init__.py` | nuovo | Package marker (vuoto) |
| `tests/golden/test_pipeline_samsung_mini.py` | nuovo | 13 test golden (cart asin/locked/qty/total/saturation, panchina, budget_t1, vgp_score per ASIN, veto/kill flags, sentinella qty=0/killed/vetoed) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry mini-golden |

Quality gate **verde**: ruff (all checks), ruff format (80 files OK),
mypy strict (38 source files, 0 issues), pytest **367 PASS** (354 unit/governance + 13 golden).

## Why

Senza un golden test, ogni futura modifica alla pipeline (errata
corrige formule, refactor vettoriale, aggiunta colonne) rischia di
introdurre drift silenziosi. Il mini-golden e' una **sentinella forte**:
fissato il listino e i parametri, l'output deve restare identico
entro tolerance.

Differenza vs `tests/unit/test_value_chain.py` (CHG-028/033):
- `test_value_chain` testa la **catena scalare riga per riga** (F1->F2->F3
  + ROI + Veto), no DataFrame.
- `test_pipeline_samsung_mini` testa la **pipeline vettoriale completa**
  via `run_session(SessionInput) -> SessionResult` con scenario fissato.
- Sentinelle complementari, non ridondanti.

### Bug rilevato durante la costruzione del golden

Nel primo smoke run dello scenario, `S010_TINY` (q_m=2.0, qty_target=1.0,
qty_final=Floor(1/5)*5=0) appariva nel `Cart` con `qty=0, cost=0`. Bug
logico: l'allocator deve skippare le righe non comprabili (R-06 letterale:
*"item con costo compatibile"* — cost=0 e' tecnicamente "compatibile"
ma semanticamente no-op).

Fix: `if qty_value <= 0: continue` nel Pass 2. Il Pass 1 (R-04 locked-in)
**non skippa** perche' un locked-in con qty=0 e' un edge case dell'utente
(forzare un ASIN non-acquistabile) — il sistema obbedisce, ma il caller
deve sapere. Future-proofing: governance test che warna se locked-in
ha qty_final=0 (CHG futuro).

### Decisioni di design

1. **Mini (10 ASIN) invece di 1000 ASIN**: il dataset Samsung 1000 ASIN
   citato in PROJECT-RAW.md richiede acquisizione reale (via
   `io_/extract` futuro). Il mini-golden e' il preludio testabile ora;
   il 1000-ASIN sara' aggiunto quando l'extractor produrra' input reali.
2. **Tolerance differenziate**: 1e-6 EUR (denominazioni monetarie),
   1e-5 score (formula composita con normalizzazione + pesi accumula
   drift float64). Lo snapshot e' a 6 decimali (round print), il valore
   reale puo' avere drift entro 1e-6: `0.929800` snapshot vs `0.9297996...`
   reale.
3. **13 test in 1 file**: ognuno verifica una proprieta' (cart asin,
   cart qty, cart total, cart saturation, panchina order, budget_t1,
   vgp_scores per ASIN, veto/kill flags) + 3 sentinelle regression
   (qty=0 / killed / vetoed esclusi). Granularita' alta = messaggio
   chiaro quando qualcosa drifta.
4. **`pytestmark = pytest.mark.golden`**: marker dedicato per esecuzione
   isolata (`pytest -m golden`). Configurato in `pyproject.toml [tool.pytest]`.
5. **Snapshot hardcoded come costanti modulo**: `_EXPECTED_*` in cima al
   file, davanti agli occhi del lettore. Modifica deliberata richiede
   lettura del CHG che documenta il cambio di pipeline.
6. **`SessionResult` typed** (non `object`): rimosso `# type: ignore[attr-defined]`
   perche' SessionResult ora viene importato dal modulo orchestrator.

### Out-of-scope

- **Golden dataset Samsung 1000 ASIN**: scope CHG futuro post `io_/extract`.
- **Test golden vettoriale puro** (senza orchestrator, solo
  `compute_vgp_score` + sort): scope errata corrige se serve isolare
  un livello.
- **Snapshot JSON files** (`samsung_mini_listino.json`,
  `samsung_mini_expected.json`): per ora i valori sono inline nel test
  (10 ASIN sono gestibili). Per il 1000-ASIN avra' senso JSON esterno.

## How

### Fix `src/talos/tetris/allocator.py`

```python
# Pass 2 (R-06): VGP decrescente. Skip vgp_score==0. Skip qty<=0. Continue su cost > remaining.
for _, row in vgp_df[~vgp_df[asin_col].isin(locked_set)].iterrows():
    score = float(row[score_col])
    if score == 0.0:
        continue
    qty_value = int(row[qty_col])
    if qty_value <= 0:
        # F5 ha azzerato (qty_target sotto soglia lotto fornitore): non comprabile.
        continue
    cost_total = float(row[cost_col]) * qty_value
    if cost_total > cart.remaining:
        continue
    cart.add(CartItem(..., qty=qty_value, ...))
    if cart.saturation >= SATURATION_THRESHOLD:
        break
```

### Snapshot atteso (10 ASIN)

```
Cart: S004_GOOD (locked, qty=5, cost=1200), S005_LOW (qty=5, cost=900), S003_MID (qty=5, cost=1500)
Cart total: 3600.0  Saturation: 0.72  Budget: 5000
Panchina: S002_HIGH (vgp=0.93), S001_TOP (vgp=0.89), S010_TINY (vgp=0.33)
Budget T+1: 6187.208180
Vetoed: S006_VETO (ROI=-0.14), S007_VETO2 (ROI=-0.20)
Killed: S008_KILL (MISMATCH), S009_KILL2 (KILLED)
```

### Test plan

- Allocator (1 nuovo): `test_skip_zero_qty_final_in_pass_2` con 3 ASIN
  (1 con qty=0, skippato; 2 normali, allocati).
- Golden (13): cart asin/locked/qty/total/saturation, panchina asin,
  budget_t1, vgp_scores per asin, veto_passed flags, kill_mask flags,
  sentinelle qty=0/killed/vetoed.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 80 files already formatted |
| Type | `uv run mypy src/` | ✅ 38 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ 354 PASS (353 + 1) |
| Golden | `uv run pytest tests/golden -q` | ✅ **13 PASS** |
| Combined | `uv run pytest tests/golden tests/unit tests/governance -q` | ✅ **367 PASS** |

**Rischi residui:**
- Tolerance score 1e-5 lascia margine: drift ~1e-7 e' tollerato (in
  realta' atteso da float64). Se in futuro emerge necessita' di
  byte-exact stringente (es. requirement legale), errata corrige
  ADR-0019 con aggiornamento snapshot a piu' cifre.
- Cyclomatic complexity di `allocate_tetris` ora 11 (sopra soglia 10):
  noqa `C901` con motivazione. Refactor in 2 funzioni (Pass 1 + Pass 2)
  e' opzione futura ma frammenta lettura della semantica ADR-0018.
- Locked-in con `qty_final=0` ancora ammesso (Pass 1 non skippa). Non
  documentato dal test; futuro CHG con governance check + warning.

## Impact

`allocate_tetris` cambia comportamento per il sotto-caso `qty_final=0`:
- Vecchio: entrava in cart con `cost=0` (no-op visivo, ma confusione).
- Nuovo: skippato (correctness + leggibilita').
- Test esistenti tutti verdi (nessun test esistente usava qty=0).

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze` la
modifica della funzione `allocate_tetris` (signature invariata, body
modificato) + i nuovi simboli golden.

## Refs

- ADR: ADR-0019 (test strategy + golden), ADR-0018 (algoritmo —
  semantica R-06), ADR-0014 (mypy/ruff strict), ADR-0013 (struttura
  `tests/golden/`)
- Predecessori: CHG-2026-04-30-036 (allocator), CHG-2026-04-30-039
  (orchestrator)
- Vision verbatim: PROJECT-RAW.md sez. 7 ("Suite pytest che copre tutti
  i moduli ... fixture di listino noto con risultato VGP + carrello
  Tetris atteso byte-exact")
- Successore atteso: golden Samsung 1000 ASIN (post `io_/extract`)
- Commit: `1615206`
