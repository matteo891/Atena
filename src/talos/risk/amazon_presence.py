"""Amazon Presence Filter — gating monopolio Amazon BuyBox (ADR-0024).

Pattern Arsenale 180k filtro 4/4. ASIN dove Amazon detiene la Buy Box
per > 25% del tempo sono `vgp_score = 0` (hard veto, simmetrico a
R-05 KILL_SWITCH e R-08 VETO_ROI).

Decisioni Leader ratificate (CHG-2026-05-02-030):
- Threshold: 25% (default Arsenale).
- Modalità: hard veto.
- ASIN nuovi senza dati `buyBoxStats[Amazon]` → pass (più liberale).

Implementazione:
- `passes_amazon_presence(share)` scalare per unit test boundary.
- `is_amazon_dominant_mask(series)` vettoriale per `compute_vgp_score`.
- `None`/NaN → False nel mask (= NOT dominant = pass).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

# Decisione Leader 2026-05-02 (ratificata ADR-0024 Active CHG-030):
# 25% threshold dal pattern Arsenale 180k. Hard veto (no soft penalty).
AMAZON_PRESENCE_MAX_SHARE: float = 0.25


def passes_amazon_presence(amazon_share: float | None) -> bool:
    """`True` se ASIN passa il filtro Amazon Presence (ADR-0024).

    `None` → `True` (ASIN nuovi senza dati `buyBoxStats[Amazon]` passano,
    decisione Leader default più liberale). Threshold inclusivo:
    `share <= 0.25` passa, `share > 0.25` viene vetato.

    >>> passes_amazon_presence(0.10)
    True
    >>> passes_amazon_presence(0.25)
    True
    >>> passes_amazon_presence(0.2501)
    False
    >>> passes_amazon_presence(None)
    True
    """
    if amazon_share is None:
        return True
    return amazon_share <= AMAZON_PRESENCE_MAX_SHARE


def is_amazon_dominant_mask(series: pd.Series) -> pd.Series:
    """Mask booleana vettoriale: `True` dove Amazon è dominante (FAIL filter).

    Coerente con `kill_mask` semantica (True = scarta). NaN/None → False
    (= NOT dominant = pass) per allineamento con `passes_amazon_presence`.

    Usato in `vgp.compute_vgp_score` come terzo gate post R-05/R-08.
    """
    return (series > AMAZON_PRESENCE_MAX_SHARE).fillna(value=False)
