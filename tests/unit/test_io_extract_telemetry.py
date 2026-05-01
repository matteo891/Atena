"""Test caplog per la telemetria del cluster `extract/` (CHG-2026-05-01-005).

Verifica `extract.kill_switch` da `SamsungExtractor.match` su R-05 hard.
Pattern caplog stdlib (pre-bridge B1.1.d, atteso CHG futuro).

I test telemetria di `io_/` (keepa/scrape/ocr) sono stati spostati in
`test_io_telemetry.py` con pattern `LogCapture` post-bridge B1.1.c
(CHG-2026-05-01-032). Quando B1.1.d migrerà `extract/`, anche questo
file sarà migrato e probabilmente rinominato `test_extract_telemetry.py`.
"""

from __future__ import annotations

import logging

import pytest

from talos.extract import SamsungEntities, SamsungExtractor

pytestmark = pytest.mark.unit


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
