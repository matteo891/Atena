"""90-Day Stress Test Filter — gating resilienza prezzo storico (ADR-0023).

Pattern Arsenale 180k filtro 3/4. ASIN dove
`cash_inflow_eur(buy_box_avg90) < cost_eur` (perdita catastrofica se il
prezzo torna alla media 90gg) sono `vgp_score = 0` (hard veto, simmetrico
a R-05/R-08/Amazon Presence).

Decisioni Leader ratificate (CHG-2026-05-02-030):
- Window: 90 giorni fisso (configurabilità per categoria = scope futuro).
- Severità: break-even (`cash_inflow >= cost`).
- Source: `product.stats.avg90[0]` Keepa (preconfezionato).

Implementazione:
- `passes_90d_stress_test(buy_box_avg90, cost_eur, fee_fba_eur,
  referral_fee_rate)` scalare per unit test boundary.
- `is_stress_test_failed_mask(df, *, avg90_col, cost_col, fee_fba_col,
  referral_fee_col)` vettoriale per `compute_vgp_score`.
- NaN/None `avg90` → False mask (= NOT failed = pass, decisione Leader).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from talos.formulas import cash_inflow_eur

if TYPE_CHECKING:
    import pandas as pd


def passes_90d_stress_test(
    *,
    buy_box_avg90: float | None,
    cost_eur: float,
    fee_fba_eur: float,
    referral_fee_rate: float,
) -> bool:
    """`True` se ASIN passa il 90-Day Stress Test (ADR-0023).

    Severità break-even: `cash_inflow_eur(avg90) >= cost_eur`. NaN/None
    → True (pass, decisione Leader default più liberale: ASIN nuovi
    senza 90gg di storia non sono filtrati).

    >>> passes_90d_stress_test(
    ...     buy_box_avg90=100.0, cost_eur=50.0, fee_fba_eur=4.10, referral_fee_rate=0.08
    ... )
    True
    >>> passes_90d_stress_test(
    ...     buy_box_avg90=50.0, cost_eur=50.0, fee_fba_eur=4.10, referral_fee_rate=0.08
    ... )
    False
    >>> passes_90d_stress_test(
    ...     buy_box_avg90=None, cost_eur=50.0, fee_fba_eur=4.10, referral_fee_rate=0.08
    ... )
    True
    """
    if buy_box_avg90 is None:
        return True
    inflow = cash_inflow_eur(
        buy_box_eur=buy_box_avg90,
        fee_fba_eur=fee_fba_eur,
        referral_fee_rate=referral_fee_rate,
    )
    return inflow >= cost_eur


def is_stress_test_failed_mask(
    df: pd.DataFrame,
    *,
    avg90_col: str = "buy_box_avg90",
    cost_col: str = "cost_eur",
    fee_fba_col: str = "fee_fba_eur",
    referral_fee_col: str = "referral_fee_resolved",
) -> pd.Series:
    """Mask booleana vettoriale: `True` dove ASIN FAIL stress test.

    Coerente con `kill_mask` semantica (True = scarta). NaN avg90 → False
    (= NOT failed = pass) per allineamento con `passes_90d_stress_test`.

    Usato in `vgp.compute_vgp_score` come quarto gate post R-05/R-08/
    Amazon Presence.
    """
    import pandas as pd  # noqa: PLC0415

    avg90 = df[avg90_col]
    fee_fba = df[fee_fba_col]
    referral = df[referral_fee_col]
    cost = df[cost_col]
    # cash_inflow vettoriale = avg90 - fee_fba - avg90·referral.
    inflow = avg90 - fee_fba - avg90 * referral
    failed = inflow < cost
    # NaN avg90 → fillna(False) (pass).
    return pd.Series(failed, index=df.index).fillna(value=False)
