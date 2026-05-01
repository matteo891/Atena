---
id: CHG-2026-05-01-035
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 6 — blocco B1 sessione dedicata 6/8)
status: Draft
commit: PENDING
adr_ref: ADR-0021, ADR-0018, ADR-0014, ADR-0019
---

## What

**B1.2: split bind helper + adoption orchestrator**. Tre interventi
coordinati che chiudono lo strato "infrastruttura context tracing"
sbloccato dalla fase B1.1:

1. **Split helper observability** (decisione Leader 3=a): aggiunti
   `bind_request_context(*, tenant_id, request_id=None) -> str` +
   `clear_request_context()` in `logging_config.py`. `bind_session_context`
   resta invariato (post-save, estende request-level). Re-export
   in `talos.observability.__init__`.
2. **Bridge `orchestrator.py`** (ultimo isolotto stdlib post B1.1):
   `import logging` → `import structlog`, `_logger = structlog.get_logger(__name__)`,
   1 emit `session.replayed` migrato a kwargs native.
3. **Adoption `bind_request_context` in `run_session`/`replay_session`**:
   try/finally wrapper. Tenant hardcoded `_DEFAULT_TENANT_ID = 1`
   (decisione Leader 5=a, TODO multi-tenant futuro). Sblocca
   correlazione log end-to-end: tutti gli eventi emessi a valle
   (`vgp.veto_roi_failed`, `tetris.skipped_budget`, ecc.) ereditano
   `request_id`/`tenant_id` via `merge_contextvars`.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/observability/logging_config.py` | modificato | + `bind_request_context(*, tenant_id, request_id=None) -> str` (genera UUID4 se None, ritorna l'id). + `clear_request_context()` (alias semantico di `clear_session_context`; entrambi pulistono i contextvars). + `import uuid`. Docstring estesa con pattern d'uso. |
| `src/talos/observability/__init__.py` | modificato | + re-export `bind_request_context` + `clear_request_context`. `__all__` esteso. |
| `src/talos/orchestrator.py` | modificato | `import logging` → `import structlog`. `_logger = structlog.get_logger(__name__)`. + costante `_DEFAULT_TENANT_ID: Final[int] = 1`. + import `bind_request_context`/`clear_request_context`. `run_session` + `replay_session` wrappati in `try/finally` con `bind_request_context(tenant_id=_DEFAULT_TENANT_ID)` all'ingresso, `clear_request_context()` in finally. Emit `session.replayed`: `extra={...}` → `**kwargs` native. |
| `tests/unit/test_replay_session_telemetry.py` | modificato | Migrato pytest `caplog` → `structlog.testing.LogCapture`. + 2 nuovi test sentinella ereditarietà context (`test_run_session_binds_request_context` verifica `request_id` UUID4 + `tenant_id=1` ereditati su `vgp.veto_roi_failed` emesso downstream; `test_run_session_clears_request_context_on_exit` verifica clear in finally + nuovo UUID al run successivo). 2 test esistenti riadattati. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **702 PASS** unit/gov/golden (+2 vs CHG-034: nuovi test sentinella).
- **138 PASS** integration (invariato).
- **840 PASS** totali.

Detect_changes: 4 file, 22 simboli touched, 1 processo affetto
(`Run_session → _resolve_referral_fee`, intra-community), **risk MEDIUM**
(behavior invariato — confermato da 138 integration live e2e).

`bind_session_context` (post-save) **NON** ancora chiamato in
orchestrator: scope CHG-B1.3 (UI dashboard `try_persist_session`).

## Why

Post-CHG-034 tutti i 12 siti emit applicativi consumano structlog
native + `merge_contextvars`. La fase B1.2 attiva il consumo del
context bind:

- **Correlazione log end-to-end**: tutti gli eventi emessi durante
  `run_session(inp)` (es. 100 ASIN listino → ~5 `vgp.veto_roi_failed`
  + 0..N `tetris.skipped_budget` + N `panchina.archived`) condividono
  lo stesso `request_id` UUID4. Filtrare un single user request
  diventa banale: `grep "request_id=<uuid>" logs.json`.
- **Multi-tenant prep**: `tenant_id` aggiunto a tutti gli eventi
  senza modificare i ~10 emit sites (oggi hardcoded 1, configurabile
  dopo provider).
- **Idempotency replay**: `replay_session` emette `session.replayed`
  con request_id distinto da `run_session` originale, anche se
  ricarica lo stesso listino — utile per audit "quanti scenari ha
  esplorato il CFO".

L'`orchestrator.py` era l'ultimo isolotto stdlib post-B1.1 (vedi
nota in CHG-034). Bridge + adoption nello stesso CHG perché:
- Bridge senza adoption = dead code (logger è native ma non binda).
- Adoption senza bridge = fallisce: `_logger.debug("evt", extra={...})`
  stdlib non vede contextvars structlog.
- Combinati = unit minima di valore deliverable.

### Decisioni di design

1. **`clear_request_context` come alias di `clear_session_context`**:
   `structlog.contextvars.clear_contextvars()` non è per-key, pulisce
   tutto. Tenere 2 funzioni con nome diverso ma stesso corpo è
   *intenzionale*: il caller "request-level" usa `clear_request_context`,
   il caller "session-only" (test storici) `clear_session_context`.
   Pattern simmetrico con `bind_*`. Backward compat 100% sul nome
   storico.

2. **`bind_request_context` ritorna `request_id`**: il caller può
   loggarlo subito (`_logger.info("session.started", request_id=rid)`)
   o passarlo a downstream callers che vogliono header HTTP. Pattern
   "Builder pattern minus mutability".

3. **`tenant_id` parametro keyword-only**: previene errori dell'ordine
   `(request_id, tenant_id)` vs `(tenant_id, request_id)`. Coerente
   con `bind_session_context`.

4. **`_DEFAULT_TENANT_ID = 1` costante locale orchestrator**: NON
   importata da `talos.config` (non esiste field `default_tenant_id`
   in `TalosSettings` oggi). Provider iniettato è scope multi-tenant
   futuro (commento esplicito).

5. **`run_session`/`replay_session` con try/finally wrapper**: pattern
   universale `bind → work → clear`. Lievemente verboso ma:
   - Non richiede context manager pythonic (non c'è bisogno di
     yielding intermedio).
   - `finally` esegue anche su exception → no leak in caso di errore.
   - Chiamabile in test mock-only senza fixture extra.

6. **Test sentinella ereditarietà context** (`test_run_session_binds_request_context`):
   verifica end-to-end del *contratto* — `merge_contextvars` propaga
   davvero il bind a moduli downstream. Senza questo test la pipeline
   era un "atto di fede". 1 test minimo, 1 invocazione reale di
   `run_session` con `veto_roi_threshold=0.50` per forzare emit
   `vgp.veto_roi_failed`.

7. **Test cleanup sentinella** (`test_run_session_clears_request_context_on_exit`):
   verifica che chiamate consecutive abbiano UUID distinti. Pattern:
   chiamo 2 volte `run_session(inp)`, verifico `rid_first != rid_second`.
   `log_capture.entries.clear()` fra le 2 chiamate per isolare i
   record del secondo run.

8. **`replay_session` emette `session.replayed` DENTRO il bind**:
   l'evento ha `request_id` distinto da `run_session` originale.
   Coerente con la decisione "ogni invocazione = 1 request".

9. **Detect_changes risk MEDIUM accettato**: `run_session` è il
   nodo del processo `Run_session → _resolve_referral_fee` (step
   1). GitNexus marca "touched" perché ho aggiunto wrapper try/finally
   intorno al corpo. Behavior invariato: i 702 unit + 138 integration
   con live e2e confermano.

### Out-of-scope

- **`bind_session_context` adoption in `dashboard.try_persist_session`**:
  scope CHG-B1.3. `session_id` è disponibile post-save, non in
  orchestrator.
- **Errata catalogo ADR-0021** (campi context-bound + pulizia
  `tenant_id` esplicito su `cache.hit/miss` + drift `serp_search`):
  scope CHG-B1.4.
- **Provider tenant configurable**: scope multi-tenant futuro.
- **`_logger.info("session.started/completed")` in run_session**:
  scope CHG futuro telemetria — il bind c'è già, basta `_logger.info`
  per attivare nuovi eventi canonici, ma servirebbe errata catalogo.

## How

### `logging_config.py` — split helper

```python
def bind_request_context(*, tenant_id: int, request_id: str | None = None) -> str:
    rid = request_id if request_id is not None else str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=rid, tenant_id=tenant_id)
    return rid


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()


def clear_session_context() -> None:  # alias backward compat
    structlog.contextvars.clear_contextvars()
```

### `orchestrator.py` — adoption pattern

```python
def run_session(inp: SessionInput) -> SessionResult:
    bind_request_context(tenant_id=_DEFAULT_TENANT_ID)
    try:
        # ... body invariato ...
    finally:
        clear_request_context()
```

Stesso pattern per `replay_session`.

### `test_replay_session_telemetry.py` — sentinella ereditarietà

```python
def test_run_session_binds_request_context(log_capture: LogCapture) -> None:
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=5000.0,
        veto_roi_threshold=0.50,  # forza veto, emette vgp.veto_roi_failed
    )
    run_session(inp)

    veto_entries = [e for e in log_capture.entries if e["event"] == "vgp.veto_roi_failed"]
    assert len(veto_entries) >= 1
    for entry in veto_entries:
        assert "request_id" in entry  # ereditato!
        assert entry["tenant_id"] == 1
        assert len(entry["request_id"]) == 36  # UUID4
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 138 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Replay + logging_config | `uv run pytest tests/unit/test_replay_session_telemetry.py tests/unit/test_logging_config.py -v` | **10 PASS** (4 replay + 6 logging_config) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **702 PASS** (era 700, +2 sentinella) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | `gitnexus_impact("run_session"/"replay_session", "upstream")` | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 22 symbols / 4 files, 1 processo affetto, **risk MEDIUM** |

**Rischi residui:**

- **Risk MEDIUM detect_changes**: `run_session` modifica strutturale
  (try/finally wrapper) ma comportamento invariato. 138 integration
  live e2e PASS confermano.
- **`clear_request_context()` pulisce TUTTO il context**: se in
  futuro un caller volesse fare bind annidati (es. `outer.run_session`
  con bind suo, poi inner `replay_session` con bind suo), `clear_request_context`
  in finally del replay pulirebbe anche il bind del run esterno.
  Mitigazione: non c'è uso annidato oggi (dashboard chiama 1 sola
  cosa a turno). Per la versione annidata serve `bind_contextvars(...)`
  + memorizzare il token di unbind (pattern structlog avanzato),
  scope CHG futuro se emerge necessità.
- **`tenant_id=1` hardcoded**: documentato + commentato + scope
  multi-tenant.
- **`session.replayed` campo `tenant_id` non più passato esplicito**:
  ora ereditato dal bind. Pre-CHG: nessun `tenant_id` su
  `session.replayed`. Post-CHG: presente come ereditato. Cambiamento
  *additivo* sul payload finale (non breaking). Documentato in
  errata catalogo CHG-B1.4.
- **Side-effect cross-test fixture**: validato cumulativamente fino
  a CHG-035. La pulizia `structlog.contextvars.clear_contextvars()`
  in fixture log_capture non è esplicita, ma il bind è
  sovrascritto al primo `bind_request_context` del test successivo.
  Validazione empirica: 702/702 + 138/138 verde.

## Test di Conformità

- **Path codice applicativo:** `src/talos/observability/`,
  `src/talos/orchestrator.py` ✓ (aree ADR-0013).
- **ADR-0021 esteso**: il bind helper era già descritto nel
  modulo (CHG-006 + errata 058). Estendere con `bind_request_context`
  è naturale completamento, non novità di scope.
- **ADR-0018 invariato**: orchestrator algoritmo invariato (R-04..R-09).
- **ADR-0019 (test strategy)**: unit puri ✓ + sentinella mock-only.
- **Quality gate verde** (ADR-0014).
- **No nuovi simboli applicativi non testati**: `bind_request_context`
  testato indirettamente via sentinella + `run_session`. Test
  diretti del helper isolato (es. UUID generato vs passato esplicito)
  scope CHG futuro se emerge bug.
- **Backward compat semantica**: `bind_session_context` /
  `clear_session_context` invariati nel signature e behavior.
  `_logger.debug("session.replayed", **kwargs)` produce stesso
  payload di `extra={...}` (a meno del bonus contextvars ereditati).
- **Sicurezza**: zero secrets/PII; UUID4 standard library Python.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 22 simboli, 1 processo, risk
  MEDIUM (giustificato).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
  L'aggiunta dei campi context-bound `request_id`/`tenant_id` è
  errata additiva — scope CHG-B1.4 (formalizzazione catalogo +
  rimozione `tenant_id` esplicito da `cache.hit/miss`).
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps; `uuid` è stdlib).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
  Errata B1.4 estenderà i campi obbligatori con `request_id`/`tenant_id`
  context-bound.
- **Test suite +2**: 702 unit/gov/golden (era 700) + 138 integration
  = 840 PASS.
- **Tutti i 17 eventi canonici emessi durante un `run_session`**
  ora portano `request_id` + `tenant_id`. La correlazione log
  end-to-end è funzionale.
- **Sblocca CHG-B1.3**: `dashboard.try_persist_session` può chiamare
  `bind_session_context(session_id=saved_id, ...)` post-save per
  arricchire il contesto. Scope esplicito.
- **Sblocca CHG-B1.4**: errata catalogo formalizza i campi
  context-bound; pulizia `tenant_id` esplicito da `cache.hit/miss`
  (ora ridondante).
- **Code health**: -1 isolotto stdlib (orchestrator). Pattern
  uniforme su tutti i moduli applicativi. Sentinella ereditarietà
  attiva.

## Refs

- ADR: ADR-0021 (logging/telemetria), ADR-0018 (orchestrator
  algoritmo invariato), ADR-0014 (mypy/ruff strict), ADR-0019
  (test strategy).
- Predecessori:
  - CHG-2026-04-30-006 (configure_logging structlog +
    `bind_session_context` originale).
  - CHG-2026-04-30-039 (orchestrator.py inaugurazione).
  - CHG-2026-04-30-058 (errata `session.replayed` catalogo).
  - CHG-2026-05-01-030..034 (B1.1.a..e bridge cluster).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1, ratificate):
  3=a (split bind helper), 5=a (tenant_id hardcoded 1).
- Successore atteso: **CHG-B1.3** (adoption UI bind context —
  `try_persist_session` con `bind_session_context` post-save).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: PENDING.
