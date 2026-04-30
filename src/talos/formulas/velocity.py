"""F4 + F4.A + F5 + velocity_monthly - velocita' / quantita' (ADR-0018).

Verbatim PROJECT-RAW.md sez. 6.2 (decisione Leader, hardcoded):

    F4.A:  Q_m = V_tot / (S_comp + 1)
    F4:    Qty_Target = Q_m * (Velocity_Target / 30)
    F5:    Qty_Final = Floor(Qty_Target / 5) * 5

L05 chiusa Round 5: Velocity Target slider 7..30 giorni, default 15.
F5 lot size = 5 (lotti fornitore Samsung MVP). Floor sempre per difetto
*"per proteggere il cashflow"* (PROJECT-RAW.md riga 316).

`velocity_monthly` (rotazione mensile attesa) deriva da Q_m e velocity
target: se l'ASIN ruota Q_m volte in `velocity_target_days`, ruota
`Q_m * (30 / velocity_target_days)` volte in 30 giorni. Termine usato
dal VGP composito (CHG-2026-04-30-035).

Tutte funzioni scalari pure, vettorizzabili "free" via pandas Series
broadcasting (no `.apply()` necessario al call site).
"""

from __future__ import annotations

import math

# Default L05 (chiusa Round 5): slider Velocity Target 7..30 giorni, default 15.
DEFAULT_VELOCITY_TARGET_DAYS: int = 15

# Default Samsung MVP: lotti del fornitore = 5 pezzi (verbatim PROJECT-RAW.md riga 313).
DEFAULT_LOT_SIZE: int = 5

# Numero giorni del mese di riferimento (denominatore F4 e numeratore velocity_monthly).
_DAYS_PER_MONTH: int = 30


def q_m(v_tot: float, s_comp: int) -> float:
    """F4.A: Quota Mensile = `V_tot / (S_comp + 1)`.

    >>> q_m(100.0, 4)
    20.0
    >>> q_m(100.0, 0)  # nessun competitor
    100.0

    :param v_tot: vendite totali mensili stimate per l'ASIN (Dati Keepa / BSR).
        Deve essere `>= 0`.
    :param s_comp: numero venditori competitivi in BuyBox (entro 2% prezzo minimo).
        Deve essere `>= 0`.
    :returns: Q_m, frazione delle vendite mensili attribuita all'utente.
    :raises ValueError: se `v_tot < 0` o `s_comp < 0`.
    """
    if v_tot < 0:
        msg = f"v_tot invalido: {v_tot}. Le vendite mensili devono essere >= 0."
        raise ValueError(msg)
    if s_comp < 0:
        msg = f"s_comp invalido: {s_comp}. Il numero di competitor deve essere >= 0."
        raise ValueError(msg)
    return v_tot / (s_comp + 1)


def qty_target(q_m_value: float, velocity_target_days: int = DEFAULT_VELOCITY_TARGET_DAYS) -> float:
    """F4: Qty_Target = `Q_m * (velocity_target_days / 30)`.

    Numero di pezzi target per coprire un orizzonte di `velocity_target_days`
    giorni (default 15). Ritorna un float; per la quantita' ordinabile vedi
    `qty_final` (Floor + lotti).

    >>> qty_target(20.0)  # default 15 giorni
    10.0
    >>> qty_target(20.0, velocity_target_days=30)  # 1 mese
    20.0

    :param q_m_value: Quota Mensile (output di `q_m`). Deve essere `>= 0`.
    :param velocity_target_days: orizzonte in giorni. Slider L05 7..30, default 15.
        Deve essere `> 0`.
    :returns: quantita' target raw (float).
    :raises ValueError: se `q_m_value < 0` o `velocity_target_days <= 0`.
    """
    if q_m_value < 0:
        msg = f"q_m_value invalido: {q_m_value}. Deve essere >= 0."
        raise ValueError(msg)
    if velocity_target_days <= 0:
        msg = f"velocity_target_days invalido: {velocity_target_days}. Deve essere > 0."
        raise ValueError(msg)
    return q_m_value * velocity_target_days / _DAYS_PER_MONTH


def qty_final(qty_target_value: float, lot_size: int = DEFAULT_LOT_SIZE) -> int:
    """F5: Qty_Final = `Floor(qty_target / lot_size) * lot_size`.

    Forzatura ai lotti del fornitore con Floor (sempre per difetto) per
    proteggere il cashflow (PROJECT-RAW.md riga 316).

    >>> qty_final(10.0)  # 10 e' multiplo di 5
    10
    >>> qty_final(7.0)  # 7 // 5 = 1 lotto -> 5
    5
    >>> qty_final(4.9)  # sotto 1 lotto -> 0
    0

    :param qty_target_value: quantita' target raw (output di `qty_target`).
        Deve essere `>= 0`.
    :param lot_size: dimensione lotto fornitore. Default 5 (Samsung MVP).
        Deve essere `> 0`.
    :returns: quantita' finale ordinabile (int, multiplo di `lot_size`).
    :raises ValueError: se `qty_target_value < 0` o `lot_size <= 0`.
    """
    if qty_target_value < 0:
        msg = f"qty_target_value invalido: {qty_target_value}. Deve essere >= 0."
        raise ValueError(msg)
    if lot_size <= 0:
        msg = f"lot_size invalido: {lot_size}. Deve essere > 0."
        raise ValueError(msg)
    return math.floor(qty_target_value / lot_size) * lot_size


def velocity_monthly(
    q_m_value: float,
    velocity_target_days: int = DEFAULT_VELOCITY_TARGET_DAYS,
) -> float:
    """Rotazione mensile attesa al velocity target.

    Se l'ASIN ruota `Q_m` volte in `velocity_target_days` giorni, ruota
    `Q_m * (30 / velocity_target_days)` volte in 30 giorni. Termine usato
    dal VGP composito (CHG-2026-04-30-035) come `velocity_norm` candidate.

    >>> velocity_monthly(10.0, 15)
    20.0
    >>> velocity_monthly(10.0, 30)
    10.0

    :param q_m_value: Quota Mensile. Deve essere `>= 0`.
    :param velocity_target_days: target slider. Deve essere `> 0`.
    :returns: rotazione mensile attesa (float).
    :raises ValueError: se input invalidi.
    """
    if q_m_value < 0:
        msg = f"q_m_value invalido: {q_m_value}. Deve essere >= 0."
        raise ValueError(msg)
    if velocity_target_days <= 0:
        msg = f"velocity_target_days invalido: {velocity_target_days}. Deve essere > 0."
        raise ValueError(msg)
    return q_m_value * _DAYS_PER_MONTH / velocity_target_days
