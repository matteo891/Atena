---
id: CHG-2026-04-30-007
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 088b410
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Persistence skeleton** — primo passo verso ADR-0015. Aggiunge SQLAlchemy 2.0 + Alembic + psycopg come dipendenze runtime, attiva il plugin `sqlalchemy[mypy]` di ADR-0014, introduce `src/talos/persistence/Base` (`DeclarativeBase` SQLAlchemy 2.0) e la struttura `migrations/` minima di Alembic. **Niente modelli concreti, niente DDL, niente Postgres reale.** Step di preparazione: i modelli concreti (`sessions`, `asin_master`, ecc.) e la migration con DDL Allegato A entreranno in CHG dedicati.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/__init__.py` | nuovo | Re-export di `Base` |
| `src/talos/persistence/base.py` | nuovo | `class Base(DeclarativeBase)` — radice di tutti i futuri ORM model |
| `alembic.ini` | nuovo | Config alembic in root: `script_location = migrations`, `prepend_sys_path = .`, post-write hook `ruff_format` per allineare le revision al quality gate, sezioni logger standard. URL placeholder (sostituita a runtime da `TALOS_DB_URL`) |
| `migrations/env.py` | nuovo | Override `sqlalchemy.url` da env `TALOS_DB_URL`; `target_metadata = Base.metadata`; supporto online + offline mode (`alembic upgrade --sql`) |
| `migrations/script.py.mako` | nuovo | Template revision (PEP 604 `str \| None`, `from __future__ import annotations`, import `sa` puliti, conformi a ruff/mypy) |
| `migrations/versions/.gitkeep` | nuovo | Placeholder per directory vuota (le revisioni reali arrivano col primo modello) |
| `tests/unit/test_persistence_skeleton.py` | nuovo | 3 test: `Base` è `DeclarativeBase` subclass; `Base.metadata` è `MetaData`; nessun model registrato (atteso allo skeleton — diventerà `≥ 1` col primo CHG di modello concreto) |
| `pyproject.toml` | modificato | `[project].dependencies` ora include `sqlalchemy[mypy]>=2.0.30,<2.1`, `alembic>=1.13.0,<2`, `psycopg[binary]>=3.2.0,<4`. `[tool.mypy].plugins = ["sqlalchemy.ext.mypy.plugin"]` attivato |
| `uv.lock` | modificato | Lockate: sqlalchemy 2.0.49, alembic 1.18.4, psycopg 3.3.3, psycopg-binary 3.3.3, greenlet, mako, markupsafe |

Quality gate locale verde: 15 test PASS, mypy strict pulito su 6 source file.

## Why

ADR-0015 prescrive PostgreSQL Zero-Trust + SQLAlchemy 2.0 sync + Alembic + RLS + audit_log + 10 tabelle dell'Allegato A. Implementare tutto in un unico CHG è grosso e fragile: serve Postgres in Docker, plugin mypy non testato, env var, RLS, ruoli. Spezzare in **skeleton + N modelli incrementali** rispetta la cadenza CHG-piccoli-e-verdi che abbiamo finora.

Beneficio dello skeleton:
1. **Plugin mypy attivo da subito.** Quando il prossimo CHG aggiungerà un modello concreto, mypy è già configurato per riconoscere `Mapped[T]` e `mapped_column(...)`. Errori di tipo intercettati al primo colpo.
2. **Alembic configurato e parsabile.** `alembic --raiseerr heads` esce 0; `alembic revision --autogenerate -m "..."` è pronto a generare la prima migration appena un modello eredita da `Base`.
3. **Disciplina di esclusione.** `migrations/env.py` legge la URL da `TALOS_DB_URL` come prescritto da ADR-0015 (niente secret hard-coded). `alembic.ini` usa placeholder `CHANGE_ME` per render visibile l'esclusione.
4. **`Base.metadata` come "fonte di verità tabelle"** — `target_metadata = Base.metadata` in `env.py` chiude il loop: ogni modello che eredita da `Base` viene autodiscoverato dall'autogenerate.

Out-of-scope dichiarato (in CHG futuri):
- Modelli concreti dell'Allegato A (10 tabelle).
- Initial migration con DDL completo.
- Ruoli (`talos_admin`/`talos_app`/`talos_audit`) + `GRANT` + `REVOKE` (richiede DB Superuser, va via Alembic operations o script SQL bootstrap).
- Policy RLS sulle 3 tabelle prescritte.
- Trigger audit_log.
- Test integration con Postgres in Docker.

## How

### Decisioni puntuali

- **`alembic.ini` in root** (non in `migrations/`) — convenzione standard `alembic init`, supportata dai tool ecosystema (`pyrightconfig`, IDE). `script_location = migrations` punta alla directory.
- **URL placeholder `CHANGE_ME`** in `alembic.ini` invece di un valore vuoto — rende esplicito che la URL **deve** essere sovrascritta da `TALOS_DB_URL`. Se qualcuno esegue `alembic` senza env var, fallisce a connect time con un errore chiaro (non silenziosamente).
- **`prepend_sys_path = .`** in `alembic.ini` — necessario per importare `talos.persistence.base` da `migrations/env.py`.
- **`post_write_hooks` con `ruff_format`** — ogni `alembic revision` viene riformattata automaticamente per essere conforme al quality gate (ADR-0014). Disciplina già al primo modello.
- **`migrations/script.py.mako` riscritto** rispetto al template default di Alembic — usa `from __future__ import annotations`, type hints PEP 604, signature pulite. Compatibile mypy strict + ruff `select=ALL`.
- **`migrations/versions/.gitkeep`** — la directory vuota deve esistere nel repo perché alembic la richiede al runtime.
- **`mypy src/`** non scansiona `migrations/`: env.py è un file Python "standalone" eseguito da Alembic. Sufficiente per ora; eventualmente in futuro si aggiunge un test che esegue `python -c "import migrations.env"` con env var dummy.
- **`ruff check src/ tests/`** anch'esso non tocca `migrations/`. Idem motivazione.
- **`Base.metadata` vuoto agli skeleton** — `test_base_metadata_no_tables_yet` blocca regressioni: se qualcuno importa accidentalmente un modello che registra una tabella, il test fallisce. Quando arriverà il primo modello concreto (CHG `sessions/asin_master`), il test verrà aggiornato a `assert len(...) >= 1`.

### Verifica funzionale

`alembic --raiseerr heads` esegue offline (legge solo la directory `migrations/`, non si connette al DB). Exit 0 → config valido. Output vuoto → 0 revisioni (atteso allo skeleton).

## Tests

Test automatici (Test Gate ADR-0002).

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 13 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 6 source files (plugin sqlalchemy[mypy] attivo) |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 15 passed in 0.40s |
| Alembic config valido | `uv run alembic --raiseerr heads` | ✅ exit 0, output vuoto (atteso) |
| Pre-commit-app E2E | (verificato in commit reale dal hook governance) | atteso PASS |

Dettaglio nuovi test (3): `test_base_subclasses_declarative_base`, `test_base_has_metadata`, `test_base_metadata_no_tables_yet`. Sommato ai 12 di CHG-006 → 15.

**Rischi residui:**
- `psycopg[binary]>=3.2.0,<4` su sistemi senza libpq potrebbe richiedere build da source (raro su Linux). uv lo gestisce. In CI Linux runners hanno libpq sempre.
- Plugin `sqlalchemy[mypy]` deprecato in SQLAlchemy 2.0+ (la docs ufficiale raccomanda di migrare a typed columns native + `Mapped[]`). Il plugin è ancora **funzionante** e necessario per casi avanzati (es. `relationship` con typing). Quando i modelli concreti useranno solo `Mapped[T]` standard, valutiamo errata di rimozione plugin (Errata Corrige di ADR-0014).
- `migrations/env.py` non è coperto da ruff/mypy ora. Trade-off accettato; rivedibile se diventa rilevante (CHG futuro).
- Il template `migrations/script.py.mako` usa `${...}` Mako: ruff/mypy non lo capirebbero. Volutamente fuori scope.
- Quando arriverà il primo modello concreto, andrà aggiornato `test_base_metadata_no_tables_yet` (oggi `len == 0`, futuro `len >= 1`). Disciplina: il CHG che aggiunge il modello aggiorna anche questo test.

## Refs

- ADR: ADR-0015 (decisione cardine — qui solo skeleton, modelli e DDL in CHG futuri), ADR-0014 (plugin mypy attivato), ADR-0013 (struttura `src/talos/persistence/` + `migrations/`), ADR-0019 (test unit)
- Predecessore: CHG-2026-04-30-006 (`observability/configure_logging`)
- Successore atteso: primo modello concreto (es. `sessions` o `asin_master`) + Alembic revision iniziale + eventuale Postgres in Docker per integration test
- Commit: `088b410`
