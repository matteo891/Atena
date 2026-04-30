"""Test unit per `talos.vgp.veto` (CHG-2026-04-30-027, ADR-0018).

Boundary R-08 verbatim: "ROI inferiore all'8%" -> strict `<`.
ROI esattamente 0.08 PASSA (non vetato). Test ancorano questa
convenzione esplicitamente.
"""

from __future__ import annotations

import pytest

from talos.vgp import DEFAULT_ROI_VETO_THRESHOLD, is_vetoed_by_roi

pytestmark = pytest.mark.unit


def test_default_threshold_is_eight_percent() -> None:
    """R-08 verbatim: 8% = 0.08. Ancora la costante esposta."""
    assert DEFAULT_ROI_VETO_THRESHOLD == 0.08


def test_vetoes_below_default_threshold() -> None:
    """ROI 7% (sotto soglia 8%) -> vetato."""
    assert is_vetoed_by_roi(0.07) is True


def test_passes_at_default_threshold() -> None:
    """Boundary R-08 verbatim: 'inferiore all'8%' -> 0.08 PASSA (strict <)."""
    assert is_vetoed_by_roi(0.08) is False


def test_passes_above_default_threshold() -> None:
    """ROI 15% (sopra soglia) -> passa."""
    assert is_vetoed_by_roi(0.15) is False


def test_vetoes_negative_roi() -> None:
    """Loss propaga: ROI negativo -> sempre vetato."""
    assert is_vetoed_by_roi(-0.10) is True


def test_custom_threshold_below_default() -> None:
    """Threshold custom 4%: ROI 5% (sopra custom) passa."""
    assert is_vetoed_by_roi(0.05, threshold=0.04) is False


def test_custom_threshold_above_default_vetoes() -> None:
    """Threshold custom 20%: ROI 15% (sotto custom) vetato."""
    assert is_vetoed_by_roi(0.15, threshold=0.20) is True


def test_threshold_one_inclusive() -> None:
    """Boundary superiore: threshold=1.0 ammesso, roi=1.0 passa."""
    assert is_vetoed_by_roi(1.0, threshold=1.0) is False


def test_raises_on_zero_threshold() -> None:
    """R-01: threshold=0 proibito (significherebbe 'nessun veto' implicito)."""
    with pytest.raises(ValueError, match="threshold"):
        is_vetoed_by_roi(0.10, threshold=0.0)


def test_raises_on_negative_threshold() -> None:
    with pytest.raises(ValueError, match="threshold"):
        is_vetoed_by_roi(0.10, threshold=-0.05)


def test_raises_on_threshold_above_one() -> None:
    with pytest.raises(ValueError, match="threshold"):
        is_vetoed_by_roi(0.10, threshold=1.5)
