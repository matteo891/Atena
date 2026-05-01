"""Velocity estimator — V_tot stimato da BSR (CHG-2026-05-02-003).

Sblocca il MVP CFO Path B': il flow descrizione+prezzo CSV (CHG-020) ha
`v_tot=0` di default quando il CFO non lo specifica. Conseguenza nella
pipeline:

    Q_m = V_tot / (S_comp + 1) = 0 / 1 = 0
    Qty_Final = Floor(Q_m * 15 / 30 / 5) * 5 = 0
    -> ASIN escluso dal Tetris (skip qty_final<=0, CHG-041)

Quindi: cart sempre vuoto, panchina sempre vuota, MVP non usabile.

Soluzione: stima `V_tot` dal BSR (Best Sellers Rank) Amazon root, che
e' gia' disponibile in `ProductData.bsr` (Keepa CHG-015 oppure scraper
CHG-013). La formula MVP sotto e' una **placeholder log-lineare** che
serve a sbloccare il flow; va **calibrata su dati storici** prima di
considerarla canonica (ratifica Leader).

R-01 NO SILENT DROPS: se `bsr` e' `None` o invalido, ritorna 0.0 (lo
stesso default pre-CHG); il caller decide se escludere l'ASIN o
loggare un warning.

> ATTENZIONE: la formula attuale non e' calibrata su dati di vendita
> reali. E' un'approssimazione MVP che assume distribuzione log-lineare
> tra BSR e vendite mensili. Per produzione: raccogliere ground truth
> (BSR snapshot + vendite mensili reali per N>=20 ASIN Samsung) e
> ricalibrare i coefficienti `_BSR_LOG_INTERCEPT` e `_BSR_LOG_SLOPE`.
"""

from __future__ import annotations

import math
from typing import Final

# Sentinel del campo audit `v_tot_source`. Documentano DA DOVE viene
# il valore di `v_tot` nel listino_raw (canonica per debug + CFO).
V_TOT_SOURCE_CSV: Final[str] = "csv"
"""Il CFO ha specificato `v_tot` esplicitamente nel CSV (override)."""

V_TOT_SOURCE_BSR_ESTIMATE: Final[str] = "bsr_estimate_mvp"
"""Stima MVP da BSR root tramite formula log-lineare placeholder."""

V_TOT_SOURCE_DEFAULT_ZERO: Final[str] = "default_zero"
"""BSR non disponibile e nessun override CSV: V_tot=0 (ASIN escluso a valle)."""

# Coefficienti formula log MVP placeholder.
# Forma: max(MIN_V_TOT, INTERCEPT - SLOPE * log10(bsr)).
# Calibrazione naive Samsung MVP (Cell Phones IT):
#   bsr 1 -> ~100 v/mese (best seller); 100 -> ~60; 10k -> ~20; >=100k -> 1.
# Modifica via errata ADR-0018 con dati storici reali.
_BSR_LOG_INTERCEPT: Final[float] = 100.0
_BSR_LOG_SLOPE: Final[float] = 20.0
_MIN_V_TOT: Final[float] = 1.0


def estimate_v_tot_from_bsr(bsr: int | None) -> float:
    """Stima V_tot (vendite mensili) da BSR root via formula log MVP.

    Formula:
        V_tot = max(1, INTERCEPT - SLOPE * log10(bsr))

    >>> estimate_v_tot_from_bsr(1)
    100.0
    >>> estimate_v_tot_from_bsr(100)
    60.0
    >>> round(estimate_v_tot_from_bsr(10000), 2)
    20.0
    >>> estimate_v_tot_from_bsr(None)
    0.0
    >>> estimate_v_tot_from_bsr(0)
    0.0

    :param bsr: BSR root Amazon. `None` o `<=0` -> ritorna `0.0`
        (caller dovrebbe escludere o loggare warning).
    :returns: V_tot stimato in vendite/mese, clampato a `>= 1.0` quando
        bsr e' valido. `0.0` solo se input invalido.

    > NB: stima MVP non calibrata. Production-ready richiede ground
    > truth + ricalibrazione coefficienti.
    """
    if bsr is None or bsr <= 0:
        return 0.0
    estimated = _BSR_LOG_INTERCEPT - _BSR_LOG_SLOPE * math.log10(bsr)
    return max(_MIN_V_TOT, estimated)


def resolve_v_tot(
    *,
    csv_v_tot: int,
    bsr_root: int | None,
) -> tuple[float, str]:
    """Risolve V_tot finale + source flag (audit).

    Logica hybrid (decisione MVP, ratifica Leader):
    1. Se `csv_v_tot > 0` -> il CFO ha specificato esplicitamente: usa
       quello (fonte: `csv`). Override del default.
    2. Altrimenti se `bsr_root` e' valido -> stima MVP da BSR (fonte:
       `bsr_estimate_mvp`).
    3. Altrimenti -> 0.0 (fonte: `default_zero`, ASIN sara' escluso a
       valle dal Tetris per `qty_final=0`).

    >>> resolve_v_tot(csv_v_tot=50, bsr_root=10000)
    (50.0, 'csv')
    >>> resolve_v_tot(csv_v_tot=0, bsr_root=10000)
    (20.0, 'bsr_estimate_mvp')
    >>> resolve_v_tot(csv_v_tot=0, bsr_root=None)
    (0.0, 'default_zero')

    :param csv_v_tot: valore `v_tot` dal CSV (default 0 se non specificato).
    :param bsr_root: BSR root da Keepa/scraper, opzionale.
    :returns: tuple `(v_tot, source)` per il listino_raw + audit.
    """
    if csv_v_tot > 0:
        return float(csv_v_tot), V_TOT_SOURCE_CSV
    estimated = estimate_v_tot_from_bsr(bsr_root)
    if estimated > 0:
        return estimated, V_TOT_SOURCE_BSR_ESTIMATE
    return 0.0, V_TOT_SOURCE_DEFAULT_ZERO
