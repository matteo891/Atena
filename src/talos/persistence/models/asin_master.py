"""ORM model `asin_master` (ADR-0015 Allegato A).

Anagrafica ASIN: lookup table popolata da Keepa (ADR-0017) e fallback
scraping. Standalone — nessuna FK a tabelle interne.

Indice secondario `idx_asin_brand_model` per le query di lookup per
famiglia/modello (es. SamsungExtractor → tutti gli ASIN brand=Samsung
con model="S24").
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, TIMESTAMP, Boolean, Index, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from talos.persistence.base import Base


class AsinMaster(Base):
    """Anagrafica ASIN (Allegato A ADR-0015 — tabella `asin_master`).

    Campi anagrafici (`title`, `brand`) obbligatori; `model`, `rom_gb`,
    `ram_gb`, `connectivity`, `color_family`, `category_node` opzionali
    (popolati incrementalmente quando Keepa o lo scraper riescono a
    risolverli). `enterprise` flag booleano, default `false`. `last_seen_at`
    timestamp dell'ultimo refresh — utile per invalidare lookup stale.

    Convenzione applicata (coerente con `AnalysisSession`):
    colonne con `server_default` valido sono dichiarate `NOT NULL`
    nell'ORM, anche se l'Allegato A non lo specifica esplicitamente
    (il `DEFAULT` rende impossibile un valore NULL in pratica).
    """

    __tablename__ = "asin_master"
    __table_args__ = (Index("idx_asin_brand_model", "brand", "model"),)

    asin: Mapped[str] = mapped_column(CHAR(10), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    rom_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connectivity: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    enterprise: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
    )
    category_node: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
