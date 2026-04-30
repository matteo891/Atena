"""Formula 1 — Cash Inflow (verbatim, PROJECT-RAW.md sez. 6.3).

    Cash Inflow = BuyBox - Fee_FBA - (BuyBox * Referral_Fee)

Nota del Leader: *"zero scorporo IVA per via del Reverse Charge + Credito
infinito"*. La formula opera su BuyBox lordo IVA; nessuno scorporo interno.

Funzione pura (no I/O, no DB). `Fee_FBA` e `Referral_Fee` sono **input**:
- `Fee_FBA` può venire da Keepa (lookup primario, ADR-0017) oppure dal
  fallback `fee_fba_manual` (R-01, ADR-0018, CHG-2026-04-30-022);
- `Referral_Fee` da lookup categoria + override manuale (L12, PROJECT-RAW
  sez. 6.3) — espresso come frazione decimale (es. 0.08 = 8%).

R-01 NO SILENT DROPS: input fisicamente impossibili (negativi, aliquote
fuori [0, 1]) sollevano `ValueError`. Output negativo (`cash_inflow < 0`,
"vendita in perdita") è ammesso e restituito invariato — è un fatto
economico, non un errore. Il filtro applicativo è il Veto ROI a valle
(R-08), non questa formula.
"""

from __future__ import annotations


def cash_inflow_eur(
    buy_box_eur: float,
    fee_fba_eur: float,
    referral_fee_rate: float,
) -> float:
    """Calcola il Cash Inflow per singola unità (Formula 1, ADR-0018).

    >>> round(cash_inflow_eur(200.0, 19.4078, 0.08), 4)
    164.5922

    :param buy_box_eur: prezzo BuyBox Amazon in EUR (IVA inclusa). Deve
        essere ≥ 0.
    :param fee_fba_eur: Fee_FBA in EUR (IVA inclusa) per singola unità.
        Deve essere ≥ 0.
    :param referral_fee_rate: aliquota referral come frazione decimale,
        in [0, 1] (es. `0.08` = 8%).
    :returns: Cash Inflow in EUR. Può essere negativo: la "vendita in
        perdita" è un fatto economico legittimo, non un errore (R-01).
    :raises ValueError: se `buy_box_eur < 0`, `fee_fba_eur < 0`, oppure
        `referral_fee_rate` fuori da `[0, 1]`.
    """
    if buy_box_eur < 0:
        msg = f"buy_box_eur invalido (negativo): {buy_box_eur}"
        raise ValueError(msg)
    if fee_fba_eur < 0:
        msg = f"fee_fba_eur invalido (negativo): {fee_fba_eur}"
        raise ValueError(msg)
    if not 0 <= referral_fee_rate <= 1:
        msg = (
            f"referral_fee_rate invalido: {referral_fee_rate}. "
            "Atteso valore in [0, 1] (frazione decimale, 0.08 = 8%)."
        )
        raise ValueError(msg)

    return buy_box_eur - fee_fba_eur - (buy_box_eur * referral_fee_rate)
