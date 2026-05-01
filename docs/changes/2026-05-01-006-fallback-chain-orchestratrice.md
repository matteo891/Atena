---
id: CHG-2026-05-01-006
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" sessione attivata 2026-05-01 — clausola di sessione, non persiste; Leader ha scelto Path B = MVP "prodotto funzionante")
status: Draft
commit: 0c9b93a
adr_ref: ADR-0017, ADR-0014, ADR-0019
---

## What

Aggiunge `lookup_product(asin, *, keepa, scraper, page, ocr) -> ProductData`
in `src/talos/io_/fallback_chain.py` — primo CHG di Fase 1 Path B
(orchestrazione mock-testabile senza setup di sistema). Compone i tre
canali skeleton dei CHG-001..003 in una signature unificata che
restituisce `ProductData` (campi prodotto + audit trail per canale).

Strategia di composizione:

1. **Keepa** primario per `buybox_eur` / `bsr` / `fee_fba_eur`. Tre
   `fetch_*` indipendenti; ogni `KeepaMissError` viene catturato e
   annotato in `notes` ("keepa miss <field> per <asin>"); il campo
   resta `None` ma la chain prosegue.
2. **AmazonScraper** fallback opzionale, invocato solo se entrambi
   `scraper` e `page` sono forniti. Quando invocato, popola `title`
   (Keepa non lo espone) e copre `buybox_eur` se Keepa ha avuto miss.
   NON copre `bsr` ne' `fee_fba_eur` (i selettori in `selectors.yaml`
   non li estraggono in CHG-006).
3. **OcrPipeline** accettato come parametro per signature compatibility
   con la nota d'handoff 2026-05-01, ma **NON invocato** in CHG-006.
   Razionale: OCR sui PDF fornitore Samsung e' canale separato (input
   listino, non ASIN lookup); OCR su screenshot Amazon e' scope futuro.
   Documentato esplicitamente nel docstring + test che ne verifica la
   non-invocazione.

R-01 NO SILENT DROPS:
- `KeepaMissError` -> field=None + entry in `notes` (caller decide:
  `fee_fba=None` -> caller chiama `fee_fba_manual` L11b CHG-022;
  `buybox=None` -> riga AMBIGUA; etc.).
- `KeepaRateLimitExceededError` / `KeepaTransientError` propagati al
  caller (fail-fast, non sono miss deterministici).
- `SelectorMissError` non viene mai sollevato in `lookup_product`
  perche' lo scraper e' invocato sempre con `missing_ok=True` di
  default; la telemetria `scrape.selector_fail` continua a essere
  emessa dal scraper stesso (CHG-005).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/io_/fallback_chain.py` | nuovo | `ProductData` (frozen dataclass: asin/buybox_eur/bsr/fee_fba_eur/title + `sources: dict[str, str]` audit trail field→canale + `notes: list[str]` R-01 trail, default factory dict/list indipendenti). Costanti `SOURCE_KEEPA="keepa"` / `SOURCE_SCRAPER="scraper"`. `lookup_product(asin, *, keepa, scraper=None, page=None, ocr=None) -> ProductData` orchestratore puro. Helper privato `_try_keepa_field` (Generic via `TypeVar` Python 3.11-compatible) che invoca un `Callable[[str], _T]`, cattura `KeepaMissError` aggiungendo a `notes`, lascia propagare le altre eccezioni. Logica scrape: invocato se `scraper` e `page` non None E (`buybox_eur is None` o `title is None`); l'asin del `ProductData` ritornato e' sempre quello del call site (non quello del `KeepaProduct`). |
| `src/talos/io_/__init__.py` | modificato | + re-export `ProductData`, `lookup_product`, `SOURCE_KEEPA`, `SOURCE_SCRAPER`. Docstring esteso. |
| `tests/unit/test_fallback_chain.py` | nuovo | 15 test puri (mock `KeepaApiAdapter` + mock `BrowserPageProtocol`, no network, no Chromium, retry wait azzerati): 2 schema (`ProductData` frozen + default factories indipendenti); 2 keepa-success (tutti i campi popolati / no scraper -> no title); 2 keepa-miss (singolo miss / triple miss = 3 notes); 2 propagation (`KeepaRateLimitExceededError` / `KeepaTransientError` non catturati); 6 scraper-fallback (title-fill / buybox-fill / scraper sempre invocato per title quando page presente / page=None graceful skip / total miss no crash / OCR placeholder non invocato); 1 asin propagation (call-site asin vince su KeepaProduct.asin). |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | + riga `src/talos/io_/fallback_chain.py` con descrizione completa scope CHG-006. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**639 PASS** (534 unit/governance/golden + 105 integration). Delta:
+15 unit (`test_fallback_chain.py`).

## Why

La nota d'handoff 2026-05-01 esplicita la signature attesa:
*"Fallback chain orchestratrice: signature `lookup_product(asin, *,
keepa, scraper, ocr) -> ProductData`, gestione `KeepaMissError ->
SelectorMissError -> AMBIGUO + log`"*.

Path B ratificato dal Leader 2026-05-01 ("obiettivo prodotto
funzionante quindi scelgo Path B"): l'integratore live richiede
setup di sistema non banale (`apt install tesseract-ocr-ita-eng` +
`uv run playwright install chromium` + sandbox API key Keepa) e 5
decisioni Leader pre-flight ratificate. **Fase 1** del piano Path B
copre tutto il valore architetturale che si puo' produrre **senza**
setup di sistema: la fallback chain e' il "cervello" che usa gli
adapter, e una volta scritto e testato contro mock dei Protocol,
swappare mock → live in Fase 3 e' meccanico (factory injection,
nessuna modifica a `lookup_product`).

Razionale per i parametri `scraper`/`page`/`ocr` opzionali:
- L'integratore reale (Fase 3 CHG futuro) costruira' page Playwright
  fresh per ogni run e la passera' a `lookup_product` insieme al
  `KeepaClient` configurato con sandbox API key.
- I test unit mockano page+adapter e testano la sola orchestrazione
  (zero dipendenza da Chromium / Tesseract / network).
- Il caller "minimo" (es. CFO con CSV strutturato manuale, Path A)
  puo' chiamare `lookup_product(asin, keepa=client)` senza scraper:
  riceve `ProductData` con title=None ma con dati Keepa.

### Decisioni di design

1. **`ProductData` frozen + audit trail**: `sources: dict[str, str]`
   mappa ogni campo non-None al canale che l'ha fornito ("keepa" o
   "scraper" in CHG-006; "ocr" riservato per CHG futuro). Permette
   al caller di tracciare la provenienza per debug/analisi qualita'
   acquisizione. `notes: list[str]` accumula messaggi diagnostici
   in formato libero (R-01 trail leggibile, non strutturato).

2. **Granularita' campo-per-campo (non source-per-source)**: ogni
   campo Keepa prova indipendentemente; un miss su `bsr` non blocca
   `buybox_eur` o `fee_fba_eur`. Razionale: in produzione e'
   plausibile avere `buybox` ma non `fee_fba` (piano subscription
   Keepa) o viceversa. Soluzione "tutto o niente" butterebbe dati
   parziali utili.

3. **OCR parametro placeholder**: la signature attesa lo include ma
   in CHG-006 non viene invocato. Mantenere il parametro evita
   breaking change di signature in CHG futuri (OCR su screenshot
   Amazon, OCR su immagine listino), e il test
   `test_lookup_with_ocr_param_does_not_invoke_ocr` verifica
   meccanicamente la non-invocazione (mock OCR che lancia
   `AssertionError` se chiamato).

4. **Scraper invocato anche con buybox Keepa presente**: la condizione
   e' `buybox_eur is None or title is None`; poiche' `title` e'
   sempre `None` post-Keepa (Keepa non lo espone), lo scraper viene
   sempre invocato quando `scraper`+`page` sono forniti. Questo e'
   un trade-off: una chiamata in piu' a Playwright per ogni ASIN
   (anche se Keepa ha tutto), in cambio del titolo. Caller che
   non vogliono il titolo passano `scraper=None`.

5. **`KeepaRateLimitExceededError` / `KeepaTransientError` propagano**:
   sono errori "tecnici" non miss deterministici. Caller (es. job
   batch) decide se aspettare e ritentare (rate limit) o fallire
   (transient post-retry-esauriti). Pattern coerente con CHG-001:
   il `KeepaClient` fa retry hard solo su transient, non su
   rate-limit.

6. **`_try_keepa_field` con `TypeVar` PEP 484 (non PEP 695 `[T]`)**:
   Python 3.11 stack (ADR-0014) non supporta la sintassi generic
   inline. `TypeVar("_T")` modulo-level e' il pattern compatibile.

7. **Posizione del modulo: `src/talos/io_/`** (non `extract/`):
   `lookup_product` orchestra esclusivamente sotto-moduli `io_/`
   (KeepaClient + AmazonScraper + OcrPipeline). Non interagisce
   con `SamsungExtractor` (estrazione brand-specific) ne' con DB
   (`upsert_asin_master`). Se in futuro la chain integra anche
   l'estrazione (parse_title sul title scrapato + match), si puo'
   spostare/wrappare; per ora `io_/` e' la collocazione naturale.

8. **`asin` del `ProductData` = call-site asin**: garantisce
   consistenza con il caller anche se l'adapter Keepa ritornasse
   un `KeepaProduct` con asin diverso (caso patologico). Test
   `test_lookup_propagates_asin_to_result` verifica questa
   invariante.

### Out-of-scope

- **Live adapters** (`_LiveKeepaAdapter`, `_PlaywrightBrowserPage`,
  `_LiveTesseractAdapter`): restano skeleton. Fase 3 Path B con
  setup di sistema + 5 decisioni Leader pre-flight.
- **Bridge `ProductData -> AsinMasterInput`**: `ProductData` non
  contiene `brand`/`enterprise` (vengono dall'estrattore Samsung
  o dal CFO). Helper di conversione e' scope CHG futuro
  (probabilmente l'integratore Fase 3 quando si chiude il loop
  acquisizione → asin_master).
- **Cache locale `lookup_product`**: scope futuro (es. JSON locale
  per ASIN gia' visti recentemente per ridurre costo Keepa).
- **OCR su screenshot Amazon** (fallback estremo se scraper miss):
  scope futuro; il parametro `ocr` resta placeholder.
- **Telemetria nuova**: nessun nuovo evento canonico. I 5 eventi
  ADR-0021 attivati in CHG-005 (`keepa.miss`, `keepa.rate_limit_hit`,
  `scrape.selector_fail`, `ocr.below_confidence`,
  `extract.kill_switch`) coprono i siti di produzione del segnale;
  la fallback chain non aggiunge informazione strutturata nuova.
  Aggiungere `lookup.completed` o `lookup.fallback_step` e' scope
  futuro (errata corrige catalogo, pattern CHG-058).

## How

### `lookup_product` (highlight)

```python
def lookup_product(
    asin: str,
    *,
    keepa: KeepaClient,
    scraper: AmazonScraper | None = None,
    page: BrowserPageProtocol | None = None,
    ocr: OcrPipeline | None = None,  # placeholder CHG-006
) -> ProductData:
    sources: dict[str, str] = {}
    notes: list[str] = []

    buybox_eur, sources, notes = _try_keepa_field(
        keepa.fetch_buybox, asin, "buybox_eur", sources, notes,
    )
    bsr, sources, notes = _try_keepa_field(
        keepa.fetch_bsr, asin, "bsr", sources, notes,
    )
    fee_fba_eur, sources, notes = _try_keepa_field(
        keepa.fetch_fee_fba, asin, "fee_fba_eur", sources, notes,
    )

    title: str | None = None
    needs_scrape = (
        scraper is not None and page is not None
        and (buybox_eur is None or title is None)
    )
    if needs_scrape:
        scraped = scraper.scrape_product(asin, page=page)
        if title is None and scraped.title is not None:
            title = scraped.title
            sources["title"] = SOURCE_SCRAPER
        if buybox_eur is None and scraped.buybox_eur is not None:
            buybox_eur = scraped.buybox_eur
            sources["buybox_eur"] = SOURCE_SCRAPER

    return ProductData(
        asin=asin,
        buybox_eur=buybox_eur,
        bsr=bsr,
        fee_fba_eur=fee_fba_eur,
        title=title,
        sources=sources,
        notes=notes,
    )
```

### `_try_keepa_field` (highlight)

```python
def _try_keepa_field(
    fetcher: Callable[[str], _T],
    asin: str,
    field_name: str,
    sources: dict[str, str],
    notes: list[str],
) -> tuple[_T | None, dict[str, str], list[str]]:
    try:
        value = fetcher(asin)
    except KeepaMissError as exc:
        notes.append(f"keepa miss {exc.field} per {asin}")
        return None, sources, notes
    sources[field_name] = SOURCE_KEEPA
    return value, sources, notes
```

### Test plan eseguito

15 unit test in `tests/unit/test_fallback_chain.py`:

- 2 schema (`ProductData` frozen + default factories indipendenti per istanza)
- 2 keepa-success (full populate + no scraper -> title None)
- 2 keepa-miss (singolo / triple = 3 notes)
- 2 propagation (RateLimitExceeded / Transient post-retry)
- 6 scraper-fallback:
  - title-fill quando Keepa ha buybox
  - buybox-fill quando Keepa miss
  - scraper sempre invocato per title (con goto verificato)
  - page=None -> graceful skip
  - total miss (Keepa+scraper) -> no crash, 3 notes
  - OCR placeholder non invocato (mock OCR che AssertionError)
- 1 asin propagation (call-site asin vince)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/fallback_chain.py src/talos/io_/__init__.py tests/unit/test_fallback_chain.py` | All checks passed |
| Format | `uv run ruff format --check src/talos/io_/fallback_chain.py src/talos/io_/__init__.py tests/unit/test_fallback_chain.py` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_fallback_chain.py` | 0 issues (49 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **534 PASS** (era 519, +15) |
| Integration | `TALOS_DB_URL=postgresql+psycopg://postgres:test@localhost:55432/postgres uv run pytest tests/integration -q` | **105 PASS** (invariato) |

**Rischi residui:**
- **`title` sempre da scraper**: se in futuro Keepa esponesse il
  titolo, il caller dovrebbe configurarlo e la chain andrebbe
  rivista. Per ora Keepa non lo espone (verificato in
  `KeepaProduct` schema CHG-001).
- **Scraper sempre invocato quando `page` presente**: anche se
  Keepa ha tutto cio' che serve al caller, lo scraper e' invocato
  per il `title`. Caller che non vogliono il title devono passare
  `scraper=None` (alternativa: aggiungere `want_title=False`
  parametro in CHG futuro).
- **`SelectorMissError` non puo' essere sollevato in `lookup_product`**:
  perche' `scrape_product` di default usa `missing_ok=True`. La
  telemetria `scrape.selector_fail` resta emessa dal scraper a
  ogni miss totale di selettori (CHG-005). Se un caller futuro
  volesse il fail-fast su selector miss, dovrebbe bypassare
  `lookup_product` e chiamare il scraper direttamente con
  `missing_ok=False` (al momento `_resolve_field` privato).
- **Nessun rate-limit budget per la chain**: ogni `lookup_product`
  consuma 3 token Keepa (3 fetch_*). Su 100 ASIN -> 300 token. Il
  caller batch deve dimensionare il `rate_limit_per_minute` di
  conseguenza, o il `KeepaRateLimitExceededError` propaga
  invasivamente. Scope CHG futuro: aggregare i 3 fetch_* in un
  unico `query()` quando il `KeepaApiAdapter` lo permettera'
  (oggi gia' c'e' `_fetch_one` interno ma viene comunque chiamato
  3 volte; ottimizzazione possibile).

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/fallback_chain.py` ✓
  (area `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Composizione esplicita Keepa primario -> Scraper fallback ✓
  - Adapter pattern preservato (zero dipendenza diretta da live) ✓
  - R-01 NO SILENT DROPS ✓ (`notes` accumula miss, eccezioni
    tecniche propagano)
- **R-01 NO SILENT DROPS (governance test):** ✓
  (`keepa miss` annotato in `notes` esplicitamente).
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `lookup_product`,
  `ProductData`, `SOURCE_KEEPA`, `SOURCE_SCRAPER`,
  `_try_keepa_field` -> ADR-0017.
- **Backward compat:** modulo nuovo, niente break. `__init__.py`
  esteso (additivo).
- **Impact analysis pre-edit:** GitNexus impact upstream su
  `KeepaClient` e `AmazonScraper` = 0 caller, risk LOW. Modifica
  additiva senza modificare l'esistente.

## Impact

- **Fase 1 Path B aperta**: primo CHG che produce valore
  architetturale unitario senza setup di sistema. La fallback
  chain e' il "cervello" che la Fase 3 (live adapters) usera'
  come orchestratore.
- **`pyproject.toml` invariato** (no nuove deps).
- **`src/talos/io_/` ora completo a livello primitive +
  orchestrazione**: 4 moduli (`keepa_client`, `scraper`, `ocr`,
  `fallback_chain`) + `selectors.yaml`. Manca solo l'integratore
  live (Fase 3).
- **Nessun nuovo evento canonico ADR-0021**: catalogo resta
  10/11 viventi (5 attivati in CHG-005 dai 4 moduli skeleton +
  4 viventi pre-blocco da `tetris/`/`vgp/`/`orchestrator`/
  `panchina` + `session.replayed`). `db.audit_log_write` resta
  dormiente lato Python (replicato dai trigger Postgres).
- **Caller minimo possibile**: `lookup_product(asin,
  keepa=client)` con solo Keepa configurato e' il pattern Path A
  (CFO con CSV manuale + acquisizione opzionale Keepa-only senza
  scraper Playwright).
- **Ponte verso Fase 3 (live adapters)**: il caller (CHG futuro)
  costruira' `page = _PlaywrightBrowserPage(...)` (live, post
  `playwright install chromium`) e la passera' a `lookup_product`.
  Zero modifica al modulo `fallback_chain.py` necessaria.

## Refs

- ADR: ADR-0017 (canale io_/extract + fallback chain), ADR-0014
  (mypy/ruff strict), ADR-0019 (test unit pattern).
- Predecessori CHG: CHG-2026-05-01-001 (`KeepaClient`),
  CHG-2026-05-01-002 (`AmazonScraper`), CHG-2026-05-01-003
  (`OcrPipeline`), CHG-2026-05-01-005 (`asin_master_writer` +
  telemetria 5 eventi).
- Pattern Adapter Protocol di riferimento: tutti i moduli
  `io_/` introdotti nei CHG-001..003.
- Memory: `project_io_extract_design_decisions.md` (D1-D5
  ratificate "default"), `project_session_handoff_2026-05-01.md`
  (signature `lookup_product`).
- Successore atteso (Fase 3 Path B): live adapters
  (`_LiveKeepaAdapter` + `_PlaywrightBrowserPage` +
  `_LiveTesseractAdapter`) + golden HTML/PDF/img + integration
  test live + 5 decisioni Leader pre-flight A/B/C ratificate.
  Setup di sistema preflight: `apt install tesseract-ocr
  tesseract-ocr-ita tesseract-ocr-eng` + `uv run playwright
  install chromium` + sandbox `TALOS_KEEPA_API_KEY`.
- Commit: `0c9b93a`.
