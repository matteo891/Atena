"""SerpSearch — adapter SERP Amazon `amazon.it/s?k=<query>` (ADR-0017).

Inaugurato in CHG-2026-05-01-017. Sblocca il primo canale del blocco
"(descrizione, prezzo) -> ASIN": dato un testo libero, ritorna i top-N
ASIN della SERP Amazon.it con titolo e prezzo display. Il caller
(`asin_resolver` CHG-016 + integrazione CHG-018) usa la lista per
calcolare `confidence_pct` via fuzzy title vs descrizione + delta
prezzo verificato con `lookup_product`.

Adapter pattern: `AmazonSerpAdapter` Protocol isola la libreria
Playwright dietro un'interfaccia stabile. `SerpBrowserProtocol`
isola la primitive `goto + evaluate` (NON estende
`BrowserPageProtocol` di CHG-002 per evitare blast radius su mock
esistenti). `_PlaywrightBrowserPage` (CHG-012) soddisfa entrambi i
Protocol via duck typing.

Estrazione strutturata via `page.evaluate(JS)` hardcoded: il JS
itera `[data-component-type="s-search-result"]`, estrae per ogni
risultato `data-asin`, titolo (`h2 a span` o `h2 span`), prezzo
(`.a-price .a-offscreen`). Robust al missing field (skip
risultato senza asin valido).

R-01 NO SILENT DROPS: zero risultati validi -> `[]` esplicito.
Selettori falliti / SERP layout cambiato -> caller (resolver) marca
candidate vuoto + `confidence_pct=0` (gia' previsto da `ResolutionResult`
CHG-016).
"""

from __future__ import annotations

import logging
import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from talos.io_.scraper import parse_eur

if TYPE_CHECKING:
    from collections.abc import Callable
    from decimal import Decimal

_logger = logging.getLogger(__name__)

DEFAULT_SERP_MAX_RESULTS: int = 5
AMAZON_IT_SEARCH_URL_TEMPLATE: str = "https://www.amazon.it/s?k={query}"

# JS hardcoded per estrarre top-N risultati SERP. Itera i container
# `[data-component-type="s-search-result"]` (selettore stabile Amazon SERP),
# estrae per ogni elemento: data-asin (attribute), title (h2 span text),
# price (.a-price .a-offscreen text). Skip risultati senza asin (= banner /
# sponsored a layout diverso). Limit applicato lato JS per ridurre payload.
_SERP_EXTRACT_JS_TEMPLATE: str = """
(() => {
    const items = Array.from(
        document.querySelectorAll('[data-component-type="s-search-result"]')
    );
    const out = [];
    for (const item of items) {
        if (out.length >= MAX_RESULTS) break;
        const asin = item.getAttribute('data-asin') || '';
        if (!asin) continue;
        const titleElem = item.querySelector('h2 a span') || item.querySelector('h2 span');
        const title = titleElem ? titleElem.innerText.trim() : '';
        if (!title) continue;
        const priceElem = item.querySelector('.a-price .a-offscreen');
        const priceText = priceElem ? priceElem.innerText.trim() : '';
        out.push({asin, title, priceText});
    }
    return out;
})()
""".strip()


class SerpBrowserProtocol(Protocol):
    """Browser primitive minimal per SERP scraping.

    Interfaccia separata da `BrowserPageProtocol` (CHG-002) per
    isolamento scope: SERP scraping richiede `evaluate` (JS DOM
    extraction strutturato), product page scraping (CHG-002/013) usa
    selector-based getters singoli. `_PlaywrightBrowserPage` live
    soddisfa entrambi via duck typing.
    """

    def goto(self, url: str) -> None:
        """Naviga al URL. Solleva su errori network (caller li wrappa)."""
        ...

    def evaluate(self, expression: str) -> object:
        """Esegue JS nel contesto della pagina, ritorna risultato JSON-serializable."""
        ...


@dataclass(frozen=True)
class SerpResult:
    """Singolo risultato SERP (top-N).

    `position` 0-based (top-1 = position=0). `price_displayed` `None` se
    il SERP non espone prezzo per quella riga (out-of-stock, "vedi piu'
    offerte", ecc.) — caller calcola confidence con delta_price=None.
    """

    asin: str
    title: str
    price_displayed: Decimal | None
    position: int


class AmazonSerpAdapter(Protocol):
    """Adapter SERP Amazon. Test mock-only via questa interfaccia."""

    def search(
        self,
        query: str,
        *,
        max_results: int = DEFAULT_SERP_MAX_RESULTS,
    ) -> list[SerpResult]:
        """Ritorna top-N risultati SERP per `query`.

        R-01: zero risultati -> `[]` esplicito (no raise). Caller
        decide come trattare (asin_resolver -> ResolutionResult con
        candidates=()).
        """
        ...


class _LiveAmazonSerpAdapter:
    """Adapter SERP live via `_PlaywrightBrowserPage` (CHG-012).

    Pattern: il caller iniettare un `browser_factory` che ritorna un
    `SerpBrowserProtocol` (in produzione: `_PlaywrightBrowserPage`).
    Questo permette riuso del context Chromium per N query in
    sequenza (apertura piu' SERP nel medesimo browser session).

    `goto` URL builder via `urllib.parse.quote`: gestisce caratteri
    speciali, accenti italiani, simboli senza injection rischi.

    `evaluate(JS)` ritorna lista dict; parsiamo prezzi via `parse_eur`
    (CHG-002) -> Decimal o None. Pattern coerente con scraper product
    page.
    """

    def __init__(self, browser_factory: Callable[[], SerpBrowserProtocol]) -> None:
        self._browser_factory = browser_factory

    def search(
        self,
        query: str,
        *,
        max_results: int = DEFAULT_SERP_MAX_RESULTS,
    ) -> list[SerpResult]:
        if not query.strip():
            msg = "query SERP vuota / whitespace-only"
            raise ValueError(msg)
        if max_results <= 0:
            msg = f"max_results deve essere > 0 (ricevuto {max_results})"
            raise ValueError(msg)

        browser = self._browser_factory()
        url = AMAZON_IT_SEARCH_URL_TEMPLATE.format(
            query=urllib.parse.quote(query, safe=""),
        )
        browser.goto(url)
        js = _SERP_EXTRACT_JS_TEMPLATE.replace("MAX_RESULTS", str(max_results))
        raw = browser.evaluate(js)
        return _parse_serp_payload(raw, max_results=max_results)


def _parse_serp_payload(
    raw: object,
    *,
    max_results: int,
) -> list[SerpResult]:
    """Parse list[dict] dal JS evaluate -> list[SerpResult].

    Robust a payload non-list / dict mancanti / type drift. Skip
    risultato malformato con telemetria DEBUG (no R-01 violazione: la
    lista parziale vale).
    """
    if not isinstance(raw, list):
        _logger.debug(
            "scrape.selector_fail",
            extra={
                "asin": "<serp>",
                "field": "serp_payload",
                "selectors_tried": ["data-component-type=s-search-result"],
            },
        )
        return []

    out: list[SerpResult] = []
    for position, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        item_dict = cast("dict[str, Any]", item)
        asin = item_dict.get("asin", "")
        title = item_dict.get("title", "")
        price_text = item_dict.get("priceText", "")
        if not isinstance(asin, str) or not asin:
            continue
        if not isinstance(title, str) or not title:
            continue
        price_displayed: Decimal | None = None
        if isinstance(price_text, str) and price_text.strip():
            try:
                price_displayed = parse_eur(price_text)
            except ValueError:
                price_displayed = None
        out.append(
            SerpResult(
                asin=asin,
                title=title,
                price_displayed=price_displayed,
                position=position,
            ),
        )
        if len(out) >= max_results:
            break
    return out
