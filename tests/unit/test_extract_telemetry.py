"""Test telemetria del cluster `extract/` (CHG-2026-05-01-005 + CHG-B1.1.d).

Verifica `extract.kill_switch` da `SamsungExtractor.match` su R-05 hard.
Pattern `structlog.testing.LogCapture` post-bridge B1.1.d (CHG-2026-05-01-033).
Fixture `log_capture` condivisa in `tests/conftest.py` (CHG-031).

Predecessor: `test_io_extract_telemetry.py` (rinominato qui via `git mv`)
ospitava 5 eventi del blocco io_/extract con caplog stdlib. CHG-032
(B1.1.c) ha estratto i 4 test cluster io_ in `test_io_telemetry.py` con
LogCapture. CHG-033 (B1.1.d) chiude la migrazione anche per cluster
extract: ora il file ospita solo i 4 test `extract.kill_switch` con
LogCapture, e ha nome simmetrico ai fratelli `test_io_telemetry`,
`test_vgp_telemetry`, `test_tetris_telemetry`, `test_panchina_telemetry`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from talos.extract import SamsungEntities, SamsungExtractor

if TYPE_CHECKING:
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# extract.kill_switch (R-05 HARDWARE)
# ---------------------------------------------------------------------------


def test_extract_kill_switch_event_emitted_on_model_mismatch(
    log_capture: LogCapture,
) -> None:
    """R-05: model mismatch hard -> emette `extract.kill_switch`."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12, rom_gb=256)
    amz = SamsungEntities(model="Galaxy S23", ram_gb=12, rom_gb=256)
    result = extractor.match(supplier=sup, amazon=amz)
    assert result.status.value == "MISMATCH"

    kill = [e for e in log_capture.entries if e["event"] == "extract.kill_switch"]
    assert len(kill) == 1
    entry = kill[0]
    assert entry["reason"] == "model_mismatch"
    assert entry["mismatch_field"] == "model"
    assert entry["expected"] == "Galaxy S24"
    assert entry["actual"] == "Galaxy S23"
    # CHG-2026-05-01-007: senza kwarg `asin`, sentinel preservato (backward compat).
    assert entry["asin"] == "<n/a>"


def test_extract_kill_switch_not_emitted_on_low_confidence(
    log_capture: LogCapture,
) -> None:
    """MISMATCH per low confidence (no model mismatch hard) NON emette kill_switch."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model=None, ram_gb=None, rom_gb=None)
    amz = SamsungEntities(model=None, ram_gb=None, rom_gb=None)
    result = extractor.match(supplier=sup, amazon=amz)
    # confidence = 0 / 9 = 0 -> MISMATCH (per low confidence, NON R-05 hardware)
    assert result.status.value == "MISMATCH"

    kill = [e for e in log_capture.entries if e["event"] == "extract.kill_switch"]
    assert kill == []


def test_extract_kill_switch_uses_real_asin_when_provided(
    log_capture: LogCapture,
) -> None:
    """CHG-2026-05-01-007: kwarg `asin` propaga al campo extra dell'evento."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12, rom_gb=256)
    amz = SamsungEntities(model="Galaxy S23", ram_gb=12, rom_gb=256)
    result = extractor.match(supplier=sup, amazon=amz, asin="B0CN3VDM4G")
    assert result.status.value == "MISMATCH"

    kill = [e for e in log_capture.entries if e["event"] == "extract.kill_switch"]
    assert len(kill) == 1
    assert kill[0]["asin"] == "B0CN3VDM4G"


def test_extract_kill_switch_explicit_none_asin_falls_back_to_sentinel(
    log_capture: LogCapture,
) -> None:
    """CHG-2026-05-01-007: passare `asin=None` esplicito mantiene il sentinel."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12)
    amz = SamsungEntities(model="Galaxy A55", ram_gb=12)
    extractor.match(supplier=sup, amazon=amz, asin=None)

    kill = [e for e in log_capture.entries if e["event"] == "extract.kill_switch"]
    assert len(kill) == 1
    assert kill[0]["asin"] == "<n/a>"
