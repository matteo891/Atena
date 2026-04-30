---
id: CHG-2026-04-30-042
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

Connette l'**intelligenza in memoria** (orchestrator/tetris) alle **tabelle
Postgres** Allegato A. Implementa `save_session_result(db_session, *,
session_input, result, tenant_id=1) -> int`: persiste l'output di
`run_session` (CHG-039) su 5 tabelle, sotto `with_tenant` per future
RLS compliance.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/session_repository.py` | nuovo | `save_session_result` + helper `_listino_hash` (sha256 deterministico) + `_to_decimal_or_none` |
| `src/talos/persistence/__init__.py` | modificato | +re-export `save_session_result` |
| `tests/integration/test_session_repository.py` | nuovo | 9 test integration su Postgres reale (header session, listino_items, vgp_results, cart_items, panchina_items, hash determinismo, custom tenant_id, return type, locked_in flag) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `session_repository.py` |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **397 PASS**
(354 unit/governance + 13 golden + **30 integration** — di cui 9 nuovi
session_repository).

## Why

Pipeline e2e (CHG-039) e UI (CHG-040) producono `SessionResult` in memoria.
Senza persistenza, ogni sessione e' effimera: il CFO non puo' confrontare
sessioni passate, lo storico ordini (R-03) non si alimenta, il `Budget_T+1`
non si propaga al prossimo run. Senza chiusura del loop architetturale, la
demo e' un giocattolo.

Mappatura `SessionResult` → 5 tabelle Allegato A:

```
SessionResult.session_input.budget        -> AnalysisSession.budget_eur
SessionResult.session_input.velocity_target_days -> AnalysisSession.velocity_target
sha256(listino_raw_csv)                   -> AnalysisSession.listino_hash
tenant_id                                 -> AnalysisSession.tenant_id

session_input.listino_raw[i]              -> ListinoItem (raw, FK session)
                                              raw_title placeholder "ASIN:<asin>"
                                              cost_eur, qty_available, match_status

result.enriched_df[i]                     -> VgpResult (FK session + listino)
                                              roi/velocity/cash_profit/norm × 3
                                              vgp_score, veto_passed, kill_triggered
                                              qty_target, qty_final

result.cart.items[i]                      -> CartItem (FK session + vgp_result)
                                              qty, unit_cost_eur, locked_in

result.panchina[i]                        -> PanchinaItem (FK session + vgp_result)
                                              qty_proposed
```

### Decisioni di design

1. **`with_tenant(db_session, tenant_id)` sempre attivo**: anche se le 5
   tabelle scritte non hanno RLS attiva (RLS solo su `config_overrides`,
   `locked_in`, `storico_ordini`), il `SET LOCAL talos.tenant_id` blinda
   contro futuri scenari multi-tabella RLS-protected nello stesso
   transaction scope. Costo: zero. Beneficio: future-proofing Zero-Trust.
2. **Caller responsabile di commit/rollback**: `save_session_result` NON
   chiama `commit()`. Lo fa il caller (tipicamente via `session_scope` o
   manualmente). Pattern Unit-of-Work: il repository compone la
   transazione, il caller la chiude.
3. **`db_session.flush()` dopo ogni `add()` di header/parent**: necessario
   per ottenere `id` autoincrementato prima dei child con FK. Costo
   minore, nessun roundtrip extra (flush e' tx-locale).
4. **`listino_hash` deterministico** via sha256 di CSV con colonne ordinate
   alfabeticamente: stesso input → stesso hash. Contratto blindato dal
   test `test_save_listino_hash_deterministic`. Implicazione futura:
   `UNIQUE(listino_hash)` permettera' upsert idempotente (CHG futuro).
5. **`raw_title` placeholder `f"ASIN:{asin}"`**: il listino raw del
   nostro orchestratore non ha `raw_title` (sara' campo dell'extractor
   futuro). Placeholder esplicito, marker per future-proof.
6. **`Decimal(str(value))` per i campi Numeric**: niente conversione
   binary float → Decimal (drift). `str()` preserva la rappresentazione
   decimale.
7. **Iterazione `iterrows()` invece di vettoriale**: la persistenza e'
   per-riga (insert ORM); il guadagno vettoriale qui e' marginale. Per
   listini >1k righe, `bulk_insert_mappings` e' errata futura ADR-0015.
8. **`tenant_id` parametro keyword-only con default 1**: MVP single-tenant.
   Test `test_save_custom_tenant_id` verifica che `tenant_id=42` venga
   materializzato sulla riga `sessions`.

### Out-of-scope

- **Idempotency / upsert**: `UNIQUE(listino_hash)` + `ON CONFLICT DO UPDATE`
  futuro. Per ora ri-eseguire stessa sessione = nuova riga.
- **Load / list sessions**: `load_session_by_id(sid)` + `list_recent_sessions(limit)`
  scope CHG futuro per UI storico.
- **Persistenza `StoricoOrdine`**: solo all'azione "ordina" del CFO (R-03).
  Non automatica al `save_session_result`.
- **Bulk insert performance**: scope errata corrige post-MVP.
- **CHAR(10) padding**: i test usano `.strip()` per confrontare ASIN; in
  futuro potremmo migrare a `VARCHAR(10)` (errata corrige Allegato A) per
  evitare la quirk Postgres.

## How

### `src/talos/persistence/session_repository.py` (highlight)

```python
def save_session_result(
    db_session: Session,
    *,
    session_input: SessionInput,
    result: SessionResult,
    tenant_id: int = 1,
) -> int:
    with with_tenant(db_session, tenant_id):
        # 1. Header
        analysis_session = AnalysisSession(...)
        db_session.add(analysis_session)
        db_session.flush()  # ottiene id

        # 2. ListinoItem per riga raw
        listino_id_by_asin = {}
        for _, row in session_input.listino_raw.iterrows():
            li = ListinoItem(...)
            db_session.add(li); db_session.flush()
            listino_id_by_asin[asin] = li.id

        # 3. VgpResult per riga enriched
        vgp_id_by_asin = {}
        for _, row in result.enriched_df.iterrows():
            vr = VgpResult(...)
            db_session.add(vr); db_session.flush()
            vgp_id_by_asin[asin] = vr.id

        # 4. CartItem per item
        for item in result.cart.items:
            db_session.add(CartItem(..., locked_in=item.locked))

        # 5. PanchinaItem per riga
        for _, row in result.panchina.iterrows():
            db_session.add(PanchinaItem(...))

        # 6. Marca conclusa
        analysis_session.ended_at = datetime.now(tz=UTC)
        db_session.flush()

        return int(analysis_session.id)
```

### Test plan (9 integration)

1. `test_save_creates_analysis_session_row` — header con campi corretti
2. `test_save_persists_listino_items` — N righe + raw_title placeholder
3. `test_save_persists_vgp_results` — N righe + flag R-08/R-05 + score=0 corretto
4. `test_save_persists_cart_items` — M righe + qty/unit_cost/locked_in
5. `test_save_persists_panchina_items` — P righe + qty_proposed
6. `test_save_listino_hash_deterministic` — stesso/diverso input → stesso/diverso hash
7. `test_save_custom_tenant_id` — tenant_id=42 materializzato
8. `test_save_returns_session_id_int` — return type
9. `test_save_with_locked_in` — flag `locked_in` + FK al VgpResult corretto

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 82 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **367 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **30 PASS** (21 + 9 nuovi) |

**Rischi residui:**
- **CHAR(10) padding**: ASIN letti dal DB tornano "S001      " con 6 spazi.
  I test usano `.strip()`. Codice applicativo che leggera' VgpResult.asin
  in futuro deve sapere/strippare. Mitigazione: errata corrige Allegato A
  per VARCHAR(10) (basso valore, scope futuro).
- **N+1 flush nel loop**: per 1k+ righe la latenza si accumula. Bulk insert
  via `db_session.bulk_save_objects` o `bulk_insert_mappings` e' errata
  futura. Per Samsung MVP (~100-500 ASIN) impatto trascurabile.
- **Mancata idempotency**: se la UI Streamlit chiama `Esegui Sessione` due
  volte sullo stesso listino, vengono create 2 righe `AnalysisSession`
  identiche (ma con `started_at`/`ended_at` diversi). Documentato; upsert
  e' scope CHG futuro con `UNIQUE(listino_hash)` migration.

## Impact

**🎯 Loop architetturale chiuso**: per la prima volta l'output dell'intelligenza
algoritmica (memory) viene scritto sulle tabelle DB (disk). Sblocca:
- UI storico ordini (CHG futuro che chiamera' `list_recent_sessions`)
- Compounding inter-sessione (caricare `Budget_T+1` come budget di T+1
  reale, non in-memory)
- Audit trail completo (5 tabelle + audit_log via trigger AFTER se
  configurati per quelle tabelle in futuro)

`run_session` resta puro (no DB side-effect): il caller compone
`run_session` + `save_session_result` quando vuole persistere. Pattern
Unit-of-Work coerente.

## Refs

- ADR: ADR-0015 (persistenza Zero-Trust + RLS), ADR-0014 (mypy/ruff strict),
  ADR-0013 (`persistence/`), ADR-0019 (test integration pattern)
- Predecessore: CHG-2026-04-30-039 (orchestrator), CHG-2026-04-30-020
  (engine/session/with_tenant)
- Schema: ADR-0015 Allegato A — 5 tabelle toccate (`sessions`,
  `listino_items`, `vgp_results`, `cart_items`, `panchina_items`)
- Successore atteso: `load_session_by_id` + `list_recent_sessions` (UI
  storico); upsert idempotente con `UNIQUE(listino_hash)`; integrazione
  `save_session_result` nella dashboard Streamlit (`if st.button("Salva")`)
- Commit: `[pending]`
