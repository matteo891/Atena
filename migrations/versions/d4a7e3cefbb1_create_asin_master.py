"""create asin_master

Revision ID: d4a7e3cefbb1
Revises: 9d9ebe778e40
Create Date: 2026-04-30

Crea la tabella `asin_master` come da Allegato A di ADR-0015 (anagrafica
ASIN, popolata da Keepa/scraping). Standalone — nessuna FK.
Indice secondario `idx_asin_brand_model` su (brand, model) per le query
di lookup per famiglia/modello.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a7e3cefbb1"
down_revision: str | None = "9d9ebe778e40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asin_master",
        sa.Column("asin", sa.CHAR(10), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("rom_gb", sa.Integer(), nullable=True),
        sa.Column("ram_gb", sa.Integer(), nullable=True),
        sa.Column("connectivity", sa.Text(), nullable=True),
        sa.Column("color_family", sa.Text(), nullable=True),
        sa.Column(
            "enterprise",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("category_node", sa.Text(), nullable=True),
        sa.Column(
            "last_seen_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_asin_brand_model",
        "asin_master",
        ["brand", "model"],
    )


def downgrade() -> None:
    op.drop_index("idx_asin_brand_model", table_name="asin_master")
    op.drop_table("asin_master")
