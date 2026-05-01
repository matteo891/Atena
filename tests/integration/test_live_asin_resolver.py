"""Integration test live `_LiveAsinResolver` (CHG-2026-05-01-018).

Skip module-level se Chromium o Keepa key assenti. Richiede entrambi:
- SERP scraping live via `_PlaywrightBrowserPage`
- `lookup_product` live via Keepa per verifica prezzo dei candidati

Quota stimata per esecuzione: ~1 SERP (Galaxy S24) + ~3 Keepa query
(top-3 candidati) = ~3 token Keepa.

Pattern coerente con `test_live_serp.py` (CHG-017) e
`test_live_keepa.py` (CHG-015).
"""

from __future__ import annotations

import shutil
import subprocess
from decimal import Decimal
from functools import partial
from pathlib import Path

import pytest

from talos.config.settings import TalosSettings
from talos.extract.asin_resolver import _LiveAsinResolver
from talos.io_.fallback_chain import lookup_product
from talos.io_.keepa_client import KeepaClient
from talos.io_.scraper import _PlaywrightBrowserPage
from talos.io_.serp_search import _LiveAmazonSerpAdapter

_CHROMIUM_CACHE = Path.home() / ".cache" / "ms-playwright"
_settings = TalosSettings()


def _chromium_runtime_libs_present() -> bool:
    """Verifica `libnspr4` in `ldconfig -p` (pattern CHG-012)."""
    ldconfig = shutil.which("ldconfig")
    if ldconfig is None:
        return False
    try:
        result = subprocess.run(  # noqa: S603 — path & args statici
            [ldconfig, "-p"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return "libnspr4" in result.stdout


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _CHROMIUM_CACHE.exists() or not _chromium_runtime_libs_present(),
        reason="Chromium binary or runtime libs not installed (skip live SERP).",
    ),
    pytest.mark.skipif(
        _settings.keepa_api_key is None,
        reason="TALOS_KEEPA_API_KEY non impostata; skip live lookup verification.",
    ),
]


def test_live_resolve_galaxy_s24_returns_plausible_top1() -> None:
    """Risolvi "Samsung Galaxy S24 256GB Onyx" con prezzo €549 -> top-1 plausibile.

    Fuzzy elevato su titolo + delta prezzo basso -> confidence > 50.
    Il selected.asin deve iniziare con B0 (formato Amazon).

    Costo quota: 1 SERP + 3 Keepa = ~3 token Keepa.
    """
    api_key = _settings.keepa_api_key
    assert api_key is not None  # narrow per mypy (verificato dal pytestmark)

    keepa_client = KeepaClient(api_key=api_key, rate_limit_per_minute=20)
    page = _PlaywrightBrowserPage()

    try:
        serp_adapter = _LiveAmazonSerpAdapter(browser_factory=lambda: page)
        # Lookup leggero: solo Keepa (nessun scraper/page/ocr per non sovraccaricare
        # la verifica prezzo per N candidati).
        lookup_callable = partial(
            lookup_product,
            keepa=keepa_client,
            scraper=None,
            page=None,
            ocr=None,
        )
        resolver = _LiveAsinResolver(
            serp_adapter=serp_adapter,
            lookup_callable=lookup_callable,
            max_candidates=3,
        )
        result = resolver.resolve_description(
            "Samsung Galaxy S24 256GB Onyx Black",
            Decimal("549.00"),
        )
    finally:
        page.close()

    # SERP non vuoto
    assert len(result.candidates) >= 1, "SERP deve ritornare almeno 1 candidato"
    assert result.selected is not None
    assert result.selected.asin.startswith("B0"), (
        f"ASIN Amazon dovrebbe iniziare con B0, got {result.selected.asin}"
    )
    # Il top-1 plausibile per "Galaxy S24 256GB" deve avere fuzzy > 30
    # (contiene almeno qualche token comune con il titolo Amazon)
    assert result.selected.fuzzy_title_pct > 30, (
        f"Fuzzy basso per top-1: {result.selected.fuzzy_title_pct} su titolo "
        f"{result.selected.title!r}"
    )
    # Confidence > 50 = match almeno discreto (non eccezionale, ma plausibile)
    assert result.selected.confidence_pct > 50, (
        f"Confidence bassa per match Galaxy S24: {result.selected.confidence_pct} - "
        f"selected={result.selected.asin}, title={result.selected.title!r}, "
        f"buybox={result.selected.buybox_eur}, delta={result.selected.delta_price_pct}"
    )
