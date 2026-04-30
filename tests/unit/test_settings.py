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
