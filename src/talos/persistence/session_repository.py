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
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import func, select

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


@dataclass(frozen=True)
class SessionSummary:
    """Vista compatta di una sessione storica per UI lista (CHG-2026-04-30-044).

    Aggrega via SQL `count()` i child relevanti, evitando di materializzare
    tutte le righe `vgp_results` / `cart_items` / `panchina_items` per la
    pagina "storico".
    """

    id: int
    started_at: datetime
    ended_at: datetime | None
    budget_eur: Decimal
    velocity_target: int
    listino_hash: str
    n_cart_items: int
    n_panchina_items: int


@dataclass(frozen=True)
class LoadedSession:
    """Sessione ricaricata dal DB per UI dettaglio (CHG-2026-04-30-045).

    Contiene il riepilogo della sessione + le righe di `cart_items` e
    `panchina_items` arricchite con i campi rilevanti dei `vgp_results`
    (asin, vgp_score, roi). Pensata per `st.dataframe` UI.

    Differenza vs `SessionResult` (orchestrator): questo e' il **read-side**
    del DB, niente `pd.DataFrame` enriched ne' `Cart` con metodi
    `saturation`/`remaining`. Ricostruzione full e' scope CHG futuro
    (`load_session_full` se serve).
    """

    summary: SessionSummary
    cart_rows: list[dict[str, object]]
    panchina_rows: list[dict[str, object]]


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


def load_session_by_id(
    db_session: Session,
    session_id: int,
    *,
    tenant_id: int = 1,
) -> LoadedSession | None:
    """Ricarica una sessione dal DB. Ritorna `None` se non esiste o tenant mismatch.

    :param db_session: SQLAlchemy `Session` aperta.
    :param session_id: id `AnalysisSession` da caricare.
    :param tenant_id: filtro tenant (la sessione deve appartenervi). Default 1.
    :returns: `LoadedSession` con summary + cart_rows + panchina_rows
        oppure `None` se la sessione non esiste o appartiene a un altro tenant.
    :raises ValueError: se `session_id <= 0`.
    """
    if session_id <= 0:
        msg = f"session_id invalido: {session_id}. Deve essere > 0."
        raise ValueError(msg)

    with with_tenant(db_session, tenant_id):
        asession = db_session.get(AnalysisSession, session_id)
        if asession is None or asession.tenant_id != tenant_id:
            return None

        # Conteggi per il summary.
        n_cart = db_session.scalar(
            select(func.count()).select_from(CartItem).where(CartItem.session_id == session_id),
        )
        n_panch = db_session.scalar(
            select(func.count())
            .select_from(PanchinaItem)
            .where(PanchinaItem.session_id == session_id),
        )
        summary = SessionSummary(
            id=int(asession.id),
            started_at=asession.started_at,
            ended_at=asession.ended_at,
            budget_eur=asession.budget_eur,
            velocity_target=asession.velocity_target,
            listino_hash=asession.listino_hash,
            n_cart_items=int(n_cart or 0),
            n_panchina_items=int(n_panch or 0),
        )

        # Cart rows (JOIN con vgp_results per asin/score).
        cart_stmt = (
            select(CartItem, VgpResult.asin, VgpResult.vgp_score, VgpResult.roi_pct)
            .join(VgpResult, CartItem.vgp_result_id == VgpResult.id)
            .where(CartItem.session_id == session_id)
            .order_by(CartItem.id.asc())
        )
        cart_rows: list[dict[str, object]] = []
        for cart_item, asin, vgp_score, roi_pct in db_session.execute(cart_stmt).all():
            cart_rows.append(
                {
                    "asin": (asin or "").strip(),  # CHAR(10) padding
                    "qty": cart_item.qty,
                    "unit_cost_eur": float(cart_item.unit_cost_eur),
                    "cost_total": float(cart_item.unit_cost_eur) * cart_item.qty,
                    "vgp_score": float(vgp_score) if vgp_score is not None else 0.0,
                    "roi": float(roi_pct) if roi_pct is not None else 0.0,
                    "locked": bool(cart_item.locked_in),
                },
            )

        # Panchina rows (JOIN con vgp_results).
        panch_stmt = (
            select(PanchinaItem, VgpResult.asin, VgpResult.vgp_score, VgpResult.roi_pct)
            .join(VgpResult, PanchinaItem.vgp_result_id == VgpResult.id)
            .where(PanchinaItem.session_id == session_id)
            .order_by(VgpResult.vgp_score.desc())
        )
        panchina_rows: list[dict[str, object]] = []
        for panch, asin, vgp_score, roi_pct in db_session.execute(panch_stmt).all():
            panchina_rows.append(
                {
                    "asin": (asin or "").strip(),
                    "qty_proposed": panch.qty_proposed,
                    "vgp_score": float(vgp_score) if vgp_score is not None else 0.0,
                    "roi": float(roi_pct) if roi_pct is not None else 0.0,
                },
            )

        return LoadedSession(
            summary=summary,
            cart_rows=cart_rows,
            panchina_rows=panchina_rows,
        )


def find_session_by_hash(
    db_session: Session,
    *,
    listino_hash: str,
    tenant_id: int = 1,
) -> SessionSummary | None:
    """Cerca una `AnalysisSession` per `(tenant_id, listino_hash)`.

    Sfrutta l'UNIQUE INDEX `ux_sessions_tenant_hash` (CHG-2026-04-30-047)
    per lookup O(log N). Pattern d'uso tipico: la UI controlla pre-save
    se il listino e' gia' stato eseguito, mostra warning ed evita
    duplicati silenziosi.

    :param db_session: SQLAlchemy `Session` aperta.
    :param listino_hash: hash sha256 hex del listino (output di `_listino_hash`).
    :param tenant_id: tenant filter. Default 1 (MVP single-tenant).
    :returns: `SessionSummary` con counts aggregati, oppure `None` se
        nessuna sessione del tenant ha quel hash.
    :raises ValueError: se `listino_hash` non e' lungo 64 (sha256 hex).
    """
    expected_hash_length = 64
    if len(listino_hash) != expected_hash_length:
        msg = (
            f"listino_hash invalido: lunghezza {len(listino_hash)} != "
            f"{expected_hash_length} (sha256 hex)."
        )
        raise ValueError(msg)

    with with_tenant(db_session, tenant_id):
        stmt = select(AnalysisSession).where(
            AnalysisSession.tenant_id == tenant_id,
            AnalysisSession.listino_hash == listino_hash,
        )
        asession = db_session.scalar(stmt)
        if asession is None:
            return None

        n_cart = db_session.scalar(
            select(func.count()).select_from(CartItem).where(CartItem.session_id == asession.id),
        )
        n_panch = db_session.scalar(
            select(func.count())
            .select_from(PanchinaItem)
            .where(PanchinaItem.session_id == asession.id),
        )
        return SessionSummary(
            id=int(asession.id),
            started_at=asession.started_at,
            ended_at=asession.ended_at,
            budget_eur=asession.budget_eur,
            velocity_target=asession.velocity_target,
            listino_hash=asession.listino_hash,
            n_cart_items=int(n_cart or 0),
            n_panchina_items=int(n_panch or 0),
        )


def list_recent_sessions(
    db_session: Session,
    *,
    limit: int = 20,
    tenant_id: int = 1,
) -> list[SessionSummary]:
    """Lista le sessioni piu' recenti per il `tenant_id`, ordinate per `started_at` DESC.

    Aggrega `n_cart_items` e `n_panchina_items` via subquery `count()`,
    senza caricare le righe child. Adatta a UI lista riepilogativa.

    :param db_session: SQLAlchemy `Session` aperta.
    :param limit: numero massimo di righe da ritornare. Default 20.
    :param tenant_id: filtro tenant (RLS-compatibile). Default 1 (MVP).
    :returns: lista (eventualmente vuota) di `SessionSummary` ordinati per
        `started_at` DESC.
    :raises ValueError: se `limit <= 0`.
    """
    if limit <= 0:
        msg = f"limit invalido: {limit}. Deve essere > 0."
        raise ValueError(msg)

    with with_tenant(db_session, tenant_id):
        cart_count_sq = (
            select(CartItem.session_id, func.count().label("n_cart"))
            .group_by(CartItem.session_id)
            .subquery()
        )
        panch_count_sq = (
            select(PanchinaItem.session_id, func.count().label("n_panch"))
            .group_by(PanchinaItem.session_id)
            .subquery()
        )

        stmt = (
            select(
                AnalysisSession,
                func.coalesce(cart_count_sq.c.n_cart, 0).label("n_cart"),
                func.coalesce(panch_count_sq.c.n_panch, 0).label("n_panch"),
            )
            .outerjoin(cart_count_sq, cart_count_sq.c.session_id == AnalysisSession.id)
            .outerjoin(panch_count_sq, panch_count_sq.c.session_id == AnalysisSession.id)
            .where(AnalysisSession.tenant_id == tenant_id)
            # `started_at` ha server_default `now()`: due insert in rapida
            # successione possono avere timestamp identico. Tiebreaker `id`
            # (sequence-generated, monotonic) garantisce ordering stabile.
            .order_by(AnalysisSession.started_at.desc(), AnalysisSession.id.desc())
            .limit(limit)
        )

        rows = db_session.execute(stmt).all()
        return [
            SessionSummary(
                id=int(asession.id),
                started_at=asession.started_at,
                ended_at=asession.ended_at,
                budget_eur=asession.budget_eur,
                velocity_target=asession.velocity_target,
                listino_hash=asession.listino_hash,
                n_cart_items=int(n_cart),
                n_panchina_items=int(n_panch),
            )
            for asession, n_cart, n_panch in rows
        ]
