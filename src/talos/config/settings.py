"""TalosSettings - config layer pydantic-settings (CHG-2026-04-30-029).

Convenzione env var: prefisso `TALOS_`, case-insensitive. Le env var
non riconosciute -> ValidationError esplicito (extra='forbid'),
protegge da typo (es. TALOS_RIO_THRESHOLD vs TALOS_ROI_VETO_THRESHOLD).

Sorgente di verita' della soglia R-08: la costante
`DEFAULT_ROI_VETO_THRESHOLD` in `talos.vgp.veto` (verbatim PROJECT-RAW
riga 226). Settings ne e' override-abile via env var
`TALOS_ROI_VETO_THRESHOLD`. Quando settings diverge dalla costante
(via env), il valore runtime e' quello di settings (configurabilita'
L10 chiusa Round 5).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from talos.vgp import DEFAULT_ROI_VETO_THRESHOLD


class TalosSettings(BaseSettings):
    """Config tipata centralizzata. Legge env var con prefisso `TALOS_`."""

    model_config = SettingsConfigDict(
        env_prefix="TALOS_",
        env_file=None,  # nessun .env in repo: env da shell/CI/secrets
        extra="forbid",
        case_sensitive=False,
    )

    db_url: str | None = Field(
        default=None,
        description=(
            "URL connessione PostgreSQL pool app (env: TALOS_DB_URL). "
            "Opzionale: module-import non deve fallire in test/CI senza DB. "
            "Errore esplicito al call site quando serve davvero."
        ),
    )
    roi_veto_threshold: float = Field(
        default=DEFAULT_ROI_VETO_THRESHOLD,
        description=(
            "Soglia Veto ROI R-08 come frazione decimale "
            "(env: TALOS_ROI_VETO_THRESHOLD). Default 0.08 (verbatim). "
            "Override per L10 chiusa Round 5 (configurabilita' soglia)."
        ),
    )
    db_url_superuser: str | None = Field(
        default=None,
        description=(
            "URL connessione superuser per bootstrap ruoli/RLS "
            "(env: TALOS_DB_URL_SUPERUSER). Usata da scripts/db_bootstrap.py; "
            "fallback su db_url se assente. Opzionale: errore al call site."
        ),
    )
    admin_password: str | None = Field(
        default=None,
        description=(
            "Password ruolo talos_admin (env: TALOS_ADMIN_PASSWORD). "
            "Richiesta da scripts/db_bootstrap.py."
        ),
    )
    app_password: str | None = Field(
        default=None,
        description=(
            "Password ruolo talos_app (env: TALOS_APP_PASSWORD). "
            "Richiesta da scripts/db_bootstrap.py."
        ),
    )
    audit_password: str | None = Field(
        default=None,
        description=(
            "Password ruolo talos_audit (env: TALOS_AUDIT_PASSWORD). "
            "Richiesta da scripts/db_bootstrap.py."
        ),
    )

    @field_validator("roi_veto_threshold")
    @classmethod
    def _check_threshold_range(cls, v: float) -> float:
        """Stesso vincolo di `is_vetoed_by_roi`: (0, 1] strict zero esclusivo."""
        if not 0 < v <= 1:
            msg = (
                f"roi_veto_threshold invalido: {v}. "
                "Deve essere in (0, 1] (frazione decimale, default 0.08)."
            )
            raise ValueError(msg)
        return v


@lru_cache(maxsize=1)
def get_settings() -> TalosSettings:
    """Factory singleton funzionale.

    Ogni call ritorna la stessa istanza; il primo call legge l'env.
    Per test con override esplicito: `get_settings.cache_clear()` +
    `monkeypatch.setenv(...)` prima del re-call.
    """
    return TalosSettings()
