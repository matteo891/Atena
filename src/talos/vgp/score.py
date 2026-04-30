"""Formula VGP composita - scoring vettoriale (ADR-0018, L04 + L04b + R-05 + R-08).

VGP Score (PROJECT-RAW.md sez. 6.3, verbatim Round 3 + Round 4):

    VGP_Score = (norm(ROI)         * 0.4)
              + (norm(Velocity)    * 0.4)
              + (norm(Cash_Profit) * 0.2)

con `norm(x)` = min-max [0,1] sul listino di sessione (vedi
`talos.vgp.normalize.min_max_normalize`).

Applicazione vettoriale dei filtri di sbarramento:
- **R-05 KILL-SWITCH HARDWARE** (PROJECT-RAW.md riga 223): mismatch
  NLP forza `vgp_score = 0`. Implementato come azzeramento delle
  righe con `kill_mask == True`.
- **R-08 VETO ROI MINIMO** (PROJECT-RAW.md riga 226): ROI < 0.08
  forza `vgp_score = 0`. Boundary inclusivo (ROI == 0.08 passa).
  Implementato vettoriale `roi >= threshold` (semantica identica
  alla primitiva scalare `talos.vgp.veto.is_vetoed_by_roi`).

Scope di questa funzione: scoring **puro** su un DataFrame con
colonne gia' calcolate (ROI, Velocity, Cash_Profit, kill_mask).
La pipeline orchestratrice end-to-end (`compute_vgp_session` di
ADR-0018, che parte dal listino raw e calcola F1/F2/F4/F5) e'
scope di un CHG futuro.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from talos.vgp.normalize import min_max_normalize
from talos.vgp.veto import DEFAULT_ROI_VETO_THRESHOLD

if TYPE_CHECKING:
    import pandas as pd

# Pesi VGP verbatim PROJECT-RAW.md riga 329-331 (chiusa L04 Round 3).
# Modifica richiede errata corrige ADR-0018 (regola ADR-0009).
ROI_WEIGHT: float = 0.4
VELOCITY_WEIGHT: float = 0.4
CASH_PROFIT_WEIGHT: float = 0.2


def compute_vgp_score(  # noqa: PLR0913 — i 6 arg sono tutti necessari (1 df + 4 col-name override + 1 threshold); design ADR-0018
    df: pd.DataFrame,
    *,
    roi_col: str = "roi",
    velocity_col: str = "velocity_monthly",
    cash_profit_col: str = "cash_profit_eur",
    kill_col: str = "kill_mask",
    veto_roi_threshold: float = DEFAULT_ROI_VETO_THRESHOLD,
) -> pd.DataFrame:
    """Calcola il VGP Score vettoriale con applicazione di R-05 e R-08.

    Aggiunge le colonne (in copia, input intoccato):
    - `roi_norm`, `velocity_norm`, `cash_profit_norm`: min-max [0,1]
      sui termini eligible (escluse righe killed).
    - `vgp_score_raw`: formula composita con pesi 0.4/0.4/0.2 prima
      dell'applicazione di R-05/R-08 (utile per debug/audit).
    - `veto_roi_passed`: bool, `True` se ROI >= soglia (R-08 inclusivo).
    - `vgp_score`: score finale post R-05 + R-08; 0.0 dove
      `kill_mask | ~veto_roi_passed`.

    :param df: DataFrame con almeno le colonne `roi_col`, `velocity_col`,
        `cash_profit_col`, `kill_col`. Index libero, preservato in output.
    :param roi_col: nome colonna ROI (frazione decimale, es. 0.15).
    :param velocity_col: nome colonna Velocity (rotazione mensile, qty/30gg).
    :param cash_profit_col: nome colonna Cash Profit assoluto in EUR.
    :param kill_col: nome colonna booleana kill_mask (R-05).
    :param veto_roi_threshold: soglia minima inclusiva R-08, in `(0, 1]`.
        Default 0.08 (8%, R-08 verbatim PROJECT-RAW.md riga 226).
    :returns: copia di `df` con 6 colonne aggiunte. Input non modificato.
    :raises ValueError: se mancano colonne richieste o `veto_roi_threshold`
        non e' in `(0, 1]`.
    """
    if not 0 < veto_roi_threshold <= 1:
        msg = (
            f"veto_roi_threshold invalido: {veto_roi_threshold}. "
            "Deve essere in (0, 1] (frazione decimale, default 0.08 = 8%)."
        )
        raise ValueError(msg)

    required = [roi_col, velocity_col, cash_profit_col, kill_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        msg = (
            f"compute_vgp_score: colonne richieste mancanti dal DataFrame: {missing}. "
            f"Attese (override via kwargs): {required}."
        )
        raise ValueError(msg)

    out = df.copy()
    kill_mask = out[kill_col].astype(bool)

    out["roi_norm"] = min_max_normalize(out[roi_col], kill_mask)
    out["velocity_norm"] = min_max_normalize(out[velocity_col], kill_mask)
    out["cash_profit_norm"] = min_max_normalize(out[cash_profit_col], kill_mask)

    out["vgp_score_raw"] = (
        out["roi_norm"] * ROI_WEIGHT
        + out["velocity_norm"] * VELOCITY_WEIGHT
        + out["cash_profit_norm"] * CASH_PROFIT_WEIGHT
    )

    # R-08 vettoriale: ROI >= soglia (inclusivo). Coerente con
    # `is_vetoed_by_roi(roi) = roi < threshold` -> passa = ~vetoed.
    out["veto_roi_passed"] = out[roi_col] >= veto_roi_threshold

    # R-05 + R-08 applicati: vgp_score = 0 dove kill | ~veto_passed.
    blocked = kill_mask | ~out["veto_roi_passed"]
    out["vgp_score"] = out["vgp_score_raw"].where(~blocked, 0.0)

    return out
