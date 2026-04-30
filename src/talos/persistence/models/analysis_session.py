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

from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Integer, Numeric, func, text
from sqlalchemy.orm import Mapped, mapped_column

from talos.persistence.base import Base


class AnalysisSession(Base):
    """Sessione di analisi del listino (Allegato A ADR-0015 — tabella `sessions`).

    Una sessione è autocontenuta:
    - `budget_eur` è il capitale fisicamente disponibile per la run (L02 Round 5).
    - `velocity_target` è lo slider 7-30 gg, default 15 (L05 Round 5).
    - `listino_hash` è lo sha256 del file di input (32 bytes hex).
    - `tenant_id` predispone la multi-tenancy (RLS attiva su `storico_ordini`,
      `locked_in`, `config_overrides`); MVP single-tenant con default 1.
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
