"""Unit test per configure_logging — ADR-0021.

Fixture `log_capture` estratta in `tests/conftest.py` da CHG-2026-05-01-031
(rule of three: ≥3 consumer test telemetria post bridge structlog).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import structlog

from talos.observability import (
    bind_session_context,
    clear_session_context,
    configure_logging,
)

if TYPE_CHECKING:
    from structlog.testing import LogCapture


@pytest.mark.unit
def test_configure_logging_default_no_raise() -> None:
    configure_logging()


@pytest.mark.unit
def test_configure_logging_console_renderer_no_raise() -> None:
    configure_logging(level="DEBUG", json_output=False)


@pytest.mark.unit
def test_configure_logging_invalid_level_raises() -> None:
    with pytest.raises(ValueError, match="Livello log non valido"):
        configure_logging(level="VERBOSE")


@pytest.mark.unit
def test_logger_emits_event_with_kwargs(log_capture: LogCapture) -> None:
    logger = structlog.get_logger()
    logger.info("vgp.veto_roi_failed", asin="B0XYZ", roi_pct=0.05, threshold=0.08)

    assert len(log_capture.entries) == 1
    entry = log_capture.entries[0]
    assert entry["event"] == "vgp.veto_roi_failed"
    assert entry["asin"] == "B0XYZ"
    assert entry["roi_pct"] == pytest.approx(0.05)
    assert entry["threshold"] == pytest.approx(0.08)


@pytest.mark.unit
def test_session_context_propagates(log_capture: LogCapture) -> None:
    clear_session_context()  # parte pulito
    bind_session_context(
        session_id=42,
        listino_hash="a" * 64,
        velocity_target=15,
        budget_eur=10000.0,
    )
    try:
        logger = structlog.get_logger()
        logger.warning("keepa.miss", asin="B0AAA", error_type="timeout", retry_count=3)
        assert len(log_capture.entries) == 1
        entry = log_capture.entries[0]
        assert entry["session_id"] == 42
        assert entry["listino_hash"] == "a" * 64
        assert entry["velocity_target"] == 15
        assert entry["budget_eur"] == pytest.approx(10000.0)
        assert entry["asin"] == "B0AAA"
    finally:
        clear_session_context()


@pytest.mark.unit
def test_clear_session_context_removes_bindings(log_capture: LogCapture) -> None:
    bind_session_context(
        session_id=1,
        listino_hash="x" * 64,
        velocity_target=15,
        budget_eur=100.0,
    )
    clear_session_context()
    logger = structlog.get_logger()
    logger.info("scrape.selector_fail", asin="B0BBB", selector_name="title", html_snippet_hash="h")
    entry = log_capture.entries[0]
    assert "session_id" not in entry
    assert "budget_eur" not in entry
