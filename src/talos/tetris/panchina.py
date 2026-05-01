"""Panchina R-09 - archivio idonei scartati per capienza (ADR-0018).

R-09 verbatim PROJECT-RAW.md riga 227: *"Nessun ASIN con ROI >= 8% deve
essere dimenticato. Al termine del ciclo di saturazione Tetris (R-06), il
bot ha l'obbligo di generare un output secondario denominato 'Panchina'.
Questo file deve contenere tutti i prodotti idonei scartati unicamente per
ragioni di capienza finanziaria, ordinati per VGP Score decrescente."*

Selezione (verbatim ADR-0018 sez. "Panchina"):
- `vgp_score > 0` (gia' R-05 + R-08 esclusi: i vetati hanno score=0)
- `~ asin in cart` (esclusi gli allocati)

Ordine: `vgp_score` DESC. Nessun limite di righe.

Il primo caller naturale e' l'orchestratore di sessione (CHG futuro):
output cruscotto = (Cart, Panchina, Budget_T+1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import pandas as pd

    from talos.tetris.allocator import Cart


_logger = structlog.get_logger(__name__)
# Evento canonico emesso (ADR-0021):
# - "panchina.archived": ASIN idoneo (vgp_score>0) non in cart, archiviato per cassa.


def build_panchina(
    vgp_df: pd.DataFrame,
    cart: Cart,
    *,
    asin_col: str = "asin",
    score_col: str = "vgp_score",
) -> pd.DataFrame:
    """R-09: ASIN idonei (vgp_score > 0) non allocati, ordinati per VGP DESC.

    :param vgp_df: DataFrame con almeno le colonne `asin_col` e `score_col`.
        Tipicamente l'output di `compute_vgp_score`.
    :param cart: `Cart` di sessione (output di `allocate_tetris`). Gli ASIN
        gia' nel cart sono esclusi.
    :param asin_col: nome colonna ASIN (default `"asin"`).
    :param score_col: nome colonna VGP score (default `"vgp_score"`).
    :returns: DataFrame con le righe di `vgp_df` filtrate (`vgp_score > 0` &
        `asin not in cart`), ordinate per `score_col` DESC. Index originale
        preservato.
    :raises ValueError: se `asin_col` o `score_col` mancano da `vgp_df`.
    """
    missing = [c for c in (asin_col, score_col) if c not in vgp_df.columns]
    if missing:
        msg = (
            f"build_panchina: colonne richieste mancanti dal DataFrame: {missing}. "
            f"Attese (override via kwargs): {[asin_col, score_col]}."
        )
        raise ValueError(msg)

    in_cart = set(cart.asin_list())
    eligible = vgp_df[(vgp_df[score_col] > 0) & (~vgp_df[asin_col].isin(in_cart))]
    out = eligible.sort_values(score_col, ascending=False)

    # Telemetria (ADR-0021): emette `panchina.archived` per ogni riga archiviata.
    for asin, score in zip(out[asin_col], out[score_col], strict=False):
        _logger.debug(
            "panchina.archived",
            asin=str(asin),
            vgp_score=float(score),
        )

    return out
