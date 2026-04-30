# ADR Index — Mappa Neurale

Grafo relazionale di tutti gli ADR ratificati. Aggiornare **prima** della ratifica di ogni nuovo ADR.

> **Regola vincolante (ADR-0001):** Nessun ADR è considerato `Active` fino a quando non è referenziato in questo indice con tutte le colonne compilate.

---

## Registro

| ID | Titolo | Status | Categoria | Data | Dipende da | Governa |
|---|---|---|---|---|---|---|
| [ADR-0001](ADR-0001-meta-architettura-adr.md) | Meta-Architettura ADR | Active | meta | 2026-04-29 | — | Tutti gli ADR |
| [ADR-0002](ADR-0002-test-gate-commit.md) | Test Gate Protocol | Active | process | 2026-04-29 | ADR-0001 | Ogni commit di codice |
| [ADR-0003](ADR-0003-restore-point-github.md) | Restore Point Strategy | Active | process | 2026-04-29 | ADR-0001, ADR-0002 | Tag GitHub, CHANGELOG |
| [ADR-0004](ADR-0004-cross-reference-documentation.md) | Cross-Reference Documentation | Active¹ | process | 2026-04-29 | ADR-0001 | docs/changes/, CHANGELOG |
| [ADR-0005](ADR-0005-commit-message-convention.md) | Commit Message Convention | Active | process | 2026-04-29 | ADR-0001, ADR-0004 | Ogni commit message non-triviale |
| [ADR-0006](ADR-0006-git-hooks-enforcement.md) | Git Hooks Enforcement | Active | process | 2026-04-29 | ADR-0001, ADR-0002, ADR-0004, ADR-0005 | scripts/hooks/, enforcement meccanico |
| [ADR-0007](ADR-0007-gitnexus-integration.md) | GitNexus Planimetria Architetturale | Active | tooling | 2026-04-29 | ADR-0001, ADR-0004 | .gitnexus/, self-briefing step 4 |
| [ADR-0008](ADR-0008-anti-allucinazione.md) | Anti-Allucinazione Protocol | Active | process | 2026-04-29 | ADR-0001, ADR-0004, ADR-0007 | Ogni affermazione di Claude, docs/STATUS.md |
| [ADR-0009](ADR-0009-errata-corrige-hardening-patch.md) | Errata Corrige & Hardening Patch | Active | meta | 2026-04-29 | ADR-0001 | Modifica di ADR Active senza supersessione |
| [ADR-0010](ADR-0010-self-briefing-hardening.md) | Self-Briefing Hardening & STATUS Anchoring | Active | process | 2026-04-29 | ADR-0001, ADR-0004, ADR-0006, ADR-0008, ADR-0009 | Step 0 self-briefing, STATUS.md, sequenza re-briefing canonica |
| [ADR-0011](ADR-0011-operational-policies.md) | Operational Policies — Push, Branch, Test Validity | Active | process | 2026-04-29 | ADR-0002, ADR-0003, ADR-0006 | Push immediato, branch policy fase governance, test manuali documentati |
| [ADR-0012](ADR-0012-project-vision-capture.md) | Project Vision Capture & Distillation | Active | process | 2026-04-29 | ADR-0001, ADR-0008, ADR-0009, ADR-0010 | `PROJECT-RAW.md`, pipeline raw → ADR/ROADMAP, regola "lacune mai completate" |
| [ADR-0013](ADR-0013-project-structure.md) | Project Structure — src-layout + uv | Active | architecture | 2026-04-29 | ADR-0001, ADR-0014 | `src/`, `tests/`, `migrations/`, `pyproject.toml`, `uv.lock` |
| [ADR-0014](ADR-0014-stack-linguaggio-quality-gates.md) | Stack Linguaggio & Quality Gates | Active | architecture | 2026-04-29 | ADR-0001, ADR-0002, ADR-0006, ADR-0013 | Python 3.11, mypy strict, ruff strict, pytest, pre-commit-app |
| [ADR-0015](ADR-0015-stack-persistenza.md) | Stack Persistenza — PostgreSQL Zero-Trust + SQLAlchemy 2.0 | Active | architecture | 2026-04-29 | ADR-0001, ADR-0013, ADR-0014 | `migrations/`, `src/talos/persistence/`, schema DDL (Allegato A) |
| [ADR-0016](ADR-0016-stack-ui-streamlit.md) | Stack UI — Streamlit + Caching Strategy | Active | architecture | 2026-04-29 | ADR-0013, ADR-0014, ADR-0015, ADR-0017, ADR-0018 | `src/talos/ui/`, `.streamlit/config.toml` |
| [ADR-0017](ADR-0017-stack-acquisizione-dati.md) | Stack Acquisizione Dati — Keepa + Playwright + Tesseract | Active | architecture | 2026-04-29 | ADR-0013, ADR-0014, ADR-0015 | `src/talos/io_/`, `src/talos/extract/`, `selectors.yaml` |
| [ADR-0018](ADR-0018-algoritmo-vgp-tetris.md) | Algoritmo VGP & Tetris — implementazione vettoriale Numpy | Active | architecture | 2026-04-29 | ADR-0013, ADR-0014, ADR-0015 | `src/talos/vgp/`, `src/talos/tetris/`, `src/talos/formulas/` |
| [ADR-0019](ADR-0019-test-strategy-applicativa.md) | Test Strategy Applicativa — pytest + golden dataset | Active | process | 2026-04-29 | ADR-0001, ADR-0002, ADR-0006, ADR-0011, ADR-0014 | `tests/`, `pyproject.toml [tool.pytest]`, coverage gate |
| [ADR-0020](ADR-0020-cicd-github-actions.md) | CI/CD Pipeline — GitHub Actions | Active | process | 2026-04-29 | ADR-0002, ADR-0003, ADR-0006, ADR-0011, ADR-0014, ADR-0019 | `.github/workflows/`, branch protection, GitHub Secrets |
| [ADR-0021](ADR-0021-logging-telemetria.md) | Logging & Telemetria — structlog + R-01 enforcement | Active | architecture | 2026-04-29 | ADR-0008, ADR-0013, ADR-0014, ADR-0015, ADR-0017, ADR-0018, ADR-0019 | `src/talos/observability/`, catalogo eventi canonici |

¹ ADR-0004 mantiene status `Active` con **hardening patch** applicata da ADR-0010 sulla sezione "Flusso di Re-Briefing" (vedi ADR-0009 per il meccanismo, sezione `## Errata` di ADR-0004 per il dettaglio).

---

## Grafo delle Dipendenze

```
ADR-0001 [meta] — La Volontà
    ├── ADR-0002 [process] — Test Gate
    │       ├── ogni commit non-triviale
    │       ├── ← esteso da ADR-0011 (test manuali documentati per infrastruttura)
    │       └── ← enforcement: ADR-0006 (pre-commit)
    ├── ADR-0003 [process] — Restore Points
    │       ├── dipende da ADR-0002 (commit certificati)
    │       ├── ← esteso da ADR-0011 (push policy: tag pushato esplicitamente)
    │       ├── ← errata corrige in CHG-2026-04-29-002 (master → main)
    │       └── governa: tag GitHub, CHANGELOG
    ├── ADR-0004 [process] — Cross-Reference
    │       ├── governa: docs/changes/
    │       ├── governa: CHANGELOG.md
    │       ├── ← hardening patch da ADR-0010 (sezione "Flusso di Re-Briefing" obsoleta)
    │       └── ← enforcement: ADR-0006 (pre-commit)
    ├── ADR-0005 [process] — Commit Convention
    │       ├── dipende da ADR-0004 (CHG-ID references)
    │       └── ← enforcement: ADR-0006 (commit-msg)
    ├── ADR-0006 [process] — Git Hooks
    │       ├── enforce: ADR-0001 (struttura ADR + Test di Conformità)
    │       ├── enforce: ADR-0002 (change doc)
    │       ├── enforce: ADR-0004 (change doc)
    │       └── enforce: ADR-0005 (commit format + ADR-NNNN + CHG-ID esistente)
    ├── ADR-0007 [tooling] — GitNexus
    │       ├── dipende da ADR-0004 (context per briefing)
    │       └── governa: .gitnexus/, self-briefing step 4 ⚠ ISS-001
    ├── ADR-0008 [process] — Anti-Allucinazione
    │       ├── dipende da ADR-0004 (STATUS.md come change doc esteso)
    │       ├── ← esteso da ADR-0010 (anchoring obbligatorio + freshness header)
    │       ├── governa: docs/STATUS.md
    │       └── governa: ogni affermazione tecnica di Claude
    ├── ADR-0009 [meta] — Errata Corrige & Hardening Patch
    │       ├── dipende da ADR-0001 (regola di non-modifica retroattiva)
    │       ├── governa: meccanismo di errata su ADR Active
    │       └── governa: meccanismo di hardening patch su sezioni obsolete
    ├── ADR-0010 [process] — Self-Briefing Hardening
    │       ├── dipende da ADR-0006 (verifica core.hooksPath)
    │       ├── dipende da ADR-0008 (anchoring esteso)
    │       ├── dipende da ADR-0009 (meccanismo hardening patch su ADR-0004)
    │       ├── governa: Step 0 del Self-Briefing
    │       ├── governa: header freshness e anchoring di STATUS.md
    │       └── governa: sequenza canonica di re-briefing
    ├── ADR-0011 [process] — Operational Policies
    │       ├── dipende da ADR-0002 (test gate, esteso)
    │       ├── dipende da ADR-0003 (restore points, push integrato)
    │       ├── governa: push immediato post-commit
    │       ├── governa: branch policy fase governance (single-branch su main)
    │       └── governa: ammissibilità test manuali documentati
    ├── ADR-0012 [process] — Project Vision Capture
    │       ├── dipende da ADR-0001 (autorità architetturale)
    │       ├── dipende da ADR-0008 (anti-allucinazione, lacune mai completate)
    │       ├── dipende da ADR-0009 (errata corrige post-Frozen)
    │       ├── dipende da ADR-0010 (anchoring esteso al Q&A Log)
    │       ├── governa: PROJECT-RAW.md (root)
    │       └── governa: pipeline raw → proposta → validazione Leader → ADR/ROADMAP
    │
    │  ── Cluster ADR di Stack (0013–0021) — promulgati post-Frozen via step [6] ADR-0012 ──
    │
    ├── ADR-0013 [architecture] — Project Structure
    │       ├── dipende da ADR-0001 (meta), ADR-0014 (linguaggio)
    │       └── governa: `src/`, `tests/`, `migrations/`, `pyproject.toml`
    ├── ADR-0014 [architecture] — Stack Linguaggio & Quality Gates
    │       ├── dipende da ADR-0001, ADR-0002 (test gate), ADR-0006 (hooks), ADR-0013
    │       └── governa: Python 3.11, mypy strict, ruff strict, pytest
    ├── ADR-0015 [architecture] — Stack Persistenza
    │       ├── dipende da ADR-0001, ADR-0013, ADR-0014
    │       └── governa: PostgreSQL 16 + SQLAlchemy 2.0 sync + Alembic + RLS Zero-Trust
    ├── ADR-0016 [architecture] — Stack UI
    │       ├── dipende da ADR-0013, ADR-0014, ADR-0015, ADR-0017, ADR-0018
    │       └── governa: Streamlit + caching strategy + idempotency
    ├── ADR-0017 [architecture] — Stack Acquisizione Dati
    │       ├── dipende da ADR-0013, ADR-0014, ADR-0015
    │       └── governa: Keepa + Playwright + Tesseract + fallback chain (R-01)
    ├── ADR-0018 [architecture] — Algoritmo VGP & Tetris
    │       ├── dipende da ADR-0013, ADR-0014, ADR-0015
    │       └── governa: pipeline vettoriale Numpy + R-01..R-09
    ├── ADR-0019 [process] — Test Strategy Applicativa
    │       ├── dipende da ADR-0001, ADR-0002 (test gate), ADR-0006, ADR-0011, ADR-0014
    │       └── governa: pytest + golden dataset Samsung + coverage gate ≥85%
    ├── ADR-0020 [process] — CI/CD Pipeline
    │       ├── dipende da ADR-0002, ADR-0003, ADR-0006, ADR-0011, ADR-0014, ADR-0019
    │       └── governa: GitHub Actions + GitNexus reindex bot + branch protection
    └── ADR-0021 [architecture] — Logging & Telemetria
            ├── dipende da ADR-0008, ADR-0013, ADR-0014, ADR-0015, ADR-0017, ADR-0018, ADR-0019
            └── governa: structlog + catalogo eventi canonici + R-01 dinamico
```

---

## Aree di Codice Coperte

| Area / Componente | ADR di Riferimento | Note |
|---|---|---|
| Workflow commit | ADR-0002, ADR-0011 | Test gate obbligatorio; test manuali ammessi per governance |
| Commit message format | ADR-0005, ADR-0006 | CHG-ID + ADR-ID nel footer (entrambi verificati dal commit-msg hook) |
| Tag e release GitHub | ADR-0003, ADR-0011 | Checkpoint ogni 5 commit + push immediato dei tag |
| Push al remote | ADR-0011 | Immediato post-commit; eccezioni solo con autorizzazione esplicita |
| Branch | ADR-0011 | Single-branch su `main` in fase governance; v2 a introduzione codice |
| docs/changes/ | ADR-0004 | Change document per ogni modifica non-triviale |
| docs/decisions/ | ADR-0001, ADR-0009 | Governance ADR; meccanismo errata/hardening patch |
| docs/decisions/INDEX.md | ADR-0001 | Questa mappa — aggiornare prima di ogni ratifica |
| docs/decisions/FILE-ADR-MAP.md | ADR-0001 | Indice inverso file→ADR |
| CHANGELOG.md | ADR-0003, ADR-0004, ADR-0005 | Checkpoint + change summary con link CHG |
| ROADMAP.md | ADR-0001 | Aggiornato ad ogni nuova decisione architetturale |
| scripts/hooks/ | ADR-0006 | pre-commit + commit-msg (entrambi rafforzati in CHG-2026-04-29-002) |
| scripts/setup-hooks.sh | ADR-0006 | Eseguire post-clone — verifica enforced da ADR-0010 step 0 |
| .gitattributes | ADR-0006 | LF su hooks/markdown, vincolo per esecuzione hook su Windows |
| .gitnexus/ | ADR-0007 | Database knowledge graph ⚠ ISS-001 |
| docs/STATUS.md | ADR-0008, ADR-0010, ADR-0004 | Stato corrente — header freshness + claim ancorati obbligatori |
| CLAUDE.md | ADR-0001, ADR-0008, ADR-0010 | Rules of Engagement; Self-Briefing con Step 0 |
| PROJECT-RAW.md | ADR-0012 | Vision raw del progetto; stati Draft/Iterating/Frozen; lacune mai completate |
| `src/talos/` | ADR-0013 | Layout `src-layout`; 8 aree consentite (`io_`, `extract`, `vgp`, `tetris`, `persistence`, `ui`, `observability`, `config`) |
| `pyproject.toml`, `uv.lock` | ADR-0013, ADR-0014 | Tool packaging `uv`; Python 3.11; ruff + mypy + pytest config |
| `migrations/` | ADR-0015 | Alembic migrations; schema iniziale Allegato A di ADR-0015 |
| `src/talos/persistence/` | ADR-0015 | SQLAlchemy 2.0 sync + Imperative Mapping; ruoli Zero-Trust + RLS |
| `src/talos/ui/`, `.streamlit/config.toml` | ADR-0016 | Streamlit + multi-page + caching `@st.cache_data` |
| `src/talos/io_/`, `src/talos/extract/`, `selectors.yaml` | ADR-0017 | Keepa + Playwright + Tesseract; fallback chain R-01 |
| `src/talos/vgp/`, `src/talos/tetris/`, `src/talos/formulas/` | ADR-0018 | Pipeline vettoriale Numpy + R-01..R-09 |
| `tests/` | ADR-0019, ADR-0002, ADR-0011 | pytest + golden Samsung byte-exact + Hypothesis (limitato) + governance |
| `.github/workflows/` | ADR-0020, ADR-0006 | CI/CD GitHub Actions; GitNexus reindex bot post-merge |
| `src/talos/observability/` | ADR-0021, ADR-0008 | structlog + catalogo eventi canonici (R-01 dinamico) |

---

## Aree Senza Copertura ADR

> Le aree elencate qui non hanno ancora un ADR `Active`. Claude deve segnalare il gap prima di toccarle.

| Area | Gap | Prossima Azione |
|---|---|---|
| ~~Stack tecnologico~~ | Coperto da ADR-0014 + ADR-0015 + ADR-0016 + ADR-0017 + ADR-0018 + ADR-0021 (CHG-2026-04-30-001) | Chiuso |
| ~~CI/CD~~ | Coperto da ADR-0020 (CHG-2026-04-30-001) | Chiuso |
| ~~Struttura directory codice applicativo~~ | Coperto da ADR-0013 (CHG-2026-04-30-001) | Chiuso |
| ~~Test strategy applicativa~~ | Coperto da ADR-0019 (CHG-2026-04-30-001) | Chiuso |
| ~~Logging & telemetria~~ | Coperto da ADR-0021 (CHG-2026-04-30-001) | Chiuso |
| Branch policy v2 (multi-branch / PR) | Rinviata da ADR-0011 + ADR-0020 (single-push MVP) | Da rivedere all'introduzione di multi-developer |

---

## Issues Aperte

| ID | Descrizione | Workaround | ADR | Priorità |
|---|---|---|---|---|
| ISS-001 | `gitnexus analyze` segfault / exit code 5 su Node v24; architettura macchina Leader incompatibile | GitNexus usato in seguito da PC operativo; self-briefing step 4 degrada con dichiarazione esplicita | ADR-0007 | Rinviata (decisione Leader 2026-04-29) |
| ISS-002 | Stack tecnologico non ancora definito | Il Leader fornirà le prime istruzioni | — | Bloccante per fase codice |

---

## Legenda Status

| Status | Significato |
|---|---|
| `Active` | In vigore, vincolante per Claude e il Leader |
| `Active¹` | Active con hardening patch su sezione/i specifica/e (vedi sezione `## Errata` dell'ADR) |
| `Proposed` | In discussione, non ancora vincolante |
| `Deprecated` | Non più in vigore, mantenuto per storia |
| `Superseded` | Sostituito — vedere campo `superseded_by` nell'ADR |
