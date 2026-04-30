---
id: CHG-2026-04-30-048
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0016, ADR-0015, ADR-0014, ADR-0019
---

## What

Integra `find_session_by_hash` (CHG-047) nella dashboard Streamlit per
**pre-save duplicate check**. Sostituisce il bottone "Salva sessione su DB"
con un warning informativo + bottone "Apri sessione esistente" quando il
listino e' gia' stato eseguito per il tenant.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | +`fetch_existing_session_for_listino(factory, listino_raw, *, tenant_id) -> SessionSummary \| None` (graceful) + `_render_existing_session_warning(factory, existing)` (warning + bottone "Apri sessione esistente"); `main()` chiama `fetch_existing_*` post-`run_session` e renderizza warning/bottone-save in mutua esclusione |
| `src/talos/ui/__init__.py` | modificato | +re-export `fetch_existing_session_for_listino` |
| `tests/integration/test_ui_duplicate_check.py` | nuovo | 4 test (None se listino non salvato, summary se salvato, filtro tenant_id isola, re-export __init__) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | entry `dashboard.py` aggiornata con CHG-048 |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **430 PASS**
(372 unit/governance/golden + 58 integration).

## Why

CHG-047 ha aperto l'idempotency a livello DB (UNIQUE INDEX). Senza UI
integration, il CFO che salva due volte stesso listino vede un errore
crudo `IntegrityError: ux_sessions_tenant_hash`. Con l'integrazione,
**vede prima del save**:
1. Warning chiaro: "questa sessione esiste, id=X, eseguita 2 ore fa".
2. Bottone "Apri sessione esistente" che ricarica via `load_session_by_id`.
3. Bottone "Salva" nascosto (no IntegrityError).

Pattern UX coerente con idempotency principle: invece di tentare e
fallire, l'UI guida verso l'azione corretta.

### Decisioni di design

1. **`fetch_existing_session_for_listino` chiama `_listino_hash`
   internamente**: l'helper privato del repository fa il calcolo
   deterministico. Il caller UI passa solo il `pd.DataFrame`,
   l'hash viene calcolato dietro le quinte. Astrazione pulita.
2. **Mutua esclusione warning vs bottone "Salva"**: `if existing is not
   None: warning else: salva`. L'UI mostra UNA sola opzione per ridurre
   confusione. Il bottone "Forza nuova" (richiede upsert) e' scope
   futuro — qui esplicitamente NON disponibile.
3. **Bottone "Apri sessione esistente" → `_render_loaded_session_detail`**:
   riusa l'helper di CHG-045. Pattern: la UI di duplicate check
   diventa una scorciatoia per il flow "load detail by id", evitando
   al CFO di copiare manualmente l'`id`.
4. **Cleanup nei test integration**: i test di duplicate check usano
   commit reale (non rollback) per ottenere `find_session_by_hash` su
   tx separata. Cleanup manuale `db.delete(obj)` finally.
5. **Niente `st.cache_data` su `fetch_existing_session_for_listino`**:
   il listino_hash dipende dal contenuto del DataFrame, non dalla
   reference; senza hashable input lo Streamlit cache fallirebbe.
   Errata corrige post-MVP se profile lo richiedera'.
6. **`re-export _listino_hash`?** No: `_listino_hash` resta privato
   nel repository. La dashboard lo importa come internal helper
   (`from talos.persistence.session_repository import _listino_hash`)
   perche' l'UI ha bisogno della stessa primitiva di hashing del
   write-side. Pattern accettabile per moduli "vicini" (UI e
   repository sono entrambi di sessione).

### Out-of-scope

- **`upsert_session`** + bottone "Forza nuova": scope CHG futuro
  (decisione Leader sulla semantica delete-recreate vs update-only).
- **Click-on-row history → load detail**: scope refactor multi-page.
- **Comparison view** (sessione corrente vs storica con stesso listino):
  scope futuro.
- **Test fail path completo**: `try/except Exception` nei due helper
  e' coperto da type checker (mypy strict) ma non runtime — scope
  CHG dedicato con mock framework.

## How

### `dashboard.py` (highlight)

```python
def fetch_existing_session_for_listino(factory, listino_raw, *, tenant_id):
    try:
        listino_hash = _listino_hash(listino_raw)
    except Exception:
        return None
    try:
        with session_scope(factory) as db:
            return find_session_by_hash(db, listino_hash=listino_hash, tenant_id=tenant_id)
    except Exception:
        return None


def main() -> None:
    # ... resto invariato ...
    existing = fetch_existing_session_for_listino(factory, inp.listino_raw, ...)
    if existing is not None:
        _render_existing_session_warning(factory, existing)
    else:
        if st.button("Salva sessione su DB"):
            ...

def _render_existing_session_warning(factory, existing):
    st.warning(f"Sessione gia' presente: id=... eseguita ...")
    st.caption("Salvataggio bloccato dall'UNIQUE INDEX (CHG-047)...")
    if st.button("Apri sessione esistente"):
        loaded = fetch_loaded_session_or_none(factory, existing.id)
        _render_loaded_session_detail(loaded)
```

### Test plan (4 integration)

1. `test_returns_none_for_unsaved_listino` — listino mai salvato → None
2. `test_returns_summary_for_existing_listino` — round-trip save → fetch
3. `test_filters_by_tenant_id` — isolamento t1 vs t2
4. `test_re_export_in_init` — `talos.ui.fetch_existing_session_for_listino`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 88 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **372 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **58 PASS** (54 + 4) |

**Rischi residui:**
- **Cleanup nei test**: se un test fallisce dopo il save ma prima del
  cleanup, una riga resta nel DB. Container ephemeral lo gestisce a
  livello restart. In produzione i test integration NON dovrebbero
  girare contro DB shared.
- **Race condition** (utente A apre listino, utente B salva listino,
  utente A clicca "Salva" → IntegrityError): il pattern check-then-save
  non e' atomic. Mitigazione: `try_persist_session` cattura
  IntegrityError e mostra `st.error`. UI futura puo' gestire con retry
  + reload.
- **Import diretto di `_listino_hash`** (private): pattern accettabile
  per UI<->repository ma andrebbe esposto come API pubblica se
  emergono altri caller. Errata corrige se necessario.

## Impact

**🎯 UX duplicate-aware**: il loop CFO ora e' "esegui → vedi → (se
duplicato: apri esistente | salva)". Niente piu' silently-error o
duplicate confusion. L'idempotency DB-level (CHG-047) ha la sua
controparte UI-level (CHG-048).

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze`:
`fetch_existing_session_for_listino`, `_render_existing_session_warning`.

## Refs

- ADR: ADR-0016 (UI Streamlit), ADR-0015 (persistenza), ADR-0014
  (mypy/ruff strict), ADR-0019 (test integration pattern)
- Predecessori: CHG-2026-04-30-040..047 (catena UI + persistenza)
- Successore atteso: `upsert_session` con `ON CONFLICT DO UPDATE`
  (decisione Leader semantica) + bottone "Forza nuova"; comparison view
  sessione corrente vs storica
- Commit: `[pending]`
