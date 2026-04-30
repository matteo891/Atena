---
id: CHG-2026-04-30-043
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 316940b
adr_ref: ADR-0016, ADR-0015, ADR-0014, ADR-0019
---

## What

Integra la persistenza (`save_session_result` di CHG-042) nella dashboard
Streamlit (CHG-040). Il CFO ora puo' **salvare su DB** una sessione
appena eseguita con un clic, con graceful degrade quando `TALOS_DB_URL`
non e' settata.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | +helper `get_session_factory_or_none()` (try/except create_app_engine) + `try_persist_session(factory, *, session_input, result, tenant_id) -> (success, sid, error)` + sezione "Persistenza Sessione" con bottone "Salva sessione su DB" condizionato. +costante `DEFAULT_TENANT_ID=1`. |
| `src/talos/ui/__init__.py` | modificato | +re-export `get_session_factory_or_none`, `try_persist_session`, `DEFAULT_TENANT_ID` |
| `tests/unit/test_ui_dashboard.py` | modificato | +2 test (factory_returns_none senza env var con monkeypatch + cache_clear; re-export persistence helpers) |
| `tests/integration/test_dashboard_persistence.py` | nuovo | 3 test integration (factory valido, persist success + cleanup, fail path skipped) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | entry `dashboard.py` aggiornata con riferimento CHG-043 |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **401 PASS**
(369 unit/governance/golden + 32 integration; +1 skipped intenzionale).

## Why

CHG-042 ha creato `save_session_result` ma **nessun caller**. La UI
Streamlit (CHG-040) era puro in-memory. Senza un punto di chiamata, la
persistenza era una primitiva non ancora utilizzata.

Senza l'integrazione, il CFO non puo' chiudere il loop "esegui sessione
→ verifica visivamente → salva". Demo incompleta.

### Decisioni di design

1. **Graceful degrade su `TALOS_DB_URL` assente**: niente crash. La
   sezione "Persistenza Sessione" mostra `st.info("Persistenza disabilitata...")`
   e fornisce le istruzioni per attivarla. Il resto della dashboard
   funziona invariato. Pattern coerente con UX MVP single-user (il CFO
   puo' usare la dashboard offline su listini di prova senza DB).
2. **`get_session_factory_or_none()` come helper testabile**: l'engine
   creation puo' fallire per (a) `TALOS_DB_URL` non settata
   (`RuntimeError`), (b) URL malformato (`ValueError`), (c) DB
   irraggiungibile (`OperationalError`). Tutto catturato in un'unica
   `except Exception` per UI-friendliness. Pattern pulito: la UI vede
   solo `Optional[sessionmaker]`.
3. **`try_persist_session` ritorna `(success, sid, error)`** invece di
   raise: l'UI deve poter mostrare `st.error` con messaggio leggibile.
   Pattern coerente con error-as-value per UI-only paths.
4. **Bottone "Salva su DB" SEPARATO dal bottone "Esegui Sessione"**: il
   CFO puo' eseguire la sessione (rerun veloce locale) e decidere DOPO
   se salvarla. Coerente con idempotency principle ADR-0016 (niente
   azioni "automatic" su esecuzioni esplorative).
5. **`DEFAULT_TENANT_ID = 1`** costante esposta: in MVP single-tenant
   non c'e' UI per scegliere il tenant; futuri CHG potranno aggiungere
   un selector quando arrivera' multi-tenancy.
6. **Test unit con `monkeypatch.delenv` + `get_settings.cache_clear()`**:
   `TalosSettings` usa `@lru_cache` su `get_settings`. Senza
   `cache_clear`, la fixture seguente vedrebbe il vecchio valore.
   Mitigazione strutturale: scope CHG futuro per fixture
   `clear_settings_cache` autouse.
7. **Test fail path skippato**: costruire un trigger fail pulito senza
   mock e' difficile (run_session valida tutto a monte). Lo skip e'
   esplicito — quando arrivera' una libreria di mock dedicata
   (es. `pytest-mock`), si scrivera' il test con `MagicMock(side_effect=...)`.

### Out-of-scope

- **Caching `@st.cache_resource`** sul factory: rerun completo a ogni
  interazione widget significa che il factory si ri-crea ogni rerun.
  Costo: ~10ms (engine setup). Errata corrige post-MVP se emerge
  lentezza.
- **Selector tenant_id in UI**: scope multi-tenancy futuro.
- **Storico sessioni nella dashboard** (`load_session_by_id`,
  `list_recent_sessions`): scope CHG-044 (UI list + dettaglio).
- **Pulsante "Carica sessione precedente"** per ri-caricare i parametri
  da una sessione passata: scope CHG futuro.
- **Test fail path** (raise dentro `save_session_result`): require mock
  framework, scope CHG dedicato.

## How

### `dashboard.py` (highlight)

```python
def get_session_factory_or_none() -> sessionmaker[Session] | None:
    try:
        engine = create_app_engine()
    except (RuntimeError, ValueError, Exception):  # graceful
        return None
    return make_session_factory(engine)


def try_persist_session(
    factory, *, session_input, result, tenant_id=DEFAULT_TENANT_ID,
) -> tuple[bool, int | None, str | None]:
    try:
        with session_scope(factory) as db_session:
            sid = save_session_result(db_session, ...)
    except Exception as exc:
        return False, None, str(exc)
    return True, sid, None


def main() -> None:
    # ... resto invariato (parametri, upload, run_session, metric, tabelle) ...

    factory = get_session_factory_or_none()
    st.subheader("Persistenza Sessione")
    if factory is None:
        st.info("Persistenza disabilitata. Imposta TALOS_DB_URL per attivarla.")
        return

    if st.button("Salva sessione su DB"):
        ok, sid, err = try_persist_session(factory, ...)
        if ok:
            st.success(f"Sessione persistita. id = `{sid}`.")
        else:
            st.error(f"Persistenza fallita: {err}")
```

### Test plan

- Unit (2 nuovi):
  - `test_get_session_factory_returns_none_without_db_url` —
    monkeypatch + cache_clear → None.
  - `test_persistence_helpers_re_exported` — `talos.ui.{factory, persist,
    DEFAULT_TENANT_ID}` accessibili.
- Integration (3 nuovi, di cui 1 skipped):
  - `test_get_session_factory_returns_valid_factory` — `pg_engine` fixture
    garantisce env, factory valido.
  - `test_try_persist_session_success` — persiste + verifica
    `AnalysisSession` letta back + cleanup `delete + commit`.
  - `test_try_persist_session_failure_returns_error_tuple` — skip:
    fail path richiede mock.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 83 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **369 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **32 PASS** + 1 skipped intenzionale |

**Rischi residui:**
- **No caching factory**: rerun Streamlit ricostruisce factory ogni volta
  (cost ~10ms). Errata corrige se profiler ne lamenta.
- **Cleanup nel test integration**: `test_try_persist_session_success` fa
  `sess.delete + commit` per non sporcare il DB tra test. Se il test
  fallisce dopo `save_session_result` ma prima del cleanup, una riga
  resta. Container ephemeral lo gestisce a livello fila (restart pulisce).
- **Fail path non testato**: skip esplicito; documentato come scope futuro.
  Il path `try/except Exception → (False, None, str(exc))` e' verificato
  dal type checker (mypy strict) ma non runtime.

## Impact

**🎯 Loop architetturale + UI integrati**: per la prima volta il CFO puo'
eseguire una sessione → vederla → salvarla in DB con un clic. Pattern
"esegui-vedi-salva" disaccoppiato:
- `Esegui Sessione` (sempre disponibile, lavora in-memory)
- `Salva sessione su DB` (condizionato a DB disponibile)

L'UI Streamlit ora esercita 4 livelli architetturali in cascata:
`run_session` (orchestrator) → `compute_vgp_score` (vgp) →
`allocate_tetris/build_panchina` (tetris) → `save_session_result`
(persistence + with_tenant Zero-Trust).

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze` i
nuovi simboli `get_session_factory_or_none`, `try_persist_session`,
`DEFAULT_TENANT_ID`.

## Refs

- ADR: ADR-0016 (UI Streamlit), ADR-0015 (persistenza), ADR-0014
  (mypy/ruff strict), ADR-0019 (test pattern integration)
- Predecessori: CHG-2026-04-30-040 (dashboard), CHG-2026-04-30-042
  (save_session_result)
- Successore atteso: CHG-044 `load_session_by_id` + `list_recent_sessions`
  per pagina storico; CHG futuro caching factory `@st.cache_resource`
- Commit: `316940b`
