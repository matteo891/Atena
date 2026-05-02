"""Tetris allocator — DP knapsack max-saturation + cart exhaustive (CHG-022).

R-06 verbatim PROJECT-RAW.md riga 224 + ratifica Leader 2026-05-02:
*"il Tetris deve calcolare la miglior combinazione di prodotti acquistati
in lotti di quantità definita per saturare al massimo il budget e non
lasciare neanche un centesimo fermo se è utilizzabile"*. CHG-2026-05-02-022
sostituisce il greedy max-fill (CHG-020) con DP bounded knapsack per
ottenere saturazione massima ottima.

R-04 verbatim PROJECT-RAW.md sez. 4.1.13: locked-in priorita' infinita
prima del normale ranking VGP, riservando il loro costo dal budget.

CHG-2026-05-02-022 — **Cart exhaustive ratificato Leader**: il cart contiene
TUTTI gli ASIN del listino, ognuno con `qty` (0+) e `reason` flag esplicito.
Gli ASIN con qty=0 hanno motivo (`VETO_ROI`, `KILL_SWITCH`, `ZERO_QTY_TARGET`,
`MIN_LOT_OVER_BUDGET`, `BUDGET_EXHAUSTED`). La "panchina" e' una vista
derivata (filtro reason).

Algoritmo:
  Pass 1 (R-04): locked-in con `qty_final` velocity-based (priorita' inf).
    Se non sta nel budget -> InsufficientBudgetError.
  Pass 2 (R-06 DP): bounded knapsack 1D su ASIN non-locked che passano veto.
    Maximize sum(cost*qty) (saturazione massima).
    Tie-break: sum(VGP*qty) (epsilon-weighted).
    Item options: qty in {0, lot_size, 2*lot_size, ..., max_qty}.
  Pass 3 (exhaustive): aggiunge al cart tutti gli ASIN del listino con
    reason flag esplicito (anche quelli con qty=0).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import pandas as pd


_logger = structlog.get_logger(__name__)
# Eventi canonici emessi (catalogo ADR-0021):
# - "tetris.skipped_budget": riga con cost > remaining (R-06 + DP).


# Soglia saturazione R-06 verbatim PROJECT-RAW.md riga 224.
SATURATION_THRESHOLD: float = 0.999

# Lot size default Samsung MVP (F5 PROJECT-RAW.md riga 313).
DEFAULT_LOT_SIZE: int = 5

# Reason flags per cart items (CHG-2026-05-02-022).
REASON_ALLOCATED: str = "ALLOCATED"
REASON_LOCKED_IN: str = "LOCKED_IN"
REASON_VETO_ROI: str = "VETO_ROI"  # vgp_score=0 via R-08 ROI < soglia
REASON_KILL_SWITCH: str = "KILL_SWITCH"  # vgp_score=0 via R-05 NLP mismatch
REASON_ZERO_QTY_TARGET: str = "ZERO_QTY_TARGET"  # F5 azzera per v_tot piccolo
REASON_MIN_LOT_OVER_BUDGET: str = "MIN_LOT_OVER_BUDGET"  # 1 lotto > budget residuo
REASON_BUDGET_EXHAUSTED: str = "BUDGET_EXHAUSTED"  # DP non l'ha scelto

# Epsilon per tie-break VGP nel DP (rispetto a saturazione cost).
_TIE_BREAK_EPS: float = 1e-6


class InsufficientBudgetError(ValueError):
    """R-04 fallisce: un ASIN locked-in ha costo > budget residuo."""


@dataclass(frozen=True)
class CartItem:
    """Item del carrello Tetris (CHG-022 cart exhaustive).

    `reason` flag esplicita perché qty è quello che è (ALLOCATED se >0,
    motivo specifico se 0). Cart contiene TUTTI gli ASIN del listino.
    """

    asin: str
    cost_total: float
    qty: int
    vgp_score: float
    locked: bool = False
    reason: str = REASON_ALLOCATED


@dataclass
class Cart:
    """Carrello Tetris di sessione (exhaustive: tutti gli ASIN del listino)."""

    budget: float
    items: list[CartItem] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return sum(item.cost_total for item in self.items)

    @property
    def remaining(self) -> float:
        return self.budget - self.total_cost

    @property
    def saturation(self) -> float:
        if self.budget <= 0:
            return 0.0
        return min(self.total_cost / self.budget, 1.0)

    def asin_list(self) -> list[str]:
        """Tutti gli ASIN del listino (anche qty=0). CHG-022 exhaustive."""
        return [item.asin for item in self.items]

    def allocated_items(self) -> list[CartItem]:
        """Solo gli ASIN con qty > 0 (subset visualizzativo)."""
        return [item for item in self.items if item.qty > 0]

    def panchina_items(self) -> list[CartItem]:
        """ASIN scartati per cassa (R-09): vgp>0, reason in BUDGET_EXHAUSTED/MIN_LOT_OVER_BUDGET."""
        return [
            item
            for item in self.items
            if item.qty == 0
            and item.vgp_score > 0
            and item.reason in (REASON_BUDGET_EXHAUSTED, REASON_MIN_LOT_OVER_BUDGET)
        ]

    def add(self, item: CartItem) -> None:
        self.items.append(item)


def _classify_reason(
    score: float,
    qty_target: int,
    *,
    kill_mask: bool,
) -> str | None:
    """Determina reason per qty=0 in base ai flag pipeline.

    Ritorna None se eligible (score>0, qty>0, no kill).
    """
    if kill_mask:
        return REASON_KILL_SWITCH
    if score == 0.0:
        return REASON_VETO_ROI
    if qty_target <= 0:
        return REASON_ZERO_QTY_TARGET
    return None


def _solve_knapsack_dp(
    items: list[tuple[str, float, float, int]],
    budget_remaining: float,
    lot_size: int,
) -> dict[str, int]:
    """Bounded DP knapsack: max sum(cost*qty), tie-break VGP. Granularità 1 EUR.

    :param items: lista `(asin, cost_unit, vgp_score, max_qty)`. `max_qty`
        deve essere multiplo di `lot_size`.
    :param budget_remaining: budget residuo dopo locked-in.
    :param lot_size: dimensione lotto fornitore.
    :returns: dict `{asin: qty_chosen}`. Asin non in dict -> 0.
    """
    if not items or budget_remaining <= 0:
        return {}
    budget_int = int(budget_remaining)
    # dp[j] = max value (sum cost*qty + eps*vgp*qty) for total cost <= j
    dp: list[float] = [0.0] * (budget_int + 1)
    # parent[j] = (item_idx, qty_chosen, prev_j) per backtrack
    parent: list[tuple[int, int, int] | None] = [None] * (budget_int + 1)

    for idx, (_asin, cost_unit, vgp, max_qty) in enumerate(items):
        cost_unit_f = float(cost_unit)
        new_dp = list(dp)
        new_parent = list(parent)
        # Iter qty options da lot_size a max_qty, step lot_size.
        for qty in range(lot_size, max_qty + 1, lot_size):
            cost_total = cost_unit_f * qty
            cost_total_int: int = math.ceil(cost_total)
            if cost_total_int > budget_int:
                break
            value_add = cost_total + _TIE_BREAK_EPS * vgp * qty
            for j in range(cost_total_int, budget_int + 1):
                prev_j = j - cost_total_int
                candidate = dp[prev_j] + value_add
                if candidate > new_dp[j] + 1e-9:
                    new_dp[j] = candidate
                    new_parent[j] = (idx, qty, prev_j)
        dp = new_dp
        parent = new_parent

    # Find best j (max value).
    best_j = int(max(range(budget_int + 1), key=lambda j: dp[j]))

    # Backtrack.
    qty_per_asin: dict[str, int] = {}
    j = best_j
    while parent[j] is not None:
        record = parent[j]
        assert record is not None  # noqa: S101 — guard logico, non runtime check
        idx, qty, prev_j = record
        asin = items[idx][0]
        qty_per_asin[asin] = qty_per_asin.get(asin, 0) + qty
        j = prev_j
    return qty_per_asin


def allocate_tetris(  # noqa: PLR0913, C901, PLR0912, PLR0915 — DP knapsack + 3 pass; semantica ADR-0018 errata CHG-022
    vgp_df: pd.DataFrame,
    budget: float,
    locked_in: list[str],
    *,
    asin_col: str = "asin",
    cost_col: str = "cost_eur",
    qty_col: str = "qty_final",
    score_col: str = "vgp_score",
    lot_size: int = DEFAULT_LOT_SIZE,
    kill_mask_col: str = "kill_mask",
) -> Cart:
    """Tetris allocator DP knapsack + cart exhaustive (CHG-2026-05-02-022).

    :param vgp_df: DataFrame ordinato per vgp_score DESC (caller responsibility).
    :param budget: budget di sessione EUR. > 0.
    :param locked_in: lista ASIN forzati R-04.
    :param lot_size: lotto fornitore (default 5).
    :param kill_mask_col: nome colonna kill_mask (R-05). Se assente, assume False.
    :returns: `Cart` exhaustive con TUTTI gli ASIN del listino.
    """
    if budget <= 0:
        msg = f"budget invalido: {budget}. Deve essere > 0."
        raise ValueError(msg)
    if lot_size <= 0:
        msg = f"lot_size invalido: {lot_size}. Deve essere > 0."
        raise ValueError(msg)
    required = [asin_col, cost_col, qty_col, score_col]
    missing = [c for c in required if c not in vgp_df.columns]
    if missing:
        msg = (
            f"allocate_tetris: colonne richieste mancanti dal DataFrame: {missing}. "
            f"Attese (override via kwargs): {required}."
        )
        raise ValueError(msg)
    has_kill_mask = kill_mask_col in vgp_df.columns

    cart = Cart(budget=budget)
    locked_set = set(locked_in)

    # Pass 1 (R-04): locked-in con qty_final velocity-based, priorità ∞.
    for asin in locked_in:
        match = vgp_df[vgp_df[asin_col] == asin]
        if match.empty:
            msg = (
                f"allocate_tetris: ASIN locked_in '{asin}' non trovato in vgp_df. "
                "R-04 richiede che il locked-in sia presente nel listino di sessione."
            )
            raise ValueError(msg)
        row = match.iloc[0]
        qty_locked = int(row[qty_col]) or lot_size  # almeno 1 lotto se qty_target=0
        cost_total = float(row[cost_col]) * qty_locked
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
                qty=qty_locked,
                vgp_score=float(row[score_col]),
                locked=True,
                reason=REASON_LOCKED_IN,
            ),
        )

    # Pass 2 (R-06 DP knapsack): tra gli ASIN non-locked eleggibili, trova
    # la combinazione che massimizza saturazione (tie-break VGP).
    eligible_items: list[tuple[str, float, float, int]] = []
    skip_reasons: dict[str, str] = {}  # asin -> reason flag
    for _, row in vgp_df[~vgp_df[asin_col].isin(locked_set)].iterrows():
        asin = str(row[asin_col])
        score = float(row[score_col])
        qty_target = int(row[qty_col])
        cost_unit = float(row[cost_col])
        kill = bool(row[kill_mask_col]) if has_kill_mask else False
        # Classify ineligible reasons.
        reason = _classify_reason(score, qty_target, kill_mask=kill)
        if reason is not None:
            skip_reasons[asin] = reason
            continue
        if cost_unit <= 0:
            skip_reasons[asin] = REASON_ZERO_QTY_TARGET
            continue
        # Max qty multiplo di lot_size compatibile col budget residuo iniziale.
        max_qty_lot = math.floor(cart.remaining / cost_unit / lot_size) * lot_size
        if max_qty_lot < lot_size:
            skip_reasons[asin] = REASON_MIN_LOT_OVER_BUDGET
            continue
        eligible_items.append((asin, cost_unit, score, max_qty_lot))

    # DP solve.
    qty_per_asin = _solve_knapsack_dp(eligible_items, cart.remaining, lot_size)

    # Allocate eligibili scelti dal DP.
    for asin, cost_unit, score, _max_qty in eligible_items:
        qty = qty_per_asin.get(asin, 0)
        if qty > 0:
            cost_total = cost_unit * qty
            cart.add(
                CartItem(
                    asin=asin,
                    cost_total=cost_total,
                    qty=qty,
                    vgp_score=score,
                    locked=False,
                    reason=REASON_ALLOCATED,
                ),
            )
        else:
            # Eligible ma DP non ha scelto -> BUDGET_EXHAUSTED.
            skip_reasons[asin] = REASON_BUDGET_EXHAUSTED

    # Pass 3 (exhaustive): aggiungi al cart tutti gli altri ASIN con reason.
    allocated_set = {item.asin for item in cart.items}
    for _, row in vgp_df.iterrows():
        asin = str(row[asin_col])
        if asin in allocated_set:
            continue
        reason = skip_reasons.get(asin, REASON_BUDGET_EXHAUSTED)
        if reason in (REASON_BUDGET_EXHAUSTED, REASON_MIN_LOT_OVER_BUDGET):
            _logger.debug(
                "tetris.skipped_budget",
                asin=asin,
                cost=float(row[cost_col]) * lot_size,
                budget_remaining=cart.remaining,
            )
        cart.add(
            CartItem(
                asin=asin,
                cost_total=0.0,
                qty=0,
                vgp_score=float(row[score_col]),
                locked=False,
                reason=reason,
            ),
        )

    return cart
