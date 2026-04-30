---
id: ADR-0019
title: Test Strategy Applicativa — pytest + golden dataset
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

ADR-0002 (Test Gate) impone test passante per ogni commit non-triviale di codice applicativo. ADR-0011 estende il test gate con manuali documentati per governance.

L20 (Round 2) ha ratificato il paniere: pytest + fixture byte-exact + grep R-01 + lint + type strict. ADR-0014 ha cristallizzato lint+type. Manca la strategia di test **applicativa** concreta: quali test, quali livelli, quale dataset, quale coverage target, come gestire fixture su DB e Playwright.

Senza questo ADR i test diventano "best effort" e la fixture byte-exact (criterio di completamento di L20) rischia di non essere mai realizzata.

## Decisione

### Layout test (`tests/`)

```
tests/
├── unit/                       # Funzioni pure, no I/O
│   ├── test_vgp_normalize.py
│   ├── test_vgp_score.py
│   ├── test_tetris_allocator.py
│   ├── test_formulas_*.py
│   └── test_extract_samsung.py
├── integration/                # I/O con DB reale + Playwright + Tesseract
│   ├── test_persistence.py
│   ├── test_rls.py
│   ├── test_audit_log.py
│   ├── test_keepa_client.py    # con cassette VCR
│   ├── test_amazon_scrape.py   # su HTML statici di golden/html/
│   ├── test_ocr_pipeline.py
│   ├── test_fallback_chain.py
│   └── test_ui_*.py
├── golden/                     # Fixture byte-exact (L20)
│   ├── samsung_1000.json       # 1000 righe sintetiche validate dal Leader
│   ├── samsung_1000_expected.json  # output VGP + Cart + Panchina atteso
│   ├── html/                   # HTML statici Amazon per scraping test
│   ├── images/                 # immagini per OCR test
│   └── test_pipeline_byte_exact.py
├── governance/                 # Invarianti governance
│   ├── test_no_silent_drops.py # grep \.drop\( (R-01)
│   ├── test_no_root_imports.py # ADR-0013: niente from src.*
│   └── test_adr_index_sync.py  # ogni ADR file presente in INDEX.md
├── conftest.py                 # fixture comuni: db_session, playwright_browser, etc.
└── pytest.ini.toml             # config (in pyproject.toml)
```

### Golden dataset Samsung — `samsung_1000.json`

**Decisione Leader:** sintetico costruito + validato dal Leader (non estratto da listino reale, per evitare rumore non controllato).

Composizione target (1000 righe):
- ~600 righe Samsung S/Z/A/M validi con costi/prezzi/BuyBox controllati
- ~150 edge case ROI (ROI < 8% → veto, ROI border 7.99% e 8.01%)
- ~100 edge case match Samsung (asimmetria benigna 5G whitelist, ROM/RAM mismatch)
- ~50 KILLED (R-05 → VGP=0)
- ~50 BuyBox alta (verifica Tetris saturazione)
- ~50 con `s_comp` estremo (1 → divisione semplice; 100 → Q_m → 0)

**Output atteso `samsung_1000_expected.json`** include: VGP score per ogni ASIN, Cart finale, Panchina, audit log row count.

**Vincolo R-01:** differenza di 1 centesimo o 1 ASIN tra output corrente e atteso → test fallisce. Niente `pytest.approx`.

### Coverage target

| Modulo | Coverage minima | Strict? |
|---|---|---|
| `vgp/`, `tetris/`, `formulas/` | **≥ 90%** | Strict (CI fallisce sotto soglia) |
| `extract/`, `io_/`, `persistence/` | ≥ 85% | Strict |
| `ui/` | ≥ 60% | Best-effort (Streamlit testing limitato) |
| `observability/`, `config/` | ≥ 80% | Strict |
| **Totale progetto** | **≥ 85%** | Strict (`--cov-fail-under=85`) |

### Hypothesis (property-based)

Decisione Leader: **solo su `vgp/normalize.py` e `vgp/score.py`**. Niente overkill altrove.

Invarianti garantiti:
- `vgp/normalize.py`:
  - `0 ≤ norm(x_i) ≤ 1` ∀ x_i (escluso edge max==min)
  - `min(x) → 0`, `max(x) → 1`
  - Idempotenza: `norm(norm(x)) == norm(x)`
- `vgp/score.py`:
  - `vgp_score == 0` se `kill_mask` o `~veto_roi_passed`
  - `0 ≤ vgp_score ≤ 1` altrimenti
  - Pesi 40/40/20: `vgp_score == 0.4*r + 0.4*v + 0.2*c` con r,v,c ∈ [0,1] tutti normalizzati

### Fixture & Setup

- **DB integration:** `pytest-postgresql` con container ephemeral; ogni test ha schema pulito.
- **Playwright:** `pytest-playwright` in headless; HTML statici da `tests/golden/html/`.
- **Keepa:** `vcr.py` per cassette HTTP riproducibili.
- **OCR:** immagini canoniche in `tests/golden/images/` con confidenza nota.

### Markers pytest (`@pytest.mark.*`)

| Marker | Scope | Esecuzione |
|---|---|---|
| `unit` | Test puri (no I/O) | Sempre, veloce |
| `integration` | DB / Playwright / OCR | Sempre in CI, su richiesta in dev |
| `golden` | Byte-exact su dataset | Sempre, blocking per release |
| `governance` | Invarianti R-01 / structure / INDEX | Sempre |
| `slow` | Test > 5s | Saltato in pre-commit, eseguito in CI nightly |

### Pre-commit applicativo

Invocato dal `pre-commit` di governance (ADR-0006) quando in staging ci sono `*.py`:

```bash
uv run pytest tests/unit -m "not slow" --cov=src/talos --cov-fail-under=85 -q
```

Solo unit + governance, < 30s. Integration + golden in CI completa.

### Convenzioni di naming test

- Funzione test: `test_<funzione_target>_<scenario>_<expected>` (es. `test_normalize_max_equals_min_returns_zero`).
- Class fixture: `class TestNormalize:` con setup/teardown via `@pytest.fixture`.
- Golden fixtures versionati con commit hash nel nome del file (`samsung_1000_v0.1.json` → bump versione su modifica strutturale).

## Conseguenze

**Positive:**
- Golden dataset è l'oracolo per ogni futura modifica del decisore: bug regression intercettati immediatamente.
- Hypothesis su VGP previene bug matematici sottili (es. divisione per zero, overflow).
- Layout per livelli (unit/integration/golden) permette esecuzione mirata in dev e completa in CI.

**Negative / costi:**
- Setup CI più lungo (Playwright + Postgres container + Tesseract).
- Manutenzione golden dataset: ogni cambio formula richiede nuovo `samsung_1000_expected.json` validato dal Leader.
- Curva iniziale: scrivere il primo `samsung_1000.json` validato è onesto lavoro (1-2 giorni del Leader).

**Effetti collaterali noti:**
- Test integration richiedono Docker disponibile in CI (lo è di default su GitHub Actions ubuntu-latest).
- Hypothesis può scoprire edge case che richiedono ulteriore disciplina nel codice (welcome).

## Test di Conformità

1. **Coverage gate:** `pytest --cov-fail-under=85` in CI (`ci.yml`).
2. **Golden invariance:** `pytest tests/golden -v` deve passare al 100% (no test xfail).
3. **Hypothesis run:** `pytest tests/unit/test_vgp_normalize.py tests/unit/test_vgp_score.py --hypothesis-show-statistics` in CI; almeno 100 esempi per invariante.
4. **No silent drops:** `pytest tests/governance/test_no_silent_drops.py` fa grep `\.drop\(` su `src/`, fallisce su occorrenze non commentate.
5. **INDEX.md sync:** `pytest tests/governance/test_adr_index_sync.py` verifica ogni ADR file referenziato in INDEX.md.
6. **Golden dataset versioning:** modifica a `samsung_1000.json` o `*_expected.json` senza change document è bloccata da pre-commit ADR-0006.

## Cross-References

- ADR correlati: ADR-0001, ADR-0002 (test gate), ADR-0006 (pre-commit), ADR-0011 (test manuali governance), ADR-0014 (stack/quality), ADR-0015/16/17/18 (test mirano questi moduli)
- Governa: `tests/`, `pyproject.toml` `[tool.pytest.ini_options]`, `[tool.coverage.run]`
- Impatta: ogni commit di codice applicativo (test gate)
- Test: il test stesso è il proprio oracolo
- Commits: `<pending>`

## Rollback

Se 85% coverage si rivela bloccante in fase di sviluppo:
1. Errata Corrige a ADR-0019: abbassare temporaneamente a 75% con motivazione documentata.
2. Re-innalzare appena la base di test cresce.

Se Hypothesis genera troppi falsi positivi:
1. Restringere `@given` strategies con `filter()` espliciti.
2. Documentare casi noti come `@example()` espliciti.
