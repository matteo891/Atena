"""Formula 2 - Cash Profit (verbatim, PROJECT-RAW.md sez. 6.3).

    Cash Profit = Cash Inflow - Costo_Fornitore

Funzione pura (no I/O, no DB). `Cash_Inflow` arriva da F1
(`cash_inflow_eur`, CHG-2026-04-30-025); `Costo_Fornitore` e' input
applicativo (catalogo fornitore o config layer).

R-01 NO SILENT DROPS: `costo_fornitore_eur < 0` solleva `ValueError`
(spesa fisicamente impossibile). `costo_fornitore_eur == 0` ammesso
(campione gratuito dal fornitore). `cash_inflow_eur` non validato
per segno: e' output di F1 che ammette negativi (vendita in perdita
propaga).

Output ammesso negativo: profit < 0 = ASIN sotto costo. Il filtro
e' il Veto R-08 (`roi < soglia`) a valle, non questa formula.
"""

from __future__ import annotations


def cash_profit_eur(
    cash_inflow_eur: float,
    costo_fornitore_eur: float,
) -> float:
    """Calcola il Cash Profit per singola unita' (Formula 2, ADR-0018).

    >>> round(cash_profit_eur(164.5922, 100.0), 4)
    64.5922

    :param cash_inflow_eur: output di F1, in EUR. Puo' essere negativo
        (vendita in perdita), nessuna validazione di segno.
    :param costo_fornitore_eur: spesa di acquisto unitario in EUR.
        Deve essere >= 0; lo zero e' ammesso (campione gratuito).
    :returns: Cash Profit in EUR. Puo' essere negativo: ASIN sotto
        costo e' un fatto economico, non un errore (R-01).
    :raises ValueError: se `costo_fornitore_eur < 0`.
    """
    if costo_fornitore_eur < 0:
        msg = f"costo_fornitore_eur invalido (negativo): {costo_fornitore_eur}"
        raise ValueError(msg)

    return cash_inflow_eur - costo_fornitore_eur
