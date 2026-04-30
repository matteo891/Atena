---
id: CHG-2026-04-30-050
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 1bdac33
adr_ref: ADR-0015, ADR-0016, ADR-0014, ADR-0019
---

## What

Implementa `config_repository` per lookup + upsert runtime di
`config_overrides` (Allegato A ADR-0015 — RLS Zero-Trust). UI dashboard
pre-carica la soglia veto ROI dal DB del tenant + bottone "Salva soglia
ROI come default tenant". Sblocca configurabilita' persistente.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/config_repository.py` | nuovo | `SCOPE_GLOBAL`/`SCOPE_CATEGORY`/`SCOPE_ASIN` costanti + `_validate_scope` + `get_config_override_numeric(...)` (lookup) + `set_config_override_numeric(...)` (UPSERT `pg_insert.on_conflict_do_update`); tutto sotto `with_tenant` |
| `src/talos/persistence/__init__.py` | modificato | +re-export 5 simboli (3 costanti scope + 2 funzioni) |
| `migrations/versions/e8b80f77961b_*.py` | nuovo | Bug fix: `idx_config_unique` ricreato con `NULLS NOT DISTINCT` (Postgres 15+). Era impossibile UPSERT su `(tenant, scope, NULL, key)` perche' Postgres tratta `NULL != NULL` per UNIQUE — UPSERT non matcha → INSERT crea sempre nuova riga. |
| `src/talos/ui/dashboard.py` | modificato | +`fetch_veto_roi_threshold_or_default(factory, ...)` (graceful default) + `try_persist_veto_roi_threshold(factory, threshold, tenant_id)` (UPSERT + tuple result) + sidebar pre-carica + bottone "Salva soglia ROI come default tenant"; +`CONFIG_KEY_VETO_ROI = "veto_roi_pct"` |
| `src/talos/ui/__init__.py` | modificato | +re-export 3 simboli config |
| `tests/integration/test_config_repository.py` | nuovo | 7 test (None su missing key, set→get roundtrip, UPSERT overwrites, filtro tenant, float→Decimal, scope invalid raises, default scope=global) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry migration `e8b80f77961b` + entry `config_repository.py` |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **445 PASS**
(380 unit/governance/golden + 65 integration).

## Why

ADR-0015 Allegato A ha la tabella `config_overrides` con RLS attiva da
CHG-012 (~50 commit fa). Era **dormiente**: nessun caller, nessuna API
esposta. Il pattern "il CFO modifica la soglia ROI nella UI e la
ritrova al rerun" richiede la primitiva di persistenza runtime.

Senza il repository:
- La soglia ROI veniva resettata al default ogni rerun Streamlit.
- Ogni tenant aveva la stessa soglia hardcoded (DEFAULT_ROI_VETO_THRESHOLD).
- Multi-tenancy futura impossibile da differenziare per parametri.

L10 (PROJECT-RAW.md Round 5) chiede esplicitamente: *"soglia 8%
configurabile dal cruscotto, persistita in DB come config"*. Questo
CHG la chiude operativamente.

### Bug Postgres NULL UNIQUE

Lo schema originale (CHG-012) ha `idx_config_unique` UNIQUE su
`(tenant_id, scope, scope_key, key)`. Postgres default tratta
`NULL != NULL` per UNIQUE constraints (SQL standard). Con
`scope_key=NULL` (override globale, caso piu' frequente),
**l'UPSERT non matcha mai**: ogni `INSERT ... ON CONFLICT (...) DO UPDATE`
con `scope_key=NULL` crea una nuova riga invece di aggiornare la
esistente. Il `get` poi ritorna la prima — il fix sembra silenzioso.

Test `test_upsert_overwrites_existing_value` ha rilevato il bug.
Migration `e8b80f77961b` ricrea l'index con `NULLS NOT DISTINCT`
(Postgres 15+). Container test postgres:16-alpine compatibile.

### Decisioni di design

1. **`SCOPE_GLOBAL`/`SCOPE_CATEGORY`/`SCOPE_ASIN` costanti string**: il
   modello ORM non ha CHECK constraint su `scope`. Validazione
   applicativa in `_validate_scope` con ValueError esplicito.
2. **API separate per `value_numeric` e `value_text`**: il modello ha
   entrambe le colonne (mutuamente esclusive). Per ora il CHG-050 copre
   solo numeric (`set_config_override_numeric` setta `value_text=NULL`
   esplicitamente). Versioni text sono scope CHG futuro quando emergeranno
   override testuali (preset di brand, regole NLP).
3. **UPSERT con `pg_insert.on_conflict_do_update`**: idiomatico SQLAlchemy
   2.0 per Postgres. Non portabile a SQLite (acceptable per ADR-0015
   Postgres-only).
4. **`with_tenant` interno (non chiesto al caller)**: la primitiva e'
   self-contained. Pattern coerente con `save_session_result`,
   `list_recent_sessions`.
5. **Float → Decimal via `str()`**: `Decimal(str(0.1))` → `Decimal('0.1')`,
   senza drift binary. Numeric(12,4) trunca a 4 decimali (`0.1234567 →
   0.1235`).
6. **`fetch_veto_roi_threshold_or_default(factory=None, ...)`**: `factory`
   nullable. Se factory None (DB non disponibile), graceful return
   `default`. UI funziona senza DB.
7. **`_render_sidebar` accetta `factory` opzionale**: la sidebar e' la
   prima cosa che si rende; chiama `get_session_factory_or_none()` una
   volta, lo passa qui. Niente double-create.
8. **Bottone "Salva soglia ROI come default tenant"** appare SOLO se
   factory != None. Coerente con il pattern graceful degrade della UI.

### Out-of-scope

- **`set_config_override_text`**: scope CHG futuro (override testuali).
- **DELETE override** (reset al default): scope futuro
  `delete_config_override(...)`.
- **Lookup hierarchy** (asin override > category > global con cascade):
  scope CHG futuro che implementa la risoluzione ordinata. Per ora
  il caller specifica esplicitamente lo scope.
- **Migration retroattiva** di config_overrides duplicate pre-fix:
  container ephemeral non ne ha. Produzione richiederebbe script
  cleanup.
- **Riapplicare soglia ROI in dashboard widget** automaticamente
  (live reload): scope refactor multi-page ADR-0016 con `@st.cache_data`.

## How

### `config_repository.py` (highlight)

```python
def get_config_override_numeric(db_session, *, key, tenant_id=1,
                                scope="global", scope_key=None):
    _validate_scope(scope)
    scope_key_filter = (
        ConfigOverride.scope_key.is_(None) if scope_key is None
        else ConfigOverride.scope_key == scope_key
    )
    with with_tenant(db_session, tenant_id):
        stmt = select(ConfigOverride.value_numeric).where(
            ConfigOverride.tenant_id == tenant_id,
            ConfigOverride.scope == scope,
            scope_key_filter,
            ConfigOverride.key == key,
        )
        return db_session.scalar(stmt)


def set_config_override_numeric(db_session, *, key, value, tenant_id=1, ...):
    decimal_value = Decimal(str(value))
    with with_tenant(db_session, tenant_id):
        stmt = (
            pg_insert(ConfigOverride)
            .values(...)
            .on_conflict_do_update(
                index_elements=["tenant_id", "scope", "scope_key", "key"],
                set_={"value_numeric": decimal_value, "value_text": None},
            )
        )
        db_session.execute(stmt)
```

### Migration `e8b80f77961b` (highlight)

```python
def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_config_unique")
    op.execute(
        "CREATE UNIQUE INDEX idx_config_unique "
        "ON config_overrides (tenant_id, scope, scope_key, key) "
        "NULLS NOT DISTINCT"
    )
```

### Test plan (7 integration)

1. `test_get_returns_none_for_missing_key`
2. `test_set_then_get_roundtrip`
3. `test_upsert_overwrites_existing_value` — verifica fix bug NULL
4. `test_filters_by_tenant_id` — RLS-compatible
5. `test_set_with_float_converts_to_decimal` — drift mitigation
6. `test_invalid_scope_raises`
7. `test_scope_global_default` — `scope=GLOBAL`, `scope_key=None`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 92 files already formatted |
| Type | `uv run mypy src/` | ✅ 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **380 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **65 PASS** (58 + 7) |
| Migration | `alembic upgrade head` | ✅ applied `e8b80f77961b` |

**Rischi residui:**
- **Postgres < 15** non supporta `NULLS NOT DISTINCT`. Container e
  produzione MVP usano Postgres 16, ma migration document il vincolo
  versione. ADR-0015 specifica gia' Postgres 16; ok.
- **No DELETE API**: per resettare al default, il caller deve fare un
  set con il valore default. Errata futura per `delete_config_override`.
- **`scope_key=None` resta NULL nella tabella**: con il fix UNIQUE
  `NULLS NOT DISTINCT` due null sono trattati uguali → UPSERT funziona.
  Pattern documentato.

## Impact

**Configurabilita' persistente aperta**: il CFO ora puo' modificare la
soglia ROI nello slider, premere "Salva soglia ROI come default
tenant", e al rerun la sidebar carica la soglia salvata. Pattern
estendibile: futuri override (`referral_fee_pct`, `velocity_target_days`,
`lot_size`) possono essere persistiti con la stessa primitiva.

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze`
i nuovi simboli `config_repository.py` + UI helper.

## Refs

- ADR: ADR-0015 (persistenza + RLS), ADR-0016 (UI Streamlit), ADR-0014
  (mypy/ruff strict), ADR-0019 (test integration pattern)
- Predecessori: CHG-2026-04-30-012 (`config_overrides` model + RLS),
  CHG-2026-04-30-035 (`compute_vgp_score` con threshold parametro)
- Vision verbatim: PROJECT-RAW.md L10 Round 5 ("soglia 8% configurabile
  dal cruscotto, persistita in DB come config")
- Successore atteso: lookup `Referral_Fee` per categoria (CHG-051?);
  `set_config_override_text` + override testuali; lookup hierarchy
  asin > category > global
- Commit: `1bdac33`
