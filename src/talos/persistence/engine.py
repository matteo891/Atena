"""Engine factory per app Talos (ADR-0015).

URL del DB letta via `TalosSettings.db_url` (CHG-2026-04-30-030); env
var canonica `TALOS_DB_URL` mappata dal config layer. `migrations/env.py`
e `scripts/db_bootstrap.py` restano su `os.getenv` per scope separato.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine

from talos.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy import Engine


def create_app_engine(url: str | None = None) -> Engine:
    """Crea l'engine SQLAlchemy 2.0 sync per l'app.

    `url` esplicito ha priorità; in alternativa fallback su
    `TalosSettings.db_url` (env var `TALOS_DB_URL`). Se nessuno dei due
    è settato, solleva `RuntimeError` con istruzioni operative.

    Pool conservativo (5+10) per dialetti con `QueuePool` (Postgres):
    app Streamlit single-process, traffico interno; aggiustabile quando
    arriverà `ui/` multi-utente. SQLite usa `SingletonThreadPool` e non
    accetta `pool_size`/`max_overflow`: i parametri sono applicati solo
    quando il dialect li supporta.
    `pool_pre_ping=True` copre il caso di connessioni dormienti.
    """
    resolved = url or get_settings().db_url
    if not resolved:
        msg = (
            "TALOS_DB_URL non settato e nessun url esplicito passato a "
            "create_app_engine(). Esempio: "
            "postgresql+psycopg://talos_app:<password>@localhost:5432/talos"
        )
        raise RuntimeError(msg)
    kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
    if not resolved.startswith("sqlite"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    return create_engine(resolved, **kwargs)
