"""create description_resolutions

Revision ID: 1d67de49c197
Revises: e8b80f77961b
Create Date: 2026-05-01 19:37:11.032905

CHG-2026-05-01-019: cache descrizione->ASIN per asin_resolver
(blocco "(descrizione, prezzo) -> ASIN", ADR-0017).

Decisioni Leader 2026-05-01 round 4:
- alpha=A: NO RLS (cache infrastructural, no PII).
- beta=A: UNIQUE `(tenant_id, description_hash)` (coerente con
  sessions tenant_hash, CHG-047).
- gamma=A: NO trigger audit (cache write-many).

NB: lo spurio drop/recreate di `idx_config_unique` rilevato da
alembic autogenerate e' stato rimosso. Era causato dal modello ORM
`ConfigOverride` che non dichiarava `postgresql_nulls_not_distinct`
(drift fra modello e DB introdotto da CHG-050). Allineamento del
modello fatto in questo CHG (no migration necessaria, l'indice e'
gia' come deve essere lato DB).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d67de49c197"
down_revision: str | None = "e8b80f77961b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "description_resolutions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("description_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("asin", sa.CHAR(length=10), nullable=False),
        sa.Column("confidence_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column(
            "resolved_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_description_resolutions_tenant_hash",
        "description_resolutions",
        ["tenant_id", "description_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_description_resolutions_tenant_hash",
        table_name="description_resolutions",
    )
    op.drop_table("description_resolutions")
