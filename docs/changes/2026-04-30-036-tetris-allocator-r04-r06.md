---
id: CHG-2026-04-30-036
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 4747382
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

Inaugura `src/talos/tetris/` con l'allocator greedy di sessione:

- `tetris/allocator.py` — `allocate_tetris(vgp_df, budget, locked_in, ...)`
  con Pass 1 (R-04 locked-in priorita' infinita) + Pass 2 (R-06 scansione VGP DESC,
  saturazione 99.9%).
- `Cart` (dataclass) e `CartItem` (frozen dataclass) — modello del carrello
  con `total_cost`, `remaining`, `saturation`, `asin_list()`.
- `InsufficientBudgetError(ValueError)` — fail-fast quando un locked-in non
  sta nel budget residuo (R-01 NO SILENT DROPS).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/tetris/__init__.py` | nuovo | Package marker; re-export `allocate_tetris`, `Cart`, `CartItem`, `InsufficientBudgetError`, `SATURATION_THRESHOLD` |
| `src/talos/tetris/allocator.py` | nuovo | Allocator + dataclass + eccezione |
| `tests/unit/test_tetris_allocator.py` | nuovo | 19 test (3 Cart + 4 base allocator + 1 partial saturation + 6 R-04 + 4 validation + 1 ordering) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `tetris/__init__.py` e `tetris/allocator.py` |

Quality gate **verde**: ruff (all checks), ruff format (69 files OK),
mypy strict (33 source files, 0 issues), pytest **286 PASS** (267 + 19).

## Why

CHG-035 ha chiuso lo scoring: ogni ASIN ha un `vgp_score` finale (R-05/R-08
gia' applicati). Manca chi consuma quel ranking per costruire il carrello di
sessione: **R-06 TETRIS ALLOCATION** (PROJECT-RAW.md riga 224) e **R-04
Manual Override locked-in** (sez. 4.1.13).

Senza l'allocator non c'e' carrello. Senza carrello, l'orchestratore di
sessione non ha output utilizzabile dalla UI Streamlit (cruscotto militare).

### Decisioni di design

1. **`Cart` come dataclass mutabile + `CartItem` frozen**: `Cart` accumula
   incrementalmente; `CartItem` e' uno snapshot immutabile di una riga al
   momento dell'allocazione (asin, cost_total, qty, vgp_score, locked).
   Pattern coerente con builder + value-object.
2. **Caller responsabile dell'ordinamento `vgp_df`**: l'allocator NON
   riordina il DataFrame in input (Pass 2 itera in ordine di iterazione del
   DataFrame). Test `test_index_does_not_affect_pass_2_order` documenta:
   se il caller passa `vgp_df` non ordinato, l'output rispetta l'ordine
   passato. Razionale: separation of concerns; `compute_vgp_score`
   non ordina (CHG-035), il chiamante orchestratore lo fara' con
   `.sort_values('vgp_score', ascending=False)`.
3. **`InsufficientBudgetError` per locked-in only**: il Pass 2 fa
   `continue` (R-06 letterale: *"prosegue cercando item con VGP inferiore
   ma costo compatibile"*); solo il Pass 1 puo' raisare, perche' R-04 e'
   un vincolo HARD del Leader (Lock-in del CFO, niente silent drop).
4. **`SATURATION_THRESHOLD = 0.999` come costante modulo**: verbatim
   PROJECT-RAW.md riga 224. Modifica via errata corrige ADR-0018.
5. **`asin in locked_in` come set semantics**: ASIN duplicati nel parametro
   `locked_in` non causano doppia allocazione (Pass 2 esclude tutti i
   locked tramite `~vgp_df[asin_col].isin(locked_set)`).
6. **Locked-in con `vgp_score=0` (kill o veto) entra comunque**: priorita'
   infinita di R-04 sovrascrive R-05/R-08. Il CFO ha forzato il lock-in
   *consapevolmente*; il sistema obbedisce. Test
   `test_r04_locked_in_with_zero_vgp_score_still_allocated`.
7. **Override colonne via kwargs**: stesso pattern di `compute_vgp_score`
   (CHG-035) — `asin_col`, `cost_col`, `qty_col`, `score_col`. Default
   coerenti col contratto downstream tipico.

### Out-of-scope

- **R-09 Panchina** (archivio idonei scartati per capienza): scope
  `tetris/panchina.py` (CHG futuro). L'allocator restituisce solo `Cart`,
  non distingue "scartato per costo" da "scartato per veto".
- **F4 + F5 (`qty_target`, `qty_final`)**: assume gia' precalcolati nel
  `vgp_df`. Calcolo inline nell'orchestratore di sessione futuro.
- **Telemetria evento `tetris_break_saturation`**: richiede primo
  orchestrator + structlog event dispatch.
- **Sort `vgp_df` interno**: deliberatamente non fatto (vedi decisione 2).

## How

### `src/talos/tetris/allocator.py` (highlight)

```python
SATURATION_THRESHOLD = 0.999

@dataclass(frozen=True)
class CartItem:
    asin: str
    cost_total: float
    qty: int
    vgp_score: float
    locked: bool = False

@dataclass
class Cart:
    budget: float
    items: list[CartItem] = field(default_factory=list)

    @property
    def remaining(self) -> float: ...
    @property
    def saturation(self) -> float: ...

class InsufficientBudgetError(ValueError): ...

def allocate_tetris(vgp_df, budget, locked_in, *, asin_col="asin", ...):
    cart = Cart(budget=budget)
    locked_set = set(locked_in)
    # Pass 1 (R-04): locked-in fail-fast
    for asin in locked_in:
        ...
        if cost_total > cart.remaining:
            raise InsufficientBudgetError(...)
        cart.add(CartItem(..., locked=True))
    # Pass 2 (R-06): VGP DESC, continue su over-budget, break su saturazione
    for _, row in vgp_df[~vgp_df[asin_col].isin(locked_set)].iterrows():
        if score == 0.0: continue
        if cost_total > cart.remaining: continue
        cart.add(CartItem(..., locked=False))
        if cart.saturation >= SATURATION_THRESHOLD: break
    return cart
```

### Test plan (19 test)

- Cart base (3): remaining, add update, saturation clamped.
- Allocator base (4): basic_top_first, skip_zero_vgp, continue_on_too_expensive, break_on_saturation.
- Partial saturation (1): listino non saturabile -> tutti allocati senza break.
- R-04 (6): added_first, zero_score_still_allocated, skipped_in_pass_2, insufficient_for_first, two_locked_second_too_expensive, not_in_df.
- Validation (4): invalid_budget, missing_columns, custom_column_names, empty_df.
- Ordering (1): allocator non riordina (caller responsibility).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 69 files already formatted |
| Type | `uv run mypy src/` | ✅ 33 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ **286 PASS** (267 + 19) |

**Rischi residui:**
- L'allocator non ordina `vgp_df`: se l'orchestratore dimentica di chiamare
  `.sort_values('vgp_score', ascending=False)`, il carrello non rispettera'
  R-06 (priorita' al top VGP). Test `test_index_does_not_affect_pass_2_order`
  documenta il comportamento; future-proofing: aggiungere un golden test
  end-to-end (CHG futuro) che verifica `compute_vgp_score(...).sort_values(...)
  → allocate_tetris(...) → verify Cart`.
- `iterrows()` puo' essere lento su listini > 10k righe (vincolo 8.1
  ADR-0018: <500ms su 10k). Implementazione iniziale; promotion a
  vettoriale post-MVP se profiler lo richiede.
- `pd.Series.iloc[0]` per estrazione locked-in: richiede `match.empty` check
  (gia' fatto).

## Impact

`gitnexus_detect_changes`: risk **none** (indice GitNexus stale di 5 commit;
tutti i nuovi simboli `Cart`, `CartItem`, `allocate_tetris`,
`InsufficientBudgetError` saranno indicizzati al prossimo `gitnexus
analyze`).

`compute_vgp_score` (CHG-035) ora ha il primo caller architetturale: in
pipeline `compute_vgp_score(...) → .sort_values('vgp_score',
ascending=False) → allocate_tetris(...)`. Nessun simbolo esistente toccato.

## Refs

- ADR: ADR-0018 (Tetris allocator R-06 + R-04), ADR-0014 (mypy/ruff strict),
  ADR-0013 (`tetris/`), ADR-0019 (test pattern unit)
- Predecessori: CHG-2026-04-30-035 (`compute_vgp_score`)
- Vision verbatim: PROJECT-RAW.md sez. 4.1.13 (R-04 locked-in) + riga 224
  (R-06 saturazione 99.9%)
- Successore atteso: `tetris/panchina.py` (R-09 archivio idonei scartati)
- Commit: `4747382`
