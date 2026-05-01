"""Unit test `scripts/calibrate_v_tot.calibrate` (CHG-2026-05-02-008)."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pandas as pd
import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "calibrate_v_tot.py"
_spec = importlib.util.spec_from_file_location("calibrate_v_tot", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
calibrate = _mod.calibrate

pytestmark = pytest.mark.unit


def test_perfect_log_linear_fit_recovers_coefficients() -> None:
    """Dato sintetico log-lineare puro -> coefficienti recuperati esattamente, R²=1."""
    bsrs = [10, 100, 1000, 10000, 100000]
    intercept_true, slope_true = 80.0, 15.0
    df = pd.DataFrame(
        {
            "asin": [f"B{i}" for i in range(len(bsrs))],
            "bsr": bsrs,
            "v_tot_real": [intercept_true - slope_true * math.log10(b) for b in bsrs],
        },
    )
    intercept, slope, r2 = calibrate(df)
    assert intercept == pytest.approx(intercept_true, abs=1e-6)
    assert slope == pytest.approx(slope_true, abs=1e-6)
    assert r2 == pytest.approx(1.0, abs=1e-6)


def test_insufficient_data_raises() -> None:
    df = pd.DataFrame({"asin": ["A"], "bsr": [100], "v_tot_real": [50]})
    with pytest.raises(ValueError, match="troppo piccolo"):
        calibrate(df)


def test_invalid_bsr_raises() -> None:
    df = pd.DataFrame(
        {
            "asin": [f"B{i}" for i in range(5)],
            "bsr": [100, 200, 0, 400, 500],
            "v_tot_real": [50, 40, 60, 30, 20],
        },
    )
    with pytest.raises(ValueError, match=r"BSR.*> 0"):
        calibrate(df)
