---
id: CHG-2026-05-01-021
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 5 — hardening flow descrizione+prezzo CHG-020 con telemetria UI)
status: Draft
commit: <pending>
adr_ref: ADR-0021, ADR-0016, ADR-0014, ADR-0019
---

## What

Errata additiva al catalogo eventi canonici ADR-0021 + emit
applicativo nei due click button del flow descrizione+prezzo
introdotto da CHG-020.

| Evento | Modulo | Campi obbligatori |
|---|---|---|
| `ui.resolve_started` | `ui/dashboard.py` | `n_rows`, `has_factory` |
| `ui.resolve_confirmed` | `ui/dashboard.py` | `n_total`, `n_resolved`, `n_ambiguous` |

**Bonus correttivo**: `session.replayed` (errata CHG-058) era
documentata in ADR-0021 ma mancava da `CANONICAL_EVENTS` in
`src/talos/observability/events.py`. Drift sanato in CHG-021
(allineamento dict ↔ ADR), insieme alla costante tipizzata
`EVENT_SESSION_REPLAYED`.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/observability/events.py` | modificato | + 3 voci nel dict `CANONICAL_EVENTS` (`session.replayed`, `ui.resolve_started`, `ui.resolve_confirmed`) + 3 costanti tipizzate `EVENT_*`. Catalogo passa da 10 a **13 voci**. Header docstring aggiornato. |
| `src/talos/ui/dashboard.py` | modificato | + `import logging` top + `_logger = logging.getLogger(__name__)` + 2 helper puri `_emit_ui_resolve_started(*, n_rows, has_factory)` / `_emit_ui_resolve_confirmed(*, n_total, n_resolved, n_ambiguous)`. Emit inline ai siti di produzione: button "Risolvi descrizioni" pre-Chromium-open + button "Conferma listino e crea sessione" pre-return DataFrame. Pattern testabile senza Streamlit context. |
| `docs/decisions/ADR-0021-logging-telemetria.md` | modificato | + voce `## Errata` 2026-05-01 con tabella 2 nuovi eventi UI + razionale + nota bonus correttivo `session.replayed`. Coerente con pattern errata CHG-058 (additivo, no supersessione). |
| `tests/unit/test_dashboard_telemetry_resolve.py` | nuovo | 5 test caplog: 2 per `_emit_ui_resolve_started` (happy path + has_factory=False edge case), 2 per `_emit_ui_resolve_confirmed` (happy path + n_resolved=0 edge case), 1 governance "catalog contains new entries" che blinda il dict aggiornato. Pattern coerente con `test_replay_session_telemetry.py` (CHG-058). |
| `tests/unit/test_events_catalog.py` | modificato | `_EXPECTED_EVENTS` esteso a 13 voci con commenti che ancorano ogni voce al CHG di origine. Test rinominato `test_catalog_has_ten_canonical_events` → `test_catalog_matches_expected_events` (snapshot non più legato al numero "ten"). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **645
PASS** unit/gov/golden + 126 integration (no live) = **771 PASS**
contati no-live (era 749 no-live in CHG-019 baseline; +5 nuovi
`test_dashboard_telemetry_resolve` + 17 nuovi resolved nei test esistenti
durante run completo).

Aggiungendo i 7 test live skippabili (Chromium/Keepa key) il totale
suite-completa diventa **778 PASS** (era 773, +5 nuovi).

## Why

CHG-020 ha consegnato il flow descrizione+prezzo come MVP CFO,
ma il primo click ("Risolvi descrizioni") consuma quota Keepa +
quota SERP scrapata Amazon — **costo invisibile** in produzione
senza telemetria. `ui.resolve_started` permette di:

- Misurare la frequenza d'uso reale del flow nuovo vs legacy.
- Diagnostica post-mortem se un CFO esaurisce quota Keepa
  ("quante volte ha cliccato 'Risolvi'? con quante righe?").
- Decidere se introdurre rate limit / preview / conferma
  pre-Chromium quando `n_rows` supera una soglia.

`ui.resolve_confirmed` traccia il **conversion rate**
(righe risolte → listino confermato), KPI prodotto: misura se
il MVP regge nell'uso reale. CFO che apre il flow, risolve, e
poi NON conferma = segnale di confidence troppo bassa /
risultato non utile, da indagare.

### Decisioni di design

1. **Helper puri `_emit_ui_resolve_*` invece di `_logger.debug`
   inline**: pattern coerente con `compare_session_kpis`
   (CHG-059) — ogni helper UI con logica derivativa = funzione
   pura testabile senza Streamlit. Il button `st.button` resta
   inline ma il payload del log è isolato. Costo zero (1 indirezione
   funzione), beneficio: 5 test caplog senza dipendenza da
   `streamlit.testing.v1.AppTest`.

2. **DEBUG level (non INFO)**: coerente con tutti gli altri 5
   eventi viventi (`tetris.skipped_budget`, `vgp.veto_*`,
   `panchina.archived`, `session.replayed`). INFO sarebbe stato
   coerente con la classificazione ADR-0021 ("eventi normali del
   business"), ma il catalogo ha già stabilito il pattern DEBUG
   per gli eventi canonici → mantengo coerenza.

3. **Campi minimali per evento**: 2-3 campi ciascuno. Trade-off:
   `ui.resolve_started` potrebbe esporre anche `tenant_id` per
   correlare con `session.replayed` futuri, ma il flow CHG-020
   è single-tenant MVP (`DEFAULT_TENANT_ID=1`), aggiungere il
   campo ora = noise. Scope futuro quando multi-tenant arriverà.

4. **`has_factory: bool` invece di `factory_id`**: privacy +
   semplicità. Il consumatore della telemetria non deve sapere
   "quale" factory; gli serve sapere se la cache è stata
   consultata (sì/no), che è già un ottimo proxy di costo.

5. **Bonus correttivo `session.replayed` aggiunto al dict**:
   il drift CHG-058 era latente — il governance test
   `test_log_events_catalog` cercava solo eventi del dict, ma
   `orchestrator.py` non ha pattern `continue/.drop/.skip`, quindi
   non era esercitato. Aggiungo `session.replayed` al dict +
   costante `EVENT_SESSION_REPLAYED` per allineare ADR ↔ codice.
   Costo zero, beneficio: il dict ora rispecchia ADR-0021 al 100%.

6. **Nessuna refactor di emit precedenti**: `orchestrator.py`
   continua a usare la stringa letterale `"session.replayed"`
   (pattern CHG-058 + `test_log_events_catalog` regola: stringhe
   letterali per garantire grep). Importare `EVENT_SESSION_REPLAYED`
   in orchestrator.py richiederebbe rifattorizzare anche gli
   altri 4 emit (vgp.*, panchina.*) per coerenza — out-of-scope.

7. **Test "catalog contains new entries"**: non duplicato con
   `test_events_catalog.py` esistente — quello fa snapshot
   _set-equality_, questo verifica esplicitamente le 3 voci nuove
   con i loro `tuple` di campi obbligatori. Doppia
   protezione: rimuovere accidentalmente uno dei 3 nuovi eventi =
   2 test rossi (più visibilità in code review).

8. **Rinomina `test_catalog_has_ten_canonical_events` →
   `test_catalog_matches_expected_events`**: il nome "ten"
   diventerebbe stale ad ogni aggiunta. Il test ora è
   ancorato all'INTENT (snapshot expected = actual) non al
   conteggio.

### Out-of-scope

- **Telemetria `ui.resolve_failed`** (resolver crash, Keepa key
  missing, rate limit): scope futuro se analisi ex-post degli
  eventi `ui.resolve_started` senza `ui.resolve_confirmed` mostra
  lacune. Per ora `ResolutionResult.notes` accumulano i fallimenti
  per riga (R-01 UX-side).
- **Streamlit testing reale via `streamlit.testing.v1.AppTest`**:
  scope smoke browser TEST-DEBT-003 residuo. Helper puri sono
  sufficienti per coverage telemetria.
- **Ricontesto bind `session_id` / `tenant_id`** (ADR-0021
  context binding): scope futuro CHG-z (`structlog.bind` migration).
  Tutti gli emit attuali usano stdlib `logging.Logger.debug`, non
  `structlog.get_logger`.
- **Errata `ui.resolve_failed` con `error_type`**: scope futuro
  se osservazione produzione mostra fallimenti opachi.
- **Refactor `orchestrator.py` per importare costanti
  `EVENT_*`**: scope futuro (out-of-scope decisione 6).

## How

### `events.py` (highlight 3 nuove voci)

```python
CANONICAL_EVENTS: Final[dict[str, tuple[str, ...]]] = {
    # ... 10 voci esistenti ...
    # Orchestrator (ADR-0018) — replay what-if (errata CHG-058)
    "session.replayed": ("asin_count", "locked_in_count", "budget", "budget_t1"),
    # UI flow descrizione+prezzo (ADR-0016) — errata CHG-021
    "ui.resolve_started": ("n_rows", "has_factory"),
    "ui.resolve_confirmed": ("n_total", "n_resolved", "n_ambiguous"),
}
```

### `dashboard.py` (highlight helper + emit inline)

```python
def _emit_ui_resolve_started(*, n_rows: int, has_factory: bool) -> None:
    _logger.debug(
        "ui.resolve_started",
        extra={"n_rows": n_rows, "has_factory": has_factory},
    )

def _emit_ui_resolve_confirmed(*, n_total, n_resolved, n_ambiguous):
    _logger.debug(
        "ui.resolve_confirmed",
        extra={
            "n_total": n_total,
            "n_resolved": n_resolved,
            "n_ambiguous": n_ambiguous,
        },
    )

# nel button "Risolvi descrizioni":
if st.button("Risolvi descrizioni", key="resolve_descriptions_btn"):
    api_key = TalosSettings().keepa_api_key
    if api_key is None:
        st.error("...")
        return None
    _emit_ui_resolve_started(n_rows=len(rows), has_factory=factory is not None)
    keepa_client = KeepaClient(...)
    # ... resolve loop ...

# nel button "Conferma listino":
if st.button("Conferma listino e crea sessione", ...):
    listino_df = build_listino_raw_from_resolved(resolved)
    if listino_df.empty:
        st.error("...")
        return None
    _emit_ui_resolve_confirmed(
        n_total=n_total, n_resolved=n_resolved, n_ambiguous=n_ambiguous,
    )
    st.session_state.resolved_rows = None
    return listino_df
```

### Test caplog (highlight pattern)

```python
def test_resolve_started_emits_canonical_event(caplog):
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_started(n_rows=12, has_factory=True)
    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_STARTED]
    assert len(records) == 1
    assert records[0].n_rows == 12
    assert records[0].has_factory is True
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria nuova + governance | `uv run pytest tests/unit/test_dashboard_telemetry_resolve.py tests/unit/test_replay_session_telemetry.py tests/governance -v` | **9 PASS** (5 nuovi + 2 replay + 2 governance) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **645 PASS** (era 640, +5 nuovi telemetry) |
| Integration (no live) | `TALOS_DB_URL=... uv run pytest tests/integration --ignore=tests/integration/test_live_*.py -q` | **126 PASS** (invariato vs CHG-020) |

**Rischi residui:**
- **Helper puri non testano lo `st.button` invocation**: il test
  copre l'emit ma non il "click → emit" Streamlit-side.
  Validazione interaction reale = manuale Leader-side (smoke
  browser, scope TEST-DEBT-003 residuo).
- **DEBUG level masking in produzione**: se la pipeline log e'
  configurata a INFO, gli eventi `ui.resolve_*` non arrivano al
  sink. Mitigazione: il container produzione MVP usa DEBUG
  default (config in `observability/logging_config.py`).
  Caller scope futuro che usa structlog.bind dovrebbe verificare
  filter level prima di affidarsi a questi eventi.
- **Drift dict ↔ ADR**: il test `test_events_catalog.py` snapshot
  protegge il dict da rimozioni accidentali, ma non verifica
  meccanicamente che ogni evento sia anche in ADR-0021.
  Verifica testuale ↔ ADR rimane disciplina umana.
- **Stringhe letterali vs costanti**: `dashboard.py` usa stringhe
  letterali (`"ui.resolve_started"`) coerente con pattern
  governance test grep. Refactor a `EVENT_*` costanti = scope
  futuro coerente con out-of-scope 6.
- **Bonus `session.replayed` add to dict**: cambio retro-compat
  (additivo) — `orchestrator.py` continua a funzionare invariato.

## Test di Conformità

- **Path codice applicativo:** `src/talos/observability/`,
  `src/talos/ui/` ✓ (aree ADR-0013 consentite).
- **ADR-0021 vincoli rispettati:**
  - Catalogo eventi canonici esteso via errata additiva (pattern
    CHG-058) — no supersessione necessaria.
  - Campi obbligatori per ogni evento esposti come `tuple`.
  - Modulo emittente documentato in errata.
  - DEBUG level coerente con eventi viventi precedenti.
  - R-01 NO SILENT DROPS dinamico verificato:
    `test_log_events_catalog` verde post-modifica.
- **ADR-0016 vincoli rispettati:** helper puri testabili senza
  Streamlit (pattern già consolidato in CHG-040/057/059).
- **Test unit puri:** ✓ (ADR-0019). 5 test caplog senza
  dipendenza Streamlit.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:**
  `_emit_ui_resolve_started` / `_emit_ui_resolve_confirmed` →
  ADR-0016 (UI) + ADR-0021 (telemetria). Costanti `EVENT_*` →
  ADR-0021.
- **Backward compat:** modifica additiva 100%; orchestrator.py /
  emit esistenti invariati.
- **Sicurezza:** zero secrets nei campi log; `n_rows` /
  `has_factory` / contatori sono dati operativi non sensibili.
- **Impact analysis pre-edit:** GitNexus risk LOW
  (`_render_descrizione_prezzo_flow` zero caller upstream;
  `CANONICAL_EVENTS` zero caller upstream).
- **Detect changes pre-commit:** GitNexus risk LOW (4 file, 0
  processi affetti).

## Impact

- **Catalogo ADR-0021: 13/13 viventi** (era 10/11; +3 voci, di
  cui 1 bonus `session.replayed` allineato).
- **Hardening A1 chiuso**: flow descrizione+prezzo CHG-020
  ora osservabile in produzione (quote tracking + conversion
  rate KPI).
- **`pyproject.toml` invariato** (no nuove deps).
- **Test suite +5 unit**: 645 unit/gov/golden (era 640).
- **MVP CFO target**: hardening incrementale; il flow nuovo
  resta production-ready, ora con telemetria.
- **Drift `session.replayed` ADR ↔ codice**: chiuso.
- **Pattern emit-helper-puro**: replicabile per futuri eventi UI
  (es. `ui.resolve_failed` se necessario).

## Refs

- ADR: ADR-0021 (catalogo eventi canonici, errata additiva
  pattern CHG-058), ADR-0016 (UI Streamlit, pattern helper puri),
  ADR-0014 (mypy/ruff strict), ADR-0019 (test unit caplog).
- Predecessori:
  - CHG-2026-04-30-049 (telemetria vgp/panchina, primo emit
    multi-evento).
  - CHG-2026-04-30-058 (errata `session.replayed`): drift
    `events.py` sanato in CHG-021.
  - CHG-2026-05-01-020 (UI flow descrizione+prezzo): consumer
    della telemetria appena aggiunta.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato (errata snella + 5 test mirati).
- Successore atteso: A2 `verified_buybox_eur` separato da
  `cost_eur` in `ResolvedRow` (estensione `build_listino_raw_from_resolved`).
- Commit: `<pending>`.
