---
id: ADR-0015
title: Stack Persistenza — PostgreSQL Zero-Trust + SQLAlchemy 2.0
date: 2026-04-29
status: Active
deciders: Leader
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

L15 (Round 5) ha ratificato PostgreSQL Zero-Trust come modello di sicurezza del database: RLS attiva su tabelle sensibili, ruoli separati `talos_app`/`talos_admin` (più `talos_audit` proposto da Claude), nessun superuser nel pool applicativo, audit log su tabelle critiche.

L16 (Round 5) ha ratificato SQLAlchemy 2.0 **sync** + Alembic per migrations. Sync (non async) è scelta deliberata: testabilità byte-exact (R-01) richiede determinismo nelle fixture; async aggiunge non-determinismo e complica i golden test della pipeline VGP→Tetris.

Mancano: schema iniziale del DB, mappatura ruoli/RLS sulle tabelle, strategia di backup, gestione segreti DB (password ruoli).

## Decisione

### Engine & ORM

- **PostgreSQL 16** in container Docker (immagine `postgres:16-alpine`).
- **SQLAlchemy 2.0** mode `Imperative Mapping` con typed columns (`Mapped[T]`, `mapped_column(...)`).
- **Alembic** per migrations (auto-generate da modelli + revisione manuale obbligatoria).
- **`psycopg[binary]`** come driver (non `asyncpg`, coerente con sync).

### Ruoli e RLS (Zero-Trust)

| Ruolo | Permessi | Uso |
|---|---|---|
| `talos_admin` | `CREATEDB`, DDL su tutte le tabelle, `BYPASSRLS` | Esclusivamente per Alembic migrations e operazioni di manutenzione |
| `talos_app` | `SELECT/INSERT/UPDATE/DELETE` solo su tabelle applicative; **soggetto a RLS** | Pool di connessione di Streamlit + worker |
| `talos_audit` | `SELECT` solo su `audit_log` e viste read-only | Reporting e investigation; nessun write |

**Nessun superuser** nel pool applicativo. Le password sono in **GitHub Secrets** (CI) e in `.env` locale (escluso da git via `.gitignore`).

**RLS attiva su:**
- `storico_ordini` — riga visibile solo se `tenant_id = current_setting('talos.tenant_id')`. In MVP single-tenant `tenant_id = 1` hardcoded; prepara future multi-tenancy senza rework.
- `locked_in` — stessa policy.
- `config_overrides` — stessa policy.

### Audit Log

Tabella `audit_log` append-only:
- Trigger `AFTER INSERT/UPDATE/DELETE` su `storico_ordini`, `locked_in`, `config_overrides`.
- Campi: `id BIGSERIAL`, `actor TEXT` (ruolo PostgreSQL), `table_name TEXT`, `op CHAR(1)` (`I`/`U`/`D`), `row_id BIGINT`, `before JSONB`, `after JSONB`, `at TIMESTAMPTZ DEFAULT NOW()`.
- `talos_app` ha `INSERT` ma non `UPDATE/DELETE` su `audit_log`.

### Backup Strategy (MVP)

**`pg_dump` schedulato + retention 7 giorni**, decisione Leader.

- Cron locale (sviluppo): `0 3 * * * pg_dump -Fc -d talos > /backups/talos-$(date +\%Y\%m\%d).dump`.
- Retention: `find /backups -name 'talos-*.dump' -mtime +7 -delete`.
- Storage: directory locale `/backups/` (in MVP). Path configurabile via env.
- **Non-MVP scope:** backup su cloud (S3/B2) post-MVP.

### Connessione & pool

- `SQLAlchemy.create_engine(url, pool_size=5, max_overflow=10, pool_recycle=3600)`.
- Connection string da `pydantic-settings` con env `TALOS_DB_URL=postgresql+psycopg://talos_app:****@localhost:5432/talos`.
- `set_session_authorization('talos_app')` come `event listener` SQLAlchemy `connect`.

---

## Allegato A — Schema DB Iniziale (DDL conceptuale)

> Schema di riferimento per Alembic initial migration. Le decisioni di tipo (`NUMERIC` vs `INT`) e gli indici secondari saranno raffinati in fase implementativa.

```sql
-- ============================================================
-- TALOS — Schema iniziale (Allegato A di ADR-0015)
-- ============================================================

-- Anagrafica ASIN (lookup, popolata da Keepa/scraping)
CREATE TABLE asin_master (
    asin            CHAR(10) PRIMARY KEY,
    title           TEXT NOT NULL,
    brand           TEXT NOT NULL,
    model           TEXT,                       -- es. "S24"
    rom_gb          INT,
    ram_gb          INT,
    connectivity    TEXT,                       -- "4G" | "5G"
    color_family    TEXT,                       -- normalizzato
    enterprise      BOOLEAN DEFAULT FALSE,
    category_node   TEXT,                       -- nodo Amazon (lookup Referral_Fee)
    last_seen_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_asin_brand_model ON asin_master(brand, model);

-- Sessioni di analisi (Stateless: ogni sessione è autocontenuta)
CREATE TABLE sessions (
    id              BIGSERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    budget_eur      NUMERIC(12,2) NOT NULL,    -- L02 budget di sessione
    velocity_target INT DEFAULT 15,             -- L05 (range 7-30)
    listino_hash    CHAR(64) NOT NULL,         -- sha256 del listino di input
    tenant_id       BIGINT NOT NULL DEFAULT 1
);

-- Righe del listino fornitore (input di sessione)
CREATE TABLE listino_items (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    asin            CHAR(10),                   -- nullable: match Amazon avviene dopo
    raw_title       TEXT NOT NULL,
    cost_eur        NUMERIC(12,2) NOT NULL,
    qty_available   INT,
    match_status    TEXT,                       -- 'MATCH_SICURO' | 'AMBIGUO' | 'KILLED'
    match_reason    TEXT
);
CREATE INDEX idx_listino_session ON listino_items(session_id);

-- Risultati VGP per ASIN per sessione
CREATE TABLE vgp_results (
    id                          BIGSERIAL PRIMARY KEY,
    session_id                  BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    listino_item_id             BIGINT NOT NULL REFERENCES listino_items(id) ON DELETE CASCADE,
    asin                        CHAR(10) NOT NULL,
    roi_pct                     NUMERIC(8,4),
    velocity_monthly            NUMERIC(12,4),
    cash_profit_eur             NUMERIC(12,2),
    roi_norm                    NUMERIC(6,4),   -- L04b: min-max [0,1]
    velocity_norm               NUMERIC(6,4),
    cash_profit_norm            NUMERIC(6,4),
    vgp_score                   NUMERIC(6,4),
    veto_roi_passed             BOOLEAN,        -- R-08
    kill_switch_triggered       BOOLEAN,        -- R-05 → vgp_score = 0
    qty_target                  INT,
    qty_final                   INT             -- floor((qty_target / 5) * 5)
);
CREATE INDEX idx_vgp_session_score ON vgp_results(session_id, vgp_score DESC);

-- Carrello finale (output principale, saturato 99.9%)
CREATE TABLE cart_items (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    vgp_result_id   BIGINT NOT NULL REFERENCES vgp_results(id) ON DELETE CASCADE,
    qty             INT NOT NULL,
    unit_cost_eur   NUMERIC(12,2) NOT NULL,
    locked_in       BOOLEAN DEFAULT FALSE       -- R-04: priorità ∞
);

-- Panchina (R-09: ROI ≥ 8% scartati per capienza)
CREATE TABLE panchina_items (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    vgp_result_id   BIGINT NOT NULL REFERENCES vgp_results(id) ON DELETE CASCADE,
    qty_proposed    INT NOT NULL
);

-- Storico ordini (R-03 ORDER-DRIVEN MEMORY)
CREATE TABLE storico_ordini (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES sessions(id),
    cart_item_id    BIGINT NOT NULL REFERENCES cart_items(id),
    asin            CHAR(10) NOT NULL,
    qty             INT NOT NULL,
    unit_cost_eur   NUMERIC(12,2) NOT NULL,
    ordered_at      TIMESTAMPTZ DEFAULT NOW(),
    tenant_id       BIGINT NOT NULL DEFAULT 1
);
ALTER TABLE storico_ordini ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON storico_ordini
    USING (tenant_id = current_setting('talos.tenant_id', true)::bigint);

-- ASIN lock-in (R-04 manual override, Priorità ∞)
CREATE TABLE locked_in (
    id              BIGSERIAL PRIMARY KEY,
    asin            CHAR(10) NOT NULL,
    qty_min         INT NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    tenant_id       BIGINT NOT NULL DEFAULT 1
);
ALTER TABLE locked_in ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON locked_in
    USING (tenant_id = current_setting('talos.tenant_id', true)::bigint);

-- Config overrides (Veto ROI %, Referral_Fee per categoria, etc.)
CREATE TABLE config_overrides (
    id              BIGSERIAL PRIMARY KEY,
    scope           TEXT NOT NULL,              -- 'global' | 'category' | 'asin'
    scope_key       TEXT,                       -- es. category_node o asin
    key             TEXT NOT NULL,              -- 'veto_roi_pct' | 'referral_fee_pct'
    value_numeric   NUMERIC(12,4),
    value_text      TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    tenant_id       BIGINT NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX idx_config_unique ON config_overrides(tenant_id, scope, scope_key, key);
ALTER TABLE config_overrides ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON config_overrides
    USING (tenant_id = current_setting('talos.tenant_id', true)::bigint);

-- Audit log (append-only)
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    actor           TEXT NOT NULL,              -- session_user
    table_name      TEXT NOT NULL,
    op              CHAR(1) NOT NULL,           -- 'I' | 'U' | 'D'
    row_id          BIGINT,
    before_data     JSONB,
    after_data      JSONB,
    at              TIMESTAMPTZ DEFAULT NOW()
);
-- Trigger su tabelle critiche → audit_log (DDL trigger in Alembic migration)

-- Ruoli
CREATE ROLE talos_admin WITH LOGIN PASSWORD :admin_password;
CREATE ROLE talos_app   WITH LOGIN PASSWORD :app_password;
CREATE ROLE talos_audit WITH LOGIN PASSWORD :audit_password;

GRANT CONNECT ON DATABASE talos TO talos_app, talos_audit;
GRANT USAGE ON SCHEMA public TO talos_app, talos_audit;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO talos_app;
GRANT INSERT ON audit_log TO talos_app;
REVOKE UPDATE, DELETE ON audit_log FROM talos_app;
GRANT SELECT ON audit_log TO talos_audit;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO talos_app;
```

> Lo schema sarà raffinato in fase di implementazione (indici di performance su `vgp_results`, gestione versionamento ASIN, eventuale partizionamento di `audit_log`). Questo allegato è il **punto di partenza vincolante**.

## Conseguenze

**Positive:**
- Sicurezza by-design: anche un'iniezione SQL nel codice applicativo non può escalare a DDL (talos_app non ha privilegi).
- RLS prepara multi-tenancy futura senza rework.
- Audit log integrale: ogni modifica su tabelle critiche è tracciata.
- Sync ORM: test fixture deterministici, golden dataset byte-exact (R-01) realizzabile.

**Negative / costi:**
- Setup DB più complesso: 3 ruoli + RLS + trigger audit. Documentazione di setup richiesta.
- Performance: psycopg sync è ~30% più lento di asyncpg. Su 10k righe non è un problema; oltre lo è (decisione di Errata Corrige in futuro).
- Backup `pg_dump` non è incremental: su DB grandi è lento. In MVP accettabile.

**Effetti collaterali noti:**
- Schema iniziale "vincolante" significa: aggiunte/modifiche allo schema vanno via Alembic + change document, non a mano.
- Il futuro modulo Streamlit (ADR-0016) deve impostare `set_local "talos.tenant_id" = 1` a inizio sessione per attivare RLS.

## Test di Conformità

1. **Migration up/down:** `alembic upgrade head && alembic downgrade base` deve completare senza errore su DB vergine.
2. **Verifica ruoli:** test integration verifica che `talos_app` non possa eseguire `DROP TABLE`.
3. **Verifica RLS:** test integration con `tenant_id = 1` e `tenant_id = 2` isola correttamente i dati.
4. **Verifica audit log:** insert/update/delete su `storico_ordini` produce riga in `audit_log` con `before_data`/`after_data` corretti.
5. **Verifica backup:** script `scripts/backup-postgres.sh` produce file `.dump` in directory configurata.

## Cross-References

- ADR correlati: ADR-0001, ADR-0013 (struttura), ADR-0014 (linguaggio), ADR-0018 (algoritmo legge/scrive da queste tabelle), ADR-0019 (test integration), ADR-0021 (audit log → log strutturato)
- Governa: `migrations/`, `src/talos/persistence/`, `scripts/backup-postgres.sh` (futuro)
- Impatta: ogni operazione di lettura/scrittura DB
- Test: `tests/integration/test_persistence.py`, `test_rls.py`, `test_audit_log.py`
- Commits: `<pending>`

## Rollback

Se Zero-Trust risulta troppo invasivo in fase di sviluppo:
1. Errata Corrige a ADR-0015: disabilitare RLS via `ALTER TABLE ... DISABLE ROW LEVEL SECURITY`.
2. Mantenere comunque ruoli separati e audit log (sono indipendenti da RLS).
3. Documentare il downgrade nella sezione `## Errata`.

Per superseduta totale (es. cambio engine):
1. Promulgare ADR-NNNN con `supersedes: ADR-0015`.
2. Esportare schema + dati (`pg_dump`) e migrare al nuovo engine.
3. Archiviare il database PostgreSQL.
