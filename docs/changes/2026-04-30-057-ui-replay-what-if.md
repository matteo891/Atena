---
id: CHG-2026-04-30-057
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Pending
commit: pending
adr_ref: ADR-0016, ADR-0018, ADR-0014, ADR-0019
---

## What

Aggancia `replay_session` (CHG-056) alla UI dashboard. Aggiunge un
sub-expander "What-if Re-allocate" dentro il dettaglio della sessione
caricata (sia dal flusso "Carica dettaglio" da storico sia dal
"Apri sessione esistente" del duplicate-check). Il CFO modifica
`budget` o `locked-in` e ottiene un nuovo `SessionResult` ricalcolato
in memoria.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | + import `load_session_full` + `replay_session`. + `try_replay_session(factory, session_id, *, locked_in_override, budget_override, tenant_id) -> tuple[SessionResult \| None, str \| None]` graceful (cattura `InsufficientBudgetError` come messaggio user-friendly). + `_render_replay_what_if(factory, session_id, *, original_budget)` con number_input budget + text_input locked-in CSV + bottone "Re-allocate (what-if)". + `_render_replay_result(replayed)` con metric saturazione/budget_t1/counts + tabelle Cart/Panchina nuove. `_render_loaded_session_detail` esteso con kwarg opzionale `factory` (compatibilità garantita: senza factory niente sub-expander). 2 caller esistenti aggiornati per passare `factory`. |
| `src/talos/ui/__init__.py` | modificato | + re-export `try_replay_session`. |
| `tests/integration/test_try_replay_session_ui.py` | nuovo | 3 test: success + R-04 fail con `InsufficientBudgetError` come stringa + ID inesistente con `"non trovata"`. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **487 PASS**
(387 unit/governance/golden + 100 integration).

## Why

CHG-056 ha implementato `replay_session` come primitive ma senza
consumer reale lato UI. Il valore architetturale del round-trip
canonico (`load_session_full` → `replay_session`) era invisibile
all'utente finale.

Senza questo CHG:
- Il bottone "what-if" che il CFO si aspetta da una dashboard di
  scenario era assente.
- `replay_session` era testabile programmaticamente ma non visualizzabile.
- Il pattern "carica sessione storica → modifica un parametro → vedi
  risultato" richiedeva codice custom (Streamlit non ha hot-reload
  trasparente sull'oggetto `SessionResult`).

### Decisioni di design

1. **Sub-expander dentro `_render_loaded_session_detail`**: il what-if
   appare solo quando una sessione e' caricata. Niente expander
   indipendente in main(): il caso d'uso "what-if su sessione
   storica" implica avere già la sessione visibile.

2. **`factory` opzionale come secondo argomento**: signature
   `_render_loaded_session_detail(loaded, factory=None)` retrocompat
   completa. Test e altri caller che non passano factory non vedono
   il sub-expander, niente break.

3. **`try_replay_session` graceful con messaggi user-friendly**:
   `InsufficientBudgetError` diventa "R-04 fallito: ..."; `ValueError`
   diventa "Validazione fallita: ..."; eccezione generica diventa
   "Errore inatteso: ...". Mai stack trace al CFO.

4. **`text_input` locked-in vuoto = stessi locked-in originali**:
   `replay_session` (CHG-056) tratta `locked_in_override=None` come
   "riusa originali", `[]` come "rimuovi tutti". L'UX rispetta:
   stringa vuota → `None` (default = originali); stringa con virgole
   ma valori vuoti → `[]` (rimuovi tutti, via `parse_locked_in`).

5. **Niente persistenza del replay**: il `SessionResult` ricalcolato
   sta in memoria/UI. Niente bottone "Salva replay" ancora — sarebbe
   bloccato dall'UNIQUE INDEX (stesso listino_hash). Pattern: replay
   = scenario teorico; salvare richiederebbe `upsert_session`
   (out-of-scope, decisione Leader pending).

6. **`key=f"replay_..._{session_id}"`**: chiavi dei widget
   parametrizzate per session_id evitano collision se l'utente
   ricarica una sessione diversa nello stesso run Streamlit.

7. **`_render_replay_result` separato**: render pulito del
   `SessionResult` + tabelle. Riutilizzabile (CHG futuri compare
   runs side-by-side).

### Out-of-scope

- **Compare runs side-by-side**: scope CHG futuro (mostra cart
  originale vs replay).
- **Persist replay**: bloccato da `upsert_session` decisione Leader.
- **Telemetria evento `session.replayed`**: scope errata catalogo
  ADR-0021 (CHG futuro micro-scope).
- **Override `veto_roi_threshold`** (richiede re-`compute_vgp_score`):
  scope CHG futuro.
- **Multi-page refactor**: l'expander resta nella mono-page MVP.

## How

### `try_replay_session` (highlight)

```python
def try_replay_session(factory, session_id, *, locked_in_override=None,
                       budget_override=None, tenant_id=DEFAULT_TENANT_ID):
    try:
        with session_scope(factory) as db:
            loaded = load_session_full(db, session_id, tenant_id=tenant_id)
            if loaded is None:
                return None, f"Sessione id={session_id} non trovata o non accessibile."
            replayed = replay_session(
                loaded,
                locked_in_override=locked_in_override,
                budget_override=budget_override,
            )
    except InsufficientBudgetError as exc:
        return None, f"R-04 fallito: {exc}"
    except ValueError as exc:
        return None, f"Validazione fallita: {exc}"
    except Exception as exc:
        return None, f"Errore inatteso: {exc}"
    return replayed, None
```

### Sub-expander UI

```python
def _render_replay_what_if(factory, session_id, *, original_budget):
    with st.expander("What-if — Re-allocate questa sessione"):
        st.caption("Niente persistenza: il replay e' in memoria.")
        new_budget = st.number_input("Budget override (EUR)", value=original_budget, ...)
        new_locked_raw = st.text_input("Locked-in override (ASIN CSV)", value="")
        if st.button("Re-allocate (what-if)"):
            locked_override = parse_locked_in(new_locked_raw) if new_locked_raw.strip() else None
            replayed, err = try_replay_session(factory, session_id,
                                                locked_in_override=locked_override,
                                                budget_override=float(new_budget))
            if err is not None:
                st.error(err)
            else:
                _render_replay_result(replayed)
```

### Test plan (3 integration)

1. `test_try_replay_session_success` — save → replay con budget=2000 → SessionResult con cart.budget=2000, total_cost ≤ 2000
2. `test_try_replay_session_missing_id_returns_error` — id 9_999_999 → (None, "non trovata...")
3. `test_try_replay_session_insufficient_budget_returns_error` — locked_in=["RU01"], budget=100 → (None, "R-04 fallito: ...")

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 99 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **387 PASS** (invariato) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **100 PASS** (97 + 3) |

**Rischi residui:**
- **Replay non persistito**: l'utente potrebbe aspettarsi che la
  modifica resti dopo il rerun. Caption "Niente persistenza" e'
  esplicita ma in produzione confirm dialog UX scope futuro.
- **Cleanup test (DELETE AnalysisSession con CASCADE)**: i test
  usano `sess.delete(asession)` per pulizia. Le tabelle child con
  FK ON DELETE CASCADE (vgp_results, cart_items, panchina_items,
  listino_items) si autopuliscono. `storico_ordini` non ha CASCADE
  ma non e' toccata dai test.
- **Streamlit widget keys parametrizzate**: due caricamenti diversi
  della stessa sessione_id (no rerun) condividono lo stato del
  widget. Pattern noto MVP, refactor multi-page con `state.py`
  risolverebbe.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/dashboard.py` ✓.
- **Test integration sotto `tests/integration/`:** ✓ (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `try_replay_session` mappa
  ad ADR-0016 — coerente con altri helper UI.
- **Backward compat:** signature `_render_loaded_session_detail`
  estesa con kwarg opzionale; caller esistenti aggiornati.
- **Impact analysis pre-edit:** modifiche additive nella UI mono-page;
  i 4 processi UI già toccati in CHG-054 restano coerenti (nuovo
  expander figlio di un render esistente).

## Impact

**Loop replay completo end-to-end:** CFO → "Carica dettaglio" → vede
sessione → "What-if Re-allocate" → modifica parametri → vede nuovo
cart in memoria. Nessuna persistenza side-effect.

`replay_session` (CHG-056) ora ha un consumer visibile. Il pattern
si estende naturalmente a compare runs side-by-side (CHG futuro).

## Refs

- ADR: ADR-0016 (UI Streamlit), ADR-0018 (orchestrator), ADR-0014
  (mypy/ruff strict), ADR-0019 (test pattern).
- Predecessori: CHG-2026-04-30-045 (`load_session_by_id` + UI dettaglio),
  CHG-2026-04-30-052 (`load_session_full`), CHG-2026-04-30-056
  (`replay_session`).
- Successore atteso: compare runs side-by-side; persist replay
  (richiede `upsert_session`); telemetria `session.replayed`.
- Commit: pending (backfill).
