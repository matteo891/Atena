---
id: CHG-2026-04-30-037
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

Completa il cluster `tetris/` con `build_panchina(vgp_df, cart)` — R-09
verbatim PROJECT-RAW.md riga 227. Ritorna gli ASIN idonei (`vgp_score > 0`)
non allocati nel `Cart`, ordinati per VGP DESC.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/tetris/panchina.py` | nuovo | `build_panchina(vgp_df, cart, *, asin_col="asin", score_col="vgp_score")` → DataFrame |
| `src/talos/tetris/__init__.py` | modificato | +re-export `build_panchina`; docstring aggiornato (cluster completo) |
| `tests/unit/test_tetris_panchina.py` | nuovo | 10 test (esclusione cart, esclusione zero-score, ordinamento DESC, vuoti, realistic, validation, custom cols) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `tetris/panchina.py` |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **296 PASS** (286 + 10).

## Why

CHG-036 ha consegnato `Cart` (allocati). R-09 e' il **secondo output canonico
di sessione** (PROJECT-RAW.md riga 227): *"Nessun ASIN con ROI >= 8% deve
essere dimenticato"*. Senza Panchina, il cruscotto perde la lista degli ASIN
"giusti ma non comprati per cassa" — informazione critica per il CFO che
vuole vedere il margine di manovra residuo.

Il filtro e' verbatim ADR-0018 sez. "Panchina":
- `vgp_score > 0` (R-05/R-08 gia' azzerati a monte)
- `~ asin in cart`

L'ordine e' VGP DESC (R-09 verbatim).

### Decisioni di design

1. **Filtro per `vgp_score > 0`**: equivalente a *"ROI >= 8% e match
   passato"* perche' R-05 azzera kill e R-08 azzera ROI < 8% (entrambi
   applicati in `compute_vgp_score`). Quindi `vgp_score > 0` ⇒ idoneo per
   panchina.
2. **Index originale preservato** (no `.reset_index()`): coerente con
   `compute_vgp_score`. Il caller decide se reset all'output finale UI.
3. **`set(cart.asin_list())` per lookup O(1)**: il Cart ha al massimo
   ~100-500 item; il listino fino a 10k. Usare set per la membership
   evita scan O(N*M).
4. **No copia esplicita**: `vgp_df[mask].sort_values(...)` ritorna gia'
   un DataFrame nuovo (pandas semantics). Aliasing rischio basso.
5. **Override colonne**: stesso pattern di `compute_vgp_score` (CHG-035) e
   `allocate_tetris` (CHG-036) — `asin_col`, `score_col`. Default coerenti.

### Out-of-scope

- **Limit `top N`** in panchina: scope futuro UI (`@st.cache_data` con limit).
- **Persistenza panchina** in DB: scope orchestratore di sessione.
- **Telemetria evento `panchina_built`**: scope orchestratore + structlog.

## How

### `src/talos/tetris/panchina.py` (highlight)

```python
def build_panchina(vgp_df, cart, *, asin_col="asin", score_col="vgp_score"):
    # validazione colonne (R-01)
    in_cart = set(cart.asin_list())
    eligible = vgp_df[(vgp_df[score_col] > 0) & (~vgp_df[asin_col].isin(in_cart))]
    return eligible.sort_values(score_col, ascending=False)
```

### Test plan (10)

1. `test_panchina_excludes_in_cart_asins`
2. `test_panchina_excludes_zero_score` — kill/veto
3. `test_panchina_ordered_by_score_desc` — invariante R-09
4. `test_panchina_empty_when_all_in_cart`
5. `test_panchina_empty_when_all_vetoed_or_killed`
6. `test_panchina_empty_when_df_empty`
7. `test_panchina_preserves_other_columns` — UI cruscotto
8. `test_panchina_realistic_cart_partial_overlap` — scenario tipico
9. `test_missing_columns_raises`
10. `test_custom_column_names`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 71 files already formatted |
| Type | `uv run mypy src/` | ✅ 34 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ **296 PASS** (286 + 10) |

**Rischi residui:**
- `vgp_df[score_col] > 0` con `score_col` di tipo non-numerico raiserebbe
  in pandas. Mitigazione: assunzione contratto (output di
  `compute_vgp_score` e' sempre `float64`).
- Index disordinato post-sort: pandas mantiene index originale,
  rinumerazione e' a discrezione caller.

## Impact

`min_max_normalize` + `compute_vgp_score` + `allocate_tetris` +
`build_panchina` formano la **pipeline core** di sessione. Manca solo
l'orchestratore che (1) calcola F1/F2/F4/F5 + velocity_monthly inline,
(2) chiama `compute_vgp_score`, (3) ordina `vgp_score` DESC,
(4) chiama `allocate_tetris`, (5) chiama `build_panchina`,
(6) calcola `compounding_t1` con `cart.items[*].vgp_score>0` profits.

Cluster `tetris/` **completo** rispetto al perimetro ADR-0018 (allocator + panchina).

## Refs

- ADR: ADR-0018 (Tetris + Panchina), ADR-0014 (mypy/ruff strict),
  ADR-0013 (`tetris/`), ADR-0019 (test pattern unit)
- Predecessori: CHG-2026-04-30-036 (`tetris/allocator.py`)
- Vision verbatim: PROJECT-RAW.md riga 227 (R-09)
- Successore atteso: orchestratore di sessione (`session.py` o
  `orchestrator.py`) — pipeline end-to-end
- Commit: `[pending]`
