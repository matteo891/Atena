"""Smoke test tab strip + action buttons shell (CHG-2026-05-02-026)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_render_action_buttons_shell_imports() -> None:
    """Smoke: l'helper esiste ed è importabile."""
    from talos.ui.dashboard import _render_action_buttons_shell  # noqa: PLC0415

    assert callable(_render_action_buttons_shell)


def test_render_tabs_section_imports() -> None:
    """Smoke: l'helper esiste ed è importabile (signature kw-only)."""
    from talos.ui.dashboard import _render_tabs_section  # noqa: PLC0415

    assert callable(_render_tabs_section)


def test_render_tabs_section_has_keyword_only_signature() -> None:
    """`_render_tabs_section` deve accettare cart_items e panchina_df keyword-only.

    Sentinel: protegge da regressione signature post-CHG-027 cart enriched.
    """
    import inspect  # noqa: PLC0415

    from talos.ui.dashboard import _render_tabs_section  # noqa: PLC0415

    sig = inspect.signature(_render_tabs_section)
    params = sig.parameters
    assert "cart_items" in params
    assert "panchina_df" in params
    assert params["cart_items"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["panchina_df"].kind == inspect.Parameter.KEYWORD_ONLY
