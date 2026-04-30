---
id: CHG-2026-04-30-020
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: ddb3229
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Database lifecycle minimo** per l'app Talos: factory `Engine`, factory `sessionmaker`, context manager `session_scope` (commit/rollback/close) e context manager `with_tenant` che imposta `talos.tenant_id` (e opzionalmente `ROLE`) in modo tx-scoped.

Sblocca la scrittura di qualsiasi futuro modulo applicativo che tocca DB (`vgp/`, `tetris/`, `formulas/`, `ui/`): senza session factory + RLS context, lo schema persistenza è una lavagna senza gesso.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/engine.py` | nuovo | `create_app_engine(url=None)` — engine SQLAlchemy 2.0 sync; URL esplicito o fallback su env var `TALOS_DB_URL`; pool `5+10` (sync app); `pool_pre_ping=True`, `future=True` |
| `src/talos/persistence/session.py` | nuovo | `make_session_factory(engine)` → `sessionmaker[Session]`; `session_scope(factory)` context manager (commit/rollback/close); `with_tenant(session, tenant_id, *, role=None)` context manager (`SET LOCAL talos.tenant_id` + opzionale `SET LOCAL ROLE`) |
| `src/talos/persistence/__init__.py` | modificato | Re-export `create_app_engine`, `make_session_factory`, `session_scope`, `with_tenant` |
| `tests/unit/test_persistence_engine.py` | nuovo | Smoke + URL precedence + RuntimeError senza env |
| `tests/unit/test_persistence_session.py` | nuovo | sessionmaker type + with_tenant role validation |
| `tests/integration/test_session_scope.py` | nuovo | commit/rollback runtime + `with_tenant` setta `current_setting('talos.tenant_id')` + isolamento RLS effettivo via with_tenant |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; **161 test** + nuovi (~8 unit + ~4 integration).

## Why

CHG-019 ha verificato che lo schema DB è coerente runtime. Ma **scrivere un modulo applicativo che chiama il DB** richiede tre primitive che non esistevano ancora:
1. **Engine factory** che legga la stessa env var di Alembic (`TALOS_DB_URL`) — disciplina single-source.
2. **Session factory** + context manager `session_scope` con commit/rollback/close — pattern app-tipico.
3. **`with_tenant(session, tenant_id)`** — la primitiva Zero-Trust di ADR-0015. Senza di questa, ogni modulo dovrebbe ripetere `session.execute(text("SET LOCAL talos.tenant_id = ..."))` con il rischio di dimenticarlo (= leak cross-tenant).

Inoltre la **scoperta runtime di CHG-019** (`postgres` ha BYPASSRLS) ha reso evidente la necessità di poter switcciare ruolo da codice (`SET LOCAL ROLE talos_app`) per attività che devono passare per RLS effettivo. La firma `with_tenant(session, tenant_id, *, role=None)` rende il role-switch opzionale: in dev/test (no ruoli applicativi) si lascia `None`; in prod (post `db-bootstrap.sh`) si passa `role='talos_app'`.

## How

### `engine.py`

```python
def create_app_engine(url: str | None = None) -> Engine:
    url = url or os.getenv("TALOS_DB_URL")
    if not url:
        raise RuntimeError(...)
    return create_engine(url, pool_pre_ping=True, future=True,
                         pool_size=5, max_overflow=10)
```

- **URL precedence:** parametro esplicito > env var `TALOS_DB_URL`. Stessa env var di Alembic (`migrations/env.py`).
- **Pool conservativo (5+10):** app Streamlit single-process, traffico interno; non serve high-concurrency. Aggiustabile se UI multi-utente.
- **`pool_pre_ping=True`:** healtcheck sulla connessione prima del riuso (utile con tmpfs ephemeral o restart Postgres).
- **`future=True`:** stile SQLAlchemy 2.0.

### `session.py`

```python
def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)

@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@contextmanager
def with_tenant(session: Session, tenant_id: int, *, role: str | None = None) -> Iterator[Session]:
    tid = int(tenant_id)
    if role is not None and not _is_safe_identifier(role):
        raise ValueError(f"Invalid DB role: {role!r}")
    if not session.in_transaction():
        session.begin()
    session.execute(text(f"SET LOCAL talos.tenant_id = '{tid}'"))
    if role is not None:
        session.execute(text(f"SET LOCAL ROLE {role}"))
    yield session
    # SET LOCAL e' tx-scoped: nessun reset esplicito
```

- **`expire_on_commit=False`:** dopo commit gli oggetti restano leggibili (più ergonomico per UI/test).
- **`SET LOCAL` non parametrizzabile:** Postgres non supporta parametri `$1` per `SET`. Mitigazione anti-injection: `tenant_id` è cast esplicito a `int`; `role` passa per whitelist `_is_safe_identifier` (alphanumeric + underscore).
- **`with_tenant` non resetta:** `SET LOCAL` muore con il commit/rollback della transazione. Il caller normale userà `with_tenant` **dentro** un `session_scope`, quindi il reset arriva gratis.
- **`session.in_transaction()`:** se non c'è tx aperta, ne apre una. Pattern: `with session_scope(factory) as s, with_tenant(s, 42) as s: ...` funziona in entrambi i casi.

### `__init__.py` re-exports

```python
from talos.persistence.engine import create_app_engine
from talos.persistence.session import make_session_factory, session_scope, with_tenant
```

### Test unit

- `test_create_app_engine_explicit_url`: passa `sqlite:///:memory:` → ritorna `Engine` valido (no DB connection ancora).
- `test_create_app_engine_env_fallback`: monkeypatch `TALOS_DB_URL=sqlite:///:memory:` → no errore.
- `test_create_app_engine_raises_without_url`: monkeypatch `TALOS_DB_URL` a `None` → `RuntimeError`.
- `test_make_session_factory_returns_sessionmaker`: verifica tipo + `bind` corretto.
- `test_with_tenant_rejects_unsafe_role`: passa `role="talos_app; DROP TABLE x"` → `ValueError`.
- `test_with_tenant_accepts_safe_role`: passa `role="talos_app"` → no errore (non eseguito su sqlite, mock di session).

### Test integration (richiede `TALOS_DB_URL`)

- `test_session_scope_commits_on_success`: INSERT in `config_overrides` dentro `session_scope` → fuori dal context, una nuova session vede la riga (poi cleanup manuale).
- `test_session_scope_rolls_back_on_exception`: INSERT + `raise RuntimeError` → fuori dal context, la riga NON è visibile.
- `test_with_tenant_sets_session_var`: dentro `with_tenant(s, 42)`, `SELECT current_setting('talos.tenant_id')` ritorna `'42'`.
- `test_with_tenant_isolates_rls_effective`: stessa logica di CHG-019 ma costruita via `with_tenant` (verifica end-to-end del wiring).

Per evitare side-effect persistenti: i primi due test fanno cleanup esplicito (DELETE) o usano una savepoint. Approccio scelto: una `engine.connect()` separata per la verifica + DELETE finale.

### Out-of-scope

- **Bootstrap ruoli `talos_app/talos_admin/talos_audit`** + `db-bootstrap.sh`: scope CHG-021 (prossimo). Senza ruoli, `with_tenant(s, 42, role='talos_app')` fallirà con `role does not exist` — atteso.
- **Config layer pydantic-settings (`config/`):** scope CHG-022 (subito dopo). Per ora `create_app_engine` legge direttamente env var.
- **Connection pool tuning** per UI multi-utente: rinviato a quando arriverà `ui/` (ADR-0016).
- **Connection retry/backoff:** non in scope; `pool_pre_ping` copre il caso comune.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (19 source files) |
| Unit | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~161 PASS |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -v` | atteso ✅ 12 PASS (8 + 4 nuovi) |

**Rischi residui:**
- `with_tenant` non valida che `tenant_id > 0`: la CHECK è applicativa nel layer chiamante (ad es. validazione UI). Documentato.
- `SET LOCAL ROLE` whitelist via `isalnum()` + underscore: stretta ma non copre prefissi come `pg_`. Per la fase corrente (3 ruoli noti: `talos_app/talos_admin/talos_audit`) è sufficiente. Errata corrige ammessa se serve estendere.
- Pool `5+10` non profilato: scelta empirica per app sync single-process. Da ricalibrare quando arriverà `ui/`.
- `expire_on_commit=False` evita refresh eager dopo commit ma può sorprendere chi legge l'oggetto post-commit aspettandosi valori "freschi". Documentato nel docstring.
- L'engine non ha listener `connect`/`begin` per auto-`SET ROLE`: se in futuro vorremo che ogni connessione fisica si assicuri di essere `talos_app`, va aggiunto un `event.listens_for(Engine, "connect")` con `SET SESSION ROLE`. Per ora il role switch è esplicito via `with_tenant`.

## Refs

- ADR: ADR-0015 (Zero-Trust + RLS — `with_tenant` realizza il SET LOCAL della policy), ADR-0014 (mypy strict), ADR-0013 (struttura `persistence/`), ADR-0019 (test pattern)
- Predecessore: CHG-2026-04-30-019 (`tests/integration/` infrastruttura — riusa la stessa fixture pattern)
- Successore atteso: CHG-021 `scripts/db-bootstrap.sh` (ruoli + GRANT/REVOKE) → sblocca `with_tenant(..., role='talos_app')` in prod; CHG-022 `config/` pydantic-settings
- Commit: `ddb3229`
