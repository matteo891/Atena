"""fix_config_overrides_unique_nulls_not_distinct

Revision ID: e8b80f77961b
Revises: e965e1b81041
Create Date: 2026-04-30 22:09:45.746655

CHG-2026-04-30-050: bug fix UNIQUE INDEX `idx_config_unique`.

Postgres default tratta `NULL != NULL` per UNIQUE constraints (SQL
standard). Con `scope_key=NULL` (override globale), due insert con
stessa `(tenant_id, scope, key)` sono ammessi → l'UPSERT
`ON CONFLICT (tenant_id, scope, scope_key, key)` non matcha mai
quando `scope_key IS NULL`, creando righe duplicate invece di update.

Fix: ricrea l'index con `NULLS NOT DISTINCT` (Postgres 15+) che tratta
NULL come uguale per il vincolo UNIQUE. Coerente con la semantica
"un solo override globale per (tenant, scope, key)".

Container test: postgres:16-alpine (compatibile).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8b80f77961b"
down_revision: str | None = "e965e1b81041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ricrea idx_config_unique con NULLS NOT DISTINCT (Postgres 15+)."""
    op.execute("DROP INDEX IF EXISTS idx_config_unique")
    op.execute(
        "CREATE UNIQUE INDEX idx_config_unique "
        "ON config_overrides (tenant_id, scope, scope_key, key) "
        "NULLS NOT DISTINCT",
    )


def downgrade() -> None:
    """Ripristina idx_config_unique con default NULLS DISTINCT."""
    op.execute("DROP INDEX IF EXISTS idx_config_unique")
    op.execute(
        "CREATE UNIQUE INDEX idx_config_unique "
        "ON config_overrides (tenant_id, scope, scope_key, key)",
    )
