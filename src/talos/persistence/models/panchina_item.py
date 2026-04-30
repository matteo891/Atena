"""ORM model `panchina_items` (ADR-0015 Allegato A).

Archivio R-09: ASIN con `vgp_score > 0` (cioè match passato + ROI ≥ soglia
veto + non kill-switched) **non entrati nel carrello** per saturazione del
budget. Tetris allocator (ADR-0018 `tetris/panchina.py`) li archivia in
ordine `vgp_score` decrescente, pronti a essere "promossi" se il CFO
elimina manualmente qualcosa dal carrello.

Schema isomorfo a `cart_items` ma più snello (4 colonne):
- niente `unit_cost_eur` (riferito tramite FK a `vgp_results.cash_profit_eur`
  e `listino_items.cost_eur`);
- niente `locked_in` (la panchina è per definizione "non scelta", R-04 si
  applica solo al carrello).

Doppia FK CASCADE: `session_id`, `vgp_result_id`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talos.persistence.base import Base

if TYPE_CHECKING:
    from talos.persistence.models.analysis_session import AnalysisSession
    from talos.persistence.models.vgp_result import VgpResult


class PanchinaItem(Base):
    """Riga della panchina (Allegato A — `panchina_items`).

    Schema verbatim Allegato A: 4 colonne, doppia FK CASCADE.
    """

    __tablename__ = "panchina_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    vgp_result_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vgp_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    qty_proposed: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    session: Mapped[AnalysisSession] = relationship(back_populates="panchina_items")
    vgp_result: Mapped[VgpResult] = relationship(back_populates="panchina_items")
