"""Tetris - cluster allocator (ADR-0018).

Inaugurato in CHG-2026-04-30-036 con `allocate_tetris` - greedy
allocator R-06 (saturazione 99.9%) + R-04 (locked-in priorita' infinita).

`build_panchina` (R-09 archivio idonei scartati per capienza) e'
scope di un CHG successivo (`tetris/panchina.py`).
"""

from talos.tetris.allocator import (
    SATURATION_THRESHOLD,
    Cart,
    CartItem,
    InsufficientBudgetError,
    allocate_tetris,
)

__all__ = [
    "SATURATION_THRESHOLD",
    "Cart",
    "CartItem",
    "InsufficientBudgetError",
    "allocate_tetris",
]
