"""Smoke test — il package è importabile (ADR-0013 src-layout)."""

import pytest

import talos


@pytest.mark.unit
def test_talos_importable() -> None:
    assert talos.__name__ == "talos"


@pytest.mark.unit
def test_talos_version_exposed() -> None:
    assert isinstance(talos.__version__, str)
    assert talos.__version__ == "0.1.0"
