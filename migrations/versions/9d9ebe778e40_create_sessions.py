"""create sessions

Revision ID: 9d9ebe778e40
Revises:
Create Date: 2026-04-30

Initial migration. Crea la tabella `sessions` come da Allegato A di ADR-0015.
È la prima delle 10 tabelle previste; ogni tabella successiva avrà la sua
revision dedicata in CHG separato.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d9ebe778e40"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # L02 — budget di sessione (Opzione (a) ratificata Round 5)
        sa.Column("budget_eur", sa.Numeric(12, 2), nullable=False),
        # L05 — slider Velocity Target (range 7-30, default 15)
        sa.Column(
            "velocity_target",
            sa.Integer(),
            server_default=sa.text("15"),
            nullable=False,
        ),
        # sha256 del listino di input (32 bytes hex = 64 chars)
        sa.Column("listino_hash", sa.CHAR(64), nullable=False),
        # Multi-tenant ready (RLS — Allegato A): default 1 in MVP single-tenant
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("sessions")
