"""ORM model `config_overrides` (ADR-0015 Allegato A).

Override runtime di parametri di configurazione (es. `veto_roi_pct`,
`referral_fee_pct`) con scoping a 3 livelli: `global` → `category` → `asin`.

**Prima tabella con Row-Level Security (RLS) attiva** (Zero-Trust ADR-0015):
la policy `tenant_isolation` (definita nella migration via `op.execute`)
filtra le righe per `tenant_id = current_setting('talos.tenant_id', true)::bigint`.
Lato applicativo, è responsabilità del bootstrap ORM (futuro CHG su `engine`)
eseguire `SET LOCAL talos.tenant_id = '<id>'` a inizio transazione.

L'indice **UNIQUE composito** `idx_config_unique` su
(`tenant_id`, `scope`, `scope_key`, `key`) garantisce che per ogni tenant
non esistano due override con la stessa chiave nello stesso scope.

Il nome colonna `key` confligge concettualmente con `dict.keys()` ma SQLAlchemy
2.0 lo accetta senza problemi (non è un keyword Python). Manteniamo il nome
letterale dell'Allegato A.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, BigInteger, Index, Numeric, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from talos.persistence.base import Base


class ConfigOverride(Base):
    """Override di configurazione runtime (Allegato A ADR-0015 — `config_overrides`).

    Scope ammessi (validati a livello applicativo, Allegato A non dichiara CHECK):
    - `global`: applica a tutto (es. soglia veto ROI di default)
    - `category`: applica al `category_node` Amazon (es. `referral_fee_pct`)
    - `asin`: applica a un singolo ASIN

    `value_numeric` e `value_text` sono **mutuamente esclusivi nell'intent**
    (uno solo dei due è popolato a seconda del tipo della chiave) ma l'Allegato A
    non vincola questo a livello DB. Validazione applicativa.
    """

    __tablename__ = "config_overrides"
    __table_args__ = (
        Index(
            "idx_config_unique",
            "tenant_id",
            "scope",
            "scope_key",
            "key",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    scope_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        server_default=text("1"),
        nullable=False,
    )
