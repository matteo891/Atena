---
id: CHG-2026-04-30-051
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 45b4757
adr_ref: ADR-0015, ADR-0016, ADR-0014, ADR-0019
---

## What

Estende `config_repository` con `list_category_referral_fees` (mappa
`category_node → referral_fee_pct` per il tenant). UI dashboard:
sidebar expander "Referral Fee per categoria" con dataframe override
esistenti + form input categoria + fee + bottone "Salva".

L12 PROJECT-RAW Round 5: *"Referral_Fee: lookup categoria + override
manuale configurabile"*. Questo CHG chiude il lato "configurabile".
Il lato "lookup automatic" (l'orchestratore usa l'override quando
l'ASIN appartiene a una categoria nota) e' scope CHG futuro.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/config_repository.py` | modificato | +costante `KEY_REFERRAL_FEE_PCT="referral_fee_pct"` + `list_category_referral_fees(db_session, *, tenant_id=1) -> dict[str, Decimal]` (filtri WHERE `scope=category`, `key=KEY_REFERRAL_FEE_PCT`, `scope_key`/`value` NOT NULL); refactor `continue` defensive → dict comprehension (governance R-01) |
| `src/talos/persistence/__init__.py` | modificato | +re-export `KEY_REFERRAL_FEE_PCT`, `list_category_referral_fees` |
| `src/talos/ui/dashboard.py` | modificato | +`fetch_category_referral_fees_or_empty(factory, *, tenant_id) -> dict[str, float]` graceful + `try_persist_category_referral_fee(factory, *, category_node, referral_fee_pct, tenant_id) -> tuple[bool, str | None]` + `_render_sidebar_referral_fees(factory)` con expander/dataframe/form/save button |
| `src/talos/ui/__init__.py` | modificato | +re-export 2 helper UI |
| `tests/integration/test_referral_fee_lookup.py` | nuovo | 7 test (empty dict, mapping post-set, filtro tenant, exclude key diverse, exclude scope global, UI floats, UI factory None) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | entry `config_repository.py` aggiornata con CHG-051 |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **452 PASS**
(380 unit/governance/golden + 72 integration).

## Why

CHG-050 ha aperto la primitiva di config persistente (soglia veto ROI
globale). L12 PROJECT-RAW richiede esplicitamente che il `Referral_Fee`
sia configurabile **per categoria** (lookup hierarchy: asin → category
→ default). Senza questo CHG:

- Il CFO non puo' definire eccezioni per categoria (es. "Books = 15%,
  Electronics = 8%, default = 12%").
- Il listino raw del CSV upload deve avere `referral_fee_pct` corretto
  per ogni riga, ma in realta' l'extractor (`io_/extract`, scope
  futuro) lo deduce dal `category_node` del Keepa.
- L12 resta dormiente.

### Decisioni di design

1. **`list_category_referral_fees` ritorna `dict[str, Decimal]`**:
   pattern lookup-friendly per il caller. L'orchestratore futuro fara'
   `referral_fee = overrides.get(category, listino_raw_value)`.
2. **Filtro WHERE multiplo (tenant + scope + key + NOT NULL)**: single
   query, no N+1. L'index `idx_config_unique` copre i 4 campi.
3. **Refactor `continue` → dict comprehension**: i filtri SQL
   `scope_key.is_not(None)` + `value_numeric.is_not(None)` rendono il
   check Python ridondante. La rimozione del `continue` evita anche il
   trigger del governance test `test_log_events_catalog`.
4. **`KEY_REFERRAL_FEE_PCT` costante esposta**: refactor-safe per il
   caller orchestrator futuro. Pattern coerente con `CONFIG_KEY_VETO_ROI`.
5. **UI form input + bottone "Salva"**: pattern coerente con il bottone
   "Salva soglia ROI come default tenant" di CHG-050. Il CFO inserisce
   una categoria alla volta (no bulk import — scope CHG futuro).
6. **`st.expander("Referral Fee per categoria")`** in sidebar: la
   sezione e' nice-to-have, non essenziale al flow principale → expander
   collapsato di default minimizza rumore visivo.
7. **`fetch_category_referral_fees_or_empty(factory: factory | None) -> dict[str, float]`**:
   ritorna `dict` non `Optional[dict]` — il vuoto e' uno stato valido
   ("nessun override registrato"). Conversione `Decimal → float` per
   `st.dataframe` JSON-friendly.

### Out-of-scope

- **Integrazione con `run_session`**: l'orchestratore NON applica
  ancora gli override per categoria. Per farlo serve:
  - Lookup `asin_master.category_node` per ogni ASIN del listino
    (richiede `asin_master` popolata da extractor reale).
  - Merge `referral_fee_overrides[category]` nella `referral_fee_pct`
    di `_enrich_listino`.
  - Errata corrige `compute_vgp_score` se i pesi del calcolo cambiano.
  Scope CHG futuro post `io_/extract`.
- **DELETE referral fee per categoria**: per ora il CFO puo' solo
  UPSERT (sovrascrivere). Errata futura per `delete_config_override`.
- **Bulk import CSV** delle referral fees: scope futuro UX.
- **Lookup hierarchy automatica** (asin > category > global con
  cascade): scope CHG dedicato.

## How

### `list_category_referral_fees` (highlight)

```python
KEY_REFERRAL_FEE_PCT = "referral_fee_pct"

def list_category_referral_fees(db_session, *, tenant_id=1):
    with with_tenant(db_session, tenant_id):
        stmt = select(ConfigOverride.scope_key, ConfigOverride.value_numeric).where(
            ConfigOverride.tenant_id == tenant_id,
            ConfigOverride.scope == SCOPE_CATEGORY,
            ConfigOverride.key == KEY_REFERRAL_FEE_PCT,
            ConfigOverride.scope_key.is_not(None),
            ConfigOverride.value_numeric.is_not(None),
        )
        return {
            str(sk): Decimal(v) for sk, v in db_session.execute(stmt).all()
        }
```

### UI helpers (highlight)

```python
def try_persist_category_referral_fee(factory, *, category_node, referral_fee_pct, tenant_id):
    try:
        with session_scope(factory) as db:
            set_config_override_numeric(
                db, key=KEY_REFERRAL_FEE_PCT, value=referral_fee_pct,
                tenant_id=tenant_id, scope=SCOPE_CATEGORY, scope_key=category_node,
            )
    except Exception as exc:
        return False, str(exc)
    return True, None


def _render_sidebar_referral_fees(factory):
    with st.sidebar.expander("Referral Fee per categoria"):
        existing = fetch_category_referral_fees_or_empty(factory)
        if existing:
            st.dataframe(pd.DataFrame([{...}]))
        category = st.text_input("Categoria")
        fee = st.number_input("Fee %", min_value=0.0, max_value=1.0, value=0.08, step=0.01)
        if st.button("Salva referral fee"):
            ok, err = try_persist_category_referral_fee(
                factory, category_node=category, referral_fee_pct=float(fee),
            )
            ...
```

### Test plan (7 integration)

1. `test_list_returns_empty_dict_when_no_overrides` — tenant vuoto → `{}`
2. `test_list_returns_mapping_after_set` — 2 categorie → 2 chiavi
3. `test_list_filters_by_tenant_id` — t1 e t2 isolati
4. `test_list_excludes_other_keys` — `veto_roi_pct` NON figura
5. `test_list_excludes_global_scope_overrides` — scope `global` NON figura
6. `test_ui_fetch_returns_floats` — UI helper ritorna `dict[str, float]`
7. `test_ui_fetch_returns_empty_dict_without_factory` — `factory=None` → `{}`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 93 files already formatted |
| Type | `uv run mypy src/` | ✅ 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **380 PASS** (governance regredito + sistemato in stesso CHG) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **72 PASS** (65 + 7) |

**Rischi residui:**
- **No integrazione orchestrator**: il CFO salva referral fees per
  categoria, ma `run_session` NON le applica. Documentato come
  out-of-scope. Il listino raw mantiene precedenza.
- **No DELETE API**: per resettare un override il CFO deve modificarlo
  (non rimuoverlo). Errata futura.
- **UI form non ha confirm su sovrascrittura**: il bottone "Salva"
  fa UPSERT senza warning se la categoria esiste gia'. Pattern
  consistente con CHG-050; scope futuro UX confirm.

## Impact

**L12 chiusa operativamente** (lato configurazione). Ora il CFO puo'
mantenere una mappa `category → referral_fee` persistente.
L'integrazione automatica con la pipeline `run_session` resta TODO,
sbloccata da CHG-051 (primitiva pronta).

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze`:
`KEY_REFERRAL_FEE_PCT`, `list_category_referral_fees`, +UI helpers.

## Refs

- ADR: ADR-0015 (persistenza + RLS), ADR-0016 (UI Streamlit), ADR-0014
  (mypy/ruff strict), ADR-0019 (test integration pattern)
- Predecessori: CHG-2026-04-30-012 (config_overrides model + RLS),
  CHG-2026-04-30-050 (config_repository numeric)
- Vision verbatim: PROJECT-RAW.md L12 Round 5 (Referral_Fee
  configurabile per categoria)
- Successore atteso: integrazione `run_session` con merge override
  per categoria (post `io_/extract` per `asin_master.category_node`);
  DELETE API; lookup hierarchy automatica
- Commit: `45b4757`
