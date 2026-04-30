"""Veto ROI R-08 - predicato scalare (PROJECT-RAW.md riga 226).

R-08 verbatim: "VETO ROI MINIMO. Nonostante la monarchia del VGP,
viene applicato un filtro di sbarramento assoluto. Qualsiasi ASIN
con un ROI stimato inferiore all'8% viene scartato a prescindere
dal punteggio VGP. Protegge il capitale da oscillazioni di prezzo
Amazon o fee impreviste, garantendo un margine di sicurezza minimo."

"inferiore all'8%" -> strict `<`. ROI esattamente 0.08 **passa**
(boundary R-08 inclusivo).

Soglia default 0.08 (8%). Configurabile dal cruscotto - L10 chiusa
Round 5: *"soglia 8% configurabile dal cruscotto, persistita in DB
come config"*. Persistenza pronta in `config_overrides` (CHG-012);
config layer (pydantic-settings) e iniezione automatica al call
site sono scope futuro. Per ora la soglia entra come parametro
funzione con default ancorato a R-08.

Versione SCALARE: predicato su un singolo ROI. La versione
vettoriale (su listino di sessione, DataFrame N-righe) e' scope
di un futuro CHG sotto `vgp/score.py` o equivalente.
"""

from __future__ import annotations

DEFAULT_ROI_VETO_THRESHOLD: float = 0.08
"""Soglia default Veto R-08, ancorata a PROJECT-RAW.md riga 226 (8%)."""


def is_vetoed_by_roi(
    roi_value: float,
    threshold: float = DEFAULT_ROI_VETO_THRESHOLD,
) -> bool:
    """True se l'ASIN deve essere scartato per ROI sotto soglia (R-08).

    >>> is_vetoed_by_roi(0.07)
    True
    >>> is_vetoed_by_roi(0.08)
    False
    >>> is_vetoed_by_roi(0.15)
    False

    :param roi_value: ROI come frazione decimale (output di
        `talos.formulas.roi`). Puo' essere negativo (loss):
        sara' VETATO comunque.
    :param threshold: soglia minima inclusiva. Deve essere in
        `(0, 1]`. Default `DEFAULT_ROI_VETO_THRESHOLD` = 0.08
        (R-08 verbatim).
    :returns: `True` se vetato (scartare), `False` se passa il
        filtro.
    :raises ValueError: se `threshold` non e' in `(0, 1]`.
    """
    if not 0 < threshold <= 1:
        msg = (
            f"threshold ROI invalido: {threshold}. "
            "Deve essere in (0, 1] (frazione decimale, default 0.08 = 8%)."
        )
        raise ValueError(msg)

    return roi_value < threshold
