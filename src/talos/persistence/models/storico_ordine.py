"""ORM model `storico_ordini` (ADR-0015 Allegato A).

Registro permanente degli ordini effettuati (R-03 ORDER-DRIVEN MEMORY).
Una riga per ASIN ordinato in una sessione. **Lo storico è permanente**:
le FK verso `sessions` e `cart_items` **non** hanno `ON DELETE CASCADE`
(aderenza letterale all'Allegato A) — cancellare la sessione o il cart_item
referenziati da uno storico_ordine **fallisce** a livello Postgres
(default RESTRICT). Comportamento desiderato per un registro contabile.

Lato ORM: nessun `passive_deletes`/`cascade` configurato sulle relationship
inverse di `AnalysisSession.storico_ordini` e `CartItem.storico_ordini`.
SQLAlchemy default ("save-update, merge") preserva il flusso normale ma
non tenta DELETE in cascata.

RLS attiva (Zero-Trust): policy `tenant_isolation` — pattern identico a
`config_overrides` (CHG-012).

Naming: classe `StoricoOrdine` (singolare, PEP 8 PascalCase) per la riga;
`__tablename__ = "storico_ordini"` plurale per la tabella (Allegato A).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    TIMESTAMP,
    BigInteger,
    ForeignKey,
    Integer,
    Numeric,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talos.persistence.base import Base

if TYPE_CHECKING:
    from talos.persistence.models.analysis_session import AnalysisSession
    from talos.persistence.models.cart_item import CartItem


class StoricoOrdine(Base):
    """Riga del registro ordini (Allegato A — `storico_ordini`).

    8 colonne: id BigInt PK, FK doppia (no CASCADE), asin/qty/unit_cost
    obbligatori, `ordered_at` con `DEFAULT NOW()` (regola CHG-010 →
    NOT NULL), `tenant_id` per isolamento RLS.
    """

    __tablename__ = "storico_ordini"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Aderenza letterale Allegato A: NO ON DELETE CASCADE (registro permanente)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sessions.id"),
        nullable=False,
    )
    cart_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cart_items.id"),
        nullable=False,
    )
    asin: Mapped[str] = mapped_column(CHAR(10), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_eur: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        server_default=text("1"),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────
    # Default SQLAlchemy cascade ("save-update, merge"): nessun delete cascade.
    session: Mapped[AnalysisSession] = relationship(back_populates="storico_ordini")
    cart_item: Mapped[CartItem] = relationship(back_populates="storico_ordini")
