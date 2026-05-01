"""Integration test live `_LiveAmazonSerpAdapter` (CHG-2026-05-01-017).

Skip module-level se Chromium non installato (pattern coerente con
`test_live_playwright.py` CHG-012). Singolo test reale su Amazon.it
per ratificare la stabilita' dei selettori SERP
`[data-component-type="s-search-result"]` + estrazione asin/title/price.

NB: il test fa una richiesta reale ad Amazon.it (no quota Keepa
consumata, ma richiesta network). In CI lo skip module-level lo
disattiva. Nei test locali del Leader e' utile ratificare il layout
reale e catturare drift Amazon (lezione CHG-013: i mock non
rilevano discrepanze HTML).

ToS-friendly: 1 query per esecuzione, no batch; rispetta
delay range del scraper (CHG-002 D2.c).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from talos.io_.scraper import _PlaywrightBrowserPage
from talos.io_.serp_search import (
    SerpResult,
    _LiveAmazonSerpAdapter,
)

_CHROMIUM_CACHE = Path.home() / ".cache" / "ms-playwright"


def _chromium_runtime_libs_present() -> bool:
    """Replica del check in `test_live_playwright.py`: libnspr4 in ldconfig."""
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
        reason=(
            "Chromium binary or runtime libs not installed (skip live SERP). "
            "Run: `uv run playwright install chromium` + "
            "`sudo playwright install-deps chromium`."
        ),
    ),
]


def test_live_serp_galaxy_s24_returns_relevant_top1() -> None:
    """SERP live su 'Galaxy S24' -> top-1 ha titolo che menziona 'Galaxy'.

    Verifica empirica: i selettori `[data-component-type="s-search-result"]`
    sono ancora validi sul layout Amazon.it 2026, e l'estrazione asin/title
    funziona end-to-end. Tollerante: il top-1 esatto puo' variare nel
    tempo (ranking SERP dinamico), ma deve almeno menzionare 'galaxy'.
    """
    page = _PlaywrightBrowserPage()
    try:
        adapter = _LiveAmazonSerpAdapter(browser_factory=lambda: page)
        results = adapter.search("Galaxy S24", max_results=3)
    finally:
        page.close()

    assert len(results) >= 1, "SERP deve ritornare almeno 1 risultato per 'Galaxy S24'"
    top1 = results[0]
    assert isinstance(top1, SerpResult)
    assert top1.asin.startswith("B0"), f"ASIN Amazon.it dovrebbe iniziare con B0, got {top1.asin}"
    assert top1.position == 0
    assert "galaxy" in top1.title.lower(), (
        f"Top-1 SERP per 'Galaxy S24' dovrebbe menzionare 'Galaxy', got {top1.title!r}"
    )
    # Prezzo non sempre esposto (Buy Box pending, "Vedi le offerte" link),
    # ma se presente deve essere positivo.
    if top1.price_displayed is not None:
        assert top1.price_displayed > 0
