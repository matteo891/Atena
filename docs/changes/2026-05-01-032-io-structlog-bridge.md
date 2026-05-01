---
id: CHG-2026-05-01-032
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 6 — blocco B1 sessione dedicata 3/8)
status: Draft
commit: aeadc98
adr_ref: ADR-0021, ADR-0014, ADR-0019
---

## What

**Bridge stdlib→structlog del cluster `io_/`** (3/5 della fase
B1.1). Replica il pattern di CHG-030/031 sui 4 file applicativi del
cluster: `keepa_client.py` (2 emit), `ocr.py` (1 emit), `scraper.py`
(1 emit), `serp_search.py` (1 emit). **Splitta** il file
`test_io_extract_telemetry.py` (sinistro CHG-2026-05-01-005) in:
- `test_io_telemetry.py` (nuovo): 4 test cluster `io_/` migrati a
  `LogCapture` (consumer fixture conftest CHG-031).
- `test_io_extract_telemetry.py` (ridotto): 4 test `extract.kill_switch`
  restano su pytest `caplog` (stdlib). Saranno migrati in CHG-B1.1.d
  contestualmente al bridge `extract/`. Probabile rinomina del file a
  `test_extract_telemetry.py` allora.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/io_/keepa_client.py` | modificato | `import logging` → `import structlog`. `_logger = logging.getLogger(__name__)` → `_logger = structlog.get_logger(__name__)`. 2 emit `keepa.miss` + `keepa.rate_limit_hit`: `extra={...}` → `**kwargs`. |
| `src/talos/io_/ocr.py` | modificato | Stesso pattern. 1 emit `ocr.below_confidence`: `extra={...}` → `**kwargs`. |
| `src/talos/io_/scraper.py` | modificato | Stesso pattern. 1 emit `scrape.selector_fail`: `extra={...}` → `**kwargs`. |
| `src/talos/io_/serp_search.py` | modificato | Stesso pattern. 1 emit `scrape.selector_fail` (drift di campi pre-esistente preservato — vedi sezione "Risk residuo"): `extra={...}` → `**kwargs`. |
| `tests/unit/test_io_telemetry.py` | nuovo | Migrato da pytest `caplog` a `structlog.testing.LogCapture`. Consumer fixture conftest. 7 test (3 keepa.miss parametrico + 1 keepa.rate_limit_hit + 2 scrape.selector_fail + 2 ocr.below_confidence + 1 ocr no-emit happy path). Rimosse type-ignore `attr-defined` (entry dict-like, no LogRecord). |
| `tests/unit/test_io_extract_telemetry.py` | modificato | Riscritto: rimossi 4 test io_-related (migrati al nuovo file); restano i 4 test `extract.kill_switch` con caplog. Header docstring aggiornato: "test extract isolato post-split B1.1.c". |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **700 PASS** unit/gov/golden (invariato).
- **138 PASS** integration (invariato).
- **838 PASS** totali.

Detect_changes: 5 file, 11 simboli touched, 3 processi affetti
(`Lookup_products → Query_selector_text/xpath_text` step 4
`_resolve_field`; `Process_image → Otsu_threshold` step 1
`process_image`), **risk MEDIUM** — vedi sezione dedicata.

## Why

CHG-030 ha aperto B1.1 progressivo per area; CHG-031 ha migrato
`tetris/` ed estratto la fixture `log_capture` in conftest. CHG-032
prosegue con `io_/`, area di acquisizione dati (Keepa + Playwright +
Tesseract — ADR-0017) con il maggior numero di emit nel cluster (5
emit reali su 4 file). Dopo CHG-032 restano `extract/` (B1.1.d) e
`ui/` (B1.1.e) per chiudere la fase B1.1.

Lo split del file test era prevedibile: il file storico
`test_io_extract_telemetry.py` (CHG-005) raggruppava 5 eventi
canonici di 2 cluster diversi. Migrare `io_/` ma non `extract/`
mette il file in stato ibrido: 4 test su `LogCapture` (post-bridge
io_/) + 4 test su `caplog` (pre-bridge extract/). Splittare ora
isola pulitamente gli scope, anticipa il pattern di rinomina a
`test_extract_telemetry.py` in B1.1.d, e consente al nuovo
`test_io_telemetry.py` di essere immediatamente coerente con i
fratelli `test_vgp_telemetry`/`test_tetris_telemetry`/
`test_panchina_telemetry`.

### Decisioni di design

1. **Split file invece di duplicare 2 fixture nel singolo file**:
   manutenibilità migliore (1 file = 1 cluster = 1 fixture).
   Pattern uniforme post-bridge: `test_<modulo>_telemetry.py` con
   `log_capture`.

2. **`test_io_extract_telemetry.py` non rinominato in CHG-032**:
   rinomina rompe `git log --follow` in misura non utile finora.
   Quando B1.1.d migrerà `extract/` (probabile rinomina contestuale
   con `git mv`), il file consoliderà la sua identità "extract-only"
   con un singolo gesto.

3. **`serp_search.py` drift di campi preservato**: il `scrape.selector_fail`
   emesso a riga 180-187 ha campi `{asin: "<serp>", field, selectors_tried}`
   invece dei canonici `{asin, selector_name, html_snippet_hash}`
   (catalogo `events.py:35`). Il drift è pre-esistente da CHG-005,
   non scope CHG-032. Sarà risolto in CHG-B1.4 (errata catalogo o
   normalizzazione campi). Bridge `extra=` → `**kwargs` lo preserva
   identicamente.

4. **`test_io_telemetry.py` con 7 test** (era 8 in `test_io_extract_telemetry`
   originale, escludendo i 4 extract): ho preservato 1 happy-path
   `test_ocr_above_threshold_does_not_emit_below` come sentinel di
   non-emit (parallel a `test_no_telemetry_when_all_pass` in vgp).

5. **Type ignore `# type: ignore[attr-defined]` rimossi**: con
   `LogCapture` gli `entries` sono `list[dict[str, Any]]`, accesso
   via chiave dict, no LogRecord proxy. Codice più pulito.

6. **Helper test `_MissingFieldAdapter`/`_MockEmptyPage`/
   `_StaticTesseractAdapter` invariati**: spostati 1:1 al nuovo file.

7. **`ruff TC002` su tutti i 4 nuovi/modificati test**: `LogCapture`
   import in TYPE_CHECKING block, pattern consolidato in CHG-031.

8. **Detect_changes risk MEDIUM accettato**: vedi sezione dedicata.
   Il bridge stdlib→structlog tocca il codice fisico delle funzioni
   (linea logger init), e `_resolve_field`/`process_image` sono
   membri di processi cross/intra-community in GitNexus. Risk LOW
   sarebbe raggiungibile solo riducendo a 0 il diff funzionale
   (impossibile per un bridge). Il segnale "MEDIUM" è giustamente
   "abbiamo toccato funzioni dentro processi"; l'integration suite
   verde (138 PASS) conferma comportamento applicativo invariato.

### Out-of-scope

- **Bridge `extract/`**: scope CHG-B1.1.d.
- **Bridge `ui/`**: scope CHG-B1.1.e.
- **Adoption `bind_session_context`**: scope CHG-B1.2 (orchestrator)
  e CHG-B1.3 (UI).
- **Errata catalogo ADR-0021 (drift `serp.selector_fail` field
  names + pulizia `tenant_id`/`session_id` context-bound)**: scope
  CHG-B1.4.
- **Rinomina `test_io_extract_telemetry.py` → `test_extract_telemetry.py`**:
  scope CHG-B1.1.d (rinomina con `git mv` contestuale alla migrazione
  fixture).

## How

### Pattern uniforme dei 4 src (highlight diff)

```diff
-import logging
+import structlog
 ...
-_logger = logging.getLogger(__name__)
+_logger = structlog.get_logger(__name__)
 ...
-_logger.debug("event", extra={"foo": ..., "bar": ...})
+_logger.debug("event", foo=..., bar=...)
```

### Test split (highlight nuovo `test_io_telemetry.py`)

```python
@pytest.mark.parametrize("field", ["buybox", "bsr", "fee_fba"])
def test_keepa_miss_event_emitted(field: str, log_capture: LogCapture) -> None:
    adapter = _MissingFieldAdapter(miss_field=field)
    client = KeepaClient(api_key="x", adapter_factory=lambda _: adapter, ...)
    method = getattr(client, f"fetch_{field}")
    with pytest.raises(KeepaMissError):
        method("B0CN3VDM4G")

    miss = [e for e in log_capture.entries if e["event"] == "keepa.miss"]
    assert len(miss) == 1
    assert miss[0]["asin"] == "B0CN3VDM4G"
    assert miss[0]["error_type"] == field
    assert miss[0]["retry_count"] == 0
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed (1 fixable autofixed: import sort `keepa_client.py`) |
| Format | `uv run ruff format src/ tests/` | 138 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria mirata io_+extract+fallback | `uv run pytest tests/unit/test_io_telemetry.py tests/unit/test_io_extract_telemetry.py tests/unit/test_fallback_chain.py -v` | **36 PASS** (7 io + 4 extract + 25 fallback) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **700 PASS** (invariato) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (4 simboli sondati: `KeepaClient`, `OcrPipeline`, `AmazonScraper`, `_parse_serp_payload`) | risk LOW per ognuno |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 11 symbols / 5 files, 3 processes affected, **risk MEDIUM** (vedi nota) |

**Rischi residui:**

- **Detect_changes risk MEDIUM**: `_resolve_field` e `process_image`
  appaiono in `proc_1_lookup_products` / `proc_2_lookup_products`
  (cross-community) e `proc_15_process_image` (intra-community).
  GitNexus segnala "abbiamo toccato funzioni che fanno parte di
  flussi end-to-end". **Comportamento applicativo invariato 100%**:
  il bridge cambia solo l'API del logger (stdlib → structlog), gli
  eventi emessi conservano nome canonico + campi (a parte il drift
  pre-esistente di `serp_search.py`). Le **138 integration PASS**
  (live e2e Keepa + Playwright + Postgres reali) sono la prova
  empirica che i 3 processi continuano a funzionare. La valutazione
  MEDIUM è strutturale del tipo di refactor (touch su nodi-foglia
  di processi), non sostanziale.

- **`serp_search.py` drift di campi pre-esistente**: l'emit `scrape.selector_fail`
  ha `field`/`selectors_tried` invece dei canonici
  `selector_name`/`html_snippet_hash`. Pre-esistente da CHG-005, NON
  introdotto qui. Risolto in CHG-B1.4 (errata catalogo) o singolo
  CHG dedicato post-B1.

- **`test_io_extract_telemetry.py` ora ibrido**: contiene solo 4
  test extract.kill_switch con `caplog` (stdlib). Quando samsung.py
  sarà migrato in B1.1.d, il file verrà migrato a `LogCapture` e
  probabilmente rinominato. Stato transitorio noto e documentato.

- **Side-effect globale `structlog.configure` nella fixture**:
  validato cross-test in CHG-030/031, ulteriormente validato in
  CHG-032 (suite full 700+138 verde).

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/` ✓ (area ADR-0013
  consentita; ADR-0017 governa modulo).
- **ADR-0017 vincoli rispettati**: i 4 canali (Keepa/Playwright/
  Tesseract/SERP) restano disaccoppiati via Protocol/Adapter.
  Nessuna modifica al disegno Protocol-based.
- **ADR-0021**: structlog libreria canonica. Allineamento dei 5
  emit del cluster.
- **ADR-0019 (test strategy)**: unit puri ✓, mock-only.
- **Quality gate verde**: ruff/format/mypy/pytest tutti pass
  (ADR-0014).
- **No nuovi simboli applicativi**: solo refactor.
- **Backward compat semantica**: invariata 100% (stessi 5 eventi,
  stessi campi salvo drift pre-esistente non scope).
- **Sicurezza**: zero secrets/PII; no nuove deps.
- **Impact analysis pre-edit**: risk LOW (KeepaClient/OcrPipeline/
  AmazonScraper/_parse_serp_payload).
- **Detect_changes risk MEDIUM**: documentato sopra. Mitigazione:
  138 integration PASS prova invarianza comportamentale; bridge è
  refactor del logger, non logica.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**: refactor
  mirato + split test motivato + change doc snello.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite invariata in conteggio**: 838 PASS. Migrazione
  in-place dei 4 test io_-related dal vecchio file al nuovo.
- **Sblocca CHG-B1.1.d/e**: stesso pattern di refactor
  replicabile su `extract/` (1 file: `samsung.py`) e `ui/` (2
  file: `dashboard.py`, `listino_input.py`).
- **Sblocca CHG-B1.2**: 9/12 siti emit applicativi ora consumano
  `merge_contextvars` (mancano solo `extract/` + `ui/`).
- **Code health**: -8 type-ignore `attr-defined` (i test dict-style
  sono più strict). +1 file test (split logico). -4 test in file
  ibrido.

## Refs

- ADR: ADR-0021 (logging/telemetria), ADR-0017 (acquisizione dati),
  ADR-0014 (mypy/ruff strict), ADR-0019 (test strategy).
- Predecessori:
  - CHG-2026-04-30-006 (configure_logging structlog).
  - CHG-2026-05-01-001/002/003 (skeleton Keepa/Scraper/Ocr).
  - CHG-2026-05-01-005 (telemetria 5 eventi io_/extract attivati).
  - CHG-2026-05-01-017 (serp_search.py — drift di campi
    pre-esistente).
  - CHG-2026-05-01-030 (B1.1.a vgp/, pattern di refactor).
  - CHG-2026-05-01-031 (B1.1.b tetris/ + estrazione fixture
    conftest).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1).
- Successore atteso: **CHG-B1.1.d** (bridge structlog su `extract/`
  + rinomina `test_io_extract_telemetry.py` → `test_extract_telemetry.py`).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: `aeadc98`.
