---
id: ADR-0020
title: CI/CD Pipeline — GitHub Actions
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
errata:
  - date: 2026-04-30
    chg: CHG-2026-04-30-003
    summary: "Aggiornato il riferimento al bypass commit-msg per il bot reindex: l'esenzione [skip ci] + author github-actions[bot] è ora wired nel commit-msg hook via Errata Corrige di ADR-0006 (CHG-2026-04-30-003), non più 'side-decision sotto-dichiarata'."
  - date: 2026-04-30
    chg: CHG-2026-04-30-005
    summary: "Documentazione del rollout progressivo dei 4 workflow: ci.yml introdotto ora con solo i job quality-gates + structure-check + governance-checks; il job 'tests' (postgres + tesseract + playwright + coverage-gate ≥85%) entrerà in vigore alla prima introduzione del modulo che lo richiede; gitnexus.yml/release.yml/hooks-check.yml rinviati a CHG dedicati."
---

## Contesto

Meta-blocco C di ROADMAP.md (CI/CD pipeline) era da definire post-Frozen. La governance attuale ha `pre-commit` + `commit-msg` di governance (ADR-0006) ma nessun CI server-side. Senza CI:
- chi ha hooks attivi rispetta i protocolli, chi non li ha può bypassare;
- i test integration (Postgres + Playwright + Tesseract) non vengono mai eseguiti automaticamente prima del merge;
- la disciplina golden test rischia di diventare opzionale.

Inoltre il Leader ha richiesto:
- branch protection MVP: single-push diretto su `main` + CI come gate (no PR mandatory)
- GitNexus reindex automatizzato post-merge (la mappa del codice sempre fresca)
- segreti su GitHub Secrets

Manca: scelta della piattaforma CI, decomposizione dei workflow, gestione concurrency, strategia di release tagging.

## Decisione

### Piattaforma: GitHub Actions

`.github/workflows/` come unica fonte di automazione CI/CD.

Razionale: repository già su GitHub (`matteo891/Atena`), zero costo per repo public, integrazione native con Secrets, runner `ubuntu-latest` con Docker pre-installato.

### Workflow 1: `ci.yml` — push e PR

**Trigger:** `push` (qualsiasi branch) e `pull_request` (target `main`).

**Job `quality-gates`** (sempre):
1. `actions/checkout@v4`
2. `astral-sh/setup-uv@v4` con `python-version: 3.11`
3. `uv sync --frozen`
4. `uv run ruff check src/ tests/`
5. `uv run ruff format --check src/ tests/`
6. `uv run mypy src/`

**Job `tests`** (depends-on `quality-gates`):
1. Service container: `postgres:16-alpine` con env vars per DB di test
2. Install Tesseract: `apt install -y tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng`
3. `uv run playwright install --with-deps chromium`
4. `uv run pytest --cov=src/talos --cov-fail-under=85 -m "not slow"`
5. Upload coverage report come artifact

**Job `governance-checks`** (parallel a `tests`):
1. `bash scripts/hooks/pre-commit` simulato sul HEAD (verifica che hook governance approverebbe il commit)
2. `pytest tests/governance/`
3. Verifica `core.hooksPath` settato (warning, non blocker)

**Job `structure-check`** (parallel):
1. Verifica layout `src/talos/<area>/` allineato ad ADR-0013 (8 aree consentite)
2. Verifica ogni ADR file referenziato in INDEX.md

**Risultato:** tutti i job verdi → mergeable. Failure → block.

### Workflow 2: `gitnexus.yml` — reindex post-merge

**Trigger:** `push` su `main` (solo dopo merge).

**Job `reindex`:**
1. `actions/checkout@v4` con `fetch-depth: 0`
2. `actions/setup-node@v4` con `node-version: 20`
3. `npx gitnexus analyze`
4. `git config user.email "github-actions[bot]@users.noreply.github.com"`
5. `git config user.name "github-actions[bot]"`
6. Se `.gitnexus/` ha cambiamenti:
   - `git add .gitnexus/`
   - `git commit -m "chore(gitnexus): reindex post-merge [skip ci]"` (no CHG-ID, no ADR-NNNN — exempt come hook governance)
   - `git push origin main`

**Concurrency:** `concurrency.group: gitnexus-reindex; cancel-in-progress: true` per evitare reindex multipli simultanei.

**Note:** il commit del bot è **esente dal commit-msg hook governance** (footer non applicabile). Hook governance va aggiornato via Errata Corrige per riconoscere `[skip ci]` come exempt.

### Workflow 3: `release.yml` — release tag manuale

**Trigger:** `workflow_dispatch` (manuale dal tab Actions).

**Input:** `version` (es. `0.2.0`).

**Job `release`:**
1. Verifica che `pyproject.toml` `version` matchi input.
2. Crea milestone tag annotato: `git tag -a milestone/v${version} -m "..."`.
3. Push tag: `git push origin milestone/v${version}`.
4. Crea GitHub Release con auto-generate notes da commit log dall'ultimo tag.

### Workflow 4: `hooks-check.yml` — verifica hook governance

**Trigger:** `push` (qualsiasi).

**Job `hook-integrity`:**
1. Verifica che `scripts/hooks/pre-commit` e `commit-msg` non siano modificati senza CHG (ricorsione: usa stesso pre-commit per validare se stesso).
2. Esegue `bash scripts/hooks/pre-commit` simulato sul HEAD.
3. Esegue `bash scripts/hooks/commit-msg .git/COMMIT_EDITMSG_FAKE` con il commit message del HEAD.

**Razionale:** previene drift tra l'hook locale e il comportamento atteso CI.

### Branch protection MVP (single-push)

Decisione Leader: **non** richiede PR. Push diretto su `main` ammesso.

CI però è **gate obbligatorio**:
- `Settings → Branches → main → Branch protection rule`:
  - Status checks: `quality-gates`, `tests`, `governance-checks`, `structure-check` required.
  - "Require branches to be up to date before merging": **off** (è single-push, non c'è merge).
  - Force push su main: **proibito** (allinea con ADR-0011).

Quando si introdurrà multi-branch (ADR futuro, post-MVP), questa regola viene aggiornata via Errata Corrige.

### Concurrency

Ogni workflow ha:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Evita CI duplicati su push rapidi.

### Caching

- `uv` cache: `actions/cache@v4` su `~/.cache/uv` con key `uv-${{ hashFiles('uv.lock') }}`.
- Playwright cache: `~/.cache/ms-playwright`.
- Tesseract: pacchetti apt cached via `awalsh128/cache-apt-pkgs-action`.

### Secrets

- `KEEPA_API_KEY` — uso in test integration Keepa con cassette + in produzione.
- `GITHUB_TOKEN` — auto-fornito da GitHub Actions; usato per `release.yml` e `gitnexus.yml`.
- `POSTGRES_PASSWORD_TEST` — per service container Postgres in CI.

Storage: **GitHub Secrets** a livello repo (decisione Leader confermata).

### Notifiche

In MVP: **none**. CI failure visibile su GitHub UI; il Leader monitora manualmente.
Post-MVP (ADR futuro): possibile integrazione Telegram/email su failure.

## Conseguenze

**Positive:**
- Quality gate uniforme: ogni push (anche di chi non ha hook locali) viene validato.
- GitNexus sempre fresco: la mappa di codice non drifta dal sorgente.
- Release riproducibili via tag annotato + auto-notes.
- Single-push diretto preserva la velocità di sviluppo dell'MVP single-developer.

**Negative / costi:**
- CI run ~5-7 minuti per push (lint + type + test integration + Playwright).
- GitHub Actions free tier: 2000 min/mese su repo public è ampio. Su privato eventualmente upgrade.
- Reindex GitNexus aggiunge commit "rumore" sul main (mitigato da `[skip ci]`).

**Effetti collaterali noti:**
- Hook governance (ADR-0006) **è stato aggiornato via Errata Corrige in CHG-2026-04-30-003**:
  - `commit-msg` riconosce `[skip ci]` + author email `github-actions[bot]@users.noreply.github.com` come bypass cumulativo (entrambe le condizioni richieste; commit umani con `[skip ci]` non sono esentati).
  - Nessun cambio per `pre-commit`: il workflow di reindex GitNexus modifica solo `.gitnexus/` (escluso da `.gitignore` ma includibile via `git add -f`); il classifier di pre-commit considera la dir come "triviale" e non richiede change document.

## Test di Conformità

1. **CI workflow validation:** `actionlint .github/workflows/*.yml` deve passare (no syntax errors). Eseguito come step di `governance-checks`.
2. **Branch protection:** verificato manualmente da Leader; non automatizzato in CI.
3. **GitNexus reindex idempotenza:** se `.gitnexus/` non cambia, il workflow non crea commit duplicati.
4. **Release tag format:** `release.yml` rifiuta input `version` non SemVer.
5. **Required checks attivi:** verifica periodica (mensile) che le 4 status check siano in `Settings → Branches`.

## Cross-References

- ADR correlati: ADR-0001, ADR-0002 (test gate), ADR-0003 (tag GitHub), ADR-0006 (hook governance, errata futura), ADR-0011 (branch policy), ADR-0014 (stack), ADR-0019 (test strategy)
- Governa: `.github/workflows/`, branch protection rules, GitHub Secrets
- Impatta: ogni push; release; freshness GitNexus
- Test: i workflow stessi (failure CI = test failure)
- Commits: `<pending>`

## Rollback

Se GitHub Actions diventa inadeguato (es. limiti free tier raggiunti, esigenza self-hosted):
1. Promulgare ADR-NNNN con `supersedes: ADR-0020`.
2. Migrare a self-hosted runner o GitLab CI / Forgejo Actions.
3. I workflow `.yml` sono parzialmente portabili (sintassi GitHub Actions).

Se branch protection MVP si rivela troppo permissiva (regressioni accidentali):
1. Errata Corrige: introdurre PR mandatory + 1 review (in MVP single-developer = self-review da branch separato).
2. Aggiornare branch policy in ADR-0011 di conseguenza.

## Errata

### 2026-04-30 — CHG-2026-04-30-003

- **Tipo:** errata corrige
- **Modifica:** sezione "Effetti collaterali noti" — frase "Hook governance va aggiornato via Errata Corrige... applicata alla prima introduzione di codice CI" sostituita con "Hook governance è stato aggiornato via Errata Corrige in CHG-2026-04-30-003" + dettaglio dei bypass effettivamente applicati al `commit-msg` (cumulativo: marker + author bot). Frontmatter `errata:` esteso con voce 2026-04-30.
- **Motivo:** allineamento al stato verificato del repository: l'aggiornamento di ADR-0006 è stato eseguito (CHG-2026-04-30-003) e il `commit-msg` ora applica il bypass cumulativo (marker `[skip ci]` + author email `github-actions[bot]`). La frase originale (futuro) era diventata obsoleta.
- **Sostanza alterata:** No. La decisione di esentare il bot resta invariata; cambia solo lo stato della relativa integrazione (da "side-decision futura" a "in vigore") e si aggiunge la precisazione che l'esenzione è cumulativa (marker da solo non basta, deve esserci anche l'author email del bot — irrigidimento testuale per evitare abusi, già implicito nell'intent originale).

### 2026-04-30 — CHG-2026-04-30-005

- **Tipo:** errata corrige (rollout staging)
- **Modifica:** documentato il rollout progressivo dei workflow rispetto al testo originale che ne prescriveva 4 con job completi sin dal giorno 1.
  - **`ci.yml` introdotto in CHG-2026-04-30-005** con job `quality-gates` (ruff+format+mypy+pytest unit+governance), `structure-check` (ADR-0013 8 aree + INDEX sync) e `governance-checks` (hook eseguibili + sezioni ADR). Replica server-side esatta del `pre-commit-app` locale.
  - **Job `tests`** (service container `postgres:16-alpine` + apt install Tesseract + playwright install chromium + `pytest --cov=src/talos --cov-fail-under=85 -m "not slow"`) **non in vigore** finché non arriva un modulo applicativo che lo giustifica. Ogni introduzione di un modulo coperto (`persistence/` → ADR-0015 attiva postgres+coverage; `ui/` → ADR-0016 attiva streamlit smoke; `io_/` → ADR-0017 attiva playwright+tesseract) si fa via CHG dedicato che aggiunge il job parziale in `ci.yml`.
  - **`gitnexus.yml`** rinviato finché ISS-001 non è risolta (ad oggi `gitnexus analyze` non gira sulla macchina di sviluppo). CHG dedicato.
  - **`release.yml`** rinviato finché non c'è un primo binario/wheel pubblicabile post-MVP. CHG dedicato.
  - **`hooks-check.yml`** rinviato; le verifiche di integrità hook sono già coperte dal job `governance-checks` di `ci.yml`. Errata futura potrà promuoverlo a workflow separato se la frequenza di check lo giustifica.
- **Motivo:** il testo originale di ADR-0020 prescriveva i 4 workflow con job completi (incluso `pytest --cov-fail-under=85`) ma il bootstrap in CHG-2026-04-30-004 ha intenzionalmente 0% di coverage (ossatura, codice di prodotto inesistente). Eseguire il job `tests` ora produrrebbe failure deterministico fino al primo modulo di sostanza. Disciplina ADR-0019: la soglia coverage è in vigore "sui moduli core" — bootstrap non rientra. Questo errata documenta esplicitamente la sequenza di rollout invece di lasciarla implicita o disattendere il testo originale silenziosamente.
- **Sostanza alterata:** No. La decisione di avere 4 workflow completi resta valida e vincolante. Cambia solo la cadenza di introduzione (da "tutti subito" a "incrementale, condizionata alla comparsa del modulo applicabile"), e l'incremento di ogni workflow viene tracciato in CHG dedicato. Coverage threshold ≥85% globale e ≥90% sui core (ADR-0019) restano invariate; entreranno nel `tests` job alla sua introduzione.
