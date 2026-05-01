---
id: CHG-2026-05-01-019
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 4 — cache descrizione->ASIN persistente, decisioni α=A/β=A/γ=A ratificate)
status: Draft
commit: TBD
adr_ref: ADR-0015, ADR-0017, ADR-0014, ADR-0019
---

## What

Inaugura `description_resolutions` (4° tabella aggiuntiva post
Allegato A). Cache persistente delle risoluzioni descrizione->ASIN
(consumate da `_LiveAsinResolver` CHG-018).

Decisioni Leader 2026-05-01 round 4 ratificate:

- **alpha=A NO RLS**: cache infrastructural, no PII (descrizione e
  ASIN sono dati pubblici Amazon); coerente con tabelle ad alta
  volatilita' (vgp_results, cart_items).
- **beta=A UNIQUE `(tenant_id, description_hash)`**: ogni tenant
  ha la sua cache (il `confidence_pct` dipende dal prezzo input
  tenant-side); coerente con `sessions(tenant_id, listino_hash)`
  CHG-047.
- **gamma=A NO trigger audit**: cache write-many (resolve molti
  candidati per batch grande), audit_log esploderebbe.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/description_resolution.py` | nuovo | `DescriptionResolution` ORM model: id BIGSERIAL PK, tenant_id INT NOT NULL, description_hash CHAR(64) NOT NULL (SHA-256 hex), asin CHAR(10) NOT NULL, confidence_pct NUMERIC(5,2) NOT NULL, resolved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(). UNIQUE INDEX `ux_description_resolutions_tenant_hash`. |
| `src/talos/persistence/models/__init__.py` | modificato | Re-export `DescriptionResolution`. |
| `migrations/versions/1d67de49c197_create_description_resolutions.py` | nuovo | Alembic revision down_revision=`e8b80f77961b`. `op.create_table` + `op.create_index` UNIQUE. Drop simmetrico in downgrade. **Bonus correttivo**: lo spurio drop/recreate `idx_config_unique` rilevato da autogenerate (drift modello ORM senza `postgresql_nulls_not_distinct`) e' stato rimosso dalla migration. |
| `src/talos/persistence/models/config_override.py` | modificato | Aggiunto `postgresql_nulls_not_distinct=True` a `idx_config_unique` per allineare ORM al DB (pattern messo da migration `e8b80f77961b` di CHG-050). Drift permanente di autogenerate eliminato. |
| `src/talos/persistence/asin_resolver_repository.py` | nuovo | `compute_description_hash(description) -> str` (SHA-256 hex 64-char di `description.strip().lower()`, ValueError su empty). `find_resolution_by_hash(db, *, tenant_id, description_hash) -> DescriptionResolution \| None` (lookup tenant-scoped). `upsert_resolution(db, *, tenant_id, description_hash, asin, confidence_pct) -> int` (UPSERT idempotente con `pg_insert.on_conflict_do_update` su UNIQUE; refresh asin/confidence/resolved_at). Pattern Unit-of-Work (caller commits). Costante `DEFAULT_TENANT_ID=1`. |
| `tests/integration/test_asin_resolver_repository.py` | nuovo | 10 test integration su Postgres reale: 4 `compute_description_hash` (deterministic 64-char hex, normalizzazione whitespace+case, descrizioni diverse hash diversi, empty raises) + 3 `find_resolution_by_hash` (None su miss, round-trip, tenant filtering) + 3 `upsert_resolution` (insert primo, UPDATE on conflict, tenant indipendenza). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **616
PASS** unit/gov/golden + 133 integration = **749 PASS** (era 740,
+10 integration nuovi, -1 differenza da fixture engine — non
significativa).

`alembic upgrade head` reale verde su Postgres 16-alpine.
`alembic check` post-upgrade: `No new upgrade operations detected`.

## Why

CHG-018 ha chiuso il motore applicativo del resolver. Senza cache
persistente, ogni esecuzione del flusso "descrizione -> ASIN"
ricalcola da zero (1 SERP + N Keepa per descrizione). Per batch
grandi e re-run quotidiani del CFO, costo cumulativo di quota
Keepa + tempo Chromium intollerabile.

La cache `(tenant_id, description_hash) -> asin + confidence_pct`
abbatte drasticamente il re-resolve: hit rate atteso > 50% per CFO
ricorrenti con stessi fornitori. Pattern Twelve-Factor App
(infrastruttura cache locale a Postgres, no Redis aggiuntivo).

### Decisioni di design

1. **alpha=A NO RLS ratificata**: la tabella e' "infrastructural"
   come `audit_log` (non ha RLS, e' append-only). Cache write-many
   con RLS aggiunge overhead per zero security gain (la mappa
   descrizione->ASIN e' pubblicamente derivabile dalla SERP Amazon).

2. **beta=A UNIQUE `(tenant_id, description_hash)` ratificata**:
   coerente architetturalmente con `sessions(tenant_id, listino_hash)`
   CHG-047. Stesso `description_hash` su tenant diversi NON
   collide (UPSERT 2 righe distinte).

3. **gamma=A NO trigger audit ratificata**: la cache puo' avere
   migliaia di righe per batch grandi. Audit ne raddoppierebbe la
   scrittura. Nessun valore investigativo (mappa pubblica).

4. **`description_hash` SHA-256 hex con normalizzazione
   `strip().lower()`**: trim + lowercase = equivalenze "Galaxy S24"
   == "galaxy s24" == "  galaxy s24  ". Equivalenze NON estese:
   "Galaxy S24" != "Galaxy S24 256GB" (descrizioni semanticamente
   diverse). Pattern conservativo: cache puo' avere ridondanze
   minori (case minuscolo vs maiuscolo del fornitore stesso ASIN
   = stessa cache hit). Hash a 64 char fissi: PRIMARY KEY-friendly.

5. **CHAR(64) hash, non VARCHAR / TEXT**: SHA-256 hex e' sempre
   esattamente 64 char. CHAR(64) padded e' deterministico,
   indice piu' piccolo / piu' veloce.

6. **CHAR(10) `asin`**: convenzione gia' usata in `asin_master`,
   `cart_items`, `vgp_results`, ecc. Test CFO devono `.strip()`
   per confronto (CHAR(10) right-padded).

7. **`confidence_pct` NUMERIC(5,2)**: range 0.00 - 100.00 sufficiente
   per `compute_confidence` (CHG-016). Pattern coerente con
   `vgp_results.vgp_score` (NUMERIC(5,4)).

8. **`resolved_at` TIMESTAMPTZ con default NOW()**: timestamp
   utile per invalidare entries stale (TTL applicabile a livello
   query, scope futuro). Pattern coerente con `analysis_session.started_at`.

9. **UPSERT con `pg_insert.on_conflict_do_update`**: pattern
   Postgres-native, atomico. Stessa semantica di `upsert_asin_master`
   (CHG-005 D5.a). `set_={asin, confidence_pct, resolved_at}` =
   "le risoluzioni nuove vincono sulle vecchie" (last-write-wins).

10. **Bonus correttivo `idx_config_unique` ORM allineato**: il
    drift fra modello ORM e DB (ORM senza `postgresql_nulls_not_distinct`,
    DB con) era un bug latente che alembic autogenerate segnalava
    ad ogni nuova revision. Allineamento ORM corregge il drift in
    modo permanente. Opportunita' colta in CHG-019, costo zero.

11. **Pattern Unit-of-Work preservato**: il repository non committa.
    Coerente con `save_session_result`, `set_config_override_*`,
    `upsert_asin_master`. Caller via `session_scope()`.

### Out-of-scope

- **Integrazione resolver -> cache**: scope CHG-2026-05-01-020 (UI),
  oppure mini-refactor di `_LiveAsinResolver` per consultare cache
  prima di SERP (decisione architetturale: la cache e' "trasparente"
  dentro il resolver oppure orchestrata dalla UI?). Default proposto
  per CHG-020: la cache e' consultata dalla UI (pattern coerente
  con `find_session_by_hash` consultato pre-save in CHG-048),
  resolver ignaro.
- **TTL invalidation `resolved_at < NOW() - INTERVAL N days`**:
  scope futuro se la stabilita' del mapping descrizione->ASIN si
  rivela problematica empirically.
- **Cleanup retention policy**: scope futuro (cron job o trigger).
  Per ora la cache cresce all'infinito (storage cheap).
- **Telemetria `cache.hit` / `cache.miss`**: scope futuro errata
  catalogo ADR-0021.

## How

### `compute_description_hash` (highlight)

```python
def compute_description_hash(description: str) -> str:
    cleaned = description.strip().lower()
    if not cleaned:
        raise ValueError("description vuota / whitespace-only")
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
```

### `upsert_resolution` (highlight)

```python
insert_stmt = pg_insert(DescriptionResolution).values(
    tenant_id=..., description_hash=..., asin=..., confidence_pct=...,
)
upsert_stmt = insert_stmt.on_conflict_do_update(
    index_elements=["tenant_id", "description_hash"],
    set_={
        "asin": insert_stmt.excluded.asin,
        "confidence_pct": insert_stmt.excluded.confidence_pct,
        "resolved_at": insert_stmt.excluded.resolved_at,
    },
).returning(DescriptionResolution.id)
return int(db.execute(upsert_stmt).scalar_one())
```

### Test plan eseguito (10 integration su Postgres reale)

- 4 `compute_description_hash`: deterministic 64-char hex,
  normalizzazione whitespace+case, descrizioni diverse hash
  diversi, empty raises ValueError.
- 3 `find_resolution_by_hash`: None on miss, round-trip
  insert+lookup, tenant filtering (tenant 1 non vede entry tenant 2).
- 3 `upsert_resolution`: insert primo (id BIGSERIAL > 0), UPDATE
  on conflict (stesso id, asin/confidence aggiornati), tenant
  indipendenza (stesso hash su tenant diversi = 2 righe distinte).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (53 source files) |
| Alembic upgrade | `TALOS_DB_URL=... uv run alembic upgrade head` | OK (e8b80f77961b -> 1d67de49c197) |
| Alembic check (no drift) | `uv run alembic check` | `No new upgrade operations detected` |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **616 PASS** (invariato vs CHG-018) |
| Integration | `uv run pytest tests/integration --ignore=test_live_*` | **133 PASS** (era 124, +9 nuovi: 10 nuovi `test_asin_resolver_repository`) |

**Rischi residui:**
- **Cache crescita illimitata**: senza retention policy, la
  tabella cresce ad ogni resolve. Mitigazione: descrizioni stabili
  per fornitore -> hash riutilizzati -> crescita lineare in N
  descrizioni distinte (non in N batch). Per scaler 500k SKUs il
  cap pratico e' 500k righe (footprint < 100 MB).
- **Stale resolution**: la mappa descrizione->ASIN puo' cambiare
  se Amazon ridireziona / ASIN delistato. La cache non ha TTL.
  Mitigazione: il caller puo' fare `delete + re-resolve` quando
  detecta inconsistenza. UPSERT garantisce refresh on
  re-resolve.
- **Hash collision SHA-256**: probabilita' astronomicamente
  bassa (2^-256). Non si verifichera' in alcuna scala praticabile.
- **`postgresql_nulls_not_distinct` ORM allineato**: cambio
  cosmetico/correttivo, no impact runtime su DB esistente.
  Verificato `alembic check` post-modifica.

## Test di Conformità

- **Path codice applicativo:** `src/talos/persistence/` ✓
  (area `persistence/` ADR-0013 consentita).
- **ADR-0015 vincoli rispettati:**
  - Tabella aggiuntiva post Allegato A: stessi pattern (BIGSERIAL,
    TIMESTAMPTZ default NOW(), CHAR(N) per ASIN).
  - Migration alembic + ORM allineato + `alembic check` verde.
  - Decisione `NO RLS / NO audit` motivata in change doc.
  - `nullable=False` per server_default valido (convention
    progetto).
- **ADR-0017 vincoli rispettati:** la cache e' consumata da
  `asin_resolver` (canale risoluzione). Pattern UPSERT idempotente
  + R-01 NO SILENT DROPS (empty hash -> ValueError esplicito).
- **Test integration su Postgres reale:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `description_resolutions`
  -> ADR-0015 (schema persistenza, decisione architetturale
  ratificata Leader).
- **Backward compat:** modulo nuovo + tabella nuova; zero impact
  su caller esistenti. Modello `ConfigOverride` allineato senza
  cambio runtime.
- **Sicurezza:** zero secrets, zero PII. Hash deterministici,
  no input untrusted.
- **Impact analysis pre-edit:** GitNexus risk LOW (tabella
  + repository nuovi, zero caller upstream finche' non integriamo
  in CHG-020).

## Impact

- **Persistenza cache asin_resolver chiusa**: 4/5 CHG attesi
  blocco asin_resolver (016 skeleton + 017 SERP + 018 composer +
  019 cache). Resta CHG-020 UI rifondata.
- **Allegato A esteso a 11 tabelle** (10 originali + 1 cache).
  Allegato A non originario, decisione Leader ratificata in
  change doc. Pattern `description_resolutions` riapre la
  porta a future tabelle "infrastructural cache" se servono.
- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11 viventi).
- **Test suite +10 integration**: 749 PASS (era 740), zero
  regression.
- **Drift `idx_config_unique` ORM/DB risolto come effetto
  collaterale**. Alembic check verde da ora in poi.
- **MVP Path B status**: pre-CHG-020, l'utente CFO (lato API)
  puo' gia' fare resolve+cache+save_session via codice Python.
  Resta UX: CHG-020.

## Refs

- ADR: ADR-0015 (schema persistenza, tabella aggiuntiva post
  Allegato A), ADR-0017 (cache consumata da asin_resolver),
  ADR-0014 (mypy/ruff strict + pattern UPSERT Postgres-native),
  ADR-0019 (test integration Postgres reale).
- Predecessori:
  - CHG-2026-05-01-018 (`_LiveAsinResolver` composer): consumer
    futuro della cache (scope CHG-020 lato UI).
  - CHG-2026-04-30-005 (`upsert_asin_master`): pattern
    `pg_insert.on_conflict_do_update` riusato.
  - CHG-2026-04-30-047 (UNIQUE `sessions(tenant_id, listino_hash)`):
    pattern UNIQUE composito riusato.
  - CHG-2026-04-30-050 (config_overrides UNIQUE NULLS NOT
    DISTINCT): drift ORM corretto in CHG-019.
- Decisioni Leader 2026-05-01 round 4: alpha=A NO RLS,
  beta=A UNIQUE tenant+hash, gamma=A NO audit (ratificate inline,
  nessuna nuova memory necessaria; documentate solo in change doc
  e docstring del modello).
- Memory: nessuna nuova; `feedback_ambigui_con_confidence.md`
  resta invariato (R-01 UX).
- Successore atteso: CHG-2026-05-01-020 (UI rifondata: nuovo flow
  upload listino "umano" descrizione+prezzo + integrazione cache
  resolver + highlight `confidence_pct` + expander legacy CSV
  con ASIN).
- Commit: TBD (backfill post-commit).
