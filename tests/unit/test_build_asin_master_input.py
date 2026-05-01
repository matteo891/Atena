"""Test unit per `build_asin_master_input` (CHG-2026-05-01-008, ADR-0017 + ADR-0015).

Bridge `ProductData` (output `lookup_product`) -> `AsinMasterInput`
(input `upsert_asin_master`). Test puri, no DB.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from talos.extract import (
    AsinMasterInput,
    SamsungEntities,
    build_asin_master_input,
)
from talos.io_ import ProductData

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _product(
    *,
    asin: str = "B0BRIDGE01",
    title: str | None = "Samsung Galaxy S24 Titanium Black",
    buybox_eur: Decimal | None = Decimal("799.00"),
) -> ProductData:
    return ProductData(
        asin=asin,
        buybox_eur=buybox_eur,
        bsr=42,
        fee_fba_eur=Decimal("3.50"),
        title=title,
    )


def _samsung_entities() -> SamsungEntities:
    return SamsungEntities(
        model="Galaxy S24",
        ram_gb=12,
        rom_gb=256,
        color="Titanium Black",
        connectivity="5G",
        enterprise=False,
    )


# ---------------------------------------------------------------------------
# Mapping core
# ---------------------------------------------------------------------------


def test_build_uses_product_title_when_present() -> None:
    inp = build_asin_master_input(_product(), brand="Samsung")
    assert isinstance(inp, AsinMasterInput)
    assert inp.asin == "B0BRIDGE01"
    assert inp.title == "Samsung Galaxy S24 Titanium Black"
    assert inp.brand == "Samsung"
    assert inp.enterprise is False
    # samsung_entities=None -> tutti i campi nullable a None
    assert inp.model is None
    assert inp.ram_gb is None
    assert inp.rom_gb is None
    assert inp.connectivity is None
    assert inp.color_family is None
    assert inp.category_node is None


def test_build_with_samsung_entities_populates_nullable_fields() -> None:
    inp = build_asin_master_input(
        _product(),
        brand="Samsung",
        samsung_entities=_samsung_entities(),
    )
    assert inp.model == "Galaxy S24"
    assert inp.ram_gb == 12
    assert inp.rom_gb == 256
    assert inp.connectivity == "5G"
    assert inp.color_family == "Titanium Black"


def test_build_enterprise_param_wins_over_samsung_entities() -> None:
    """`enterprise` param prevale: samsung_entities.enterprise non viene letto."""
    ents = SamsungEntities(model="Galaxy S24", enterprise=False)
    inp = build_asin_master_input(
        _product(),
        brand="Samsung",
        enterprise=True,
        samsung_entities=ents,
    )
    assert inp.enterprise is True


def test_build_category_node_passes_through() -> None:
    inp = build_asin_master_input(
        _product(),
        brand="Samsung",
        category_node="electronics/smartphones",
    )
    assert inp.category_node == "electronics/smartphones"


# ---------------------------------------------------------------------------
# Title fallback (R-01 NO SILENT DROPS)
# ---------------------------------------------------------------------------


def test_build_uses_title_fallback_when_product_title_is_none() -> None:
    pd = _product(title=None)
    inp = build_asin_master_input(
        pd,
        brand="Samsung",
        title_fallback="Listino fornitore Samsung",
    )
    assert inp.title == "Listino fornitore Samsung"


def test_build_raises_when_both_titles_are_none() -> None:
    pd = _product(title=None)
    with pytest.raises(ValueError, match="title is None"):
        build_asin_master_input(pd, brand="Samsung")


def test_build_product_title_takes_precedence_over_fallback() -> None:
    """Se entrambi forniti, vince `product_data.title` (canale acquisizione)."""
    pd = _product(title="From Amazon Scrape")
    inp = build_asin_master_input(
        pd,
        brand="Samsung",
        title_fallback="From Listino",
    )
    assert inp.title == "From Amazon Scrape"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_build_partial_samsung_entities_leaves_rest_none() -> None:
    """Solo `model` popolato in samsung_entities -> ram/rom/connectivity/color None."""
    ents = SamsungEntities(model="Galaxy S24")
    inp = build_asin_master_input(
        _product(),
        brand="Samsung",
        samsung_entities=ents,
    )
    assert inp.model == "Galaxy S24"
    assert inp.ram_gb is None
    assert inp.rom_gb is None
    assert inp.connectivity is None
    assert inp.color_family is None
