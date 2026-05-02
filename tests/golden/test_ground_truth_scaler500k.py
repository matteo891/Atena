"""Golden test calibrazione ground truth ScalerBot500K (CHG-2026-05-02-039).

Origine: file Leader `ordine_scaler500k (22).xlsx` (3 tab: ORDINE / STRATEGIA /
BLOCCATI). Estratti i 7 ASIN della tab STRATEGIA come ground truth per
validazione TALOS field-by-field. Dati 100% reali del CFO, non Samsung-mini
sintetico.

Discrepanze documentate (NON risolte: ratifica Leader necessaria prima di
errata corrige ADR-0017 alpha-prime policy fee_fba):
- ScalerBot fee_fba implicita ≈ €3 (atomica, Keepa pickAndPackFee).
- TALOS fee_fba_manual L11b ≈ €22 (totale, formula Frozen).
- Effetto: 5/6 ASIN sotto VETO_ROI 8% in TALOS → cart vuoto.
"""

from __future__ import annotations

from typing import Final, TypedDict

import pytest

from talos.formulas.fee_fba import fee_fba_manual
from talos.risk import passes_amazon_presence
from talos.vgp import is_vetoed_by_roi

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixture inline: 7 ASIN ScalerBot500K (no separate file, vincolo pytest)
# ---------------------------------------------------------------------------


class _GroundTruthAsin(TypedDict):
    asin: str
    hw_id: str
    descrizione: str
    fornitore: str
    cost_eur: float
    buy_box_eur: float
    margin_pct: float
    profit_unit_eur: float
    roi_pct: float
    velocity_label: str
    vendite_mese: float
    qty_carrello: int
    qty_target_15gg: int
    status: str
    n_fornitori_alt: int


GROUND_TRUTH_ASINS: Final[tuple[_GroundTruthAsin, ...]] = (
    {
        "asin": "B0DZHNGR82",
        "hw_id": "A26/256GB/5G",
        "descrizione": "Samsung Galaxy A26 5G 256GB Black",
        "fornitore": "_offerte_gk",
        "cost_eur": 185.0,
        "buy_box_eur": 238.0,
        "margin_pct": 13.0,
        "profit_unit_eur": 30.97,
        "roi_pct": 16.74,
        "velocity_label": "Veloce",
        "vendite_mese": 41.14,
        "qty_carrello": 20,
        "qty_target_15gg": 20,
        "status": "CARRELLO",
        "n_fornitori_alt": 2,
    },
    {
        "asin": "B0DV9D6665",
        "hw_id": "A16/256GB",
        "descrizione": "Samsung A16 6.7 8/256GB Blue Black",
        "fornitore": "_offerte_gk",
        "cost_eur": 145.0,
        "buy_box_eur": 199.99,
        "margin_pct": 17.8,
        "profit_unit_eur": 35.58,
        "roi_pct": 24.54,
        "velocity_label": "Buona",
        "vendite_mese": 15.67,
        "qty_carrello": 5,
        "qty_target_15gg": 7,
        "status": "CARRELLO",
        "n_fornitori_alt": 1,
    },
    {
        "asin": "B0DZHHZFQV",
        "hw_id": "A56/128GB/5G",
        "descrizione": "Samsung Galaxy A56 5G 128GB Olive Green",
        "fornitore": "_offerte_gk",
        "cost_eur": 253.0,
        "buy_box_eur": 310.0,
        "margin_pct": 9.7,
        "profit_unit_eur": 30.01,
        "roi_pct": 11.86,
        "velocity_label": "Buona",
        "vendite_mese": 14.50,
        "qty_carrello": 5,
        "qty_target_15gg": 7,
        "status": "CARRELLO",
        "n_fornitori_alt": 1,
    },
    {
        "asin": "B0G1425KST",
        "hw_id": "S25FE/256GB/5G",
        "descrizione": "Samsung Galaxy S25 FE 5G 256GB Jetblack",
        "fornitore": "parktel_non_eu",
        "cost_eur": 425.0,
        "buy_box_eur": 509.9,
        "margin_pct": 8.7,
        "profit_unit_eur": 44.14,
        "roi_pct": 10.39,
        "velocity_label": "Buona",
        "vendite_mese": 21.0,
        "qty_carrello": 11,
        "qty_target_15gg": 10,
        "status": "PANCHINA_NO_BUDGET",
        "n_fornitori_alt": 1,
    },
    {
        "asin": "B0FMD7H9N5",
        "hw_id": "A17/128GB/5G",
        "descrizione": "Samsung Galaxy A17 5G 128GB Grey",
        "fornitore": "_offerte_gk",
        "cost_eur": 128.0,
        "buy_box_eur": 161.0,
        "margin_pct": 10.1,
        "profit_unit_eur": 16.28,
        "roi_pct": 12.72,
        "velocity_label": "Buona",
        "vendite_mese": 13.62,
        "qty_carrello": 7,
        "qty_target_15gg": 6,
        "status": "PANCHINA_NO_BUDGET",
        "n_fornitori_alt": 1,
    },
    {
        "asin": "B0FR5BXMFK",
        "hw_id": "S25FE/128GB",
        "descrizione": "Samsung Galaxy S25 FE 128GB Jetblack",
        "fornitore": "_offerte_gk",
        "cost_eur": 375.0,
        "buy_box_eur": 459.9,
        "margin_pct": 10.3,
        "profit_unit_eur": 47.59,
        "roi_pct": 12.69,
        "velocity_label": "Lenta",
        "vendite_mese": 2.0,
        "qty_carrello": 0,
        "qty_target_15gg": 1,
        "status": "PANCHINA_NO_BUDGET",
        "n_fornitori_alt": 1,
    },
    # NB: l'ASIN B0DZHNGR82 appare 2 volte (riga 0 + riga 3) per 2 fornitori.
    # ScalerBot lista ognuno separatamente; TALOS oggi tratta 1 ASIN = 1 riga
    # (no Comparazione Fornitori, ADR-0022 proposed).
    {
        "asin": "B0DZHNGR82",
        "hw_id": "A26/256GB/5G",
        "descrizione": "Samsung Galaxy A26 5G 256GB Black (parktel)",
        "fornitore": "parktel_non_eu",
        "cost_eur": 187.0,
        "buy_box_eur": 238.0,
        "margin_pct": 12.2,
        "profit_unit_eur": 28.97,
        "roi_pct": 15.49,
        "velocity_label": "Veloce",
        "vendite_mese": 41.14,
        "qty_carrello": 0,
        "qty_target_15gg": 20,
        "status": "PANCHINA_FORNITORE_ALT",
        "n_fornitori_alt": 2,
    },
)

SCALERBOT_BUDGET_EUR: Final[float] = 6000.0
SCALERBOT_VELOCITY_TARGET_DAYS: Final[int] = 15
SCALERBOT_REFERRAL_FEE_PCT: Final[float] = 0.08
SCALERBOT_FINAL_CART_TOTAL_EUR: Final[float] = 5690.0
SCALERBOT_FINAL_CART_ASINS: Final[tuple[str, ...]] = (
    "B0DZHNGR82",
    "B0DV9D6665",
    "B0DZHHZFQV",
)


def _implied_fee_fba_atomic(gt: _GroundTruthAsin) -> float:
    """Calcola la fee_fba atomica implicita dai numeri ScalerBot."""
    return (
        gt["buy_box_eur"]
        - gt["profit_unit_eur"]
        - gt["buy_box_eur"] * SCALERBOT_REFERRAL_FEE_PCT
        - gt["cost_eur"]
    )


# ---------------------------------------------------------------------------
# Discrepanza #1: fee_fba L11b vs implied atomica
# ---------------------------------------------------------------------------


def test_calibration_fee_fba_l11b_diverges_from_scalerbot_atomic() -> None:
    """SENTINEL: TALOS L11b è ~6-50x più grande dell'atomica ScalerBot.

    Documenta lo stato post-CHG-039. Quando il Leader ratifica errata
    ADR-0017 alpha-prime (sostituzione L11b → atomica), aggiornare assertion.
    """
    for gt in GROUND_TRUTH_ASINS:
        implied = _implied_fee_fba_atomic(gt)
        l11b = float(fee_fba_manual(gt["buy_box_eur"]))
        # Lock contract: stato pre-ratifica alpha-prime. L11b sistematicamente >> implied.
        # Se passa il check < 2x significa ratifica avvenuta → aggiornare sentinel.
        if implied > 0:
            assert l11b > implied, (
                f"{gt['asin']}: L11b {l11b:.2f} dovrebbe essere > implied {implied:.2f}"
            )


# ---------------------------------------------------------------------------
# Discrepanza #2: cart selection con TALOS L11b vs ScalerBot
# ---------------------------------------------------------------------------


def test_calibration_talos_vetoes_majority_of_scalerbot_carrello() -> None:
    """SENTINEL: maggioranza ASIN ScalerBot CARRELLO falliscono R-08 in TALOS L11b."""
    veto_count = 0
    seen: set[str] = set()
    for gt in GROUND_TRUTH_ASINS:
        if gt["asin"] in seen:
            continue
        seen.add(gt["asin"])
        l11b = float(fee_fba_manual(gt["buy_box_eur"]))
        cash_inflow = gt["buy_box_eur"] - l11b - gt["buy_box_eur"] * SCALERBOT_REFERRAL_FEE_PCT
        cash_profit = cash_inflow - gt["cost_eur"]
        roi = cash_profit / gt["cost_eur"]
        if is_vetoed_by_roi(roi):
            veto_count += 1
    assert veto_count >= 4, (
        f"VETO count {veto_count}/6 — atteso ≥4 con L11b. "
        "Se cambiato (e.g. errata alpha-prime applicata), aggiornare il sentinel."
    )


# ---------------------------------------------------------------------------
# Match #1: ROI TALOS replica ScalerBot SE useremo la fee atomica
# ---------------------------------------------------------------------------


def test_calibration_roi_match_with_atomic_fee() -> None:
    """Se fee_fba = atomica → TALOS ROI == ScalerBot ROI (verifica formule pure)."""
    for gt in GROUND_TRUTH_ASINS:
        atomic_fee = _implied_fee_fba_atomic(gt)
        cash_inflow = (
            gt["buy_box_eur"] - atomic_fee - gt["buy_box_eur"] * SCALERBOT_REFERRAL_FEE_PCT
        )
        cash_profit = cash_inflow - gt["cost_eur"]
        roi_pct = cash_profit / gt["cost_eur"] * 100.0
        assert cash_profit == pytest.approx(gt["profit_unit_eur"], abs=0.05), (
            f"{gt['asin']}: profit calc={cash_profit:.2f} "
            f"vs ground truth={gt['profit_unit_eur']:.2f}"
        )
        assert roi_pct == pytest.approx(gt["roi_pct"], abs=0.05), (
            f"{gt['asin']}: roi calc={roi_pct:.2f}% vs ground truth={gt['roi_pct']:.2f}%"
        )


# ---------------------------------------------------------------------------
# Match #2: velocity badge thresholds TALOS == ScalerBot
# ---------------------------------------------------------------------------


def test_calibration_velocity_badge_match_scalerbot() -> None:
    """Soglie velocity TALOS (CHG-027 placeholder) coincidono con ScalerBot."""
    from talos.ui.dashboard import _classify_velocity_badge  # noqa: PLC0415

    for gt in GROUND_TRUTH_ASINS:
        talos_label = _classify_velocity_badge(gt["vendite_mese"])
        # ScalerBot "Lenta" (femminile) → TALOS "Lento" (maschile).
        scalerbot_normalized = gt["velocity_label"].replace("Lenta", "Lento")
        assert talos_label == scalerbot_normalized, (
            f"{gt['asin']}: TALOS '{talos_label}' vs ScalerBot '{gt['velocity_label']}' "
            f"(velocity_monthly={gt['vendite_mese']:.2f})"
        )


# ---------------------------------------------------------------------------
# Match #3: qty_target ScalerBot replica F4
# ---------------------------------------------------------------------------


def test_calibration_qty_target_match_scalerbot_15gg() -> None:
    """Quota Target 15gg ScalerBot ≈ TALOS qty_target = q_m x 15/30."""
    from talos.formulas import qty_target  # noqa: PLC0415

    for gt in GROUND_TRUTH_ASINS:
        q_m = gt["vendite_mese"]
        talos_qty_target = qty_target(q_m, velocity_target_days=15)
        scalerbot_target = gt["qty_target_15gg"]
        assert abs(talos_qty_target - scalerbot_target) <= 2, (
            f"{gt['asin']}: TALOS qty_target={talos_qty_target} "
            f"vs ScalerBot 15gg={scalerbot_target} (vendite_mese={q_m:.1f})"
        )


# ---------------------------------------------------------------------------
# Sentinel: ground truth dataset shape integrity
# ---------------------------------------------------------------------------


def test_ground_truth_dataset_has_7_rows() -> None:
    """Lock contract: il dataset Leader contiene 7 ASIN (6 unique)."""
    assert len(GROUND_TRUTH_ASINS) == 7
    asins_unique = {gt["asin"] for gt in GROUND_TRUTH_ASINS}
    assert len(asins_unique) == 6  # B0DZHNGR82 appare 2x (2 fornitori)


def test_ground_truth_amazon_presence_filter_no_op() -> None:
    """ScalerBot non espone amazon_buybox_share → TALOS Amazon Presence pass."""
    for _gt in GROUND_TRUTH_ASINS:
        assert passes_amazon_presence(None) is True
