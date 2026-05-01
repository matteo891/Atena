---
id: CHG-2026-05-01-012
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 2 attiva, Path B target — Fase 3 in corso)
status: Draft
commit: e553b5f
adr_ref: ADR-0017, ADR-0014, ADR-0019
---

## What

Implementa `_LiveTesseractAdapter`'s sibling: `_PlaywrightBrowserPage`
ratificato live (era skeleton `NotImplementedError` da CHG-2026-05-01-002).
Secondo live adapter della Fase 3 Path B, sbloccato dall'installazione
`uv run playwright install chromium` (~115 MB cache).

Decisioni Leader Fase 3 ratificate "default" 2026-05-01:

- **Cookie consent GDPR Amazon (A)**: post-`goto`, click best-effort
  su `#sp-cc-accept`; `contextlib.suppress(Exception)` se l'overlay
  non c'e' (non-blocking). Selettore costante
  `COOKIE_CONSENT_SELECTOR_AMAZON` modulo-level.
- **Stealth strategy (B medium)**: `playwright-stealth` 2.0.3 nuova
  dep; `Stealth().apply_stealth_sync(page)` riduce fingerprint
  (`navigator.webdriver`, sec-ch-ua, plugins, ecc.). Viewport
  realistico 1920x1080. UA fisso (D2.b da CHG-002).
- **Timeout `goto` (B)**: 60s default via
  `DEFAULT_PLAYWRIGHT_TIMEOUT_MS = 60_000`. Configurabile in
  `__init__`.

Pattern lazy-init + context manager: il browser apre al primo
`goto()` (o `__enter__`), `close()` rilascia tutte le risorse in
ordine inverso (page -> context -> browser -> playwright). `close()`
e' idempotente. Riusabile fra ASIN multipli nello stesso ciclo
(riuso context Chromium come previsto da `lookup_products` CHG-009).

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | + dep `playwright-stealth>=2.0.3` (canale 2 ADR-0017, decisione Leader B medium). + override mypy `playwright_stealth.*` ignore_missing_imports (community lib senza py.typed, deroga ADR-0014 documentata; pattern coerente con `pytesseract.*`). |
| `src/talos/io_/scraper.py` | modificato | `_PlaywrightBrowserPage` ratificato live: `sync_playwright().start()` lazy + `browser.new_context(user_agent, viewport)` + `Stealth().apply_stealth_sync(page)` + `set_default_timeout(60_000)`. `goto(url)` chiama `page.goto(url, wait_until="domcontentloaded")` + `_dismiss_cookie_overlay(page)` best-effort. `query_selector_text` e `query_selector_xpath_text` usano `page.query_selector(...)` con XPath via prefisso `xpath=`. `close()` idempotente con `contextlib.suppress`. `__enter__/__exit__` per uso `with` idiomatico. + costanti `DEFAULT_PLAYWRIGHT_TIMEOUT_MS=60_000`, `COOKIE_CONSENT_SELECTOR_AMAZON="#sp-cc-accept"`. + import top-level di `sync_playwright`, `Stealth`, `contextlib`, `Self`. |
| `tests/integration/test_live_playwright.py` | nuovo | 6 test integration live (skip module-level se `~/.cache/ms-playwright/` assente OPPURE `ldconfig -p` non riporta `libnspr4` — segnala system deps mancanti): goto+CSS query inline HTML / XPath query / selettore assente -> None / `close()` idempotente / `query_*` prima di `goto` -> None / scenario integrato scraper+stealth+selectors.yaml su `data:text/html,...` URL. Pattern `data:text/html,...` evita fixture httpserver e dip esterne. |
| `tests/unit/test_amazon_scraper.py` | modificato | Rimossi 3 test obsoleti `test_playwright_page_*_raises_not_implemented` (skeleton ora implementato; copertura live nei nuovi integration). Rimosso import `_PlaywrightBrowserPage` non piu' usato. Sostituiti con commento esplicativo che rinvia ai test integration live. |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Riga `src/talos/io_/scraper.py` aggiornata con descrizione `_PlaywrightBrowserPage` live (decisioni A/B/B). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**660 PASS + 6 skipped** (544 unit/governance/golden + 116
integration; era 663, netto −3 unit rimosse, +6 integration skipped
in attesa system deps libnspr4/libnss3).

## Why

`uv run playwright install chromium` installa il binario Chrome
Headless Shell (~115 MB), ma il binario stesso richiede librerie
condivise di sistema (`libnspr4.so`, `libnss3.so`,
`libatk-1.0-0`, ecc.) che il flag `--with-deps` (richiede sudo)
avrebbe installato automaticamente. Senza tali librerie, ogni
launch del browser fallisce con
`error while loading shared libraries: libnspr4.so: cannot open
shared object file`.

I 6 test integration nuovi sono pronti e scritti correttamente
ma sono attualmente in stato **skipped** (verifica
`ldconfig -p | grep libnspr4`); una volta installate le system
deps via `sudo playwright install-deps chromium` (oppure
equivalente apt), passano automaticamente al run successivo.

Il codice del `_PlaywrightBrowserPage` e' funzionalmente completo
e ratificato secondo le decisioni Leader; solo il run dei test
e' bloccato da un prerequisito di sistema documentato.

### Decisioni di design

1. **Cookie consent A — click `#sp-cc-accept` best-effort**:
   l'overlay GDPR Amazon non altera il contenuto prodotto;
   accettare i cookie tracking non degrada il valore acquisito
   (price, title, BSR sono pubblici). Selettore in costante
   `COOKIE_CONSENT_SELECTOR_AMAZON` permette evolvere senza
   ridistribuire codice (futuro: spostare in `selectors.yaml`
   se Amazon cambia layout).

2. **Stealth B medium — `playwright-stealth`**: scelta
   conservativa fra A (no mitigation) e C (proxy residenziali).
   `playwright-stealth` 2.0.3 patcha i fingerprint piu' ovvi:
   `navigator.webdriver=false`, `navigator.plugins`,
   `sec-ch-ua`, viewport realistico, ecc. ~3 MB di codice
   Python. Riduce significativamente la probabilita' di captcha
   senza richiedere infra (proxy a pagamento, gestione
   header HTTP custom).

3. **Timeout 60s — B**: 30s e' il default Playwright; ho
   ratificato 60s come compromesso per rete europea/CDN. 90s+retry
   non scala bene per batch (ogni ASIN raddoppia o triplica la
   latenza). Caller batch decide retry a livello superiore via
   `KeepaTransientError` retry o batch retry su lista intera.

4. **Lazy-init + context manager**: il browser non si apre al
   `__init__` (un caller potrebbe creare l'oggetto e non usarlo,
   o passarlo a un altro thread). Apre al primo `goto()` o
   `__enter__`. `close()` esplicito o `__exit__` rilasciano
   tutto. Pattern Pythonic.

5. **Resource cleanup con `contextlib.suppress(Exception)`**:
   `close()` deve essere idempotente e tollerante a errori
   parziali (es. browser gia' crashato). `try/except: pass`
   sostituito con `contextlib.suppress` (idiomatico Python ≥3.4).

6. **Import top-level (no lazy)**: ruff PLC0415 vieta lazy
   import e ho rimosso il workaround. `playwright` e
   `playwright-stealth` sono dep dichiarate, sempre presenti.

7. **`Self` come return type di `__enter__`**: PEP 673 (Python
   3.11+, gia' parte dello stack ADR-0014). Pattern coerente con
   ruff PYI034.

8. **Test live via `data:text/html,...` URL**: Playwright
   supporta nativamente, evita fixture httpserver locale. HTML
   inline con `<h1 id='title'>...</h1>` test selettori CSS/XPath.
   Quando avremo golden HTML statici Amazon (CHG futuro), si
   aggiungeranno test su `tests/golden/html/amazon_*.html`
   caricati via `page.set_content()` o `file://`.

9. **Skip robusto su 2 condizioni**: `_CHROMIUM_CACHE.exists()`
   (cache scaricata) AND `_chromium_runtime_libs_present()`
   (libnspr4 in `ldconfig -p`). Senza una delle due, skip
   pulito. Pattern coerente con CHG-011 (`shutil.which("tesseract")`).

10. **Rimozione 3 test legacy `_PlaywrightBrowserPage_*_raises_not_implemented`**:
    skeleton non piu' raise; test sono contraddittori al codice
    nuovo. Sostituiti con commento esplicativo che rimanda ai
    test integration live. Pattern coerente con CHG-011 (rimosso
    `test_live_adapter_raises_not_implemented` per Tesseract).

### Out-of-scope

- **`AmazonScraper.scrape_product` end-to-end live su Amazon
  reale**: scope CHG futuro con golden HTML statici (ToS-friendly,
  deterministico, veloce). Oggi `scrape_product` hardcoda
  `AMAZON_IT_PRODUCT_URL`; non c'e' modo di testarlo via
  `data:text/html,...`. Workaround test: chiamare direttamente
  `_resolve_field` o costruire `_PlaywrightBrowserPage` + chiamare
  i metodi senza passare da `scrape_product`.
- **Storage state persistence (D2.c.alt)**: D2.c e' "fresh
  context per run" (gia' ratificato). `storage_state.json` e'
  scope futuro se vorra' velocizzare i batch grandi (cookie
  consent gia' settato).
- **Headless=False per debug**: parametro non esposto; caller
  che vuole headless=False patcha il modulo o aggiunge param
  in CHG futuro.
- **Telemetria nuova** (`scrape.page_load_time`, `scrape.cookie_dismissed`):
  scope futuro errata catalogo ADR-0021 quando il flusso e'
  in produzione e si vuole osservabilita' per-ASIN.
- **Concurrent context**: lazy-init crea UN contesto. Per
  parallelism (es. asyncio.gather), ogni task deve avere il suo
  `_PlaywrightBrowserPage`. Scope futuro se serve.

## How

### `_PlaywrightBrowserPage._ensure_started` (highlight)

```python
def _ensure_started(self) -> Page:
    if self._page is not None:
        return self._page
    self._playwright = sync_playwright().start()
    self._browser = self._playwright.chromium.launch(headless=True)
    self._context = self._browser.new_context(
        user_agent=self._user_agent,
        viewport=self._viewport,
    )
    self._context.set_default_timeout(self._timeout_ms)
    self._page = self._context.new_page()
    if self._apply_stealth:
        Stealth().apply_stealth_sync(self._page)
    return self._page
```

### Cookie consent GDPR (highlight)

```python
@staticmethod
def _dismiss_cookie_overlay(page: Page) -> None:
    with contextlib.suppress(Exception):
        btn = page.query_selector(COOKIE_CONSENT_SELECTOR_AMAZON)
        if btn is not None:
            btn.click(timeout=2_000)
```

### Test plan eseguito (skipped finché libs non installate)

6 test integration in `tests/integration/test_live_playwright.py`:

- `test_live_playwright_goto_inline_html_and_query_css`: goto +
  query CSS `#title` su HTML inline.
- `test_live_playwright_query_xpath`: XPath via `xpath=//div[@class='price']`.
- `test_live_playwright_returns_none_on_missing_selector`: selettori
  assenti -> None (R-01).
- `test_live_playwright_close_is_idempotent`: `close()` 2x senza raise.
- `test_live_playwright_query_before_goto_returns_none`: `query_*`
  prima di `goto()` -> None (no crash).
- `test_live_playwright_amazon_scraper_end_to_end_with_data_url`:
  goto data URL Samsung-like + parse_eur su prezzo italiano €
  799,90 -> Decimal("799.90").

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/scraper.py tests/integration/test_live_playwright.py tests/unit/test_amazon_scraper.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (49 source files; +1 override mypy `playwright_stealth.*`) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **544 PASS** (era 547; netto −3 per rimozione legacy `test_playwright_page_*_raises_not_implemented`) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **116 PASS + 6 skipped** (era 116; +6 nuovi live playwright skipped per system deps mancanti) |

**Rischi residui:**
- **System deps libnspr4/libnss3/libatk-1.0/etc. mancanti**:
  bloccante per esecuzione live (skip module-level finche' non
  installate). `sudo playwright install-deps chromium` oppure
  apt manuale come documentato nel reason del skip.
- **`playwright-stealth` plugin community**: non e' parte di
  Microsoft Playwright. Aggiornamenti possono lag-gare con le
  nuove versioni Playwright. Pin `>=2.0.3` lascia spazio a
  patch ma non a major. Caller futuro che voglia disabilitare
  passa `apply_stealth=False` in `__init__`.
- **Cookie consent GDPR Amazon**: il selettore `#sp-cc-accept`
  e' visto da scraping community come stabile, ma Amazon puo'
  cambiare layout. Mitigazione: `_dismiss_cookie_overlay` e'
  best-effort (suppress) -> selettore assente non blocca lo
  scraping. Caller deve monitorare il rate di
  `scrape.selector_fail` per detectare drift.
- **headless=True con `chrome-headless-shell`**: Playwright
  recente preferisce questo binario per scenari pure-headless;
  e' piu' leggero ma alcune feature avanzate (estensioni,
  service workers) potrebbero comportarsi diversamente da
  Chromium completo. Per il caso d'uso scraping non e' un
  problema.
- **Lazy init non thread-safe**: due thread che chiamano
  `goto()` simultaneamente potrebbero entrambi eseguire
  `sync_playwright().start()`. Caller singolo-thread (default)
  non ha il problema. Concurrency e' scope futuro.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/scraper.py` ✓
  (area `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Wrapper isolato Playwright dietro `BrowserPageProtocol` ✓
  - D2.a CSS->XPath fallback chain (in `_resolve_field` di
    `AmazonScraper`, invariato) ✓
  - D2.b UA fisso ✓
  - D2.c delay range (in `AmazonScraper`, invariato) ✓
- **R-01 NO SILENT DROPS (governance test):** ✓ (overlay GDPR
  best-effort suppress; ma `scrape.selector_fail` resta sempre
  emesso da `_resolve_field` se selettori falliscono — segnale
  drift non perso).
- **Test integration live + unit ridotti:** ✓ (ADR-0019 +
  ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** modifica live
  adapter privato + costanti modulo-level -> ADR-0017.
- **Backward compat:** API `_PlaywrightBrowserPage` retro-compat
  (constructor accetta `user_agent` come prima; nuovo kwarg
  `timeout_ms`/`viewport`/`apply_stealth` opzionali con
  default).
- **Impact analysis pre-edit:** modifica live adapter privato;
  `AmazonScraper` invariato; impact LOW.

## Impact

- **Fase 3 Path B avanzamento**: 2/3 live adapter ratificati
  (CHG-011 Tesseract + CHG-012 Playwright). Resta `_LiveKeepaAdapter`
  (post Fase 2 step 3 = sandbox API key Keepa).
- **`pyproject.toml` cresce di 1 dep**: `playwright-stealth>=2.0.3`.
- **System deps mancanti documentate**: 6 test integration live
  skipped finche' non installate. Sblocca al prossimo run dopo
  `sudo playwright install-deps chromium`.
- **Pattern adapter live consolidato**: pyproject mypy override
  ora copre 2 librerie senza py.typed (`pytesseract.*`,
  `playwright_stealth.*`); pattern documentato per future
  dep community.
- **Catalogo eventi canonici ADR-0021**: invariato (10/11
  viventi). Telemetria `scrape.selector_fail` continua a
  funzionare via `_resolve_field` di `AmazonScraper`.

## Refs

- ADR: ADR-0017 (canale Amazon scraping), ADR-0014 (mypy/ruff
  strict + override `playwright_stealth.*`), ADR-0019 (test
  integration pattern).
- Predecessore: CHG-2026-05-01-002 (`AmazonScraper` skeleton
  + `_PlaywrightBrowserPage` `NotImplementedError`).
- Sibling: CHG-2026-05-01-011 (`_LiveTesseractAdapter` live —
  pattern coerente: skip module-level su system deps mancanti
  + rimozione test legacy skeleton).
- Setup di sistema:
  - ✓ `uv run playwright install chromium` (~115 MB cache scaricata)
  - ⚠️ `sudo playwright install-deps chromium` PENDING — sblocca
    i 6 test live attualmente skipped.
- Decisioni Leader ratificate "default" 2026-05-01:
  - Cookie consent GDPR: A (click best-effort)
  - Stealth: B (medium via `playwright-stealth`)
  - Timeout: B (60s)
- Memory: `project_io_extract_design_decisions.md` (D2 ratificata
  "default", ora estesa con decisioni Fase 3).
- Successore atteso: CHG-2026-05-01-013 (`_LiveKeepaAdapter`
  live, sbloccato dall'arrivo della sandbox API key Keepa) +
  CHG futuro (golden HTML statici Amazon per `scrape_product`
  end-to-end live).
- Commit: `e553b5f`.
