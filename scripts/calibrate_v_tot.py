# noqa: INP001 (script standalone, no package init).
"""Calibrazione formula `estimate_v_tot_from_bsr` su dati storici reali.

CHG-2026-05-02-008: il Leader esegue questo script quando ha raccolto un
ground truth (BSR snapshot + vendite mensili reali per N>=20 ASIN). Lo
script fa un fit log-lineare ai minimi quadrati e suggerisce i nuovi
coefficienti `_BSR_LOG_INTERCEPT` e `_BSR_LOG_SLOPE` da ratificare via
errata ADR-0018.

INPUT: CSV con header `asin,bsr,v_tot_real`. Esempio:
    asin,bsr,v_tot_real
    B0CSTC2RDW,2500,45
    B0BLP2GS6K,5000,28
    ...

OUTPUT: stampa su stdout coefficienti + R² + suggerimento errata.

Esecuzione:
    uv run python scripts/calibrate_v_tot.py path/to/ground_truth.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_MIN_SAMPLE: int = 5
_R2_WARN_THRESHOLD: float = 0.5
_EXPECTED_ARGS: int = 2


def calibrate(df: pd.DataFrame) -> tuple[float, float, float]:
    """Fit `v_tot = INTERCEPT - SLOPE * log10(bsr)` ai minimi quadrati.

    :returns: tuple `(intercept, slope, r_squared)`.
    :raises ValueError: dati insufficienti o BSR<=0.
    """
    if len(df) < _MIN_SAMPLE:
        msg = (
            f"Dataset troppo piccolo per fit affidabile: {len(df)} righe "
            f"(richiesto >={_MIN_SAMPLE})."
        )
        raise ValueError(msg)
    if (df["bsr"] <= 0).any():
        msg = "Tutti i BSR devono essere > 0 (log10 indefinito altrimenti)."
        raise ValueError(msg)

    log_bsr = np.log10(df["bsr"].to_numpy(dtype=float))
    v_tot = df["v_tot_real"].to_numpy(dtype=float)
    a_matrix = np.column_stack([np.ones_like(log_bsr), -log_bsr])
    (intercept, slope), _res, _rank, _sv = np.linalg.lstsq(a_matrix, v_tot, rcond=None)
    predicted = intercept - slope * log_bsr
    ss_res = float(np.sum((v_tot - predicted) ** 2))
    ss_tot = float(np.sum((v_tot - v_tot.mean()) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(intercept), float(slope), float(r_squared)


def main(argv: list[str]) -> int:
    if len(argv) != _EXPECTED_ARGS:
        sys.stderr.write("Usage: calibrate_v_tot.py <ground_truth.csv>\n")
        return 2
    path = Path(argv[1])
    if not path.is_file():
        sys.stderr.write(f"File non trovato: {path}\n")
        return 1
    df = pd.read_csv(path)
    required = {"asin", "bsr", "v_tot_real"}
    missing = required - set(df.columns)
    if missing:
        sys.stderr.write(f"Colonne mancanti: {missing}\n")
        return 1

    intercept, slope, r_squared = calibrate(df)

    sys.stdout.write("\n=== TALOS V_tot calibration ===\n")
    sys.stdout.write(f"Sample size:        {len(df)}\n")
    sys.stdout.write(f"Intercept (A):      {intercept:.4f}\n")
    sys.stdout.write(f"Slope     (B):      {slope:.4f}\n")
    sys.stdout.write(f"R-squared:          {r_squared:.4f}\n")
    sys.stdout.write("\n=== Errata ADR-0018 suggerita ===\n")
    sys.stdout.write(
        f"In `src/talos/extract/velocity_estimator.py`:\n"
        f"  _BSR_LOG_INTERCEPT: Final[float] = {intercept:.2f}\n"
        f"  _BSR_LOG_SLOPE:     Final[float] = {slope:.2f}\n",
    )
    if r_squared < _R2_WARN_THRESHOLD:
        sys.stdout.write(
            "\nWARNING: R² < 0.5 -> fit log-lineare insufficiente. "
            "Considerare modello alternativo (es. power law o per-categoria).\n",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
