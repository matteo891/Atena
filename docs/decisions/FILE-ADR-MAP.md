# File-to-ADR Map — Indice Inverso

Navigazione inversa: da un file qualsiasi al suo ADR di riferimento.

> **Regola (ADR-0001):** Aggiornare questa mappa ogni volta che si aggiunge un nuovo componente o un nuovo ADR copre un file esistente. La colonna "ADR Primario" indica il vincolo architetturale principale; la colonna "ADR Secondari" indica i protocolli operativi che si applicano.

**Come usarla:**
- Stai per toccare un file? Cerca qui il suo ADR e leggilo prima.
- Non trovi il file? → Gap ADR. Segnala al Leader prima di procedere (CLAUDE.md — Gap ADR).

---

## Governance e Infrastruttura Documentale

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `CLAUDE.md` | ADR-0001 | ADR-0008, ADR-0010 (Step 0 + sequenza re-briefing) | Rules of Engagement; modificare solo con ADR di supporto |
| `PROJECT-RAW.md` | ADR-0012 | ADR-0008 (lacune), ADR-0009 (errata post-Frozen) | Vision raw; modifica diretta solo in stato Draft/Iterating; post-Frozen via Errata Corrige |
| `ROADMAP.md` | ADR-0001 | ADR-0012 (popolato da scomposizione validata del Frozen) | Aggiornare ad ogni ADR ratificato; task da Frozen popolano i meta-blocchi futuri |
| `CHANGELOG.md` | ADR-0003, ADR-0004 | ADR-0005 | Checkpoint log + change summary con link CHG |
| `docs/STATUS.md` | ADR-0008 | ADR-0004, ADR-0010 (header freshness + anchoring) | Fonte di verità sullo stato corrente; aggiornare a fine sessione con modifiche |
| `docs/decisions/ADR-*.md` | ADR-0001 | ADR-0009 (errata corrige + hardening patch) | Ogni ADR segue TEMPLATE.md; vedi INDEX.md |
| `docs/decisions/INDEX.md` | ADR-0001 | — | Aggiornare prima della ratifica di ogni nuovo ADR |
| `docs/decisions/FILE-ADR-MAP.md` | ADR-0001 | — | Questo file; aggiornare ad ogni nuovo componente |
| `docs/decisions/TEMPLATE.md` | ADR-0001 | — | Template ADR; modificare solo con nuovo ADR meta |
| `docs/changes/*.md` | ADR-0004 | ADR-0005 | Change documents; un file per modifica non-triviale |
| `docs/changes/TEMPLATE.md` | ADR-0004 | — | Template change doc; non è un change document reale |

## Git e CI/CD

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `scripts/hooks/pre-commit` | ADR-0006 | ADR-0001, ADR-0002, ADR-0004 | Enforcement meccanico change doc + struttura ADR (incl. Test di Conformità) |
| `scripts/hooks/commit-msg` | ADR-0006 | ADR-0005 | Enforcement meccanico commit convention (CHG-ID + ADR-NNNN + classifier staging) |
| `scripts/setup-hooks.sh` | ADR-0006 | ADR-0010 (verifica via Step 0) | Eseguire dopo ogni clone |
| `.gitnexus/` | ADR-0007 | — | Database GitNexus; non modificare manualmente; runtime locale escluso da `.gitignore` |
| `.gitattributes` | ADR-0006 | — | Forza LF su hooks e markdown; vincolo di esecuzione hook su Windows |
| `.gitignore` | — | — | Esclude artefatti runtime locali (es. `.gitnexus/`); modifiche solo via change document |
| `AGENTS.md` | ADR-0007 | — | Gemello multi-agent del blocco GitNexus presente in CLAUDE.md (Cursor/Cline/Aider) |
| `.claude/skills/gitnexus/` | ADR-0007 | — | Skill condivise per uso operativo di GitNexus tramite Claude Code |

## Push, Branch, Tag

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| Branch `main` | ADR-0011 | ADR-0003 | Single-branch in fase governance; force push proibito senza autorizzazione |
| Tag `checkpoint/*`, `milestone/*` | ADR-0003 | ADR-0011 (push immediato) | Immutabili; pushati esplicitamente al remote |
| Remote `origin` | ADR-0011 | ADR-0003 | Push immediato post-commit certificato |

## Codice Applicativo

> ADR di stack 0013–0021 promulgati il 2026-04-30 (CHG-2026-04-30-001). I path elencati sono **vincolanti** anche se la directory non esiste ancora: il primo file sotto un path coperto deve rispettare l'ADR Primario.

### Layout & Packaging

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `src/talos/` | ADR-0013 | — | src-layout; 8 aree consentite |
| `src/talos/__init__.py` | ADR-0013 | ADR-0021 (bootstrap logging) | Inizializza package + structlog |
| `tests/` | ADR-0019 | ADR-0002, ADR-0011 | unit / integration / golden / governance |
| `tests/integration/` | ADR-0019 | ADR-0015 (RLS + audit), ADR-0011 (test gate) | DB reale via env var `TALOS_DB_URL`; skip module-level se assente — CHG-2026-04-30-019 |
| `migrations/` | ADR-0015 | — | Alembic; initial migration = Allegato A di ADR-0015 |
| `pyproject.toml` | ADR-0013, ADR-0014 | — | uv + ruff + mypy + pytest config |
| `uv.lock` | ADR-0013, ADR-0014 | — | Versionato; aggiornato con `uv sync` |
| `scripts/setup-dev.sh` | ADR-0013 | — | Bootstrap ambiente dev (futuro) |
| `scripts/db_bootstrap.py` | ADR-0015 | ADR-0014 | Bootstrap ruoli + GRANT/REVOKE + FORCE RLS Zero-Trust (idempotente) — CHG-2026-04-30-021 |

### Moduli Applicativi (`src/talos/<area>/`)

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `src/talos/io_/` | ADR-0017 | ADR-0013, ADR-0021 (logging mismatch) | Keepa client, scraper, OCR |
| `src/talos/io_/keepa_client.py` | ADR-0017 | ADR-0021 | Wrapper isolato libreria community `keepa` |
| `src/talos/io_/scraper.py` | ADR-0017 | ADR-0021 | Playwright + selectors.yaml + cadence umana |
| `src/talos/io_/ocr.py` | ADR-0017 | ADR-0021 | pytesseract + soglia 70 + status AMBIGUO |
| `src/talos/extract/` | ADR-0017 | ADR-0013 | SamsungExtractor + interface BrandExtractor |
| `src/talos/vgp/` | ADR-0018 | ADR-0013, ADR-0019 (golden+hypothesis), ADR-0021 | normalize, score, veto |
| `src/talos/tetris/` | ADR-0018 | ADR-0013, ADR-0019, ADR-0021 | allocator, panchina (R-04..R-09) |
| `src/talos/formulas/` | ADR-0018 | ADR-0019 | F1..F5 + fee_fba (L11b verbatim) |
| `src/talos/persistence/` | ADR-0015 | ADR-0013, ADR-0019 | SQLAlchemy 2.0 + RLS bootstrap |
| `src/talos/persistence/engine.py` | ADR-0015 | ADR-0014 | Factory `create_app_engine` (env var `TALOS_DB_URL`) — CHG-2026-04-30-020 |
| `src/talos/persistence/session.py` | ADR-0015 | ADR-0014 | `make_session_factory` + `session_scope` + `with_tenant` (Zero-Trust SET LOCAL) — CHG-2026-04-30-020 |
| `src/talos/ui/` | ADR-0016 | ADR-0013, ADR-0015 (RLS), ADR-0019 | Streamlit dashboard + pages + components |
| `src/talos/ui/dashboard.py` | ADR-0016 | — | Entrypoint Streamlit |
| `src/talos/observability/` | ADR-0021 | ADR-0008, ADR-0019 (test catalogo) | structlog config + catalogo eventi |
| `src/talos/config/` | ADR-0013 | ADR-0014 | pydantic-settings + override layer |
| `selectors.yaml` | ADR-0017 | — | Configurazione vivente Amazon scraping |
| `.streamlit/config.toml` | ADR-0016 | — | Theme dark default |

### Configurazione & Asset

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `tests/golden/samsung_1000.json` | ADR-0019 | — | Golden dataset sintetico validato dal Leader |
| `tests/golden/samsung_1000_expected.json` | ADR-0019 | — | Output VGP+Cart+Panchina atteso (byte-exact) |
| `tests/golden/html/` | ADR-0017, ADR-0019 | — | HTML statici Amazon per scraping test |
| `tests/golden/images/` | ADR-0017, ADR-0019 | — | Immagini canoniche per OCR test |

### CI/CD

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `.github/workflows/ci.yml` | ADR-0020 | ADR-0014, ADR-0019 | Lint + type + test + governance + structure |
| `.github/workflows/gitnexus.yml` | ADR-0020 | ADR-0007 | Reindex post-merge bot |
| `.github/workflows/release.yml` | ADR-0020 | ADR-0003 | Release tag manuale |
| `.github/workflows/hooks-check.yml` | ADR-0020 | ADR-0006 | Verifica integrità hook governance |
| `scripts/hooks/pre-commit-app` | ADR-0014 | ADR-0006 (governance hook caller) | Pre-commit applicativo (lint+type+unit) |
| `scripts/backup-postgres.sh` | ADR-0015 | — | pg_dump schedulato + retention 7gg |

---

## Gap Noti (Aree Senza Copertura ADR)

| Area | Gap | Azione Richiesta |
|---|---|---|
| ~~Stack tecnologico~~ | Chiuso da ADR-0014/0015/0016/0017/0018/0021 (CHG-2026-04-30-001) | — |
| ~~CI/CD pipeline~~ | Chiuso da ADR-0020 (CHG-2026-04-30-001) | — |
| ~~Struttura directory del codice~~ | Chiuso da ADR-0013 (CHG-2026-04-30-001) | — |
| Branch policy v2 (multi-branch / PR) | Rinviata da ADR-0011 + ADR-0020 (MVP single-push) | Rivedere all'introduzione di multi-developer |
| Cloud backup (post-MVP) | Out-of-scope MVP per ADR-0015 | Promulgare ADR successivo se serve resilienza off-site |
| Metriche / OpenTelemetry | Out-of-scope MVP per ADR-0021 | Promulgare ADR successivo post-MVP |
