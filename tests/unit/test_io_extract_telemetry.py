"""Test caplog per la telemetria del blocco io_/extract (CHG-2026-05-01-005).

Verifica che i 5 eventi canonici dormienti del catalogo ADR-0021
siano emessi quando le condizioni si verificano:
- `keepa.miss` da `KeepaClient.fetch_*` su miss del campo
- `keepa.rate_limit_hit` da `KeepaClient` su rate limit ecceduto
- `scrape.selector_fail` da `AmazonScraper._resolve_field` su drift
- `ocr.below_confidence` da `OcrPipeline.process_image` su AMBIGUOUS
- `extract.kill_switch` da `SamsungExtractor.match` su R-05 hard

Pattern caplog (no Tesseract, no Chromium, no API key reali).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pytest

from talos.extract import SamsungEntities, SamsungExtractor
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
    """Mock page che ritorna sempre None (drift totale)."""

    def goto(self, url: str) -> None:
        pass

    def query_selector_text(self, selector: str) -> str | None:  # noqa: ARG002 — mock
        return None

    def query_selector_xpath_text(self, xpath: str) -> str | None:  # noqa: ARG002 — mock
        return None


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
def test_keepa_miss_event_emitted(field: str, caplog: pytest.LogCaptureFixture) -> None:
    """Ogni miss su buybox/bsr/fee_fba emette `keepa.miss` con error_type=field."""
    adapter = _MissingFieldAdapter(miss_field=field)
    client = KeepaClient(
        api_key="x",
        adapter_factory=lambda _: adapter,
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )
    method = getattr(client, f"fetch_{field}")
    with (
        caplog.at_level(logging.DEBUG, logger="talos.io_.keepa_client"),
        pytest.raises(KeepaMissError),
    ):
        method("B0CN3VDM4G")
    miss_records = [r for r in caplog.records if r.message == "keepa.miss"]
    assert len(miss_records) == 1
    rec = miss_records[0]
    assert rec.asin == "B0CN3VDM4G"  # type: ignore[attr-defined]
    assert rec.error_type == field  # type: ignore[attr-defined]
    assert rec.retry_count == 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# keepa.rate_limit_hit
# ---------------------------------------------------------------------------


def test_keepa_rate_limit_hit_event_emitted(caplog: pytest.LogCaptureFixture) -> None:
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
    with (
        caplog.at_level(logging.DEBUG, logger="talos.io_.keepa_client"),
        pytest.raises(KeepaRateLimitExceededError),
    ):
        client.fetch_buybox("B")
    rl_records = [r for r in caplog.records if r.message == "keepa.rate_limit_hit"]
    assert len(rl_records) == 1
    rec = rl_records[0]
    assert rec.limit == 1  # type: ignore[attr-defined]
    assert rec.requests_in_window == 1  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# scrape.selector_fail
# ---------------------------------------------------------------------------


def test_scrape_selector_fail_event_emitted(caplog: pytest.LogCaptureFixture) -> None:
    """Tutti i selettori falliti -> emette `scrape.selector_fail` (anche con missing_ok)."""
    scraper = AmazonScraper()
    page = _MockEmptyPage()
    with caplog.at_level(logging.DEBUG, logger="talos.io_.scraper"):
        # public scrape_product usa missing_ok=True, ma l'evento e' emesso comunque
        scraper.scrape_product("B0CN3VDM4G", page=page)
    fail_records = [r for r in caplog.records if r.message == "scrape.selector_fail"]
    # Almeno 1 evento (per product_title o buybox_price); idealmente 2 perche'
    # entrambi i campi falliscono col mock empty.
    assert len(fail_records) >= 1
    fields_failed = {r.selector_name for r in fail_records}  # type: ignore[attr-defined]
    assert "product_title" in fields_failed or "buybox_price" in fields_failed


def test_scrape_selector_fail_emitted_also_on_required_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`_resolve_field(missing_ok=False)` emette evento + raise SelectorMissError."""
    scraper = AmazonScraper()
    page = _MockEmptyPage()
    with (
        caplog.at_level(logging.DEBUG, logger="talos.io_.scraper"),
        pytest.raises(SelectorMissError),
    ):
        scraper._resolve_field(  # noqa: SLF001
            "B0CN3VDM4G",
            "product_title",
            page,
            missing_ok=False,
        )
    fail_records = [r for r in caplog.records if r.message == "scrape.selector_fail"]
    assert any(
        r.selector_name == "product_title"  # type: ignore[attr-defined]
        for r in fail_records
    )


# ---------------------------------------------------------------------------
# ocr.below_confidence
# ---------------------------------------------------------------------------


def test_ocr_below_confidence_event_emitted(caplog: pytest.LogCaptureFixture) -> None:
    """Confidence < threshold -> emette `ocr.below_confidence`."""
    pipeline = OcrPipeline(
        confidence_threshold=80,
        adapter_factory=lambda **_: _StaticTesseractAdapter(confidence=50),
    )
    img = np.full((10, 10), 128, dtype=np.uint8)
    with caplog.at_level(logging.DEBUG, logger="talos.io_.ocr"):
        result = pipeline.process_image(img)
    assert result.status.value == "AMBIGUOUS"
    below_records = [r for r in caplog.records if r.message == "ocr.below_confidence"]
    assert len(below_records) == 1
    rec = below_records[0]
    assert rec.confidence == 50.0  # type: ignore[attr-defined]
    assert rec.threshold == 80  # type: ignore[attr-defined]
    assert rec.text_extracted == "some text"  # type: ignore[attr-defined]


def test_ocr_above_threshold_does_not_emit_below(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Confidence >= threshold (status OK) NON emette `ocr.below_confidence`."""
    pipeline = OcrPipeline(
        confidence_threshold=50,
        adapter_factory=lambda **_: _StaticTesseractAdapter(confidence=90),
    )
    img = np.full((10, 10), 128, dtype=np.uint8)
    with caplog.at_level(logging.DEBUG, logger="talos.io_.ocr"):
        pipeline.process_image(img)
    below_records = [r for r in caplog.records if r.message == "ocr.below_confidence"]
    assert below_records == []


# ---------------------------------------------------------------------------
# extract.kill_switch (R-05 HARDWARE)
# ---------------------------------------------------------------------------


def test_extract_kill_switch_event_emitted_on_model_mismatch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """R-05: model mismatch hard -> emette `extract.kill_switch`."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12, rom_gb=256)
    amz = SamsungEntities(model="Galaxy S23", ram_gb=12, rom_gb=256)
    with caplog.at_level(logging.DEBUG, logger="talos.extract.samsung"):
        result = extractor.match(supplier=sup, amazon=amz)
    assert result.status.value == "MISMATCH"
    kill_records = [r for r in caplog.records if r.message == "extract.kill_switch"]
    assert len(kill_records) == 1
    rec = kill_records[0]
    assert rec.reason == "model_mismatch"  # type: ignore[attr-defined]
    assert rec.mismatch_field == "model"  # type: ignore[attr-defined]
    assert rec.expected == "Galaxy S24"  # type: ignore[attr-defined]
    assert rec.actual == "Galaxy S23"  # type: ignore[attr-defined]
    # CHG-2026-05-01-007: senza kwarg `asin`, sentinel preservato (backward compat).
    assert rec.asin == "<n/a>"  # type: ignore[attr-defined]


def test_extract_kill_switch_not_emitted_on_low_confidence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """MISMATCH per low confidence (no model mismatch hard) NON emette kill_switch."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model=None, ram_gb=None, rom_gb=None)
    amz = SamsungEntities(model=None, ram_gb=None, rom_gb=None)
    with caplog.at_level(logging.DEBUG, logger="talos.extract.samsung"):
        result = extractor.match(supplier=sup, amazon=amz)
    # confidence = 0 / 9 = 0 -> MISMATCH (per low confidence, NON R-05 hardware)
    assert result.status.value == "MISMATCH"
    kill_records = [r for r in caplog.records if r.message == "extract.kill_switch"]
    assert kill_records == []


def test_extract_kill_switch_uses_real_asin_when_provided(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CHG-2026-05-01-007: kwarg `asin` propaga al campo extra dell'evento."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12, rom_gb=256)
    amz = SamsungEntities(model="Galaxy S23", ram_gb=12, rom_gb=256)
    with caplog.at_level(logging.DEBUG, logger="talos.extract.samsung"):
        result = extractor.match(supplier=sup, amazon=amz, asin="B0CN3VDM4G")
    assert result.status.value == "MISMATCH"
    kill_records = [r for r in caplog.records if r.message == "extract.kill_switch"]
    assert len(kill_records) == 1
    assert kill_records[0].asin == "B0CN3VDM4G"  # type: ignore[attr-defined]


def test_extract_kill_switch_explicit_none_asin_falls_back_to_sentinel(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CHG-2026-05-01-007: passare `asin=None` esplicito mantiene il sentinel."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12)
    amz = SamsungEntities(model="Galaxy A55", ram_gb=12)
    with caplog.at_level(logging.DEBUG, logger="talos.extract.samsung"):
        extractor.match(supplier=sup, amazon=amz, asin=None)
    kill_records = [r for r in caplog.records if r.message == "extract.kill_switch"]
    assert len(kill_records) == 1
    assert kill_records[0].asin == "<n/a>"  # type: ignore[attr-defined]
