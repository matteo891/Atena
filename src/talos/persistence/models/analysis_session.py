"""ORM model `sessions` (ADR-0015 Allegato A).

Rappresenta una singola sessione di analisi del bot — Stateless
(L01 Round 5): nessuna dipendenza causale da sessioni precedenti.

Nome della classe: `AnalysisSession`. Nome tabella: `sessions`.
La discrepanza è voluta: `Session` è già usato da `sqlalchemy.orm.Session`
per le sessioni di connessione DB; chiamare il modello `AnalysisSession`
elimina ambiguità nei moduli che importano sia il model sia l'ORM session.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Integer, Numeric, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talos.persistence.base import Base

if TYPE_CHECKING:
    from talos.persistence.models.cart_item import CartItem
    from talos.persistence.models.listino_item import ListinoItem
    from talos.persistence.models.panchina_item import PanchinaItem
    from talos.persistence.models.storico_ordine import StoricoOrdine
    from talos.persistence.models.vgp_result import VgpResult


class AnalysisSession(Base):
    """Sessione di analisi del listino (Allegato A ADR-0015 — tabella `sessions`).

    Una sessione è autocontenuta:
    - `budget_eur` è il capitale fisicamente disponibile per la run (L02 Round 5).
    - `velocity_target` è lo slider 7-30 gg, default 15 (L05 Round 5).
    - `listino_hash` è lo sha256 del file di input (32 bytes hex).
    - `tenant_id` predispone la multi-tenancy (RLS attiva su `storico_ordini`,
      `locked_in`, `config_overrides`); MVP single-tenant con default 1.

    Relationship one-to-many con `ListinoItem`: ogni sessione possiede zero o
    più righe di listino. Il delete cascade è gestito a livello DB tramite
    `ON DELETE CASCADE` definita sulla FK di `listino_items.session_id`;
    `passive_deletes=True` lato ORM evita doppia logica di cascade.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    budget_eur: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    velocity_target: Mapped[int] = mapped_column(
        Integer,
        server_default=text("15"),
        nullable=False,
    )
    listino_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        server_default=text("1"),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────
    listino_items: Mapped[list[ListinoItem]] = relationship(
        back_populates="session",
        passive_deletes=True,
    )
    vgp_results: Mapped[list[VgpResult]] = relationship(
        back_populates="session",
        passive_deletes=True,
    )
    cart_items: Mapped[list[CartItem]] = relationship(
        back_populates="session",
        passive_deletes=True,
    )
    panchina_items: Mapped[list[PanchinaItem]] = relationship(
        back_populates="session",
        passive_deletes=True,
    )
    # Storico ordini: NO passive_deletes/cascade (registro permanente,
    # FK senza CASCADE — cancellazione padre fallirà se ci sono storico).
    storico_ordini: Mapped[list[StoricoOrdine]] = relationship(
        back_populates="session",
    )
