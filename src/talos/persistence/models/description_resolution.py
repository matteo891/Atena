"""ORM model `description_resolutions` (cache asin_resolver, CHG-2026-05-01-019).

Cache descrizione->ASIN risolto. Decisioni Leader 2026-05-01 round 4:

- **alpha=A NO RLS**: cache infrastructural, no PII, dato pubblico
  Amazon. Coerente con tabelle ad alta volatilità (vgp_results,
  cart_items).
- **beta=A UNIQUE `(tenant_id, description_hash)`**: ogni tenant ha
  la sua cache (il `confidence_pct` dipende dal prezzo input,
  tenant-side). Coerente con `sessions(tenant_id, listino_hash)`
  CHG-047.
- **gamma=A NO trigger audit**: cache write-many, audit_log
  esploderebbe.

Hash: SHA-256 hex (64 char) di `description.strip().lower()`,
deterministico cross-platform. Il caller normalizza prima di hashing.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Index, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from talos.persistence.base import Base


class DescriptionResolution(Base):
    """Cache risoluzione descrizione->ASIN (CHG-019, ADR-0017).

    Hit rate atteso > 50% per batch ricorrenti dello stesso CFO
    (stesso fornitore con descrizioni stabili). `resolved_at`
    timestamp utile per invalidare entries stantie (TTL applicabile
    a livello query, non DB-side, scope futuro).
    """

    __tablename__ = "description_resolutions"
    __table_args__ = (
        Index(
            "ux_description_resolutions_tenant_hash",
            "tenant_id",
            "description_hash",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    asin: Mapped[str] = mapped_column(CHAR(10), nullable=False)
    confidence_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
