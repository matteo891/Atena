"""Formule applicative Talos (ADR-0018).

Funzioni pure (no I/O, no DB) che implementano F1..F5 + Fee_FBA L11b.
Versioni scalari per test e contesti scalari; le versioni vettoriali
(Numpy/pandas) sui DataFrame di sessione vivono in `vgp/`.

Inaugurato in CHG-2026-04-30-022 con `fee_fba_manual` — primo modulo
applicativo del prodotto Talos.
"""

from talos.formulas.fee_fba import fee_fba_manual

__all__ = ["fee_fba_manual"]
