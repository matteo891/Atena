"""Persistenza — SQLAlchemy 2.0 sync + Alembic + Zero-Trust (ADR-0015).

Re-export delle API pubbliche. I modelli concreti sono in `models/` e
vengono aggiunti incrementalmente in CHG separati.

L'import di `models` è importante: registra le tabelle in `Base.metadata`
così che `migrations/env.py` (che fa `target_metadata = Base.metadata`)
le veda tutte automaticamente in `alembic revision --autogenerate`.
"""

from talos.persistence.base import Base
from talos.persistence.engine import create_app_engine
from talos.persistence.models import (
    AnalysisSession,
    AsinMaster,
    AuditLog,
    CartItem,
    ConfigOverride,
    ListinoItem,
    LockedInItem,
    PanchinaItem,
    StoricoOrdine,
    VgpResult,
)
from talos.persistence.session import (
    make_session_factory,
    session_scope,
    with_tenant,
)
from talos.persistence.session_repository import (
    SessionSummary,
    list_recent_sessions,
    save_session_result,
)

__all__ = [
    "AnalysisSession",
    "AsinMaster",
    "AuditLog",
    "Base",
    "CartItem",
    "ConfigOverride",
    "ListinoItem",
    "LockedInItem",
    "PanchinaItem",
    "SessionSummary",
    "StoricoOrdine",
    "VgpResult",
    "create_app_engine",
    "list_recent_sessions",
    "make_session_factory",
    "save_session_result",
    "session_scope",
    "with_tenant",
]
