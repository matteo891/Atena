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
        # `.env` locale (gitignored) per ergonomia sviluppo locale: pydantic-settings
        # carica le var da .env nel cwd al boot. Le env var dirette dalla shell/CI
        # hanno PRECEDENZA su .env (pattern standard pydantic-settings) — la CI
        # continua a iniettare secrets via env senza file.
        env_file=".env",
        env_file_encoding="utf-8",
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
    keepa_api_key: str | None = Field(
        default=None,
        description=(
            "API key Keepa (env: TALOS_KEEPA_API_KEY). Opzionale: "
            "module-import non deve fallire in test/CI senza chiave. "
            "Errore esplicito al call site di KeepaClient.fetch_*. "
            "ADR-0017."
        ),
    )
    keepa_rate_limit_per_minute: int = Field(
        default=60,
        description=(
            "Limite hard di richieste Keepa per minuto "
            "(env: TALOS_KEEPA_RATE_LIMIT_PER_MINUTE). Default 60 "
            "(esempio ADR-0017). Eccedere il limite -> errore "
            "esplicito (R-01 NO SILENT DROPS), non silenziamento."
        ),
    )
    ocr_confidence_threshold: int = Field(
        default=70,
        description=(
            "Soglia di confidenza Tesseract OCR (0-100, "
            "env: TALOS_OCR_CONFIDENCE_THRESHOLD). Default 70 "
            "(verbatim ADR-0017). Sotto soglia -> status AMBIGUO "
            "(R-01 NO SILENT DROPS), riga listino marcata e "
            "mostrata al CFO per validazione manuale. Override "
            "runtime possibile via `config_overrides` "
            "(key 'ocr_confidence_threshold')."
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

    @field_validator("keepa_rate_limit_per_minute")
    @classmethod
    def _check_keepa_rate_limit(cls, v: int) -> int:
        """Rate limit positivo intero. Zero/negativo non ha senso operativo."""
        if v <= 0:
            msg = (
                f"keepa_rate_limit_per_minute invalido: {v}. "
                "Deve essere intero positivo (richieste/minuto)."
            )
            raise ValueError(msg)
        return v

    @field_validator("ocr_confidence_threshold")
    @classmethod
    def _check_ocr_threshold(cls, v: int) -> int:
        """Soglia confidence Tesseract: intero in [0, 100]."""
        if not 0 <= v <= 100:  # noqa: PLR2004 — intervallo Tesseract verbatim
            msg = (
                f"ocr_confidence_threshold invalido: {v}. "
                "Deve essere intero in [0, 100] (scala Tesseract)."
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
