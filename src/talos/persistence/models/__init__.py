"""ORM models — sotto-package di `talos.persistence` (ADR-0015).

Ogni modello vive in un modulo dedicato; `__init__` re-esporta le classi
in modo che `Base.metadata` veda tutte le tabelle quando il package
`talos.persistence` viene importato (es. da `migrations/env.py`).
"""

from talos.persistence.models.analysis_session import AnalysisSession
from talos.persistence.models.asin_master import AsinMaster
from talos.persistence.models.audit_log import AuditLog
from talos.persistence.models.cart_item import CartItem
from talos.persistence.models.config_override import ConfigOverride
from talos.persistence.models.listino_item import ListinoItem
from talos.persistence.models.locked_in_item import LockedInItem
from talos.persistence.models.panchina_item import PanchinaItem
from talos.persistence.models.storico_ordine import StoricoOrdine
from talos.persistence.models.vgp_result import VgpResult

__all__ = [
    "AnalysisSession",
    "AsinMaster",
    "AuditLog",
    "CartItem",
    "ConfigOverride",
    "ListinoItem",
    "LockedInItem",
    "PanchinaItem",
    "StoricoOrdine",
    "VgpResult",
]
