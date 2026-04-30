---
id: CHG-2026-04-30-056
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Committed
commit: e7c2666
adr_ref: ADR-0018, ADR-0014, ADR-0019
---

## What

Aggiunge `replay_session(loaded, *, locked_in_override, budget_override)`:
data una `SessionResult` ricaricata (tipicamente da `load_session_full`),
ri-esegue **solo** Tetris + panchina + compounding senza ri-fare
enrichment/score. Pensato per il flusso "what-if" interattivo del CFO
("e se avessi un budget di 5k invece di 10k?", "e se rimuovessi il
locked-in X?").

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/orchestrator.py` | modificato | + `replay_session(loaded, *, locked_in_override=None, budget_override=None) -> SessionResult`. Riusa `loaded.enriched_df` (vgp_score/kill_mask/veto già calcolati), riapplica `allocate_tetris` + `build_panchina` + `compounding_t1`. Default override: locked_in da `loaded.cart.items[?].locked`, budget da `loaded.cart.budget`. |
| `tests/integration/test_replay_session.py` | nuovo | 6 test: round-trip senza override (cart equivalente), locked_in override aggiunge ASIN, locked_in vuoto rimuove tutti, budget basso shrinks cart, locked_in over-budget raise InsufficientBudgetError, budget_t1 ricalcolato. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **484 PASS**
(387 unit/governance/golden + 97 integration).

## Why

CHG-052 ha aperto `load_session_full` che ricostruisce un canonico
`SessionResult` da DB. Senza `replay_session`, l'unico utilizzo era
"visualizzazione storica" — il CFO non poteva derivare nuovi scenari
dal dato salvato senza ri-esecuzione completa della pipeline.

Senza questo CHG:
- Per "spostare un locked-in" dovevi ri-fare upload listino raw +
  re-run completo (10x più lento del replay).
- L'oggetto `SessionResult` ricaricato era *write-only*: lo
  guardavi, non lo manipolavi.
- Dimostrare il valore architetturale di `load_session_full` (CHG-052)
  richiedeva un primo consumer → questo CHG lo è.

### Decisioni di design

1. **Riuso di `enriched_df` ricaricato** invece di ri-fare enrichment:
   l'enriched_df ha già `vgp_score`, `kill_mask`, `veto_roi_passed`,
   `cash_profit_eur`, `qty_final`. Allocator + panchina + compounding
   leggono solo queste colonne. Drift Decimal→float (CHG-052) si
   propaga, ma è < 1 EUR su budget tipici e già documentato.

2. **No `veto_roi_threshold_override` in V1**: cambiare la threshold
   richiederebbe rilanciare `compute_vgp_score` (R-08 dipende dalla
   threshold, R-05 no). Il caller perderebbe il vantaggio del replay
   (diventerebbe equivalente a `run_session`). Scope CHG futuro
   se il pattern UX lo richiederà.

3. **`locked_in_override=None` riusa locked-in originali**: il caso
   d'uso più comune è "stesso scenario, budget diverso". Default
   intuitivo. `[]` esplicito per "rimuovi tutti".

4. **Sort defensive `vgp_score DESC`**: l'enriched_df ricaricato è
   già ordinato (load_session_full impone l'order_by), ma il sort
   è a costo trascurabile e blinda l'invariante per caller diretti
   che passino df costruiti a mano.

5. **`RuntimeError` su mapping corrotto** (ASIN nel cart ma assente
   da df): coerente con `run_session` originale (R-01 strict). Non
   silently-skip — un drift indica corruzione DB/codice.

### Out-of-scope

- **`veto_roi_threshold_override`**: scope CHG dedicato (richiede
  re-`compute_vgp_score`).
- **UI integration**: nessun bottone "Re-allocate" in dashboard
  ancora. Il CHG-055 ha chiuso il loop CFO→DB→UI per overrides
  referral fee; il replay UI è scope CHG successivo (post `io_/extract`).
- **Persistenza dei replay**: ogni replay produce un nuovo
  `SessionResult` in memory che NON viene salvato. Per persisterlo
  serve `save_session_result` standard. Pattern intenzionale: il
  what-if non sporca lo storico.
- **Telemetria evento `session.replayed`**: scope errata corrige
  catalogo ADR-0021 se profiler richiederà.

## How

### `replay_session` (highlight)

```python
def replay_session(loaded, *, locked_in_override=None, budget_override=None):
    new_budget = budget_override if budget_override is not None else loaded.cart.budget
    if locked_in_override is None:
        new_locked_in = [item.asin for item in loaded.cart.items if item.locked]
    else:
        new_locked_in = list(locked_in_override)

    sorted_df = loaded.enriched_df.sort_values("vgp_score", ascending=False)
    cart = allocate_tetris(sorted_df, budget=new_budget, locked_in=new_locked_in)
    panchina = build_panchina(sorted_df, cart)

    cart_profits = []
    for item in cart.items:
        match = sorted_df[sorted_df["asin"] == item.asin]
        if match.empty:
            raise RuntimeError(...)  # R-01 strict
        cart_profits.append(float(match.iloc[0]["cash_profit_eur"]) * item.qty)
    budget_t1 = compounding_t1(new_budget, cart_profits)

    return SessionResult(cart=cart, panchina=panchina, budget_t1=budget_t1,
                        enriched_df=sorted_df)
```

### Test plan (6 integration)

1. `test_replay_no_overrides_equivalent_to_loaded` — round-trip identico
2. `test_replay_with_locked_in_override` — RP04 entra come locked
3. `test_replay_with_empty_locked_in_removes_locks` — `[]` rimuove tutti
4. `test_replay_with_lower_budget_shrinks_cart` — budget=1000 → cart ≤ 1000
5. `test_replay_with_locked_in_over_budget_raises` — InsufficientBudgetError
6. `test_replay_recomputes_budget_t1` — budget basso → budget_t1 ridotto

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 98 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **387 PASS** (invariato) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **97 PASS** (91 + 6) |

**Rischi residui:**
- **Drift Decimal→float** ereditato da `load_session_full` (~1 EUR su
  budget tipici): il replay opera su valori float già drift-affetti.
  Il cart prodotto può differire di alcuni decimali rispetto a un
  `run_session` fresh sul listino raw originale. Documentato.
- **`apply` row-wise compounding loop**: O(N²) per il `match`
  scan-by-asin nel cart. Per cart Samsung MVP (~10 ASIN) trascurabile;
  per 1000+ ASIN potrebbe contare. Vettorializzazione scope futuro.
- **No telemetria**: replay invisibile nei log. Catalogo ADR-0021
  potrebbe aggiungere `session.replayed` evento futuro.

## Test di Conformità

- **Path codice applicativo:** `src/talos/orchestrator.py` ✓.
- **Test integration sotto `tests/integration/`:** ✓ (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `replay_session` mappa ad
  ADR-0018 — coerente con `run_session`.
- **Backward compat:** `run_session` invariato; `SessionResult`
  invariato. `replay_session` puramente additivo.
- **Impact analysis pre-edit:** `allocate_tetris` 0 caller upstream
  nel grafo (è invocato dall'orchestrator).

## Impact

**Primo consumer reale di `load_session_full`** (CHG-052): dimostra
il valore architetturale del round-trip canonico. Sblocca il pattern
"what-if" da CFO. Pattern utile in CHG futuri:
- UI bottone "Re-allocate" su sessione caricata.
- Confronto pre/post di scenari (compare runs).
- A/B test di parametri locked_in / budget senza ri-eseguire pipeline.

`gitnexus_detect_changes` rileva risk LOW (nuovo simbolo isolato,
zero modifiche a simboli esistenti).

## Refs

- ADR: ADR-0018 (orchestrator + R-01..R-09), ADR-0014 (mypy/ruff
  strict), ADR-0019 (test integration).
- Predecessori: CHG-2026-04-30-039 (`run_session`),
  CHG-2026-04-30-052 (`load_session_full` round-trip).
- Successore atteso: UI bottone "Re-allocate"; confronto pre/post;
  `veto_roi_threshold_override` (richiede re-`compute_vgp_score`);
  evento canonico `session.replayed`.
- Commit: `e7c2666`.
