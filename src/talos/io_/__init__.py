"""Acquisizione dati esterni — ADR-0017.

Inaugurato in CHG-2026-05-01-001 con `KeepaClient` (canale 1
fallback chain). Successivi: `scraper.py` Playwright (canale 2),
`ocr.py` Tesseract (canale 3).

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

__all__ = [
    "KeepaApiAdapter",
    "KeepaClient",
    "KeepaMissError",
    "KeepaProduct",
    "KeepaRateLimitExceededError",
    "KeepaTransientError",
]
