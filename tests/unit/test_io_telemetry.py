"""Test telemetria del cluster `io_/` (CHG-2026-05-01-005 + CHG-B1.1.c).

Verifica che gli eventi canonici dormienti del catalogo ADR-0021
siano emessi quando le condizioni si verificano:
- `keepa.miss` da `KeepaClient.fetch_*` su miss del campo
- `keepa.rate_limit_hit` da `KeepaClient` su rate limit ecceduto
- `scrape.selector_fail` da `AmazonScraper._resolve_field` su drift
- `ocr.below_confidence` da `OcrPipeline.process_image` su AMBIGUOUS

Pattern `structlog.testing.LogCapture` (post-bridge B1.1.c).
Fixture `log_capture` condivisa in `tests/conftest.py` (CHG-031).

Test su `extract.kill_switch` restano in `test_io_extract_telemetry.py`
(pattern caplog stdlib) finché CHG-B1.1.d non migra anche `extract/`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pytest

from talos.io_ import (
    AmazonScraper,
    KeepaClient,
    KeepaMissError,
    KeepaProduct,
    KeepaRateLimitExceededError,
    OcrPipeline,
    RawOcrData,
    SelectorMissError,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MissingFieldAdapter:
    """Adapter Keepa che ritorna sempre product con campo richiesto = None."""

    def __init__(self, *, miss_field: str) -> None:
        self.miss_field = miss_field

    def query(self, asin: str) -> KeepaProduct:
        return KeepaProduct(
            asin=asin,
            buybox_eur=None if self.miss_field == "buybox" else Decimal(100),
            bsr=None if self.miss_field == "bsr" else 1234,
            fee_fba_eur=None if self.miss_field == "fee_fba" else Decimal(4),
        )


class _MockEmptyPage:
    """Mock page che ritorna sempre None / [] (drift totale)."""

    def goto(self, url: str) -> None:
        pass

    def query_selector_text(self, selector: str) -> str | None:  # noqa: ARG002 — mock
        return None

    def query_selector_xpath_text(self, xpath: str) -> str | None:  # noqa: ARG002 — mock
        return None

    def query_selector_all_text(self, selector: str) -> list[str]:  # noqa: ARG002 — mock
        return []


class _StaticTesseractAdapter:
    """Adapter Tesseract con confidence configurabile."""

    def __init__(self, *, confidence: int) -> None:
        self.confidence = confidence

    def image_to_data(
        self,
        image: NDArray[np.uint8],  # noqa: ARG002 — mock
        *,
        lang: str,  # noqa: ARG002 — mock
    ) -> RawOcrData:
        return RawOcrData(text="some text", word_confidences=[self.confidence])


# ---------------------------------------------------------------------------
# keepa.miss
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["buybox", "bsr", "fee_fba"])
def test_keepa_miss_event_emitted(field: str, log_capture: LogCapture) -> None:
    """Ogni miss su buybox/bsr/fee_fba emette `keepa.miss` con error_type=field."""
    adapter = _MissingFieldAdapter(miss_field=field)
    client = KeepaClient(
        api_key="x",
        adapter_factory=lambda _: adapter,
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )
    method = getattr(client, f"fetch_{field}")
    with pytest.raises(KeepaMissError):
        method("B0CN3VDM4G")
    miss = [e for e in log_capture.entries if e["event"] == "keepa.miss"]
    assert len(miss) == 1
    entry = miss[0]
    assert entry["asin"] == "B0CN3VDM4G"
    assert entry["error_type"] == field
    assert entry["retry_count"] == 0


# ---------------------------------------------------------------------------
# keepa.rate_limit_hit
# ---------------------------------------------------------------------------


def test_keepa_rate_limit_hit_event_emitted(log_capture: LogCapture) -> None:
    """Rate limit ecceduto emette `keepa.rate_limit_hit` con limit/requests_in_window."""

    class _OkAdapter:
        def query(self, asin: str) -> KeepaProduct:  # noqa: ARG002 — mock
            return KeepaProduct(
                asin="X",
                buybox_eur=Decimal(100),
                bsr=1,
                fee_fba_eur=Decimal(4),
            )

    client = KeepaClient(
        api_key="x",
        rate_limit_per_minute=1,
        adapter_factory=lambda _: _OkAdapter(),
    )
    client.fetch_buybox("A")  # consuma il singolo permit
    with pytest.raises(KeepaRateLimitExceededError):
        client.fetch_buybox("B")
    rl = [e for e in log_capture.entries if e["event"] == "keepa.rate_limit_hit"]
    assert len(rl) == 1
    entry = rl[0]
    assert entry["limit"] == 1
    assert entry["requests_in_window"] == 1


# ---------------------------------------------------------------------------
# scrape.selector_fail
# ---------------------------------------------------------------------------


def test_scrape_selector_fail_event_emitted(log_capture: LogCapture) -> None:
    """Tutti i selettori falliti -> emette `scrape.selector_fail` (anche con missing_ok)."""
    scraper = AmazonScraper()
    page = _MockEmptyPage()
    # public scrape_product usa missing_ok=True, ma l'evento e' emesso comunque
    scraper.scrape_product("B0CN3VDM4G", page=page)
    fail = [e for e in log_capture.entries if e["event"] == "scrape.selector_fail"]
    # Almeno 1 evento (per product_title o buybox_price); idealmente 2 perche'
    # entrambi i campi falliscono col mock empty.
    assert len(fail) >= 1
    fields_failed = {e["selector_name"] for e in fail}
    assert "product_title" in fields_failed or "buybox_price" in fields_failed


def test_scrape_selector_fail_emitted_also_on_required_call(
    log_capture: LogCapture,
) -> None:
    """`_resolve_field(missing_ok=False)` emette evento + raise SelectorMissError."""
    scraper = AmazonScraper()
    page = _MockEmptyPage()
    with pytest.raises(SelectorMissError):
        scraper._resolve_field(  # noqa: SLF001
            "B0CN3VDM4G",
            "product_title",
            page,
            missing_ok=False,
        )
    fail = [e for e in log_capture.entries if e["event"] == "scrape.selector_fail"]
    assert any(e["selector_name"] == "product_title" for e in fail)


# ---------------------------------------------------------------------------
# ocr.below_confidence
# ---------------------------------------------------------------------------


def test_ocr_below_confidence_event_emitted(log_capture: LogCapture) -> None:
    """Confidence < threshold -> emette `ocr.below_confidence`."""
    pipeline = OcrPipeline(
        confidence_threshold=80,
        adapter_factory=lambda **_: _StaticTesseractAdapter(confidence=50),
    )
    img = np.full((10, 10), 128, dtype=np.uint8)
    result = pipeline.process_image(img)
    assert result.status.value == "AMBIGUOUS"
    below = [e for e in log_capture.entries if e["event"] == "ocr.below_confidence"]
    assert len(below) == 1
    entry = below[0]
    assert entry["confidence"] == 50.0
    assert entry["threshold"] == 80
    assert entry["text_extracted"] == "some text"


def test_ocr_above_threshold_does_not_emit_below(log_capture: LogCapture) -> None:
    """Confidence >= threshold (status OK) NON emette `ocr.below_confidence`."""
    pipeline = OcrPipeline(
        confidence_threshold=50,
        adapter_factory=lambda **_: _StaticTesseractAdapter(confidence=90),
    )
    img = np.full((10, 10), 128, dtype=np.uint8)
    pipeline.process_image(img)
    below = [e for e in log_capture.entries if e["event"] == "ocr.below_confidence"]
    assert below == []
