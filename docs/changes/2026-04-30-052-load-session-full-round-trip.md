---
id: CHG-2026-04-30-052
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Committed
commit: 4c710ea
adr_ref: ADR-0015, ADR-0014, ADR-0019
---

## What

Aggiunge `load_session_full(db_session, session_id, *, tenant_id=1) -> SessionResult | None`:
ricostruisce un `SessionResult` (cart/panchina/budget_t1/enriched_df) a
partire da una `AnalysisSession` storica del DB. Round-trip rispetto a
`save_session_result` (CHG-2026-04-30-042).

Differenza vs `load_session_by_id` (CHG-2026-04-30-045): quello ritorna
`LoadedSession` *lite* (dict per UI dataframe). Questo ritorna l'oggetto
canonico dell'orchestratore (`SessionResult`), pronto per essere passato
a downstream consumer (re-allocate hypothetical, comparison fra sessioni,
export richiestissimi dal CFO).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/session_repository.py` | modificato | + costante `_LOADED_ENRICHED_COLUMNS` (13 colonne) + `load_session_full(...)`. 4 query (header + VgpResult JOIN ListinoItem ordered, CartItem JOIN VgpResult ordered, PanchinaItem JOIN VgpResult ordered). Lazy import `pd`/`SessionResult`/`Cart`/`CartItem` per evitare ciclo `persistence ↔ orchestrator`. `budget_t1` ricalcolato via `compounding_t1` (non persistito). |
| `src/talos/persistence/__init__.py` | modificato | + re-export `load_session_full`. |
| `tests/integration/test_load_session_full.py` | nuovo | 8 test integration round-trip (None on missing/invalid, tipo SessionResult, cart asin/qty/cost/locked/score round-trip, enriched_df 13 col, panchina round-trip + ordering, budget_t1 ricalcolato entro tolerance, tenant filter). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **460 PASS**
(380 unit/governance/golden + 80 integration).

## Why

CHG-045 (`load_session_by_id`) ha aperto la lettura DB, ma con shape
*lite* (dict pensato per `st.dataframe` UI). Mancava la primitiva
canonica per il caller programmatico: ricostruire l'oggetto `SessionResult`
*esattamente* come l'orchestratore lo emette.

Senza `load_session_full`:
- Un eventuale "what-if" (cambia `locked_in`, ri-alloca senza modificare
  i dati di vgp_results) richiedeva ri-fetchare il listino + rieseguire
  la pipeline da zero.
- Confronto programmatico fra due sessioni storiche richiedeva
  ricostruzione manuale dei DataFrame.
- Export "completo" verso CSV/JSON era hand-rolled per ogni consumer.

`load_session_full` chiude il loop CRUD (READ-full), preparando il terreno
per i CHG futuri di re-allocate / compare / export.

### Decisioni di design

1. **`SessionResult` canonico**: la funzione ritorna esattamente lo stesso
   tipo emesso da `run_session`, non un sottotipo. Pattern: il consumer
   non deve sapere se l'oggetto viene da DB o da pipeline live.

2. **Drift documentato Decimal → float**: i campi monetari sono
   `Numeric(12, 4)` nel DB. `Decimal('0.3923')` ↔ `float(0.3923)` ha
   round-trip fedele entro le 4 cifre conservate (drift atteso `< 1e-4`
   sulle metriche, `< 1.0 EUR` sul `budget_t1` ricalcolato per cart
   tipici MVP). Test tolerance riflettono il drift reale, non un
   ideale matematico.

3. **`enriched_df` non contiene `fee_fba_eur`/`cash_inflow_eur`/`q_m`**:
   queste colonne non sono in `vgp_results` (Allegato A ADR-0015). Sono
   ricalcolabili on-demand dalle formule scalari. Documentato in
   docstring + costante `_LOADED_ENRICHED_COLUMNS` esplicita.

4. **`budget_t1` ricalcolato vs persistito**: `analysis_sessions` non
   ha colonna `budget_t1`. Per CHG futuro (compare runs) potremmo
   aggiungerlo, ma il valore è deterministico da `cart_profits` +
   `budget_eur`, quindi ricalcolare evita drift Decimal aggiuntivo.

5. **Ordinamento `enriched_df` per `vgp_score DESC, id ASC`**: replica
   l'ordine post-`compute_vgp_score`. Il tiebreaker `id ASC` dipende
   dalla sequence DB, non dall'ordine pre-allocator originale → drift
   atteso solo su righe con `vgp_score` identico (es. tutte vetate
   con score 0).

6. **Lazy import `pd`/`Cart`/`CartItem`/`SessionResult`/`compounding_t1`**:
   ciclo `persistence` → `orchestrator` → `tetris` evitato. Pattern
   coerente con `_empty_scored_df` in orchestrator.

7. **Alias `CartItem as TetrisCartItem`**: il modulo top-level già
   importa il modello DB `CartItem`. L'alias è esplicito a punto d'uso
   per evitare confusione nei test (rare ma il caso di un test che
   leghi oggetti DB e dataclass nel medesimo scope).

8. **`panchina.qty_final = panchina.qty_proposed`**: il save scrive
   `qty_proposed=int(row["qty_final"])` (CHG-042 line 205). Nel load
   replichiamo entrambe le colonne per coerenza con consumer downstream
   che cercano `qty_final` nel panchina df (es. orchestrator step 5).

### Out-of-scope

- **Re-allocate hypothetical** (cambia locked_in / budget e ri-alloca
  via `allocate_tetris` su `enriched_df` ricaricato): scope CHG dedicato.
- **Compare runs** (diff fra due `SessionResult` storici): scope futuro
  UI multi-page.
- **Persistere `budget_t1` esplicitamente**: scope errata corrige
  ADR-0015 se profiling lo richiederà.
- **Persistere `fee_fba_eur`/`cash_inflow_eur`/`q_m` in `vgp_results`**:
  scope errata corrige ADR-0015 se consumer downstream lo richiederà.
- **UI integration**: nessun bottone "Riapri come SessionResult" in
  dashboard. Scope CHG futuro post `io_/extract`.

## How

### `load_session_full` (highlight)

```python
def load_session_full(db_session, session_id, *, tenant_id=1):
    if session_id <= 0:
        raise ValueError(...)

    import pandas as pd
    from talos.formulas import compounding_t1
    from talos.orchestrator import SessionResult
    from talos.tetris import Cart, CartItem as TetrisCartItem

    with with_tenant(db_session, tenant_id):
        asession = db_session.get(AnalysisSession, session_id)
        if asession is None or asession.tenant_id != tenant_id:
            return None

        # 1. Enriched df: VgpResult JOIN ListinoItem (cost_eur).
        vgp_stmt = (
            select(VgpResult, ListinoItem.cost_eur)
            .join(ListinoItem, VgpResult.listino_item_id == ListinoItem.id)
            .where(VgpResult.session_id == session_id)
            .order_by(VgpResult.vgp_score.desc(), VgpResult.id.asc())
        )
        # ... build records ...

        # 2. Cart: CartItem JOIN VgpResult (asin/score) — append order.
        cart = Cart(budget=float(asession.budget_eur))
        # ... iterate cart_items ordered by id ASC ...

        # 3. Panchina df: PanchinaItem JOIN VgpResult.
        # ... iterate panch_items ordered by vgp_score DESC, id ASC ...

        # 4. Ricalcola budget_t1 via F3.
        budget_t1 = compounding_t1(float(asession.budget_eur), cart_profits)

        return SessionResult(
            cart=cart,
            panchina=panchina_df,
            budget_t1=budget_t1,
            enriched_df=enriched_df,
        )
```

### Test plan (8 integration)

1. `test_load_full_returns_none_for_missing_id` — id 999_999 → None
2. `test_load_full_invalid_id_raises` — id ≤ 0 → ValueError
3. `test_load_full_returns_session_result_after_save` — tipo + 4 campi
4. `test_load_full_cart_round_trip` — asin/qty/cost/locked/score match
5. `test_load_full_enriched_df_columns_present` — 13 col canoniche
6. `test_load_full_panchina_round_trip` — set ASIN + ordering vgp DESC
7. `test_load_full_budget_t1_recalculated` — drift < 1.0 EUR
8. `test_load_full_filters_by_tenant_id` — tenant=2 → None

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 94 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **380 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **80 PASS** (72 + 8) |

**Rischi residui:**
- **Drift Decimal → float fino a ~1 EUR su budget_t1**: documentato
  nel test tolerance + docstring. Se profiling richiederà fedeltà
  esatta, errata corrige ADR-0015 per `Numeric(12, 6)`.
- **`enriched_df` mancante di colonne intermedie** (`fee_fba_eur`,
  `cash_inflow_eur`, `q_m`): consumer downstream che le richiedono
  devono ricalcolarle. Documentato.
- **Lazy import**: il primo invocazione paga import time di
  `pandas`/`orchestrator`/`tetris`. Trascurabile per use-case
  interactive UI; un consumer batch ad alta frequenza potrebbe
  preferire eager import.

## Test di Conformità

- **Path codice applicativo:** `src/talos/persistence/session_repository.py` ✓
  (`persistence/` consentito da ADR-0013).
- **Test integration sotto `tests/integration/`:** ✓ (ADR-0019).
- **Quality gate verde:** ruff/format/mypy/pytest tutti PASS (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `load_session_full` mappa
  ad ADR-0015 (persistenza) — coerente con `save_session_result` /
  `load_session_by_id` predecessori.

## Impact

**CRUD-light READ completo**: il CFO ora può ricaricare una sessione
storica come oggetto canonico `SessionResult`, equivalente all'output
live di `run_session`. Sblocca consumer programmatici (re-allocate,
compare, export) senza richiedere ri-esecuzione pipeline da zero.

`gitnexus_detect_changes` rileva risk LOW, 0 processi affected (modifica
puramente additiva — nessun simbolo esistente toccato in semantica).

## Refs

- ADR: ADR-0015 (persistenza + Allegato A), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test integration pattern).
- Predecessori: CHG-2026-04-30-042 (`save_session_result`),
  CHG-2026-04-30-045 (`load_session_by_id` lite),
  CHG-2026-04-30-039 (orchestrator + `SessionResult`).
- Successori attesi: re-allocate hypothetical da load_session_full;
  compare runs UI; export CSV/JSON.
- Commit: `4c710ea`.
