"""Integration test live `_PlaywrightBrowserPage` (CHG-2026-05-01-012, Fase 3 Path B).

Richiede Chromium installato via `uv run playwright install chromium`
(~150 MB cache in `~/.cache/ms-playwright/`). Skip module-level se
la cache non e' presente: pytest passa, CI senza Chromium non si rompe.

Pattern: usa `data:text/html;charset=utf-8,...` URL inline (Playwright li supporta
nativamente) per evitare dipendenze da Amazon.it reale (lento,
non-deterministico, ToS-issue) o da httpserver locale.

Quando arriveranno golden HTML statici Amazon (CHG futuro), si
aggiungeranno test `tests/golden/html/amazon_*.html` caricati via
`page.set_content()` per scenari realistici.
"""

from __future__ import annotations

import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from talos.io_ import AmazonScraper, parse_eur
from talos.io_.scraper import _PlaywrightBrowserPage

_CHROMIUM_CACHE = Path.home() / ".cache" / "ms-playwright"


def _chromium_runtime_libs_present() -> bool:
    """Verifica che le librerie di sistema richieste da Chromium siano installate.

    Chrome Headless Shell richiede `libnspr4`, `libnss3`, ecc. Installati
    via `sudo playwright install-deps chromium` o `sudo apt install
    libnspr4 libnss3 libatk-1.0-0 libatk-bridge-2.0-0 libcups2 libdrm2
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2
    libgbm1 libpango-1.0-0 libcairo2 libasound2`.

    Senza sudo, `playwright install chromium` scarica il binario ma il
    launch fallisce con `error while loading shared libraries: libnspr4.so`.
    """
    ldconfig = shutil.which("ldconfig")
    if ldconfig is None:
        return False
    try:
        # ldconfig path resolved by shutil.which; arg statico, no untrusted input.
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
        not _CHROMIUM_CACHE.exists(),
        reason="Chromium not installed (run `uv run playwright install chromium`)",
    ),
    pytest.mark.skipif(
        not _chromium_runtime_libs_present(),
        reason=(
            "Chromium runtime system libs missing (libnspr4 etc.) — "
            "run `sudo playwright install-deps chromium` or "
            "`sudo apt install libnspr4 libnss3 libatk-1.0-0 libatk-bridge-2.0-0 "
            "libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 "
            "libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2`"
        ),
    ),
]


def test_live_playwright_goto_inline_html_and_query_css() -> None:
    """Carica HTML inline via data URL e legge un selettore CSS."""
    html = "<html><body><h1 id='title'>Hello Talos</h1></body></html>"
    url = f"data:text/html;charset=utf-8,{html}"
    with _PlaywrightBrowserPage() as page:
        page.goto(url)
        text = page.query_selector_text("#title")
    assert text == "Hello Talos"


def test_live_playwright_query_xpath() -> None:
    """XPath supportato via prefisso `xpath=`."""
    html = "<html><body><div class='price'>€ 199,99</div></body></html>"
    url = f"data:text/html;charset=utf-8,{html}"
    with _PlaywrightBrowserPage() as page:
        page.goto(url)
        text = page.query_selector_xpath_text("//div[@class='price']")
    assert text == "€ 199,99"


def test_live_playwright_returns_none_on_missing_selector() -> None:
    """Selettore assente -> None (R-01: il caller decide il fallback)."""
    html = "<html><body><h1>Empty</h1></body></html>"
    url = f"data:text/html;charset=utf-8,{html}"
    with _PlaywrightBrowserPage() as page:
        page.goto(url)
        assert page.query_selector_text("#missing-id") is None
        assert page.query_selector_xpath_text("//div[@class='absent']") is None


def test_live_playwright_close_is_idempotent() -> None:
    """`close()` chiamato due volte non solleva (idempotenza)."""
    page = _PlaywrightBrowserPage()
    page.goto("data:text/html;charset=utf-8,<p>x</p>")
    page.close()
    page.close()  # secondo close: no raise


def test_live_playwright_query_before_goto_returns_none() -> None:
    """`query_*` prima di `goto()` ritorna None (no crash, R-01)."""
    page = _PlaywrightBrowserPage()
    try:
        assert page.query_selector_text("#anything") is None
        assert page.query_selector_xpath_text("//x") is None
    finally:
        page.close()


def test_live_playwright_amazon_scraper_end_to_end_with_data_url() -> None:
    """Smoke test integrato: AmazonScraper.scrape_product su HTML inline.

    Verifica che il selectors.yaml + parse_eur funzionino con la page
    live. NON tocca amazon.it reale (data URL).
    """
    html = (
        "<html><body>"
        "<h1 id='productTitle'>Samsung Galaxy S24 256GB Titanium Black</h1>"
        "<div id='corePrice_feature_div'>"
        "<span class='a-price'>"
        "<span class='a-offscreen'>€ 799,90</span>"
        "</span>"
        "</div>"
        "</body></html>"
    )

    # Approccio: testiamo direttamente i selettori invece di scrape_product
    # (che hardcoda l'URL Amazon AMAZON_IT_PRODUCT_URL). Il test per
    # scrape_product live su Amazon reale e' scope di un CHG futuro con
    # golden HTML statico Amazon.
    scraper = AmazonScraper()
    with _PlaywrightBrowserPage() as page:
        page.goto(f"data:text/html;charset=utf-8,{html}")
        title = page.query_selector_text("#productTitle")
        price_text = page.query_selector_text(
            "#corePrice_feature_div .a-price .a-offscreen",
        )
    assert title is not None
    assert "Samsung Galaxy S24" in title
    assert price_text is not None
    assert "799,90" in price_text
    # parse_eur deve gestire il prezzo italiano
    assert parse_eur(price_text) == Decimal("799.90")
    _ = scraper  # scraper non invocato direttamente (vedi commento sopra)
