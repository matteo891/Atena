"""add_unique_constraint_sessions_tenant_hash

Revision ID: e965e1b81041
Revises: 6e03f2a4f5a3
Create Date: 2026-04-30 21:54:53.313697

CHG-2026-04-30-047: idempotency su `sessions(tenant_id, listino_hash)`.

Sblocca:
- `find_session_by_hash` (lookup deterministico per evitare ricreazione)
- Pattern futuro `upsert_session` con `ON CONFLICT (tenant_id, listino_hash) DO ...`

Vincolo applicato come `UNIQUE INDEX` (non constraint) per allineamento
con gli altri indici dello schema (CHG-009, CHG-013, ecc) e per
permettere drop/rebuild snello in errata corrige future.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e965e1b81041"
down_revision: str | None = "6e03f2a4f5a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aggiunge UNIQUE INDEX su (tenant_id, listino_hash) della tabella sessions."""
    op.create_index(
        "ux_sessions_tenant_hash",
        "sessions",
        ["tenant_id", "listino_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Rimuove l'UNIQUE INDEX."""
    op.drop_index("ux_sessions_tenant_hash", table_name="sessions")
