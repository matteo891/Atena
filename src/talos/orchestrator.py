"""Orchestratore di sessione end-to-end (ADR-0018).

Compone i building block scalari + vettoriali in un'unica funzione
`run_session(SessionInput) -> SessionResult` che produce i due output
canonici di sessione: `Cart` (R-06 + R-04) e `panchina_df` (R-09),
con il `Budget_T+1` (F3 R-07) gia' calcolato.

Pipeline interna:
1. **Enrichment** del listino raw (F1 cash_inflow, F2 cash_profit, ROI,
   F4.A q_m, F4 qty_target, F5 qty_final, velocity_monthly, kill_mask).
   Usa le funzioni scalari come single-source-of-truth (CHG-022/025/026/038).
2. **Score**: `compute_vgp_score` (CHG-035) applica formula composita +
   R-05 + R-08.
3. **Sort** per `vgp_score` DESC (contratto allocator).
4. **Tetris**: `allocate_tetris` (CHG-036) Pass 1 R-04 + Pass 2 R-06.
5. **Panchina**: `build_panchina` (CHG-037) R-09 archivio idonei scartati.
6. **Compounding**: `compounding_t1` (CHG-032) su `cash_profit_eur * qty`
   per gli ASIN allocati nel cart. Il "100% reinvestibile" (R-07) si
   applica solo agli allocati: gli scartati restano in panchina, non
   contribuiscono al budget T+1.

Posizionamento (gap ADR risolto 2026-04-30): file top-level
`src/talos/orchestrator.py`, non directory. Conforme al Test di
Conformita' #1 di ADR-0013 (`find -type d` non vede file). L'orchestratore
e' un *coordinatore* dei cluster esistenti, non un nuovo cluster.

Versione "happy path" senza:
- Telemetria evento `session_started` / `tetris_break_saturation`
  (richiede structlog dispatch, scope ADR-0021 successivo).
- Persistenza DB di `SessionResult` (scope `persistence/`).
- UI Streamlit (scope ADR-0016 ui).
- Versione vettoriale full degli enrichment (uses `apply` per single-
  source-of-truth con le funzioni scalari; promotion vettoriale e' errata
  futura ADR-0018 quando profiling lo richiedera' su 10k righe).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from talos.formulas import (
    DEFAULT_LOT_SIZE,
    DEFAULT_VELOCITY_TARGET_DAYS,
    cash_inflow_eur,
    cash_profit_eur,
    compounding_t1,
    fee_fba_manual,
    q_m,
    qty_final,
    qty_target,
    roi,
    velocity_monthly,
)
from talos.tetris import (
    Cart,
    allocate_tetris,
    build_panchina,
)
from talos.vgp import DEFAULT_ROI_VETO_THRESHOLD, compute_vgp_score

if TYPE_CHECKING:
    import pandas as pd


# Status di match (output futuro di `extract/`) che attivano R-05 KILL-SWITCH.
# Il caller (extractor) emette uno status nominale; l'orchestratore lo traduce
# in kill_mask vettoriale per `compute_vgp_score`.
KILLED_STATUSES: Final[tuple[str, ...]] = ("KILLED", "MISMATCH")

# Colonne richieste nel listino raw (input dell'orchestratore).
# La nomenclatura ricalca PROJECT-RAW.md sez. 6.2 + Allegato A di ADR-0015
# (`listino_items` table) per facilitare la mappatura DB->df.
REQUIRED_INPUT_COLUMNS: Final[tuple[str, ...]] = (
    "asin",
    "buy_box_eur",
    "cost_eur",
    "referral_fee_pct",
    "v_tot",
    "s_comp",
    "match_status",
)


@dataclass(frozen=True)
class SessionInput:
    """Input per `run_session`. Dataclass frozen = immutabile = cacheable."""

    listino_raw: pd.DataFrame
    budget: float
    locked_in: list[str] = field(default_factory=list)
    velocity_target_days: int = DEFAULT_VELOCITY_TARGET_DAYS
    veto_roi_threshold: float = DEFAULT_ROI_VETO_THRESHOLD
    lot_size: int = DEFAULT_LOT_SIZE


@dataclass(frozen=True)
class SessionResult:
    """Output canonico di sessione.

    `enriched_df` contiene il listino completo post-enrichment + score
    (utile per audit/UI dettaglio). `cart` e `panchina` sono i due
    output principali. `budget_t1` e' il capitale reinvestibile alla
    sessione successiva (R-07 verbatim).
    """

    cart: Cart
    panchina: pd.DataFrame
    budget_t1: float
    enriched_df: pd.DataFrame


def _empty_scored_df() -> pd.DataFrame:
    """DataFrame vuoto con le colonne attese da `allocate_tetris`/`build_panchina`.

    Edge case: listino input vuoto. Le funzioni downstream richiedono colonne
    `asin`, `cost_eur`, `qty_final`, `vgp_score`; le iniziamo a dtype corretto.
    """
    import pandas as pd  # noqa: PLC0415 — runtime usage in fallback path

    return pd.DataFrame(
        {
            "asin": pd.Series([], dtype=str),
            "cost_eur": pd.Series([], dtype=float),
            "qty_final": pd.Series([], dtype=int),
            "vgp_score": pd.Series([], dtype=float),
        },
    )


def _enrich_listino(
    listino_raw: pd.DataFrame,
    *,
    velocity_target_days: int,
    lot_size: int,
) -> pd.DataFrame:
    """Aggiunge le colonne calcolate al listino raw via funzioni scalari.

    Single-source-of-truth: ogni cella deriva esattamente dallo stesso
    codice testato in CHG-022/025/026/038. Se una formula cambia, il
    test di quella formula scoppia e l'enrichment automaticamente.

    Performance note: `apply` row-wise e' ~10-100x piu' lento del
    vettoriale puro su 10k righe. Vincolo 8.1 ADR-0018 (<500ms su 10k)
    sara' rivisitato post-MVP via errata corrige se profiling lo
    impone. Per Samsung MVP (~100-500 righe) il costo e' trascurabile.
    """
    out = listino_raw.copy()
    out["fee_fba_eur"] = out["buy_box_eur"].apply(fee_fba_manual)
    out["cash_inflow_eur"] = out.apply(
        lambda r: cash_inflow_eur(
            buy_box_eur=float(r["buy_box_eur"]),
            fee_fba_eur=float(r["fee_fba_eur"]),
            referral_fee_rate=float(r["referral_fee_pct"]),
        ),
        axis=1,
    )
    out["cash_profit_eur"] = out.apply(
        lambda r: cash_profit_eur(
            cash_inflow_eur=float(r["cash_inflow_eur"]),
            costo_fornitore_eur=float(r["cost_eur"]),
        ),
        axis=1,
    )
    out["roi"] = out.apply(
        lambda r: roi(
            cash_profit_eur=float(r["cash_profit_eur"]),
            costo_fornitore_eur=float(r["cost_eur"]),
        ),
        axis=1,
    )
    out["q_m"] = out.apply(
        lambda r: q_m(v_tot=float(r["v_tot"]), s_comp=int(r["s_comp"])),
        axis=1,
    )
    out["velocity_monthly"] = out["q_m"].apply(
        lambda v: velocity_monthly(float(v), velocity_target_days),
    )
    out["qty_target"] = out["q_m"].apply(
        lambda v: qty_target(float(v), velocity_target_days),
    )
    out["qty_final"] = out["qty_target"].apply(
        lambda v: qty_final(float(v), lot_size),
    )
    out["kill_mask"] = out["match_status"].isin(KILLED_STATUSES)
    return out


def run_session(inp: SessionInput) -> SessionResult:
    """Pipeline end-to-end di sessione: input listino raw -> output cruscotto.

    :param inp: `SessionInput` immutabile con `listino_raw` + budget +
        locked_in + parametri opzionali.
    :returns: `SessionResult` con `cart`, `panchina`, `budget_t1`,
        `enriched_df`.
    :raises ValueError: se mancano colonne richieste, budget invalido,
        threshold/days/lot fuori range.
    :raises InsufficientBudgetError: se un locked-in supera il budget
        residuo (R-04 fail-fast, propagato da `allocate_tetris`).
    """
    missing = [c for c in REQUIRED_INPUT_COLUMNS if c not in inp.listino_raw.columns]
    if missing:
        msg = (
            f"run_session: colonne richieste mancanti dal listino: {missing}. "
            f"Attese: {list(REQUIRED_INPUT_COLUMNS)}."
        )
        raise ValueError(msg)

    # Edge case: listino vuoto. `apply(axis=1)` su DataFrame vuoto ritorna
    # DataFrame (non Series), rompendo l'enrichment. Cortocircuito esplicito.
    if inp.listino_raw.empty:
        empty_cart = allocate_tetris(
            _empty_scored_df(),
            budget=inp.budget,
            locked_in=inp.locked_in,
        )
        return SessionResult(
            cart=empty_cart,
            panchina=_empty_scored_df(),
            budget_t1=compounding_t1(inp.budget, []),
            enriched_df=_empty_scored_df(),
        )

    # Step 1: enrichment (F1, F2, ROI, F4.A, F4, F5, velocity_monthly, kill_mask).
    # Le funzioni scalari raise R-01 su valori invalidi (es. fee_fba_manual su BuyBox sotto soglia).
    enriched = _enrich_listino(
        inp.listino_raw,
        velocity_target_days=inp.velocity_target_days,
        lot_size=inp.lot_size,
    )

    # Step 2: VGP score (R-05 + R-08 applicati internamente).
    scored = compute_vgp_score(
        enriched,
        roi_col="roi",
        velocity_col="velocity_monthly",
        cash_profit_col="cash_profit_eur",
        kill_col="kill_mask",
        veto_roi_threshold=inp.veto_roi_threshold,
    )

    # Step 3: sort per vgp_score DESC (contratto allocator).
    scored_sorted = scored.sort_values("vgp_score", ascending=False)

    # Step 4: Tetris allocator (R-04 + R-06).
    cart = allocate_tetris(
        scored_sorted,
        budget=inp.budget,
        locked_in=inp.locked_in,
    )

    # Step 5: Panchina (R-09).
    panchina = build_panchina(scored_sorted, cart)

    # Step 6: Compounding T+1 (F3, R-07 100% reinvestibile).
    # Cash profit di sessione = somma(cash_profit_per_unit * qty_acquistate)
    # per gli ASIN nel cart. Locked-in con vgp_score=0 (kill/veto) sono
    # allocati ma NON contribuiscono se ROI sotto soglia (forzano comunque
    # il loro cash_profit nel calcolo — R-04 prevale anche sul reinvestimento).
    cart_profits: list[float] = []
    for item in cart.items:
        match = scored_sorted[scored_sorted["asin"] == item.asin]
        if match.empty:
            # Branch impossibile per costruzione: `allocate_tetris` valida che
            # ogni ASIN allocato sia presente in `vgp_df`. Se mai si verificasse,
            # silently skipping nasconderebbe un bug di mapping interno -> raise.
            msg = (
                f"BUG interno: ASIN '{item.asin}' nel cart ma assente da "
                "scored_sorted; mapping VgpResult/Cart corrotto."
            )
            raise RuntimeError(msg)
        cash_profit_per_unit = float(match.iloc[0]["cash_profit_eur"])
        cart_profits.append(cash_profit_per_unit * item.qty)
    budget_t1 = compounding_t1(inp.budget, cart_profits)

    return SessionResult(
        cart=cart,
        panchina=panchina,
        budget_t1=budget_t1,
        enriched_df=scored_sorted,
    )
