"""Repository per `config_overrides` (ADR-0015).

Lookup + upsert runtime di parametri di configurazione del tenant
(es. soglia Veto ROI L10, Referral_Fee per categoria L12). Scope a
3 livelli: `global` → `category` → `asin` (verbatim Allegato A).

**RLS Zero-Trust** (ADR-0015 + CHG-2026-04-30-012): la tabella
`config_overrides` ha policy `tenant_isolation`. Tutte le operazioni
qui devono essere wrappate in `with_tenant(tenant_id)` (lo facciamo
internamente).

API:
- `get_config_override_numeric(...) -> Decimal | None`
- `set_config_override_numeric(...) -> None` (UPSERT idempotente).
- `list_category_referral_fees(...) -> dict[str, Decimal]` (CHG-051,
  L12 Round 5: mappa `category_node` → `referral_fee_pct`).

Le chiavi `value_text` (`set_config_override_text`,
`get_config_override_text`) sono scope CHG futuro quando emergeranno
override testuali (es. preset di brand).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from talos.persistence.models import ConfigOverride
from talos.persistence.session import with_tenant

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


SCOPE_GLOBAL: str = "global"
SCOPE_CATEGORY: str = "category"
SCOPE_ASIN: str = "asin"

_VALID_SCOPES: frozenset[str] = frozenset({SCOPE_GLOBAL, SCOPE_CATEGORY, SCOPE_ASIN})

# Chiave canonica del Referral Fee Amazon per categoria (L12 PROJECT-RAW Round 5).
# Override per `scope="category"`, `scope_key=<category_node>`.
KEY_REFERRAL_FEE_PCT: str = "referral_fee_pct"


def _validate_scope(scope: str) -> None:
    if scope not in _VALID_SCOPES:
        msg = f"scope invalido: {scope!r}. Ammessi: {sorted(_VALID_SCOPES)}."
        raise ValueError(msg)


def get_config_override_numeric(
    db_session: Session,
    *,
    key: str,
    tenant_id: int = 1,
    scope: str = SCOPE_GLOBAL,
    scope_key: str | None = None,
) -> Decimal | None:
    """Lookup di un override numerico per `(tenant_id, scope, scope_key, key)`.

    :returns: `Decimal` se esiste, `None` se nessun override registrato.
    :raises ValueError: se `scope` non e' tra gli ammessi.
    """
    _validate_scope(scope)
    scope_key_filter = (
        ConfigOverride.scope_key.is_(None)
        if scope_key is None
        else ConfigOverride.scope_key == scope_key
    )
    with with_tenant(db_session, tenant_id):
        stmt = select(ConfigOverride.value_numeric).where(
            ConfigOverride.tenant_id == tenant_id,
            ConfigOverride.scope == scope,
            scope_key_filter,
            ConfigOverride.key == key,
        )
        return db_session.scalar(stmt)


def list_category_referral_fees(
    db_session: Session,
    *,
    tenant_id: int = 1,
) -> dict[str, Decimal]:
    """Lista tutti gli override `referral_fee_pct` con `scope="category"` per il tenant.

    Pattern usage: il CFO configura una mappa `category_node → fee` per
    correggere/sovrascrivere il valore del listino raw quando l'ASIN
    appartiene a una categoria nota (L12 PROJECT-RAW Round 5).

    :returns: dict `{category_node: referral_fee_pct}`. Vuoto se nessun
        override registrato.
    """
    with with_tenant(db_session, tenant_id):
        stmt = select(ConfigOverride.scope_key, ConfigOverride.value_numeric).where(
            ConfigOverride.tenant_id == tenant_id,
            ConfigOverride.scope == SCOPE_CATEGORY,
            ConfigOverride.key == KEY_REFERRAL_FEE_PCT,
            ConfigOverride.scope_key.is_not(None),
            ConfigOverride.value_numeric.is_not(None),
        )
        # Filtri SQL `is_not(None)` garantiscono che entrambi i campi siano popolati;
        # niente `continue` defensive lato Python (R-01 governance: no silent drops).
        return {
            str(scope_key): Decimal(value) for scope_key, value in db_session.execute(stmt).all()
        }


def set_config_override_numeric(  # noqa: PLR0913 — 6 arg necessari (db + key + value + tenant + scope + scope_key) per UPSERT su UNIQUE composito Allegato A
    db_session: Session,
    *,
    key: str,
    value: Decimal | float,
    tenant_id: int = 1,
    scope: str = SCOPE_GLOBAL,
    scope_key: str | None = None,
) -> None:
    """UPSERT di un override numerico (`ON CONFLICT (tenant, scope, scope_key, key) DO UPDATE`).

    Usa `dialects.postgresql.insert` con `on_conflict_do_update` ancorato
    all'UNIQUE INDEX `idx_config_unique` (Allegato A). Il caller e'
    responsabile di commit/rollback (tipicamente via `session_scope`).

    :raises ValueError: se `scope` non e' tra gli ammessi.
    """
    _validate_scope(scope)
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    with with_tenant(db_session, tenant_id):
        stmt = (
            pg_insert(ConfigOverride)
            .values(
                tenant_id=tenant_id,
                scope=scope,
                scope_key=scope_key,
                key=key,
                value_numeric=decimal_value,
                value_text=None,
            )
            .on_conflict_do_update(
                index_elements=["tenant_id", "scope", "scope_key", "key"],
                set_={"value_numeric": decimal_value, "value_text": None},
            )
        )
        db_session.execute(stmt)
