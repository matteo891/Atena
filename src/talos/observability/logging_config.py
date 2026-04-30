"""Configurazione `structlog` — ADR-0021.

`configure_logging` è chiamata esplicitamente dall'entrypoint del caller
(Streamlit, CLI, pytest setup). Nessun bootstrap implicito da
`talos.__init__` per non sorprendere i test che non se lo aspettano.

Output:
- `json_output=True` → `structlog.processors.JSONRenderer()` (default in CI/prod)
- `json_output=False` → `structlog.dev.ConsoleRenderer()` (dev locale)

Livelli:
- "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
"""

from __future__ import annotations

import logging
from typing import Final

import structlog

_LEVELS: Final[dict[str, int]] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(*, level: str = "INFO", json_output: bool = True) -> None:
    """Configura structlog con il pipeline canonico (ADR-0021).

    Idempotente. Chiamabile più volte in un test (cambiando livello o renderer)
    grazie a ``cache_logger_on_first_use=False`` in test mode.
    """
    if level.upper() not in _LEVELS:
        msg = f"Livello log non valido: {level!r}. Atteso: {sorted(_LEVELS)}"
        raise ValueError(msg)

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_LEVELS[level.upper()]),
        cache_logger_on_first_use=True,
    )


def bind_session_context(
    *,
    session_id: int,
    listino_hash: str,
    velocity_target: int,
    budget_eur: float,
) -> None:
    """Lega il context globale di una sessione di analisi (ADR-0021).

    Tutti gli eventi successivi nella stessa task ereditano questi campi.
    Va invocato una volta a inizio sessione, dopo `configure_logging`.
    """
    structlog.contextvars.bind_contextvars(
        session_id=session_id,
        listino_hash=listino_hash,
        velocity_target=velocity_target,
        budget_eur=budget_eur,
    )


def clear_session_context() -> None:
    """Pulisce il context legato (ADR-0021). Da invocare a fine sessione."""
    structlog.contextvars.clear_contextvars()
