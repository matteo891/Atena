"""Persistenza — SQLAlchemy 2.0 sync + Alembic + Zero-Trust (ADR-0015).

Re-export delle API pubbliche. I modelli concreti sono in moduli dedicati
e vengono aggiunti incrementalmente in CHG separati.
"""

from talos.persistence.base import Base

__all__ = ["Base"]
