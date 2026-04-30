---
id: CHG-2026-04-30-054
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Pending
commit: pending
adr_ref: ADR-0015, ADR-0016, ADR-0014, ADR-0019
---

## What

Chiude la triade CRUD-light di `config_overrides` con la primitiva
DELETE: `delete_config_override(db, *, key, tenant_id, scope, scope_key)`
+ 2 helper UI (`try_delete_veto_roi_threshold`,
`try_delete_category_referral_fee`) + bottoni "Reset" affiancati ai
"Salva" esistenti nella sidebar dashboard.

Il CFO ora può tornare al **default applicativo** (`DEFAULT_ROI_VETO_THRESHOLD`,
`referral_fee_pct` raw) senza dover inserire manualmente il valore di
default. Out-of-scope esplicito di CHG-2026-04-30-051 chiuso.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/config_repository.py` | modificato | + `from sqlalchemy import delete`; + `delete_config_override(db, *, key, tenant_id=1, scope=GLOBAL, scope_key=None) -> bool`. Pattern pre-check + execute (per ritornare `bool` tipizzato senza `Result.rowcount` che non e' nella signature SQLAlchemy 2.0 strict). Idempotente: `False` se non esisteva, `True` se cancellata. Validazione scope identica a `set/get`. |
| `src/talos/persistence/__init__.py` | modificato | + re-export `delete_config_override`. |
| `src/talos/ui/dashboard.py` | modificato | + import `delete_config_override`; + `try_delete_veto_roi_threshold(factory, *, tenant_id) -> tuple[bool, str \| None]`; + `try_delete_category_referral_fee(factory, *, category_node, tenant_id) -> tuple[bool, str \| None]`; sidebar — bottone "Salva soglia ROI" affiancato a "Reset al default" (`st.sidebar.columns(2)`); expander "Referral Fee per categoria" — bottoni "Salva" + "Reset" (`st.columns(2)`). |
| `src/talos/ui/__init__.py` | modificato | + re-export 2 helper UI. |
| `tests/integration/test_delete_config_override.py` | nuovo | 8 test integration (no-op missing, round-trip set→delete→get None, filter tenant, filter scope_key, no cross-pollution global vs category, scope invalido, 2 UI helper round-trip). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **475 PASS**
(387 unit/governance/golden + 88 integration).

## Why

CHG-051 ha esplicitamente lasciato fuori scope la primitiva DELETE
("per ora il CFO puo' solo UPSERT (sovrascrivere). Errata futura per
`delete_config_override`."). Senza DELETE:

- Per "rimuovere" un override il CFO doveva ri-settarlo al valore di
  default — ma il default applicativo e' definito nel codice, non in
  DB, quindi serviva conoscere il numero esatto.
- Test integration di config dovevano fare cleanup manuale via SQL
  raw, non via API ufficiale.
- Il pattern UX "Reset" (familiare al CFO da qualunque applicazione
  business) era assente.

Questo CHG completa la matrice CRUD: `set` (write/upsert), `get` /
`list_*` (read), `delete` (reset al default). Il loop e' chiuso.

### Decisioni di design

1. **Pre-check + execute** invece di `result.rowcount`: in SQLAlchemy 2.0
   strict mypy, `Session.execute()` ritorna `Result[Any]` che NON espone
   `rowcount` nel type stub. Cast/`type: ignore` sono brutti e fragili
   (signature potrebbe cambiare in mypy/SA upgrade). Il pre-check con
   `select(ConfigOverride.id)` aggiunge 1 round-trip ma e':
   - Type-safe per costruzione (signature `Result.scalar()` standard).
   - Auto-documentato (idempotenza esplicita).
   - Costo trascurabile (UNIQUE INDEX `idx_config_unique` lo rende O(log N)).

2. **`delete_config_override` ritorna `bool`** (non `int`/`None`): il
   caller principale (UI) vuole sapere "e' successo qualcosa o no?",
   non "quante righe". Per multi-row delete future (es. cancellare
   tutti gli override di un tenant) servira' un'API distinta
   (`delete_all_config_overrides_for_tenant`).

3. **Idempotenza**: cancellare un override inesistente NON e' un
   errore. Il caller UI non deve gestire "non c'era nulla da
   cancellare" come caso speciale. Pattern coerente con `DROP IF EXISTS`
   SQL e con UX "il bottone Reset funziona sempre".

4. **`scope_key=None` vs valore-string distinti**: la query usa
   `is_(None)` per `scope_key=None`, `==` per valori. Gestione corretta
   del NULL Postgres (CHG-050 ha già fixato `NULLS NOT DISTINCT` per
   l'UNIQUE INDEX, ma per il DELETE serve comunque la WHERE NULL-aware).

5. **Bottoni Reset affiancati a Salva via `st.columns(2)`**: pattern UX
   familiare. Niente confirm dialog (azione reversibile via re-set,
   non distruttiva). Pattern coerente con CHG-050/051 layout sidebar.

6. **`try_delete_*` graceful con `Exception` catturato**: `tuple[bool,
   str | None]` come `try_persist_*` (CHG-050/051). UI non crasha.

7. **No multi-page** ancora: l'expander resta nel `_render_sidebar`
   monolitico. Refactor multi-page ADR-0016 e' separato CHG.

### Out-of-scope

- **DELETE multi-row** (es. "cancella tutti gli override di un tenant"):
  scope CHG futuro se necessario. Per ora 1 chiamata = 1 row.
- **Audit di DELETE**: la tabella `config_overrides` non ha trigger
  audit (gli `audit_log` triggers sono su `sessions`/`vgp_results`/
  `cart_items`). Errata corrige ADR-0015 se compliance lo richiedera'.
- **Bulk reset UI** ("Reset tutto"): scope futuro, richiede confirm
  dialog (azione potenzialmente distruttiva di molti override).
- **Confirm dialog** sui Reset singoli: pattern UX scope futuro
  multi-page.

## How

### `delete_config_override` (highlight)

```python
def delete_config_override(db_session, *, key, tenant_id=1,
                           scope="global", scope_key=None) -> bool:
    _validate_scope(scope)
    scope_key_filter = (
        ConfigOverride.scope_key.is_(None)
        if scope_key is None
        else ConfigOverride.scope_key == scope_key
    )
    with with_tenant(db_session, tenant_id):
        # Pre-check tipizzato (ritornare bool senza affidarsi a Result.rowcount)
        existing = db_session.scalar(
            select(ConfigOverride.id).where(
                ConfigOverride.tenant_id == tenant_id,
                ConfigOverride.scope == scope,
                scope_key_filter,
                ConfigOverride.key == key,
            ),
        )
        if existing is None:
            return False
        stmt = delete(ConfigOverride).where(...)  # stesse condizioni
        db_session.execute(stmt)
        return True
```

### UI helpers (highlight)

```python
def try_delete_veto_roi_threshold(factory, *, tenant_id=DEFAULT_TENANT_ID):
    try:
        with session_scope(factory) as db:
            delete_config_override(db, key=CONFIG_KEY_VETO_ROI, tenant_id=tenant_id)
    except Exception as exc:
        return False, str(exc)
    return True, None
```

Sidebar: `st.sidebar.columns(2)` con "Salva soglia ROI" + "Reset al default";
expander Referral Fee con stesso pattern + "Salva" / "Reset".

### Test plan (8 integration)

1. `test_delete_missing_key_returns_false` — idempotenza
2. `test_delete_existing_returns_true_and_get_returns_none` — round-trip
3. `test_delete_filters_by_tenant_id` — RLS-style tenant isolation
4. `test_delete_filters_by_scope_key` — Books/Electronics non si toccano
5. `test_delete_does_not_touch_global_when_category_targeted` — scope distinti
6. `test_delete_invalid_scope_raises` — validation
7. `test_ui_helper_try_delete_veto_roi_threshold` — UI round-trip
8. `test_ui_helper_try_delete_category_referral_fee` — UI round-trip

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 96 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **387 PASS** (invariato) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **88 PASS** (80 + 8) |

**Rischi residui:**
- **Pre-check costo extra**: 1 round-trip aggiuntivo per ogni DELETE.
  Trascurabile vs costo di 1 query DB (ms su LAN). Profiler post-MVP
  puo' dropparlo se il tipo statico cambierà.
- **No confirm UX**: bottone "Reset" rimuove l'override senza dialog.
  Azione reversibile (basta re-set), ma se l'override conteneva un
  valore "esotico" (es. fee 0.99% per categoria sperimentale), il
  CFO può doverlo ri-inserire. Documentato come errata futura UX
  multi-page.
- **Test UI helper persistono dati**: il `session_scope` interno fa
  commit. I test usano `tenant_id=99` (sintetico) + cleanup paranoid
  finally. Se un run fallisce a metà, può lasciare residui — il
  set successivo li sovrascrive comunque (UPSERT semantica). Pattern
  noto e accettabile MVP.

## Test di Conformità

- **Path codice applicativo:** `src/talos/persistence/config_repository.py`
  ✓, `src/talos/ui/dashboard.py` ✓ (entrambi in path consentiti).
- **Test integration sotto `tests/integration/`:** ✓ (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `delete_config_override`
  mappa ad ADR-0015 (persistenza); UI helper mappano ad ADR-0016.
- **Backward compat:** signature `set/get/list_category_referral_fees`
  invariate. Nuovo simbolo `delete_*` puramente additivo.
- **Impact analysis pre-edit:** risk LOW su `set_config_override_numeric`
  (0 caller upstream nel grafo); risk MEDIUM ammesso sui processi UI
  perché le funzioni `_render_sidebar` / `_render_sidebar_referral_fees`
  sono toccate (refactor del button layout), ma comportamento
  esistente preservato (Salva ancora funziona, test 475 PASS).

## Impact

**Triade CRUD config_overrides chiusa**: write (set), read (get/list),
delete (reset). Il loop UX completo è disponibile per il CFO senza
intermediari (extractor non richiesto per usare i bottoni).

`gitnexus_detect_changes` segnala 4 processi UI affected ma 0 simboli
con behavioral change distruttivo: i bottoni Salva esistenti
funzionano identici, sono solo affiancati da Reset addon.

## Refs

- ADR: ADR-0015 (persistenza + RLS), ADR-0016 (UI Streamlit), ADR-0014
  (mypy/ruff strict), ADR-0019 (test integration pattern).
- Predecessori: CHG-2026-04-30-050 (`set_config_override_numeric`),
  CHG-2026-04-30-051 (`list_category_referral_fees` + UI),
  CHG-2026-04-30-053 (orchestrator referral fee resolved).
- Vision verbatim: out-of-scope dichiarato in CHG-051 (DELETE
  referral fee).
- Successore atteso: confirm dialog UX su Reset; bulk reset; audit
  trail config_overrides; multi-page refactor.
- Commit: pending (backfill).
