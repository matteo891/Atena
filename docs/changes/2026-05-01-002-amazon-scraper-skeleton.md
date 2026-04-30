---
id: CHG-2026-05-01-002
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" sessione attivata 2026-04-30 sera, prosegue oltre mezzanotte)
status: Draft
commit: ba2421c
adr_ref: ADR-0017, ADR-0014, ADR-0019, ADR-0021
---

## What

Aggiunge `AmazonScraper` + `selectors.yaml` a `src/talos/io_/`
— secondo canale della fallback chain ADR-0017 (canale 2:
scraping `amazon.it` su miss Keepa). Adapter pattern:
`BrowserPageProtocol` isola Playwright per testabilita' senza
Chromium. `_PlaywrightBrowserPage` e' uno skeleton
(`NotImplementedError` esplicito) — la ratifica live richiede
`playwright install chromium` ed e' rinviata a
CHG-2026-05-01-005 integratore.

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | + dep `playwright>=1.40.0,<2` (canale 2 ADR-0017); + dep `pyyaml>=6.0,<7` (lettura selectors.yaml); + dev dep `types-PyYAML>=6.0,<7` (mypy strict). Commento aggiornato: "Tesseract resta da aggiungere". |
| `src/talos/io_/selectors.yaml` | nuovo | Schema `amazon_it.<field>.{css,xpath}` con 3 campi (`product_title`, `buybox_price`, `asin_marker`). Selettori CSS plurimi ordinati + XPath di backup. Versionato in `src/talos/io_/` (vicino al modulo). |
| `src/talos/io_/scraper.py` | nuovo | Costanti `DEFAULT_USER_AGENT`, `DEFAULT_DELAY_RANGE_S=(1.5, 4.0)`, `DEFAULT_SELECTORS_YAML` (Path), `AMAZON_IT_PRODUCT_URL`. `@dataclass(frozen=True) ScrapedProduct(asin, title, buybox_eur)`. `SelectorMissError(asin, *, field, attempted)` (R-01). `BrowserPageProtocol` con `goto`/`query_selector_text`/`query_selector_xpath_text`. `load_selectors(path)` parser YAML con check schema (TypeError su mapping invalido, ValueError su chiave radice mancante). `parse_eur(raw)` heuristica italiano/anglo (ultima fra `,` e `.` = decimale; `\xa0` non-breaking space gestito; ritorna None su input non parsabile). `AmazonScraper(*, user_agent, delay_range_s, selectors_path)` + `scrape_product(asin, *, page)` (calls `goto` + resolve fields + parse Decimal); `_resolve_field(asin, field, page, *, missing_ok)` con fallback CSS→XPath (primo non-empty vince). `_PlaywrightBrowserPage` skeleton (3 metodi `NotImplementedError` con messaggio esplicito che cita CHG-005 + `playwright install chromium`). |
| `src/talos/io_/__init__.py` | modificato | + re-export `AmazonScraper`, `BrowserPageProtocol`, `ScrapedProduct`, `SelectorMissError`, `load_selectors`, `parse_eur`, `AMAZON_IT_PRODUCT_URL`, `DEFAULT_USER_AGENT`, `DEFAULT_DELAY_RANGE_S`, `DEFAULT_SELECTORS_YAML`. Docstring esteso: "esteso in CHG-2026-05-01-002 con AmazonScraper". |
| `tests/unit/test_amazon_scraper.py` | nuovo | 34 test puri (mock `BrowserPageProtocol` + tmp YAML fixture, no Chromium): 6 `load_selectors` (default file in repo + custom + 4 errori schema/file); 14 `parse_eur` (9 valid parametrici italiano/anglo/EUR/`\xa0` + 5 invalid); 2 construction (default + custom); 7 fallback chain (1° CSS / 2° CSS / XPath / all-miss-optional / all-miss-required raises / unknown field raises); 3 `scrape_product` integration (goto URL + buybox parsed + buybox unparsable -> None); 3 `_PlaywrightBrowserPage` skeleton (3 metodi raise NotImplementedError). |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Riga `src/talos/io_/scraper.py` aggiornata con descrizione completa scope CHG-002. Spostato/aggiornato `selectors.yaml` -> `src/talos/io_/selectors.yaml` con schema descritto. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**550 PASS** (450 unit/governance/golden + 100 integration).
Delta unit: +34 (`test_amazon_scraper.py`).

## Why

ADR-0017 designa lo scraping `amazon.it` come canale 2 della
fallback chain (attivato su miss Keepa per `BuyBox`/titolo).
Senza un wrapper isolato, il caller avrebbe codice Playwright
inline + selettori hardcoded — ogni cambio layout Amazon
richiederebbe deploy di codice invece di update YAML.

CHG-2026-05-01-002 e' il secondo CHG del blocco `io_/extract`
Samsung (4-5 attesi, decisioni Leader D1-D5 ratificate "default"
2026-04-30 sera). D2 applicata in questo CHG.

### Decisioni di design (D2 ratificata)

1. **D2.a Selector fallback CSS -> XPath (B)**: per ogni campo,
   `selectors.yaml` lista CSS in ordine + XPath di backup. Primo
   selettore con testo non vuoto vince. No `aria-label` (D2.a
   esclude opzione C). Razionale: CSS e' rapido + leggibile;
   XPath copre i casi in cui Amazon usa attributi dinamici;
   `aria-label` aggiungerebbe rumore senza beneficio nel breve.

2. **D2.b User-agent singolo fisso (A)**: `DEFAULT_USER_AGENT`
   = Chrome desktop realistico, immutabile a costruzione del
   client. No rotation (D2.b esclude opzione B). Razionale:
   anti-detection medium-low; rotation aggiungerebbe complessita'
   senza beneficio dimostrato sui pochi listini Samsung MVP.

3. **D2.c Browser context fresh (A)**: ogni run ottiene un
   nuovo context, no `storage_state.json` (D2.c esclude opzione
   B). Razionale: cookie carry-over rischia di legare le
   sessioni successive a uno stato inconsistente; il fresh
   context replica lo stato anonymous coerente. Tradeoff: ad ogni
   run Amazon mostra eventuale captcha first-touch.

4. **Adapter pattern + Protocol**: `BrowserPageProtocol` espone
   3 metodi minimal (`goto`, `query_selector_text`,
   `query_selector_xpath_text`). Il modulo non importa Playwright
   per esecuzione test unit -> Chromium NON necessario.
   `_PlaywrightBrowserPage` adapter live e' lo skeleton (R-01
   NO SILENT DROPS via NotImplementedError).

5. **`parse_eur` come funzione modulo-level**: helper puro,
   indipendente dallo scraper (riusabile per OCR/Keepa
   normalizzazione). Heuristica robusta su 9 casi parametrici.

6. **`scrape_product` con `missing_ok=True` di default**: la
   signature pubblica gestisce field-level miss come `None`
   (caller decide). `_resolve_field` con `missing_ok=False` e'
   accessibile internamente (test) per il pattern "campo
   obbligatorio" (futura ratifica caller).

7. **`selectors.yaml` in `src/talos/io_/`**: vicino al modulo
   che lo consuma (no path globale). Versionato git
   (configurazione vivente, vedi ADR-0017 sez. "Effetti
   collaterali noti": modifiche frequenti, change document
   obbligatorio).

8. **Costanti delay range come tuple**: `(1.5, 4.0)` cadence
   umana ADR-0017. NON viene applicata in CHG-002 (richiede
   adapter live); il valore e' solo esposto via property per
   futuro consumo del `_PlaywrightBrowserPage` integratore.

### Out-of-scope

- **`_PlaywrightBrowserPage` live wrapper**: richiede
  `playwright install chromium` (~150 MB) + context manager
  `sync_playwright()`. Ratifica in CHG-2026-05-01-005
  integratore.
- **Selettori reali validati su HTML Amazon corrente**:
  scope golden HTML in `tests/golden/html/`. Quelli inclusi in
  `selectors.yaml` sono best-effort basati su layout pubblici
  comuni; verifica empirica al primo run live.
- **Telemetria evento `scrape.selector_fail`**: catalogo
  ADR-0021 (dormiente). Attivata nell'integratore CHG-2026-05-01-005
  quando il caller gestisce il `SelectorMissError`.
- **Cadence umana applicata** (delay random): logica nel live
  adapter (CHG-005), non qui.
- **Pagina di ricerca/listing**: solo product page detail
  in CHG-002. Lookup ASIN da titolo (`SamsungExtractor.parse_title`)
  e' scope CHG-2026-05-01-004.
- **Login Amazon / cookie consenso**: ADR-0017 vincola scraping
  non-autenticato; il consenso cookie e' scope futuro UX live.

## How

### `parse_eur` heuristica (highlight)

```python
def parse_eur(raw: str) -> Decimal | None:
    cleaned = raw.replace("€", "").replace("EUR", "").replace("\xa0", " ").strip()
    if not cleaned:
        return None
    has_comma, has_dot = "," in cleaned, "." in cleaned
    if has_comma and has_dot:
        if cleaned.rindex(",") > cleaned.rindex("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")  # IT
        else:
            cleaned = cleaned.replace(",", "")  # anglo
    elif has_comma:
        cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
```

### `_resolve_field` fallback chain (highlight)

```python
def _resolve_field(self, asin, field, page, *, missing_ok):
    chain = self._selectors[field]
    attempted = []
    for css in chain.css:
        attempted.append(f"css:{css}")
        v = page.query_selector_text(css)
        if v is not None and v.strip():
            return v.strip()
    for xpath in chain.xpath:
        attempted.append(f"xpath:{xpath}")
        v = page.query_selector_xpath_text(xpath)
        if v is not None and v.strip():
            return v.strip()
    if missing_ok:
        return None
    raise SelectorMissError(asin, field=field, attempted=attempted)
```

### Test plan eseguito

34 unit test sul modulo `scraper.py` + selectors.yaml:

- 6 `load_selectors` (default in repo / custom / missing root /
  amazon_it non mapping / field non mapping / file mancante)
- 14 `parse_eur` (9 valid parametrizzati incluso `\xa0` + 5
  invalid: vuoto/spazi/`€`/`abc`/multi-comma)
- 2 construction (default + custom UA/delay/path)
- 7 fallback chain (1° CSS match / 2° CSS / XPath all-CSS-fail /
  all-fail optional / all-fail required raises / unknown field
  raises KeyError)
- 3 `scrape_product` integration (goto URL + buybox parsed +
  buybox unparsable -> None)
- 3 `_PlaywrightBrowserPage` skeleton (3 metodi raise
  NotImplementedError)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/ tests/unit/test_amazon_scraper.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_amazon_scraper.py` | 0 issues (44 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **450 PASS** (era 416, +34) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **100 PASS** (invariato) |

**Rischi residui:**
- **Selettori `selectors.yaml` non validati su HTML Amazon
  reale**: l'integratore CHG-005 fara' il primo round con HTML
  golden statici (CHG separato per la calibrazione). Probabile
  drift gia' al primo touch; aggiornamento iterativo previsto.
- **`parse_eur` heuristica multi-comma**: input come `"12,34,56"`
  ritorna None (parsato male). I test coprono questo caso. Per
  formati non standard, il caller deve normalizzare a monte.
- **`_PlaywrightBrowserPage` skeleton chiamato direttamente**:
  raise immediato NotImplementedError con messaggio esplicito
  che cita CHG-005 + `playwright install`. R-01 rispettato (no
  silent fallback). Test coprono i 3 metodi.
- **`scrape_product` non applica cadence umana**: il delay
  random sara' applicato dall'adapter live in CHG-005 (logica
  pre-`goto`). In CHG-002 i test non aspettano alcun sleep.
- **`scrape_product` con tutti i campi miss**: ritorna
  `ScrapedProduct(asin, title=None, buybox_eur=None)` senza
  raise (missing_ok=True public default). Il caller deve
  trattare il `None` come miss (R-01 a livello caller).

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/scraper.py`,
  `src/talos/io_/selectors.yaml` ✓ (area `io_/` ADR-0013
  consentita).
- **ADR-0017 vincoli rispettati:**
  - Wrapper isolato Playwright dietro `BrowserPageProtocol` ✓
  - Selettori multipli con fallback in `selectors.yaml` ✓
  - User-agent realistico fisso ✓ (Chrome desktop)
  - Cadence umana (delay range esposto come property) ✓
  - No automazione del cart ✓ (solo lookup informativo)
  - Logging strutturato selector mismatch ✓ (`SelectorMissError`
    + telemetria attesa CHG-005)
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `AmazonScraper` +
  classi mappano ad ADR-0017.
- **Backward compat:** modulo nuovo, niente break. `__init__.py`
  re-export estesi (additivo).
- **Impact analysis pre-edit:** primo modulo `io_/scraper.py`
  (zero caller). Esposizione via `__init__.py` re-export non
  rompe consumer (KeepaClient resta esportato uguale).

## Impact

- **Secondo canale ADR-0017 attivato a livello primitive.**
  Resta da implementare il live adapter (CHG-005) e la fallback
  chain caller (`KeepaClient` fail -> `AmazonScraper` chiama).
- **`pyproject.toml` cresce di 2 deps applicative**:
  `playwright`, `pyyaml`. Trascina `pyee`. Aggiunta dev dep
  `types-PyYAML`.
- **5 eventi dormienti ADR-0021** (`keepa.miss`,
  `keepa.rate_limit_hit`, `scrape.selector_fail`,
  `ocr.below_confidence`, `extract.kill_switch`) attendono
  ancora i CHG successivi per attivarsi.
- **`selectors.yaml` versionato in `src/talos/io_/`**:
  configurazione vivente. Modifiche richiedono change document
  (ADR-0017 sez. "Effetti collaterali noti").
- **`parse_eur` riusabile**: helper puro module-level, gia'
  candidato per consumo da Tesseract OCR (CHG-003) sui prezzi
  estratti da PDF/immagini.
- **Avanzamento blocco `io_/extract` Samsung: 2/5**.

## Refs

- ADR: ADR-0017 (canale 2 scraping), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test unit), ADR-0021 (catalogo eventi `scrape.*`
  dormienti).
- Predecessori: CHG-2026-05-01-001 (`KeepaClient` skeleton —
  pattern adapter + R-01 + skeleton live adapter coerente).
- Successori attesi: CHG-2026-05-01-003 (`ocr.py` Tesseract);
  CHG-2026-05-01-004 (`extract/samsung.py` SamsungExtractor +
  R-05); CHG-2026-05-01-005 (integratore fallback chain +
  `_PlaywrightBrowserPage` live + telemetria 5 eventi).
- Memory: `project_io_extract_design_decisions.md` (D2 ratificata
  "default").
- Commit: `ba2421c`.
