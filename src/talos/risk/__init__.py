"""Risk-filter applicativi (Pattern Arsenale 180k — ADR-0022/0023/0024).

Cluster nuovo introdotto da CHG-2026-05-02-031. 8ª area applicativa
permessa da ADR-0013 (`io_`, `extract`, `vgp`, `tetris`, `persistence`,
`ui`, `observability`, `config`, **`risk`**).

Filtri di gating decisionale che agiscono come `kill_mask` aggiuntivi
in `vgp.compute_vgp_score`. Composizione AND con R-05/R-08 esistenti
(un ASIN passa solo se TUTTI i gate passano).

Filtri attivi:
- `amazon_presence` (ADR-0024): hard veto Amazon BuyBox > 25%.

Filtri previsti (CHG futuri):
- `stress_test` (ADR-0023): break-even sul prezzo medio 90gg.
- `ghigliottina` (ADR-0022): tier profit assoluto stratificato per costo.
"""

from __future__ import annotations

from talos.risk.amazon_presence import (
    AMAZON_PRESENCE_MAX_SHARE,
    is_amazon_dominant_mask,
    passes_amazon_presence,
)
from talos.risk.ghigliottina import (
    GHIGLIOTTINA_TIERS,
    is_ghigliottina_failed_mask,
    min_profit_for_cost,
    passes_ghigliottina,
)
from talos.risk.stress_test import (
    is_stress_test_failed_mask,
    passes_90d_stress_test,
)

__all__ = (
    "AMAZON_PRESENCE_MAX_SHARE",
    "GHIGLIOTTINA_TIERS",
    "is_amazon_dominant_mask",
    "is_ghigliottina_failed_mask",
    "is_stress_test_failed_mask",
    "min_profit_for_cost",
    "passes_90d_stress_test",
    "passes_amazon_presence",
    "passes_ghigliottina",
)
