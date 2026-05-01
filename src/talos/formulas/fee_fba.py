"""Formula manuale Fee_FBA L11b — verbatim del Leader (PROJECT-RAW.md sez. 6.3).

Fallback obbligatorio se Keepa non espone Fee_FBA: la formula riproduce la
struttura tariffaria FBA Italia (scorpora IVA al 22%, applica scaglione
percentuale + fee fissa, lorda IVA con 1.03, somma cap finale).

Forma analitica: `((buy_box / 1.22 - 100) * 0.0816 + 7.14) * 1.03 + 6.68`.

Breakdown coefficienti (verbatim Leader, CHG-2026-04-29-008 Frozen):
  - `1.22`  divisore IVA Italia 22% (scorporo netto).
  - `100`   soglia minima dello scaglione (sotto -> ValueError R-01).
  - `0.0816` aliquota 8.16% sull'eccedenza oltre 100 EUR (single-tier MVP;
            la struttura tariffaria FBA Amazon reale ha multi-scaglioni
            per peso/dimensioni ma per Samsung MVP smartphone l'unico
            scaglione attivo coincide con questa aliquota).
  - `7.14`  fee fissa addizionale sul singolo pezzo (EUR netto).
  - `1.03`  **markup operativo** del Leader: interpretazione speculativa
            "gross-up parziale residuo" (3%); non documentato esplicitamente
            in PROJECT-RAW Round 5. Errata ADR-0018 quando il Leader
            ratifica l'interpretazione canonica con dati storici Amazon
            Italia (CHG-2026-05-02-005 segnala il debito documentale).
  - `6.68`  cap finale sommato (EUR lordo IVA, fee gestionale fissa
            dell'operazione).

> NB: la presenza simultanea di scorporo (`/1.22`) e gross-up (`*1.03`)
> implica che il valore finale è espresso al **lordo IVA**, ma con un
> coefficiente residuo (1.03 vs 1.22) il cui razionale non è esplicitato
> nella vision originale. La formula è cmq "Frozen" e non va modificata
> senza errata corrige.

Dichiarata `Frozen` dal Leader nel Round 5 della esposizione TALOS
(CHG-2026-04-29-008). Modifiche solo via Errata Corrige di ADR-0018.

R-01 NO SILENT DROPS: condizioni di input fuori range sollevano
`ValueError` esplicito; mai un valore "implicito" o un NaN.
"""

from __future__ import annotations

# Coefficienti L11b verbatim Frozen Round 5 (vedi docstring per breakdown).
_VAT_DIVISOR: float = 1.22  # scorporo IVA 22% Italia
_THRESHOLD: float = 100.0  # soglia minima scaglione (sotto -> ValueError)
_RATE: float = 0.0816  # aliquota 8.16% su eccedenza > 100 EUR
_FIXED_FEE: float = 7.14  # fee fissa scaglione (EUR netto)
_VAT_GROSS_UP: float = 1.03  # markup operativo Leader (3%, interpretazione da ratificare)
_FINAL_ADD: float = 6.68  # cap finale (EUR lordo IVA)


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
