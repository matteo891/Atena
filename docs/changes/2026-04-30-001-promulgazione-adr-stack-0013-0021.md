---
id: CHG-2026-04-30-001
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 8cd06f7
adr_ref: ADR-0012, ADR-0013, ADR-0014, ADR-0015, ADR-0016, ADR-0017, ADR-0018, ADR-0019, ADR-0020, ADR-0021
---

## What

Promulgazione formale del **cluster di ADR di stack 0013–0021** (9 ADR: 7 architettura + 2 process), che chiude lo step [6] di ADR-0012 (scomposizione della vision `Frozen` in ADR di stack vincolanti).

| ADR | Titolo | Categoria | Cosa decide |
|---|---|---|---|
| ADR-0013 | Project Structure — src-layout + uv | architecture | Layout `src/talos/` (8 aree), `tests/`, `migrations/`, packaging via `uv` con `uv.lock` versionato |
| ADR-0014 | Stack Linguaggio & Quality Gates | architecture | Python **3.11**, mypy `--strict` (non pyright) + plugin SQLAlchemy, ruff `select=ALL` strict, pytest, pre-commit applicativo separato |
| ADR-0015 | Stack Persistenza | architecture | PostgreSQL 16 + SQLAlchemy 2.0 **sync** + Alembic + Zero-Trust (3 ruoli + RLS) + audit_log + pg_dump retention 7gg. **Schema DDL incluso come Allegato A** (10 tabelle) |
| ADR-0016 | Stack UI | architecture | Streamlit + multi-page + caching (`@st.cache_data ttl=600` su Keepa) + bottone "Forza Aggiornamento" + idempotency su side-effect + dark mode |
| ADR-0017 | Stack Acquisizione Dati | architecture | Keepa (libreria community wrapped) + Playwright sync + Tesseract; fallback chain con R-01 a ogni livello; rate limit hard configurabile; soglia OCR 70 default; **PA-API 5 escluso da MVP** |
| ADR-0018 | Algoritmo VGP & Tetris | architecture | Moduli `vgp/`, `tetris/`, `formulas/`; **pandas** + Numpy vettoriale; errore esplicito su edge case Fee_FBA L11b; greedy con Priorità=∞ per locked-in |
| ADR-0019 | Test Strategy Applicativa | process | pytest + marker (unit/integration/golden/governance/slow); golden Samsung 1000 righe **sintetico validato dal Leader**; coverage ≥90% core / ≥85% totale; **Hypothesis limitato a `vgp/normalize.py` + `vgp/score.py`** |
| ADR-0020 | CI/CD Pipeline | process | GitHub Actions (4 workflow); **single-push diretto + CI gate** (no PR mandatory MVP); GitNexus reindex bot post-merge; GitHub Secrets |
| ADR-0021 | Logging & Telemetria | architecture | structlog JSON + catalogo eventi canonici (10 eventi); R-01 enforcement statico + dinamico; rotazione 10MB×7 |

Tutti `Active` da 2026-04-29 (data di redazione = data di validazione bulk del Leader; promulgati formalmente 2026-04-30 con questo CHG).

## Why

ADR-0012 step [6]: la vision TALOS `Frozen` (CHG-2026-04-29-009) ha sbloccato la scomposizione in ADR di stack. La sessione precedente (interrotta) aveva esposto al Leader una proposta di scomposizione **in chat** (8 ADR + decisioni trasversali), ricevendo validazione bulk **Opzione A** con override puntuali per ogni ADR.

**Decisioni Leader incise (override su default Claude):**

| Ambito | Default Claude | Decisione Leader | ADR |
|---|---|---|---|
| Layout | flat o src-layout | **src-layout** | 0013 |
| Tool packaging | uv vs Poetry | **uv** | 0013 |
| Python version | 3.10+ vs 3.11 | **3.11** | 0014 |
| Type checker | mypy vs pyright | **mypy** | 0014 |
| Schema DB | Allegato A vs ADR-0015b | **Allegato A inline** | 0015 |
| Backup | nessuno vs pg_dump+retention | **pg_dump 7gg** | 0015 |
| TTL Keepa | 10 min hard | **10 min + bottone "Forza Aggiornamento"** | 0016 |
| Theme UI | custom vs default | **default + dark mode** | 0016 |
| Rate limit Keepa | hardcoded vs config | **hard limit in config (chiamate/minuto)** | 0017 |
| Soglia OCR | fixed vs config | **70 default + esposto in config** | 0017 |
| PA-API 5 | valutare in MVP | **escluso dall'MVP** | 0017 |
| DataFrame | pandas vs polars | **pandas** | 0018 |
| Edge case Fee_FBA | None/skip vs raise | **errore esplicito (R-01)** | 0018 |
| Golden dataset | sintetico vs reale anonimizzato | **sintetico validato dal Leader** | 0019 |
| Hypothesis scope | dappertutto vs limitato | **solo `vgp/normalize.py` + `vgp/score.py`** | 0019 |
| Branch protection | PR mandatory vs single-push | **single-push + CI gate** | 0020 |
| GitNexus reindex | manuale vs bot | **bot automatizzato post-merge** | 0020 |
| Secrets | GitHub Secrets confermato | confermato | 0020 |
| Logging | sub-ADR 0014 vs ADR dedicato | **ADR-0021 dedicato** | 0021 |
| Versioning | manuale vs auto | **manuale per MVP** | (trasversale) |
| Multi-brand | ADR vs task ROADMAP | **task ROADMAP post-MVP** | (trasversale) |
| Documentazione | ADR vs ROADMAP | **task ROADMAP** | (trasversale) |

Conseguenze immediate:
- **Chiusura ISS-002** (stack tecnologico non promulgato).
- **Chiusura ESP-007** (proposta scomposizione → ADR di stack).
- **Sblocco fase codice** — tutti i path `src/talos/<area>/`, `tests/`, `migrations/`, `.github/workflows/` hanno ora ADR Primario + Secondari mappati in FILE-ADR-MAP.md.
- **HARD STOP** richiesto esplicitamente dal Leader: post-CHG-002 e post-tag, niente cartelle, niente prima riga di codice. Il Leader procede al clone di `Atena-Core` nello stato di purezza infrastrutturale.

## How

### File creati (untracked → tracked)

- `docs/decisions/ADR-0013-project-structure.md`
- `docs/decisions/ADR-0014-stack-linguaggio-quality-gates.md`
- `docs/decisions/ADR-0015-stack-persistenza.md`
- `docs/decisions/ADR-0016-stack-ui-streamlit.md`
- `docs/decisions/ADR-0017-stack-acquisizione-dati.md`
- `docs/decisions/ADR-0018-algoritmo-vgp-tetris.md`
- `docs/decisions/ADR-0019-test-strategy-applicativa.md`
- `docs/decisions/ADR-0020-cicd-github-actions.md`
- `docs/decisions/ADR-0021-logging-telemetria.md`
- `docs/changes/2026-04-30-001-promulgazione-adr-stack-0013-0021.md` (questo CHG)

Ogni ADR rispetta il template di ADR-0001:
- Frontmatter (`id`, `title`, `date`, `status: Active`, `deciders: Leader`, `category`, `supersedes`, `superseded_by`)
- Sezioni: `## Contesto`, `## Decisione`, `## Conseguenze`, `## Test di Conformità`, `## Cross-References`, `## Rollback`
- Campo `Commits: <pending>` da backfillare post-commit
- Test di Conformità eseguibili (descritti come step CI o test pytest specifici)

### Aggiornamenti ai documenti governance

- `docs/decisions/INDEX.md`:
  - 9 nuove righe nel registro tabellare
  - 9 nuovi nodi nel grafo dipendenze (con commento separatore "Cluster ADR di Stack")
  - "Aree di Codice Coperte" estesa con i path `src/talos/<area>/`, `tests/`, `migrations/`, `.github/workflows/`, `pyproject.toml`/`uv.lock`
  - "Aree Senza Copertura ADR" aggiornata: gap di stack/CI-CD/struttura/test/logging tutti chiusi
- `docs/decisions/FILE-ADR-MAP.md`:
  - Nuova sezione "Codice Applicativo" con sotto-sezioni: Layout & Packaging / Moduli Applicativi / Configurazione & Asset / CI/CD
  - Path con ADR Primario + Secondari per ogni area
  - "Gap Noti" aggiornati
- `docs/STATUS.md`:
  - Header `Ultimo aggiornamento` aggiornato (commit hash da backfillare)
  - "Stato in Una Riga": stack hardened, repo in stato di purezza infrastrutturale
  - "Appena Completato": riga CHG-2026-04-30-001 aggiunta
  - "In Sospeso": ESP-007 chiusa, ISS-002 chiusa, HARD-STOP attivo
  - "Prossima Azione": HARD STOP esplicito + procedura di rientro
  - "Nota al Prossimo Claude": HARD STOP, regole su path consentiti per moduli applicativi
- `ROADMAP.md`:
  - Obiettivo #8 marcato Completato
  - #10 (clone Atena-Core) e #11 (bootstrap primo modulo) aggiunti
  - Meta-blocchi A/B/C chiusi; D/E/F aggiornati; G (cloud backup), H (metriche), I (multi-brand), J (docs utente) nuovi post-MVP
  - Log validazioni: nuova riga 2026-04-30 con sintesi del cluster
- `CHANGELOG.md`:
  - Nuova versione `[0.9.0]` in cima — bumpa minor (non patch) perché segna sblocco fase codice

## Tests

Test manuali documentati (governance — ADR-0011). Codice applicativo non ancora introdotto, quindi non si applica il Test Gate automatico ADR-0002.

| Test | Comando / Verifica | Esito atteso |
|---|---|---|
| ADR-0013 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0013-project-structure.md` | PASS |
| ADR-0014 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0014-stack-linguaggio-quality-gates.md` | PASS |
| ADR-0015 file presente + status Active + Allegato A | `grep '^status: Active' docs/decisions/ADR-0015-stack-persistenza.md && grep '## Allegato A' docs/decisions/ADR-0015-stack-persistenza.md` | PASS |
| ADR-0016 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0016-stack-ui-streamlit.md` | PASS |
| ADR-0017 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0017-stack-acquisizione-dati.md` | PASS |
| ADR-0018 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0018-algoritmo-vgp-tetris.md` | PASS |
| ADR-0019 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0019-test-strategy-applicativa.md` | PASS |
| ADR-0020 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0020-cicd-github-actions.md` | PASS |
| ADR-0021 file presente + status Active | `grep '^status: Active' docs/decisions/ADR-0021-logging-telemetria.md` | PASS |
| Sezioni obbligatorie su tutti i 9 ADR | `for f in docs/decisions/ADR-001[3-9]*.md docs/decisions/ADR-002[01]*.md; do for s in '## Contesto' '## Decisione' '## Conseguenze' '## Test di Conformità' '## Cross-References' '## Rollback'; do grep -q "^$s" "$f" \|\| echo "MISSING: $s in $f"; done; done` | nessun MISSING |
| INDEX.md sync (ogni ADR-001[3-9] e -002[01] referenziato) | `for n in 0013 0014 0015 0016 0017 0018 0019 0020 0021; do grep -q "ADR-$n" docs/decisions/INDEX.md \|\| echo "MISSING $n"; done` | nessun MISSING |
| FILE-ADR-MAP.md sezione "Codice Applicativo" | `grep -A1 'Codice Applicativo' docs/decisions/FILE-ADR-MAP.md \| grep 'src/talos\|migrations\|tests'` | PASS |
| STATUS.md header `Ultimo aggiornamento` aggiornato | `head -10 docs/STATUS.md \| grep '2026-04-30'` | PASS |
| STATUS.md HARD-STOP presente | `grep 'HARD-STOP\|HARD STOP' docs/STATUS.md` | PASS |
| ROADMAP.md obiettivo #8 Completato | `grep -F '\| 8 \|' ROADMAP.md \| grep 'Completato'` | PASS |
| ROADMAP.md log validazione 2026-04-30 | `grep '2026-04-30' ROADMAP.md` | PASS |
| CHANGELOG.md `[0.9.0]` presente | `grep '\[0.9.0\]' CHANGELOG.md` | PASS |
| Pre-commit hook simulato (sezioni ADR + INDEX sync) | `bash scripts/hooks/pre-commit` con file in staging | PASS |
| Commit-msg hook simulato (CHG-ID + ADR-NNNN nel footer) | `bash scripts/hooks/commit-msg` su messaggio test | PASS |

**Copertura:** verifica strutturale completa (presenza file + status + sezioni obbligatorie + sync INDEX/MAP). Validità tecnica delle scelte di stack (es. correttezza schema DDL, idoneità soglia OCR 70, robustezza fallback chain) sarà testata in fase implementativa, sotto il rispettivo ADR.

**Rischi residui:**
- Schema Allegato A di ADR-0015 è "vincolante ma raffinabile": indici secondari, partizionamento `audit_log`, eventuale versionamento ASIN potranno richiedere Errata Corrige in fase implementativa. Documentato esplicitamente nell'ADR.
- ADR-0006 (governance hooks) ha **side-decision sotto-dichiarata** in ADR-0014 e ADR-0020:
  - ADR-0014 prevede `pre-commit-app` separato chiamato dal `pre-commit` di governance (estensione futura)
  - ADR-0020 prevede esenzione dal `commit-msg` per i commit del bot `github-actions[bot]` con `[skip ci]`
  - Entrambe le modifiche entreranno in vigore tramite **Errata Corrige di ADR-0006** alla prima introduzione di codice CI/applicativo. Documentato.
- Il golden dataset Samsung (1000 righe sintetiche) è il prossimo asset da costruire (1-2 giorni del Leader): è il prerequisito per i test golden byte-exact (R-01).
- HARD STOP attivo post-tag: nessun bootstrap di codice fino a riapertura esplicita.

## Refs

- ADR: ADR-0012 (step [6] completato), ADR-0013, ADR-0014, ADR-0015, ADR-0016, ADR-0017, ADR-0018, ADR-0019, ADR-0020, ADR-0021
- Predecessore: CHG-2026-04-29-009 (Frozen vision)
- Successore: CHG-2026-04-30-002 (tooling GitNexus + tag milestone)
- Commit: `8cd06f7`
- Issue: ESP-007 (chiusa con questo CHG), ISS-002 (chiusa con questo CHG), HARD-STOP (attivata)
