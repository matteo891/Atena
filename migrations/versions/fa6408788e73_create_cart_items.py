"""create cart_items

Revision ID: fa6408788e73
Revises: c9527f017d5c
Create Date: 2026-04-30

Crea la tabella `cart_items` come da Allegato A di ADR-0015.
Carrello finale del Tetris allocator (ADR-0018): contiene gli ASIN
selezionati dall'algoritmo di saturazione 99.9% (R-06) + i lock-in
manuali a Priorità ∞ (R-04 — flag `locked_in`).

Doppia FK con ON DELETE CASCADE:
- `session_id → sessions.id`
- `vgp_result_id → vgp_results.id`
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fa6408788e73"
down_revision: str | None = "c9527f017d5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cart_items",
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
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_cost_eur", sa.Numeric(12, 2), nullable=False),
        # R-04: locked_in (Manual Override Priorita' infinito).
        # DEFAULT FALSE -> NOT NULL implicito (regola CHG-010).
        sa.Column(
            "locked_in",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("cart_items")
