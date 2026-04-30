"""Engine factory per app Talos (ADR-0015).

Single source di verità per la URL del DB: stessa env var `TALOS_DB_URL`
che usa `migrations/env.py`. Il `config/` layer (pydantic-settings, CHG
futuro) sostituirà la lettura diretta di env var senza cambiare la firma
pubblica `create_app_engine(url=None)`.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine

if TYPE_CHECKING:
    from sqlalchemy import Engine


def create_app_engine(url: str | None = None) -> Engine:
    """Crea l'engine SQLAlchemy 2.0 sync per l'app.

    `url` esplicito ha priorità; in alternativa fallback su env var
    `TALOS_DB_URL`. Se nessuno dei due è settato, solleva `RuntimeError`
    con istruzioni operative.

    Pool conservativo (5+10) per dialetti con `QueuePool` (Postgres):
    app Streamlit single-process, traffico interno; aggiustabile quando
    arriverà `ui/` multi-utente. SQLite usa `SingletonThreadPool` e non
    accetta `pool_size`/`max_overflow`: i parametri sono applicati solo
    quando il dialect li supporta.
    `pool_pre_ping=True` copre il caso di connessioni dormienti.
    """
    resolved = url or os.getenv("TALOS_DB_URL")
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
