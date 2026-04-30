"""Acquisizione dati esterni — ADR-0017.

Inaugurato in CHG-2026-05-01-001 con `KeepaClient` (canale 1
fallback chain). Esteso in CHG-2026-05-01-002 con `AmazonScraper`
(canale 2 Playwright). Esteso in CHG-2026-05-01-003 con
`OcrPipeline` (canale 3 Tesseract).

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
    ScrapedProduct,
    SelectorMissError,
    load_selectors,
    parse_eur,
)

__all__ = [
    "AMAZON_IT_PRODUCT_URL",
    "DEFAULT_DELAY_RANGE_S",
    "DEFAULT_OCR_CONFIDENCE_THRESHOLD",
    "DEFAULT_SELECTORS_YAML",
    "DEFAULT_TESSERACT_LANG",
    "DEFAULT_USER_AGENT",
    "AmazonScraper",
    "BrowserPageProtocol",
    "KeepaApiAdapter",
    "KeepaClient",
    "KeepaMissError",
    "KeepaProduct",
    "KeepaRateLimitExceededError",
    "KeepaTransientError",
    "OcrPipeline",
    "OcrResult",
    "OcrStatus",
    "RawOcrData",
    "ScrapedProduct",
    "SelectorMissError",
    "TesseractAdapter",
    "binarize_otsu",
    "load_selectors",
    "otsu_threshold",
    "parse_eur",
]
