---
id: CHG-2026-04-30-005
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0020, ADR-0006, ADR-0009
---

## What

Introduzione del primo workflow CI: `.github/workflows/ci.yml` (3 job, 14 step). Replica server-side esatta del `pre-commit-app` locale + verifiche `structure-check` (ADR-0013) e `governance-checks` (ADR-0001/0006). **Errata Corrige di ADR-0020** per documentare il rollout progressivo dei 4 workflow prescritti (gli altri 3 — `gitnexus.yml`, `release.yml`, `hooks-check.yml` — rinviati a CHG dedicati alla loro maturazione).

| File | Tipo | Cambio |
|---|---|---|
| `.github/workflows/ci.yml` | nuovo | 3 job: `quality-gates` (lint+format+mypy+pytest unit+governance), `structure-check` (ADR-0013 8 aree + ADR INDEX sync), `governance-checks` (hook eseguibili + sezioni ADR obbligatorie). Trigger: push qualsiasi branch + pull_request verso main. Concurrency con cancel-in-progress. Permissions read-only. |
| `docs/decisions/ADR-0020-cicd-github-actions.md` | errata corrige | Frontmatter `errata:` esteso con voce CHG-005. Sezione `## Errata` allungata con descrizione del rollout staging: ci.yml ora; tests/gitnexus/release/hooks-check rinviati con condizioni esplicite di attivazione. |

Nessun nuovo ADR promulgato.

## Why

ADR-0020 prevede 4 workflow GitHub Actions. Il testo originale li prescriveva tutti come parte della decisione cardine, ma il bootstrap in CHG-2026-04-30-004 ha intenzionalmente 0% coverage e zero dipendenze runtime. Conseguenza:
- **Job `tests` (postgres + tesseract + playwright + `--cov-fail-under=85`)** se eseguito ora produrrebbe failure deterministico per coverage. Il `--cov-fail-under=85` di ADR-0019 è in vigore "sui moduli core (vgp, tetris, extract)" — moduli che ancora non esistono.
- **`gitnexus.yml`** richiede `npx gitnexus analyze` server-side; ISS-001 dichiara questo non operativo.
- **`release.yml`** ha senso quando esiste un binario/wheel pubblicabile, post-MVP.
- **`hooks-check.yml`** sovrappone il job `governance-checks` già in `ci.yml`.

Senza un'errata corrige documentale, il testo originale di ADR-0020 risulterebbe disatteso silenziosamente. Disciplina ADR-0009 + ADR-0008 (anti-allucinazione): documentare lo scarto **prima** di eseguirlo.

Beneficio strutturale immediato di `ci.yml` minimale:
1. Ogni `git push origin main` viene validato server-side dagli stessi check del pre-commit locale, intercettando regressi anche da chi non ha attivato i hook (`bash scripts/setup-hooks.sh`).
2. Il job `structure-check` blocca commit che introducono directory fuori dalle 8 aree consentite di `src/talos/` (ADR-0013).
3. Il job `governance-checks` blocca commit con ADR malformati (sezioni mancanti) anche server-side.
4. Sblocca il pattern: ogni futuro modulo di sostanza estende `ci.yml` con il proprio job (es. ADR-0015 aggiungerà `tests-persistence` con postgres service container).

## How

### Struttura `ci.yml`

```yaml
on:
  push:
  pull_request:
    branches: [main]
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
```

3 job paralleli (no `needs:`) — falliscono indipendentemente.

#### Job `quality-gates`

Replica esatta del `scripts/hooks/pre-commit-app`:
1. `actions/checkout@v4`
2. `astral-sh/setup-uv@v4` con cache su `uv.lock`
3. `uv python install 3.11`
4. `uv sync --all-groups --frozen`
5. `uv run ruff check src/ tests/`
6. `uv run ruff format --check src/ tests/`
7. `uv run mypy src/`
8. `uv run pytest tests/unit tests/governance -m "not slow" -q`

Timeout 10 min. Cache uv accelera i run successivi (~30s a regime).

#### Job `structure-check`

Verifica ADR-0013 (8 aree consentite) + INDEX sync:
- Loop su `src/talos/*/`, fallisce se trova directory non in `^(io_|extract|vgp|tetris|formulas|persistence|ui|observability|config)$`.
- Loop su `docs/decisions/ADR-*.md`: per ogni `id:` estratto, verifica presenza in `INDEX.md`.

Timeout 5 min. No setup pesante.

#### Job `governance-checks`

Verifica struttura governance:
- `scripts/hooks/{pre-commit,commit-msg,pre-commit-app}` esistenti ed eseguibili.
- Ogni ADR in `docs/decisions/ADR-*.md` ha tutte le 6 sezioni obbligatorie (Contesto/Decisione/Conseguenze/Test di Conformità/Cross-References/Rollback).

Timeout 5 min. Replica le verifiche del `pre-commit` governance ma su tutti gli ADR (non solo quelli in staging).

### Decisioni di config (motivate)

- **Trigger su `push:` qualsiasi branch + `pull_request: branches: [main]`** — coerente con ADR-0020 single-push MVP. Branch protection (Settings → Branches) andrà configurata manualmente dal Leader: i `quality-gates` + `structure-check` + `governance-checks` sono i required status check.
- **`concurrency.group: ci-${{ github.ref }}` + `cancel-in-progress: true`** — evita CI duplicati su push rapidi (ADR-0020 prescrizione esplicita).
- **`permissions: contents: read`** — principio di least privilege; nessun job ha bisogno di scrivere. `gitnexus.yml` futuro avrà permissions write su `contents`.
- **`astral-sh/setup-uv@v4`** — versione stabile attuale (ottobre 2025). Errata futura se `v5+` introduce breaking changes.
- **No matrix Python** — un solo target (3.11), coerente con ADR-0014 `requires-python = ">=3.11,<3.13"`. Un eventuale matrix 3.11/3.12 può essere aggiunto dopo, decisione operativa non bloccante.
- **No upload coverage artifact** — il job `tests` (futuro) lo introdurrà; ora coverage è 0% per costruzione, niente da archiviare.

### Test in CHG-005

Il primo run reale di `ci.yml` su GitHub Actions sarà il push di questo CHG stesso. Atteso: `quality-gates` PASS (specchio del locale), `structure-check` PASS, `governance-checks` PASS.

## Tests

Test manuali documentati (ADR-0011 — file di governance/CI, non codice applicativo).

| Test | Comando / Verifica | Esito |
|---|---|---|
| YAML syntactically valid | `uv run --with pyyaml python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` | ✅ 3 jobs, 14 steps |
| Trigger configurato | `grep -E '^on:' .github/workflows/ci.yml` | ✅ |
| Concurrency configurata | `grep 'cancel-in-progress' .github/workflows/ci.yml` | ✅ |
| Permissions least-privilege | `grep -A1 '^permissions:' .github/workflows/ci.yml` → `contents: read` | ✅ |
| `quality-gates` ha 8 step canonici | conteggio step nel job (4 setup + 4 check) | ✅ |
| `structure-check` regex 8 aree corretta | `grep "^(io_\|extract\|vgp\|tetris\|formulas\|persistence\|ui\|observability\|config)$" .github/workflows/ci.yml` | ✅ |
| ADR-0020 frontmatter `errata:` esteso | `grep -c 'CHG-2026-04-30-005' docs/decisions/ADR-0020-cicd-github-actions.md` ≥ 2 (frontmatter + Errata section) | ✅ |
| ADR-0020 sezione Errata estesa | `grep -A3 '### 2026-04-30 — CHG-2026-04-30-005' docs/decisions/ADR-0020-cicd-github-actions.md` | ✅ |

**Validazione semantica end-to-end:** il primo run di GitHub Actions su questo push fungerà da test definitivo. Se uno dei 3 job fallisce, errata corrige immediata di `ci.yml` con CHG dedicato.

**Rischi residui:**
- `astral-sh/setup-uv@v4` potrebbe avere drift; in tal caso il fallimento è in fase setup, errata mira al pin di versione.
- `uv sync --frozen` richiede `uv.lock` esattamente coerente con `pyproject.toml`. Se in futuro un commit aggiorna `pyproject.toml` senza rigenerare `uv.lock`, il job fallisce: comportamento atteso, è un guard rail.
- I job `structure-check` e `governance-checks` sono bash-puro: facili da estendere ma anche da rompere se cambia il layout di `INDEX.md`. Mantenere la regex `^id:` allineata al template ADR-0001.
- L'incremento progressivo dei workflow (gitnexus, release, hooks-check, job tests) richiede CHG dedicati: ogni gap di copertura va segnalato esplicitamente al Leader (anti-allucinazione ADR-0008).

## Refs

- ADR: ADR-0020 (errata corrige primaria), ADR-0006 (governance hooks verificati nel job), ADR-0009 (meccanismo errata)
- Predecessore: CHG-2026-04-30-004 (Bootstrap codice minimale — il `pre-commit-app` qui replicato in CI)
- Successore atteso: prima estensione di `ci.yml` con job `tests` parziale, accompagnata dal CHG che introduce il primo modulo di sostanza
- Commit: `<pending>`
