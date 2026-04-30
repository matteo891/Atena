---
id: CHG-2026-04-30-031
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 877b8ea
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

Estende `TalosSettings` con 4 campi ancorati alle env var di bootstrap DB e rifattorizza `scripts/db_bootstrap.py` per leggerle via `get_settings()` anziché `os.getenv` diretto. Secondo consumatore reale del config layer dopo `engine.py` (CHG-030); chiude il debito esplicitamente inscritto in CHG-029 ("Out-of-scope: refactor `db_bootstrap.py` per leggere via `TalosSettings`").

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/config/settings.py` | modificato | +4 campi `str | None = None`: `db_url_superuser`, `admin_password`, `app_password`, `audit_password`; nessun nuovo validator (coerenza con i due esistenti) |
| `scripts/db_bootstrap.py` | modificato | `os.getenv` → `get_settings()`; rimosso `import os`, `_REQUIRED_ENV` rimpiazzato da check su `settings.*_password`; `_resolve_superuser_url()` legge da settings (priorità invariata `db_url_superuser` → `db_url`) |
| `tests/unit/test_settings.py` | modificato | +5 test: 4 sui campi nuovi (default None + override env) + 1 sulla priorità `db_url_superuser` rispetto a `db_url` (sanity check semantico) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Riga `src/talos/config/settings.py` aggiornata con elenco campi attuali + riferimento CHG-031 |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; ~226 test PASS (221 + 5 nuovi unit settings). Test integration `test_db_bootstrap.py` passa env via subprocess (variabili `TALOS_*` raggiungono il child) — invariato funzionalmente.

## Why

Tre debiti chiusi:

1. **Centralizzazione completa env var DB**: dopo CHG-030 `engine.py` legge via settings; `db_bootstrap.py` restava l'ultimo consumatore con `os.getenv` diretto su 4 var. Ora tutte le var DB convergono su un unico punto tipato.
2. **Sblocca (c) lookup `config_overrides` runtime**: per leggere la soglia ROI dal DB serve una sessione costruita con credenziali consistenti. Avere il pattern "tutte le credenziali via settings" è prerequisito naturale.
3. **Riduzione superficie di errore**: `_REQUIRED_ENV` tuple manuale e check dedicati erano brittle. Con campi tipati il check diventa "campo None?" — più semplice e meno duplicato.

### Decisioni di design

1. **4 campi nuovi tutti `str | None = None`**: stesso pattern di `db_url`. Import-time non fallisce in ambienti senza env (test/CI/dev). Errore esplicito al call site quando i campi sono richiesti (script `db_bootstrap.py`).
2. **Niente nuovo validator**: le 3 password sono stringhe arbitrarie (no vincoli di formato). `db_url_superuser` è una URL psycopg/SQLAlchemy: stesso "no validator" di `db_url` — la validazione effettiva avviene quando psycopg tenta la connessione.
3. **`_check_required_env()` rinominato `_check_required_settings(settings)`**: non più check su nomi env var stringa, ma su attributi del modello. Il messaggio di errore continua a citare i nomi env var canonici (`TALOS_ADMIN_PASSWORD`, ecc.) per compatibilità con il test integration `test_missing_password_fails_with_exit_code` che fa `assert "TALOS_APP_PASSWORD" in result.stderr`.
4. **Priorità `db_url_superuser` su `db_url` invariata**: replica `os.getenv("TALOS_DB_URL_SUPERUSER") or os.getenv("TALOS_DB_URL")` con `settings.db_url_superuser or settings.db_url`. Stesso comportamento.
5. **Strip `+psycopg` invariato**: la trasformazione `postgresql+psycopg://` → `postgresql://` resta nello script (è semantica di consumo del bootstrap, non di settings).
6. **`migrations/env.py` resta su `os.getenv`**: confermo scope di CHG-030 — Alembic isolato, no `talos.*` import al runtime di migrazione. Centralizzazione qui sarebbe scope diverso.

## How

### Estensione `TalosSettings`

```python
class TalosSettings(BaseSettings):
    # ... esistenti
    db_url: str | None = Field(default=None, ...)
    roi_veto_threshold: float = Field(...)
    # nuovi (CHG-031)
    db_url_superuser: str | None = Field(default=None, description="URL superuser per bootstrap DB (env: TALOS_DB_URL_SUPERUSER)")
    admin_password: str | None = Field(default=None, description="Password ruolo talos_admin (env: TALOS_ADMIN_PASSWORD)")
    app_password: str | None = Field(default=None, description="Password ruolo talos_app (env: TALOS_APP_PASSWORD)")
    audit_password: str | None = Field(default=None, description="Password ruolo talos_audit (env: TALOS_AUDIT_PASSWORD)")
```

### Refactor `db_bootstrap.py`

```python
from talos.config import get_settings, TalosSettings

def _resolve_superuser_url(settings: TalosSettings) -> str:
    url = settings.db_url_superuser or settings.db_url
    if not url:
        raise RuntimeError("TALOS_DB_URL_SUPERUSER (o TALOS_DB_URL) non settato. ...")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)

def _check_required_settings(settings: TalosSettings) -> None:
    missing: list[str] = []
    if not settings.admin_password: missing.append("TALOS_ADMIN_PASSWORD")
    if not settings.app_password: missing.append("TALOS_APP_PASSWORD")
    if not settings.audit_password: missing.append("TALOS_AUDIT_PASSWORD")
    if missing:
        raise RuntimeError("Env var richieste assenti: " + ", ".join(missing))

def bootstrap() -> None:
    settings = get_settings()
    _check_required_settings(settings)
    url = _resolve_superuser_url(settings)
    admin_pwd = settings.admin_password
    app_pwd = settings.app_password
    audit_pwd = settings.audit_password
    assert admin_pwd and app_pwd and audit_pwd  # post-check, narrowing per mypy
    # ... resto invariato
```

### Test plan

`test_settings.py` (+5 test):
1. `test_db_url_superuser_default_none` → `TALOS_DB_URL_SUPERUSER` assente → `settings.db_url_superuser is None`
2. `test_db_url_superuser_from_env` → setenv → letta correttamente
3. `test_passwords_default_none` → tutti i 3 campi password sono `None` di default
4. `test_passwords_from_env` → 3 setenv → 3 valori letti
5. `test_db_url_superuser_independent_from_db_url` → setenv solo `TALOS_DB_URL_SUPERUSER`, lascia `TALOS_DB_URL` vuoto → settings.db_url is None ma db_url_superuser è settata (verifica indipendenza dei due campi)

Test integration `test_db_bootstrap.py`: **invariato**. Lo script è invocato via subprocess; le env var `TALOS_*` fluiscono al child via `env=os.environ.copy() + env_extra`. `TalosSettings()` nel child legge l'ambiente fresco. Test `test_missing_password_fails_with_exit_code` continua a passare: lo stderr contiene "TALOS_APP_PASSWORD" per costruzione del messaggio.

### Out-of-scope

- **Refactor `migrations/env.py`**: confermato scope diverso (Alembic isolato).
- **Validatori per password**: nessun vincolo di lunghezza/formato richiesto da PostgreSQL.
- **Lookup `config_overrides` runtime**: scope CHG separato, ora sbloccabile.
- **`extra='forbid'` su env var TALOS_***: limite noto pydantic-settings (CHG-029), non risolto qui.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/ scripts/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (28 source files invariati) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~226 PASS (221 + 5) |
| Integration | `uv run pytest tests/integration/test_db_bootstrap.py -q` | atteso ✅ 9 PASS (richiede `TALOS_DB_URL` Postgres + `talos-pg-test` container; se assenti → SKIP module-level) |

**Rischi residui:**

- I 4 nuovi campi sono tutti opzionali: import-time della config non fallisce in ambienti senza env var. La validazione avviene al call site (`db_bootstrap.py`). Pattern coerente con `db_url`.
- `TalosSettings` cresce a 6 campi. Soglia di leggibilità ancora bassa, ma se cresce ulteriormente vale la pena spezzare in sub-settings (`DbSettings`, `VgpSettings`, ecc.) — scope futuro.
- Test integration richiede ambiente Postgres reale. Se `TALOS_DB_URL` non è settata in CI → skip module-level (vedere `tests/integration/conftest.py`). CI gate futuro deve fail-fast se non raccoglie almeno N integration test, evitando skip silente.

## Refs

- ADR: ADR-0015 (persistence — ruoli Zero-Trust), ADR-0014 (mypy/ruff strict + pydantic-settings), ADR-0013 (struttura `config/`), ADR-0019 (test pattern unit)
- Predecessore: CHG-2026-04-30-030 (refactor `engine.py` via settings — primo consumatore)
- Predecessore originario: CHG-2026-04-30-021 (`db_bootstrap.py` originale con `os.getenv`)
- Vision: PROJECT-RAW.md L10 (configurabilità) — questo CHG completa la centralizzazione env var DB
- Successore atteso: lookup `config_overrides` runtime per soglia ROI (ora sbloccato); centralizzazione `migrations/env.py` (scope separato, basso valore attuale)
- Commit: `877b8ea`
