"""create vgp_results

Revision ID: c9527f017d5c
Revises: 027a145f76a8
Create Date: 2026-04-30

Crea la tabella `vgp_results` come da Allegato A di ADR-0015.
Nucleo del decisore: ogni riga rappresenta il calcolo VGP per un ASIN
in una sessione. Doppia FK con ON DELETE CASCADE (`session_id`,
`listino_item_id`).

Indice composito `idx_vgp_session_score` su `(session_id, vgp_score DESC)`
supporta le query "top-N per session" del Tetris allocator (ADR-0018).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9527f017d5c"
down_revision: str | None = "027a145f76a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vgp_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "listino_item_id",
            sa.BigInteger(),
            sa.ForeignKey("listino_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asin", sa.CHAR(10), nullable=False),
        # Termini grezzi del decisore
        sa.Column("roi_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("velocity_monthly", sa.Numeric(12, 4), nullable=True),
        sa.Column("cash_profit_eur", sa.Numeric(12, 2), nullable=True),
        # L04b: termini normalizzati min-max [0,1] sul listino di sessione
        sa.Column("roi_norm", sa.Numeric(6, 4), nullable=True),
        sa.Column("velocity_norm", sa.Numeric(6, 4), nullable=True),
        sa.Column("cash_profit_norm", sa.Numeric(6, 4), nullable=True),
        # VGP score finale + flag R-08 / R-05
        sa.Column("vgp_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("veto_roi_passed", sa.Boolean(), nullable=True),
        sa.Column("kill_switch_triggered", sa.Boolean(), nullable=True),
        # Quantità target / lotti di 5 (R-06)
        sa.Column("qty_target", sa.Integer(), nullable=True),
        sa.Column("qty_final", sa.Integer(), nullable=True),
    )
    # Indice composito con `vgp_score DESC` per supportare "top-N per session"
    op.create_index(
        "idx_vgp_session_score",
        "vgp_results",
        ["session_id", sa.text("vgp_score DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_vgp_session_score", table_name="vgp_results")
    op.drop_table("vgp_results")
