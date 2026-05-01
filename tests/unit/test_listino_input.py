"""Test unit `talos.ui.listino_input` (CHG-2026-05-01-020).

Helper puri SENZA dipendenza Streamlit. Mock factory + resolver
duck-typed.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from talos.extract.asin_resolver import ResolutionCandidate, ResolutionResult
from talos.ui.listino_input import (
    DEFAULT_REFERRAL_FEE_PCT,
    DescrizionePrezzoRow,
    ResolvedRow,
    apply_candidate_overrides,
    build_listino_raw_from_resolved,
    format_confidence_badge,
    parse_descrizione_prezzo_csv,
    resolve_listino_with_cache,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# `parse_descrizione_prezzo_csv`
# ---------------------------------------------------------------------------


def test_parse_csv_minimal_2_columns() -> None:
    """CSV con sole colonne obbligatorie -> default per opzionali."""
    df = pd.DataFrame(
        {
            "descrizione": ["Galaxy S24 256GB", "iPhone 15 Pro"],
            "prezzo": [549.00, 1199.00],
        },
    )
    rows, warnings = parse_descrizione_prezzo_csv(df)
    assert len(rows) == 2
    assert rows[0].descrizione == "Galaxy S24 256GB"
    assert rows[0].prezzo_eur == Decimal("549.00")
    assert rows[0].v_tot == 0  # default
    assert rows[0].s_comp == 0  # default
    assert rows[0].category_node is None
    assert warnings == []


def test_parse_csv_with_optional_columns() -> None:
    """Colonne opzionali popolate -> override default."""
    df = pd.DataFrame(
        {
            "descrizione": ["Galaxy S24"],
            "prezzo": [549.00],
            "v_tot": [100],
            "s_comp": [5],
            "category_node": ["Smartphone Cellulari"],
        },
    )
    rows, warnings = parse_descrizione_prezzo_csv(df)
    assert len(rows) == 1
    assert rows[0].v_tot == 100
    assert rows[0].s_comp == 5
    assert rows[0].category_node == "Smartphone Cellulari"
    assert warnings == []


def test_parse_csv_missing_required_columns_raises() -> None:
    """Manca `descrizione` o `prezzo` -> ValueError."""
    df = pd.DataFrame({"descrizione": ["x"]})
    with pytest.raises(ValueError, match="prezzo"):
        parse_descrizione_prezzo_csv(df)
    df2 = pd.DataFrame({"prezzo": [100]})
    with pytest.raises(ValueError, match="descrizione"):
        parse_descrizione_prezzo_csv(df2)


def test_parse_csv_skips_empty_description_with_warning() -> None:
    """Descrizione vuota / whitespace -> riga skippata + warning."""
    df = pd.DataFrame(
        {
            "descrizione": ["Galaxy S24", "", "   "],
            "prezzo": [549, 100, 200],
        },
    )
    rows, warnings = parse_descrizione_prezzo_csv(df)
    assert len(rows) == 1
    assert rows[0].descrizione == "Galaxy S24"
    assert len(warnings) == 2
    assert all("descrizione vuota" in w for w in warnings)


def test_parse_csv_skips_invalid_price() -> None:
    """Prezzo <= 0 o non parsable -> warning + skip."""
    df = pd.DataFrame(
        {
            "descrizione": ["Galaxy S24", "Item B", "Item C"],
            "prezzo": [549, 0, -10],
        },
    )
    rows, warnings = parse_descrizione_prezzo_csv(df)
    assert len(rows) == 1
    assert rows[0].descrizione == "Galaxy S24"
    assert len(warnings) == 2


def test_parse_csv_normalizes_whitespace_in_description() -> None:
    """Descrizione con spazi laterali -> trim."""
    df = pd.DataFrame(
        {
            "descrizione": ["  Galaxy S24  "],
            "prezzo": [549],
        },
    )
    rows, _ = parse_descrizione_prezzo_csv(df)
    assert rows[0].descrizione == "Galaxy S24"


# ---------------------------------------------------------------------------
# `format_confidence_badge`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("conf", "expected_prefix"),
    [
        (95.0, "OK"),
        (85.0, "OK"),  # boundary inclusive
        (84.9, "DUB"),
        (75.0, "DUB"),
        (70.0, "DUB"),  # boundary inclusive
        (69.9, "AMB"),
        (50.0, "AMB"),
        (0.0, "AMB"),
        (100.0, "OK"),
    ],
)
def test_format_confidence_badge_thresholds(conf: float, expected_prefix: str) -> None:
    """Soglie 85 / 70 -> OK / DUB / AMB."""
    badge = format_confidence_badge(conf)
    assert badge.startswith(expected_prefix)


def test_format_confidence_badge_out_of_range() -> None:
    """Confidence fuori [0,100] -> stringa fallback `?`."""
    assert format_confidence_badge(150.0).startswith("?")
    assert format_confidence_badge(-5.0).startswith("?")


# ---------------------------------------------------------------------------
# `build_listino_raw_from_resolved`
# ---------------------------------------------------------------------------


def _resolved(
    asin: str,
    prezzo: float,
    *,
    category: str | None = None,
    verified_buybox: float | None = None,
) -> ResolvedRow:
    return ResolvedRow(
        descrizione=f"desc {asin}",
        prezzo_eur=Decimal(str(prezzo)),
        asin=asin,
        confidence_pct=90.0,
        is_ambiguous=False,
        is_cache_hit=False,
        v_tot=10,
        s_comp=2,
        category_node=category,
        notes=(),
        verified_buybox_eur=Decimal(str(verified_buybox)) if verified_buybox is not None else None,
    )


def test_build_listino_raw_minimal_7_columns() -> None:
    """Output ha le 7 colonne obbligatorie + valori risolti."""
    rows = [_resolved("B0CSTC2RDW", 549.00), _resolved("B0OTHER001", 299.00)]
    df = build_listino_raw_from_resolved(rows)
    expected = {
        "asin",
        "buy_box_eur",
        "cost_eur",
        "referral_fee_pct",
        "v_tot",
        "s_comp",
        "match_status",
    }
    assert set(df.columns) >= expected
    assert len(df) == 2
    assert df.iloc[0]["asin"] == "B0CSTC2RDW"
    assert df.iloc[0]["buy_box_eur"] == 549.00
    assert df.iloc[0]["cost_eur"] == 549.00
    assert df.iloc[0]["referral_fee_pct"] == DEFAULT_REFERRAL_FEE_PCT
    assert df.iloc[0]["match_status"] == "SICURO"


def test_build_listino_raw_skips_unresolved() -> None:
    """Righe con `asin=""` (resolver fail) skippate dal listino finale."""
    rows = [
        _resolved("B0CSTC2RDW", 549.00),
        ResolvedRow(
            descrizione="Galaxy A55",
            prezzo_eur=Decimal("299.00"),
            asin="",  # Unresolved
            confidence_pct=0.0,
            is_ambiguous=True,
            is_cache_hit=False,
            v_tot=0,
            s_comp=0,
            category_node=None,
            notes=("zero risultati SERP",),
        ),
    ]
    df = build_listino_raw_from_resolved(rows)
    assert len(df) == 1
    assert df.iloc[0]["asin"] == "B0CSTC2RDW"


def test_build_listino_raw_includes_category_node_when_any_present() -> None:
    """Se almeno una riga ha category_node, colonna inclusa nel df finale."""
    rows = [
        _resolved("B0AAA000001", 100.00, category="Cellulari"),
        _resolved("B0BBB000002", 200.00, category=None),
    ]
    df = build_listino_raw_from_resolved(rows)
    assert "category_node" in df.columns
    assert df.iloc[0]["category_node"] == "Cellulari"
    assert df.iloc[1]["category_node"] == ""


def test_build_listino_raw_no_category_when_all_absent() -> None:
    """Se nessuna riga ha category_node, colonna non emessa (lighter df)."""
    rows = [_resolved("B0AAA000001", 100.00, category=None)]
    df = build_listino_raw_from_resolved(rows)
    assert "category_node" not in df.columns


def test_build_listino_raw_all_unresolved_returns_empty_with_schema() -> None:
    """Tutte le righe non risolte -> df vuoto ma con le 7 colonne."""
    rows = [
        ResolvedRow(
            descrizione="X",
            prezzo_eur=Decimal(100),
            asin="",
            confidence_pct=0.0,
            is_ambiguous=True,
            is_cache_hit=False,
            v_tot=0,
            s_comp=0,
            category_node=None,
            notes=(),
        ),
    ]
    df = build_listino_raw_from_resolved(rows)
    assert len(df) == 0
    assert set(df.columns) == {
        "asin",
        "buy_box_eur",
        "cost_eur",
        "referral_fee_pct",
        "v_tot",
        "s_comp",
        "match_status",
    }


# ---------------------------------------------------------------------------
# `resolve_listino_with_cache` — happy path mock-only
# ---------------------------------------------------------------------------


class _MockResolver:
    """Mock resolver: ritorna un ResolutionResult statico per descrizione."""

    def __init__(self, mapping: dict[str, str]) -> None:
        # mapping: descrizione -> asin
        self._mapping = mapping
        self.calls = 0

    def resolve_description(self, description: str, input_price_eur: Decimal) -> ResolutionResult:
        self.calls += 1
        asin = self._mapping.get(description)
        if asin is None:
            return ResolutionResult(
                description=description,
                input_price_eur=input_price_eur,
                selected=None,
                candidates=(),
                is_ambiguous=True,
                notes=("mock no match",),
            )
        cand = ResolutionCandidate(
            asin=asin,
            title=f"Title {asin}",
            buybox_eur=input_price_eur,
            fuzzy_title_pct=95.0,
            delta_price_pct=0.0,
            confidence_pct=97.0,
        )
        return ResolutionResult(
            description=description,
            input_price_eur=input_price_eur,
            selected=cand,
            candidates=(cand,),
            is_ambiguous=False,
            notes=(),
        )


def test_resolve_with_no_factory_skips_cache_always_resolves() -> None:
    """Senza DB (factory=None): sempre resolve, no cache ops."""
    resolver = _MockResolver({"Galaxy S24": "B0CSTC2RDW"})
    rows = [
        DescrizionePrezzoRow(
            descrizione="Galaxy S24",
            prezzo_eur=Decimal(549),
            v_tot=0,
            s_comp=0,
            category_node=None,
        ),
    ]
    resolved = resolve_listino_with_cache(
        rows,
        factory=None,
        resolver_provider=lambda: resolver,
    )
    assert len(resolved) == 1
    assert resolved[0].asin == "B0CSTC2RDW"
    assert resolved[0].is_cache_hit is False
    assert resolved[0].confidence_pct == pytest.approx(97.0)
    assert resolver.calls == 1


def test_resolve_unresolvable_description_returns_empty_asin() -> None:
    """Descrizione che il resolver non risolve -> asin="" + notes."""
    resolver = _MockResolver({})  # vuoto
    rows = [
        DescrizionePrezzoRow(
            descrizione="ProdottoIntrovabile",
            prezzo_eur=Decimal(100),
            v_tot=0,
            s_comp=0,
            category_node=None,
        ),
    ]
    resolved = resolve_listino_with_cache(rows, factory=None, resolver_provider=lambda: resolver)
    assert len(resolved) == 1
    assert resolved[0].asin == ""
    assert resolved[0].is_ambiguous is True
    assert resolved[0].notes == ("mock no match",)


def test_resolve_resolver_lazy_init_only_when_needed() -> None:
    """Resolver provider chiamato solo se necessario (no rows -> mai)."""
    call_count = {"n": 0}

    def provider() -> _MockResolver:
        call_count["n"] += 1
        return _MockResolver({})

    resolved = resolve_listino_with_cache([], factory=None, resolver_provider=provider)
    assert resolved == []
    assert call_count["n"] == 0


# ---------------------------------------------------------------------------
# `verified_buybox_eur` propagation (CHG-2026-05-01-022)
# ---------------------------------------------------------------------------


class _MockResolverWithBuybox:
    """Mock resolver con buybox custom (per test A2 verified_buybox propagation)."""

    def __init__(self, mapping: dict[str, tuple[str, Decimal | None]]) -> None:
        # mapping: descrizione -> (asin, buybox_eur or None per lookup-failed)
        self._mapping = mapping

    def resolve_description(self, description: str, input_price_eur: Decimal) -> ResolutionResult:
        entry = self._mapping.get(description)
        if entry is None:
            return ResolutionResult(
                description=description,
                input_price_eur=input_price_eur,
                selected=None,
                candidates=(),
                is_ambiguous=True,
                notes=("mock no match",),
            )
        asin, buybox = entry
        cand = ResolutionCandidate(
            asin=asin,
            title=f"Title {asin}",
            buybox_eur=buybox,
            fuzzy_title_pct=95.0,
            delta_price_pct=0.0 if buybox is not None else None,
            confidence_pct=97.0 if buybox is not None else 57.0,
        )
        return ResolutionResult(
            description=description,
            input_price_eur=input_price_eur,
            selected=cand,
            candidates=(cand,),
            is_ambiguous=False,
            notes=(),
        )


def test_resolved_row_propagates_verified_buybox_from_resolver() -> None:
    """Resolver buybox -> ResolvedRow.verified_buybox_eur."""
    resolver = _MockResolverWithBuybox(
        {"Galaxy S24 256GB": ("B0CSTC2RDW", Decimal("599.50"))},
    )
    rows = [
        DescrizionePrezzoRow(
            descrizione="Galaxy S24 256GB",
            prezzo_eur=Decimal("549.00"),  # prezzo fornitore (cost)
            v_tot=0,
            s_comp=0,
            category_node=None,
        ),
    ]
    resolved = resolve_listino_with_cache(rows, factory=None, resolver_provider=lambda: resolver)
    assert len(resolved) == 1
    assert resolved[0].verified_buybox_eur == Decimal("599.50")
    assert resolved[0].prezzo_eur == Decimal("549.00")  # cost preservato


def test_resolved_row_buybox_none_when_lookup_failed() -> None:
    """Resolver con buybox=None (lookup fail) -> ResolvedRow.verified_buybox_eur=None."""
    resolver = _MockResolverWithBuybox(
        {"Galaxy S24": ("B0AAA111111", None)},  # lookup fallito
    )
    rows = [
        DescrizionePrezzoRow(
            descrizione="Galaxy S24",
            prezzo_eur=Decimal("549.00"),
            v_tot=0,
            s_comp=0,
            category_node=None,
        ),
    ]
    resolved = resolve_listino_with_cache(rows, factory=None, resolver_provider=lambda: resolver)
    assert resolved[0].asin == "B0AAA111111"
    assert resolved[0].verified_buybox_eur is None


def test_build_listino_uses_verified_buybox_when_present() -> None:
    """Buy Box live (es. Keepa NEW) -> `buy_box_eur` distinto da `cost_eur`."""
    rows = [_resolved("B0AAA111111", 549.00, verified_buybox=599.50)]
    df = build_listino_raw_from_resolved(rows)
    assert df.iloc[0]["cost_eur"] == 549.00  # prezzo fornitore
    assert df.iloc[0]["buy_box_eur"] == 599.50  # Amazon NEW


def test_build_listino_falls_back_to_cost_when_no_verified_buybox() -> None:
    """Senza buybox verificato -> fallback retro-compat: buy_box=cost (CHG-020)."""
    rows = [_resolved("B0AAA111111", 549.00, verified_buybox=None)]
    df = build_listino_raw_from_resolved(rows)
    assert df.iloc[0]["cost_eur"] == 549.00
    assert df.iloc[0]["buy_box_eur"] == 549.00  # fallback


def test_build_listino_mixed_verified_and_fallback() -> None:
    """Listino misto (alcuni con buybox verificato, alcuni no): comportamento per-riga."""
    rows = [
        _resolved("B0AAA000001", 100.00, verified_buybox=120.00),
        _resolved("B0BBB000002", 200.00, verified_buybox=None),
        _resolved("B0CCC000003", 50.00, verified_buybox=55.00),
    ]
    df = build_listino_raw_from_resolved(rows)
    assert list(df["cost_eur"]) == [100.00, 200.00, 50.00]
    assert list(df["buy_box_eur"]) == [120.00, 200.00, 55.00]


def test_resolved_row_default_verified_buybox_is_none() -> None:
    """Default `verified_buybox_eur=None` per backward compat costruzione esplicita."""
    row = ResolvedRow(
        descrizione="x",
        prezzo_eur=Decimal(100),
        asin="B0AAA111111",
        confidence_pct=80.0,
        is_ambiguous=False,
        is_cache_hit=False,
        v_tot=0,
        s_comp=0,
        category_node=None,
        notes=(),
    )
    assert row.verified_buybox_eur is None
    assert row.candidates == ()


# ---------------------------------------------------------------------------
# `apply_candidate_overrides` (CHG-2026-05-01-023)
# ---------------------------------------------------------------------------


def _candidate(
    asin: str,
    *,
    confidence: float = 80.0,
    buybox: float | None = 100.0,
    title: str = "Mock Title",
) -> ResolutionCandidate:
    return ResolutionCandidate(
        asin=asin,
        title=title,
        buybox_eur=Decimal(str(buybox)) if buybox is not None else None,
        fuzzy_title_pct=85.0,
        delta_price_pct=5.0 if buybox is not None else None,
        confidence_pct=confidence,
    )


def _ambiguous_resolved(asin: str = "B0DEFAULT01") -> ResolvedRow:
    """ResolvedRow ambigua con 3 candidati (CHG-023 fixture base)."""
    candidates = (
        _candidate(asin, confidence=60.0, buybox=100.0),
        _candidate("B0CAND00002", confidence=58.0, buybox=110.0),
        _candidate("B0CAND00003", confidence=55.0, buybox=95.0),
    )
    return ResolvedRow(
        descrizione="Galaxy ambiguous",
        prezzo_eur=Decimal("99.00"),
        asin=asin,
        confidence_pct=60.0,
        is_ambiguous=True,
        is_cache_hit=False,
        v_tot=0,
        s_comp=0,
        category_node=None,
        notes=(),
        verified_buybox_eur=Decimal("100.00"),
        candidates=candidates,
    )


def test_apply_overrides_no_op_when_empty() -> None:
    """Override map vuoto -> resolved invariato."""
    rows = [_ambiguous_resolved()]
    result = apply_candidate_overrides(rows, {})
    assert result == rows


def test_apply_overrides_swaps_asin_and_buybox_and_confidence() -> None:
    """Override valido -> asin/buybox/confidence presi dal candidato scelto."""
    rows = [_ambiguous_resolved("B0DEFAULT01")]
    result = apply_candidate_overrides(rows, {0: "B0CAND00002"})
    assert result[0].asin == "B0CAND00002"
    assert result[0].confidence_pct == 58.0
    assert result[0].verified_buybox_eur == Decimal("110.00")


def test_apply_overrides_propagates_ambiguous_threshold() -> None:
    """`is_ambiguous` ricalcolato sul confidence del candidato scelto (boundary 70)."""
    high_conf_candidates = (
        _candidate("B0DEFAULT01", confidence=60.0, buybox=100.0),
        ResolutionCandidate(
            asin="B0HIGHCONF1",
            title="Confident",
            buybox_eur=Decimal(100),
            fuzzy_title_pct=95.0,
            delta_price_pct=2.0,
            confidence_pct=92.0,
        ),
    )
    rows = [
        ResolvedRow(
            descrizione="x",
            prezzo_eur=Decimal(100),
            asin="B0DEFAULT01",
            confidence_pct=60.0,
            is_ambiguous=True,
            is_cache_hit=False,
            v_tot=0,
            s_comp=0,
            category_node=None,
            notes=(),
            verified_buybox_eur=Decimal(100),
            candidates=high_conf_candidates,
        ),
    ]
    result = apply_candidate_overrides(rows, {0: "B0HIGHCONF1"})
    assert result[0].is_ambiguous is False  # 92 >= 70
    assert result[0].confidence_pct == 92.0


def test_apply_overrides_appends_audit_note() -> None:
    """R-01: ogni override aggiunge nota audit con la scelta originale."""
    rows = [_ambiguous_resolved("B0DEFAULT01")]
    result = apply_candidate_overrides(rows, {0: "B0CAND00002"})
    assert any("override manuale CFO" in n for n in result[0].notes)
    assert any("B0CAND00002" in n and "B0DEFAULT01" in n for n in result[0].notes)


def test_apply_overrides_invalid_asin_is_no_op() -> None:
    """Override con asin non in candidates -> riga invariata (no-op silenzioso)."""
    rows = [_ambiguous_resolved("B0DEFAULT01")]
    result = apply_candidate_overrides(rows, {0: "B0NOTACAND0"})
    assert result[0].asin == "B0DEFAULT01"
    assert result[0].notes == ()


def test_apply_overrides_redundant_no_op() -> None:
    """Override == asin corrente -> no-op (no nota audit duplicata)."""
    rows = [_ambiguous_resolved("B0DEFAULT01")]
    result = apply_candidate_overrides(rows, {0: "B0DEFAULT01"})
    assert result[0].notes == ()


def test_apply_overrides_only_specified_indexes_changed() -> None:
    """Override per idx specifico non tocca altre righe."""
    rows = [
        _ambiguous_resolved("B0AAA000001"),
        _ambiguous_resolved("B0BBB000002"),
        _ambiguous_resolved("B0CCC000003"),
    ]
    result = apply_candidate_overrides(rows, {1: "B0CAND00002"})
    assert result[0].asin == "B0AAA000001"  # invariato
    assert result[1].asin == "B0CAND00002"  # cambiato
    assert result[2].asin == "B0CCC000003"  # invariato


def test_apply_overrides_idx_out_of_range_no_crash() -> None:
    """idx fuori range nell'override map -> ignorato, no crash."""
    rows = [_ambiguous_resolved()]
    result = apply_candidate_overrides(rows, {99: "B0CAND00002"})
    assert result == rows
