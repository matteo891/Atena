"""Acquisizione dati esterni — ADR-0017.

Inaugurato in CHG-2026-05-01-001 con `KeepaClient` (canale 1
fallback chain). Esteso in CHG-2026-05-01-002 con `AmazonScraper`
(canale 2 Playwright). Esteso in CHG-2026-05-01-003 con
`OcrPipeline` (canale 3 Tesseract). Esteso in
CHG-2026-05-01-006 con la fallback chain orchestratrice
`lookup_product` (composizione Keepa primario + Scraper
fallback su buybox/title).

Vedi memory `project_io_extract_design_decisions.md` per il
pacchetto D1-D5 ratificato dal Leader.
"""

from talos.io_.fallback_chain import (
    SOURCE_KEEPA,
    SOURCE_SCRAPER,
    ProductData,
    lookup_product,
    lookup_products,
)
from talos.io_.keepa_client import (
    KeepaApiAdapter,
    KeepaClient,
    KeepaMissError,
    KeepaProduct,
    KeepaRateLimitExceededError,
    KeepaTransientError,
)
from talos.io_.ocr import (
    DEFAULT_OCR_CONFIDENCE_THRESHOLD,
    DEFAULT_TESSERACT_LANG,
    OcrPipeline,
    OcrResult,
    OcrStatus,
    RawOcrData,
    TesseractAdapter,
    binarize_otsu,
    otsu_threshold,
)
from talos.io_.scraper import (
    AMAZON_IT_PRODUCT_URL,
    DEFAULT_DELAY_RANGE_S,
    DEFAULT_SELECTORS_YAML,
    DEFAULT_USER_AGENT,
    AmazonScraper,
    BrowserPageProtocol,
    BsrEntry,
    ScrapedProduct,
    SelectorMissError,
    load_selectors,
    parse_bsr_text,
    parse_eur,
)

__all__ = [
    "AMAZON_IT_PRODUCT_URL",
    "DEFAULT_DELAY_RANGE_S",
    "DEFAULT_OCR_CONFIDENCE_THRESHOLD",
    "DEFAULT_SELECTORS_YAML",
    "DEFAULT_TESSERACT_LANG",
    "DEFAULT_USER_AGENT",
    "SOURCE_KEEPA",
    "SOURCE_SCRAPER",
    "AmazonScraper",
    "BrowserPageProtocol",
    "BsrEntry",
    "KeepaApiAdapter",
    "KeepaClient",
    "KeepaMissError",
    "KeepaProduct",
    "KeepaRateLimitExceededError",
    "KeepaTransientError",
    "OcrPipeline",
    "OcrResult",
    "OcrStatus",
    "ProductData",
    "RawOcrData",
    "ScrapedProduct",
    "SelectorMissError",
    "TesseractAdapter",
    "binarize_otsu",
    "load_selectors",
    "lookup_product",
    "lookup_products",
    "otsu_threshold",
    "parse_bsr_text",
    "parse_eur",
]
