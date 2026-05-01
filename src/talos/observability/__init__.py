"""Observability — logging strutturato + catalogo eventi (ADR-0021).

Re-export delle API pubbliche.
"""

from talos.observability.events import CANONICAL_EVENTS
from talos.observability.logging_config import (
    bind_request_context,
    bind_session_context,
    clear_request_context,
    clear_session_context,
    configure_logging,
)

__all__ = [
    "CANONICAL_EVENTS",
    "bind_request_context",
    "bind_session_context",
    "clear_request_context",
    "clear_session_context",
    "configure_logging",
]
