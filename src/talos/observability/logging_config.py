"""Configurazione `structlog` — ADR-0021.

`configure_logging` è chiamata esplicitamente dall'entrypoint del caller
(Streamlit, CLI, pytest setup). Nessun bootstrap implicito da
`talos.__init__` per non sorprendere i test che non se lo aspettano.

Output:
- `json_output=True` → `structlog.processors.JSONRenderer()` (default in CI/prod)
- `json_output=False` → `structlog.dev.ConsoleRenderer()` (dev locale)

Livelli:
- "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

Bind context split (CHG-2026-05-01-035, B1.2):
- `bind_request_context(tenant_id, request_id?)`: ogni invocazione di
  `run_session` / `replay_session` / flow UI. Genera `request_id` UUID4
  se non passato, ritorna l'id binded. Sempre presente in produzione.
- `bind_session_context(session_id, listino_hash, velocity_target,
  budget_eur)`: solo POST-save (quando esiste un `id` reale in DB) o
  in `replay_session` con `session_id` ricaricato. Estende il context
  request-level senza sovrascriverlo.
- `clear_request_context()` / `clear_session_context()` in finally,
  rispettivamente. NB: l'implementazione di `clear_*` in structlog
  pulisce **tutti** i contextvars (non per-key); chiamare entrambi è
  idempotente. Pattern raccomandato: 1 solo `clear_request_context()`
  in finally del caller più esterno.
"""

from __future__ import annotations

import logging
import uuid
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


def bind_request_context(
    *,
    tenant_id: int,
    request_id: str | None = None,
) -> str:
    """Lega il context request-level (CHG-2026-05-01-035 + 036, ADR-0021).

    Ogni invocazione di `run_session` / `replay_session` / flow UI deve
    invocare questo helper all'ingresso (try/finally + `clear_request_context`).
    Sblocca la correlazione log end-to-end fra eventi emessi in moduli
    diversi nella stessa unit-of-work.

    **Idempotente nesting-safe (CHG-2026-05-01-036, B1.3)**: se
    `request_id` è già binded nel context corrente, viene **riusato**
    invece di sovrascritto. Pattern: il caller più esterno (es. UI
    Streamlit) binda; i caller annidati (es. orchestrator chiamato
    dalla UI) condividono lo stesso request_id. Il caller più esterno
    è anche responsabile del `clear_request_context` finale.

    :param tenant_id: tenant attivo (MVP single-tenant: 1).
    :param request_id: opzionale; se `None`, viene generato UUID4
        stringa quando non c'è bind preesistente.
    :returns: il `request_id` effettivamente binded (esistente o nuovo).
    """
    existing = structlog.contextvars.get_contextvars()
    if "request_id" in existing:
        # Nesting: rispetta il bind esistente, non sovrascrivere.
        return str(existing["request_id"])
    rid = request_id if request_id is not None else str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        request_id=rid,
        tenant_id=tenant_id,
    )
    return rid


def is_request_context_bound() -> bool:
    """True se un `request_id` è già binded nel context corrente.

    Helper introspettivo (CHG-2026-05-01-036, B1.3) per i caller
    annidati che vogliono fare clear *solo se* sono i bind originator
    (pattern is_outer). Esempio:

        is_outer = not is_request_context_bound()
        bind_request_context(tenant_id=1)  # idempotente
        try:
            ...  # work
        finally:
            if is_outer:
                clear_request_context()
    """
    return "request_id" in structlog.contextvars.get_contextvars()


def bind_session_context(
    *,
    session_id: int,
    listino_hash: str,
    velocity_target: int,
    budget_eur: float,
) -> None:
    """Lega il context session-level (post-save, ADR-0021).

    Estende il context request-level (`bind_request_context`) con i
    metadati della sessione DB. Tutti gli eventi successivi ereditano
    `session_id`/`listino_hash`/`velocity_target`/`budget_eur` oltre
    a `request_id`/`tenant_id`.

    Va invocato:
    - In `dashboard.try_persist_session` post-save (quando `id` esiste).
    - In `replay_session` con `session_id` ricaricato da `loaded`.
    - **Mai** pre-save (`session_id=0` non significativo): preferire
      solo `bind_request_context`.
    """
    structlog.contextvars.bind_contextvars(
        session_id=session_id,
        listino_hash=listino_hash,
        velocity_target=velocity_target,
        budget_eur=budget_eur,
    )


def clear_request_context() -> None:
    """Pulisce TUTTI i contextvars (CHG-2026-05-01-035, ADR-0021 B1.2).

    Implementazione `structlog.contextvars.clear_contextvars()` non è
    per-key: pulisce l'intero scope. Chiamarlo in `finally` del caller
    più esterno (orchestrator/UI) garantisce nessun leak fra request.
    """
    structlog.contextvars.clear_contextvars()


def clear_session_context() -> None:
    """Pulisce TUTTI i contextvars (alias semantico di `clear_request_context`).

    Mantenuto per backward compat con test storici (`test_logging_config`)
    e per chiarezza nel caller `dashboard` quando il bind era solo
    session-level. In nuovi caller preferire `clear_request_context`.
    """
    structlog.contextvars.clear_contextvars()
