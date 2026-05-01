---
id: CHG-2026-05-01-030
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" estesa round 6 — blocco B1 sessione dedicata 1/8)
status: Draft
commit: 5c2e92b
adr_ref: ADR-0021, ADR-0014, ADR-0019
---

## What

**Bridge stdlib→structlog del modulo `vgp/`** (1/5 della fase B1.1
"`structlog.bind` context tracing"). Apre il blocco B1 ratificato
Leader 2026-05-01 round 6 (decisioni 1=B/2=a/3=a/4=a/5=a).

Sostituisce in `vgp/score.py` lo stack `_logger = logging.getLogger(__name__)`
+ `_logger.debug("evt", extra={...})` (stdlib logging) con
`_logger = structlog.get_logger(__name__)` + `_logger.debug("evt", **kwargs)`
(structlog native). Migra `tests/unit/test_vgp_telemetry.py` da pytest
`caplog` (stdlib `LogRecord`) a `structlog.testing.LogCapture` (pattern
già consolidato in `test_logging_config.py`).

Comportamento applicativo invariato: stessi 2 eventi canonici (`vgp.veto_roi_failed`,
`vgp.kill_switch_zero`) con stessi campi (`asin`, `roi_pct`, `threshold`,
`match_status`). La differenza è che da ora il pipeline structlog
configurato in `configure_logging` (CHG-2026-04-30-006) può effettivamente
**vedere** questi eventi e applicarvi `merge_contextvars` — sblocca
l'adoption futura di `bind_session_context` (CHG-B1.2).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/vgp/score.py` | modificato | `import logging` → `import structlog`. `_logger = logging.getLogger(__name__)` → `_logger = structlog.get_logger(__name__)`. 2 emit sites: `_logger.debug("evt", extra={...})` → `_logger.debug("evt", **kwargs)`. Aggiornato commento riga 124 (caplog → LogCapture). |
| `tests/unit/test_vgp_telemetry.py` | modificato | Riscritto: `pytest.LogCaptureFixture` → `structlog.testing.LogCapture`. + fixture `log_capture` (pattern `test_logging_config.py:16-27`). Asserzioni `r.message`/`getattr(rec, ...)` → `entry["event"]`/`entry["asin"]`. 5 test invariati semanticamente. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **700 PASS** unit/gov/golden (invariato, stesso conteggio CHG-029).
- **138 PASS** integration (invariato).
- **838 PASS** totali.

Detect_changes: 2 file, 12 simboli touched, 0 processi affetti, **risk LOW**.

## Why

CHG-006 ratificò ADR-0021 con `configure_logging` (structlog native +
`merge_contextvars` nel pipeline) e gli helper `bind_session_context` /
`clear_session_context` (CHG-006/Errata 058). MA tutti i 12 siti emit
applicativi (`vgp/`, `tetris/`, `io_/`, `extract/`, `ui/`) usano stdlib
`logging.getLogger`, **non vedendo i contextvars di structlog**: il
bind helper era di fatto morto in produzione. I test telemetria reali
(`test_vgp_telemetry.py`, `test_listino_input_cache_telemetry.py`,
etc.) usano pytest `caplog` (stdlib `LogRecord`), confermando che il
flusso ufficiale corrente è stdlib.

Per consumare il bind context (sblocca multi-tenant + correlazione log
end-to-end + propagazione `session_id`/`request_id`/`tenant_id` su
tutti i 17 eventi catalogo) serve completare il bridge stdlib→structlog.

CHG-030 apre la fase B1.1 progressiva (decisione Leader 1=B):
modulo `vgp/` per primo perché:
- 1 solo file applicativo (`score.py`).
- 1 file test telemetria dedicato (5 test).
- 0 dipendenze upstream (impact analysis su `compute_vgp_score`:
  upstream=0, processes=0, risk=LOW).
- Pattern di refactor minimale, validabile prima di replicare su
  `tetris/`/`io_/`/`extract/`/`ui/` (4 CHG successivi del blocco
  B1.1: tetris/io_/extract/ui).

### Decisioni di design

1. **`structlog.get_logger(__name__)` invece di `structlog.get_logger()`
   senza nome**: preserva la convenzione `talos.<area>.<file>` come
   logger identifier. Utile per filtraggio futuro (es. routing per
   modulo a tracing backend diversi).

2. **`extra={"asin": ..., "roi_pct": ...}` → `**kwargs` direct**:
   structlog native consuma kwargs come campi del record. `extra=`
   è API stdlib `LogRecord.__dict__` injection, non valido in
   structlog (verrebbe trattato come singolo campo `extra` con dict
   payload). La modifica è del tutto equivalente in semantica
   applicativa.

3. **Fixture `log_capture` replica esatta del pattern
   `test_logging_config.py:16-27`**: zero invenzione di pattern,
   coerenza pieno con l'unico altro test pre-esistente che usa
   `LogCapture`. La fixture è function-scoped (default pytest).
   `cache_logger_on_first_use=False` garantisce che la riconfigurazione
   sia attiva per il test corrente.

4. **NO conftest.py condiviso per `log_capture`** (per ora): la fixture
   è duplicata localmente nel file test. Razionale: fino a CHG-030
   solo 1 file la usa (test_logging_config). Da CHG-030 a 2.
   Estrazione a `tests/conftest.py` quando saranno >=3 file (regola
   "rule of three" pratica). Soglia attesa: post-CHG-B1.1.b (tetris)
   se appare un nuovo test telemetria, oppure post-CHG-B1.1.c (io_)
   con più probabilità.

5. **`merge_contextvars` nel pipeline fixture** anche se i 5 test
   non bind nulla: pattern coerente con `test_logging_config.py:22`,
   prepara fixture future che testeranno l'ereditarietà context
   (CHG-B1.2). Costo trascurabile.

6. **Side-effect su configurazione globale structlog**: `structlog.configure(...)`
   nella fixture sostituisce la config globale del processo pytest.
   I test successivi nella stessa run ereditano. **Verifica
   empirica**: `pytest tests/unit tests/governance tests/golden -q`
   passa 700/700, nessuna regressione cross-file. Il pattern è
   validato dal pre-esistente `test_logging_config.py` che già fa
   lo stesso side-effect.

7. **Nessuna modifica al catalogo eventi ADR-0021**: gli eventi
   restano i 17 attuali (catalogo + tuple campi obbligatori
   invariati). La pulizia "context-bound" (es. rimozione `tenant_id`
   da `cache.hit/miss` perché ereditato dal bind) è scope CHG-B1.4.

8. **NO `from __future__ import annotations` rimosso**: invariato
   (preservato a riga 28 per consistenza con resto della codebase).

### Out-of-scope

- **Adoption `bind_session_context` in `compute_vgp_score`**: scope
  CHG-B1.2 (orchestrator) e CHG-B1.3 (UI). `vgp.score` è chiamato
  dall'orchestrator: il bind sarà legato a livello chiamante, non
  emit-site.
- **Bridge altri moduli applicativi**: scope CHG-B1.1.b/c/d/e
  (tetris, io_, extract, ui).
- **Errata catalogo ADR-0021**: scope CHG-B1.4.
- **Estensione `bind_session_context` con `tenant_id`/`request_id`**:
  scope CHG-B1.2 (split helper).
- **Conftest condiviso per `log_capture`**: rule-of-three trigger
  in CHG-B1.1.b o successivi.

## How

### `vgp/score.py` (highlight diff)

```diff
-import logging
+import structlog
 ...
-_logger = logging.getLogger(__name__)
+_logger = structlog.get_logger(__name__)
 ...
-_logger.debug(
-    "vgp.veto_roi_failed",
-    extra={
-        "asin": str(asin),
-        "roi_pct": float(roi_value),
-        "threshold": veto_roi_threshold,
-    },
-)
+_logger.debug(
+    "vgp.veto_roi_failed",
+    asin=str(asin),
+    roi_pct=float(roi_value),
+    threshold=veto_roi_threshold,
+)
```

Stesso pattern per `vgp.kill_switch_zero` (riga ~155).

### `tests/unit/test_vgp_telemetry.py` (highlight pattern)

```python
@pytest.fixture
def log_capture() -> LogCapture:
    capture = LogCapture()
    structlog.configure(
        processors=[structlog.contextvars.merge_contextvars, capture],
        cache_logger_on_first_use=False,
    )
    return capture


def test_veto_roi_failed_event_emitted(log_capture: LogCapture) -> None:
    df = _df([("A_OK", 0.20, ...), ("B_VETO", 0.05, ...), ...])
    compute_vgp_score(df)

    veto_entries = [e for e in log_capture.entries if e["event"] == "vgp.veto_roi_failed"]
    assert len(veto_entries) == 1
    entry = veto_entries[0]
    assert entry["asin"] == "B_VETO"
    assert entry["roi_pct"] == pytest.approx(0.05)
    assert entry["threshold"] == pytest.approx(0.08)
```

### Pattern caplog → LogCapture (mapping concettuale)

| stdlib `caplog` | structlog `LogCapture` |
|---|---|
| `caplog.at_level(logging.DEBUG, logger="...")` context manager | (assente) — fixture configura tutto pre-test |
| `r.message` | `entry["event"]` |
| `getattr(r, "asin", None)` | `entry["asin"]` (solleva KeyError se mancante — più strict) |
| `caplog.records` | `log_capture.entries` |

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/vgp/score.py tests/unit/test_vgp_telemetry.py` | All checks passed |
| Format | `uv run ruff format src/talos/vgp/score.py tests/unit/test_vgp_telemetry.py` | 2 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria mirata | `uv run pytest tests/unit/test_vgp_telemetry.py -v` | **5 PASS** |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **700 PASS** (invariato) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | `gitnexus_impact("compute_vgp_score", "upstream")` | risk LOW, 0 upstream, 0 processes |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 12 symbols touched, 0 processes affected, risk LOW |

**Rischi residui:**
- **Side-effect globale `structlog.configure(...)` nella fixture**:
  i test successivi ereditano la configurazione del LogCapture
  finché un altro `structlog.configure` non sovrascrive. La suite
  full (700/700 + 138/138) verde dimostra zero regressione cross-test
  oggi. Mitigazione strutturale futura (post B1.1.e): teardown
  esplicito o conftest condiviso che reimposta `configure_logging()`
  default in `autouse` fixture.
- **`getattr(rec, ...)` (vecchio pattern caplog) era tollerante a
  campi mancanti, `entry["..."]` solleva KeyError**: divergenza
  voluta — il test è ora più strict, intercetta drift di campi non
  emessi. Trade-off: se un campo opzionale non viene emesso il test
  diventa rosso esplicitamente, invece che silenziosamente passare.
- **`extra={"foo": ...}` rimosso**: in `caplog.records` stdlib gli
  extra erano accessibili come attributi dell'oggetto `LogRecord`.
  Verificato: i test sono tutti aggiornati al nuovo pattern; nessun
  altro consumer di questi log esiste.
- **Performance**: structlog `get_logger()` è marginalmente più
  costoso del primo `logging.getLogger()`, ma il logger è module-level
  + cached. Trascurabile.

## Test di Conformità

- **Path codice applicativo:** `src/talos/vgp/` ✓ (area ADR-0013
  consentita).
- **ADR-0021 vincoli rispettati:** structlog è già la libreria di
  scelta canonica (CHG-006 + ADR-0021). Allineamento dei 12 siti
  emit alla scelta canonica è completamento, non deviazione.
- **ADR-0019 (test strategy):** unit puri ✓. Test telemetria
  mock-only invariati (no DB, no live). Pattern `LogCapture` già
  consolidato.
- **Quality gate verde:** ruff/format/mypy/pytest tutti pass
  (ADR-0014).
- **No nuovi simboli senza ADR Primario:** zero simboli nuovi (solo
  refactor di simboli esistenti).
- **Backward compat semantica:** comportamento applicativo invariato
  100% (stessi eventi, stessi campi, stessi valori). Cambia solo
  l'API del logger sottostante.
- **Sicurezza:** zero secrets/PII; nessuna nuova dipendenza
  (`structlog` già `>=24` in `pyproject.toml`).
- **Impact analysis pre-edit:** `compute_vgp_score` upstream=0,
  processes=0, risk LOW (GitNexus).
- **Detect changes pre-commit:** 12 simboli touched (1 funzione
  applicativa + 5 test + helpers), 0 processi affetti, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
  Refactor infrastrutturale, no errata.
- **`feedback_concisione_documentale.md` rispettato**: refactor
  mirato + 0 test nuovi (riusati i 5 esistenti) + change doc snello.

## Impact

- **`pyproject.toml` invariato** (no nuove deps; `structlog` già `>=24`).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite invariata in conteggio**: 838 PASS (700 + 138). I 5
  test telemetria `vgp` migrati 1:1 al pattern `LogCapture`.
- **Sblocca CHG-B1.1.b..e**: stesso pattern di refactor replicabile
  su tetris/io_/extract/ui.
- **Sblocca CHG-B1.2/B1.3**: dopo che tutti i 12 siti usano structlog
  native, `bind_session_context` smette di essere "morto" e propaga
  `session_id`/`tenant_id`/`request_id` a tutti gli emit downstream
  via `merge_contextvars`.
- **Code health**: allineamento dei 12 siti emit alla scelta
  canonica ADR-0021. Riduce confusion ("perché c'è bind helper se
  nessuno lo consuma?").

## Refs

- ADR: ADR-0021 (logging/telemetria), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test strategy unit puri).
- Predecessori:
  - CHG-2026-04-30-006 (observability `configure_logging` reale —
    structlog pipeline + merge_contextvars).
  - CHG-2026-04-30-049 (telemetria vgp.veto_roi_failed +
    vgp.kill_switch_zero — emit sites stdlib originali).
  - CHG-2026-04-30-058 (errata catalogo `session.replayed` —
    pattern errata catalogo additiva).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1):
  1. Strategia conversione = **B** (progressivo per area, 5 CHG).
  2. session_id vs request_id = **a** (request_id UUID4 + session_id
     post-save distinti).
  3. Estensione bind helper = **a** (split bind_request_context +
     bind_session_context).
  4. Pulizia tenant_id su cache.hit/miss = **a** (errata, context-bound).
  5. tenant_id source = **a** (hardcoded 1 + TODO provider futuro).
- Successore atteso: **CHG-B1.1.b** (bridge structlog su `tetris/`).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato; `project_session_handoff_2026-05-01-round5plus.md`
  identificava B1 come blocco "sessione dedicata".
- Commit: `5c2e92b`.
