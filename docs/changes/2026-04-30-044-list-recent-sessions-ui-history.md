---
id: CHG-2026-04-30-044
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0015, ADR-0016, ADR-0014, ADR-0019
---

## What

Aggiunge il **read-side** della pipeline DB: `list_recent_sessions` per
listare sessioni storiche del tenant + integrazione UI con expander
"Storico Sessioni (lista recente)".

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/session_repository.py` | modificato | +`SessionSummary` frozen dataclass (id, started_at, ended_at, budget_eur, velocity_target, listino_hash, n_cart_items, n_panchina_items) + `list_recent_sessions(db_session, *, limit=20, tenant_id=1) -> list[SessionSummary]` con subquery `count()` aggregati e tiebreaker `id DESC` su `started_at` (mitigazione `now()` collision) |
| `src/talos/persistence/__init__.py` | modificato | +re-export `SessionSummary`, `list_recent_sessions` |
| `src/talos/ui/dashboard.py` | modificato | +`fetch_recent_sessions_or_empty(factory, *, limit, tenant_id) -> list[dict]` (graceful empty su error) + `_render_history(factory, tenant_id, limit)` con `st.expander` + `st.dataframe` |
| `src/talos/ui/__init__.py` | modificato | +re-export `fetch_recent_sessions_or_empty` |
| `tests/integration/test_list_recent_sessions.py` | nuovo | 8 test (lista vuota, summary post-save, ordering DESC con tiebreaker, limit, invalid limit raise, filtro tenant_id, count aggregati, fetch_recent_sessions_or_empty schema dict) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | entry `session_repository.py` aggiornata |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **409 PASS**
(369 unit/governance/golden + 40 integration).

## Why

CHG-042/043 hanno chiuso il loop **WRITE** (memory→DB). Senza il loop
**READ**, il CFO salva sessioni ma non puo' rivederle: storico
inaccessibile, confronti impossibili. La pagina "Storico" e' il
prerequisito per:
- Audit ("quando ho eseguito quella sessione e con che budget?")
- Compounding inter-sessione futuro ("carica Budget_T+1 da sessione X")
- Demo CFO completa ("vedi cosa ha fatto il sistema le ultime 20 volte")

### Decisioni di design

1. **`SessionSummary` separato da `AnalysisSession`**: il modello ORM
   ha relationships pesanti (carica children al touch). `SessionSummary`
   e' un DTO leggero per liste — frozen dataclass, no I/O lazy. Pattern
   coerente con `SessionInput`/`SessionResult` (CHG-039).
2. **Aggregazione via subquery `count()` JOIN**: alternativa
   `selectinload` di SQLAlchemy carica TUTTE le righe child, costoso su
   liste storiche di 100+ sessioni. Subquery aggregata = 1 row per
   sessione, conteggio in DB.
3. **Tiebreaker `id DESC` su `started_at`**: i test hanno scoperto che
   due insert in rapida successione hanno lo stesso `now()` (precisione
   sub-ms). Senza tiebreaker l'ordering e' indeterminato. `id`
   sequence-generated e' monotonic = tiebreaker stabile. Documentato
   in commento del codice.
4. **`fetch_recent_sessions_or_empty` lato UI**: separa "ottenere lista"
   da "renderizzare". Ritorna `list[dict]` consumabile da
   `pd.DataFrame` per `st.dataframe`. Graceful: try/except cattura
   query failure (DB temporaneo down) → lista vuota. UI nice-to-have,
   non critica.
5. **Hash troncato a 12 char + "..."** in UI: il sha256 hex 64-char e'
   illeggibile in tabella. La UI mostra prefix; il caller che vuole
   match esatto ha l'oggetto `SessionSummary` completo.
6. **`tenant_id` filter applicativo + `with_tenant` SQL session var**:
   doppia barriera. La WHERE clause garantisce filtro deterministico;
   `with_tenant` e' future-proof per RLS.

### Out-of-scope

- **`load_session_by_id`** (ricostruzione full `SessionResult` con cart +
  panchina + enriched_df): scope CHG futuro (CHG-045?). Richiede join
  multi-tabella + ricostruzione `pd.DataFrame` da `VgpResult` + `Cart`
  da `CartItem`.
- **Bottone "Ricarica sessione"** in UI: scope CHG futuro post
  `load_session_by_id`.
- **Search / filter** nella lista (per data range, hash, budget): scope
  futuro quando emergeranno >50 sessioni.
- **Pagination**: limit-based; pagination keyset-based e' scope futuro
  se le sessioni esplodono.
- **Sorting in UI** (click su colonna): Streamlit `st.dataframe` ha
  sorting client-side built-in, sufficiente per MVP.

## How

### `list_recent_sessions` (highlight)

```python
def list_recent_sessions(
    db_session: Session, *, limit: int = 20, tenant_id: int = 1,
) -> list[SessionSummary]:
    if limit <= 0:
        raise ValueError(...)
    with with_tenant(db_session, tenant_id):
        cart_count_sq = (
            select(CartItem.session_id, func.count().label("n_cart"))
            .group_by(CartItem.session_id).subquery()
        )
        panch_count_sq = (
            select(PanchinaItem.session_id, func.count().label("n_panch"))
            .group_by(PanchinaItem.session_id).subquery()
        )
        stmt = (
            select(AnalysisSession,
                   func.coalesce(cart_count_sq.c.n_cart, 0),
                   func.coalesce(panch_count_sq.c.n_panch, 0))
            .outerjoin(cart_count_sq, ...)
            .outerjoin(panch_count_sq, ...)
            .where(AnalysisSession.tenant_id == tenant_id)
            .order_by(AnalysisSession.started_at.desc(),
                      AnalysisSession.id.desc())
            .limit(limit)
        )
        rows = db_session.execute(stmt).all()
        return [SessionSummary(...) for asession, n_cart, n_panch in rows]
```

### Test plan (8 integration)

1. `test_list_returns_empty_for_unused_tenant` — tenant 999 vuoto
2. `test_list_returns_session_summary_after_save` — round-trip save → list
3. `test_list_orders_by_started_at_desc` — ordering con tiebreaker `id`
4. `test_list_respects_limit` — limit=2 cap
5. `test_list_invalid_limit_raises` — 0/-5 → ValueError
6. `test_list_filters_by_tenant_id` — isolamento t1 vs t2
7. `test_list_n_cart_items_matches_actual_count` — aggregati correttiz
8. `test_fetch_recent_sessions_or_empty_returns_dicts` — UI helper schema

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 84 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **369 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **40 PASS** |

**Rischi residui:**
- **No idempotency `(tenant_id, listino_hash)` UNIQUE**: ri-eseguire
  stessa sessione crea righe duplicate in `sessions`. Documentato come
  out-of-scope; UI mostra il duplicato finche' `UNIQUE(listino_hash)`
  migration non arrivera'.
- **Subquery count su `cart_items`/`panchina_items` puo' essere lenta**
  su tabelle grandi. Indici esistenti su `session_id` (FK) mitigano.
  Profile post-MVP se emerge.
- **N+1 sui DTO**: la list comprehension finale itera N righe; ognuna
  costruisce un `SessionSummary`. Costo trascurabile per limit=20.
- **CHAR(64) hash padding**: `listino_hash` e' CHAR(64) — Postgres NON
  padda con spazi se la stringa e' esattamente 64 char. sha256 hex e'
  sempre 64 → niente quirk come per CHAR(10) ASIN.

## Impact

**🎯 Loop READ chiuso**: il CFO ora puo' eseguire → vedere → salvare →
**RILEGGERE** lo storico. Per la prima volta una sessione persistita ha
visibilita' nella UI.

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze`
i nuovi simboli `SessionSummary`, `list_recent_sessions`,
`fetch_recent_sessions_or_empty`, `_render_history`.

## Refs

- ADR: ADR-0015 (persistenza), ADR-0016 (UI Streamlit), ADR-0014
  (mypy/ruff strict), ADR-0019 (test integration pattern)
- Predecessori: CHG-2026-04-30-042 (save_session_result), CHG-2026-04-30-043
  (UI persistence integration)
- Successore atteso: CHG-045 `load_session_by_id` + bottone "Ricarica
  sessione" UI; `UNIQUE(listino_hash)` migration + upsert
- Commit: `[pending]`
