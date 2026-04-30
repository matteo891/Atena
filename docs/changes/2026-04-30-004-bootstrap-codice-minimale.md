---
id: CHG-2026-04-30-004
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Pending Leader approval
commit: <pending>
adr_ref: ADR-0013, ADR-0014, ADR-0019, ADR-0021, ADR-0006
---

## What

**Primo commit di codice applicativo del progetto.** Bootstrap minimale che concretizza i path vincolanti di `src-layout` (ADR-0013) e attiva i quality gate (ADR-0014). Nessuna funzionalità di prodotto ancora — solo l'ossatura installabile e testabile.

| File | ADR Primario | Cosa contiene |
|---|---|---|
| `pyproject.toml` | ADR-0013, ADR-0014 | Metadata progetto (Python 3.11–3.12, version 0.1.0); `[dependency-groups] dev` con ruff/mypy/pytest/hypothesis; `[tool.ruff] select=ALL` con ignore commentati; `[tool.mypy] strict=true`; `[tool.pytest]` con marker (unit/integration/golden/governance/slow) |
| `uv.lock` | ADR-0013 | Lock riproducibile generato da `uv sync --all-groups` (Python 3.11.15, ruff 0.15.12, mypy 1.x, pytest 9.x, hypothesis, pytest-cov) |
| `src/talos/__init__.py` | ADR-0013 | Docstring del progetto + `__version__ = "0.1.0"` |
| `src/talos/observability/__init__.py` | ADR-0021 | Stub modulo (placeholder, configure_logging arriverà in CHG dedicato) |
| `tests/conftest.py` | ADR-0019 | Skeleton (vuoto a oggi; le fixture cross-test arriveranno con i moduli) |
| `tests/unit/test_smoke.py` | ADR-0019 | 2 test unit: `test_talos_importable`, `test_talos_version_exposed` |
| `tests/governance/test_no_root_imports.py` | ADR-0019 + ADR-0013 | Test governance: vieta `from src.` / `import src.` in `src/` e `tests/` |
| `scripts/hooks/pre-commit-app` | ADR-0014 (gancio da ADR-0006 errata CHG-003) | Hook applicativo: `ruff check` → `ruff format --check` → `mypy src/` → `pytest unit + governance -m "not slow"`. Exit non-zero blocca il commit |
| `scripts/setup-dev.sh` | ADR-0013 | Setup idempotente post-clone: install uv → install Python 3.11 → uv sync → setup-hooks |
| `README.md` | — (operativo) | Setup, struttura, workflow, comandi rapidi. Documentazione utente CFO esplicitamente fuori scope (ROADMAP) |
| `.gitignore` (esteso) | — (operativo) | Aggiunte le esclusioni standard Python: `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage*`, `htmlcov/` |

**Stato:** working tree pronto + tutti i quality gate verdi locali (vedi sezione Tests). **Commit subordinato a permesso esplicito Leader (Test Gate ADR-0002).**

## Why

ADR-0013/0014/0019/0021 sono stati ratificati il 2026-04-30 (CHG-001). Senza un primo commit applicativo:
- I path vincolanti (`src/talos/`, `tests/{unit,governance}/`) restano astratti — nessun futuro CI o test può ancorarsi a uno scheletro inesistente.
- Il `pre-commit-app` (ADR-0014, integrato dal pre-commit governance via CHG-003) non ha nulla da invocare.
- L'asticella di disciplina viene rinviata: scrivere il primo modulo di sostanza richiede un quality gate **già funzionante**, non da assemblare contestualmente.

Il bootstrap è **minimale di proposito**:
- **Zero dipendenze runtime** in `[project].dependencies`. SQLAlchemy, Streamlit, Keepa, Playwright, Tesseract, structlog, pandas, numpy verranno aggiunti **modulo per modulo** in CHG dedicati — ognuno con il proprio ADR di riferimento (0015/0016/0017/0018/0021), il proprio test passante, il proprio change document. Questo evita un `pyproject.toml` "tutto e niente" senza modulo che lo motivi.
- **Solo dev tools** (ruff/mypy/pytest/hypothesis/pytest-cov) in `[dependency-groups].dev`. Sono i requisiti minimi per far girare il quality gate.
- **2 unit test + 1 governance test**. Sufficienti a certificare che (a) il package è installato e importabile, (b) la disciplina src-layout (ADR-0013) è enforced come test eseguibile.

## How

### Setup riproducibile (per chiunque cloni)

```bash
bash scripts/setup-dev.sh
```

Esegue: `uv` install (se assente) → `uv python install 3.11` → `uv sync --all-groups` → `setup-hooks.sh`.

### Decisioni puntuali di config (con motivazione)

- **`requires-python = ">=3.11,<3.13"`** — coerente con ADR-0014; permette anche Python 3.12 (la macchina del Leader ha 3.12.3 di sistema, l'ambiente uv usa 3.11.15).
- **`build-system = "hatchling"`** — backend di build standard PEP 517; nessun vincolo da ADR-0013/0014, scelta operativa per `uv build`.
- **`[dependency-groups] dev`** — formato moderno (PEP 735, supportato da uv) preferito a `[project.optional-dependencies]` perché esclude i dev tool dalla wheel finale.
- **`ruff select = ["ALL"]`** + 7 ignore commentati: D (docstring → ROADMAP), ANN (duplica mypy), COM812/ISC001 (conflitto con formatter), FIX/TD003 (TODO MVP-friendly), CPY001 (no copyright header per progetto interno).
- **`per-file-ignores` per `tests/**`**: S101 (assert), INP001 (no `__init__.py`), PLR2004 (magic numbers).
- **`mypy strict = true`** + flag aggiuntivi (warn_unreachable, warn_redundant_casts). Plugin `sqlalchemy[mypy]` **non** attivato ora — entrerà con il primo modulo `persistence/` (ADR-0015).
- **`coverage [tool.coverage]`** definita ma `fail_under` **non** settata sul `[tool.coverage.report]` per ora: in bootstrap il progetto è sotto 85% per costruzione (codice di prodotto inesistente). Quando arriverà il primo modulo di sostanza, alziamo la soglia a 85%/90% come da ADR-0019.

### Test governance (test_no_root_imports)

Implementa concretamente uno dei "Test di Conformità" di ADR-0013 (`tests/governance/test_no_root_imports.py`). Scansiona `src/` e `tests/`, fallisce se trova `from src.` o `import src.` in qualunque file `.py`. Coerente con la promessa src-layout: un import "magico" dalla root rompe la disciplina di pacchetto installato.

### Pre-commit applicativo

`scripts/hooks/pre-commit-app` — invocato dal `pre-commit` di governance (ADR-0006 errata CHG-003) **solo** quando in staging ci sono `*.py`/`pyproject.toml`/`uv.lock`. Esegue ruff check + ruff format check + mypy + pytest (unit + governance, escluso slow). Diagnostica esplicita su exit non-zero.

`scripts/setup-dev.sh` — wrapper idempotente che il README espone come singolo comando di onboarding.

### File esclusi dal commit

`.gitignore` esteso in questo CHG con le esclusioni standard Python (mancavano fino a oggi perché non c'era codice Python):

```
__pycache__/, *.py[cod], *$py.class, *.egg-info/, build/, dist/
.venv/
.pytest_cache/, .ruff_cache/, .mypy_cache/
.coverage, .coverage.*, htmlcov/, coverage.xml
```

Resta intatta l'esclusione precedente: `.claude/settings.local.json` (CHG-002) e `.gitnexus/` (CHG-002).

## Tests

Test automatici eseguiti localmente prima del report al Leader (Test Gate ADR-0002). Tutti **PASS**.

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 5 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 2 source files |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ 3 passed in 0.44s |
| Pre-commit-app E2E | `bash scripts/hooks/pre-commit-app` | ✅ "Pre-commit applicativo: PASS" |
| Hook syntax | `bash -n scripts/hooks/pre-commit-app && bash -n scripts/setup-dev.sh` | ✅ |

Test manuali documentati (ADR-0011) — verifiche strutturali integrative:

| Test | Verifica | Esito |
|---|---|---|
| Layout src-layout | `find src/talos -type d` corrisponde alle aree consentite | ✅ `src/talos/` + `src/talos/observability/` |
| Importabilità | `uv run python -c "import talos; print(talos.__version__)"` | ✅ `0.1.0` |
| `pyproject.toml` valido TOML | parsing implicito da `uv sync` | ✅ |
| `uv.lock` versionato | `test -f uv.lock && head -3 uv.lock` | ✅ |
| Hook applicativo eseguibile | `test -x scripts/hooks/pre-commit-app` | ✅ |
| Hook governance invoca app | `grep "scripts/hooks/pre-commit-app" scripts/hooks/pre-commit` | ✅ (CHG-003) |

**Copertura attuale:** 0% sui moduli `src/talos` (è un'ossatura — `__init__.py` solo). Sotto la soglia ADR-0019 ≥ 85% per costruzione: il bootstrap **non** può rispettare quella soglia (non c'è nulla di sostanza da coprire). Soglia attivata su CI con `--cov-fail-under=85` quando arriverà il primo modulo applicativo.

**Rischi residui:**
- `uv.lock` versionato (~310 righe) può creare conflitti di merge in futuro multi-developer; soluzione standard è risolvere con `uv sync --upgrade`. Non bloccante in fase MVP single-developer.
- Plugin `sqlalchemy[mypy]` non attivato ora; entrerà con CHG `persistence/` (ADR-0015). Ricordare in quel momento di aggiungere il plugin a `[tool.mypy].plugins`.
- `[tool.coverage.report]` non ha `fail_under` ora: i CI runner che invocheranno `pytest --cov --cov-fail-under=85` lo forzeranno comunque dall'invocazione (ADR-0020 `ci.yml`). Decisione esplicita: il quality gate locale di sviluppo non blocca su coverage finché il progetto è in bootstrap.
- ruff config: la lista degli `ignore` (D, ANN, COM812, ISC001, FIX, TD003, CPY001) è motivata ma rivedibile. Errata Corrige di ADR-0014 ammessa se uno di questi diventa bloccante o, viceversa, se vogliamo riattivarli.

## Refs

- ADR: ADR-0013 (struttura), ADR-0014 (linguaggio + quality gates), ADR-0019 (test strategy), ADR-0021 (observability stub), ADR-0006 (hook governance — gancio applicativo via errata CHG-003)
- Predecessore: CHG-2026-04-30-003 (Errata Corrige ADR-0006 — hooks v2)
- Successore atteso: CHG dedicato al primo modulo di sostanza (probabilmente `persistence/` per partire dal "fondo" → ADR-0015 + plugin mypy)
- Commit: `<pending — in attesa permesso Leader>`
- Issue: HARD-STOP risolto (CHG-003); fase codice attiva
