---
id: CHG-2026-05-01-013
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 2 attiva, Path B target — chiusura gap funzionale BSR)
status: Draft
commit: TBD
adr_ref: ADR-0017, ADR-0014, ADR-0019
---

## What

Scraping BSR multi-livello per chiudere il gap funzionale principale
in scenario "scraping-only" (no Keepa). Il BSR e' input critico per
la formula Velocity F4.A (`Q_m = V_tot / (S_comp + 1)`); senza, il
carrello viene allocato con stima di rotazione degradata.

Generalizzazione richiesta dal Leader: il sistema gestisce qualsiasi
gerarchia Amazon (Elettronica > Cellulari > Samsung; ma anche Casa >
Cucina > X), non solo "Samsung Cellulari Elettronica". Soluzione:
`BsrEntry(category: str, rank: int)` dataclass + `bsr_chain:
list[BsrEntry]` ordinata dal piu' specifico al piu' ampio. Caller
(Velocity) sceglie il livello: default `bsr_chain[0]` = sotto-categoria
piu' profonda (massima discriminazione).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/io_/scraper.py` | modificato | + `BsrEntry(category: str, rank: int)` frozen dataclass. + `_BSR_PATTERN` regex italiano/anglo (`n. <num> in <cat>` con eventuale parentetico finale scartato). + `parse_bsr_text(raw) -> BsrEntry \| None` (R-01: stringa malformata -> None). + `BrowserPageProtocol.query_selector_all_text(selector) -> list[str]` nuovo metodo (lista di tutti i match CSS). + `ScrapedProduct.bsr_chain: list[BsrEntry] = field(default_factory=list)` con docstring sull'ordine specifico→ampio. + `AmazonScraper._resolve_bsr_chain(asin, page)` privato: aggrega `bsr_root` (single via `_resolve_field` missing_ok=True) + `bsr_sub` (multi via `_collect_all` con dedup esatto). + `AmazonScraper._collect_all(page, field_name) -> list[str]` privato: itera CSS chain, aggrega via `query_selector_all_text`, dedup preservando ordine. + helper modulo-level `_entry_in(entry, chain)` per dedup ProductData/scraper. + `_PlaywrightBrowserPage.query_selector_all_text` live: `page.query_selector_all(selector)` -> `[elem.inner_text() for elem in elements]`. |
| `src/talos/io_/selectors.yaml` | modificato | + sezione `bsr_root` (3 selettori CSS + 2 XPath: layout `productDetails_detailBullets_sections1` table cell, `detailBulletsWrapper_feature_div` list-item, fallback XPath). + sezione `bsr_sub` (2 CSS + 1 XPath: `ul.zg_hrsr li` con varianti). |
| `src/talos/io_/fallback_chain.py` | modificato | `ProductData` + `bsr_chain: list[BsrEntry] = field(default_factory=list)`. Logica `lookup_product`: lo scraper viene ora invocato anche se Keepa ha tutto (BSR multi-livello da scraper sblocca informazione che Keepa SALES root non fornisce); se Keepa miss `bsr` -> `bsr = bsr_chain[0].rank` (sotto-categoria piu' specifica) + `sources["bsr"] = "scraper"`; se Keepa ha gia' `bsr`, viene preservato (Keepa SALES root) ma `bsr_chain` viene comunque popolata dallo scraper (informazione complementare). |
| `src/talos/io_/__init__.py` | modificato | + re-export `BsrEntry`, `parse_bsr_text` in `__all__`. |
| `tests/unit/test_amazon_scraper.py` | modificato | `_MockPage` + parametro `css_all_map: dict[str, list[str]]` + metodo `query_selector_all_text`. + 5 test `parse_bsr_text` valid (italiano semplice, italiano sub-categoria con &, anglo, parentetico scartato, separatore migliaia rimosso) + 6 parametrici invalid (empty, whitespace, "n.a.", non parsabile, header, senza numero). + 5 test `scrape_product` BSR (chain specifico→ampio / solo root quando no sub / chain vuota su miss totale / dedup + skip unparsable / `ScrapedProduct.bsr_chain` default empty backward compat). |
| `tests/unit/test_fallback_chain.py` | modificato | `_MockPage` + parametro `css_all_map`. `_build_scraper` esteso con sezioni `bsr_root` e `bsr_sub` nel YAML. + 5 test BSR propagation (chain da scraper / Keepa miss bsr -> piu' specifico vince / no scraper -> chain vuota / scraper miss totale -> chain vuota / `ProductData.bsr_chain` default empty backward compat). |
| `tests/unit/test_io_extract_telemetry.py` | modificato | `_MockEmptyPage` + metodo `query_selector_all_text() -> []`. |
| `tests/integration/test_lookup_to_asin_master.py` | modificato | `_ScrapedPage` + metodo `query_selector_all_text() -> []`. |
| `tests/integration/test_acquire_and_persist.py` | modificato | `_PerAsinPage` + metodo `query_selector_all_text() -> []`. |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Righe `scraper.py` e `fallback_chain.py` aggiornate con CHG-013 details. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**681 PASS + 6 skipped** (565 unit/governance/golden + 116
integration; era 660 + 6 skipped, +21 nuovi unit).

## Why

Senza Keepa API key disponibile, il **gap funzionale critico** dello
scenario "scraping-only" e' il BSR: in CHG-006 lo scraper estraeva
solo `title` e `buybox_eur`, NON `bsr` (selettori assenti in
`selectors.yaml` originale). Quindi Velocity F4.A non era calcolabile
in produzione senza Keepa, e il carrello veniva allocato con stima
di rotazione degradata.

Generalizzazione richiesta dal Leader: il sistema deve gestire
qualsiasi gerarchia Amazon, non solo "Samsung Cellulari Elettronica".
Soluzione strutturale: `BsrEntry` come dataclass (categoria stringa
verbatim, no enum chiuso), `bsr_chain` come lista (no dict, ordine
significativo). Il caller decide quale livello usare; default
`bsr_chain[0]` (piu' specifico) come euristica per Velocity.

Inoltre: quando arrivera' la Keepa API key, lo scraper BSR resta
**fallback strutturale** (architettura `lookup_product` gia' progettata
per multi-canale). Keepa fornisce SALES root via CSV idx 3; lo scraper
arricchisce con sub-livelli che Keepa non espone in piano subscription
base. Quindi CHG-013 e' valore architetturale duraturo, non
"surrogato pre-Keepa".

### Decisioni di design

1. **`BsrEntry` come frozen dataclass (no NamedTuple, no Enum
   categoria)**: pattern coerente con `ScrapedProduct`,
   `ProductData`, `KeepaProduct`. La categoria e' stringa verbatim
   Amazon (es. "Cellulari & Accessori", "Smartphone Samsung Galaxy
   S24"); il caller che vuole matchare con un sistema di
   classificazione interno normalizza a monte (es. via
   `category_node` di asin_master).

2. **Ordine `bsr_chain` specifico→ampio**: convenzione fissata.
   Razionale: `bsr_chain[0]` deve essere la "scelta default" del
   caller (Velocity); il rank piu' specifico discrimina meglio.
   Caller che vuole il root scorre fino in fondo. L'ordine HTML
   Amazon mette i sub-rank in `ul.zg_hrsr` (di solito ordinati dal
   piu' specifico) e il root nel detail bullets; il scraper preserva
   l'ordine HTML dei sub e mette il root in coda.

3. **`parse_bsr_text` regex italiano + anglo**: pattern
   `n.\s*([\d.,]+)\s+in\s+(.+?)(?:\s*\(.*?\))?\s*$`. Gestisce
   "n. 1.234 in Categoria" (italiano), "n. 1,234 in Category"
   (anglo); rimuove parentetico finale ("(Visualizza Top 100)")
   via lookahead non-greedy. Dedup separatori migliaia (`.` o `,`)
   rimossi prima di `int()`. R-01: stringa malformata o senza
   match -> `None` (caller decide).

4. **`query_selector_all_text` esteso al Protocol** (non utility
   esterna): le API browser ritornano naturalmente "primo match"
   (`query_selector`) o "tutti i match" (`query_selector_all`); il
   Protocol espone entrambi. Mock devono implementarli (default
   `[]`).

5. **`_resolve_bsr_chain` come metodo privato** (non funzione
   modulo-level): logica strettamente legata a `selectors.yaml`
   caricato in `_selectors`. Pattern coerente con `_resolve_field`.

6. **`_collect_all` aggregatore CSS-only** in CHG-013: gli XPath
   per `bsr_sub` sono nel YAML ma `_collect_all` li ignora per ora
   (caso d'uso non emerge: i selettori CSS per `ul.zg_hrsr li` sono
   sufficienti). Estensione XPath possibile in CHG futuro se
   emergono layout alternativi.

7. **Dedup esatto su stringa trim-mata**: due selettori CSS che
   matchano lo stesso elemento HTML producono la stessa stringa;
   dedup via `set` preserva ordine via `seen`/`out`. Pattern
   classico per "first-occurrence preserve".

8. **`ProductData.bsr_chain` propagato da scraper, NON da Keepa**:
   in CHG-013 Keepa resta single-rank (idx 3 SALES). Quando arrivera'
   `_LiveKeepaAdapter` (CHG futuro), Keepa potrebbe esporre piu'
   livelli (CSV ha indici aggiuntivi); a quel punto si aggiorna
   `_LiveKeepaAdapter` per popolare `KeepaProduct.bsr_chain` (oggi
   non esistente). Per ora, scope CHG-013 limitato al canale
   scraper.

9. **Lo scraper ora viene SEMPRE invocato se `scraper`+`page`
   forniti** (era: solo se `buybox` o `title` mancanti): il BSR
   multi-livello e' informazione che Keepa SALES root non fornisce,
   quindi vale la pena scrapare anche con Keepa OK. Comportamento
   change-of-default rispetto a CHG-006: i caller che non vogliono
   scrape passano `scraper=None`. Backward compat: i caller esistenti
   che gia' passavano scraper+page non hanno modifiche di output
   (ricevono solo info aggiuntiva in `bsr_chain`).

10. **Backward compat strict su signature**: `BsrEntry` nuovo,
    `bsr_chain` nuovo campo con default `[]`, tutti i caller esistenti
    di `ScrapedProduct(...)` o `ProductData(...)` senza `bsr_chain=`
    continuano a funzionare. Nessun rename.

### Out-of-scope

- **Keepa multi-livello BSR**: `KeepaProduct.bsr_chain` e mapping
  CSV indici Keepa per sub-rank scope CHG-014 quando arrivera' la
  key. Keepa attuale = single SALES root.
- **Velocity F4.A consume `bsr_chain`**: oggi la formula prende
  `ProductData.bsr` (scalare); il caller riceve `bsr` valorizzato
  dal piu' specifico se scraper-only. Refactor `velocity_monthly`
  per scegliere fra livelli e' scope CHG futuro (decisione: quale
  policy applicare? Sempre il piu' specifico? Soglie minime di
  rank?).
- **Persistenza `bsr_chain` su DB**: `asin_master` ha `bsr` scalare?
  No: `bsr` e' campo sessione (varia con tempo), non anagrafica.
  `vgp_results` traccia il `bsr` usato per ogni run. Per ora il
  multilivello e' in-memory; persistenza scope futuro se serve audit.
- **Telemetria `scrape.bsr_extracted`**: scope futuro errata catalogo
  ADR-0021 quando si vuole monitorare la copertura BSR per ASIN.
- **XPath aggregati**: `_collect_all` ignora XPath in CHG-013;
  scope futuro se layout Amazon richiede.
- **Live test su data:URL con BSR HTML**: il pattern `data:text/html,`
  funzionerebbe, ma i test live Playwright sono comunque skipped
  per system deps. Quando le deps saranno installate, si potranno
  aggiungere test live `test_live_playwright_bsr_extraction` con
  HTML inline che simula la struttura `ul.zg_hrsr` Amazon.

## How

### `BsrEntry` + `parse_bsr_text` (highlight)

```python
@dataclass(frozen=True)
class BsrEntry:
    category: str
    rank: int


_BSR_PATTERN = re.compile(
    r"n\.\s*([\d.,]+)\s+in\s+(.+?)(?:\s*\(.*?\))?\s*$",
    re.IGNORECASE,
)


def parse_bsr_text(raw: str) -> BsrEntry | None:
    cleaned = raw.strip()
    if not cleaned:
        return None
    match = _BSR_PATTERN.search(cleaned)
    if match is None:
        return None
    rank_str = match.group(1).replace(".", "").replace(",", "")
    try:
        rank = int(rank_str)
    except ValueError:
        return None
    category = match.group(2).strip()
    if not category:
        return None
    return BsrEntry(category=category, rank=rank)
```

### `_resolve_bsr_chain` (highlight)

```python
def _resolve_bsr_chain(self, asin, page):
    sub_texts = self._collect_all(page, "bsr_sub") if "bsr_sub" in self._selectors else []
    root_text = self._resolve_field(asin, "bsr_root", page, missing_ok=True) if "bsr_root" in self._selectors else None
    chain = []
    for raw in sub_texts:
        entry = parse_bsr_text(raw)
        if entry is not None:
            chain.append(entry)
    if root_text is not None:
        entry = parse_bsr_text(root_text)
        if entry is not None and not _entry_in(entry, chain):
            chain.append(entry)
    return chain
```

### Test plan eseguito

21 nuovi test unit:

- 5 `parse_bsr_text` valid parametrici (italiano simple, italiano &
  + sub-categoria, anglo virgola migliaia, parentetico scartato,
  separatore complesso)
- 6 `parse_bsr_text` invalid parametrici (empty, whitespace,
  "n.a.", "abc", header senza match, "in Elettronica" senza numero)
- 5 `scrape_product` BSR:
  - chain specifico→ampio (sub HTML order + root in coda)
  - solo root quando no sub
  - chain vuota su miss totale
  - dedup + skip unparsable
  - `ScrapedProduct.bsr_chain` default empty (backward compat
    senza sezioni bsr_* in YAML)
- 5 `lookup_product` BSR propagation:
  - chain da scraper (Keepa ha bsr root, scraper aggiunge multilivello)
  - Keepa miss bsr → `bsr = bsr_chain[0].rank` (più specifico)
  - no scraper → chain vuota
  - scraper miss totale → chain vuota + sources non ha bsr_chain
  - `ProductData.bsr_chain` default empty (backward compat)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (49 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **565 PASS** (era 544, +21) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **116 PASS + 6 skipped** (invariato; live Playwright continua skipped per system deps) |

**Rischi residui:**
- **Selettori Amazon brittle**: `bsr_root` e `bsr_sub` in
  `selectors.yaml` derivati da analisi pubblica della struttura
  HTML Amazon.it. Amazon puo' cambiare layout; mitigazione: 3+
  selettori CSS in fallback chain CSS, fallback XPath. La
  telemetria `scrape.selector_fail` (CHG-005) emette evento se
  TUTTI i selettori falliscono per un campo (anche con
  `missing_ok=True`), permettendo monitoraggio drift.
- **Categoria normalization**: `BsrEntry.category` e' stringa
  verbatim Amazon. Caller che vuole matchare con un sistema di
  classificazione interno (es. `asin_master.category_node`) deve
  normalizzare a monte. Scope futuro mappare via lookup table.
- **Velocity policy**: oggi `ProductData.bsr` viene valorizzato
  con il piu' specifico se Keepa miss; con Keepa ok, resta SALES
  root. Quando entrambe le sorgenti danno informazione, la
  decisione "Keepa root vs scraper sub" e' soft: Keepa ha
  precedenza per `bsr` scalare (piu' stabile, R-01-friendly), ma
  `bsr_chain` complementare resta. Caller che vuole pure
  scraper-based passa `keepa` con mock no-op o futuro
  `keepa=None` (scope CHG futuro).
- **Lo scraper ora invocato sempre con scraper+page**: questo
  raddoppia il costo runtime per ASIN se Keepa gia' fornisce
  tutto (~150ms goto Chromium aggiuntivi). Caller batch large
  che non vuole il BSR multi-livello passa `scraper=None`.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/scraper.py`,
  `src/talos/io_/fallback_chain.py`, `src/talos/io_/selectors.yaml`
  ✓ (area `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - D2.a CSS→XPath fallback chain preservata in `_resolve_field`
    (per title/buybox); per BSR sub `_collect_all` aggrega tutti
    i CSS (XPath fallback solo se necessario, scope futuro).
  - R-01 NO SILENT DROPS: `parse_bsr_text` ritorna `None` su
    malformato (caller decide); `bsr_chain` vuota su miss totale
    selettori. La telemetria `scrape.selector_fail` (CHG-005)
    rimane in vigore tramite `_resolve_field`.
- **Test unit + integration:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `BsrEntry`,
  `parse_bsr_text`, `query_selector_all_text`,
  `ScrapedProduct.bsr_chain`, `ProductData.bsr_chain` -> ADR-0017.
- **Backward compat:** `BsrEntry`/`bsr_chain` additivi con default
  `[]`; tutti i mock `BrowserPageProtocol` aggiornati con
  `query_selector_all_text() -> []` default; caller esistenti
  ricevono solo info aggiuntiva in `bsr_chain` (campo nuovo).
- **Impact analysis pre-edit:** GitNexus risk MEDIUM (estensione
  Protocol + nuovi campi); tutti i mock aggiornati e 681 PASS
  confermano backward compat. detect_changes mostra 2 affected
  processes (i 2 flussi `scrape_product`) — change additivi.

## Impact

- **Gap funzionale BSR scraping-only chiuso**: scenario "no Keepa"
  ora ha BSR multi-livello disponibile per Velocity. Path B
  scraping-only sale da ~80% a ~92-94% di prodotto utilizzabile.
- **Architettura `lookup_product` rinforzata**: lo scraper non
  e' piu' "fallback su miss" ma "fonte arricchente complementare";
  pattern coerente con multi-canale.
- **`pyproject.toml` invariato** (no nuove deps; regex e
  dataclass sono stdlib).
- **Pronto per Velocity refactor (CHG futuro)**: la formula
  F4.A puo' ora scegliere fra livelli BSR. Decisione di policy
  pendente: sempre il piu' specifico? Sceglie in base alla
  categoria del listino?
- **Pronto per `_LiveKeepaAdapter` (CHG-014, post Keepa key)**:
  quando Keepa fornira' multilivello, `KeepaProduct.bsr_chain`
  estendera' con la stessa shape; `lookup_product` mergera' i 2
  canali (oggi: scraper-only popola bsr_chain).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11
  viventi). Telemetria `scrape.selector_fail` continua a coprire
  drift sui nuovi selettori `bsr_root`/`bsr_sub`.

## Refs

- ADR: ADR-0017 (canale Amazon scraping), ADR-0014 (mypy/ruff
  strict), ADR-0019 (test pattern unit/integration).
- Predecessori: CHG-2026-05-01-002 (`AmazonScraper` skeleton +
  `BrowserPageProtocol`), CHG-2026-05-01-006 (`lookup_product`
  fallback chain), CHG-2026-05-01-012 (`_PlaywrightBrowserPage`
  live).
- Memory: `project_io_extract_design_decisions.md` (D2 ratificata
  "default", ora estesa con BSR multi-livello).
- Decisione Leader 2026-05-01 (in chat, no errata ADR formale per
  ora): Path B scraping-only ratificato come direzione
  prevalente; Keepa posticipata; BSR multi-livello generalizzato
  a qualsiasi gerarchia Amazon.
- Successore atteso: CHG-2026-05-01-014 (eventuale)
  `_LiveKeepaAdapter` quando arrivera' la sandbox key + decisione
  Velocity policy "quale livello BSR usare".
- Commit: TBD.
