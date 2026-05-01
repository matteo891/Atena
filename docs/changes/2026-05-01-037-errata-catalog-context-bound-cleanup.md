---
id: CHG-2026-05-01-037
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 6 — blocco B1 sessione dedicata 8/8 — CHIUDE BLOCCO B1)
status: Draft
commit: 14a408b
adr_ref: ADR-0021, ADR-0009, ADR-0014, ADR-0019
---

## What

**B1.4: errata catalogo ADR-0021 + pulizia `tenant_id` esplicito +
fix drift `serp_search`. CHIUDE BLOCCO B1.** Quattro interventi
coordinati che formalizzano lo stato architetturale post B1.1+B1.2+B1.3:

1. **Errata ADR-0021** (sezione `## Errata`): formalizza i **4 campi
   context-bound** (`request_id`, `tenant_id`, `session_id`,
   `listino_hash`), elencando per ognuno chi binda + quando. Documenta
   pattern `is_outer` per nesting + esistenza dei 4 helper observability.
2. **`CANONICAL_EVENTS` aggiornato**: tupla `cache.hit/miss` ridotta da
   `("table", "tenant_id")` a `("table",)`. `tenant_id` rimosso perché
   ora ereditato dal bind UI.
3. **Pulizia callsite cache**: `_emit_cache_hit`/`_emit_cache_miss`
   rimuovono il parametro `tenant_id` dalla firma. `resolve_listino_with_cache`
   smette di passarlo. Comportamento esterno invariato (tenant_id
   resta nel payload finale degli eventi via context-bind).
4. **Fix drift pre-esistente `io_/serp_search.py:scrape.selector_fail`**:
   campi non-canonici `field`/`selectors_tried` → canonici
   `selector_name`/`html_snippet_hash` (drift da CHG-005, sanato qui
   perché lo scope B1 ha richiesto verifica catalogo).

| File | Tipo | Cosa |
|---|---|---|
| `docs/decisions/ADR-0021-logging-telemetria.md` | modificato | Sezione `## Errata` estesa con voce CHG-2026-05-01-035 + 036 + 037 — 4 sotto-sezioni: bind helpers, campi context-bound (tabella), adozione (orchestrator + UI), pulizia drift. Catalogo resta a 17 voci. |
| `src/talos/observability/events.py` | modificato | `CANONICAL_EVENTS["cache.hit"]` + `["cache.miss"]`: tupla da `("table", "tenant_id")` → `("table",)`. Docstring file estesa con sezione "Campi context-bound". |
| `src/talos/ui/listino_input.py` | modificato | `_emit_cache_hit/_emit_cache_miss`: parametro `tenant_id: int` rimosso dalla firma. `resolve_listino_with_cache` callsite smette di passarlo. Docstring helper aggiornata. |
| `src/talos/io_/serp_search.py` | modificato | `_parse_serp_payload` emit `scrape.selector_fail`: `field=` → `selector_name=`, `selectors_tried=[...]` → `html_snippet_hash="<no-html>"`. Drift pre-esistente da CHG-005 sanato. |
| `tests/unit/test_listino_input_cache_telemetry.py` | modificato | 4 test esistenti aggiornati: chiamano `_emit_cache_hit/miss(table=...)` senza `tenant_id`, bind manuale via `bind_request_context(tenant_id=...)` + try/finally + clear. + 1 test nuovo `test_cache_emit_without_bind_omits_tenant_id` (sentinel: senza bind, evento ha solo `table` — comportamento atteso post-B1.4). + asserzione catalogo aggiornata. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **705 PASS** unit/gov/golden (era 704, +1 sentinel cache senza bind).
- **138 PASS** integration (invariato).
- **843 PASS** totali.

Detect_changes: 7 file, 24 simboli touched, **0 processi affetti**,
**risk LOW**.

## Why

Il blocco B1 era stato pensato in 4 fasi (B1.1 bridge + B1.2
infrastruttura + B1.3 adoption UI + B1.4 cleanup). B1.4 chiude
formalmente il blocco con 3 atti necessari ma minori:

- **Documentale**: senza errata ADR-0021, il concetto di "campi
  context-bound" non avrebbe ancoraggio canonico. CHG-035/036
  l'hanno introdotto operativamente ma il concetto vive solo nei
  commit message + change docs. L'errata lo eleva al livello ADR
  (memoria istituzionale).

- **Coerenza catalogo**: `cache.hit/miss` con `tenant_id` esplicito
  è ora *drift* del catalogo rispetto al codice (post-B1.3 il
  `tenant_id` viene passato esplicito MA è anche ereditato dal
  bind, doppio bind risulterebbe in `tenant_id=1` ridondante con
  bind dashboard). Pulizia rimuove la duplicazione + chiude il
  drift.

- **Drift `serp_search`**: pre-esistente da CHG-005, identificato
  in CHG-032 ma deferred. Lo scope B1 ha richiesto verifica del
  catalogo end-to-end → era il momento giusto per sanare. 1 emit,
  3 campi, scope minimo.

### Decisioni di design

1. **Errata additiva (ADR-0009)**: pattern coerente con tutte le
   precedenti errata di ADR-0021 (CHG-058/021/024/025). Una nuova
   sotto-sezione `**2026-05-01 (CHG-035 + 036 + 037)**` raggruppa
   logicamente i 3 CHG del blocco B1 finale. Modifica additiva, non
   altera la semantica esistente — non richiede supersessione
   (regola ADR-0001 non si applica).

2. **Tupla `("table",)` invece di `()`**: `cache.hit` ha sempre
   almeno 1 campo event-specific. Rimuovere tutti porterebbe a tupla
   vuota, semanticamente "no campi obbligatori" — è errato perché
   `table` resta obbligatorio. La scelta `("table",)` riflette
   correttamente il contratto residuo.

3. **Pulizia callsite OBBLIGATORIA**: lasciare `tenant_id=tenant_id`
   nel callsite con la nuova firma del helper avrebbe causato
   `TypeError`. Quindi il refactor del callsite è side-effect
   necessario, non opzionale.

4. **`_emit_cache_*` helper signature breaking change**: i callsite
   esterni (oggi solo `resolve_listino_with_cache`) sono interni
   al package `talos.ui`. Test esistenti aggiornati nello stesso
   CHG. Nessun caller cliente esterno (è codice interno).

5. **Drift `serp_search`**: 3 campi (`field` → `selector_name`,
   `selectors_tried` → `html_snippet_hash`). `selectors_tried` era
   `list[str]`; `html_snippet_hash` è `str`. Decisione: hardcoded
   `"<no-html>"` (coerente con `scraper.py:_resolve_field` che usa
   lo stesso placeholder per non aggiungere overhead di hashing).

6. **Sentinel "senza bind, no tenant_id"** (`test_cache_emit_without_bind_omits_tenant_id`):
   blinda il contratto post-B1.4. Se in futuro qualcuno ri-aggiunge
   `tenant_id=` al kwargs di `_emit_cache_hit` (regressione), il
   test rompe esplicitamente. Pattern "lock the new contract".

7. **Tutti gli helper `_emit_cache_*` test bindano manualmente**:
   senza bind, gli eventi hanno solo `table` (ereditarietà NON attiva).
   Pattern per testare "in scope UI": bind+try/clear. Side-effect
   pulito test-side, nessun leak fra test grazie a `clear_request_context`
   in finally.

8. **Errata ADR documenta i 4 campi context-bound in tabella**:
   discoverable + scopable. Future estensioni del set (es.
   `correlation_id`, `user_id`) si aggiungono additivamente.

9. **Detect_changes risk LOW**: 0 processi affetti. La modifica è
   "infrastrutturale + cleanup", il behavior osservabile è
   invariato (stesso payload finale degli eventi).

### Out-of-scope

- **Provider tenant configurabile**: scope multi-tenant futuro.
- **Aggiunta nuovi eventi**: nessuno. B1 è "infrastruttura context",
  non aggiunta semantica.
- **Test integration sui campi context-bound end-to-end**: già
  coperti in CHG-035/036 (sentinella ereditarietà).

## How

### `events.py` (highlight diff)

```diff
-    "cache.hit": ("table", "tenant_id"),
-    "cache.miss": ("table", "tenant_id"),
+    # CHG-2026-05-01-037 (B1.4): tenant_id rimosso dalla tupla — ora ereditato
+    # dal bind UI (`bind_request_context(tenant_id=DEFAULT_TENANT_ID)` in
+    # `_render_descrizione_prezzo_flow`).
+    "cache.hit": ("table",),
+    "cache.miss": ("table",),
```

### `listino_input.py` (highlight diff)

```diff
-def _emit_cache_hit(*, table: str, tenant_id: int) -> None:
-    _logger.debug("cache.hit", table=table, tenant_id=tenant_id)
+def _emit_cache_hit(*, table: str) -> None:
+    _logger.debug("cache.hit", table=table)

 # callsite:
-_emit_cache_hit(table=_CACHE_TABLE_DESCRIPTION_RESOLUTIONS, tenant_id=tenant_id)
+_emit_cache_hit(table=_CACHE_TABLE_DESCRIPTION_RESOLUTIONS)
```

### `serp_search.py` (highlight diff)

```diff
-_logger.debug(
-    "scrape.selector_fail",
-    asin="<serp>",
-    field="serp_payload",
-    selectors_tried=["data-component-type=s-search-result"],
-)
+_logger.debug(
+    "scrape.selector_fail",
+    asin="<serp>",
+    selector_name="serp_payload",
+    html_snippet_hash="<no-html>",
+)
```

### Test sentinella (highlight)

```python
def test_cache_hit_emits_canonical_event(log_capture):
    bind_request_context(tenant_id=1)
    try:
        _emit_cache_hit(table="description_resolutions")
    finally:
        clear_request_context()

    entries = [e for e in log_capture.entries if e["event"] == EVENT_CACHE_HIT]
    assert entries[0]["table"] == "description_resolutions"
    assert entries[0]["tenant_id"] == 1  # ereditato dal bind, non kwarg


def test_cache_emit_without_bind_omits_tenant_id(log_capture):
    """Senza bind, evento ha solo `table` (no auto-fallback)."""
    _emit_cache_hit(table="description_resolutions")
    entries = [...]
    assert "tenant_id" not in entries[0]
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 138 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Cache + governance | `uv run pytest tests/unit/test_listino_input_cache_telemetry.py tests/governance/test_log_events_catalog.py -v` | **7 PASS** (6 cache + 1 governance) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **705 PASS** (era 704, +1 sentinel) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (cache helper + serp_search) | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 24 symbols / 7 files, **0 processi affetti**, **risk LOW** |

**Rischi residui:**

- **Cambio firma `_emit_cache_*` interno**: nessun caller cliente
  esterno (è prefisso underscore, package interno). Test esistenti
  aggiornati nello stesso CHG.
- **`tenant_id` non più passato esplicito**: se in produzione il bind
  UI fallisse (eccezione DURANTE bind, before emit), gli eventi non
  avrebbero `tenant_id`. Mitigazione: il bind è la prima istruzione
  del flow (no logica before), exception path improbabile.
- **Test `test_cache_emit_without_bind_omits_tenant_id`** documenta
  esplicitamente questo trade-off (sentinel del nuovo contratto).
- **Drift `serp_search` sanato**: il valore semantico del log ora è
  conforme al catalogo. Eventuali consumer log a valle (oggi nessuno
  in produzione) che cercavano `field=` o `selectors_tried=` falliranno.
  Pattern: aderiamo al catalogo, i consumer si adeguano.

## Test di Conformità

- **Path codice applicativo:** `src/talos/observability/`,
  `src/talos/ui/`, `src/talos/io_/`, `docs/decisions/` ✓ (aree
  ADR-0013 + governance).
- **ADR-0021 esteso via errata** (ADR-0009): pattern consolidato.
- **ADR-0009**: errata corrige modalità "additivo + tabella". Nessun
  ADR Active rotto.
- **ADR-0019 (test strategy)**: unit puri ✓ + sentinel mock-only.
- **Quality gate verde** (ADR-0014).
- **Backward compat semantica payload finale**: invariata (stessi
  eventi, stessi campi nel payload — `tenant_id` ora context-bind
  invece che kwarg, ma sempre presente quando il bind è attivo, cioè
  in produzione UI).
- **Sicurezza**: zero secrets/PII; nessuna nuova dep.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 24 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: 17/17 voci invariato in
  conteggio; 2 voci (`cache.hit/miss`) con tupla aggiornata.
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: 17/17 voci. 2 tuple
  aggiornate (cache.hit/miss).
- **Test suite +1**: 705 unit/gov/golden (era 704) + 138 integration
  = 843 PASS.
- **🎯 Blocco B1 chiuso 8/8 CHG**: pattern context tracing operativo
  end-to-end, documentato canonicamente in ADR-0021, drift sanati,
  callsite puliti.
- **Sblocca**: futuri CHG che vorranno aggiungere `correlation_id`
  / `user_id` / altri context-bound (errata additiva al pattern
  documentato in ADR-0021).
- **Code health**: -1 parametro ridondante (`tenant_id` da
  `_emit_cache_*`). -3 campi non-canonici da `serp_search`. +1
  sentinel cache senza bind (lock contract).

## Refs

- ADR: ADR-0021 (logging/telemetria — esteso via errata), ADR-0009
  (errata corrige modalità additivo), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test strategy).
- Predecessori:
  - CHG-2026-04-30-006 (configure_logging structlog).
  - CHG-2026-05-01-005 (telemetria 5 eventi io_/extract attivati,
    inclusivo del drift `serp_search`).
  - CHG-2026-05-01-025 (telemetria cache.hit/miss originale con
    `tenant_id` esplicito).
  - CHG-2026-05-01-030..036 (B1.1.a..e + B1.2 + B1.3).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1, ratificate):
  4=a (errata catalogo pulizia tenant_id).
- Successore atteso: nessuno specifico (B1 chiuso). Possibili rotte
  (decisione Leader): (B2) refactor UI multi-page, (B3) Path PDF→Path B',
  (B4) bulk_resolve_async, (B5) golden Samsung 1000 ASIN. Vedi
  `project_session_handoff_2026-05-01-round5plus.md` per pacchetto
  completo.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: `14a408b`.
