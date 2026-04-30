---
id: ADR-0014
title: Stack Linguaggio & Quality Gates
date: 2026-04-29
status: Active
deciders: Leader
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

`PROJECT-RAW.md` sez. 6.1 fissa "Python 3.10+, architettura modulare". L20 (Round 2) ha ratificato pytest + ruff strict + mypy/pyright strict + lint zero warning. L16 (Round 5) ha completato lo stack con SQLAlchemy 2.0 sync + Alembic + Playwright + Tesseract.

Tutto il paniere Quality Gate è ratificato a livello di **vision**. Manca l'incisione formale: versione esatta del linguaggio, type checker scelto fra mypy e pyright, configurazione esatta di ogni tool, integrazione con il workflow `pre-commit` esistente di governance.

Senza questo ADR, i tool si applicano "a buon senso" e divergono nei mesi.

## Decisione

### Versione Python

**Python 3.11** come minimo richiesto (`requires-python = ">=3.11,<3.13"` in `pyproject.toml`).

Razionale: prestazioni 10–60% superiori a 3.10 su workload tipici (CPython faster), `Self` type built-in, `ExceptionGroup` per gestione errori in chain, `tomllib` stdlib. Nessun vincolo legacy ci forza alla 3.10. Esclusa 3.13 dal supporto MVP per stabilizzazione ecosistema (libreria `keepa` e plugin SQLAlchemy mypy).

### Type Checker

**mypy `--strict`** (non pyright).

Razionale: maturità del plugin `sqlalchemy[mypy]` (colonne tipate inferite correttamente), ecosistema più ampio, integrazione editor stabile. Pyright sarebbe leggermente più veloce ma il differenziale è trascurabile per progetto MVP.

Configurazione `[tool.mypy]` in `pyproject.toml`:
- `strict = true`
- `plugins = ["sqlalchemy.ext.mypy.plugin"]`
- `warn_unreachable = true`
- `enable_error_code = ["redundant-self", "redundant-expr", "truthy-bool"]`
- `exclude = ["tests/golden/.*\\.json"]` (fixture statiche)

### Linter & Formatter

**ruff** strict come unico tool (replace black + isort + flake8 + pyupgrade + parte di pylint, lock-step con `ruff format`).

Configurazione `[tool.ruff]`:
- `target-version = "py311"`
- `line-length = 100` (no 79: leggibilità su laptop moderni)
- `[tool.ruff.lint] select = ["ALL"]` con `ignore` minimo argomentato (vedi commenti in `pyproject.toml`)
- `[tool.ruff.lint.per-file-ignores]` per `tests/` (consente `assert`, `print` debug)

### Test Runner

**pytest** + plugin: `pytest-cov` (coverage), `pytest-xdist` (parallel), `hypothesis` (property-based, limitato a `vgp/normalize.py` e `vgp/score.py` per ADR-0019).

### Pre-commit hook applicativo

Aggiungere `scripts/hooks/pre-commit-app` (separato da `pre-commit` di governance esistente) che esegue:
1. `uv run ruff check src/ tests/` → fail se warning
2. `uv run ruff format --check src/ tests/` → fail se formato deviato
3. `uv run mypy src/` → fail se errore type
4. `uv run pytest tests/unit/` → fail se test rosso (solo unit, non integration)

Il governance `pre-commit` esistente (ADR-0006) chiama il nuovo applicativo come step finale **solo se** in staging ci sono file Python (`*.py` o `pyproject.toml`).

### Versioning

SemVer manuale (decisione esplicita Leader). `version = "0.1.0"` come bootstrap MVP.

## Conseguenze

**Positive:**
- Tool unico (ruff) replace 4-5 tool: meno dipendenze, meno conflitti versione, più veloce.
- mypy strict + SQLAlchemy plugin: errori di tipo su query DB intercettati a compile-time.
- Pre-commit applicativo: regressioni triviali (formato, type) bloccate prima del commit.

**Negative / costi:**
- mypy strict ha curva ripida iniziale; primi moduli richiederanno annotazioni complete (no `Any` impliciti).
- `ruff "ALL"` produce inizialmente molti warning; richiede `ignore` ben argomentati per ogni regola disabilitata.
- Setup dev più lungo (1-2 minuti) per `uv sync` + scaricamento Python 3.11 al primo run.

**Effetti collaterali noti:**
- ADR-0006 (governance hooks) verrà aggiornato via Errata Corrige per integrare la chiamata al pre-commit-app: questa modifica è sotto-dichiarata qui ed entrerà in vigore alla prima introduzione di codice Python.
- Future librerie devono essere compatibili con Python 3.11; libreria che richiede 3.10 max → blocker.

## Test di Conformità

1. **CI `ci.yml` step `lint`:** `uv run ruff check . && uv run ruff format --check .` → fail se output ≠ 0.
2. **CI `ci.yml` step `typecheck`:** `uv run mypy src/` → fail se errore.
3. **CI `ci.yml` step `test`:** `uv run pytest --cov=src/talos --cov-fail-under=85 tests/unit tests/integration tests/golden` → fail se coverage < 85% sui core (vgp, tetris, extract).
4. **Verifica versione Python:** `uv run python --version` deve essere `3.11.x`. CI ha `actions/setup-python` con `python-version: '3.11'`.
5. **Pre-commit applicativo:** `bash scripts/hooks/pre-commit-app` fallisce su un file con `def f(x): pass` (manca tipo).

## Cross-References

- ADR correlati: ADR-0001, ADR-0002 (test gate), ADR-0006 (governance hooks), ADR-0013 (struttura), ADR-0019 (test strategy), ADR-0020 (CI/CD)
- Governa: `pyproject.toml`, `uv.lock`, `scripts/hooks/pre-commit-app` (futuro), `.github/workflows/ci.yml`
- Impatta: ogni file `*.py` del progetto
- Test: CI workflow `ci.yml` job `quality-gates`
- Commits: `<pending>`

## Rollback

Se mypy strict si rivela insostenibile in fase di sviluppo:
1. Promulgare ADR-NNNN come Errata Corrige di ADR-0014: passare a `mypy` non-strict con elenco esplicito di flag mantenuti (`disallow_untyped_defs = true`, `warn_redundant_casts = true`, etc.).
2. Aggiornare `pyproject.toml` `[tool.mypy]`.
3. CI step `typecheck` aggiorna invocazione.

Se ruff "ALL" si rivela troppo invasivo:
1. Errata Corrige: passare a `select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "PT", "SIM", "TCH"]` (subset focalizzato).
2. Aggiornare `pyproject.toml` `[tool.ruff.lint]`.
3. Documentare regole disabilitate con motivazione.
