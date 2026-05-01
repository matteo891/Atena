---
id: CHG-2026-05-01-036
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 6 — blocco B1 sessione dedicata 7/8)
status: Draft
commit: PENDING
adr_ref: ADR-0021, ADR-0016, ADR-0014, ADR-0019
---

## What

**B1.3: adoption UI bind context** + **idempotenza nesting di
`bind_request_context`** (scoperta architetturale a-posteriori di
B1.2). Tre interventi:

1. **Idempotenza nesting `bind_request_context`** + helper introspettivo
   `is_request_context_bound()`. Pattern: bind annidato riusa il
   `request_id` esistente invece di sovrascriverlo. Indispensabile
   per consentire che `dashboard._render_descrizione_prezzo_flow`
   binda all'ingresso e poi `run_session` (chiamato dal flow) NON
   resetti il bind UI.
2. **Pattern `is_outer` in `orchestrator`**: `run_session` /
   `replay_session` chiamano `clear_request_context()` in finally
   **solo se** sono i bind originator (cioè se non c'era bind
   preesistente). Senza questo, il clear orchestrator cancellava il
   bind UI esterno.
3. **Adoption in `dashboard`**:
   - `_render_descrizione_prezzo_flow` wrappa il body in
     `bind_request_context(tenant_id=DEFAULT_TENANT_ID)` +
     `clear_request_context()` finally (con pattern `is_outer` per
     nesting da test futuri).
   - `try_persist_session` post-save chiama `bind_session_context`
     per arricchire il context con `session_id` + `listino_hash`
     reali (eventi successivi nello stesso rerun ereditano).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/observability/logging_config.py` | modificato | `bind_request_context` ora idempotente: se `request_id` già binded, riusa. + helper `is_request_context_bound() -> bool`. Docstring estesa con pattern `is_outer`. |
| `src/talos/observability/__init__.py` | modificato | + re-export `is_request_context_bound`. `__all__` esteso. |
| `src/talos/orchestrator.py` | modificato | `run_session` + `replay_session`: pattern `is_outer = not is_request_context_bound()`; `clear_request_context()` chiamato solo se `is_outer`. Bind resta idempotente (no sovrascrittura). |
| `src/talos/ui/dashboard.py` | modificato | + import 4 helper observability. Wrap `_render_descrizione_prezzo_flow` in `bind/clear` (pattern `is_outer`); body estratto in `_render_descrizione_prezzo_flow_body` (no logica modificata). `try_persist_session` post-save chiama `bind_session_context` con `_listino_hash(listino_raw)`. |
| `tests/unit/test_dashboard_telemetry_resolve.py` | modificato | + 2 test sentinella: `test_ui_emit_inherits_request_context_when_bound` (UI emit ereditano context durante bind) + `test_bind_request_context_idempotent_nesting` (bind annidato riusa request_id, tenant_id originale conservato). |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **704 PASS** unit/gov/golden (era 702, +2 sentinella nesting).
- **138 PASS** integration (invariato).
- **842 PASS** totali.

Detect_changes: 6 file, 12 simboli touched, 1 processo affetto
(`Run_session → _resolve_referral_fee`), **risk MEDIUM**.

## Why

Post-B1.2 il bind context era operativo nell'orchestrator MA con un
limite di nesting: ogni `bind_request_context` sovrascriveva, e
`clear_request_context()` in finally cancellava ANCHE il bind del
caller esterno. Conseguenza pratica:

- Dashboard binda → emit `ui.resolve_started` con request_id-A
- Dashboard chiama `run_session(inp)` → orchestrator binda → request_id-B
  sovrascrive A
- Orchestrator esce, `clear_request_context()` svuota tutto
- Dashboard continua dopo run_session → nessun context attivo
- Successivi `_emit_ui_resolve_confirmed` / `cache.hit` NON hanno
  request_id

L'**idempotenza** + il **pattern `is_outer`** risolvono questo
problema *senza* dover cambiare la firma dei caller annidati. Ogni
livello chiama `bind_request_context(tenant_id=...)` + try/finally
con clear-only-if-outer; il caller più esterno (UI) è automaticamente
riconosciuto come "originator" e gestisce il clear finale.

`try_persist_session` post-save bind `session_id` + `listino_hash`:
arricchisce il context per gli eventi emessi DOPO save (oggi nessun
emit, ma è preparatorio per CHG futuri tipo `session.persisted` o
`session.duplicate_detected`). Costo minimo, valore architetturale
chiaro.

### Decisioni di design

1. **`bind_request_context` idempotente, non eccezione**: se già
   binded, ritorna l'id esistente. Pattern accommodante per nesting
   "nudo" (caller annidato non deve sapere se è outer o no, basta
   chiamare).

2. **`tenant_id` del nested call ignorato in caso di bind esistente**:
   il caller più esterno fissa il tenant. Test sentinella
   `test_bind_request_context_idempotent_nesting` lo verifica
   esplicitamente (`tenant_id=99` nel nested → resta `tenant_id=1`
   dell'outer). Decisione coerente con la semantica "request-level"
   del bind.

3. **`is_request_context_bound()` come helper introspettivo
   pubblico**: necessario per il pattern `is_outer`. Esposto in
   `talos.observability.__all__` + re-export.

4. **Pattern `is_outer` orchestrator e UI**: identico, replicabile.
   Documentato in docstring `bind_request_context`. Estendibile a
   futuri caller annidati (es. CLI, batch script).

5. **`_render_descrizione_prezzo_flow` body extraction**: il flow
   originale aveva ~280 righe. Wrap try/finally inline avrebbe reso
   illeggibile la struttura. Ho creato `_render_descrizione_prezzo_flow_body`
   con la firma identica + comportamento identico; il wrapper
   esterno è solo bind/clear. Il `# noqa: C901, ...` resta sul body
   (complessità reale).

6. **`try_persist_session` NON ha try/finally con clear**: il bind
   `session_id` viene fatto solo nel success path; il context
   sopravvive al return e finisce il proprio ciclo quando il flow
   chiama `clear_request_context()` o quando Streamlit re-runna lo
   script (re-init contextvars). Pattern intenzionale: post-save
   è un "punto di arricchimento", non un nuovo scope.

7. **Test sentinella minimi (2)**: 1 per ereditarietà context, 1
   per idempotenza nesting. Coprono il contratto comportamentale
   nuovo. Test mock-only, no DB, no Streamlit (gli helper `_emit_*`
   sono già puri).

8. **`bind_session_context` a `try_persist_session` non testato in
   isolamento**: richiederebbe mock DB factory + verify del bind
   post-save via context inspection. Marginale: `bind_session_context`
   è già coperto in `test_logging_config.py:test_session_context_propagates`.
   Test specifico `try_persist_session.bind` = scope CHG futuro se
   emerge bug.

9. **Detect_changes risk MEDIUM accettato**: `run_session` modificato
   strutturalmente (pattern is_outer). Comportamento invariato
   confermato da 702 unit + 138 integration; risk MEDIUM è
   "abbiamo toccato un nodo di processo", non "abbiamo rotto".

### Out-of-scope

- **Errata catalogo ADR-0021** (formalizzazione campi context-bound,
  pulizia `tenant_id` esplicito da `cache.hit/miss`, drift
  `serp_search` field names): scope CHG-B1.4.
- **Bind in altri rendering (`_render_loaded_session_detail`)**:
  scope CHG futuro se emerge necessità. Oggi il flow loaded usa
  già `try_replay_session` che eredita il bind orchestrator.
- **Test integration `try_persist_session.bind`**: vedi decisione 8.

## How

### `logging_config.py` (highlight)

```python
def bind_request_context(*, tenant_id: int, request_id: str | None = None) -> str:
    existing = structlog.contextvars.get_contextvars()
    if "request_id" in existing:
        return str(existing["request_id"])  # nesting: rispetta il bind esistente
    rid = request_id if request_id is not None else str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=rid, tenant_id=tenant_id)
    return rid


def is_request_context_bound() -> bool:
    return "request_id" in structlog.contextvars.get_contextvars()
```

### `orchestrator.py` (highlight pattern)

```python
def run_session(inp: SessionInput) -> SessionResult:
    is_outer = not is_request_context_bound()
    bind_request_context(tenant_id=_DEFAULT_TENANT_ID)
    try:
        # ... body invariato ...
    finally:
        if is_outer:
            clear_request_context()
```

Stesso pattern in `replay_session`.

### `dashboard.py` (highlight)

```python
def _render_descrizione_prezzo_flow(factory):
    is_outer = not is_request_context_bound()
    bind_request_context(tenant_id=DEFAULT_TENANT_ID)
    try:
        return _render_descrizione_prezzo_flow_body(factory)
    finally:
        if is_outer:
            clear_request_context()


def _render_descrizione_prezzo_flow_body(factory):
    # ... body originale invariato ...


def try_persist_session(factory, *, session_input, result, tenant_id=DEFAULT_TENANT_ID):
    try:
        with session_scope(factory) as db_session:
            sid = save_session_result(...)
    except Exception as exc:
        return False, None, str(exc)
    bind_session_context(
        session_id=sid,
        listino_hash=_listino_hash(session_input.listino_raw),
        velocity_target=session_input.velocity_target_days,
        budget_eur=session_input.budget,
    )
    return True, sid, None
```

### Test sentinella (highlight)

```python
def test_bind_request_context_idempotent_nesting(log_capture):
    assert not is_request_context_bound()
    rid_outer = bind_request_context(tenant_id=1)
    try:
        rid_inner = bind_request_context(tenant_id=99)  # tenant_id ignorato
        assert rid_inner == rid_outer
        _emit_ui_resolve_started(n_rows=1, has_factory=False)
    finally:
        clear_request_context()
    assert not is_request_context_bound()

    entries = [e for e in log_capture.entries if e["event"] == EVENT_UI_RESOLVE_STARTED]
    assert entries[0]["tenant_id"] == 1  # tenant_id originale, non sovrascritto
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed (1 fixable autofixed: PLC0415 import) |
| Format | `uv run ruff format src/ tests/` | 138 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Sentinelle context | `uv run pytest tests/unit/test_dashboard_telemetry_resolve.py tests/unit/test_replay_session_telemetry.py -v` | **15 PASS** (11 dashboard + 4 replay) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **704 PASS** (era 702, +2 sentinella nesting) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (helper observability + run_session) | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 12 symbols / 6 files, 1 processo affetto, **risk MEDIUM** |

**Rischi residui:**

- **Risk MEDIUM detect_changes**: `run_session` modificato strutturalmente
  (pattern `is_outer`); behavior invariato confermato da 138
  integration live e2e PASS. `try_persist_session` ha 2 nuove righe
  (bind post-save), zero blast radius downstream.
- **Streamlit re-run**: ogni rerun re-inizializza contextvars (Python
  contextvars sono per-thread; Streamlit ricrea lo script execution).
  Il bind dura 1 rerun. Per tracking inter-rerun servirebbe
  `st.session_state` — scope CHG futuro.
- **`tenant_id=99` in nested ignorato**: comportamento *intenzionale*
  (decisione 2). Se il caller annidato volesse forzare un tenant
  diverso, dovrebbe `clear_request_context()` prima e ri-bind. Pattern
  pesante ma intenzionale: il tenant è proprietà del caller più
  esterno.
- **`try_persist_session.bind` non testato in isolamento**: marginale
  (vedi decisione 8).

## Test di Conformità

- **Path codice applicativo:** `src/talos/observability/`,
  `src/talos/orchestrator.py`, `src/talos/ui/dashboard.py` ✓ (aree
  ADR-0013).
- **ADR-0021**: estensione naturale del bind helper.
- **ADR-0018 invariato**: orchestrator algoritmo invariato.
- **ADR-0016 (UI Streamlit)**: helper extraction (`_render_*_flow_body`)
  preserva `# noqa: C901, ...` complessità reale.
- **ADR-0019 (test strategy)**: sentinelle mock-only ✓.
- **Quality gate verde** (ADR-0014).
- **No nuovi simboli applicativi non testati**: `is_request_context_bound`
  testato indirettamente via test nesting + sentinella ereditarietà.
- **Backward compat semantica**: invariata 100% sui test esistenti
  (15 PASS dashboard+replay vs 13 pre-CHG; +2 sentinella nuovi).
- **Sicurezza**: zero secrets/PII; UUID4 standard library Python.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 12 simboli, 1 processo, risk
  MEDIUM (giustificato).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
  Errata B1.4 formalizzerà i campi context-bound.
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +2**: 704 unit/gov/golden (era 702) + 138 integration
  = 842 PASS.
- **Tutti i 12+ siti emit applicativi** ora capaci di ereditare
  `request_id`/`tenant_id` quando un caller esterno (UI, orchestrator,
  CLI futuro) binda. Pattern `is_outer` consente nesting senza
  conflitto.
- **`try_persist_session` post-save bind**: prepara il context per
  futuri eventi `session.persisted` / `session.duplicate_detected`
  con `session_id` + `listino_hash` ereditati.
- **Sblocca CHG-B1.4**: errata catalogo ADR-0021 può ora formalizzare
  i campi context-bound (`request_id`/`tenant_id`/`session_id`/
  `listino_hash`) come ereditati, e pulire `tenant_id` esplicito da
  `cache.hit/miss` (oggi ridondante).
- **Code health**: pattern di adoption end-to-end (UI → orchestrator
  → emit cluster) ora completo e testato. Sentinella nesting blinda
  il contratto.

## Refs

- ADR: ADR-0021 (logging/telemetria), ADR-0016 (UI Streamlit), ADR-0014
  (mypy/ruff strict), ADR-0019 (test strategy).
- Predecessori:
  - CHG-2026-04-30-006 (configure_logging structlog).
  - CHG-2026-05-01-035 (B1.2 split helper + adoption orchestrator).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1, ratificate):
  2=a (request_id+session_id distinti), 3=a (split helper).
- Successore atteso: **CHG-B1.4** (errata catalogo ADR-0021 + pulizia
  `tenant_id` esplicito).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: PENDING.
