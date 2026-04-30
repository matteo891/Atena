"""ORM model `listino_items` (ADR-0015 Allegato A).

Riga del listino fornitore in input alla sessione di analisi. Il match
ASIN avviene **dopo** l'ingestion: il campo `asin` è quindi nullable
finché Keepa/scraping non lo risolvono. `match_status` riflette l'esito
del Filtro Kill-Switch (`MATCH_SICURO` / `AMBIGUO` / `KILLED` —
R-01 NO SILENT DROPS).

FK `session_id → sessions.id ON DELETE CASCADE`: cancellare una sessione
elimina automaticamente le sue righe di listino. Cascade gestito a
livello DB; lato ORM `passive_deletes=True` su `AnalysisSession.listino_items`.

Indice `idx_listino_session` per le query di scan-per-sessione.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, BigInteger, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talos.persistence.base import Base

if TYPE_CHECKING:
    from talos.persistence.models.analysis_session import AnalysisSession
    from talos.persistence.models.vgp_result import VgpResult


class ListinoItem(Base):
    """Riga del listino fornitore (Allegato A ADR-0015 — tabella `listino_items`).

    Campi obbligatori dell'ingestion: `session_id`, `raw_title`, `cost_eur`.
    Campi popolati dal pipeline di matching: `asin`, `match_status`, `match_reason`.
    `qty_available` è opzionale (alcuni fornitori non lo dichiarano).

    Allegato A non prescrive una FK su `asin`: il match Amazon avviene
    in-flight via Keepa/scraping (ADR-0017) e l'`asin_master` può non
    essere ancora popolata al momento dell'ingestion. Mantenere `asin`
    come CHAR(10) libero senza FK è scelta deliberata dell'Allegato A.
    """

    __tablename__ = "listino_items"
    __table_args__ = (Index("idx_listino_session", "session_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    asin: Mapped[str | None] = mapped_column(CHAR(10), nullable=True)
    raw_title: Mapped[str] = mapped_column(Text, nullable=False)
    cost_eur: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    qty_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    session: Mapped[AnalysisSession] = relationship(back_populates="listino_items")
    vgp_results: Mapped[list[VgpResult]] = relationship(
        back_populates="listino_item",
        passive_deletes=True,
    )
