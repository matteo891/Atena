"""Normalizzazione min-max [0,1] (L04b - ADR-0018).

L04b verbatim Round 4 PROJECT-RAW.md: *"normalizzazione min-max [0,1]
dei tre termini (ROI, Velocity, Cash Profit) sul listino di sessione"*.

Esclusione `kill_mask`: le righe KILLED (R-05 hardware mismatch) sono
escluse dal calcolo di `min`/`max` per evitare che il VGP=0 forzato
downstream comprima la scala dei valori eligible. La formula
`(x - min) / (max - min)` viene comunque applicata a tutta la serie;
le righe killed sono azzerate in `vgp/score.py` (R-05) - quel codice
e' scope di un CHG successivo.

Edge cases (verbatim ADR-0018):
- `eligible` vuoto (tutte le righe killed) -> ritorna serie di `0.0`.
- `max == min` (tutti i valori eligible identici) -> ritorna serie di `0.0`.
  Il termine non discrimina nessun ASIN, convenzione L04b.

Versione SCALARE/per-colonna: opera su una `pd.Series`. La pipeline
completa che orchestra le 3 colonne (ROI, Velocity, Cash Profit) e'
scope di `vgp/score.py` (CHG futuro).
"""

from __future__ import annotations

import pandas as pd


def min_max_normalize(series: pd.Series, kill_mask: pd.Series) -> pd.Series:
    """Min-max [0,1] sul listino di sessione, escludendo righe KILLED dal min/max.

    >>> import pandas as pd
    >>> s = pd.Series([10.0, 20.0, 30.0])
    >>> k = pd.Series([False, False, False])
    >>> min_max_normalize(s, k).tolist()
    [0.0, 0.5, 1.0]

    :param series: serie di valori numerici (ROI, Velocity, Cash Profit)
        di una colonna del listino di sessione.
    :param kill_mask: serie booleana con stesso indice di `series`. `True`
        dove R-05 e' applicato (match status `KILLED`).
    :returns: serie normalizzata in `[0,1]` per le righe eligible. Per
        le righe killed la formula viene applicata, quindi il risultato
        puo' uscire dal range `[0,1]` by design (sara' azzerato downstream
        in `vgp/score.py`). Edge case `eligible` vuoto o `max==min` ->
        serie di `0.0` con stesso indice di `series`.
    :raises ValueError: se `series.index` e `kill_mask.index` non
        coincidono (R-01 NO SILENT DROPS - errore esplicito vs allineamento
        accidentale).
    """
    if not series.index.equals(kill_mask.index):
        msg = (
            "min_max_normalize: gli indici di `series` e `kill_mask` devono "
            f"coincidere (len(series)={len(series)}, len(kill_mask)={len(kill_mask)})."
        )
        raise ValueError(msg)

    eligible = series[~kill_mask]
    if len(eligible) == 0:
        return pd.Series(0.0, index=series.index)

    min_val: float = float(eligible.min())
    max_val: float = float(eligible.max())
    if max_val == min_val:
        return pd.Series(0.0, index=series.index)

    return (series - min_val) / (max_val - min_val)
