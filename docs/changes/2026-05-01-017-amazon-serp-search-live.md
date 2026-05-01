---
id: CHG-2026-05-01-017
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 4 — apertura blocco SERP scraping live)
status: Draft
commit: 467c713
adr_ref: ADR-0017, ADR-0014, ADR-0019
---

## What

Inaugura `src/talos/io_/serp_search.py` — adapter SERP Amazon.it
live (`amazon.it/s?k=<query>`) via Playwright. Sblocca la
risoluzione `(descrizione, prezzo) -> ASIN top-N` consumata da
`asin_resolver` (CHG-016 -> integrazione CHG-018).

Pattern adapter coerente con il resto di `io_/`:
- `SerpResult` frozen dataclass (asin, title, price_displayed,
  position) - top-N risultato con posizione 0-based.
- `SerpBrowserProtocol` minimal (`goto + evaluate`), separato da
  `BrowserPageProtocol` (CHG-002) per zero blast radius su mock
  esistenti. `_PlaywrightBrowserPage` (CHG-012) soddisfa entrambi
  via duck typing (un nuovo metodo `evaluate` aggiunto in CHG-017).
- `AmazonSerpAdapter` Protocol con `search(query, *, max_results=5)
  -> list[SerpResult]`.
- `_LiveAmazonSerpAdapter` con `browser_factory` per riusare context
  Chromium fra query (pattern Playwright session reuse).

Estrazione strutturata via `page.evaluate(JS)` hardcoded:
- itera `[data-component-type="s-search-result"]`
- estrae `data-asin` (attribute), titolo (`h2 a span`/`h2 span`),
  prezzo (`.a-price .a-offscreen`)
- skip risultati senza asin (banner / sponsored a layout diverso)
- limit applicato JS-side per ridurre payload

Verifica live (1 test reale Amazon.it): selettori
`[data-component-type="s-search-result"]` validi sul layout 2026.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/io_/serp_search.py` | nuovo | `SerpResult`, `SerpBrowserProtocol`, `AmazonSerpAdapter`, `_LiveAmazonSerpAdapter` con `urllib.parse.quote(safe="")` URL builder + JS hardcoded `_SERP_EXTRACT_JS_TEMPLATE` (sostituzione `MAX_RESULTS` testuale). + `_parse_serp_payload(raw, *, max_results)` helper modulo-level: robust a payload non-list / dict mancanti / type drift; emette `scrape.selector_fail` event su payload non-list (catalogo ADR-0021). + `parse_eur` riusato (CHG-002) per parsing `.a-offscreen` con tolleranza italiano/anglo. + costanti `DEFAULT_SERP_MAX_RESULTS=5`, `AMAZON_IT_SEARCH_URL_TEMPLATE`. |
| `src/talos/io_/scraper.py` | modificato | `_PlaywrightBrowserPage` aggiunge metodo `evaluate(expression: str) -> object` (delegato a `page.evaluate`). Soddisfa duck-typing per `SerpBrowserProtocol`. `BrowserPageProtocol` invariato (no breaking su mock esistenti CHG-002/013). |
| `src/talos/io_/__init__.py` | modificato | Re-export `SerpResult`, `SerpBrowserProtocol`, `AmazonSerpAdapter`, costanti `DEFAULT_SERP_MAX_RESULTS`, `AMAZON_IT_SEARCH_URL_TEMPLATE`. |
| `tests/unit/test_serp_search.py` | nuovo | 17 test unit mock-only via `_MockSerpBrowser`: 2 costanti modulo, 8 `_parse_serp_payload` (happy path, missing asin/title, no price -> None, invalid price text, max_results cap, non-list returns [], non-dict items skip), 7 `_LiveAmazonSerpAdapter.search` (URL builder + evaluate, top-N, max_results cap, empty query raises, max_results<=0 raises, URL encode special chars, zero results []). |
| `tests/integration/test_live_serp.py` | nuovo | 1 test integration live (skip module-level se Chromium non installato, pattern CHG-012). Query reale Amazon.it "Galaxy S24" -> verifica top-1 ha `asin.startswith("B0")`, titolo contiene "galaxy", `position=0`. Tollerante a ranking SERP dinamico (no asin esatto). Costo: zero quota Keepa, ~3s Chromium goto reale. PASS in 2.83s. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **604
PASS** unit/gov/golden + 123 integration = **727 PASS** (era 713,
+17 unit + +1 integration live).

## Why

CHG-016 ha aperto il blocco asin_resolver con tipi + helper puri,
ma manca lo stadio di acquisizione SERP. CHG-017 e' il primo
adapter live: dato un testo libero, ritorna top-N candidati ASIN
da Amazon.it. Senza questo, `asin_resolver` non puo' essere
integrato (CHG-018) perche' non ha sorgente di candidati.

Decisione 1=A ratificata Leader round 4: SERP primario, no quota.
Implementato qui.

Pattern di estensione "Protocol separato + duck typing" scelto per
minimizzare blast radius. Alternative considerate:
- Estendere `BrowserPageProtocol` con `evaluate`: avrebbe richiesto
  toccare 5 mock esistenti (test_amazon_scraper, test_fallback_chain,
  test_io_extract_telemetry, test_lookup_to_asin_master,
  test_acquire_and_persist) - blast radius alto per zero valore
  immediato.
- Multi-fetch separato (3 chiamate `query_selector_all_text` per
  asin/title/price separati): fragile (ordine non garantito se un
  risultato ha titolo ma non prezzo, drift dell'array).
- `evaluate` come Protocol indipendente nuovo: chosen ✓ - zero
  impact su mock esistenti, JS hardcoded sicuro by design.

### Decisioni di design

1. **`SerpBrowserProtocol` separato**: come spiegato sopra. Zero
   impact sui 5 mock di `BrowserPageProtocol` esistenti.

2. **JS hardcoded come template + sostituzione testuale `MAX_RESULTS`**:
   il valore `max_results` e' Python int validato (>=1), niente
   injection rischi. Alternativa f-string con `{}` braces: esce con
   parsing del JS (le `{}` sono blocchi JS validi). Sostituzione
   testuale e' piu' robusta.

3. **`urllib.parse.quote(query, safe="")`**: encode TUTTI i caratteri
   non-ASCII e tutti i simboli special-URL (`&`, `?`, `=`).
   Alternativa `safe="/"` lascerebbe passare `&` che romperebbe l'URL.

4. **`SerpResult.position` 0-based**: convenzione Python uniforme.
   Caller/UI possono mostrare `position+1` se serve "Rank #1".

5. **`SerpResult.price_displayed: Decimal | None`**: il prezzo SERP
   non e' sempre presente (out-of-stock, "vedi piu' offerte" link,
   prezzo "a partire da" senza valore puntuale). `None` esplicito
   permette al caller di calcolare confidence con `delta_price=None`
   (CHG-016 `compute_confidence(80.0, None) = 48`).

6. **`browser_factory` lambda invece di browser diretto**: pattern
   permette riuso context Chromium attraverso N query nello stesso
   `_LiveAmazonSerpAdapter`. Caller batch grande passa una lambda
   che cattura un `_PlaywrightBrowserPage` istanza riusata. Caller
   one-shot passa lambda che ne crea uno nuovo per ogni search.

7. **Skip risultati senza `asin` o senza `title`**: sponsored ads /
   banner Amazon hanno layout `[data-component-type="s-search-result"]`
   ma `data-asin=""` o titoli incollati in shadow DOM. Skip
   silenzioso vale: il caller puo' contarli per stats ma il flusso
   resolver non e' impattato.

8. **`_parse_serp_payload` modulo-level**: pure function, testabile
   direttamente senza adapter. Pattern coerente con `_last_valid_value`
   (CHG-015).

9. **Telemetria `scrape.selector_fail`**: emessa quando il payload
   e' non-list (= JS evaluate fallito o layout cambiato). Pattern
   coerente con `_resolve_field` di `AmazonScraper` (CHG-002/013).
   Catalogo ADR-0021 invariato.

10. **1 test live in CHG-017**: lezione round 3 (CHG-013) "i mock
    non rilevano drift HTML reale". Costo basso (zero quota Keepa,
    ~3s goto Chromium), ratifica selettori SERP 2026 immediatamente.
    Pattern coerente con CHG-013 smoke 1-shot.

### Out-of-scope

- **Integrazione `asin_resolver` <- SERP -> `lookup_product`**:
  scope CHG-2026-05-01-018.
- **Cache description -> asin** (`description_resolutions` table):
  scope CHG-2026-05-01-019.
- **UI Streamlit nuovo flow upload**: scope CHG-2026-05-01-020.
- **Keepa Product Search fallback**: scope CHG futuro post-CHG-018
  se SERP scraping mostra blind spots empirici.
- **Filtri SERP avanzati** (categoria, prezzo range, brand): non
  servono per MVP. Caller passa query libera.
- **Concorrenza N query batch**: scope futuro asyncio. Sequenziale
  va bene per MVP listini < 100 ASIN.
- **Stealth aggiuntivo**: il `_PlaywrightBrowserPage` di CHG-012 ha
  gia' `playwright-stealth`. Riusato as-is.
- **Telemetria nuova `serp.search_completed` / `serp.zero_results`**:
  scope futuro errata catalogo ADR-0021 quando il flusso e' in
  produzione.

## How

### `_LiveAmazonSerpAdapter.search` (highlight)

```python
def search(self, query, *, max_results=5):
    if not query.strip():
        raise ValueError("query SERP vuota")
    if max_results <= 0:
        raise ValueError(f"max_results > 0 (got {max_results})")
    browser = self._browser_factory()
    url = AMAZON_IT_SEARCH_URL_TEMPLATE.format(
        query=urllib.parse.quote(query, safe=""),
    )
    browser.goto(url)
    js = _SERP_EXTRACT_JS_TEMPLATE.replace("MAX_RESULTS", str(max_results))
    raw = browser.evaluate(js)
    return _parse_serp_payload(raw, max_results=max_results)
```

### Live test (highlight verbatim)

```python
def test_live_serp_galaxy_s24_returns_relevant_top1():
    page = _PlaywrightBrowserPage()
    try:
        adapter = _LiveAmazonSerpAdapter(browser_factory=lambda: page)
        results = adapter.search("Galaxy S24", max_results=3)
    finally:
        page.close()
    assert len(results) >= 1
    top1 = results[0]
    assert top1.asin.startswith("B0")
    assert "galaxy" in top1.title.lower()
```

PASS in 2.83s -> selettori SERP confermati validi sul layout 2026.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (51 source files, +1) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **604 PASS** (era 587, +17 nuovi `test_serp_search`) |
| Integration (no live keepa) | `uv run pytest tests/integration --ignore=tests/integration/test_live_keepa.py -q` | **123 PASS** (era 122, +1 live SERP) |
| Live SERP | `uv run pytest tests/integration/test_live_serp.py -v` | PASS in 2.83s su Galaxy S24 reale |

**Rischi residui:**
- **Layout Amazon.it dinamico**: i selettori SERP possono cambiare
  con A/B test Amazon. Mitigazione: telemetria
  `scrape.selector_fail` su payload vuoto + test live ricorrente.
  Drift catturato al primo run successivo al cambio.
- **Anti-bot Amazon**: i SERP sono protezioni anti-scraping piu'
  severe delle product pages. `playwright-stealth` (CHG-012) attivo.
  Caller batch deve rispettare delay range (CHG-002 D2.c). Captcha
  rilevato -> top-1 non avra' titolo Galaxy + il test live fallisce
  esplicitamente.
- **Quota richiesta**: 1 SERP query = 1 goto Chromium (~150ms +
  payload load ~2-3s). Per batch 100 ASIN -> ~5 minuti. Trade-off
  noto. Cache via `description_resolutions` (CHG-019) abbattera'
  drasticamente per re-run.
- **JS template con MAX_RESULTS sostituzione testuale**: se per
  errore qualcuno sostituisse `MAX_RESULTS` con uno string non-int,
  il JS fallirebbe a runtime con SyntaxError. Sostituzione fatta
  in posto unico, validato dal test
  `test_search_builds_correct_url_and_calls_evaluate`.
- **`evaluate` aggiunto a `_PlaywrightBrowserPage`**: nuovo metodo
  invariante per i caller esistenti. Test esistenti su `BrowserPageProtocol`
  invariati (mock con 4 metodi originali continuano a passare).
- **Test live richiede Chromium installato + libs**: skip
  module-level su CI senza setup. Coerente con
  `test_live_playwright.py`.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/serp_search.py` ✓
  (area `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Adapter pattern + Protocol separato per scope-isolation ✓
  - R-01 NO SILENT DROPS: `_parse_serp_payload` su non-list ->
    [] esplicito + emit `scrape.selector_fail`. Empty query /
    invalid max_results -> ValueError. Skip risultati senza
    asin/title -> defensive (caller riceve top-N puliti, banner
    skipped non e' "drop silente di dati": e' "dato non era un
    risultato prodotto"). Per la fonte ratificata (`asin_resolver`
    CHG-018), zero risultati = candidato_count=0 esposto
    esplicitamente al CFO via `ResolutionResult` con `selected=None`.
- **Test unit + integration live:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `serp_search.py` ->
  ADR-0017 (canale acquisizione, estensione naturale dei 3 canali
  esistenti).
- **Backward compat:** `BrowserPageProtocol` invariato; tutti i mock
  esistenti (CHG-002/013) inalterati. `_PlaywrightBrowserPage`
  estesa con `evaluate` (additivo, no breaking). `AmazonScraper`
  invariato (usa solo i 4 metodi pre-esistenti del Protocol).
- **Sicurezza:** JS hardcoded nel sorgente Talos (no input esterno),
  URL builder con `quote(safe="")` (no injection).
  `playwright-stealth` attivo (CHG-012). 1 test live tocca Amazon.it
  reale ma in modalita' "ToS-friendly" (1 query / esecuzione,
  rispetto delay range).
- **Impact analysis pre-edit:** GitNexus risk LOW (modulo nuovo,
  zero caller upstream applicativi finche' non lo integriamo in
  CHG-018).

## Impact

- **Apertura canale SERP live**: 2/5 CHG attesi del blocco
  asin_resolver (CHG-016 skeleton + CHG-017 SERP live).
- **Path B end-to-end ora copre anche risoluzione descrizione->ASIN**
  (in modo isolato; integrazione resolver<-SERP+lookup scope CHG-018).
- **`pyproject.toml` invariato** (no nuove deps; `urllib.parse`
  stdlib, Playwright gia' dep).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11 viventi).
  `scrape.selector_fail` ora si attiva anche per SERP malformati.
- **Test suite cresce di +18 (17 unit + 1 integration)**: 727 PASS
  totali (era 713), zero regression.
- **Selettori SERP 2026 ratificati live**: lezione round 3 confermata,
  i mock non bastano. Live test ricorrente su CI cattura drift.
- **`_PlaywrightBrowserPage.evaluate`**: primitive disponibile per
  futuri scenari (review extraction, structured data multi-attr,
  ecc.). Riusabile senza estensioni Protocol.

## Refs

- ADR: ADR-0017 (canale SERP acquisizione, estensione canale 2),
  ADR-0014 (mypy/ruff strict + Protocol pattern), ADR-0019 (test
  unit puri + integration live skip-on-missing-deps).
- Predecessori:
  - CHG-2026-05-01-002 (`AmazonScraper` + `parse_eur` riusato).
  - CHG-2026-05-01-012 (`_PlaywrightBrowserPage` live):
    `_PlaywrightBrowserPage` esteso con `evaluate`.
  - CHG-2026-05-01-013 (lezione "i mock non rilevano drift HTML"):
    test live 1-shot ratifica selettori SERP.
  - CHG-2026-05-01-016 (`asin_resolver` skeleton): consumer dei
    `SerpResult` in CHG-2026-05-01-018.
- Decisione Leader 2026-05-01 round 4: 1=A (SERP primario, zero
  quota Keepa).
- Sibling: `AmazonScraper` (product page scraping, CHG-002), distinct
  scope.
- Memory: `feedback_ambigui_con_confidence.md` (R-01 NO SILENT DROPS
  UX-side, fonte design `_parse_serp_payload` skip vs raise).
- Successore atteso: CHG-2026-05-01-018 (`resolve_description`
  composition: SERP -> top-N -> per ogni candidato `lookup_product`
  per buybox -> `compute_confidence(fuzzy_title, delta_price)` ->
  `ResolutionResult`).
- Commit: `467c713`.
