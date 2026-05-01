"""AmazonScraper — Playwright + selectors.yaml + cadence umana (ADR-0017 canale 2).

CHG-2026-05-01-002 inaugura il secondo canale della fallback chain
ADR-0017. CHG-2026-05-01-005 attiva la telemetria: emette
`scrape.selector_fail` (catalogo ADR-0021) quando tutti i
selettori (CSS+XPath) di un campo falliscono, anche con
`missing_ok=True` (segnale di drift selettori).

Decisioni di design (D2 ratificata "default" Leader
2026-04-30 sera, memory `project_io_extract_design_decisions.md`):

- D2.a Selector fallback: B = CSS -> XPath (2 livelli, no aria).
- D2.b User-agent: A = singolo UA realistico fisso.
- D2.c Browser context: A = fresh ogni run (no `storage_state.json`).

Adapter pattern: `BrowserPageProtocol` isola Playwright per
testabilita' senza Chromium. Test unit usano mock page;
`_PlaywrightBrowserPage` e' uno skeleton (`NotImplementedError`)
da ratificare nell'integratore CHG-2026-05-01-005 (richiede
`playwright install chromium`).
"""

from __future__ import annotations

import contextlib
import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, Self

import yaml
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

if TYPE_CHECKING:
    from collections.abc import Mapping

    from playwright.sync_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        ViewportSize,
    )

_logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
DEFAULT_DELAY_RANGE_S = (1.5, 4.0)
DEFAULT_SELECTORS_YAML = Path(__file__).parent / "selectors.yaml"
AMAZON_IT_PRODUCT_URL = "https://www.amazon.it/dp/{asin}"


@dataclass(frozen=True)
class BsrEntry:
    """Singola voce della classifica Bestseller Amazon (CHG-2026-05-01-013).

    Generalizzata a qualsiasi gerarchia Amazon: una pagina prodotto
    espone tipicamente 2-3 livelli di rank (es. "Elettronica" root +
    "Cellulari" mid + "Smartphone Samsung" deep). `BsrEntry` cattura
    una sola coppia (categoria, rank).

    Ordine convenzione `bsr_chain` (sort `key=rank` ascending):
    rank piu' basso = sotto-categoria piu' specifica (perche' la
    nicchia e' subset della root, quindi il prodotto e' meglio
    piazzato li'). `bsr_chain[0]` e' il livello a maggior valore
    discriminante per la formula Velocity F4.A.

    `category` e' la stringa Amazon verbatim (es. "Cellulari e
    Smartphone", "Smartphone Samsung Galaxy S24"). Il caller che
    vuole matchare con il `category_node` interno deve normalizzarla
    a monte; il dataclass non re-classifica.
    """

    category: str
    rank: int


_BSR_PATTERN = re.compile(
    r"n\.\s*([\d.,]+)\s+in\s+(.+?)(?:\s*\(.*?\))?\s*$",
    re.IGNORECASE,
)


def parse_bsr_text(raw: str) -> BsrEntry | None:
    """Parser di una stringa BSR Amazon.it (CHG-2026-05-01-013).

    Esempi gestiti:
      - "n. 1.234 in Elettronica" -> BsrEntry("Elettronica", 1234)
      - "n. 15 in Cellulari & Accessori" -> BsrEntry("Cellulari & Accessori", 15)
      - "n. 3 in Smartphone Samsung (Visualizza Top 100)" -> BsrEntry("Smartphone Samsung", 3)
      - "n. 1,234 in Electronics" (anglo) -> BsrEntry("Electronics", 1234)
      - "" / "n.a." / "abc" -> None (R-01: caller decide il fallback)

    Heuristica:
      - Match `n. <numero> in <categoria>` (case-insensitive); il
        separatore migliaia `.` o `,` viene rimosso prima di int().
      - Eventuale parentetico finale ("(Visualizza Top 100)") viene
        scartato dalla regex.
      - Categoria: stringa trim-mata.
    """
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


@dataclass(frozen=True)
class ScrapedProduct:
    """Risposta normalizzata dal scraping di amazon.it.

    Un campo `None` significa che il selettore corrispondente non
    ha trovato match, oppure il parsing Decimal e' fallito. Il
    caller (fallback chain, CHG futuro) decide la strategia
    (es. AMBIGUO + R-01 log).

    `bsr_chain` (CHG-2026-05-01-013) contiene tutti i livelli BSR
    estratti, ordinati dal **piu' specifico al piu' ampio** (deep
    -> root). Lista vuota = nessun BSR estratto (selettori miss
    totale). `bsr_chain[0]` e' il livello con maggior valore
    discriminante per la formula Velocity (default).
    """

    asin: str
    title: str | None
    buybox_eur: Decimal | None
    bsr_chain: list[BsrEntry] = field(default_factory=list)


class SelectorMissError(Exception):
    """Tutti i selettori (CSS + XPath) hanno fallito per un campo richiesto.

    R-01 NO SILENT DROPS: il caller deve loggare `scrape.selector_fail`
    (catalogo ADR-0021) e attivare il fallback (OCR / AMBIGUO).
    """

    def __init__(self, asin: str, *, field: str, attempted: list[str]) -> None:
        super().__init__(
            f"Selector miss su {field} per ASIN {asin}; attempted: {attempted}",
        )
        self.asin = asin
        self.field = field
        self.attempted = attempted


class BrowserPageProtocol(Protocol):
    """Interfaccia minimal per una pagina browser.

    Astrazione dietro Playwright Page per testabilita' senza
    Chromium. Test mockano questo Protocol; runtime e'
    `_PlaywrightBrowserPage` (skeleton in CHG-2026-05-01-002,
    completato in CHG-2026-05-01-005).
    """

    def goto(self, url: str) -> None:
        """Naviga alla URL richiesta (o solleva su errore)."""
        ...

    def query_selector_text(self, selector: str) -> str | None:
        """Ritorna text-content del primo elemento CSS, o None se assente."""
        ...

    def query_selector_xpath_text(self, xpath: str) -> str | None:
        """Ritorna text-content del primo elemento XPath, o None se assente."""
        ...

    def query_selector_all_text(self, selector: str) -> list[str]:
        """Ritorna text-content di TUTTI gli elementi CSS che matchano.

        Aggiunto in CHG-2026-05-01-013 per l'estrazione di liste BSR
        multi-livello (es. `ul.zg_hrsr li`). Se il selettore non
        matcha, ritorna `[]`. Stringhe vuote ("") sono filtrate dal
        caller; il Protocol ritorna l'inner_text raw di ogni
        elemento.
        """
        ...


@dataclass(frozen=True)
class _SelectorChain:
    """Raggruppa CSS + XPath fallback per un singolo campo (D2.a)."""

    css: list[str]
    xpath: list[str]


def load_selectors(
    path: Path = DEFAULT_SELECTORS_YAML,
) -> Mapping[str, _SelectorChain]:
    """Carica e parse `selectors.yaml`. Solleva su YAML malformato.

    Schema atteso:

        amazon_it:
          <field_name>:
            css: [<selettore1>, <selettore2>, ...]
            xpath: [<xpath1>, <xpath2>, ...]
    """
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict) or "amazon_it" not in raw:
        msg = f"selectors.yaml invalido in {path}: manca chiave radice 'amazon_it'"
        raise ValueError(msg)
    fields = raw["amazon_it"]
    if not isinstance(fields, dict):
        msg = f"selectors.yaml invalido in {path}: 'amazon_it' deve essere un mapping"
        raise TypeError(msg)
    out: dict[str, _SelectorChain] = {}
    for field_name, chain_raw in fields.items():
        if not isinstance(chain_raw, dict):
            msg = (
                f"selectors.yaml invalido: campo '{field_name}' deve avere chiavi 'css' e/o 'xpath'"
            )
            raise TypeError(msg)
        css_list = chain_raw.get("css") or []
        xpath_list = chain_raw.get("xpath") or []
        out[field_name] = _SelectorChain(css=list(css_list), xpath=list(xpath_list))
    return out


def parse_eur(raw: str) -> Decimal | None:
    """Parser robusto per prezzi in EUR (italiano + anglo-sassone).

    Esempi gestiti:
      - "€ 199,99" / "199,99 €" -> Decimal('199.99')
      - "EUR 1.234,56"          -> Decimal('1234.56')
      - "1,234.56"              -> Decimal('1234.56') (anglo)
      - "199.99"                -> Decimal('199.99')

    Heuristica: se sono presenti sia ',' che '.', l'ULTIMO dei due
    e' il separatore decimale (l'altro e' migliaia). Se solo virgola,
    diventa decimale. Se solo punto, e' gia' decimale.

    Ritorna None su input non parsabile (R-01: il caller decide).
    """
    cleaned = raw.replace("€", "").replace("EUR", "").replace("\xa0", " ").strip()
    if not cleaned:
        return None
    has_comma = "," in cleaned
    has_dot = "." in cleaned
    if has_comma and has_dot:
        if cleaned.rindex(",") > cleaned.rindex("."):
            # Italiano: 1.234,56 -> 1234.56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Anglo: 1,234.56 -> 1234.56
            cleaned = cleaned.replace(",", "")
    elif has_comma:
        cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


class AmazonScraper:
    """Scraper Amazon.it con fallback CSS->XPath e cadence umana.

    Uso runtime:

        scraper = AmazonScraper()
        page = _PlaywrightBrowserPage(...)  # CHG-2026-05-01-005 integratore
        product = scraper.scrape_product("B0CN3VDM4G", page=page)

    Uso test (mock page, no Chromium):

        scraper = AmazonScraper(selectors_path=tmp_yaml)
        product = scraper.scrape_product("X", page=mock_page)
    """

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        delay_range_s: tuple[float, float] = DEFAULT_DELAY_RANGE_S,
        selectors_path: Path = DEFAULT_SELECTORS_YAML,
    ) -> None:
        self._user_agent = user_agent
        self._delay_range_s = delay_range_s
        self._selectors = load_selectors(selectors_path)

    @property
    def user_agent(self) -> str:
        return self._user_agent

    @property
    def delay_range_s(self) -> tuple[float, float]:
        return self._delay_range_s

    def scrape_product(self, asin: str, *, page: BrowserPageProtocol) -> ScrapedProduct:
        """Scrape product page per `asin` usando la `page` iniettata.

        Logica:
          1. Naviga a `https://www.amazon.it/dp/{asin}`.
          2. Per ogni campo (`product_title`, `buybox_price`):
             tenta tutti i selettori CSS in ordine; se tutti
             falliscono, tenta gli XPath. Primo match -> vince.
          3. Parsing Decimal su `buybox_price` (gestione virgola
             decimale italiana via `parse_eur`).
          4. **BSR multi-livello (CHG-2026-05-01-013)**: estrae il
             rank root via `bsr_root` (testo grezzo "n. 1.234 in
             Elettronica") + i sub-rank via `bsr_sub` (lista di
             stringhe "n. 15 in Cellulari", "n. 3 in Smartphone
             Samsung", ecc.). `parse_bsr_text` parsa ogni stringa.
             La `bsr_chain` finale e' ordinata dal piu' specifico
             al piu' ampio: prima i sub (ordine HTML preservato),
             poi il root in coda. Lista vuota se selettori miss
             totale.
          5. Ritorna `ScrapedProduct` (campi opzionali = None su
             miss; `bsr_chain` lista, possibilmente vuota).

        Raises:
            SelectorMissError: solo se invocato in modalita'
            `missing_ok=False` su `_resolve_field`. La signature
            pubblica usa `missing_ok=True` (caller gestisce i None).
        """
        url = AMAZON_IT_PRODUCT_URL.format(asin=asin)
        page.goto(url)
        title_raw = self._resolve_field(asin, "product_title", page, missing_ok=True)
        buybox_raw = self._resolve_field(asin, "buybox_price", page, missing_ok=True)
        bsr_chain = self._resolve_bsr_chain(asin, page)
        return ScrapedProduct(
            asin=asin,
            title=title_raw,
            buybox_eur=parse_eur(buybox_raw) if buybox_raw is not None else None,
            bsr_chain=bsr_chain,
        )

    def _resolve_bsr_chain(
        self,
        asin: str,
        page: BrowserPageProtocol,
    ) -> list[BsrEntry]:
        """Estrae la `bsr_chain` multi-livello (CHG-2026-05-01-013).

        Ordine output: dal piu' specifico al piu' ampio (sub
        prima, root in fondo). Sia `bsr_sub` che `bsr_root`
        vengono raccolti con `_collect_all` (lista di tutti i
        match CSS); `parse_bsr_text` filtra naturalmente le
        stringhe che NON contengono il pattern "n. <num> in
        <cat>" (es. altre righe della tabella tech specs come
        peso/dimensioni). Dedup esatto su (categoria, rank).
        """
        del asin  # logging delegato a `_resolve_field` chiamato da altri campi
        chain: list[BsrEntry] = []
        seen: set[tuple[str, int]] = set()

        for field_name in ("bsr_sub", "bsr_root"):
            if field_name not in self._selectors:
                continue
            for raw in self._collect_all(page, field_name):
                entry = parse_bsr_text(raw)
                if entry is None:
                    continue
                key = (entry.category, entry.rank)
                if key in seen:
                    continue
                seen.add(key)
                chain.append(entry)

        # Ordinamento "specifico → ampio" via rank crescente: per
        # definizione, una sotto-categoria e' subset della root,
        # quindi `rank_sub <= rank_root` (il prodotto e' meglio
        # piazzato nella nicchia che nella categoria larga).
        # Validato live 2026-05-01 su B0CSTC2RDW (Samsung S24):
        # Amazon.it ritorna root prima nel DOM ("Elettronica" #6182)
        # poi sub ("Cellulari e Smartphone" #162); il sort restituisce
        # sub→root come da convenzione `bsr_chain[0]` = piu' specifico.
        chain.sort(key=lambda e: e.rank)
        return chain

    def _collect_all(
        self,
        page: BrowserPageProtocol,
        field_name: str,
    ) -> list[str]:
        """Itera i selettori CSS+XPath del campo, raccoglie TUTTI i match.

        Differenza con `_resolve_field`: quello ritorna il primo
        non-empty (vincitore), questo aggrega da tutti i selettori
        CSS via `page.query_selector_all_text` (XPath fallback per
        ora omesso: i casi d'uso CHG-013 hanno selettori CSS
        sufficienti). Ordine di prima apparizione preservato,
        deduplica esatta su stringa trim-mata.
        """
        chain = self._selectors[field_name]
        seen: set[str] = set()
        out: list[str] = []
        for css in chain.css:
            for raw in page.query_selector_all_text(css):
                stripped = raw.strip()
                if not stripped or stripped in seen:
                    continue
                seen.add(stripped)
                out.append(stripped)
        return out

    def _resolve_field(
        self,
        asin: str,
        field: str,
        page: BrowserPageProtocol,
        *,
        missing_ok: bool,
    ) -> str | None:
        """Tenta CSS chain, poi XPath chain. Primo non-empty vince."""
        if field not in self._selectors:
            msg = f"Campo '{field}' non presente in selectors.yaml"
            raise KeyError(msg)
        chain = self._selectors[field]
        attempted: list[str] = []
        for css in chain.css:
            attempted.append(f"css:{css}")
            value = page.query_selector_text(css)
            if value is not None and value.strip():
                return value.strip()
        for xpath in chain.xpath:
            attempted.append(f"xpath:{xpath}")
            value = page.query_selector_xpath_text(xpath)
            if value is not None and value.strip():
                return value.strip()
        # Tutti i selettori (CSS + XPath) hanno fallito per questo campo.
        # Telemetria CHG-2026-05-01-005: evento canonico ADR-0021,
        # emesso anche con missing_ok=True (segnale di drift selettori).
        _logger.debug(
            "scrape.selector_fail",
            extra={
                "asin": asin,
                "selector_name": field,
                "html_snippet_hash": "<no-html>",
            },
        )
        if missing_ok:
            return None
        raise SelectorMissError(asin, field=field, attempted=attempted)


DEFAULT_PLAYWRIGHT_TIMEOUT_MS = 60_000  # 60s (decisione Leader B, CHG-012)
COOKIE_CONSENT_SELECTOR_AMAZON = "#sp-cc-accept"


class _PlaywrightBrowserPage:
    """Adapter live su Playwright sync. Ratificato in CHG-2026-05-01-012.

    Decisioni Leader Fase 3 (default ratificati 2026-05-01):

    - **Cookie consent GDPR Amazon (A)**: post-goto, click best-effort
      su `#sp-cc-accept`; nessuna eccezione se l'overlay non c'e'.
    - **Stealth strategy (B medium)**: `playwright-stealth` applicato
      al page nel `_ensure_started` (riduce fingerprint
      `navigator.webdriver`, sec-ch-ua, plugins, ecc.) + viewport
      realistico (1920x1080) + UA fisso (D2.b).
    - **Timeout `goto` (B)**: 60s default (configurabile via `__init__`).

    Pattern lazy-init + context manager: il browser viene aperto
    al primo `goto` (o all'`__enter__`); `close()` rilascia tutte
    le risorse Playwright (page -> context -> browser -> playwright
    process). Riusabile fra piu' ASIN nello stesso ciclo (riuso
    context Chromium come previsto da `lookup_products` CHG-009).

    Esempio uso runtime:

        with _PlaywrightBrowserPage() as page:
            for asin in asin_list:
                product = scraper.scrape_product(asin, page=page)

    Esempio uso test:

        page = _PlaywrightBrowserPage()
        try:
            page.goto("data:text/html,<h1 id='t'>x</h1>")
            assert page.query_selector_text("#t") == "x"
        finally:
            page.close()
    """

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_ms: int = DEFAULT_PLAYWRIGHT_TIMEOUT_MS,
        viewport: ViewportSize | None = None,
        apply_stealth: bool = True,
    ) -> None:
        self._user_agent = user_agent
        self._timeout_ms = timeout_ms
        # ViewportSize e' un TypedDict; copia per evitare default mutabile condiviso.
        self._viewport: ViewportSize = (
            viewport if viewport is not None else {"width": 1920, "height": 1080}
        )
        self._apply_stealth = apply_stealth
        # Lazy-init: aperti al primo `goto()` o al `__enter__`.
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

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

    def goto(self, url: str) -> None:
        page = self._ensure_started()
        page.goto(url, wait_until="domcontentloaded")
        # Cookie consent GDPR (decisione A): best-effort, no raise.
        self._dismiss_cookie_overlay(page)

    @staticmethod
    def _dismiss_cookie_overlay(page: Page) -> None:
        """Chiude overlay GDPR Amazon se presente. R-01 best-effort.

        L'overlay puo' non comparire (ASIN non-Amazon, sessione gia'
        consensata via cookie, A/B test Amazon). Il fallimento del
        click NON deve far fallire lo scraping.
        """
        with contextlib.suppress(Exception):
            btn = page.query_selector(COOKIE_CONSENT_SELECTOR_AMAZON)
            if btn is not None:
                btn.click(timeout=2_000)

    def query_selector_text(self, selector: str) -> str | None:
        if self._page is None:
            return None
        elem = self._page.query_selector(selector)
        if elem is None:
            return None
        return elem.inner_text()

    def query_selector_xpath_text(self, xpath: str) -> str | None:
        if self._page is None:
            return None
        # Playwright accetta XPath via prefisso `xpath=`.
        elem = self._page.query_selector(f"xpath={xpath}")
        if elem is None:
            return None
        return elem.inner_text()

    def query_selector_all_text(self, selector: str) -> list[str]:
        if self._page is None:
            return []
        elements = self._page.query_selector_all(selector)
        return [elem.inner_text() for elem in elements]

    def close(self) -> None:
        """Rilascia risorse Playwright in ordine inverso di creazione.

        Idempotente: chiamabile piu' volte senza effetto. Caller deve
        invocare `close()` (manualmente o via context manager) per
        evitare process Chromium zombie.
        """
        if self._context is not None:
            with contextlib.suppress(Exception):
                self._context.close()
            self._context = None
        if self._browser is not None:
            with contextlib.suppress(Exception):
                self._browser.close()
            self._browser = None
        if self._playwright is not None:
            with contextlib.suppress(Exception):
                self._playwright.stop()
            self._playwright = None
        self._page = None

    def __enter__(self) -> Self:
        self._ensure_started()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
