"""ORM model `audit_log` (ADR-0015 Allegato A).

Registro append-only delle modifiche sulle tabelle critiche. Ogni INSERT/
UPDATE/DELETE su `storico_ordini`, `locked_in`, `config_overrides` produce
automaticamente una riga qui via trigger AFTER (definito nella migration).

Append-only enforcement (Zero-Trust):
- A livello DB: `REVOKE UPDATE, DELETE ON audit_log FROM talos_app` (gestito
  fuori da questa migration — vedi nota).
- A livello applicativo: `talos_app` può solo `INSERT`. La verifica è coperta
  da `talos_audit` (read-only) per investigation.

Nota: i ruoli e i GRANT/REVOKE sono **out-of-scope** della migration
`6e03f2a4f5a3`: richiedono ruoli pre-esistenti. Saranno gestiti da un
setup bootstrap esterno (futuro CHG su `scripts/db-bootstrap.sh`).

Lato ORM nessuna FK, nessuna relationship. La connessione semantica con le
3 tabelle audited avviene via `table_name` (TEXT del nome) e `row_id`
(BigInt dell'`id` originale), non come FK formale — coerente con la natura
append-only del registro.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, TIMESTAMP, BigInteger, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from talos.persistence.base import Base


class AuditLog(Base):
    """Riga del registro di audit (Allegato A — `audit_log`).

    8 colonne. Append-only. Ogni record rappresenta una mutazione di una
    tabella critica.

    Campo `op`:
    - `'I'` = INSERT (`before_data` = NULL, `after_data` = JSONB della nuova riga)
    - `'U'` = UPDATE (`before_data` e `after_data` entrambi popolati)
    - `'D'` = DELETE (`before_data` = JSONB della vecchia riga, `after_data` = NULL)

    `row_id` è l'`id` BigInt della riga modificata (lookup chain con la
    tabella sorgente via `table_name` + `row_id`, senza FK formale).
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    table_name: Mapped[str] = mapped_column(Text, nullable=False)
    op: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    row_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
