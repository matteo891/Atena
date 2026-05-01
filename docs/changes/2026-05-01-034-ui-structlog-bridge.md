---
id: CHG-2026-05-01-034
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 6 — blocco B1 sessione dedicata 5/8 — chiude fase B1.1)
status: Draft
commit: PENDING
adr_ref: ADR-0021, ADR-0016, ADR-0014, ADR-0019
---

## What

**Bridge stdlib→structlog del cluster `ui/`** (5/5 fase B1.1 —
**chiude la fase B1.1**). Migra i 2 file applicativi del cluster:
`dashboard.py` (4 emit canonici UI) e `listino_input.py` (2 emit
cache). Migra i 2 test telemetria correlati a `LogCapture`.

**Pattern uniforme post-bridge raggiunto su tutti i 5 cluster
applicativi `vgp` / `tetris` / `io_` / `extract` / `ui`**: i 12
siti emit ora consumano `merge_contextvars` di `configure_logging`,
sbloccando l'adoption di `bind_session_context` (CHG-B1.2).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | `import logging` → `import structlog`. `_logger = logging.getLogger(__name__)` → `_logger = structlog.get_logger(__name__)`. 4 emit `ui.resolve_started` / `ui.resolve_confirmed` / `ui.override_applied` / `ui.resolve_failed`: `extra={...}` → `**kwargs` native. |
| `src/talos/ui/listino_input.py` | modificato | Stesso pattern. 2 emit `cache.hit` / `cache.miss`: `extra={...}` → `**kwargs`. |
| `tests/unit/test_dashboard_telemetry_resolve.py` | modificato | Migrato pytest `caplog` → `LogCapture` (consumer fixture conftest CHG-031). 9 test invariati semanticamente (8 caplog migrati + 1 verifica catalogo invariato). Type-ignore `attr-defined` rimossi. |
| `tests/unit/test_listino_input_cache_telemetry.py` | modificato | Stesso pattern. 5 test (4 caplog migrati + 1 verifica catalogo). |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **700 PASS** unit/gov/golden (invariato).
- **138 PASS** integration (invariato).
- **838 PASS** totali.

Detect_changes: 5 file, 20 simboli touched, **0 processi affetti**,
**risk LOW**.

Comportamento applicativo invariato 100%: stessi 6 eventi canonici
(`ui.resolve_started`/`_confirmed`/`override_applied`/`_failed` +
`cache.hit`/`miss`) con stessi campi.

## Why

`ui/` è il 5° e ultimo cluster applicativo della fase B1.1
(decisione Leader 1=B progressivo per area). Dopo CHG-034 tutti
i 12 siti emit applicativi consumano `structlog.contextvars.merge_contextvars`
(processor configurato in `configure_logging`, CHG-006), e
`bind_session_context` smette di essere "morto in produzione".

`ui/` ha il maggior numero di emit per cluster (6 emit su 2 file,
vs 1-5 emit per gli altri cluster) ma il refactor è meccanico: 4
helper `_emit_ui_*` in `dashboard.py` + 2 helper `_emit_cache_*`
in `listino_input.py` sono già astratti e testabili — il bridge
si limita a sostituire l'init + i kwargs, gli helper restano
invariati nella firma.

I 2 test sono i più "ricchi" della suite telemetria:
- `test_dashboard_telemetry_resolve.py`: 9 test (4 helper × 2
  varianti per ognuno + 1 catalogo).
- `test_listino_input_cache_telemetry.py`: 5 test (2 helper × 2
  varianti + 1 catalogo).

### Decisioni di design

1. **Helper `_emit_*` invariati nella firma**: tutti rimangono
   `def _emit_*(*, ...) -> None`. Cambia solo l'API del logger
   sottostante. Caller in `dashboard.py` invariati 100%.

2. **`test_canonical_events_catalog_contains_*` invariati**:
   verificano `CANONICAL_EVENTS` dict + costanti `EVENT_*` —
   non usano caplog/LogCapture. Lasciati identici.

3. **`hasattr(record, "asin")` rimossi nei test**: pattern dict
   structlog non usa attribute access. I test ora fanno
   `entry["table"]` direttamente: solleva `KeyError` se il campo
   manca, più strict.

4. **Side-effect cross-test validato cumulativamente**: la fixture
   `log_capture` riconfigura structlog globalmente. Validato
   cross-test in CHG-030/031/032/033/034. La suite full
   (700+138 verde) è la prova empirica che zero regressione
   cross-file.

5. **`test_replay_session_telemetry.py` NON toccato**: questo
   test usa caplog stdlib su `session.replayed` emesso da
   `orchestrator.py` (riga 412). `orchestrator.py` è ancora
   stdlib (sarà migrato in CHG-B1.2). Stato transitorio noto:
   l'orchestrator è l'ultimo "isolotto" stdlib post-CHG-034,
   migrato come parte di B1.2 con adoption del bind context.

6. **Detect_changes risk LOW**: i 4 helper `_emit_ui_*` non sono
   nodi di processi GitNexus — sono helper puri. Refactor
   isolato, comportamento invariato, **0 processi affetti**.

7. **`tenant_id` in `cache.hit/miss` mantenuto come campo
   esplicito**: drift da pulire in CHG-B1.4 (campi context-bound).
   Bridge preserva esattamente il pattern attuale: il campo è
   ancora passato al logger come kwarg, sarà l'errata B1.4 a
   marcarlo come ereditato e a rimuoverlo dal contratto del
   catalogo.

### Out-of-scope

- **Adoption `bind_session_context` in `dashboard.py`**: scope
  CHG-B1.3 (split helper + bind in flow descrizione+prezzo).
- **Bridge `orchestrator.py`**: scope CHG-B1.2 (insieme
  all'adoption del bind, ultimo file applicativo stdlib).
- **Errata catalogo**: scope CHG-B1.4 (drift `serp_search` field
  names + pulizia `tenant_id` context-bound + estensione
  `_EXPECTED_EVENTS` snapshot).
- **Pulizia `tenant_id` esplicito su `cache.hit/miss`**: scope
  CHG-B1.4.

## How

### `dashboard.py` (highlight diff per ognuno dei 4 emit)

```diff
 def _emit_ui_resolve_started(*, n_rows: int, has_factory: bool) -> None:
-    _logger.debug("ui.resolve_started", extra={"n_rows": n_rows, "has_factory": has_factory})
+    _logger.debug("ui.resolve_started", n_rows=n_rows, has_factory=has_factory)
```

### `listino_input.py` (highlight diff)

```diff
 def _emit_cache_hit(*, table: str, tenant_id: int) -> None:
-    _logger.debug("cache.hit", extra={"table": table, "tenant_id": tenant_id})
+    _logger.debug("cache.hit", table=table, tenant_id=tenant_id)
```

### Test migration (highlight)

```python
def test_resolve_started_emits_canonical_event(log_capture: LogCapture) -> None:
    _emit_ui_resolve_started(n_rows=12, has_factory=True)

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_STARTED]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["n_rows"] == 12
    assert entry["has_factory"] is True
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 138 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria mirata | `uv run pytest tests/unit/test_dashboard_telemetry_resolve.py tests/unit/test_listino_input_cache_telemetry.py -v` | **14 PASS** |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **700 PASS** (invariato) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (4 helper `_emit_*` sondati; tutti puri) | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 20 symbols / 5 files, 0 processes affected, **risk LOW** |

**Rischi residui:**

- **`test_replay_session_telemetry.py` ancora caplog**: sentinel
  ricognoscibile dell'isolotto orchestrator stdlib pre-B1.2.
  Atteso, documentato.

- **`tenant_id` esplicito su cache.hit/miss**: drift catalogo da
  pulire in B1.4. Pre-esistente da CHG-025, non scope B1.1.e.

- **Side-effect cross-test fixture**: validato cumulativamente
  attraverso 5 CHG B1.1.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area ADR-0013
  consentita; ADR-0016 governa).
- **ADR-0016 vincoli rispettati**: helper `_emit_*` puri,
  testabili senza Streamlit. Pattern Streamlit downstream invariato.
- **ADR-0021**: structlog libreria canonica.
- **ADR-0019 (test strategy)**: unit puri ✓, mock-only.
- **Quality gate verde**: ruff/format/mypy/pytest tutti pass
  (ADR-0014).
- **No nuovi simboli applicativi**: solo refactor.
- **Backward compat semantica**: invariata 100%.
- **Sicurezza**: zero secrets/PII; no nuove deps.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 20 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**: refactor
  mirato + 0 test nuovi (riusati gli esistenti) + change doc snello.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite invariata in conteggio**: 838 PASS.
- **Chiude fase B1.1**: 12/12 siti emit applicativi ora consumano
  structlog native + `merge_contextvars`. `bind_session_context`
  pronta a propagare context su tutti i 16 eventi catalogo (17
  totali; `extract.kill_switch`/`session.replayed` ancora caplog
  per ragioni elencate sopra; `db.audit_log_write` non emesso da
  Python — è il trigger Postgres).
- **Sblocca CHG-B1.2**: split `bind_session_context` →
  `bind_request_context` + `bind_session_context`, adoption in
  `orchestrator.run_session()` con try/finally + bridge
  `orchestrator.py` stesso (ultimo isolotto stdlib).
- **Code health**: -8 type-ignore `attr-defined` (test dict-style
  ui). +0 nuovi file (refactor in-place). Pattern uniforme su 5
  cluster applicativi.

## Refs

- ADR: ADR-0021 (logging/telemetria), ADR-0016 (UI Streamlit),
  ADR-0014 (mypy/ruff strict), ADR-0019 (test strategy).
- Predecessori:
  - CHG-2026-04-30-006 (configure_logging structlog).
  - CHG-2026-05-01-021 (telemetria UI ui.resolve_*).
  - CHG-2026-05-01-024 (errata UI ui.override_applied/_failed).
  - CHG-2026-05-01-025 (telemetria cache.hit/miss).
  - CHG-2026-05-01-030..033 (B1.1.a vgp / B1.1.b tetris / B1.1.c
    io_ / B1.1.d extract).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1).
- Successore atteso: **CHG-B1.2** (split helper + adoption
  orchestrator).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: PENDING.
