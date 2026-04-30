"""Config layer Talos (ADR-0013, ADR-0014).

Centralizza env var TALOS_* via `pydantic-settings`. Inaugurato in
CHG-2026-04-30-029 con due campi: `db_url` (alias TALOS_DB_URL) e
`roi_veto_threshold` (override-abile via TALOS_ROI_VETO_THRESHOLD,
default 0.08 = R-08 verbatim).

Pattern di accesso: `from talos.config import get_settings; s = get_settings()`.
La factory `get_settings` e' un singleton funzionale (lru_cache). Per
test che vogliono override esplicito: `get_settings.cache_clear()` +
`monkeypatch.setenv(...)`.
"""

from talos.config.settings import TalosSettings, get_settings

__all__ = ["TalosSettings", "get_settings"]
