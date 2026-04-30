"""ORM models — sotto-package di `talos.persistence` (ADR-0015).

Ogni modello vive in un modulo dedicato; `__init__` re-esporta le classi
in modo che `Base.metadata` veda tutte le tabelle quando il package
`talos.persistence` viene importato (es. da `migrations/env.py`).
"""

from talos.persistence.models.analysis_session import AnalysisSession

__all__ = ["AnalysisSession"]
