"""Formula manuale Fee_FBA L11b — verbatim del Leader (PROJECT-RAW.md sez. 6.3).

Fallback obbligatorio se Keepa non espone Fee_FBA: la formula riproduce la
struttura tariffaria FBA Italia (scorpora IVA al 22%, applica scaglione
percentuale + fee fissa, lorda IVA con 1.03, somma cap finale).

Dichiarata `Frozen` dal Leader nel Round 5 della esposizione TALOS
(CHG-2026-04-29-008). Modifiche solo via Errata Corrige di ADR-0018.

R-01 NO SILENT DROPS: condizioni di input fuori range sollevano
`ValueError` esplicito; mai un valore "implicito" o un NaN.
"""

from __future__ import annotations

_VAT_DIVISOR: float = 1.22
_THRESHOLD: float = 100.0
_RATE: float = 0.0816
_FIXED_FEE: float = 7.14
_VAT_GROSS_UP: float = 1.03
_FINAL_ADD: float = 6.68


def fee_fba_manual(buy_box_eur: float) -> float:
    """Calcola Fee_FBA dalla formula manuale L11b.

    >>> round(fee_fba_manual(200.0), 4)
    19.4078

    :param buy_box_eur: prezzo BuyBox Amazon in EUR (IVA inclusa). Deve
        essere ≥ 0 e produrre `buy_box_eur / 1.22 ≥ 100` (soglia di validità
        dichiarata dal Leader: *"non blocca per Samsung MVP, sempre sopra"*).
    :returns: Fee_FBA in EUR (IVA inclusa).
    :raises ValueError: se `buy_box_eur < 0` oppure `scorporato < 100`
        (R-01 NO SILENT DROPS).
    """
    if buy_box_eur < 0:
        msg = f"buy_box_eur invalido (negativo): {buy_box_eur}"
        raise ValueError(msg)

    scorporato = buy_box_eur / _VAT_DIVISOR
    if scorporato < _THRESHOLD:
        msg = (
            f"buy_box_eur={buy_box_eur} sotto soglia: "
            f"scorporato={scorporato:.2f} < {_THRESHOLD}. "
            "Formula Fee_FBA L11b non garantita in questo range."
        )
        raise ValueError(msg)

    return ((scorporato - _THRESHOLD) * _RATE + _FIXED_FEE) * _VAT_GROSS_UP + _FINAL_ADD
