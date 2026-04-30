"""Tetris - cluster allocator + panchina (ADR-0018).

Inaugurato in CHG-2026-04-30-036 con `allocate_tetris` - greedy
allocator R-06 (saturazione 99.9%) + R-04 (locked-in priorita' infinita).

Esteso in CHG-2026-04-30-037 con `build_panchina` - R-09 archivio
idonei (vgp_score > 0) scartati per capienza, ordinati per VGP DESC.

I due output canonici di sessione sono `Cart` (alloca) + `panchina_df`
(scartati per cassa) — entrambi consumati dall'orchestratore di
sessione (CHG futuro).
"""

from talos.tetris.allocator import (
    SATURATION_THRESHOLD,
    Cart,
    CartItem,
    InsufficientBudgetError,
    allocate_tetris,
)
from talos.tetris.panchina import build_panchina

__all__ = [
    "SATURATION_THRESHOLD",
    "Cart",
    "CartItem",
    "InsufficientBudgetError",
    "allocate_tetris",
    "build_panchina",
]
