"""Test unit Anagrafica + Esporta ORDINE+STRATEGIA (CHG-2026-05-02-028)."""

from __future__ import annotations

import pytest

from talos.ui.dashboard import (
    _build_ordine_strategia_csv,
    _render_anagrafica_modal,
    _render_export_ordine_strategia,
    fetch_asin_masters_or_empty,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# `_build_ordine_strategia_csv`
# ---------------------------------------------------------------------------


def test_build_ordine_strategia_csv_empty_cart_emits_only_header_metadata() -> None:
    """Cart vuoto: CSV contiene solo righe `# key=value` di metadata, nessun row."""
    csv_bytes = _build_ordine_strategia_csv(
        [],
        budget=10000.0,
        velocity_target_days=15,
        veto_threshold=0.08,
        saturation=0.0,
        cycle_kpis={
            "cash_profit_eur": 0.0,
            "projected_annual_eur": 10000.0,
            "cycles_per_year": 24.33,
        },
    )
    text = csv_bytes.decode("utf-8")
    assert "# budget_eur=10000.00" in text
    assert "# velocity_target_days=15" in text
    assert "# veto_roi_threshold=0.0800" in text
    assert "# cycles_per_year=24.33" in text
    # Nessun header CSV cart (cart vuoto).
    assert "asin," not in text


def test_build_ordine_strategia_csv_with_cart_includes_metadata_and_rows() -> None:
    """Cart con items: CSV ha metadata header + cart_df 13-col."""
    cart_items = [
        {
            "asin": "B0AAA",
            "hw_id": "—",
            "prodotto": "—",
            "fornitore": "—",
            "cst_unit": 100.0,
            "prft_unit": 130.0,
            "vgp": 0.7,
            "mrg": "—",
            "roi": 0.30,
            "vel": "Veloce",
            "q_15gg": 7,
            "stock": "—",
            "qta": 5,
            "prft_total": 150.0,
            "spesa_total": 500.0,
            "a_m": "—",
            "azioni": "ALLOCATED",
        },
    ]
    csv_bytes = _build_ordine_strategia_csv(
        cart_items,
        budget=5000.0,
        velocity_target_days=15,
        veto_threshold=0.08,
        saturation=0.10,
        cycle_kpis={
            "cash_profit_eur": 150.0,
            "projected_annual_eur": 12500.0,
            "cycles_per_year": 24.33,
        },
    )
    text = csv_bytes.decode("utf-8")
    assert "# budget_eur=5000.00" in text
    assert "# cash_profit_eur=150.00" in text
    assert "B0AAA" in text
    assert "ALLOCATED" in text


def test_build_ordine_strategia_csv_metadata_header_first() -> None:
    """Metadata `# ...` lines DEVONO precedere il cart header (audit trail leggibile)."""
    csv_bytes = _build_ordine_strategia_csv(
        [
            {
                "asin": "B0AAA",
                "qta": 1,
                "vgp": 0.5,
                "cst_unit": 100.0,
                "prft_unit": 110.0,
                "roi": 0.10,
                "vel": "Lento",
                "q_15gg": 1,
                "prft_total": 10.0,
                "spesa_total": 100.0,
                "azioni": "ALLOCATED",
                "hw_id": "—",
                "prodotto": "—",
                "fornitore": "—",
                "mrg": "—",
                "stock": "—",
                "a_m": "—",
            },
        ],
        budget=1000.0,
        velocity_target_days=30,
        veto_threshold=0.08,
        saturation=0.10,
        cycle_kpis={
            "cash_profit_eur": 10.0,
            "projected_annual_eur": 1100.0,
            "cycles_per_year": 12.17,
        },
    )
    text = csv_bytes.decode("utf-8")
    lines = text.split("\n")
    # Prime righe devono essere `# key=value` (metadata).
    metadata_line_count = sum(1 for line in lines if line.startswith("#"))
    assert metadata_line_count >= 5, "almeno 5 righe metadata attese"
    # La prima riga deve essere metadata.
    assert lines[0].startswith("# generated=")


# ---------------------------------------------------------------------------
# `fetch_asin_masters_or_empty`
# ---------------------------------------------------------------------------


def test_fetch_asin_masters_or_empty_none_factory() -> None:
    """Factory=None → list vuota (graceful pattern)."""
    out = fetch_asin_masters_or_empty(None, ["B0AAA", "B0BBB"])
    assert out == []


def test_fetch_asin_masters_or_empty_empty_asins() -> None:
    """Lista ASIN vuota → list vuota (no DB query inutile)."""
    # factory non-None ma asins vuoti: short-circuit prima della query.
    out = fetch_asin_masters_or_empty(object(), [])  # type: ignore[arg-type]
    assert out == []


# ---------------------------------------------------------------------------
# Smoke import
# ---------------------------------------------------------------------------


def test_render_helpers_importable() -> None:
    """Smoke: tutti gli helper sono importabili e callable."""
    assert callable(_render_anagrafica_modal)
    assert callable(_render_export_ordine_strategia)
    assert callable(_build_ordine_strategia_csv)
    assert callable(fetch_asin_masters_or_empty)
