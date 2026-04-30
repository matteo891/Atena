"""Test unit per `talos.extract.samsung` (CHG-2026-05-01-004, ADR-0017 + R-05).

Pattern: `SamsungExtractor()` con whitelist default (in repo);
test su titoli Samsung sintetici plausibili. Nessun network,
nessun binario.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from talos.extract import (
    DEFAULT_FIELD_WEIGHTS,
    MatchResult,
    MatchStatus,
    SamsungEntities,
    SamsungExtractor,
    load_whitelist,
)
from talos.extract.samsung import DEFAULT_WHITELIST_YAML

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# load_whitelist
# ---------------------------------------------------------------------------


def test_load_default_whitelist_parses() -> None:
    wl = load_whitelist(DEFAULT_WHITELIST_YAML)
    assert "Galaxy S24 Ultra" in wl.models_5g
    assert 256 in wl.rom_gb_canonical
    assert 12 in wl.ram_gb_canonical
    assert "Titanium Black" in wl.colors_canonical


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "samsung_whitelist.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_whitelist_missing_keys_raises(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, "models_5g:\n  - foo\n")  # mancano altre 3 chiavi
    with pytest.raises(ValueError, match="mancano chiavi"):
        load_whitelist(path)


def test_load_whitelist_not_mapping_raises(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, "- just\n- list\n")
    with pytest.raises(TypeError, match="mapping"):
        load_whitelist(path)


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


def test_extractor_default_construction() -> None:
    extractor = SamsungExtractor()
    assert "Galaxy S24" in extractor.whitelist_5g_models
    assert dict(extractor.field_weights) == DEFAULT_FIELD_WEIGHTS


def test_extractor_invalid_thresholds_raises() -> None:
    """sicuro <= ambiguo non e' permesso."""
    with pytest.raises(ValueError, match="thresholds"):
        SamsungExtractor(sicuro_threshold=0.5, ambiguo_threshold=0.7)


def test_extractor_invalid_color_threshold_raises() -> None:
    with pytest.raises(ValueError, match="color_fuzzy_threshold"):
        SamsungExtractor(color_fuzzy_threshold=150)


# ---------------------------------------------------------------------------
# parse_title — model
# ---------------------------------------------------------------------------


def test_parse_title_extracts_galaxy_s24() -> None:
    extractor = SamsungExtractor()
    e = extractor.parse_title("Samsung Galaxy S24 5G 256GB Titanium Black")
    assert e.model == "Galaxy S24"


def test_parse_title_longest_match_s24_ultra_over_s24() -> None:
    """`Galaxy S24 Ultra` deve vincere su `Galaxy S24` (longest-match)."""
    extractor = SamsungExtractor()
    e = extractor.parse_title("Samsung Galaxy S24 Ultra 5G 512GB 12GB")
    assert e.model == "Galaxy S24 Ultra"


def test_parse_title_unknown_model_returns_none() -> None:
    """Modello non in whitelist -> model=None (R-05 implicito a valle)."""
    extractor = SamsungExtractor()
    e = extractor.parse_title("Apple iPhone 15 Pro 256GB Black")
    assert e.model is None


# ---------------------------------------------------------------------------
# parse_title — RAM/ROM
# ---------------------------------------------------------------------------


def test_parse_title_extracts_ram() -> None:
    extractor = SamsungExtractor()
    e = extractor.parse_title("Galaxy S24 5G 256GB 12GB RAM Titanium Black")
    assert e.ram_gb == 12


def test_parse_title_extracts_rom() -> None:
    extractor = SamsungExtractor()
    e = extractor.parse_title("Galaxy S24 5G 256GB 12GB RAM Titanium Black")
    assert e.rom_gb == 256


def test_parse_title_inline_ram_rom_pattern() -> None:
    """Pattern '12+256' come variante compact RAM+ROM."""
    extractor = SamsungExtractor()
    e = extractor.parse_title("Galaxy S24 12+256 Titanium Black 5G")
    assert e.ram_gb == 12
    assert e.rom_gb == 256


def test_parse_title_ram_not_in_whitelist_returns_none() -> None:
    """RAM 999 non e' nella whitelist canonica -> None."""
    extractor = SamsungExtractor()
    e = extractor.parse_title("Galaxy S24 999GB RAM 256GB")
    assert e.ram_gb is None


# ---------------------------------------------------------------------------
# parse_title — color (rapidfuzz)
# ---------------------------------------------------------------------------


def test_parse_title_extracts_canonical_color() -> None:
    extractor = SamsungExtractor()
    e = extractor.parse_title("Galaxy S24 Ultra 5G 512GB 12GB Titanium Black")
    assert e.color == "Titanium Black"


def test_parse_title_color_fuzzy_match() -> None:
    """rapidfuzz partial_ratio: 'titanium blk' fuzzy-matches 'Titanium Black'."""
    extractor = SamsungExtractor(color_fuzzy_threshold=70)
    e = extractor.parse_title("Galaxy S24 5G 256GB Titanium Blk")
    # Match fuzzy plausibile; almeno verifichiamo che il colore "Titanium *" venga proposto.
    assert e.color is not None
    assert "Titanium" in e.color


def test_parse_title_no_color_match_returns_none() -> None:
    """Stringa senza colore canonico vicino -> None."""
    extractor = SamsungExtractor(color_fuzzy_threshold=95)
    e = extractor.parse_title("Galaxy S24 5G 256GB Random Random")
    assert e.color is None


# ---------------------------------------------------------------------------
# parse_title — connectivity / enterprise
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Galaxy S24 5G 256GB", "5G"),
        ("Galaxy A55 4G 256GB", "4G"),
        ("Galaxy S22 LTE 128GB", "4G"),
        ("Galaxy S24 256GB", None),
    ],
)
def test_parse_title_connectivity(text: str, expected: str | None) -> None:
    extractor = SamsungExtractor()
    assert extractor.parse_title(text).connectivity == expected


def test_parse_title_enterprise_flag() -> None:
    extractor = SamsungExtractor()
    e = extractor.parse_title("Galaxy S24 5G 256GB Titanium Black Enterprise Edition")
    assert e.enterprise is True


def test_parse_title_no_enterprise_flag() -> None:
    extractor = SamsungExtractor()
    e = extractor.parse_title("Galaxy S24 5G 256GB Titanium Black")
    assert e.enterprise is False


# ---------------------------------------------------------------------------
# match — confidence + status
# ---------------------------------------------------------------------------


def _full_entities(model: str = "Galaxy S24") -> SamsungEntities:
    return SamsungEntities(
        model=model,
        ram_gb=12,
        rom_gb=256,
        color="Titanium Black",
        connectivity="5G",
    )


def test_match_perfect_returns_sicuro() -> None:
    extractor = SamsungExtractor()
    sup = _full_entities()
    amz = _full_entities()
    result = extractor.match(supplier=sup, amazon=amz)
    assert result.status is MatchStatus.SICURO
    assert result.confidence == 1.0
    assert set(result.matched_fields) == {"model", "ram_gb", "rom_gb", "color", "connectivity"}


def test_match_partial_returns_ambiguo() -> None:
    """Match modello + RAM + ROM (3+2+2=7) / 9 = 0.78 -> AMBIGUO (0.50..0.85)."""
    extractor = SamsungExtractor()
    sup = _full_entities()
    amz = SamsungEntities(
        model="Galaxy S24",
        ram_gb=12,
        rom_gb=256,
        color=None,
        connectivity=None,
    )
    result = extractor.match(supplier=sup, amazon=amz)
    assert result.status is MatchStatus.AMBIGUO
    assert result.confidence == pytest.approx(7 / 9)


def test_match_only_color_match_returns_mismatch() -> None:
    """Solo color + connectivity match (1+1=2) / 9 = 0.22 -> MISMATCH (< 0.50)."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(
        model=None,
        ram_gb=None,
        rom_gb=None,
        color="Titanium Black",
        connectivity="5G",
    )
    amz = SamsungEntities(
        model=None,
        ram_gb=None,
        rom_gb=None,
        color="Titanium Black",
        connectivity="5G",
    )
    result = extractor.match(supplier=sup, amazon=amz)
    assert result.status is MatchStatus.MISMATCH
    assert result.confidence == pytest.approx(2 / 9)


def test_match_model_mismatch_hard_r05() -> None:
    """R-05 KILL-SWITCH: model differente -> MISMATCH a prescindere."""
    extractor = SamsungExtractor()
    sup = _full_entities(model="Galaxy S24")
    amz = _full_entities(model="Galaxy S23")  # tutti gli altri match
    result = extractor.match(supplier=sup, amazon=amz)
    assert result.status is MatchStatus.MISMATCH
    assert "model" in result.mismatched_fields


def test_match_model_one_side_missing_no_hard_mismatch() -> None:
    """Se il modello manca da una parte (None), R-05 hard NON scatta."""
    extractor = SamsungExtractor()
    sup = SamsungEntities(
        model="Galaxy S24", ram_gb=12, rom_gb=256, color="Titanium Black", connectivity="5G"
    )
    amz = SamsungEntities(
        model=None, ram_gb=12, rom_gb=256, color="Titanium Black", connectivity="5G"
    )
    result = extractor.match(supplier=sup, amazon=amz)
    # Score = 2+2+1+1 = 6; max=9; 6/9 = 0.67 -> AMBIGUO
    assert result.status is MatchStatus.AMBIGUO
    assert "model" not in result.mismatched_fields  # entrambi devono essere non-None per mismatch


def test_match_custom_weights_change_confidence() -> None:
    """Pesi custom: model=10 + altri=1 -> match modello dominante."""
    extractor = SamsungExtractor(
        field_weights={"model": 10, "ram_gb": 1, "rom_gb": 1, "color": 1, "connectivity": 1},
    )
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12, rom_gb=256, color=None, connectivity=None)
    amz = SamsungEntities(model="Galaxy S24", ram_gb=12, rom_gb=256, color=None, connectivity=None)
    result = extractor.match(supplier=sup, amazon=amz)
    # score = 10+1+1=12, max=14, 12/14 = 0.857 -> SICURO
    assert result.status is MatchStatus.SICURO


def test_match_result_is_frozen() -> None:
    result = MatchResult(
        status=MatchStatus.SICURO,
        confidence=1.0,
        matched_fields=[],
        mismatched_fields=[],
    )
    with pytest.raises(AttributeError):
        result.confidence = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integrazione parse_title -> match end-to-end
# ---------------------------------------------------------------------------


def test_end_to_end_supplier_amazon_match_realistic() -> None:
    """Scenario realistico: stesso prodotto formattato diversamente sui due lati.

    Nota: per scope minimal CHG-004, l'estrazione RAM richiede la
    keyword 'RAM' o il pattern inline '<n>+<m>'. Titoli Amazon che
    omettono 'RAM' producono ram_gb=None lato Amazon -> confidence
    ridotta. Il caller (orchestratore) dovrebbe normalizzare a
    monte oppure CHG futuro estende l'extractor con dispatch
    "smaller=RAM larger=ROM" sulle whitelist.
    """
    extractor = SamsungExtractor()
    supplier_title = "Samsung Galaxy S24 Ultra 5G 256GB 12GB RAM Titanium Black Enterprise"
    amazon_title = "Samsung Galaxy S24 Ultra 5G 256GB 12GB RAM Titanium Black"
    sup = extractor.parse_title(supplier_title)
    amz = extractor.parse_title(amazon_title)
    result = extractor.match(supplier=sup, amazon=amz)
    assert result.status is MatchStatus.SICURO


def test_end_to_end_supplier_amazon_model_mismatch_r05() -> None:
    """Fornitore S24 vs Amazon S23 -> MISMATCH (R-05 trigger)."""
    extractor = SamsungExtractor()
    sup = extractor.parse_title("Samsung Galaxy S24 5G 256GB Titanium Black")
    amz = extractor.parse_title("Samsung Galaxy S23 5G 256GB Titanium Black")
    result = extractor.match(supplier=sup, amazon=amz)
    assert result.status is MatchStatus.MISMATCH
