---
id: CHG-2026-05-01-031
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 6 — blocco B1 sessione dedicata 2/8)
status: Draft
commit: PENDING
adr_ref: ADR-0021, ADR-0014, ADR-0019
---

## What

**Bridge stdlib→structlog del modulo `tetris/`** (2/5 della fase
B1.1). Replica il pattern di CHG-030 su `allocator.py` + `panchina.py`
+ relativi test telemetria. **Estrae** la fixture `log_capture` in
`tests/conftest.py` come scope-extension naturale (rule of three:
4 consumer test post-CHG-031).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/tetris/allocator.py` | modificato | `import logging` rimosso → `import structlog`. `_logger = logging.getLogger(__name__)` → `_logger = structlog.get_logger(__name__)`. 1 emit `tetris.skipped_budget`: `extra={...}` → `**kwargs`. |
| `src/talos/tetris/panchina.py` | modificato | Stesso pattern. 1 emit `panchina.archived`: `extra={...}` → `**kwargs`. |
| `tests/conftest.py` | modificato | + fixture `log_capture` (estratta da `test_logging_config.py` + `test_vgp_telemetry.py`, condivisa con i nuovi consumer). Pattern `structlog.testing.LogCapture` + `merge_contextvars`. |
| `tests/unit/test_logging_config.py` | modificato | Rimossa fixture locale `log_capture` (ora in conftest). Ruff TC002: `LogCapture` import in `TYPE_CHECKING` block. 6 test invariati. |
| `tests/unit/test_vgp_telemetry.py` | modificato | Rimossa fixture locale `log_capture` (CHG-030 → conftest). Ruff TC002. 5 test invariati. |
| `tests/unit/test_tetris_telemetry.py` | modificato | Migrato pytest `caplog` → `LogCapture` (consumer fixture conftest). Ruff TC002. 3 test invariati. |
| `tests/unit/test_panchina_telemetry.py` | modificato | Migrato pytest `caplog` → `LogCapture`. Ruff TC002. 3 test invariati. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **700 PASS** unit/gov/golden (invariato).
- **138 PASS** integration (invariato).
- **838 PASS** totali.

Detect_changes: 7 file, 15 simboli touched, 0 processi affetti, **risk LOW**.

Comportamento applicativo invariato 100%: stessi 2 eventi canonici
(`tetris.skipped_budget`, `panchina.archived`) con stessi campi.

## Why

CHG-030 ha aperto la fase B1.1 progressiva (decisione Leader 1=B):
modulo `vgp/` per primo. CHG-031 prosegue con `tetris/`, area
direttamente downstream nell'orchestrator pipeline (`compute_vgp_score`
→ `allocate_tetris` → `build_panchina`).

CHG-030 dichiarava esplicitamente: *"Soglia attesa [conftest condiviso]:
post-CHG-B1.1.b (tetris) se appare un nuovo test telemetria, oppure
post-CHG-B1.1.c (io_) con più probabilità."* Tetris introduce 2 nuovi
consumer della fixture (`test_tetris_telemetry`, `test_panchina_telemetry`):
con `test_logging_config` e `test_vgp_telemetry` arriviamo a **4
consumer** — rule of three è ampiamente superato. L'estrazione in
`tests/conftest.py` è stata fatta in questo CHG come scope-extension
"obbligata dalla naturalezza" (no over-engineering, no anticipo).

### Decisioni di design

1. **`tests/conftest.py` (root) NOT `tests/unit/conftest.py`**:
   pattern pytest standard. La fixture `log_capture` può servire in
   futuro a test integration che vogliano sottoscrivere eventi
   structlog (es. test su `acquire_and_persist` che verifichi
   l'emit di `keepa.miss` durante una sequenza). Conftest più alto
   = visibilità più ampia, costo zero per i test che non la
   richiedono.

2. **`from typing import TYPE_CHECKING` + `if TYPE_CHECKING: from
   structlog.testing import LogCapture`**: ruff TC002 segnala che
   l'import è usato solo come type annotation (la fixture pytest
   passa l'oggetto runtime, ma il binding lessicale è `LogCapture
   | None`). Pattern standard ruff/mypy strict, già usato altrove
   nella codebase per `pd.DataFrame`.

3. **Rimosso `import structlog` non usato runtime in
   `test_vgp_telemetry.py`**: la fixture conftest contiene
   `structlog.configure`, il test consumer non ne ha più bisogno.
   Ruff lo segnalava come unused.

4. **Test `test_logging_config.py` invariato semanticamente**: la
   fixture conftest replica esattamente il pattern locale precedente
   (CHG-030). Le 6 asserzioni esistenti continuano a passare
   senza modifiche.

5. **Pattern `caplog` → `log_capture` per tetris/panchina**: stesso
   mapping di CHG-030:
   - `caplog.at_level(logging.DEBUG, logger="...")` rimosso
     (fixture configura tutto pre-test).
   - `r.message` → `entry["event"]`.
   - `getattr(r, "asin", None)` → `entry["asin"]`.
   - `caplog.records` → `log_capture.entries`.

6. **Set comprehension `{getattr(r, "asin", None) for r in archived}`
   → `{e["asin"] for e in archived}`**: stesso intent, sintassi
   coerente con il nuovo pattern.

7. **Test `_cart_with` helper invariato**: utility test, non
   coinvolta nel bridge.

8. **`test_logging_config.py` mantiene `clear_session_context()` setup
   esplicito**: testa il bind helper, non solo la cattura. Lo
   scope di responsabilità del test resta lo stesso.

### Out-of-scope

- **Bridge altri moduli applicativi**: scope CHG-B1.1.c (io_),
  B1.1.d (extract), B1.1.e (ui).
- **Adoption `bind_session_context` nei caller**: scope CHG-B1.2
  (orchestrator) e CHG-B1.3 (UI).
- **Errata catalogo ADR-0021** (campi context-bound + pulizia
  `tenant_id`): scope CHG-B1.4.
- **Test e2e per `merge_contextvars` end-to-end**: scope CHG-B1.2
  (sentinella ereditarietà context dopo orchestrator adoption).

## How

### `tests/conftest.py` (highlight)

```python
@pytest.fixture
def log_capture() -> LogCapture:
    """Cattura eventi structlog per assertion (ADR-0021)."""
    capture = LogCapture()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            capture,
        ],
        cache_logger_on_first_use=False,
    )
    return capture
```

### `tetris/allocator.py` (highlight diff)

```diff
-import logging
+import structlog
 ...
-_logger = logging.getLogger(__name__)
+_logger = structlog.get_logger(__name__)
 ...
-_logger.debug(
-    "tetris.skipped_budget",
-    extra={"asin": str(row[asin_col]), "cost": cost_total, "budget_remaining": cart.remaining},
-)
+_logger.debug(
+    "tetris.skipped_budget",
+    asin=str(row[asin_col]),
+    cost=cost_total,
+    budget_remaining=cart.remaining,
+)
```

Stesso pattern per `tetris/panchina.py` (emit `panchina.archived`).

### Test consumer (highlight)

```python
def test_skipped_budget_emits_canonical_event(log_capture: LogCapture) -> None:
    cart = allocate_tetris(vgp_df, budget=500.0, locked_in=[])
    skipped = [e for e in log_capture.entries if e["event"] == "tetris.skipped_budget"]
    assert len(skipped) == 1
    assert skipped[0]["asin"] == "B_BIG"
    assert skipped[0]["cost"] == pytest.approx(1000.0)
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 137 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria mirata (4 file) | `uv run pytest tests/unit/test_tetris_telemetry.py tests/unit/test_panchina_telemetry.py tests/unit/test_vgp_telemetry.py tests/unit/test_logging_config.py -v` | **17 PASS** |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **700 PASS** (invariato) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | `gitnexus_impact("allocate_tetris"/"build_panchina", "upstream")` | risk LOW, 0 upstream, 0 processes |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 15 symbols / 7 files, 0 processes affected, risk LOW |

**Rischi residui:**
- **`tests/conftest.py` ora ha side-effect globale `structlog.configure`**:
  ogni test che usa `log_capture` (4 file oggi, espandibile). I
  test che NON la usano non vedono effetti. La suite full
  (700+138) verde dimostra zero regressione.
- **`structlog.testing.LogCapture` import in TYPE_CHECKING**:
  funziona solo perché `from __future__ import annotations` è
  attivo. Se rimosso il future import, le annotazioni `LogCapture`
  diventerebbero forward references non risolvibili. Mitigazione:
  `from __future__ import annotations` è policy comune in
  `tests/`.
- **Side-effect `structlog.configure` nella fixture residua dopo
  il test**: i test successivi vedono la config del LogCapture
  finché un altro `structlog.configure` non sovrascrive. Validato
  cross-test in CHG-030 e ora cross-conftest in CHG-031.
  Mitigazione strutturale futura (post B1.1.e): teardown esplicito
  in fixture o `autouse` reset.

## Test di Conformità

- **Path codice applicativo:** `src/talos/tetris/` ✓ (area
  ADR-0013 consentita).
- **ADR-0021 vincoli rispettati:** structlog è la libreria canonica.
  Allineamento dei 2 siti emit `tetris/` completa la coerenza nel
  cluster.
- **ADR-0019 (test strategy):** unit puri ✓. Conftest condiviso è
  pattern pytest standard.
- **Quality gate verde:** ruff/format/mypy/pytest tutti pass
  (ADR-0014).
- **No nuovi simboli applicativi**: solo refactor di simboli
  esistenti. La fixture `log_capture` è test-side, scope ADR-0019.
- **Backward compat semantica:** invariata 100% (stessi eventi,
  stessi campi).
- **Sicurezza:** zero secrets/PII; no nuove deps.
- **Impact analysis pre-edit:** `allocate_tetris` + `build_panchina`
  upstream=0, processes=0, risk LOW (GitNexus).
- **Detect changes pre-commit:** 15 simboli touched, 0 processi
  affetti, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**: refactor
  mirato + 0 test nuovi (riusati gli esistenti) + estrazione
  conftest dichiarata in CHG-030.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite invariata in conteggio**: 838 PASS. I 14 test
  telemetria (3 tetris + 3 panchina + 5 vgp + 6 logging_config)
  ora condividono fixture conftest.
- **Sblocca CHG-B1.1.c..e**: stesso pattern replicabile su io_/,
  extract/, ui/ (i 3 CHG successivi). Nuovi consumer telemetria
  riutilizzeranno la fixture conftest senza copia locale.
- **Sblocca CHG-B1.2/B1.3**: dopo che tutti i 12 siti usano
  structlog native, `bind_session_context` smette di essere "morto"
  e propaga `session_id`/`tenant_id`/`request_id` a tutti gli
  emit downstream via `merge_contextvars`.
- **Code health**: -1 fixture duplicata (4 → 1 conftest condiviso).
  Ruff TC002 disciplinato come pattern standard.

## Refs

- ADR: ADR-0021 (logging/telemetria), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test strategy + fixture conftest).
- Predecessori:
  - CHG-2026-04-30-006 (observability `configure_logging` reale).
  - CHG-2026-04-30-046 (telemetria `tetris.skipped_budget`).
  - CHG-2026-04-30-049 (telemetria `panchina.archived`).
  - CHG-2026-05-01-030 (B1.1.a vgp/ — apertura fase B1.1, pattern
    di refactor consolidato + dichiarazione rule-of-three).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1, ratificate in
  CHG-030).
- Successore atteso: **CHG-B1.1.c** (bridge structlog su `io_/`).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: PENDING (atteso permesso esplicito Leader).
