"""Ghigliottina Tier Profit Filter — gating profitto assoluto stratificato (ADR-0022).

Pattern Arsenale 180k filtro 1/4. AFFIANCA R-08 (doppio gate AND):
ASIN passa solo se `roi >= 8%` AND `cash_profit >= min_profit_tier(cost)`.

Decisioni Leader ratificate (CHG-2026-05-02-030):
- AFFIANCA R-08 (doppio gate AND).
- Tier breakpoints (50€, 150€) + min profit (10€, 25€, 50€).

Tier:
| Cost fornitore (EUR) | Min profit assoluto (EUR) |
|---|---|
| `< 50`         | `10` |
| `50 .. 150`    | `25` |
| `> 150`        | `50` |

Razionale: il rischio di immobilizzo capitale è non-lineare nel costo.
Un prodotto da 1000€ in giacenza brucia capitale enormemente più di
uno da 100€ — anche se il ROI% è identico. Tier assoluti garantiscono
profit minimo significativo per giustificare il rischio.

Implementazione:
- `min_profit_for_cost(cost)` lookup tier.
- `passes_ghigliottina(cost, cash_profit)` scalare.
- `is_ghigliottina_failed_mask(df, ...)` vettoriale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import pandas as pd

# Tier ordinati per cost_max ascending: il primo tier che matcha vince.
# Decisione Leader 2026-05-02 (ratificata CHG-030): valori Arsenale 180k.
GHIGLIOTTINA_TIERS: Final[tuple[tuple[float, float], ...]] = (
    (50.0, 10.0),  # cost < 50  → min profit 10
    (150.0, 25.0),  # cost < 150 → min profit 25
    (float("inf"), 50.0),  # cost qualsiasi → min profit 50
)


def min_profit_for_cost(cost_eur: float) -> float:
    """Lookup min profit per tier basato sul costo fornitore.

    >>> min_profit_for_cost(30.0)
    10.0
    >>> min_profit_for_cost(50.0)
    25.0
    >>> min_profit_for_cost(100.0)
    25.0
    >>> min_profit_for_cost(150.0)
    50.0
    >>> min_profit_for_cost(1000.0)
    50.0
    """
    for cost_max, min_profit in GHIGLIOTTINA_TIERS:
        if cost_eur < cost_max:
            return min_profit
    return GHIGLIOTTINA_TIERS[-1][1]


def passes_ghigliottina(*, cost_eur: float, cash_profit_eur: float) -> bool:
    """`True` se ASIN passa il filtro Ghigliottina (ADR-0022).

    Boundary inclusivo: `cash_profit >= min_profit_tier(cost)`.

    >>> passes_ghigliottina(cost_eur=30.0, cash_profit_eur=10.0)
    True
    >>> passes_ghigliottina(cost_eur=30.0, cash_profit_eur=9.99)
    False
    >>> passes_ghigliottina(cost_eur=100.0, cash_profit_eur=25.0)
    True
    >>> passes_ghigliottina(cost_eur=200.0, cash_profit_eur=49.99)
    False
    """
    min_required = min_profit_for_cost(cost_eur)
    return cash_profit_eur >= min_required


def is_ghigliottina_failed_mask(
    df: pd.DataFrame,
    *,
    cost_col: str = "cost_eur",
    cash_profit_col: str = "cash_profit_eur",
) -> pd.Series:
    """Mask booleana vettoriale: `True` dove ASIN FAIL Ghigliottina.

    Coerente con `kill_mask` semantica (True = scarta). Usato in
    `vgp.compute_vgp_score` come quinto gate post R-05/R-08/Amazon
    Presence/Stress Test.
    """
    import pandas as pd  # noqa: PLC0415

    cost = df[cost_col]
    cash_profit = df[cash_profit_col]
    # Vettorizziamo `min_profit_for_cost` con ricerca tier.
    min_required = cost.apply(min_profit_for_cost)
    failed = cash_profit < min_required
    return pd.Series(failed, index=df.index).fillna(value=False)
