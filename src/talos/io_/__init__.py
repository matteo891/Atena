"""Acquisizione dati esterni — ADR-0017.

Inaugurato in CHG-2026-05-01-001 con `KeepaClient` (canale 1
fallback chain). Esteso in CHG-2026-05-01-002 con `AmazonScraper`
(canale 2 Playwright). Atteso `ocr.py` Tesseract (canale 3) in
CHG-2026-05-01-003.

Vedi memory `project_io_extract_design_decisions.md` per il
pacchetto D1-D5 ratificato dal Leader.
"""

from talos.io_.keepa_client import (
    KeepaApiAdapter,
    KeepaClient,
    KeepaMissError,
    KeepaProduct,
    KeepaRateLimitExceededError,
    KeepaTransientError,
)
from talos.io_.scraper import (
    AMAZON_IT_PRODUCT_URL,
    DEFAULT_DELAY_RANGE_S,
    DEFAULT_SELECTORS_YAML,
    DEFAULT_USER_AGENT,
    AmazonScraper,
    BrowserPageProtocol,
    ScrapedProduct,
    SelectorMissError,
    load_selectors,
    parse_eur,
)

__all__ = [
    "AMAZON_IT_PRODUCT_URL",
    "DEFAULT_DELAY_RANGE_S",
    "DEFAULT_SELECTORS_YAML",
    "DEFAULT_USER_AGENT",
    "AmazonScraper",
    "BrowserPageProtocol",
    "KeepaApiAdapter",
    "KeepaClient",
    "KeepaMissError",
    "KeepaProduct",
    "KeepaRateLimitExceededError",
    "KeepaTransientError",
    "ScrapedProduct",
    "SelectorMissError",
    "load_selectors",
    "parse_eur",
]
