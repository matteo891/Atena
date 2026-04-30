"""Formule applicative Talos (ADR-0018).

Funzioni pure (no I/O, no DB) che implementano F1..F5 + Fee_FBA L11b
+ ROI. Versioni scalari per test e contesti scalari; le versioni
vettoriali (Numpy/pandas) sui DataFrame di sessione vivono in `vgp/`.

Catena del valore (incrementata progressivamente):

- CHG-2026-04-30-022: `fee_fba_manual` (L11b verbatim, primo modulo).
- CHG-2026-04-30-025: `cash_inflow_eur` (F1, primo consumatore di fee_fba).
- CHG-2026-04-30-026: `cash_profit_eur` (F2) + `roi` (gate Veto R-08).
"""

from talos.formulas.cash_inflow import cash_inflow_eur
from talos.formulas.cash_profit import cash_profit_eur
from talos.formulas.fee_fba import fee_fba_manual
from talos.formulas.roi import roi

__all__ = [
    "cash_inflow_eur",
    "cash_profit_eur",
    "fee_fba_manual",
    "roi",
]
