---
id: CHG-2026-04-30-039
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

Implementa `src/talos/orchestrator.py` — pipeline end-to-end di sessione
`run_session(SessionInput) -> SessionResult` che compone tutti i building
block esistenti in una singola chiamata. **Primo punto di ingresso
funzionale per il cruscotto Streamlit futuro.**

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/orchestrator.py` | nuovo (top-level, no directory) | `SessionInput` (frozen dataclass) + `SessionResult` + `run_session(...)` + `_enrich_listino` + `_empty_scored_df` (helper); costanti `KILLED_STATUSES` e `REQUIRED_INPUT_COLUMNS` |
| `tests/unit/test_orchestrator.py` | nuovo | 20 test (defaults, smoke, enriched cols, sort, R-05/R-08, cart/panchina exclusion, budget_t1, R-04 locked-in, validations, frozen, empty, all-killed, no-mutation) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `src/talos/orchestrator.py` con annotazione "gap ADR risolto inline 2026-04-30" |

Quality gate **verde**: ruff (all checks), ruff format (75 files OK),
mypy strict (36 source files, 0 issues), pytest **345 PASS** (325 + 20).

## Why

Tutti i cluster esistono e sono testati in isolamento (`vgp/`, `tetris/`,
`formulas/`). Manca **l'attore che orchestra** i sei step canonici di
sessione:

1. Enrichment del listino raw → 9 colonne calcolate (fee_fba, cash_inflow,
   cash_profit, ROI, q_m, velocity_monthly, qty_target, qty_final, kill_mask).
2. `compute_vgp_score` (CHG-035) → +6 colonne (norm × 3, score_raw, veto, score).
3. Sort `vgp_score` DESC (contratto allocator).
4. `allocate_tetris` (CHG-036) → `Cart` con R-04 + R-06.
5. `build_panchina` (CHG-037) → DataFrame R-09.
6. `compounding_t1` (CHG-032) sui `cash_profit_eur * qty` per item nel cart →
   `Budget_T+1` (R-07 100% reinvestibile).

Senza l'orchestratore, ogni cluster e' un'isola: la UI non avrebbe un
singolo entrypoint da chiamare. **Sblocca il cruscotto Streamlit** (CHG futuro).

### Gap ADR risolto

ADR-0013 prescrive 8 aree consentite (`io_, extract, vgp, tetris, formulas,
persistence, ui, observability, config`). L'orchestratore non e' un cluster
applicativo (e' un coordinatore). Tre opzioni valutate:

- **(A) File top-level** `src/talos/orchestrator.py`: passa il Test di
  Conformita' #1 di ADR-0013 (`find -type d` non vede file). **RATIFICATA
  DAL LEADER 2026-04-30**: *"posizionare l'orchestratore come file top-level
  ... compromesso perfetto tra rispetto formale del Test di Conformita' di
  ADR-0013 e l'evitamento di overhead burocratico (premature abstraction)"*.
- (B) Errata Corrige ADR-0013 estendere a 9 aree → **NON ammissibile**
  (ADR-0009 vieta errata per modifiche di sostanza).
- (C) Promulgare ADR-0022 con `orchestrator/` come 9° area → overhead per
  scope minimo (1 file).

### Decisioni di design

1. **`SessionInput` e `SessionResult` come dataclass `frozen=True`**:
   immutabili, cacheable (utile per `@st.cache_data` Streamlit), test
   `test_session_input_is_frozen` lo blinda.
2. **`_enrich_listino` interno usa `apply` per single-source-of-truth**:
   ogni cella deriva dalle funzioni scalari testate in CHG-022/025/026/038.
   Se una formula cambia, l'orchestratore segue automaticamente. Performance:
   `apply` row-wise e' ~10-100x piu' lento del vettoriale puro su 10k righe;
   vincolo 8.1 ADR-0018 (<500ms su 10k) rivedibile via errata corrige
   post-MVP. Per Samsung MVP (~100-500 righe) il costo e' trascurabile.
3. **`KILLED_STATUSES = ("KILLED", "MISMATCH")`**: tradurre lo status
   nominale dell'extractor in `kill_mask` boolean. Coerente con
   PROJECT-RAW.md sez. 4.1.3 (NLP filter emit MATCH_SICURO / AMBIGUO /
   MISMATCH). Estensibile via errata se emergono altri status.
4. **`budget_t1` calcolato su `cash_profit_per_unit * qty`**: il Cash Profit
   verbatim e' "per pezzo" (CHG-026). Per N pezzi acquistati, profit di
   sessione = `cash_profit * qty`. **Anche locked-in con `vgp_score=0`
   (kill/veto) contribuiscono al budget T+1**: R-04 ha priorita' infinita
   anche sul reinvestimento, il CFO ha forzato il lock-in *consapevolmente*.
5. **Edge case empty listino**: `apply(axis=1)` su DataFrame vuoto ritorna
   `DataFrame` (non Series), rompendo l'assignment di colonne. Cortocircuito
   esplicito con helper `_empty_scored_df` che ritorna DataFrame vuoto
   tipato con colonne attese da `allocate_tetris`/`build_panchina`.
6. **Input non mutato** (`listino_raw.copy()` in `_enrich_listino`): test
   `test_run_session_input_listino_not_mutated` lo verifica.
7. **Output completo `enriched_df`** in `SessionResult`: utile per UI
   dettaglio + audit + futuri test golden Samsung byte-exact (ADR-0019).

### Out-of-scope

- **Telemetria** (`session_started`, `tetris_break_saturation`,
  `veto_roi_applied`): scope ADR-0021 + structlog dispatch.
- **Persistenza DB di `SessionResult`**: scope `persistence/` (CHG futuro,
  consumer di `sessions`/`vgp_results`/`cart_items` tables Allegato A).
- **Versione vettoriale full degli enrichment**: errata futura ADR-0018 se
  profiler richiedera' speedup su listini >>1k righe.
- **Lookup `config_overrides` runtime**: i parametri sono in `SessionInput`
  (UI passa, Streamlit slider). Lookup DB e' scope separato.

## How

### `src/talos/orchestrator.py` (highlight)

```python
@dataclass(frozen=True)
class SessionInput:
    listino_raw: pd.DataFrame
    budget: float
    locked_in: list[str] = field(default_factory=list)
    velocity_target_days: int = 15
    veto_roi_threshold: float = 0.08
    lot_size: int = 5

@dataclass(frozen=True)
class SessionResult:
    cart: Cart
    panchina: pd.DataFrame
    budget_t1: float
    enriched_df: pd.DataFrame

def run_session(inp: SessionInput) -> SessionResult:
    # 0. validate columns
    # edge case: empty listino -> shortcut
    # 1. _enrich_listino (apply scalar formulas row-wise)
    enriched = _enrich_listino(inp.listino_raw, ...)
    # 2. compute_vgp_score (CHG-035)
    scored = compute_vgp_score(enriched, ...)
    # 3. sort DESC
    scored_sorted = scored.sort_values("vgp_score", ascending=False)
    # 4. allocate_tetris (CHG-036)
    cart = allocate_tetris(scored_sorted, ...)
    # 5. build_panchina (CHG-037)
    panchina = build_panchina(scored_sorted, cart)
    # 6. compounding_t1 (CHG-032) on cash_profit * qty per cart item
    cart_profits = [
        float(scored_sorted[scored_sorted["asin"] == item.asin].iloc[0]["cash_profit_eur"])
        * item.qty
        for item in cart.items
    ]
    budget_t1 = compounding_t1(inp.budget, cart_profits)
    return SessionResult(cart, panchina, budget_t1, scored_sorted)
```

### Test plan (20)

- Metadata (2): REQUIRED_INPUT_COLUMNS doc, KILLED_STATUSES content.
- Smoke + enrichment (3): SessionResult shape, enriched_df columns, sort DESC.
- R-05/R-08 (2): killed → vgp_score=0, low ROI vetoed.
- Cart/Panchina (2): exclusion, panchina disjoint cart.
- F3 (1): budget_t1 = budget + Σ(cash_profit*qty).
- R-04 locked-in (2): added first, insufficient budget raises.
- Validations (3): missing columns, invalid budget, low buy_box → fee_fba raise.
- SessionInput (2): defaults, frozen.
- Edge cases (3): empty listino, all killed, no input mutation.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 75 files already formatted |
| Type | `uv run mypy src/` | ✅ 36 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ **345 PASS** (325 + 20) |

**Rischi residui:**
- `apply(axis=1)` su listini >> 1k righe: errata futura ADR-0018 per
  promotion vettoriale (zero apply, algebra inline su Series). Per ora
  Samsung MVP ~100-500 righe, costo trascurabile.
- `match_status` non in `KILLED_STATUSES` viene trattato come "non killed":
  se l'extractor in futuro emette `AMBIGUO`, va aggiunto qui (non c'e'
  fail-safe). Mitigazione: governance test che verifica copertura tra
  `KILLED_STATUSES` e gli status emessi (CHG futuro extractor).
- `cash_profit_per_unit * item.qty` assume che `cash_profit_eur` sia per
  pezzo (CHG-026 verbatim). Se in futuro si decidesse di calcolare il
  cash_profit gia' per qty totale, qui ci sarebbe un double-counting.
  Mitigazione: docstring esplicita + test budget_t1.

## Impact

**Catena completa**: per la prima volta un singolo entrypoint produce il
cruscotto end-to-end (Cart, Panchina, Budget_T+1) da un listino raw +
budget + locked_in. Sblocca:
- UI Streamlit (consumer di `SessionResult`)
- Persistenza `SessionResult` in DB (consumer di Allegato A tables)
- Telemetria di sessione (consumer di structlog events)

`gitnexus_detect_changes`: rilevera' i nuovi simboli al prossimo
`gitnexus analyze` post-merge.

## Refs

- ADR: ADR-0018 (algoritmo VGP/Tetris + R-01..R-09 + R-07 reinvestimento),
  ADR-0014 (mypy/ruff strict), ADR-0013 (struttura — gap risolto inline),
  ADR-0019 (test pattern unit)
- Predecessori: CHG-022/025/026/032/034/035/036/037/038 (tutti i building
  block scalari + vettoriali consumati dall'orchestratore)
- Vision verbatim: PROJECT-RAW.md sez. 4 (Leggi R-01..R-09) + 6 (Formule)
- Successore atteso: UI Streamlit (`src/talos/ui/dashboard.py` ADR-0016)
  consumer di `SessionResult`; persistenza `SessionResult` in DB
- Commit: `[pending]`
