---
id: CHG-2026-04-30-045
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0015, ADR-0016, ADR-0014, ADR-0019
---

## What

Aggiunge `load_session_by_id(db_session, sid, *, tenant_id=1) -> LoadedSession | None`
per ricaricare una sessione storica + UI dettaglio nella dashboard
Streamlit. Chiude il **CRUD-light** del cluster persistenza
(create/list/load).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/session_repository.py` | modificato | +`LoadedSession` frozen dataclass (summary + cart_rows + panchina_rows) + `load_session_by_id(...)` con `db_session.get` + filtro `tenant_id` applicativo + JOIN `CartItem`/`PanchinaItem` con `VgpResult` per asin/score/roi |
| `src/talos/persistence/__init__.py` | modificato | +re-export `LoadedSession`, `load_session_by_id` |
| `src/talos/ui/dashboard.py` | modificato | +`fetch_loaded_session_or_none(factory, sid, *, tenant_id) -> LoadedSession \| None` + `_render_loaded_session_detail(loaded)` con metric + 2 dataframe + `_render_history` esteso con `number_input` + bottone "Carica dettaglio" |
| `src/talos/ui/__init__.py` | modificato | +re-export `fetch_loaded_session_or_none` |
| `tests/integration/test_load_session_by_id.py` | nuovo | 8 test integration (None su id mancante, ValueError su id<=0, round-trip save→load, cart_rows match orchestrator, panchina_rows match, panchina ordinata DESC, tenant filter, locked_in flag) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | entry `session_repository.py` aggiornata con CHG-045 |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **417 PASS**
(369 unit/governance/golden + 48 integration).

## Why

CHG-044 ha aggiunto la **lista** delle sessioni (summary). Senza il
**load** della singola sessione, il CFO vede l'header storico ma non
puo' ispezionare cosa c'era nel Cart o nella Panchina. Click su una
riga della lista → niente. Il loop di "memoria operativa" e' incompleto.

`load_session_by_id` chiude il loop:
- Click "Carica dettaglio" su una sessione storica
- UI mostra: budget, velocity_target, # cart/panchina, tabella cart, tabella panchina
- Il CFO puo' confrontare visualmente decisioni passate

### Decisioni di design

1. **`LoadedSession` separato da `SessionResult`**: `SessionResult` ha
   `pd.DataFrame enriched_df` + `Cart` con metodi (saturation/remaining).
   La ricostruzione full richiederebbe rebuild del DataFrame da N
   `VgpResult` con tutti i campi, oltre a istanziare un `Cart` con
   `items`. Scope troppo grande per il primo CHG. `LoadedSession` e'
   un DTO snello: `summary` + `list[dict]` per cart e panchina,
   sufficiente per UI dettaglio. Ricostruzione full `SessionResult` e'
   scope CHG futuro (`load_session_full`).
2. **JOIN in SQL invece di lazy-load relationship**: `CartItem` ha
   `relationship('vgp_result')` ma il lazy-load farebbe N+1 query.
   `select(CartItem, VgpResult.asin, ...).join(VgpResult, ...)` e'
   single-query.
3. **Filtro `tenant_id` applicativo + `with_tenant` SQL var**: doppia
   barriera coerente con `list_recent_sessions`. La sessione di un
   tenant diverso ritorna `None`, non raise. Test
   `test_load_filters_by_tenant_id` lo blinda.
4. **Ordering panchina: `vgp_score DESC`**: coerente con R-09 (ASIN
   scartati per cassa, ordinati VGP DESC). Cart ordering: `id ASC`
   (ordine di inserimento, locked-in prima).
5. **`unit_cost_eur` ricostruito**: nel DB c'e' `unit_cost_eur` e
   `qty`; `cost_total = unit * qty` calcolato in lettura. Pattern
   coerente con la persistenza (CartItem ha colonna `unit_cost_eur`,
   non `cost_total`).
6. **CHAR(10) padding strip**: `.strip()` su `asin` per UI leggibile.
   Documentato dalla quirk Postgres (CHG-042).
7. **`number_input` invece di selectbox**: la lista storica puo'
   crescere a 100+ sessioni; il number_input permette di incollare l'id
   dalla colonna sopra. Meno UX-friendly di un click-on-row, ma
   Streamlit `st.dataframe` MVP non supporta nativamente row-click
   senza componenti custom. Errata corrige post-MVP.
8. **`fetch_loaded_session_or_none`** lato UI: stesso pattern di
   `fetch_recent_sessions_or_empty`, graceful None su error.

### Out-of-scope

- **`load_session_full`** (ricostruzione `SessionResult` con
  `pd.DataFrame enriched_df` + `Cart` con metodi): scope CHG futuro
  quando emergera' bisogno di "ri-eseguire" pipeline da una sessione
  passata (es. compounding inter-sessione).
- **Bottone "Ri-esegui sessione" / "Esporta CSV"**: scope futuro.
- **Click-on-row**: richiede componente custom Streamlit (es.
  `streamlit-aggrid`), scope refactor multi-page ADR-0016.
- **Search / filter / sort sulla tabella storico**: scope quando
  emergera' la necessita' (>50 sessioni).
- **Test fail path** UI (DB down dopo il load): scope CHG dedicato con
  mock framework.

## How

### `load_session_by_id` (highlight)

```python
def load_session_by_id(
    db_session: Session, session_id: int, *, tenant_id: int = 1,
) -> LoadedSession | None:
    if session_id <= 0:
        raise ValueError(...)
    with with_tenant(db_session, tenant_id):
        asession = db_session.get(AnalysisSession, session_id)
        if asession is None or asession.tenant_id != tenant_id:
            return None
        # n_cart / n_panch via count
        summary = SessionSummary(...)
        # JOIN per cart_rows + panchina_rows
        cart_rows = [...]
        panchina_rows = [...]
        return LoadedSession(summary, cart_rows, panchina_rows)
```

### Test plan (8 integration)

1. `test_load_returns_none_for_missing_id` — id=999_999 → None
2. `test_load_invalid_id_raises` — id<=0 → ValueError
3. `test_load_returns_loaded_session_after_save` — round-trip
4. `test_load_cart_rows_match_orchestrator_cart` — qty/locked match
5. `test_load_panchina_rows_match` — asin set match
6. `test_load_panchina_rows_ordered_vgp_desc` — ordering
7. `test_load_filters_by_tenant_id` — t1 visto da t1, NON da t2
8. `test_load_session_with_locked_in_marks_correct_row` — locked flag preserved

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 85 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **369 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **48 PASS** (40 + 8) |

**Rischi residui:**
- **N+1 nelle subquery `count`**: 2 query separate (`count(CartItem)`,
  `count(PanchinaItem)`). Per UI dettaglio singola sessione costa nulla;
  per liste di 100+ sessioni andrebbe usato il pattern aggregato di
  `list_recent_sessions`. Documentato.
- **Decimal precision in cart_rows**: `unit_cost_eur` letto come
  `Decimal(12,2)` viene convertito a `float` per JSON-friendly UI.
  Drift trascurabile (1 cent), ma se serve precisione esatta si puo'
  esporre come `Decimal` (rompe `pd.DataFrame`).
- **No clic-on-row UX**: number_input come fallback. Documentato.

## Impact

**🎯 CRUD-light persistenza completo**: il cluster `persistence/`
implementa ora Create (`save_session_result`), List (`list_recent_sessions`),
Load (`load_session_by_id`). Manca solo Update/Delete, ma:
- Update non e' richiesto (storico append-only ADR-0015).
- Delete e' opzionale (UI futura: "elimina sessione" con confirm).

UI Streamlit ora ha 2 funzioni "esegui-vedi-salva" + "rivedi-ispeziona"
chiuse end-to-end.

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze`:
`LoadedSession`, `load_session_by_id`, `fetch_loaded_session_or_none`,
`_render_loaded_session_detail`.

## Refs

- ADR: ADR-0015 (persistenza), ADR-0016 (UI Streamlit), ADR-0014
  (mypy/ruff strict), ADR-0019 (test integration pattern)
- Predecessori: CHG-2026-04-30-042 (save), CHG-2026-04-30-043 (UI persist
  integration), CHG-2026-04-30-044 (list_recent_sessions)
- Successore atteso: `load_session_full` per re-execute pipeline da
  sessione passata; click-on-row UX; `UNIQUE(listino_hash)` migration +
  upsert
- Commit: `[pending]`
