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
    count_cache_hit,
    count_eligible_for_overrides,
    count_resolved,
    count_with_verified_buybox,
    format_buybox_verified_caption,
    format_cache_hit_caption,
    format_confidence_badge,
    parse_descrizione_prezzo_csv,
    resolve_listino_with_cache,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Costanti — contract sentinels (CHG-2026-05-01-038)
# ---------------------------------------------------------------------------


def test_default_referral_fee_pct_is_decimal_fraction() -> None:
    """Lock contract: `DEFAULT_REFERRAL_FEE_PCT` deve essere frazione [0, 1].

    Coerente con `cash_inflow_eur(referral_fee_rate)` che valida lo
    stesso range. Sentinel per prevenire la regressione fixata in
    CHG-2026-05-01-038 (era 8.0 = "8 percent" → rotta pipeline su default).
    """
    assert 0.0 <= DEFAULT_REFERRAL_FEE_PCT <= 1.0


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
# `format_cache_hit_caption` (CHG-2026-05-01-026)
# ---------------------------------------------------------------------------


def _resolved_with_cache_hit(*, is_cache_hit: bool, asin: str = "B0CSTC2RDW") -> ResolvedRow:
    """Helper minimo: ResolvedRow con flag is_cache_hit per stat aggregata."""
    return ResolvedRow(
        descrizione="Galaxy S24",
        prezzo_eur=Decimal("549.00"),
        asin=asin,
        confidence_pct=95.0,
        is_ambiguous=False,
        is_cache_hit=is_cache_hit,
        v_tot=0,
        s_comp=0,
        category_node=None,
        notes=(),
    )


def test_format_cache_hit_caption_empty_returns_empty_string() -> None:
    """Lista vuota -> stringa vuota (caller suppress dal caption finale)."""
    assert format_cache_hit_caption([]) == ""


def test_format_cache_hit_caption_all_hits() -> None:
    """Tutti hit -> 100%."""
    rows = [_resolved_with_cache_hit(is_cache_hit=True) for _ in range(5)]
    assert format_cache_hit_caption(rows) == "Cache: 5/5 hit (100%)."


def test_format_cache_hit_caption_all_misses() -> None:
    """Tutti miss (cache fredda o factory=None) -> 0%."""
    rows = [_resolved_with_cache_hit(is_cache_hit=False) for _ in range(4)]
    assert format_cache_hit_caption(rows) == "Cache: 0/4 hit (0%)."


def test_format_cache_hit_caption_mixed() -> None:
    """Mixed 3 hit / 12 totali -> 25%."""
    rows = [_resolved_with_cache_hit(is_cache_hit=True) for _ in range(3)] + [
        _resolved_with_cache_hit(is_cache_hit=False) for _ in range(9)
    ]
    assert format_cache_hit_caption(rows) == "Cache: 3/12 hit (25%)."


def test_format_cache_hit_caption_single_hit() -> None:
    """Single hit -> 100%."""
    rows = [_resolved_with_cache_hit(is_cache_hit=True)]
    assert format_cache_hit_caption(rows) == "Cache: 1/1 hit (100%)."


def test_format_cache_hit_caption_single_miss() -> None:
    """Single miss -> 0%."""
    rows = [_resolved_with_cache_hit(is_cache_hit=False)]
    assert format_cache_hit_caption(rows) == "Cache: 0/1 hit (0%)."


def test_format_cache_hit_caption_includes_unresolved_rows() -> None:
    """Righe non risolte (asin='') contate nel total ma con is_cache_hit=False."""
    rows = [
        _resolved_with_cache_hit(is_cache_hit=True),
        _resolved_with_cache_hit(is_cache_hit=False, asin=""),
    ]
    assert format_cache_hit_caption(rows) == "Cache: 1/2 hit (50%)."


# ---------------------------------------------------------------------------
# `format_buybox_verified_caption` (CHG-2026-05-01-027)
# ---------------------------------------------------------------------------


def _resolved_with_buybox(
    *,
    verified_buybox_eur: Decimal | None,
    asin: str = "B0CSTC2RDW",
) -> ResolvedRow:
    """Helper minimo: ResolvedRow con verified_buybox_eur per stat aggregata."""
    return ResolvedRow(
        descrizione="Galaxy S24",
        prezzo_eur=Decimal("549.00"),
        asin=asin,
        confidence_pct=95.0,
        is_ambiguous=False,
        is_cache_hit=False,
        v_tot=0,
        s_comp=0,
        category_node=None,
        notes=(),
        verified_buybox_eur=verified_buybox_eur,
    )


def test_format_buybox_verified_caption_empty_returns_empty_string() -> None:
    """Lista vuota -> stringa vuota (caller suppress dal caption finale)."""
    assert format_buybox_verified_caption([]) == ""


def test_format_buybox_verified_caption_all_verified() -> None:
    """Tutti hanno Buy Box live -> 100%."""
    rows = [_resolved_with_buybox(verified_buybox_eur=Decimal("599.00")) for _ in range(5)]
    assert format_buybox_verified_caption(rows) == "Buy Box verificato: 5/5 righe (100%)."


def test_format_buybox_verified_caption_none_verified() -> None:
    """Tutti fallback (cache hit / lookup fail) -> 0%."""
    rows = [_resolved_with_buybox(verified_buybox_eur=None) for _ in range(4)]
    assert format_buybox_verified_caption(rows) == "Buy Box verificato: 0/4 righe (0%)."


def test_format_buybox_verified_caption_mixed() -> None:
    """Mixed 3 verified / 12 totali -> 25%."""
    rows = [_resolved_with_buybox(verified_buybox_eur=Decimal("599.00")) for _ in range(3)] + [
        _resolved_with_buybox(verified_buybox_eur=None) for _ in range(9)
    ]
    assert format_buybox_verified_caption(rows) == "Buy Box verificato: 3/12 righe (25%)."


def test_format_buybox_verified_caption_single_verified() -> None:
    """Single verified -> 100%."""
    rows = [_resolved_with_buybox(verified_buybox_eur=Decimal("549.00"))]
    assert format_buybox_verified_caption(rows) == "Buy Box verificato: 1/1 righe (100%)."


def test_format_buybox_verified_caption_single_fallback() -> None:
    """Single fallback (no Buy Box live) -> 0%."""
    rows = [_resolved_with_buybox(verified_buybox_eur=None)]
    assert format_buybox_verified_caption(rows) == "Buy Box verificato: 0/1 righe (0%)."


def test_format_buybox_verified_caption_includes_unresolved_rows() -> None:
    """Righe non risolte (asin='') contate nel total con buybox=None per definizione."""
    rows = [
        _resolved_with_buybox(verified_buybox_eur=Decimal("599.00")),
        _resolved_with_buybox(verified_buybox_eur=None, asin=""),
    ]
    assert format_buybox_verified_caption(rows) == "Buy Box verificato: 1/2 righe (50%)."


# ---------------------------------------------------------------------------
# `count_eligible_for_overrides` (CHG-2026-05-01-028)
# ---------------------------------------------------------------------------


def _resolved_eligibility(
    *,
    is_ambiguous: bool,
    asin: str,
    n_candidates: int,
) -> ResolvedRow:
    """Helper minimo: ResolvedRow con condizioni di eligibility variate.

    Conta solo: is_ambiguous, asin (truthy), len(candidates) > 1.
    Per `n_candidates`, popoliamo `candidates` con tuple di placeholder
    (i contenuti non vengono ispezionati dall'helper sotto test).
    """
    candidates = tuple(
        ResolutionCandidate(
            asin=f"B0CSTC2RD{i}",
            title="placeholder",
            buybox_eur=Decimal("549.00"),
            confidence_pct=80.0,
            fuzzy_title_pct=80.0,
            delta_price_pct=0.0,
        )
        for i in range(n_candidates)
    )
    return ResolvedRow(
        descrizione="placeholder",
        prezzo_eur=Decimal("549.00"),
        asin=asin,
        confidence_pct=65.0,
        is_ambiguous=is_ambiguous,
        is_cache_hit=False,
        v_tot=0,
        s_comp=0,
        category_node=None,
        notes=(),
        candidates=candidates,
    )


def test_count_eligible_empty_returns_zero() -> None:
    """Lista vuota -> 0."""
    assert count_eligible_for_overrides([]) == 0


def test_count_eligible_no_ambiguous_returns_zero() -> None:
    """Tutte le righe sicure (is_ambiguous=False) -> 0 anche con N candidates."""
    rows = [
        _resolved_eligibility(is_ambiguous=False, asin="B0CSTC2RD0", n_candidates=3)
        for _ in range(5)
    ]
    assert count_eligible_for_overrides(rows) == 0


def test_count_eligible_unresolved_excluded() -> None:
    """Righe ambigue ma senza asin (resolver fail) -> 0 (non ci sono candidati da scegliere)."""
    rows = [
        _resolved_eligibility(is_ambiguous=True, asin="", n_candidates=3),
    ]
    assert count_eligible_for_overrides(rows) == 0


def test_count_eligible_single_candidate_excluded() -> None:
    """Riga ambigua con 1 solo candidato -> 0 (override su set di 1 = no-op)."""
    rows = [
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD0", n_candidates=1),
    ]
    assert count_eligible_for_overrides(rows) == 0


def test_count_eligible_zero_candidates_excluded() -> None:
    """Cache hit con candidates=() -> 0 (l'override sulla cache non è interattivo)."""
    rows = [
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD0", n_candidates=0),
    ]
    assert count_eligible_for_overrides(rows) == 0


def test_count_eligible_mixed() -> None:
    """3 eligible + 2 ambigui-con-1-cand + 1 sicura + 1 unresolved -> 3."""
    rows = [
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD0", n_candidates=3),
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD1", n_candidates=2),
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD2", n_candidates=4),
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD3", n_candidates=1),
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD4", n_candidates=1),
        _resolved_eligibility(is_ambiguous=False, asin="B0CSTC2RD5", n_candidates=3),
        _resolved_eligibility(is_ambiguous=True, asin="", n_candidates=3),
    ]
    assert count_eligible_for_overrides(rows) == 3


# ---------------------------------------------------------------------------
# `count_resolved` / `count_cache_hit` / `count_with_verified_buybox`
# (CHG-2026-05-01-029 — extension count family)
# ---------------------------------------------------------------------------


def test_count_resolved_empty_returns_zero() -> None:
    """Lista vuota -> 0."""
    assert count_resolved([]) == 0


def test_count_resolved_all_resolved() -> None:
    """Tutte le righe risolte (asin truthy) -> N."""
    rows = [_resolved_with_cache_hit(is_cache_hit=False, asin=f"B0CSTC2RD{i}") for i in range(5)]
    assert count_resolved(rows) == 5


def test_count_resolved_all_unresolved() -> None:
    """Tutte le righe non risolte (asin='') -> 0."""
    rows = [_resolved_with_cache_hit(is_cache_hit=False, asin="") for _ in range(4)]
    assert count_resolved(rows) == 0


def test_count_resolved_mixed() -> None:
    """3 risolte + 2 non risolte -> 3."""
    rows = [
        *[_resolved_with_cache_hit(is_cache_hit=False, asin=f"B0CSTC2RD{i}") for i in range(3)],
        *[_resolved_with_cache_hit(is_cache_hit=False, asin="") for _ in range(2)],
    ]
    assert count_resolved(rows) == 3


def test_count_cache_hit_empty_returns_zero() -> None:
    """Lista vuota -> 0."""
    assert count_cache_hit([]) == 0


def test_count_cache_hit_all_hits() -> None:
    """Tutte hit -> N."""
    rows = [_resolved_with_cache_hit(is_cache_hit=True) for _ in range(4)]
    assert count_cache_hit(rows) == 4


def test_count_cache_hit_all_misses() -> None:
    """Tutte miss (factory=None o cache fredda) -> 0."""
    rows = [_resolved_with_cache_hit(is_cache_hit=False) for _ in range(5)]
    assert count_cache_hit(rows) == 0


def test_count_cache_hit_mixed() -> None:
    """2 hit + 7 miss -> 2."""
    rows = [
        *[_resolved_with_cache_hit(is_cache_hit=True) for _ in range(2)],
        *[_resolved_with_cache_hit(is_cache_hit=False) for _ in range(7)],
    ]
    assert count_cache_hit(rows) == 2


def test_count_with_verified_buybox_empty_returns_zero() -> None:
    """Lista vuota -> 0."""
    assert count_with_verified_buybox([]) == 0


def test_count_with_verified_buybox_all_verified() -> None:
    """Tutte con Buy Box live -> N."""
    rows = [_resolved_with_buybox(verified_buybox_eur=Decimal("599.00")) for _ in range(3)]
    assert count_with_verified_buybox(rows) == 3


def test_count_with_verified_buybox_none_verified() -> None:
    """Tutte fallback (cache hit / lookup fail) -> 0."""
    rows = [_resolved_with_buybox(verified_buybox_eur=None) for _ in range(6)]
    assert count_with_verified_buybox(rows) == 0


def test_count_with_verified_buybox_mixed() -> None:
    """4 verified + 8 fallback -> 4."""
    rows = [
        *[_resolved_with_buybox(verified_buybox_eur=Decimal("599.00")) for _ in range(4)],
        *[_resolved_with_buybox(verified_buybox_eur=None) for _ in range(8)],
    ]
    assert count_with_verified_buybox(rows) == 4


# ---------------------------------------------------------------------------
# `build_listino_raw_from_resolved`
# ---------------------------------------------------------------------------


def _resolved(  # noqa: PLR0913 — test fixture helper, args correlati a ResolvedRow shape
    asin: str,
    prezzo: float,
    *,
    category: str | None = None,
    verified_buybox: float | None = None,
    v_tot: int = 10,
    bsr_root: int | None = None,
) -> ResolvedRow:
    return ResolvedRow(
        descrizione=f"desc {asin}",
        prezzo_eur=Decimal(str(prezzo)),
        asin=asin,
        confidence_pct=90.0,
        is_ambiguous=False,
        is_cache_hit=False,
        v_tot=v_tot,
        s_comp=2,
        category_node=category,
        notes=(),
        verified_buybox_eur=Decimal(str(verified_buybox)) if verified_buybox is not None else None,
        bsr_root=bsr_root,
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


def test_build_listino_v_tot_csv_override_wins() -> None:
    """CHG-2026-05-02-003: v_tot CSV>0 ignora bsr_root (override esplicito)."""
    rows = [_resolved("B0AAA", 100.0, v_tot=42, bsr_root=5000)]
    df = build_listino_raw_from_resolved(rows)
    assert df.iloc[0]["v_tot"] == 42.0
    assert df.iloc[0]["v_tot_source"] == "csv"


def test_build_listino_v_tot_estimated_from_bsr_when_csv_zero() -> None:
    """CHG-2026-05-02-003: v_tot CSV=0 + bsr disponibile -> stima MVP."""
    # bsr=10000 -> formula log: 100 - 20*log10(10000) = 100 - 80 = 20
    rows = [_resolved("B0AAA", 100.0, v_tot=0, bsr_root=10000)]
    df = build_listino_raw_from_resolved(rows)
    assert df.iloc[0]["v_tot"] == pytest.approx(20.0)
    assert df.iloc[0]["v_tot_source"] == "bsr_estimate_mvp"


def test_build_listino_v_tot_default_zero_when_no_csv_no_bsr() -> None:
    """CHG-2026-05-02-003: nessun override + nessun BSR -> v_tot=0."""
    rows = [_resolved("B0AAA", 100.0, v_tot=0, bsr_root=None)]
    df = build_listino_raw_from_resolved(rows)
    assert df.iloc[0]["v_tot"] == 0.0
    assert df.iloc[0]["v_tot_source"] == "default_zero"


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
# Cache hit + buybox live (CHG-2026-05-01-039)
# ---------------------------------------------------------------------------


class _FakeCachedRow:
    """Stub minimo di `DescriptionResolution` per mock cache hit."""

    def __init__(self, *, asin: str, confidence_pct: float) -> None:
        self.asin = asin
        self.confidence_pct = Decimal(str(confidence_pct))


class _FakeProductData:
    """Stub minimo di `ProductData` (`buybox_eur` + `bsr` consumati dall'helper)."""

    def __init__(self, buybox_eur: Decimal | None, bsr: int | None = None) -> None:
        self.buybox_eur = buybox_eur
        self.bsr = bsr


class _FakeFactory:
    """Sessionmaker fake che ritorna un context manager stub."""

    def __call__(self) -> _FakeFactory:
        return self

    def __enter__(self) -> object:
        return object()

    def __exit__(self, *_args: object) -> None:
        pass


def _row(descrizione: str = "Galaxy S24 256GB", prezzo: float = 380.0) -> DescrizionePrezzoRow:
    return DescrizionePrezzoRow(
        descrizione=descrizione,
        prezzo_eur=Decimal(str(prezzo)),
        v_tot=0,
        s_comp=0,
        category_node=None,
    )


def test_cache_hit_calls_lookup_callable_for_live_buybox(monkeypatch: pytest.MonkeyPatch) -> None:
    """CHG-039: cache hit chiama `lookup_callable(asin)` -> verified_buybox_eur valorizzato."""
    cached = _FakeCachedRow(asin="B0CSTC2RDW", confidence_pct=92.5)
    monkeypatch.setattr(
        "talos.ui.listino_input.find_resolution_by_hash",
        lambda _db, *, tenant_id, description_hash: cached,  # noqa: ARG005
    )

    lookup_calls: list[str] = []

    def lookup_stub(asin: str) -> _FakeProductData:
        lookup_calls.append(asin)
        return _FakeProductData(buybox_eur=Decimal("549.00"))

    resolved = resolve_listino_with_cache(
        [_row()],
        factory=_FakeFactory(),
        resolver_provider=lambda: _MockResolver({}),  # non chiamato (cache hit)
        lookup_callable=lookup_stub,
    )
    assert len(resolved) == 1
    assert resolved[0].asin == "B0CSTC2RDW"
    assert resolved[0].is_cache_hit is True
    assert resolved[0].verified_buybox_eur == Decimal("549.00")
    assert resolved[0].notes == ()
    assert lookup_calls == ["B0CSTC2RDW"]


def test_cache_hit_lookup_failure_yields_buybox_none_with_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CHG-039: lookup_callable solleva -> verified_buybox_eur=None + nota R-01."""
    cached = _FakeCachedRow(asin="B0CSTC2RDW", confidence_pct=92.5)
    monkeypatch.setattr(
        "talos.ui.listino_input.find_resolution_by_hash",
        lambda _db, *, tenant_id, description_hash: cached,  # noqa: ARG005
    )

    def lookup_failing(_asin: str) -> _FakeProductData:
        msg = "rate limit"
        raise RuntimeError(msg)

    resolved = resolve_listino_with_cache(
        [_row()],
        factory=_FakeFactory(),
        resolver_provider=lambda: _MockResolver({}),
        lookup_callable=lookup_failing,
    )
    assert resolved[0].asin == "B0CSTC2RDW"
    assert resolved[0].verified_buybox_eur is None
    assert len(resolved[0].notes) == 1
    assert "buybox lookup live failed: RuntimeError" in resolved[0].notes[0]


def test_cache_hit_without_lookup_callable_retro_compat_buybox_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CHG-039: lookup_callable=None (default) -> verified_buybox_eur=None (retro-compat)."""
    cached = _FakeCachedRow(asin="B0CSTC2RDW", confidence_pct=92.5)
    monkeypatch.setattr(
        "talos.ui.listino_input.find_resolution_by_hash",
        lambda _db, *, tenant_id, description_hash: cached,  # noqa: ARG005
    )

    resolved = resolve_listino_with_cache(
        [_row()],
        factory=_FakeFactory(),
        resolver_provider=lambda: _MockResolver({}),
        # lookup_callable omesso -> default None
    )
    assert resolved[0].asin == "B0CSTC2RDW"
    assert resolved[0].is_cache_hit is True
    assert resolved[0].verified_buybox_eur is None
    assert resolved[0].notes == ()


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
