"""ORM model `vgp_results` (ADR-0015 Allegato A).

Nucleo del decisore: una riga per ogni ASIN di una sessione di analisi,
con i tre termini grezzi (ROI, velocity, cash_profit), i tre normalizzati
min-max [0,1] sul listino (L04b), il `vgp_score` finale e i flag
`veto_roi_passed` (R-08) / `kill_switch_triggered` (R-05).

Doppia FK con ON DELETE CASCADE:
- `session_id → sessions.id`
- `listino_item_id → listino_items.id`

Indice composito `idx_vgp_session_score` su `(session_id, vgp_score DESC)`
per le query "top-N per session" del Tetris allocator (ADR-0018).

Allegato A non dichiara `UNIQUE` su `listino_item_id`: la relazione è
modellata come many-to-one (lato `ListinoItem.vgp_results: list[VgpResult]`)
in aderenza letterale, anche se concettualmente per una stessa run di
sessione ogni listino_item produce 0 o 1 risultato.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talos.persistence.base import Base

if TYPE_CHECKING:
    from talos.persistence.models.analysis_session import AnalysisSession
    from talos.persistence.models.listino_item import ListinoItem


class VgpResult(Base):
    """Risultato VGP per un ASIN in una sessione (Allegato A — `vgp_results`).

    Schema verbatim Allegato A: 15 colonne, doppia FK CASCADE, indice
    composito `(session_id, vgp_score DESC)`.

    I campi numerici dei termini sono **nullable**: durante l'ingestion
    iniziale del listino le righe vengono create con campi a NULL e
    popolate progressivamente dal pipeline (ADR-0018 vgp/normalize, score,
    veto). Il `vgp_score = 0` può rappresentare sia "calcolato e azzerato"
    (R-05 kill-switch / R-08 veto fallito) sia "non ancora calcolato"; i
    flag booleani `veto_roi_passed` / `kill_switch_triggered` disambiguano.
    """

    __tablename__ = "vgp_results"
    __table_args__ = (
        Index(
            "idx_vgp_session_score",
            "session_id",
            text("vgp_score DESC"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    listino_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("listino_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    asin: Mapped[str] = mapped_column(CHAR(10), nullable=False)
    # Termini grezzi del decisore VGP
    roi_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    velocity_monthly: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    cash_profit_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # L04b: normalizzati min-max [0,1] sul listino di sessione
    roi_norm: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    velocity_norm: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    cash_profit_norm: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    # VGP score finale + flag R-08 / R-05
    vgp_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    veto_roi_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    kill_switch_triggered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Quantità target / lotti di 5 (R-06)
    qty_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qty_final: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    session: Mapped[AnalysisSession] = relationship(back_populates="vgp_results")
    listino_item: Mapped[ListinoItem] = relationship(back_populates="vgp_results")
