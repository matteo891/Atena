"""Test unit per `talos.config.settings` (CHG-2026-04-30-029, ADR-0014).

Pattern: monkeypatch.setenv + get_settings.cache_clear() prima di
ogni test che si aspetta valori non-default. Senza cache_clear, la
prima istanza vince e i test successivi vedono lo stato vecchio.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from talos.config import TalosSettings, get_settings
from talos.vgp import DEFAULT_ROI_VETO_THRESHOLD

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Resetta il singleton funzionale prima di ogni test."""
    get_settings.cache_clear()


def test_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza env var TALOS_*, i campi prendono i default."""
    monkeypatch.delenv("TALOS_DB_URL", raising=False)
    monkeypatch.delenv("TALOS_ROI_VETO_THRESHOLD", raising=False)
    settings = TalosSettings()
    assert settings.db_url is None
    assert settings.roi_veto_threshold == DEFAULT_ROI_VETO_THRESHOLD == 0.08


def test_db_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`TALOS_DB_URL` letta come stringa."""
    monkeypatch.setenv("TALOS_DB_URL", "postgresql+psycopg://user:pass@h/d")
    settings = TalosSettings()
    assert settings.db_url == "postgresql+psycopg://user:pass@h/d"


def test_roi_threshold_override_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`TALOS_ROI_VETO_THRESHOLD=0.10` -> soglia override 10%."""
    monkeypatch.setenv("TALOS_ROI_VETO_THRESHOLD", "0.10")
    settings = TalosSettings()
    assert settings.roi_veto_threshold == 0.10


def test_get_settings_returns_cached_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Due call a `get_settings()` ritornano la stessa istanza (singleton)."""
    monkeypatch.delenv("TALOS_DB_URL", raising=False)
    a = get_settings()
    b = get_settings()
    assert a is b


def test_threshold_zero_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validator: threshold=0 e' esterno a (0, 1] -> ValidationError."""
    monkeypatch.setenv("TALOS_ROI_VETO_THRESHOLD", "0")
    with pytest.raises(ValidationError, match="roi_veto_threshold"):
        TalosSettings()


def test_threshold_negative_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validator: threshold negativo -> ValidationError."""
    monkeypatch.setenv("TALOS_ROI_VETO_THRESHOLD", "-0.05")
    with pytest.raises(ValidationError, match="roi_veto_threshold"):
        TalosSettings()


def test_extra_kwarg_at_construction_rejected() -> None:
    """`extra='forbid'`: kwarg Python sconosciuto -> ValidationError.

    Nota: pydantic-settings IGNORA le env var con prefisso TALOS_ che
    non corrispondono a campi noti (non solleva errore). `extra='forbid'`
    si applica solo ai kwarg passati al costruttore Python.
    """
    with pytest.raises(ValidationError, match="typo_field"):
        TalosSettings(typo_field="noise")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Campi DB bootstrap (CHG-2026-04-30-031)
# ---------------------------------------------------------------------------


def test_db_url_superuser_default_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza env var, `db_url_superuser` e' None."""
    monkeypatch.delenv("TALOS_DB_URL_SUPERUSER", raising=False)
    settings = TalosSettings()
    assert settings.db_url_superuser is None


def test_db_url_superuser_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`TALOS_DB_URL_SUPERUSER` letta come stringa."""
    monkeypatch.setenv("TALOS_DB_URL_SUPERUSER", "postgresql://postgres:x@h:5432/postgres")
    settings = TalosSettings()
    assert settings.db_url_superuser == "postgresql://postgres:x@h:5432/postgres"


def test_passwords_default_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza env var, le 3 password ruoli sono None."""
    for var in ("TALOS_ADMIN_PASSWORD", "TALOS_APP_PASSWORD", "TALOS_AUDIT_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    settings = TalosSettings()
    assert settings.admin_password is None
    assert settings.app_password is None
    assert settings.audit_password is None


def test_passwords_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le 3 env var TALOS_*_PASSWORD popolano i campi."""
    admin_value = "admin_pwd_x"
    app_value = "app_pwd_y"
    audit_value = "audit_pwd_z"
    monkeypatch.setenv("TALOS_ADMIN_PASSWORD", admin_value)
    monkeypatch.setenv("TALOS_APP_PASSWORD", app_value)
    monkeypatch.setenv("TALOS_AUDIT_PASSWORD", audit_value)
    settings = TalosSettings()
    assert settings.admin_password == admin_value
    assert settings.app_password == app_value
    assert settings.audit_password == audit_value


def test_db_url_superuser_independent_from_db_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`db_url_superuser` e `db_url` sono campi distinti, indipendenti."""
    monkeypatch.delenv("TALOS_DB_URL", raising=False)
    monkeypatch.setenv("TALOS_DB_URL_SUPERUSER", "postgresql://postgres:x@h/p")
    settings = TalosSettings()
    assert settings.db_url is None
    assert settings.db_url_superuser == "postgresql://postgres:x@h/p"


# ---------------------------------------------------------------------------
# Campi Keepa (CHG-2026-05-01-001)
# ---------------------------------------------------------------------------


def test_keepa_api_key_default_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza env var, `keepa_api_key` e' None (test/CI senza chiave)."""
    monkeypatch.delenv("TALOS_KEEPA_API_KEY", raising=False)
    settings = TalosSettings()
    assert settings.keepa_api_key is None


def test_keepa_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`TALOS_KEEPA_API_KEY` letta come stringa."""
    monkeypatch.setenv("TALOS_KEEPA_API_KEY", "abc123secret")
    settings = TalosSettings()
    assert settings.keepa_api_key == "abc123secret"


def test_keepa_rate_limit_default_60(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza env var, `keepa_rate_limit_per_minute=60` (esempio ADR-0017)."""
    monkeypatch.delenv("TALOS_KEEPA_RATE_LIMIT_PER_MINUTE", raising=False)
    settings = TalosSettings()
    assert settings.keepa_rate_limit_per_minute == 60


def test_keepa_rate_limit_override_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`TALOS_KEEPA_RATE_LIMIT_PER_MINUTE=30` -> rate limit 30/min."""
    monkeypatch.setenv("TALOS_KEEPA_RATE_LIMIT_PER_MINUTE", "30")
    settings = TalosSettings()
    assert settings.keepa_rate_limit_per_minute == 30


def test_keepa_rate_limit_zero_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validator: rate_limit=0 -> ValidationError."""
    monkeypatch.setenv("TALOS_KEEPA_RATE_LIMIT_PER_MINUTE", "0")
    with pytest.raises(ValidationError, match="keepa_rate_limit_per_minute"):
        TalosSettings()


def test_keepa_rate_limit_negative_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validator: rate_limit negativo -> ValidationError."""
    monkeypatch.setenv("TALOS_KEEPA_RATE_LIMIT_PER_MINUTE", "-5")
    with pytest.raises(ValidationError, match="keepa_rate_limit_per_minute"):
        TalosSettings()


# ---------------------------------------------------------------------------
# Campi OCR Tesseract (CHG-2026-05-01-003)
# ---------------------------------------------------------------------------


def test_ocr_threshold_default_70(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza env var, `ocr_confidence_threshold=70` (verbatim ADR-0017)."""
    monkeypatch.delenv("TALOS_OCR_CONFIDENCE_THRESHOLD", raising=False)
    settings = TalosSettings()
    assert settings.ocr_confidence_threshold == 70


def test_ocr_threshold_override_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`TALOS_OCR_CONFIDENCE_THRESHOLD=80` -> soglia override 80."""
    monkeypatch.setenv("TALOS_OCR_CONFIDENCE_THRESHOLD", "80")
    settings = TalosSettings()
    assert settings.ocr_confidence_threshold == 80


@pytest.mark.parametrize("boundary", [0, 100])
def test_ocr_threshold_boundaries_accepted(
    monkeypatch: pytest.MonkeyPatch,
    boundary: int,
) -> None:
    """Validator: 0 e 100 sono i confini inclusivi della scala Tesseract."""
    monkeypatch.setenv("TALOS_OCR_CONFIDENCE_THRESHOLD", str(boundary))
    settings = TalosSettings()
    assert settings.ocr_confidence_threshold == boundary


def test_ocr_threshold_negative_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validator: soglia negativa -> ValidationError."""
    monkeypatch.setenv("TALOS_OCR_CONFIDENCE_THRESHOLD", "-1")
    with pytest.raises(ValidationError, match="ocr_confidence_threshold"):
        TalosSettings()


def test_ocr_threshold_above_100_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validator: soglia > 100 fuori scala Tesseract -> ValidationError."""
    monkeypatch.setenv("TALOS_OCR_CONFIDENCE_THRESHOLD", "101")
    with pytest.raises(ValidationError, match="ocr_confidence_threshold"):
        TalosSettings()
