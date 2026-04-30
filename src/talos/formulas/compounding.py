"""Formula 3 — Compounding T+1 (verbatim, PROJECT-RAW.md riga 280).

    Budget_T+1 = Budget_T + Somma(Cash_Profit)

R-07 VAT CREDIT COMPOUNDING (PROJECT-RAW riga 225): *"100% del bonifico
Amazon è capitale reinvestibile."* — l'IVA è già zero per Reverse Charge
+ credito infinito, quindi nessuno scorporo interno.

Funzione pura (no I/O, no DB). Accetta qualsiasi iterabile di profitti
(lista, tuple, generator). Niente raise: la somma è matematicamente
sempre lecita; budget negativo è continuità del compounding (sessione
fortemente in perdita erode il budget oltre zero). I gate stanno altrove
(Veto R-08 a monte sui ROI singoli, sizing del Tetris a valle).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def compounding_t1(budget_t: float, cash_profits: Iterable[float]) -> float:
    """Calcola il Budget_T+1 dalla sessione T (Formula 3, ADR-0018).

    >>> compounding_t1(1000.0, [50.0, 30.0, -10.0])
    1070.0
    >>> compounding_t1(1000.0, [])
    1000.0

    :param budget_t: budget reinvestibile della sessione corrente (T) in
        EUR. Può essere zero o negativo: il caller decide la semantica
        del valore di partenza.
    :param cash_profits: iterabile dei `Cash_Profit` di tutte le righe
        chiuse della sessione T (output di F2). I valori possono essere
        negativi (perdite) o positivi (guadagni). Iterabile consumato
        una sola volta.
    :returns: `Budget_T+1` in EUR. Può essere negativo se le perdite
        della sessione superano il budget di partenza (continuità di
        compounding, non un errore).
    """
    return budget_t + sum(cash_profits)
