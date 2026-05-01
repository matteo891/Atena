"""Fixture comuni cross-test (ADR-0019).

In bootstrap minimale (CHG-2026-04-30-004) era vuoto; le fixture di sessione
(`db_session`, `playwright_browser`, `keepa_cassette`) saranno aggiunte
modulo per modulo, ognuna sotto l'ADR del modulo che la introduce.

`log_capture` introdotta in CHG-2026-05-01-031 (B1.1.b) per consolidare il
pattern `structlog.testing.LogCapture` usato dai test telemetria post-bridge
stdlib→structlog (CHG-B1.1.a..e). Estratta da `test_logging_config.py` e
`test_vgp_telemetry.py` quando i consumer sono diventati ≥3 (rule of three).
"""

from __future__ import annotations

import pytest
import structlog
from structlog.testing import LogCapture


@pytest.fixture
def log_capture() -> LogCapture:
    """Cattura eventi structlog per assertion (ADR-0021).

    Riconfigura globalmente structlog con `LogCapture` come unico processor
    + `merge_contextvars` (preserva propagazione contestuale del bind, utile
    per i test futuri di `bind_session_context` / `bind_request_context`).
    Function-scoped: ogni test ricrea la propria istanza, side-effect di
    riconfigurazione globale tollerato (validato cross-test in CHG-030).
    """
    capture = LogCapture()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            capture,
        ],
        cache_logger_on_first_use=False,
    )
    return capture
