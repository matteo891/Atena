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

import structlog

from talos.vgp.normalize import min_max_normalize
from talos.vgp.veto import DEFAULT_ROI_VETO_THRESHOLD

if TYPE_CHECKING:
    import pandas as pd


_logger = structlog.get_logger(__name__)
# Eventi canonici emessi (ADR-0021):
# - "vgp.veto_roi_failed": riga vetata da R-08 (asin/roi_pct/threshold).
# - "vgp.kill_switch_zero": riga killed da R-05 (asin/match_status).
# - "vgp.amazon_dominant_seller": riga vetata da Amazon Presence (ADR-0024,
#   CHG-031): asin/amazon_share/threshold.
# - "vgp.stress_test_failed": riga vetata da 90-Day Stress Test (ADR-0023,
#   CHG-032): asin/buy_box_avg90/cost.
# - "vgp.ghigliottina_failed": riga vetata da Ghigliottina (ADR-0022,
#   CHG-033): asin/cost/cash_profit/min_required.

# Pesi VGP verbatim PROJECT-RAW.md riga 329-331 (chiusa L04 Round 3).
# Modifica richiede errata corrige ADR-0018 (regola ADR-0009).
ROI_WEIGHT: float = 0.4
VELOCITY_WEIGHT: float = 0.4
CASH_PROFIT_WEIGHT: float = 0.2


def compute_vgp_score(  # noqa: PLR0913, C901, PLR0912 — design ADR-0018 + risk-filters opzionali (CHG-031/032)
    df: pd.DataFrame,
    *,
    roi_col: str = "roi",
    velocity_col: str = "velocity_monthly",
    cash_profit_col: str = "cash_profit_eur",
    kill_col: str = "kill_mask",
    veto_roi_threshold: float = DEFAULT_ROI_VETO_THRESHOLD,
    asin_col: str = "asin",
    match_status_col: str = "match_status",
    amazon_share_col: str = "amazon_buybox_share",
    avg90_col: str = "buy_box_avg90",
    fee_fba_col: str = "fee_fba_eur",
    referral_fee_col: str = "referral_fee_resolved",
    enable_ghigliottina: bool = True,
    cost_col: str = "cost_eur",
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

    # CHG-2026-05-02-031: Amazon Presence Filter (ADR-0024). Mask attiva solo
    # se la colonna `amazon_share_col` è presente nel DataFrame (graceful skip
    # backwards-compat: listini senza dato Keepa NON sono filtrati).
    import pandas as pd  # noqa: PLC0415 — lazy runtime import (TYPE_CHECKING only sopra)

    if amazon_share_col in out.columns:
        from talos.risk import is_amazon_dominant_mask  # noqa: PLC0415

        amazon_dominant_mask = is_amazon_dominant_mask(out[amazon_share_col])
    else:
        amazon_dominant_mask = pd.Series(data=False, index=out.index)

    # CHG-2026-05-02-032: 90-Day Stress Test (ADR-0023). Mask attiva solo
    # se TUTTE le 4 colonne (avg90 + cost + fee_fba + referral) sono presenti.
    stress_required_cols = (avg90_col, "cost_eur", fee_fba_col, referral_fee_col)
    if all(c in out.columns for c in stress_required_cols):
        from talos.risk import is_stress_test_failed_mask  # noqa: PLC0415

        stress_test_mask = is_stress_test_failed_mask(
            out,
            avg90_col=avg90_col,
            cost_col="cost_eur",
            fee_fba_col=fee_fba_col,
            referral_fee_col=referral_fee_col,
        )
    else:
        stress_test_mask = pd.Series(data=False, index=out.index)

    # CHG-2026-05-02-033: Ghigliottina (ADR-0022). Mask attiva sempre se
    # `enable_ghigliottina=True` (default) e cost_col + cash_profit_col
    # presenti. `enable_ghigliottina=False` permette test isolati R-08.
    if enable_ghigliottina and cost_col in out.columns and cash_profit_col in out.columns:
        from talos.risk import is_ghigliottina_failed_mask  # noqa: PLC0415

        ghigliottina_mask = is_ghigliottina_failed_mask(
            out,
            cost_col=cost_col,
            cash_profit_col=cash_profit_col,
        )
    else:
        ghigliottina_mask = pd.Series(data=False, index=out.index)

    # R-05 + R-08 + ADR-0024 + ADR-0023 + ADR-0022 applicati.
    blocked = (
        kill_mask
        | ~out["veto_roi_passed"]
        | amazon_dominant_mask
        | stress_test_mask
        | ghigliottina_mask
    )
    out["vgp_score"] = out["vgp_score_raw"].where(~blocked, 0.0)

    # Telemetria (ADR-0021). Eventi per-asin a livello DEBUG: silenti in produzione,
    # capturable nei test via `structlog.testing.LogCapture` (fixture in conftest).
    # Skip se la colonna `asin_col` non e' presente (caller-friendly: il modulo non
    # forza il contratto, lo verifica e degrada gracefully).
    if asin_col in out.columns:
        # vgp.veto_roi_failed: ASIN non killed ma sotto soglia ROI.
        veto_only_mask = ~out["veto_roi_passed"] & ~kill_mask
        for asin, roi_value in zip(
            out.loc[veto_only_mask, asin_col],
            out.loc[veto_only_mask, roi_col],
            strict=False,
        ):
            _logger.debug(
                "vgp.veto_roi_failed",
                asin=str(asin),
                roi_pct=float(roi_value),
                threshold=veto_roi_threshold,
            )
        # vgp.kill_switch_zero: ASIN killed (R-05).
        if kill_mask.any():
            killed_match_status = (
                out.loc[kill_mask, match_status_col]
                if match_status_col in out.columns
                else [None] * int(kill_mask.sum())
            )
            for asin, match_status in zip(
                out.loc[kill_mask, asin_col],
                killed_match_status,
                strict=False,
            ):
                _logger.debug(
                    "vgp.kill_switch_zero",
                    asin=str(asin),
                    match_status=str(match_status) if match_status is not None else "",
                )
        # vgp.amazon_dominant_seller: ASIN vetato da ADR-0024 (CHG-031).
        # Solo se la colonna è presente e c'è almeno un dominant_seller.
        if amazon_share_col in out.columns and amazon_dominant_mask.any():
            from talos.risk import AMAZON_PRESENCE_MAX_SHARE  # noqa: PLC0415

            for asin, share in zip(
                out.loc[amazon_dominant_mask, asin_col],
                out.loc[amazon_dominant_mask, amazon_share_col],
                strict=False,
            ):
                _logger.debug(
                    "vgp.amazon_dominant_seller",
                    asin=str(asin),
                    amazon_share=float(share),
                    threshold=AMAZON_PRESENCE_MAX_SHARE,
                )
        # vgp.stress_test_failed: ASIN vetato da ADR-0023 (CHG-032).
        if all(c in out.columns for c in stress_required_cols) and stress_test_mask.any():
            for asin, avg90, cost in zip(
                out.loc[stress_test_mask, asin_col],
                out.loc[stress_test_mask, avg90_col],
                out.loc[stress_test_mask, "cost_eur"],
                strict=False,
            ):
                _logger.debug(
                    "vgp.stress_test_failed",
                    asin=str(asin),
                    buy_box_avg90=float(avg90),
                    cost=float(cost),
                )
        # vgp.ghigliottina_failed: ASIN vetato da ADR-0022 (CHG-033).
        if ghigliottina_mask.any() and cost_col in out.columns:
            from talos.risk import min_profit_for_cost  # noqa: PLC0415

            for asin, cost, profit in zip(
                out.loc[ghigliottina_mask, asin_col],
                out.loc[ghigliottina_mask, cost_col],
                out.loc[ghigliottina_mask, cash_profit_col],
                strict=False,
            ):
                _logger.debug(
                    "vgp.ghigliottina_failed",
                    asin=str(asin),
                    cost=float(cost),
                    cash_profit=float(profit),
                    min_required=min_profit_for_cost(float(cost)),
                )

    return out
