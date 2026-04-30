"""Persistenza — declarative base SQLAlchemy 2.0 (ADR-0015)."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base per ogni ORM model di Talos.

    Tutti i modelli concreti (sessions, asin_master, listino_items, vgp_results,
    cart_items, panchina_items, storico_ordini, locked_in, config_overrides,
    audit_log) ereditano da `Base` e vengono introdotti uno alla volta in CHG
    dedicati che includono la corrispondente Alembic revision.

    Lo schema iniziale di riferimento è l'Allegato A di ADR-0015.
    """
