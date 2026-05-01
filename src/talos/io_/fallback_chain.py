"""Fallback chain orchestratrice — `lookup_product` (ADR-0017).

CHG-2026-05-01-006 inaugura la fallback chain che compone i tre
canali `io_/` introdotti nei CHG-001..003: Keepa primario,
AmazonScraper fallback su `buybox`/`title`, OCR come parametro
placeholder per estensioni future.

Il modulo NON tocca DB, NON estrae entita' brand-specific
(SamsungExtractor resta separato in `extract/`), NON istanzia
adapter live: e' orchestrazione pura di Protocol gia' esistenti
e mockabili. Tutti i live adapters (`_LiveKeepaAdapter`,
`_PlaywrightBrowserPage`, `_LiveTesseractAdapter`) restano
skeleton in attesa di sessione dedicata con setup di sistema
(apt install tesseract-ocr-ita-eng + playwright install chromium
+ sandbox API key Keepa).

Strategia di composizione:

1. **Keepa** (primario): tre `fetch_*` indipendenti su
   `buybox_eur` / `bsr` / `fee_fba_eur`. Ogni `KeepaMissError`
   viene catturato e annotato in `notes`; non interrompe la chain.
2. **AmazonScraper** (fallback opzionale): invocato solo se
   `buybox_eur` o `title` sono ancora `None` dopo Keepa, e solo
   se `scraper` + `page` sono entrambi forniti. Lo scraper
   fornisce `title` (Keepa non lo espone) e puo' coprire
   `buybox_eur` se Keepa ha avuto miss. NON copre `bsr` ne'
   `fee_fba_eur` (i selettori in `selectors.yaml` non li
   estraggono in CHG-006).
3. **OcrPipeline** (placeholder): parametro accettato per
   signature compatibility con la nota d'handoff
   2026-05-01, ma NON invocato in CHG-006. OCR sui PDF
   fornitore Samsung e' canale separato (input listino, non
   ASIN lookup). OCR su screenshot Amazon e' scope futuro.

R-01 NO SILENT DROPS:
- `KeepaMissError` -> field=None in `ProductData` + entry in
  `notes` ("keepa miss <field> per <asin>"). Caller decide
  come gestire (es. `fee_fba=None` -> caller chiama
  `fee_fba_manual` L11b CHG-2026-04-30-022).
- `KeepaRateLimitExceededError` / `KeepaTransientError`:
  propagati al caller (fail-fast, non sono miss
  deterministici).
- `SelectorMissError` (con `missing_ok=False`): NON sollevato
  in `lookup_product` perche' lo scraper e' invocato sempre
  con `missing_ok=True` di default in `scrape_product`. La
  telemetria `scrape.selector_fail` e' gia' emessa dal
  scraper stesso (CHG-005).

Nessun nuovo evento canonico ADR-0021 viene introdotto: la
fallback chain e' orchestrazione, e i sotto-moduli emettono
gia' i 5 eventi `keepa.miss` / `keepa.rate_limit_hit` /
`scrape.selector_fail` / `ocr.below_confidence` /
`extract.kill_switch` ai siti di produzione.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeVar

from talos.io_.keepa_client import KeepaMissError

if TYPE_CHECKING:
    from collections.abc import Callable
    from decimal import Decimal

    from talos.io_.keepa_client import KeepaClient
    from talos.io_.ocr import OcrPipeline
    from talos.io_.scraper import AmazonScraper, BrowserPageProtocol

_T = TypeVar("_T")


SOURCE_KEEPA = "keepa"
SOURCE_SCRAPER = "scraper"


@dataclass(frozen=True)
class ProductData:
    """Risultato di `lookup_product` per un singolo ASIN.

    Tutti i campi dato sono opzionali (`None` su miss totale dei
    canali coinvolti). Il caller decide come gestire i `None`:
    `fee_fba_eur=None` -> `fee_fba_manual` L11b; `buybox_eur=None`
    -> riga AMBIGUA per validazione CFO; `title=None` -> ASIN
    senza titolo (potrebbe comparire vuoto in cruscotto).

    `sources` mappa ogni campo non-None al canale che l'ha
    fornito (audit trail). `notes` contiene messaggi diagnostici
    in formato libero (R-01 trail leggibile).
    """

    asin: str
    buybox_eur: Decimal | None
    bsr: int | None
    fee_fba_eur: Decimal | None
    title: str | None
    sources: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def lookup_product(
    asin: str,
    *,
    keepa: KeepaClient,
    scraper: AmazonScraper | None = None,
    page: BrowserPageProtocol | None = None,
    ocr: OcrPipeline | None = None,  # noqa: ARG001 — placeholder signature CHG-006
) -> ProductData:
    """Risolve i dati prodotto per `asin` componendo i canali `io_/`.

    Algoritmo:

        1. Per ogni campo Keepa (buybox_eur, bsr, fee_fba_eur):
           - try fetch -> success: popola campo + sources[field]="keepa"
           - KeepaMissError -> field resta None + notes annota miss
        2. Se (buybox_eur is None or title is None) AND scraper
           AND page: invoca `scraper.scrape_product(asin, page=page)`.
           - title is None and scraped.title is not None -> popola
             title + sources["title"]="scraper"
           - buybox_eur is None and scraped.buybox_eur is not None
             -> popola buybox_eur + sources["buybox_eur"]="scraper"
        3. OCR: parametro accettato ma non invocato in CHG-006.

    Eccezioni propagate al caller (NON catturate):
        - `KeepaRateLimitExceededError`: rate limit hard locale.
          Caller decide se aspettare o rivedere il limite.
        - `KeepaTransientError`: errore transitorio dopo retry
          esauriti. Caller decide se ritentare a livello
          applicativo (es. job batch).
        - Qualunque eccezione raise dal `page.goto` (Playwright
          live errors).

    Args:
        asin: ASIN Amazon target.
        keepa: client Keepa configurato (rate-limit + retry).
        scraper: AmazonScraper opzionale. Se None, il fallback
          su Amazon non viene tentato.
        page: pagina Playwright opzionale. Necessaria con
          `scraper`. Se `scraper` e' fornito ma `page` e' None,
          lo scraper non viene invocato (graceful degrade).
        ocr: OcrPipeline opzionale. Placeholder CHG-006 non
          invocato (vedi modulo docstring).

    Returns:
        ProductData con campi popolati (al meglio possibile) +
        sources audit trail + notes R-01.
    """
    sources: dict[str, str] = {}
    notes: list[str] = []

    buybox_eur, sources, notes = _try_keepa_field(
        keepa.fetch_buybox,
        asin,
        "buybox_eur",
        sources,
        notes,
    )
    bsr, sources, notes = _try_keepa_field(
        keepa.fetch_bsr,
        asin,
        "bsr",
        sources,
        notes,
    )
    fee_fba_eur, sources, notes = _try_keepa_field(
        keepa.fetch_fee_fba,
        asin,
        "fee_fba_eur",
        sources,
        notes,
    )

    title: str | None = None
    needs_scrape = (
        scraper is not None and page is not None and (buybox_eur is None or title is None)
    )
    if needs_scrape:
        assert scraper is not None  # noqa: S101 — narrow per mypy
        assert page is not None  # noqa: S101 — narrow per mypy
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


def _try_keepa_field(
    fetcher: Callable[[str], _T],
    asin: str,
    field_name: str,
    sources: dict[str, str],
    notes: list[str],
) -> tuple[_T | None, dict[str, str], list[str]]:
    """Helper: invoca `fetcher(asin)`, gestisce `KeepaMissError`.

    Ritorna la tripla `(value, sources, notes)` con `value=None`
    su miss e `notes` esteso con un messaggio diagnostico.
    `KeepaRateLimitExceededError` / `KeepaTransientError` NON
    sono catturati (propagano al caller).
    """
    try:
        value = fetcher(asin)
    except KeepaMissError as exc:
        notes.append(f"keepa miss {exc.field} per {asin}")
        return None, sources, notes
    sources[field_name] = SOURCE_KEEPA
    return value, sources, notes
