# TALOS — Scaler 500k

Hedge fund algoritmico applicato al modello FBA Wholesale High-Ticket. Vision in [`PROJECT-RAW.md`](PROJECT-RAW.md) (`Frozen` dal 2026-04-29).

> **README operativo**, non documentazione utente. La user-guide del CFO è in ROADMAP (post-bootstrap).

---

## Setup

Dopo ogni clone:

```bash
bash scripts/setup-dev.sh
```

Idempotente. Installa `uv` (Astral) se assente, scarica Python 3.11, esegue `uv sync` e attiva i git hook governance (ADR-0006).

Verifica setup:

```bash
git config core.hooksPath        # deve stampare: scripts/hooks
uv run pytest tests/unit tests/governance -q
```

## Struttura

Layout vincolato da [ADR-0013](docs/decisions/ADR-0013-project-structure.md) (`src-layout`):

```
src/talos/
  io_/            # Keepa + Playwright + Tesseract (ADR-0017)
  extract/        # SamsungExtractor + interface BrandExtractor (ADR-0017)
  vgp/            # VGP score + normalize + veto (ADR-0018)
  tetris/         # Allocator + panchina (ADR-0018)
  formulas/       # F1..F5 + fee_fba L11b (ADR-0018)
  persistence/    # SQLAlchemy 2.0 sync + RLS (ADR-0015)
  ui/             # Streamlit + multi-page (ADR-0016)
  observability/  # structlog + catalogo eventi (ADR-0021)
  config/         # pydantic-settings (ADR-0013)
tests/{unit,integration,golden,governance}/
migrations/       # Alembic (ADR-0015)
.github/workflows/  # CI (ADR-0020)
```

## Workflow

1. Self-Briefing al rientro: leggere [`docs/STATUS.md`](docs/STATUS.md), [`docs/decisions/INDEX.md`](docs/decisions/INDEX.md), ultimi 3 change docs in `docs/changes/`.
2. Ogni modifica non-triviale richiede **change document** in `docs/changes/YYYY-MM-DD-NNN-slug.md` (ADR-0004) **prima** del commit.
3. Commit message footer obbligatorio:
   ```
   CHG-YYYY-MM-DD-NNN
   ADR-NNNN
   ```
   Verificato meccanicamente dal `commit-msg` hook (ADR-0006).
4. Test gate (ADR-0002 + ADR-0011): codice applicativo → test automatici PASS; governance → test manuali documentati.

## Comandi rapidi

```bash
uv run pytest tests/                         # tutti i test
uv run pytest -m "not slow" -q               # senza i lenti
uv run ruff check --fix src/ tests/          # lint con autofix
uv run ruff format src/ tests/               # format
uv run mypy src/                             # type check
```

## Documenti

- [`CLAUDE.md`](CLAUDE.md) — Rules of Engagement per Claude (Self-Briefing, ADR-driven workflow).
- [`AGENTS.md`](AGENTS.md) — Equivalente multi-agent (Cursor/Cline/Aider).
- [`PROJECT-RAW.md`](PROJECT-RAW.md) — Vision integrale, `Frozen`. Modifiche solo via Errata Corrige (ADR-0009).
- [`ROADMAP.md`](ROADMAP.md) — Tracker operativo.
- [`docs/decisions/`](docs/decisions/) — Architectural Decision Records (autorità).
- [`docs/changes/`](docs/changes/) — Cross-reference documents.
- [`CHANGELOG.md`](CHANGELOG.md) — Storia versioni.

## Stato corrente

Vedi [`docs/STATUS.md`](docs/STATUS.md). Tag milestone: `milestone/stack-frozen-v0.9.0`.
