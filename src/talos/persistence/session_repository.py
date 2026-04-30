"""Repository: persiste `SessionResult` in DB (ADR-0015).

Mappa l'output dell'orchestratore (CHG-2026-04-30-039) sulle tabelle
Allegato A:

- `AnalysisSession` (header: budget, velocity_target, listino_hash, tenant_id)
- `ListinoItem` x N (riga listino raw originale)
- `VgpResult` x N (riga enriched_df: roi/velocity/cash_profit + norm + score + flag)
- `CartItem` x M (item allocati nel Cart)
- `PanchinaItem` x P (idonei scartati per cassa)

**Vincoli RLS** (ADR-0015): la scrittura avviene sotto `with_tenant(session,
tenant_id)`. Le tabelle sopra non hanno policy RLS attiva (RLS solo su
`config_overrides`, `locked_in`, `storico_ordini`); il `with_tenant` qui e'
**preventivo** per scenari futuri in cui la stessa transazione possa
toccare anche tabelle RLS-protected — e per consistenza Zero-Trust.

`tenant_id` viene materializzato sulla riga `AnalysisSession.tenant_id`
(default schema = 1, MVP single-tenant). Le tabelle child derivano il
tenant via FK transitiva (no campo `tenant_id` propagato).

Scope MVP:
- **No update / delete**: solo `save`. Storico e' append-only.
- **No idempotency**: il listino_hash NON e' UNIQUE; ri-eseguire la
  stessa sessione crea una nuova `AnalysisSession`. Idempotency e' scope
  CHG futuro (`upsert_session` con `ON CONFLICT (listino_hash) DO ...`).
- **No load / list**: scope CHG futuro (`load_session_by_id`,
  `list_recent_sessions(limit)`).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from talos.persistence.models import (
    AnalysisSession,
    CartItem,
    ListinoItem,
    PanchinaItem,
    VgpResult,
)
from talos.persistence.session import with_tenant

if TYPE_CHECKING:
    import pandas as pd
    from sqlalchemy.orm import Session

    from talos.orchestrator import SessionInput, SessionResult


def _listino_hash(listino_raw: pd.DataFrame) -> str:
    """sha256 deterministico del listino raw (32 bytes hex = 64 char).

    Usa `to_csv` con header + index off + sort_index per minimizzare
    drift tra run identici. Il risultato e' stabile per ordine colonne
    + valori; modifica di 1 cell -> hash diverso.
    """
    # Ordina le colonne alfabeticamente per stabilita' tra run con ordini diversi.
    sorted_df = listino_raw.reindex(sorted(listino_raw.columns), axis=1)
    csv_str = sorted_df.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(csv_str.encode("utf-8")).hexdigest()


def _to_decimal_or_none(value: float | None) -> Decimal | None:
    """Convert float -> Decimal con `str()` (no binary drift). None passa."""
    if value is None:
        return None
    return Decimal(str(value))


def save_session_result(
    db_session: Session,
    *,
    session_input: SessionInput,
    result: SessionResult,
    tenant_id: int = 1,
) -> int:
    """Persiste `SessionResult` in DB e ritorna `analysis_session.id`.

    :param db_session: SQLAlchemy `Session` aperta. Il commit/rollback e'
        responsabilita' del caller (tipicamente via `session_scope`).
    :param session_input: input originale di `run_session` (per
        budget/velocity/hash).
    :param result: output di `run_session` (cart/panchina/budget_t1/enriched_df).
    :param tenant_id: tenant per `with_tenant` + colonna
        `analysis_session.tenant_id`. Default 1 (MVP single-tenant).
    :returns: id della `AnalysisSession` creata.
    """
    with with_tenant(db_session, tenant_id):
        # 1. Header sessione.
        analysis_session = AnalysisSession(
            budget_eur=Decimal(str(session_input.budget)),
            velocity_target=session_input.velocity_target_days,
            listino_hash=_listino_hash(session_input.listino_raw),
            tenant_id=tenant_id,
        )
        db_session.add(analysis_session)
        db_session.flush()  # genera analysis_session.id

        # 2. ListinoItem per ogni riga raw + map asin -> listino_item_id.
        listino_id_by_asin: dict[str, int] = {}
        for _, row in session_input.listino_raw.iterrows():
            asin = str(row["asin"])
            li = ListinoItem(
                session_id=analysis_session.id,
                asin=asin,
                # `raw_title` placeholder finche' l'extractor non emette titoli reali.
                raw_title=f"ASIN:{asin}",
                cost_eur=Decimal(str(row["cost_eur"])),
                qty_available=int(row["v_tot"]) if "v_tot" in row else None,
                match_status=str(row["match_status"]) if "match_status" in row else None,
                match_reason=None,
            )
            db_session.add(li)
            db_session.flush()
            listino_id_by_asin[asin] = li.id

        # 3. VgpResult per ogni riga enriched + map asin -> vgp_result_id.
        vgp_id_by_asin: dict[str, int] = {}
        for _, row in result.enriched_df.iterrows():
            asin = str(row["asin"])
            vr = VgpResult(
                session_id=analysis_session.id,
                listino_item_id=listino_id_by_asin[asin],
                asin=asin,
                roi_pct=_to_decimal_or_none(float(row["roi"])),
                velocity_monthly=_to_decimal_or_none(float(row["velocity_monthly"])),
                cash_profit_eur=_to_decimal_or_none(float(row["cash_profit_eur"])),
                roi_norm=_to_decimal_or_none(float(row["roi_norm"])),
                velocity_norm=_to_decimal_or_none(float(row["velocity_norm"])),
                cash_profit_norm=_to_decimal_or_none(float(row["cash_profit_norm"])),
                vgp_score=_to_decimal_or_none(float(row["vgp_score"])),
                veto_roi_passed=bool(row["veto_roi_passed"]),
                kill_switch_triggered=bool(row["kill_mask"]),
                qty_target=int(row["qty_target"]),
                qty_final=int(row["qty_final"]),
            )
            db_session.add(vr)
            db_session.flush()
            vgp_id_by_asin[asin] = vr.id

        # 4. CartItem per ogni item allocato.
        for item in result.cart.items:
            unit_cost = (item.cost_total / item.qty) if item.qty > 0 else 0.0
            ci = CartItem(
                session_id=analysis_session.id,
                vgp_result_id=vgp_id_by_asin[item.asin],
                qty=item.qty,
                unit_cost_eur=Decimal(str(unit_cost)),
                locked_in=item.locked,
            )
            db_session.add(ci)

        # 5. PanchinaItem per ogni riga in panchina.
        for _, row in result.panchina.iterrows():
            asin = str(row["asin"])
            pi = PanchinaItem(
                session_id=analysis_session.id,
                vgp_result_id=vgp_id_by_asin[asin],
                qty_proposed=int(row["qty_final"]),
            )
            db_session.add(pi)

        # 6. Marca sessione conclusa.
        analysis_session.ended_at = datetime.now(tz=UTC)
        db_session.flush()

        return int(analysis_session.id)
