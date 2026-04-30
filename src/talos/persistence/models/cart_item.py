"""ORM model `cart_items` (ADR-0015 Allegato A).

Carrello finale del Tetris allocator (ADR-0018): l'output principale
della sessione di analisi. Contiene gli ASIN selezionati dall'algoritmo
di saturazione 99.9% (R-06) + i lock-in manuali a Priorità ∞ (R-04).

Doppia FK con ON DELETE CASCADE: `session_id`, `vgp_result_id`.

Il flag `locked_in` (R-04) marca le righe inserite via Manual Override
del CFO: durante l'allocazione del Tetris (ADR-0018 `tetris/allocator.py`)
queste righe entrano per prime, riservando il loro budget al di fuori del
ranking VGP (Priorità ∞).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talos.persistence.base import Base

if TYPE_CHECKING:
    from talos.persistence.models.analysis_session import AnalysisSession
    from talos.persistence.models.storico_ordine import StoricoOrdine
    from talos.persistence.models.vgp_result import VgpResult


class CartItem(Base):
    """Riga del carrello finale (Allegato A — `cart_items`).

    Schema verbatim Allegato A: 6 colonne, doppia FK CASCADE, flag `locked_in`
    con default `false` (regola CHG-010 → NOT NULL).
    """

    __tablename__ = "cart_items"

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
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_eur: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # R-04: Manual Override (Priorità ∞ nel Tetris)
    locked_in: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────
    session: Mapped[AnalysisSession] = relationship(back_populates="cart_items")
    vgp_result: Mapped[VgpResult] = relationship(back_populates="cart_items")
    # Storico ordini: NO cascade (registro permanente, FK senza CASCADE).
    storico_ordini: Mapped[list[StoricoOrdine]] = relationship(
        back_populates="cart_item",
    )
