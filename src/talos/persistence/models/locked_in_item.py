"""ORM model `locked_in` (ADR-0015 Allegato A).

R-04 Manual Override: ASIN che il CFO ha forzato a entrare nel carrello
a Priorità ∞ (entrano per primi durante l'allocazione del Tetris, riservando
il loro budget al di fuori del ranking VGP).

Standalone (no FK): la `locked_in` è un set di "ASIN che il CFO vuole sempre
in cart, con almeno qty_min unità". A run-time il Tetris allocator (ADR-0018
`tetris/allocator.py`) consulta questa tabella **prima** di iniziare il fill
VGP-based, e ogni ASIN locked riservato finisce in `cart_items` con flag
`locked_in=true` (CHG-014).

RLS Zero-Trust attiva (terza tabella dopo `config_overrides` e
`storico_ordini`): policy `tenant_isolation` filtra per `tenant_id`.

Naming: classe `LockedInItem` per coerenza con `CartItem`/`PanchinaItem`
(ogni riga è un "item locked-in"); tabella `locked_in` letterale Allegato A.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from talos.persistence.base import Base


class LockedInItem(Base):
    """ASIN locked-in (Allegato A — `locked_in`).

    6 colonne: id BigInt PK, asin CHAR(10) NOT NULL, qty_min Int NOT NULL,
    notes Text NULL, created_at TIMESTAMPTZ default NOW NOT NULL (regola
    CHG-010), tenant_id BigInt default 1 NOT NULL.

    Allegato A non dichiara `UNIQUE(tenant_id, asin)`. Concettualmente per
    un dato tenant un ASIN può apparire una sola volta nella `locked_in`,
    ma il vincolo è applicativo (validazione in `ui/`). Errata corrige di
    ADR-0015 ammessa se in futuro si vuole irrigidire a UNIQUE.
    """

    __tablename__ = "locked_in"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asin: Mapped[str] = mapped_column(CHAR(10), nullable=False)
    qty_min: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        server_default=text("1"),
        nullable=False,
    )
