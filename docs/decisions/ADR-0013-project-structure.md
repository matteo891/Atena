---
id: ADR-0013
title: Project Structure — src-layout + uv
date: 2026-04-29
status: Active
deciders: Leader
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

Con la vision TALOS in stato `Frozen` (ADR-0012), inizia la fase di codice applicativo. Serve una struttura di directory non ambigua che (a) separi codice sorgente da test e da artefatti di build, (b) impedisca import "magici" dalla root durante i test (errore frequente con flat layout), (c) sia compatibile con i tool packaging Python moderni e (d) renda il progetto installabile come pacchetto.

In assenza di un ADR di struttura, ogni futuro modulo (pre-MVP e post-MVP) rischia di rifondare convenzioni divergenti, vanificando la disciplina governance.

## Decisione

### Layout Python: `src-layout`

```
Atena/
├── src/
│   └── talos/
│       ├── __init__.py
│       ├── io_/                  # input/output: ingestion listini (xlsx, csv, pdf, docx, img)
│       ├── extract/              # SamsungExtractor + interface BrandExtractor
│       ├── vgp/                  # VGP Score: normalize, score, veto
│       ├── tetris/               # allocator + panchina
│       ├── persistence/          # SQLAlchemy models + repository
│       ├── ui/                   # Streamlit dashboard
│       ├── observability/        # logging strutturato + metriche (ADR-0021)
│       └── config/               # pydantic settings + override layer
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/                   # fixture Samsung byte-exact
│   ├── governance/               # grep R-01 + invarianti governance
│   └── conftest.py
├── migrations/                   # Alembic migrations (ADR-0015)
├── docs/                         # esistente — governance
├── scripts/                      # esistente — hooks + utility
├── .github/workflows/            # ADR-0020
├── pyproject.toml
├── uv.lock
├── README.md                     # operativo (non documentazione utente)
└── CLAUDE.md, PROJECT-RAW.md, ROADMAP.md, CHANGELOG.md  # esistenti
```

**Vincolo:** il package `talos` è importabile solo se installato (`uv pip install -e .` in dev). I test importano sempre `from talos.vgp.score import ...`, mai `from src.talos...` né con manipolazione `sys.path`.

### Tool packaging: `uv`

`uv` (Astral) come gestore unico di:
- Python toolchain (`uv python install 3.11`)
- ambienti virtuali (`uv venv`)
- dipendenze (`uv pip install`, `uv sync`)
- lock file riproducibile (`uv.lock` versionato)
- esecuzione script (`uv run pytest`, `uv run ruff check`)

`pyproject.toml` come unico file di configurazione (PEP 621 metadata + `[tool.uv]` + `[tool.ruff]` + `[tool.mypy]` + `[tool.pytest.ini_options]`).

### Naming module

- Snake_case per moduli e funzioni.
- PascalCase per classi.
- Underscore trailing per evitare collisioni con built-in (`io_` invece di `io`).

## Conseguenze

**Positive:**
- Test puliti: `uv run pytest` non ha bisogno di `PYTHONPATH` né di hack.
- Riproducibilità: `uv sync` ricostruisce ambiente identico in CI/locale.
- Editor-friendly: VSCode/PyCharm riconoscono `src/` come source root via `pyproject.toml`.

**Negative / costi:**
- Ogni dev deve installare `uv` (script di setup `scripts/setup-dev.sh` lo automatizza).
- Doppia profondità (`src/talos/`) leggermente più verbosa nella navigazione.
- Migrazione da flat → src-layout in futuro è non-banale: la decisione qui è **definitiva** per evitare rework.

**Effetti collaterali noti:**
- L'ADR governa anche `scripts/setup-dev.sh` (da creare in fase di bootstrap codice — task ROADMAP).
- Ogni nuovo modulo applicativo deve essere collocato in `src/talos/<area>/`. Aggiungere area = aggiornare FILE-ADR-MAP.md.

## Test di Conformità

1. **Verifica strutturale (CI ADR-0020):** workflow `ci.yml` esegue `find src/talos -type d` e fallisce se trova directory fuori dalle 8 aree consentite (`io_`, `extract`, `vgp`, `tetris`, `persistence`, `ui`, `observability`, `config`).
2. **Verifica importabilità:** `uv run python -c "import talos"` senza error.
3. **Verifica src-layout enforcement:** test `tests/governance/test_no_root_imports.py` fallisce se trova `from src.` o manipolazioni di `sys.path` nel codice sorgente o nei test.
4. **Verifica `uv.lock` versionato:** pre-commit hook (estensione futura di ADR-0006) blocca commit di `pyproject.toml` senza `uv.lock` aggiornato.
5. **Verifica gap-ADR su nuove directory:** se `src/talos/<nuova_area>/` non è registrata in FILE-ADR-MAP.md, CI fallisce.

## Cross-References

- ADR correlati: ADR-0001 (meta), ADR-0014 (stack linguaggio), ADR-0015 (persistenza), ADR-0016 (UI), ADR-0017 (acquisizione), ADR-0018 (algoritmo), ADR-0019 (test), ADR-0020 (CI/CD), ADR-0021 (logging)
- Governa: `src/`, `tests/`, `migrations/`, `pyproject.toml`, `uv.lock`, `scripts/setup-dev.sh` (futuro)
- Impatta: ogni nuovo modulo applicativo, ogni workflow CI/CD
- Test: `tests/governance/test_no_root_imports.py` (da creare); job `ci.yml` step "structure-check"
- Commits: `<pending>`

## Rollback

Per superseduta da nuovo ADR: passi concreti
1. Promulgare ADR-NNNN (es. `Project Structure v2 — flat layout`) come `Active` con `supersedes: ADR-0013`.
2. Aggiornare `pyproject.toml` rimuovendo configurazione `src` come source root.
3. Spostare `src/talos/` → `talos/` con `git mv`.
4. Aggiornare tutti gli import nei test (rimossa indirezione).
5. Aggiornare CI workflow: rimuovere step "structure-check" o adattarlo.
6. ADR-0013 status → `Superseded`, campo `superseded_by: ADR-NNNN` compilato.
