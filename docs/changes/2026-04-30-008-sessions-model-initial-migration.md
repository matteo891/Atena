---
id: CHG-2026-04-30-008
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Primo modello concreto della persistence**: `AnalysisSession` (tabella `sessions`) — nucleo centrale di ogni sessione di analisi. È la prima delle 10 tabelle dell'Allegato A di ADR-0015. Genera la **revision Alembic iniziale** `9d9ebe778e40_create_sessions.py` con DDL aderente verbatim allo schema dell'Allegato A.

Niente Postgres reale ancora: la migration è **validata offline** via `alembic upgrade head --sql` (output SQL coerente con Allegato A).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/__init__.py` | nuovo | Re-export `AnalysisSession`. L'import in `talos.persistence` registra la tabella in `Base.metadata` (visibile a `migrations/env.py`) |
| `src/talos/persistence/models/analysis_session.py` | nuovo | `class AnalysisSession(Base)` con `__tablename__ = "sessions"` e tutte le 7 colonne dell'Allegato A: `id` (BigInteger PK autoincrement), `started_at` (TIMESTAMP TZ default NOW), `ended_at` (TIMESTAMP TZ nullable), `budget_eur` (Numeric 12,2), `velocity_target` (Integer default 15), `listino_hash` (CHAR 64), `tenant_id` (BigInteger default 1) |
| `migrations/versions/9d9ebe778e40_create_sessions.py` | nuovo | Initial revision Alembic. `op.create_table("sessions", ...)` con tutti i `server_default` corretti |
| `tests/unit/test_persistence_skeleton.py` | modificato | `test_base_metadata_no_tables_yet` → `test_base_metadata_has_registered_tables` (asserzione invertita ora che `sessions` è registrata) |
| `tests/unit/test_analysis_session_model.py` | nuovo | 9 test: tablename, registrazione metadata, set colonne, PK BigInteger, listino_hash CHAR(64), budget_eur NUMERIC(12,2) NOT NULL, velocity_target default 15, tenant_id default 1, ended_at TIMESTAMP TZ nullable, costruzione con Decimal |
| `src/talos/persistence/__init__.py` | modificato | Re-export `AnalysisSession` (oltre a `Base`) |
| `pyproject.toml` | modificato | `[tool.ruff.lint.per-file-ignores]` aggiunge `"src/talos/persistence/models/**" = ["TC003"]` (vedi sezione How per motivazione) |
| `alembic.ini` | modificato | `[post_write_hooks]` corretto da `console_scripts/entrypoint` (sintassi sbagliata) a `exec/executable` (sintassi corretta Alembic 1.x) |

Quality gate locale verde: **25 test PASS**, mypy strict pulito su 8 source file, `alembic upgrade --sql` produce DDL coerente con Allegato A.

## Why

ADR-0015 prescrive 10 tabelle (Allegato A) ma il primo modello da introdurre è strategico: ogni tabella successiva (`vgp_results`, `cart_items`, `panchina_items`, `storico_ordini`, `listino_items`) ha una FK a `sessions(id)`. Avere `sessions` per primo permette di costruire i prossimi modelli senza dover refattorizzare le FK.

Decisione di non introdurre Postgres reale ora:
- Il Leader non ha ancora confermato Docker disponibile sulla macchina locale.
- ADR-0015 prescrive integration test (RLS, ruoli, audit_log) che richiedono Postgres + ruoli setup.
- Strategia: validare la **migration in offline mode** (`alembic upgrade --sql`). L'SQL output è confrontabile riga per riga con l'Allegato A → garanzia che il DDL futuro sarà identico a quello promesso dall'ADR. Quando arriverà Postgres in Docker, basterà `alembic upgrade head` (online) per applicare la stessa migration.

Beneficio operativo: ora `Base.metadata.tables["sessions"]` è popolato. Il prossimo CHG che aggiunge un modello concreto:
1. Crea `src/talos/persistence/models/<modello>.py`.
2. Aggiunge re-export in `models/__init__.py`.
3. Genera revision con `alembic revision --autogenerate -m "create <modello>"` (autogenerate funziona ora, perché `target_metadata` ha già `sessions`).
4. Verifica via `alembic upgrade --sql` che il DDL sia coerente.

## How

### Modello `AnalysisSession`

Nome classe `AnalysisSession`, nome tabella `sessions`. La discrepanza è voluta:
- `Session` è già usato da `sqlalchemy.orm.Session` (sessione DB);
- chiamare il modello `AnalysisSession` elimina ambiguità nei moduli che importano sia il model sia l'ORM session.

Tipi colonna aderenti all'Allegato A:

| Colonna | DDL Allegato A | SQLAlchemy 2.0 | server_default |
|---|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `BigInteger`, `primary_key=True`, `autoincrement=True` | (autoincrement) |
| `started_at` | `TIMESTAMPTZ DEFAULT NOW()` | `TIMESTAMP(timezone=True)`, `nullable=False` | `func.now()` |
| `ended_at` | `TIMESTAMPTZ` | `TIMESTAMP(timezone=True)`, `nullable=True` | — |
| `budget_eur` | `NUMERIC(12,2) NOT NULL` | `Numeric(12, 2)`, `nullable=False` | — |
| `velocity_target` | `INT DEFAULT 15` | `Integer`, `nullable=False` | `text("15")` |
| `listino_hash` | `CHAR(64) NOT NULL` | `CHAR(64)`, `nullable=False` | — |
| `tenant_id` | `BIGINT NOT NULL DEFAULT 1` | `BigInteger`, `nullable=False` | `text("1")` |

Validazione end-to-end: `alembic upgrade head --sql` produce esattamente il DDL Allegato A:

```sql
CREATE TABLE sessions (
    id BIGSERIAL NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    budget_eur NUMERIC(12, 2) NOT NULL,
    velocity_target INTEGER DEFAULT 15 NOT NULL,
    listino_hash CHAR(64) NOT NULL,
    tenant_id BIGINT DEFAULT 1 NOT NULL,
    PRIMARY KEY (id)
);
```

### Conflitto ruff `TC003` ↔ SQLAlchemy 2.0

SQLAlchemy 2.0 ORM valuta a runtime le annotazioni `Mapped[T]` per dedurre il tipo colonna (`de_stringify_annotation`). Spostare `datetime`/`Decimal` in `TYPE_CHECKING` block (come prescriverebbe `TC003`) farebbe fallire l'init con `MappedAnnotationError: Could not resolve all types within mapped annotation`.

Trade-off documentato in `pyproject.toml`:

```toml
[tool.ruff.lint.per-file-ignores]
"src/talos/persistence/models/**" = ["TC003"]
```

L'eccezione è limitata ai file model (uniche dipendenti da SQLAlchemy `Mapped[T]`). Tutti gli altri moduli del progetto continuano a soggiacere al pattern `TYPE_CHECKING`.

### Fix `alembic.ini` post-write hook

Il primo `alembic revision` di questo CHG ha emesso `FAILED: Could not find entrypoint console_scripts.ruff` perché la sintassi originale (`type = console_scripts`, `entrypoint = ruff`) era sbagliata: ruff non espone un Python entry point così. Sintassi corretta per Alembic 1.x:

```ini
ruff_format.type = exec
ruff_format.executable = ruff
ruff_format.options = format REVISION_SCRIPT_FILENAME
```

`type = exec` invoca un binario in PATH. Se `ruff` non c'è in PATH (es. fuori da `uv run`), il hook fallisce silenziosamente — accettabile perché è cosmetico (la migration funziona comunque).

### Test sul model (9)

`tests/unit/test_analysis_session_model.py` copre:
- Identità tabella (`__tablename__ == "sessions"`)
- Registrazione in `Base.metadata`
- Insieme esatto delle 7 colonne dell'Allegato A
- PK è `id BigInteger`
- `listino_hash CHAR(64) NOT NULL`
- `budget_eur NUMERIC(12,2) NOT NULL`
- `velocity_target` default `15`
- `tenant_id` default `1` (multi-tenant ready, MVP single-tenant)
- `ended_at` nullable, TIMESTAMP TZ
- Costruzione del modello con `Decimal` per `budget_eur` (verifica compatibilità tipi)

Tutti i test sono **runtime invariants** sul `Base.metadata.tables["sessions"]`: non richiedono engine connesso. Il primo test integration con Postgres reale verrà introdotto quando Docker sarà disponibile.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed (con `per-file-ignores` documentato) |
| Format | `uv run ruff format --check src/ tests/` | ✅ 16 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 8 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 25 passed in 0.23s |
| Migration offline | `uv run alembic upgrade head --sql` | ✅ DDL coerente con Allegato A |
| Pre-commit-app E2E | (verificato in commit reale dal hook governance) | atteso PASS |

Nuovi test (10): 1 modificato in `test_persistence_skeleton.py` (asserzione invertita) + 9 in `test_analysis_session_model.py`.

**Rischi residui:**
- `per-file-ignores` su `TC003` per i model: trade-off necessario fintanto che si usa SQLAlchemy 2.0 ORM con `Mapped[T]`. SQLAlchemy potrebbe in futuro evolversi per rendere TC003 compatibile (dummy import a livello modulo); rivedremo via errata ADR-0014 se serve.
- La migration revision id `9d9ebe778e40` è generato randomicamente da Alembic. È **immutabile** una volta committata: revisioni successive avranno `down_revision = "9d9ebe778e40"`. Modificare il filename romperebbe la chain.
- `tenant_id BIGINT DEFAULT 1` è MVP single-tenant. RLS sulle 3 tabelle prescritte (`storico_ordini`, `locked_in`, `config_overrides`) NON è in `sessions`: la `sessions` non ha RLS perché ogni sessione è di un solo tenant by-construction (la app la crea con `tenant_id=1`).
- L'autogenerate Alembic non è stato usato (`alembic revision -m "..."` senza `--autogenerate`). Per i modelli successivi proverò `--autogenerate`, ma la disciplina resta: revisione manuale obbligatoria del file generato (Allegato A è la fonte di verità, autogenerate è solo bootstrap).
- Test integration con Postgres reale (RLS, ruoli, audit) restano out-of-scope finché non c'è Docker disponibile. Continueranno ad arrivare in CHG dedicati.

## Refs

- ADR: ADR-0015 (Allegato A — schema), ADR-0014 (mypy strict + plugin SQLAlchemy + ruff per-file-ignore documentato), ADR-0013 (struttura `src/talos/persistence/models/`), ADR-0019 (test unit invarianti)
- Predecessore: CHG-2026-04-30-007 (persistence skeleton)
- Tag intermedio: `checkpoint/2026-04-30-01` (post CHG-007)
- Successore atteso: prossima tabella dell'Allegato A (probabilmente `asin_master` come lookup table indipendente, o `listino_items` con FK a `sessions`)
- Commit: `<pending>`
