"""Tetris allocator - R-06 saturazione 99.9% + R-04 locked-in priorita' infinita.

R-06 verbatim PROJECT-RAW.md riga 224: *"L'allocatore scorre la classifica
VGP. Se un ASIN supera il budget residuo, prosegue (continue) cercando item
con VGP inferiore ma costo compatibile, fino a saturare il budget di sessione
al 99.9%."*

R-04 verbatim PROJECT-RAW.md sez. 4.1.13 (L13 Round 5): *"ASIN locked_in
entrano nel Tetris con Priorita'=infinity prima del normale ranking VGP,
riservando il loro costo dal budget di sessione."*

CHG-2026-05-02-020 — **Errata semantica F5/R-06 ratificata Leader**:
`qty_final = floor(qty_target / lot_size) * lot_size` NON e' il MASSIMO
acquistabile, e' il MINIMO (1 lotto fornitore = 5 unita' Samsung MVP).
Pass 2 R-06 ora compra il **MAX multiplo di `lot_size`** che sta nel
budget residuo per ogni ASIN VGP DESC che passa veto (greedy max-fill).
Decisione Leader 2026-05-02: "5 sono i multipli, non il massimo".

Semantica:
- **Pass 1 (R-04)**: ogni ASIN in `locked_in` entra prima del normale
  ranking con qty_final velocity-based del listino. Se non sta nel budget
  residuo -> `InsufficientBudgetError` esplicito (R-01 NO SILENT DROPS).
- **Pass 2 (R-06 greedy max-fill)**: scansione del DataFrame ordinato per
  `vgp_score` DESC. Skip `vgp_score == 0` (R-05/R-08). Skip `qty_target<=0`
  (F5 azzera per v_tot piccolo). Per ogni ASIN comprabile: `qty = floor(
  remaining / cost_unit / lot_size) * lot_size` (greedy MAX multiplo).
  Skip se nemmeno 1 lotto sta nel budget. Break su saturation >= 0.999.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import pandas as pd


_logger = structlog.get_logger(__name__)
# Eventi canonici emessi da questo modulo (catalogo ADR-0021 + governance).
# Pattern stringa-letterale per consentire al governance test
# `tests/governance/test_log_events_catalog.py` di rilevarli via grep:
# - "tetris.skipped_budget": riga con cost_total > budget residuo (Pass 2 R-06).


# Soglia saturazione R-06 verbatim PROJECT-RAW.md riga 224.
# Modifica richiede errata corrige ADR-0018 (regola ADR-0009).
SATURATION_THRESHOLD: float = 0.999

# Lot size default (F5 PROJECT-RAW.md riga 313, Samsung MVP).
# CHG-2026-05-02-020: parametrizzato per coerenza greedy max-fill.
DEFAULT_LOT_SIZE: int = 5


class InsufficientBudgetError(ValueError):
    """R-04 fallisce: un ASIN locked-in ha costo > budget residuo.

    R-01 NO SILENT DROPS: il caller (UI) deve sapere che un locked-in
    non entra. Mai silently-skip.
    """


@dataclass(frozen=True)
class CartItem:
    """Item del carrello Tetris.

    Snapshot di una riga del listino al momento dell'allocazione.
    `locked` distingue R-04 (priorita' infinita) dal normale ranking R-06.
    """

    asin: str
    cost_total: float  # cost_unit * qty
    qty: int
    vgp_score: float
    locked: bool = False


@dataclass
class Cart:
    """Carrello Tetris di sessione.

    `items` e' la lista append-only degli ASIN allocati (in ordine di
    inserimento: locked-in prima, poi VGP decrescente). `budget` e'
    immutabile post-init.
    """

    budget: float
    items: list[CartItem] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        """Costo totale degli item in carrello."""
        return sum(item.cost_total for item in self.items)

    @property
    def remaining(self) -> float:
        """Budget residuo (puo' diventare negativo solo via bug — R-04 lo previene)."""
        return self.budget - self.total_cost

    @property
    def saturation(self) -> float:
        """Frazione di budget utilizzato in `[0, 1]` (al massimo 1.0 per costruzione)."""
        if self.budget <= 0:
            return 0.0
        return min(self.total_cost / self.budget, 1.0)

    def asin_list(self) -> list[str]:
        """ASIN nel carrello in ordine di inserimento."""
        return [item.asin for item in self.items]

    def add(self, item: CartItem) -> None:
        """Append-only. Caller responsabile del check `cost <= remaining`."""
        self.items.append(item)


def allocate_tetris(  # noqa: PLR0913, C901 — 4 col-name override + due passi (R-04 + R-06) con skip multipli (score=0, qty=0, over-budget); semantica ADR-0018
    vgp_df: pd.DataFrame,
    budget: float,
    locked_in: list[str],
    *,
    asin_col: str = "asin",
    cost_col: str = "cost_eur",
    qty_col: str = "qty_final",
    score_col: str = "vgp_score",
    lot_size: int = DEFAULT_LOT_SIZE,
) -> Cart:
    """Allocator Tetris greedy: R-04 (Pass 1) + R-06 (Pass 2).

    :param vgp_df: DataFrame con almeno le colonne `asin_col`, `cost_col`,
        `qty_col`, `score_col`. **Atteso ordinato per `score_col` DESC**
        per il Pass 2 (il caller e' responsabile dell'ordinamento — di
        solito output di `compute_vgp_score`).
    :param budget: budget di sessione in EUR. Deve essere > 0.
    :param locked_in: lista di ASIN da forzare prima del Pass 2 (R-04).
        Ordine preservato. ASIN duplicati ignorati (set semantics).
    :param asin_col: nome colonna ASIN (default `"asin"`).
    :param cost_col: nome colonna costo unitario (default `"cost_eur"`).
    :param qty_col: nome colonna quantita' (default `"qty_final"`).
    :param score_col: nome colonna VGP score (default `"vgp_score"`).
    :returns: `Cart` con `items` allocati. `cart.saturation` puo' essere
        < 0.999 se il listino non e' saturabile al budget dato.
    :raises ValueError: se `budget <= 0`, colonne mancanti, o un ASIN in
        `locked_in` non presente in `vgp_df`.
    :raises InsufficientBudgetError: se un locked-in ha cost > remaining
        dopo i precedenti locked-in (R-04 fail-fast).
    """
    if budget <= 0:
        msg = f"budget invalido: {budget}. Deve essere > 0."
        raise ValueError(msg)

    required = [asin_col, cost_col, qty_col, score_col]
    missing = [c for c in required if c not in vgp_df.columns]
    if missing:
        msg = (
            f"allocate_tetris: colonne richieste mancanti dal DataFrame: {missing}. "
            f"Attese (override via kwargs): {required}."
        )
        raise ValueError(msg)

    cart = Cart(budget=budget)
    locked_set = set(locked_in)

    # Pass 1 (R-04): locked-in con priorita' infinita.
    for asin in locked_in:
        match = vgp_df[vgp_df[asin_col] == asin]
        if match.empty:
            msg = (
                f"allocate_tetris: ASIN locked_in '{asin}' non trovato in vgp_df. "
                "R-04 richiede che il locked-in sia presente nel listino di sessione."
            )
            raise ValueError(msg)
        row = match.iloc[0]
        cost_total = float(row[cost_col]) * int(row[qty_col])
        if cost_total > cart.remaining:
            msg = (
                f"R-04 fallisce: locked-in '{asin}' costa {cost_total:.2f} EUR, "
                f"budget residuo {cart.remaining:.2f} EUR. "
                "Risolvi a monte (rimuovi un locked-in precedente o aumenta budget)."
            )
            raise InsufficientBudgetError(msg)
        cart.add(
            CartItem(
                asin=str(row[asin_col]),
                cost_total=cost_total,
                qty=int(row[qty_col]),
                vgp_score=float(row[score_col]),
                locked=True,
            ),
        )

    # Pass 2 (R-06 greedy max-fill, CHG-2026-05-02-020):
    # Per ogni ASIN VGP DESC che passa veto: compra il MAX multiplo di
    # `lot_size` che sta nel budget residuo. Skip vgp=0, qty_target<=0,
    # nemmeno-1-lotto. Break su saturation >= 0.999.
    if lot_size <= 0:
        msg = f"lot_size invalido: {lot_size}. Deve essere > 0."
        raise ValueError(msg)
    for _, row in vgp_df[~vgp_df[asin_col].isin(locked_set)].iterrows():
        score = float(row[score_col])
        if score == 0.0:
            # R-05 / R-08 hanno gia' azzerato: skippa.
            continue
        qty_target = int(row[qty_col])
        if qty_target <= 0:
            # F5 azzera per v_tot piccolo: ASIN non vendibile, skippa.
            continue
        cost_unit = float(row[cost_col])
        if cost_unit <= 0:
            continue
        # Greedy MAX multiplo di lot_size compatibile col budget residuo.
        qty_max_lot = math.floor(cart.remaining / cost_unit / lot_size) * lot_size
        if qty_max_lot < lot_size:
            # Nemmeno 1 lotto fornitore sta nel budget residuo -> skip.
            _logger.debug(
                "tetris.skipped_budget",
                asin=str(row[asin_col]),
                cost=cost_unit * lot_size,
                budget_remaining=cart.remaining,
            )
            continue
        cost_total = cost_unit * qty_max_lot
        cart.add(
            CartItem(
                asin=str(row[asin_col]),
                cost_total=cost_total,
                qty=qty_max_lot,
                vgp_score=score,
                locked=False,
            ),
        )
        if cart.saturation >= SATURATION_THRESHOLD:
            break

    return cart
