"""create panchina_items

Revision ID: 618105641c27
Revises: fa6408788e73
Create Date: 2026-04-30

Crea la tabella `panchina_items` come da Allegato A di ADR-0015.
Archivio R-09: ASIN con vgp_score > 0 (ROI ≥ soglia veto, match passato)
ma NON entrati nel carrello per saturazione del budget. Schema isomorfo
a `cart_items` (no `unit_cost_eur`, no `locked_in`); doppia FK CASCADE.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "618105641c27"
down_revision: str | None = "fa6408788e73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "panchina_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vgp_result_id",
            sa.BigInteger(),
            sa.ForeignKey("vgp_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qty_proposed", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("panchina_items")
