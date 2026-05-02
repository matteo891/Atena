# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/lang/it/).

---

## [Unreleased]

### Added
- `src/talos/ui/listino_input.py` — `_detect_columns(df) -> tuple[str, str]` heuristica deterministica (alias canonici 10+10 → fallback ratio price-parseable ≥80% + avg-len descrizione ≥4 char). + `_column_price_parseable_ratio` / `_column_avg_string_length` oracle. + `_coerce_prezzo(value)` con fallback `parse_eur` per stringhe formato italiano (`€ 549,99`). + costanti `DESCRIZIONE_HEADER_ALIASES` / `PREZZO_HEADER_ALIASES` (frozenset). [CHG-2026-05-02-023]
- `tests/unit/test_listino_input.py` — 12 test nuovi (alias parametrico 6-case, header anonimi, prezzi italiano, opzionali preservate, errori espliciti R-01, alias-overrides-heuristic, backwards-compat sentinel). [CHG-2026-05-02-023]
- `src/talos/ui/document_parser.py` — costante `CSV_ENCODING_CHAIN` (`utf-8-sig` → `cp1252` → `latin-1`) + helper `_decode_with_fallback(raw) -> str`. `_parse_csv` ora itera la chain per `pd.read_csv(encoding=...)`. Bug fix live Leader: byte 0x97 em-dash da Excel italiano cp1252 rompeva UTF-8 strict. [CHG-2026-05-02-024]
- `tests/unit/test_document_parser.py` — 5 test nuovi (UTF-8 ASCII, UTF-8 italiano accenti, UTF-8-sig BOM, cp1252 em-dash 0x97, cp1252 accenti italiano). [CHG-2026-05-02-024]

### Changed
- `parse_descrizione_prezzo_csv` ora chiama `_detect_columns` e rinomina internamente le colonne riconosciute a `descrizione`/`prezzo`. Header canonici NON più obbligatori. Vincolo 2 colonne separate invariato. R-01 NO SILENT DROPS: 4 errori espliciti (1-col / no-price-cand / tie-ambiguous / no-desc-cand). Backwards-compat 100% (header canonici matchano via alias al primo step). [CHG-2026-05-02-023]
- `_parse_csv` encoding fallback chain: `utf-8-sig → cp1252 → latin-1`. CSV Excel italiano (cp1252) ora parseable senza intervento CFO. `latin-1` finale è single-byte catch-all (mai solleva). [CHG-2026-05-02-024]
- `src/talos/ui/dashboard.py` — `_compute_cycle_kpis(result, *, velocity_target_days)` helper puro (cart_value/cash_profit/profit_cost_pct/n_orders/cycles_per_year/projected_annual_eur). + `_render_cycle_overview(*, budget, velocity_target_days, veto_threshold_pct, kpis, last_order_days_ago)` (3 pillole header + 4 KPI tile gradient + Proiezione Annua Compound). CSS +95 righe `.talos-pills-row` / `.talos-pill` / `.talos-tiles-cycle` / `.talos-tile-cycle` / `.talos-tile-projection` con animazioni `talos-fade-in`. Sostituisce `_render_metrics` post-`run_session` (legacy preservato per `_render_replay_result`). [CHG-2026-05-02-025]
- `tests/unit/test_dashboard_cycle_overview.py` — 8 test math F3 + edge cases (empty cart, single allocated, qty=0 excluded, velocity boundaries 7/15/30gg, ValueError R-01, compound math sentinel). [CHG-2026-05-02-025]
- `_render_tabs_section(*, cart_items, panchina_df)` con `st.tabs(['🛒 Carrello', '🪑 Panchina', '🤝 Comparazione Fornitori', '✅ Centrale Validazione'])`. Tab 3-4 = shell ADR-0022/0023 proposed. + `_render_action_buttons_shell` (3 bottoni disabled: Satura Cash/WhatsApp/Chiudi Ciclo). CSS +25 righe `.talos-shell-info` / icon / title / meta. Sostituisce chiamata `_render_cart_table` diretta nel main flow. [CHG-2026-05-02-026]
- `tests/unit/test_dashboard_tabs_shell.py` — 3 smoke test (import helpers + signature kw-only sentinel anti-regressione CHG-027). [CHG-2026-05-02-026]
- `_build_enriched_cart_view(result)` helper puro JOIN cart_items x enriched_df → 13 colonne ScalerBot-like + `_classify_velocity_badge` (placeholder ≥30/≥10/<10 monthly per Veloce/Buona/Lento, errata ADR-0018 con valori autoritativi Leader prevista FASE 2). Costante `_CART_COLUMN_ORDER` 17 colonne (13 visibili + locked). 6 sentinel `—` (HW_ID/PRODOTTO/FORNITORE/STOCK/MRG/A_M) shell CHG-028+ / risk-filters Arsenale. `_render_cart_table` aggiornato signature backwards-compat ma consuma 13-col view (era 6-col). [CHG-2026-05-02-027]
- `tests/unit/test_dashboard_cart_enriched.py` — 15 test (10 boundary velocity badge classification + 5 JOIN/sentinel/locked/empty/column order completeness sentinel). [CHG-2026-05-02-027]
- `fetch_asin_masters_or_empty(factory, asins, *, tenant_id)` graceful query AsinMaster ORM filtrata per ASIN cart list. + `_render_anagrafica_modal(factory, cart_items)` expander `📇 Anagrafica`. + `_build_ordine_strategia_csv(cart, *, budget, velocity, veto, saturation, cycle_kpis) -> bytes` (CSV audit con 8 righe `# key=value` metadata ciclo + cart 13-col). + `_render_export_ordine_strategia` CTA `type=primary`. + 4° bottone shell Override in `_render_action_buttons_shell`. Import `sqla_select` aggiunto. [CHG-2026-05-02-028]
- `tests/unit/test_dashboard_anagrafica_export.py` — 6 test puri (CSV content/empty/metadata-first/graceful None factory/empty asins/smoke import). [CHG-2026-05-02-028]

### Changed
- `_render_action_buttons_shell` ora 4 colonne (Override aggiunto come 4° shell). `cart_items_view` calcolato una sola volta nel main flow (anticipato per riuso in Anagrafica + Esporta CTA + tabs section). [CHG-2026-05-02-028]

### Proposed (in attesa ratifica Leader)
- `docs/decisions/ADR-0022-ghigliottina-tier-profit-filter.md` — gating profitto netto assoluto stratificato per tier di costo (10€/25€/50€). Pattern Arsenale 180k. [CHG-2026-05-02-029]
- `docs/decisions/ADR-0023-90-day-stress-test-filter.md` — gating resilienza prezzo storico (avg90 Keepa break-even). Pattern Arsenale 180k. [CHG-2026-05-02-029]
- `docs/decisions/ADR-0024-amazon-presence-filter.md` — hard veto Amazon BuyBox share > 25%. Pattern Arsenale 180k. [CHG-2026-05-02-029]

### Ratified (Active)
- ADR-0022 Ghigliottina ratificato `Active` con decisioni default Leader 2026-05-02 (affianca R-08, tier 10/25/50€). [CHG-2026-05-02-030]
- ADR-0023 90-Day Stress Test ratificato `Active` con decisioni default (window 90gg fisso, break-even, source `stats.avg90`). [CHG-2026-05-02-030]
- ADR-0024 Amazon Presence ratificato `Active` con decisioni default (threshold 25%, hard veto, ASIN nuovi → pass). [CHG-2026-05-02-030]

### Added (CHG-2026-05-02-031 — Amazon Presence implementazione)
- `src/talos/risk/` — 8° cluster applicativo (ADR-0013 area permessa). `__init__.py` re-export.
- `src/talos/risk/amazon_presence.py` — `AMAZON_PRESENCE_MAX_SHARE=0.25` + `passes_amazon_presence(share)` scalare + `is_amazon_dominant_mask(series)` vettoriale (NaN/None → False = pass). [CHG-2026-05-02-031]
- `src/talos/observability/events.py` — voce catalogo `vgp.amazon_dominant_seller` (asin/amazon_share/threshold) + costante `EVENT_VGP_AMAZON_DOMINANT_SELLER`. Catalogo ADR-0021 ora 21 eventi. [CHG-2026-05-02-031]
- `tests/unit/test_risk_amazon_presence.py` — 17 test (boundary inclusivo 0.0/0.25/0.2501/None + vettoriale + NaN handling + integrazione `compute_vgp_score` + telemetria `log_capture` LogCapture + backwards-compat sentinel). [CHG-2026-05-02-031]
- `tests/unit/test_events_catalog.py` — `_EXPECTED_EVENTS` esteso con `vgp.amazon_dominant_seller`. [CHG-2026-05-02-031]

### Changed (CHG-2026-05-02-031)
- `src/talos/vgp/score.py:compute_vgp_score` — kwarg opzionale `amazon_share_col: str = "amazon_buybox_share"`. Mask `amazon_dominant_mask` calcolata se colonna presente (graceful skip altrimenti). Composizione `blocked = kill | ~veto_passed | amazon_dominant`. Telemetria `vgp.amazon_dominant_seller` per ASIN vetati. Backwards-compat 100%: 953 test esistenti invariati. [CHG-2026-05-02-031]

### Added (CHG-2026-05-02-032 — 90-Day Stress Test implementazione)
- `src/talos/risk/stress_test.py` — `passes_90d_stress_test(*, buy_box_avg90, cost_eur, fee_fba_eur, referral_fee_rate)` scalare (riusa `cash_inflow_eur`, R-01 break-even). `is_stress_test_failed_mask(df, *, avg90_col, cost_col, fee_fba_col, referral_fee_col)` vettoriale (NaN avg90 → False = pass). [CHG-2026-05-02-032]
- `src/talos/observability/events.py` — voce catalogo `vgp.stress_test_failed` (asin/buy_box_avg90/cost) + costante `EVENT_VGP_STRESS_TEST_FAILED`. Catalogo ADR-0021 ora 22 eventi. [CHG-2026-05-02-032]
- `tests/unit/test_risk_stress_test.py` — 13 test (boundary break-even / NaN pass / vettoriale / integrazione vgp / telemetria / backwards-compat sentinel). [CHG-2026-05-02-032]
- `tests/unit/test_events_catalog.py` — `_EXPECTED_EVENTS` esteso con `vgp.stress_test_failed`. [CHG-2026-05-02-032]

### Changed (CHG-2026-05-02-032)
- `src/talos/vgp/score.py:compute_vgp_score` — kwarg opzionali `avg90_col`/`fee_fba_col`/`referral_fee_col`. Mask `stress_test_mask` calcolata SOLO se TUTTE le 4 colonne (avg90+cost+fee+referral) sono presenti (graceful skip altrimenti). Composizione `blocked = kill | ~veto_passed | amazon_dominant | stress_test_failed`. Telemetria `vgp.stress_test_failed`. Backwards-compat 100%: 970 test esistenti invariati. [CHG-2026-05-02-032]

### Added (CHG-2026-05-02-033 — Ghigliottina implementazione, chiusura risk-filters Arsenale 3/3)
- `src/talos/risk/ghigliottina.py` — costante `GHIGLIOTTINA_TIERS` `((50, 10), (150, 25), (inf, 50))` ratificata Leader. `min_profit_for_cost(cost) -> float` lookup. `passes_ghigliottina(*, cost_eur, cash_profit_eur)` scalare. `is_ghigliottina_failed_mask(df, *, cost_col, cash_profit_col)` vettoriale. [CHG-2026-05-02-033]
- `src/talos/observability/events.py` — voce catalogo `vgp.ghigliottina_failed` (asin/cost/cash_profit/min_required) + costante `EVENT_VGP_GHIGLIOTTINA_FAILED`. Catalogo ADR-0021 ora 23 eventi. [CHG-2026-05-02-033]
- `tests/unit/test_risk_ghigliottina.py` — 26 test (tier mapping boundary 9 cases + scalare 9 cases + vettoriale base + integrazione vgp default-on + AND con R-08 + telemetria + bypass disable). [CHG-2026-05-02-033]

### Changed (CHG-2026-05-02-033)
- `src/talos/vgp/score.py:compute_vgp_score` — kwarg `enable_ghigliottina: bool = True` (default Active per ADR-0022 AFFIANCA R-08) + `cost_col: str = "cost_eur"`. Mask `ghigliottina_mask` attiva sempre (cost+profit già required). Composizione `blocked = kill | ~veto_passed | amazon_dominant | stress_test_failed | ghigliottina`. Telemetria `vgp.ghigliottina_failed`. **Default-on backwards-compat verificata**: 983 test esistenti invariati (i golden Samsung-mini snapshot restano stabili perché qty/profit-ratio già passano entrambi i gate). [CHG-2026-05-02-033]

### Added (CHG-2026-05-02-034 — Errata ADR-0018 drops_30 V_tot upgrade)
- `src/talos/extract/velocity_estimator.py` — sentinel `V_TOT_SOURCE_DROPS_30 = "drops_30"`. + `estimate_v_tot_from_drops_30(drops) -> float` (gold-standard community: 1 drop ≈ 1 vendita). + parametro opzionale `drops_30: int | None = None` in `resolve_v_tot`. Gerarchia hybrid v2: CSV → drops_30 → bsr_estimate_mvp (placeholder) → default_zero. Pattern Arsenale 180k Dynamic Floor MVP completo. [CHG-2026-05-02-034]
- `tests/unit/test_velocity_estimator.py` — 8 test nuovi (estimate boundary 4 cases + resolve hybrid v2 priorità 4 cases). [CHG-2026-05-02-034]
- `docs/decisions/ADR-0018-algoritmo-vgp-tetris.md` — sezione `## Errata` voce CHG-034 (drops_30 promosso a fonte preferita). [CHG-2026-05-02-034]

### Changed (CHG-2026-05-02-034)
- `resolve_v_tot` signature estesa con `drops_30: int | None = None` kwarg opzionale. Caller esistenti (no kwarg) → behavior pre-CHG-034 invariato (backwards-compat 100% verificato: 1009 test esistenti pass invariati). [CHG-2026-05-02-034]

### Added (CHG-2026-05-02-035 — KeepaClient extension upstream Arsenale)
- `src/talos/io_/keepa_client.py` — `KeepaProduct` esteso con `drops_30: int | None = None`, `buy_box_avg90: Decimal | None = None`, `amazon_buybox_share: float | None = None`. + costante `_AMAZON_SELLER_ID = "ATVPDKIKX0DER"`. + helpers `_safe_int(value)` / `_safe_index(arr, index)`. `_LiveKeepaAdapter.query()` parsa `stats.salesRankDrops30` / `stats.avg90[1]` (NEW source) / `buyBoxStats[ATVPDKIKX0DER].percentageWon`. + 3 nuovi metodi `KeepaClient.fetch_drops_30(asin)` / `fetch_avg_price_90d(asin)` / `fetch_buybox_amazon_share(asin)` — **NON sollevano** su miss (ritornano None, dati ancillari). [CHG-2026-05-02-035]
- `src/talos/io_/fallback_chain.py` — `ProductData` esteso simmetricamente con 3 campi default None. `lookup_product` chiama i 3 nuovi `fetch_*` keepa e popola ProductData + audit `sources` per i campi non-None. [CHG-2026-05-02-035]
- `tests/unit/test_keepa_client.py` — 9 test nuovi (parsing 3 campi nuovi via mock + miss → None + integrazione fetch wrapper + retry skip + KeepaProduct default backwards-compat sentinel). [CHG-2026-05-02-035]
- `tests/unit/test_fallback_chain.py` — 4 test nuovi (lookup_product propagation 3 campi + sources audit + miss case + ProductData default sentinel + partial population). [CHG-2026-05-02-035]

### Out-of-scope (rimandato a CHG-036+)
- Propagation `ResolvedRow` + `listino_input.py` (`_fetch_buybox_live_or_none` tuple esteso).
- Propagation `build_listino_raw_from_resolved` → 3 nuove colonne nel listino_raw.
- Orchestrator `_enrich_listino` propagation → `enriched_df`.
- Integration test live con `KEEPA_API_KEY` reale (1-2 token Keepa).
Senza CHG-036, i 3 filtri Arsenale restano dormienti (nessuna colonna nel dataframe pipeline). CHG-035 chiude la prima metà del wiring (io_ layer pronto).

### Added (CHG-2026-05-02-036 — Propagation upstream Arsenale end-to-end)
- `src/talos/extract/asin_resolver.py:ResolutionCandidate` esteso con `drops_30`/`buy_box_avg90`/`amazon_buybox_share` (default None). `_LiveAsinResolver.resolve_description` propaga da `ProductData` (CHG-035) per ogni candidato SERP. [CHG-2026-05-02-036]
- `src/talos/ui/listino_input.py:ResolvedRow` esteso simmetricamente. + dataclass `_LiveLookupSnapshot` (sostituisce 3-tuple di `_fetch_buybox_live_or_none`). `_resolved_row_from_result` + `apply_candidate_overrides` propagation. [CHG-2026-05-02-036]
- `tests/unit/test_listino_input.py` — 4 test propagation puri (default None / colonne incluse / drops_30 → v_tot source / fields None se assenti). + `_FakeProductData` esteso. [CHG-2026-05-02-036]

### Changed (CHG-2026-05-02-036)
- `_fetch_buybox_live_or_none` signature: ritorna `_LiveLookupSnapshot` invece di `(buybox, bsr, notes)` 3-tuple. Cache hit branch in `resolve_listino_with_cache` aggiornato. [CHG-2026-05-02-036]
- `build_listino_raw_from_resolved` aggiunge al DataFrame le 3 colonne `drops_30`/`buy_box_avg90`/`amazon_buybox_share` + chiama `resolve_v_tot(drops_30=...)` (errata ADR-0018 CHG-034 ora **live**: drops_30 promosso a fonte preferita per stima v_tot quando disponibile). [CHG-2026-05-02-036]

### Pipeline Arsenale end-to-end CHIUSA
Con CHG-036, i 3 filtri pull-only (Amazon Presence/Stress Test/Ghigliottina) si attivano **automaticamente** quando `KEEPA_API_KEY` è configurata e il `lookup_callable` viene iniettato in `resolve_listino_with_cache`. La pipeline è ora: `Keepa.product() → ProductData → ResolutionCandidate → ResolvedRow → listino_raw (3 nuove colonne) → enriched_df (cascade) → compute_vgp_score (5 gate AND)`.

### Fixed (CHG-2026-05-02-037 — Hotfix defensive getattr ProductData)
- `src/talos/ui/listino_input.py:_fetch_buybox_live_or_none` legge i 5 attributi via `getattr(product, "<name>", None)` (defensive). [CHG-2026-05-02-037]
- `src/talos/extract/asin_resolver.py:_LiveAsinResolver.resolve_description` idem nel try-block lookup candidato SERP. [CHG-2026-05-02-037]
- Bug live Leader 2026-05-02 post-CHG-036: Streamlit `@st.cache_data` serviva `ProductData` pre-CHG-035 → `AttributeError`. Fix tollerante a oggetti legacy. [CHG-2026-05-02-037]
- `tests/unit/test_listino_input.py` — 1 test sentinel `_LegacyProductDataStub` anti-regressione hotfix. [CHG-2026-05-02-037]

### Fixed (CHG-2026-05-02-038 — Hotfix defensive resolve_v_tot kwarg)
- `src/talos/ui/listino_input.py:build_listino_raw_from_resolved` wrappa `resolve_v_tot(drops_30=...)` con `try/except TypeError` + fallback signature legacy (senza drops_30). [CHG-2026-05-02-038]
- Bug live Leader 2026-05-02 post-CHG-037: Streamlit hot-reload skew (listino_input.py reloaded ma velocity_estimator.py no) → `TypeError unexpected kwarg drops_30`. [CHG-2026-05-02-038]
- `tests/unit/test_listino_input.py` — 1 sentinel `monkeypatch` resolve_v_tot legacy stub anti-regressione hotfix. [CHG-2026-05-02-038]

### Reverted (CHG-2026-05-02-042 — Revert CHG-039/040/041)
- 5 commit revertati in singolo commit unificato: `4813222` CHG-039 (golden ground truth ScalerBot500K), `bf75142` backfill CHG-040, `5bfa844` CHG-040 (errata ADR-0017 fee_fba atomica Keepa), `39b261a` backfill CHG-039, `4717755` CHG-041 (proiezione compound r-cap). Decisione Leader 2026-05-02 round 7+ post-confronto file `ordine_scaler500k (22).xlsx`. [CHG-2026-05-02-042]
- ADR-0017 sezione `## Errata` rimossa: decisione α'' originale CHG-2026-05-01-015 ripristinata (`_LiveKeepaAdapter.query()` ritorna SEMPRE `fee_fba_eur=None`; `fee_fba_manual` L11b verbatim Frozen Samsung resta verbatim). [CHG-2026-05-02-042]
- Pipeline propagation Keepa→ResolutionCandidate→ResolvedRow per `fee_fba_eur` rimossa. Proiezione compound torna a `(1+r_actual)^N` senza cap (`_PROJECTION_R_MAX_CAP` rimosso). Golden test ground truth ScalerBot500K rimosso (file Leader resta su disco non versionato). [CHG-2026-05-02-042]
- Working tree ripristinato a `c689799` pre-CHG-039. Test count: 894 PASS unit/gov/golden + integration (-16 vs 1052 post-CHG-041 atteso). Quality gate ruff/format/mypy strict puliti. [CHG-2026-05-02-042]

## [0.22.0] — 2026-04-30 — 🎯 Schema Allegato A 10/10 COMPLETO: audit_log + trigger

`AuditLog` (tabella `audit_log`) è la decima e ultima tabella dell'Allegato A. **Conclude la copertura dello schema verbatim** dell'ADR-0015. Append-only registry con funzione PL/pgSQL `record_audit_log()` + 3 trigger AFTER (storico_ordini, locked_in, config_overrides). Primi campi JSONB del DB (`before_data`, `after_data`). Revision Alembic `6e03f2a4f5a3`.

### Added
- `src/talos/persistence/models/audit_log.py` — `class AuditLog(Base)` con 8 colonne (id BigInt PK, actor/table_name TEXT NOT NULL, op CHAR(1) NOT NULL, row_id BigInt NULL, before_data/after_data JSONB NULL, at TIMESTAMPTZ default NOW NOT NULL). No FK. Type hint JSONB: `Mapped[dict[str, Any] | None]`.
- `migrations/versions/6e03f2a4f5a3_create_audit_log_with_triggers.py` — Alembic revision (catena: `Revises: e7a92c0260fa`). `op.create_table` + `op.execute` per: funzione PL/pgSQL `record_audit_log()` (cattura `session_user`, mappa `TG_OP` su 'I'/'U'/'D', serializza OLD/NEW via `row_to_json(...)::jsonb`) + 3 trigger `AFTER INSERT OR UPDATE OR DELETE ON {table}` su tabelle critiche. Downgrade simmetrico.
- `tests/unit/test_audit_log_model.py` — 19 test invarianti incluso 4 schema-aware sul file di migration (funzione, mapping I/U/D, 3 trigger, downgrade).
- `docs/changes/2026-04-30-018-audit-log-model-with-triggers.md`

### Changed
- `src/talos/persistence/models/__init__.py` — re-export `AuditLog`
- `src/talos/persistence/__init__.py` — re-export `AuditLog`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (17 source file) → puliti
- `pytest tests/unit tests/governance -q` → **153 passed** (era 134, +19)
- `alembic upgrade --sql` → DDL + funzione PL/pgSQL + 3 trigger coerenti con Allegato A

### Out-of-scope (esplicitamente dichiarato in CHG)
- Ruoli `talos_admin`/`talos_app`/`talos_audit` e `GRANT INSERT` / `REVOKE UPDATE,DELETE` su `audit_log`: richiedono setup di bootstrap esterno (futuro CHG su `scripts/db-bootstrap.sh`). In sviluppo locale (utente superuser/admin) la tabella è scrivibile da chiunque — append-only effettivo solo in produzione.

## [0.21.0] — 2026-04-30 — Nona tabella Allegato A: locked_in (R-04 Manual Override + RLS)

`LockedInItem` (tabella `locked_in`) è la nona delle 10 tabelle dell'Allegato A. R-04 Manual Override: ASIN che il CFO ha forzato a Priorità ∞. Standalone (no FK). Terza tabella con RLS Zero-Trust — pattern riusato verbatim da `config_overrides` (CHG-012) e `storico_ordini` (CHG-016). Revision Alembic `e7a92c0260fa`.

### Added
- `src/talos/persistence/models/locked_in_item.py` — `class LockedInItem(Base)` con 6 colonne (id BigInt PK, asin CHAR(10) NOT NULL, qty_min Integer NOT NULL, notes Text NULL, created_at TIMESTAMPTZ default NOW NOT NULL, tenant_id BigInt default 1 NOT NULL). No FK, no relationship.
- `migrations/versions/e7a92c0260fa_create_locked_in_with_rls.py` — Alembic revision (catena: `Revises: a074ee67895c`). `op.create_table` + `op.execute` per `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation`.
- `tests/unit/test_locked_in_item_model.py` — 15 test invarianti incluso `test_no_foreign_keys` esplicito + 3 schema-aware sul file di migration.
- `docs/changes/2026-04-30-017-locked-in-model-with-rls.md`

### Changed
- `src/talos/persistence/models/__init__.py` — re-export `LockedInItem`
- `src/talos/persistence/__init__.py` — re-export `LockedInItem`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (16 source file) → puliti
- `pytest tests/unit tests/governance -q` → **134 passed** (era 119, +15)
- `alembic upgrade --sql` → DDL + RLS + POLICY coerenti con Allegato A

## [0.20.0] — 2026-04-30 — Ottava tabella Allegato A: storico_ordini (R-03 registro permanente + RLS)

`StoricoOrdine` (tabella `storico_ordini`) è l'ottava delle 10 tabelle dell'Allegato A. **R-03 ORDER-DRIVEN MEMORY**: registro permanente degli ordini. Differenza chiave: FK `session_id`/`cart_item_id` **senza** `ON DELETE CASCADE` (aderenza letterale Allegato A — un registro contabile non si cascade-cancella). Seconda tabella con RLS Zero-Trust (pattern identico a `config_overrides`). Revision Alembic `a074ee67895c`.

### Added
- `src/talos/persistence/models/storico_ordine.py` — `class StoricoOrdine(Base)` con 8 colonne (id BigInt PK, session_id+cart_item_id BigInt FK NOT NULL **senza CASCADE**, asin CHAR(10) NOT NULL, qty Integer NOT NULL, unit_cost_eur Numeric(12,2) NOT NULL, ordered_at TIMESTAMPTZ default NOW NOT NULL, tenant_id BigInt default 1 NOT NULL). Relationship `session: Mapped[AnalysisSession]` + `cart_item: Mapped[CartItem]` (no `passive_deletes`/cascade — registro permanente).
- `migrations/versions/a074ee67895c_create_storico_ordini_with_rls.py` — Alembic revision (catena: `Revises: 618105641c27`). `op.create_table` con 2 `sa.ForeignKey` **senza `ondelete=`** + `op.execute` per `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation`. Downgrade simmetrico con `DROP POLICY IF EXISTS` + `DISABLE`.
- `tests/unit/test_storico_ordine_model.py` — 17 test invarianti incluso 2 test espliciti per `fk.ondelete is None` + 3 schema-aware sul file di migration per RLS / policy / downgrade.
- `docs/changes/2026-04-30-016-storico-ordini-model-with-rls.md`

### Changed
- `src/talos/persistence/models/analysis_session.py` — relationship `storico_ordini: Mapped[list[StoricoOrdine]]` aggiunta **senza `passive_deletes`** (registro permanente)
- `src/talos/persistence/models/cart_item.py` — relationship `storico_ordini: Mapped[list[StoricoOrdine]]` aggiunta **senza `passive_deletes`**
- `src/talos/persistence/models/__init__.py` — re-export `StoricoOrdine`
- `src/talos/persistence/__init__.py` — re-export `StoricoOrdine`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (15 source file) → puliti
- `pytest tests/unit tests/governance -q` → **119 passed** (era 102, +17)
- `alembic upgrade --sql` → DDL + 2 FK senza CASCADE + RLS + POLICY coerenti con Allegato A

## [0.19.0] — 2026-04-30 — Settima tabella Allegato A: panchina_items (R-09 archivio)

`PanchinaItem` (tabella `panchina_items`) è la settima delle 10 tabelle dell'Allegato A. R-09 archivio degli ASIN con `vgp_score > 0` non scelti per saturazione del budget. Schema isomorfo a `cart_items` ma snello (4 colonne, no `unit_cost_eur`/`locked_in`). Revision Alembic `618105641c27`.

### Added
- `src/talos/persistence/models/panchina_item.py` — `class PanchinaItem(Base)` con 4 colonne (id BigInt PK, session_id+vgp_result_id BigInt FK CASCADE, qty_proposed Integer NOT NULL). Relationship triple aggiornate.
- `migrations/versions/618105641c27_create_panchina_items.py` — Alembic revision (catena: `Revises: fa6408788e73`).
- `tests/unit/test_panchina_item_model.py` — 10 test invarianti
- `docs/changes/2026-04-30-015-panchina-items-model.md`

### Changed
- `src/talos/persistence/models/analysis_session.py` — relationship `panchina_items: Mapped[list[PanchinaItem]]` aggiunta
- `src/talos/persistence/models/vgp_result.py` — relationship `panchina_items: Mapped[list[PanchinaItem]]` aggiunta
- `src/talos/persistence/models/__init__.py` — re-export `PanchinaItem`
- `src/talos/persistence/__init__.py` — re-export `PanchinaItem`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (14 source file) → puliti
- `pytest tests/unit tests/governance -q` → **102 passed** (era 92, +10)
- `alembic upgrade --sql` → DDL + 2 FK CASCADE coerenti con Allegato A

## [0.18.0] — 2026-04-30 — Sesta tabella Allegato A: cart_items (carrello Tetris)

`CartItem` (tabella `cart_items`) è la sesta delle 10 tabelle dell'Allegato A. Output principale della sessione: il carrello finale del Tetris allocator. Doppia FK CASCADE + flag `locked_in` (R-04 Manual Override) con default `false` (NOT NULL implicito da regola CHG-010). Revision Alembic `fa6408788e73`.

### Added
- `src/talos/persistence/models/cart_item.py` — `class CartItem(Base)` con 6 colonne (id BigInt PK, session_id+vgp_result_id BigInt FK CASCADE, qty Integer NOT NULL, unit_cost_eur Numeric(12,2) NOT NULL, locked_in Boolean default false NOT NULL). Relationship `session: Mapped[AnalysisSession]` + `vgp_result: Mapped[VgpResult]`.
- `migrations/versions/fa6408788e73_create_cart_items.py` — Alembic revision (catena: `Revises: c9527f017d5c`). `op.create_table` con 2 `sa.ForeignKey(..., ondelete="CASCADE")`.
- `tests/unit/test_cart_item_model.py` — 13 test invarianti (9 strutturali + 2 relationship + 2 costruzioni)
- `docs/changes/2026-04-30-014-cart-items-model.md`
- Tag annotato `checkpoint/2026-04-30-02` su `37fdc7e` (6 CHG significativi post checkpoint-01)

### Changed
- `src/talos/persistence/models/analysis_session.py` — relationship `cart_items: Mapped[list[CartItem]]` aggiunta. Forward reference `CartItem` in `TYPE_CHECKING`.
- `src/talos/persistence/models/vgp_result.py` — relationship `cart_items: Mapped[list[CartItem]]` aggiunta. Forward reference in `TYPE_CHECKING`.
- `src/talos/persistence/models/__init__.py` — re-export `CartItem`
- `src/talos/persistence/__init__.py` — re-export `CartItem`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (13 source file) → puliti
- `pytest tests/unit tests/governance -q` → **92 passed** (era 79, +13)
- `alembic upgrade --sql` → DDL + 2 FK CASCADE + `locked_in BOOLEAN DEFAULT false NOT NULL` coerenti con Allegato A

## [0.17.0] — 2026-04-30 — Quinta tabella Allegato A: vgp_results (nucleo decisore)

`VgpResult` (tabella `vgp_results`) è la quinta delle 10 tabelle dell'Allegato A. **Nucleo del decisore VGP**. Primo modello con **doppia FK** (entrambe ON DELETE CASCADE) e primo con **indice composito direzionale** `(session_id, vgp_score DESC)` per supportare le query "top-N per session" del Tetris allocator. Revision Alembic `c9527f017d5c` in catena.

### Added
- `src/talos/persistence/models/vgp_result.py` — `class VgpResult(Base)` con 15 colonne dell'Allegato A: id BigInt PK, session_id/listino_item_id BigInt FK NOT NULL ON DELETE CASCADE, asin CHAR(10) NOT NULL, 7 campi `Numeric` con precision/scale specifici (`roi_pct`/`8,4`, `velocity_monthly`/`12,4`, `cash_profit_eur`/`12,2`, `roi_norm`/`velocity_norm`/`cash_profit_norm`/`vgp_score` `6,4`), `veto_roi_passed`/`kill_switch_triggered` Boolean nullable, `qty_target`/`qty_final` Integer nullable. `__table_args__` con `Index("idx_vgp_session_score", "session_id", text("vgp_score DESC"))`. Relationship `session: Mapped[AnalysisSession]` + `listino_item: Mapped[ListinoItem]`.
- `migrations/versions/c9527f017d5c_create_vgp_results.py` — Alembic revision (catena: `Revises: 027a145f76a8`). `op.create_table` con 2 `sa.ForeignKey(..., ondelete="CASCADE")` + `op.create_index(..., ["session_id", sa.text("vgp_score DESC")])`.
- `tests/unit/test_vgp_result_model.py` — 16 test invarianti (14 strutturali + 1 schema-aware per `vgp_score DESC` + 2 relationship + 2 costruzioni runtime)
- `docs/changes/2026-04-30-013-vgp-results-model.md`

### Changed
- `src/talos/persistence/models/analysis_session.py` — aggiunta relationship `vgp_results: Mapped[list[VgpResult]] = relationship(back_populates="session", passive_deletes=True)`. Forward reference `VgpResult` in `TYPE_CHECKING`.
- `src/talos/persistence/models/listino_item.py` — aggiunta relationship `vgp_results: Mapped[list[VgpResult]] = relationship(back_populates="listino_item", passive_deletes=True)`. Forward reference `VgpResult` in `TYPE_CHECKING`.
- `src/talos/persistence/models/__init__.py` — re-export anche `VgpResult`
- `src/talos/persistence/__init__.py` — re-export anche `VgpResult`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (12 source file) → puliti
- `pytest tests/unit tests/governance -q` → **79 passed** (era 63, +16)
- `alembic upgrade --sql` → DDL + 2 FK CASCADE + `CREATE INDEX idx_vgp_session_score ON vgp_results (session_id, vgp_score DESC)` coerenti con Allegato A

## [0.16.0] — 2026-04-30 — Quarta tabella Allegato A: config_overrides (primo con RLS + UNIQUE INDEX)

`ConfigOverride` (tabella `config_overrides`) è la quarta delle 10 tabelle dell'Allegato A. **Primo modello con Row-Level Security (RLS) Zero-Trust attiva** + **primo con indice UNIQUE composito a 4 colonne**. Pattern RLS ratificato per le 3 tabelle che lo richiedono nell'Allegato A (`storico_ordini`, `locked_in`, `config_overrides`). Revision Alembic `027a145f76a8` in catena.

### Added
- `src/talos/persistence/models/config_override.py` — `class ConfigOverride(Base)` con 8 colonne (id BigInt PK, scope/key TEXT NOT NULL, scope_key/value_numeric/value_text NULL, value_numeric NUMERIC(12,4), updated_at TIMESTAMPTZ default NOW NOT NULL, tenant_id BigInt default 1 NOT NULL) + indice **UNIQUE composito** `idx_config_unique` su `(tenant_id, scope, scope_key, key)`.
- `migrations/versions/027a145f76a8_create_config_overrides_with_rls.py` — Alembic revision (catena: `Revises: d6ab9ffde2a2`). `op.create_table` + `op.create_index(unique=True)` + `op.execute` per `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)`. Downgrade simmetrico con `DROP POLICY IF EXISTS` + `DISABLE`.
- `tests/unit/test_config_override_model.py` — 15 test invarianti (12 sul mapper + 3 **schema-aware sul file di migration** che verificano la presenza di RLS / policy / downgrade)
- `docs/changes/2026-04-30-012-config-overrides-model-with-rls.md`

### Changed
- `src/talos/persistence/models/__init__.py` — re-export anche `ConfigOverride`
- `src/talos/persistence/__init__.py` — re-export anche `ConfigOverride`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (11 source file) → puliti
- `pytest tests/unit tests/governance -q` → **63 passed** (era 48, +15)
- `alembic upgrade --sql` → DDL + `CREATE UNIQUE INDEX` + `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation` coerenti con Allegato A

## [0.15.0] — 2026-04-30 — Terza tabella Allegato A: listino_items (primo con FK + relationship)

`ListinoItem` (tabella `listino_items`) è la terza delle 10 tabelle dell'Allegato A. **Primo modello con Foreign Key** (`session_id → sessions.id ON DELETE CASCADE`) e prima **relationship bidirezionale** (`AnalysisSession.listino_items ↔ ListinoItem.session`). Pattern `passive_deletes=True` lato ORM (cascade gestito dal DB). Revision Alembic `d6ab9ffde2a2` in catena.

### Added
- `src/talos/persistence/models/listino_item.py` — `class ListinoItem(Base)` con 8 colonne dell'Allegato A: id BigInt PK, session_id BigInt FK NOT NULL (`ondelete=CASCADE`), asin CHAR(10) NULL **senza FK** (Allegato A letterale: match in-flight via Keepa/scraping), raw_title TEXT NOT NULL, cost_eur NUMERIC(12,2) NOT NULL, qty_available Integer NULL, match_status TEXT NULL, match_reason TEXT NULL. Indice `idx_listino_session` su `session_id`. Relationship `session: Mapped[AnalysisSession]` con `back_populates`.
- `migrations/versions/d6ab9ffde2a2_create_listino_items.py` — Alembic revision (catena: `Revises: d4a7e3cefbb1`). `op.create_table` con `sa.ForeignKey(..., ondelete="CASCADE")` + `op.create_index`.
- `tests/unit/test_listino_item_model.py` — 12 test invarianti (10 strutturali + 1 relationship bidirezionale + 1 costruzione)
- `docs/changes/2026-04-30-011-listino-items-model-with-fk.md`

### Changed
- `src/talos/persistence/models/analysis_session.py` — aggiunta relationship inversa `listino_items: Mapped[list[ListinoItem]] = relationship(back_populates="session", passive_deletes=True)`. Import `relationship`. Forward reference `ListinoItem` in `TYPE_CHECKING`.
- `src/talos/persistence/models/__init__.py` — re-export anche `ListinoItem`
- `src/talos/persistence/__init__.py` — re-export anche `ListinoItem`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (10 source file) → puliti
- `pytest tests/unit tests/governance -q` → **48 passed** (era 36, +12)
- `alembic upgrade head --sql` → DDL `listino_items` con `FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE` + indice `idx_listino_session` coerenti con Allegato A

## [0.14.1] — 2026-04-30 — Errata Corrige ADR-0015 (regola "DEFAULT → NOT NULL" ratificata)

Risolve la open question dichiarata in CHG-009. Decisione esplicita del Leader (risoluzione (a)): ratifica formale della convenzione "Qualsiasi colonna definita con un `DEFAULT` in Allegato A implica automaticamente il vincolo `NOT NULL` (`nullable=False`)" per garantire allineamento DB/Typing. I modelli esistenti (`AnalysisSession`, `AsinMaster`) erano già conformi: nessun rework di codice.

### Changed
- `docs/decisions/ADR-0015-stack-persistenza.md`:
  - Frontmatter `errata:` esteso con voce CHG-010.
  - Nuova sezione "Convenzione interpretativa" inserita prima del DDL dell'Allegato A.
  - Sezione `## Errata` in coda con descrizione + motivazione.

### Added
- `docs/changes/2026-04-30-010-errata-adr-0015-default-implies-not-null.md`

## [0.14.0] — 2026-04-30 — Seconda tabella Allegato A: asin_master (anagrafica ASIN)

`AsinMaster` (tabella `asin_master`) è la seconda delle 10 tabelle dell'Allegato A. Lookup table standalone (no FK) con tutti i campi anagrafici e di connettività. Revision Alembic `d4a7e3cefbb1` in catena alla `9d9ebe778e40` di CHG-008. Migration validata offline.

### Added
- `src/talos/persistence/models/asin_master.py` — `class AsinMaster(Base)` con 11 colonne (asin CHAR(10) PK, title/brand TEXT NOT NULL, model/connectivity/color_family/category_node TEXT NULL, rom_gb/ram_gb Integer NULL, enterprise Boolean default false NOT NULL, last_seen_at TIMESTAMPTZ default NOW NOT NULL) + indice secondario `idx_asin_brand_model` su (brand, model)
- `migrations/versions/d4a7e3cefbb1_create_asin_master.py` — Alembic revision (catena: `Revises: 9d9ebe778e40`)
- `tests/unit/test_asin_master_model.py` — 11 test invarianti (tablename, columns set, PK CHAR(10), NOT NULL, nullable, defaults, indice, costruzione runtime)
- `docs/changes/2026-04-30-009-asin-master-model.md`

### Changed
- `src/talos/persistence/models/__init__.py` — re-export anche `AsinMaster`
- `src/talos/persistence/__init__.py` — re-export anche `AsinMaster`

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (9 source file) → puliti
- `pytest tests/unit tests/governance -q` → **36 passed**
- `alembic upgrade head --sql` → DDL `asin_master` + indice `idx_asin_brand_model` coerente con Allegato A

### Open question per il Leader
- L'Allegato A di ADR-0015 non prescrive `NOT NULL` esplicito su `started_at` (CHG-008), `enterprise`, `last_seen_at` (CHG-009). I modelli applicano la convenzione "colonna con `server_default` valido → `nullable=False` nell'ORM" per coerenza interna e chiarezza tipi Python. Va ratificata via errata corrige di ADR-0015 (chiarisce la convenzione) o errata inversa sui modelli (strict letterale).

## [0.13.0] — 2026-04-30 — Primo modello concreto + initial migration (sessions, Allegato A)

Nucleo centrale del DB pronto. `AnalysisSession` (tabella `sessions`, 7 colonne dell'Allegato A) è il primo dei 10 modelli prescritti da ADR-0015. Migration Alembic `9d9ebe778e40` validata in offline mode (`alembic upgrade head --sql`): DDL output coerente verbatim con l'Allegato A. Tag `checkpoint/2026-04-30-01` su HEAD pre-CHG-008 (5 CHG significativi post stack-frozen).

### Added
- `src/talos/persistence/models/__init__.py` — re-export `AnalysisSession`
- `src/talos/persistence/models/analysis_session.py` — model con `__tablename__ = "sessions"`, tipi `Mapped[T]` per le 7 colonne dell'Allegato A
- `migrations/versions/9d9ebe778e40_create_sessions.py` — initial Alembic revision
- `tests/unit/test_analysis_session_model.py` — 9 test invarianti (tablename, columns set, tipi, default, nullable)
- `docs/changes/2026-04-30-008-sessions-model-initial-migration.md`
- Tag annotato `checkpoint/2026-04-30-01` su `0f8f40a`

### Changed
- `src/talos/persistence/__init__.py` — re-export anche `AnalysisSession`
- `tests/unit/test_persistence_skeleton.py` — `test_base_metadata_no_tables_yet` → `test_base_metadata_has_registered_tables` (asserzione invertita)
- `pyproject.toml` — `[tool.ruff.lint.per-file-ignores]` aggiunge `"src/talos/persistence/models/**" = ["TC003"]` (SQLAlchemy 2.0 `Mapped[T]` richiede tipi runtime, conflitto noto con TC003)
- `alembic.ini` — sezione `[post_write_hooks]` corretta (`type = exec` + `executable = ruff` invece di `console_scripts/entrypoint`)

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (8 source file) → puliti
- `pytest tests/unit tests/governance -q` → **25 passed**
- `alembic upgrade head --sql` → DDL coerente con Allegato A (verificato a vista)

## [0.12.0] — 2026-04-30 — Persistence skeleton (SQLAlchemy 2.0 + Alembic + plugin mypy)

Primo passo verso ADR-0015. Aggiunge SQLAlchemy 2.0, Alembic e psycopg come dipendenze runtime, attiva il plugin `sqlalchemy[mypy]` di ADR-0014, introduce la `DeclarativeBase` e la struttura minima `migrations/`. **No modelli concreti, no DDL, no Postgres**: step di preparazione.

### Added
- `src/talos/persistence/__init__.py` — re-export di `Base`
- `src/talos/persistence/base.py` — `class Base(DeclarativeBase)` (SQLAlchemy 2.0 typed mapping)
- `alembic.ini` — config Alembic in root: `script_location = migrations`, `prepend_sys_path = .`, post-write hook `ruff_format`, URL placeholder (sostituita a runtime da `TALOS_DB_URL`)
- `migrations/env.py` — `target_metadata = Base.metadata` + override URL da env var
- `migrations/script.py.mako` — template revision compatibile mypy strict + ruff
- `migrations/versions/.gitkeep`
- `tests/unit/test_persistence_skeleton.py` — 3 test invarianti (Base subclasses DeclarativeBase, has metadata, no tables yet)
- `docs/changes/2026-04-30-007-persistence-skeleton.md`

### Changed
- `pyproject.toml` — `[project].dependencies` ora include `sqlalchemy[mypy]>=2.0.30,<2.1`, `alembic>=1.13.0,<2`, `psycopg[binary]>=3.2.0,<4`. `[tool.mypy].plugins = ["sqlalchemy.ext.mypy.plugin"]` attivato
- `uv.lock` — sqlalchemy 2.0.49, alembic 1.18.4, psycopg 3.3.3, psycopg-binary 3.3.3, greenlet, mako, markupsafe lockate

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (6 source file con plugin SQLAlchemy attivo) → puliti
- `pytest tests/unit tests/governance -q` → **15 passed**
- `alembic --raiseerr heads` → exit 0, output vuoto (atteso allo skeleton)

## [0.11.0] — 2026-04-30 — Primo modulo applicativo: observability (configure_logging + catalogo eventi)

`src/talos/observability/` ottiene la sua prima implementazione concreta: configurazione `structlog` aderente ad ADR-0021, catalogo dei 10 eventi canonici come fonte di verità statica, helper di session context. Sblocca la disciplina R-01 NO SILENT DROPS dinamica (test governance attivo).

### Added
- `src/talos/observability/events.py` — `CANONICAL_EVENTS: Final[dict[str, tuple[str, ...]]]` con le 10 voci di ADR-0021 + 10 costanti `Final[str]` (`EVENT_*`) per uso applicativo
- `src/talos/observability/logging_config.py` — `configure_logging(level, json_output)` + `bind_session_context(...)` + `clear_session_context()`. Pipeline structlog: `contextvars.merge_contextvars → add_log_level → TimeStamper(iso) → StackInfoRenderer → format_exc_info → renderer`
- `tests/unit/test_logging_config.py` — 6 test con `LogCapture`
- `tests/unit/test_events_catalog.py` — 2 test invarianti del catalogo
- `tests/governance/test_log_events_catalog.py` — R-01 dinamico (scansiona `src/talos/`, fallisce se trova `.drop`/`.skip`/`continue` senza evento canonico)
- `docs/changes/2026-04-30-006-observability-configure-logging.md`

### Changed
- `src/talos/observability/__init__.py` — re-export delle API pubbliche (`CANONICAL_EVENTS`, `configure_logging`, `bind_session_context`, `clear_session_context`)
- `pyproject.toml` — `[project].dependencies` ora include `structlog>=24.4.0` (prima dipendenza runtime). Commento spiega la sequenza modulo-per-modulo per le altre dipendenze applicative
- `uv.lock` — `structlog==25.5.0` lockato

### Quality gate verde
- `ruff check` / `ruff format --check` / `mypy src/` (4 source file) → puliti
- `pytest tests/unit tests/governance -q` → **12 passed** (2 smoke + 6 logging + 2 catalog + 1 no-root + 1 governance log)

## [0.10.1] — 2026-04-30 — Prima pipeline CI (server-side quality gate)

Estende il quality gate locale (CHG-004) a GitHub Actions. Errata Corrige di ADR-0020 documenta il rollout staging dei 4 workflow prescritti dall'ADR.

### Added
- `.github/workflows/ci.yml` — 3 job server-side:
  - `quality-gates` (replica del `pre-commit-app` locale: ruff check + ruff format check + mypy + pytest unit+governance)
  - `structure-check` (verifica ADR-0013 8 aree consentite in `src/talos/` + ADR INDEX sync)
  - `governance-checks` (hook eseguibili + sezioni ADR obbligatorie su tutti gli ADR del repo)
- `docs/changes/2026-04-30-005-ci-base-github-actions.md`

### Changed
- `docs/decisions/ADR-0020-cicd-github-actions.md`: errata corrige (rollout staging documentato — `tests` job + `gitnexus.yml` + `release.yml` + `hooks-check.yml` rinviati a CHG dedicati alla loro maturazione). Frontmatter `errata:` esteso con voce CHG-005.

## [0.10.0] — 2026-04-30 — Primo commit di codice applicativo (bootstrap minimale)

Sblocco fase codice. Concretizzazione dei path vincolanti di ADR-0013 (`src-layout`) e attivazione del quality gate di ADR-0014. Zero funzionalità di prodotto: solo l'ossatura installabile e testabile su cui costruire i moduli successivi modulo per modulo.

### Added
- `pyproject.toml` — Python 3.11-3.12, dev tools (ruff/mypy/pytest/hypothesis/pytest-cov), config completi di tutti i tool secondo ADR-0014 (ruff `select=ALL` con 7 ignore motivati, mypy `strict=true`, pytest marker `unit/integration/golden/governance/slow`)
- `uv.lock` (310 righe) — lock riproducibile da `uv sync --all-groups`
- `src/talos/__init__.py` — `__version__ = "0.1.0"`
- `src/talos/observability/__init__.py` — stub modulo (configure_logging arriverà in CHG dedicato a ADR-0021)
- `tests/conftest.py` — skeleton
- `tests/unit/test_smoke.py` — 2 test: `test_talos_importable`, `test_talos_version_exposed`
- `tests/governance/test_no_root_imports.py` — implementa il "Test di Conformità" di ADR-0013 (vieta `from src.` / `import src.`)
- `scripts/hooks/pre-commit-app` — pre-commit applicativo (ruff check + ruff format check + mypy + pytest unit+governance), invocato dal `pre-commit` di governance via gancio CHG-003
- `scripts/setup-dev.sh` — onboarding idempotente (install uv → install Python 3.11 → uv sync → setup-hooks)
- `README.md` — setup, struttura, workflow, comandi rapidi
- `docs/changes/2026-04-30-004-bootstrap-codice-minimale.md`

### Changed
- `.gitignore` esteso con esclusioni standard Python: `__pycache__/`, `*.py[cod]`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage*`, `htmlcov/`

### Quality gate verde end-to-end
- `ruff check src/ tests/` → All checks passed
- `ruff format --check src/ tests/` → 5 files already formatted
- `mypy src/` → no issues found in 2 source files
- `pytest tests/unit tests/governance -q` → 3 passed
- **`bash scripts/hooks/pre-commit-app`** invocato automaticamente dal `pre-commit` governance al commit reale → PASS

## [0.9.1] — 2026-04-30 — Errata Corrige ADR-0006 (hooks v2)

Hardening governance pre-bootstrap codice. **Errata Corrige di ADR-0006** (meccanismo ADR-0009) per allineare testo + hook eseguibili alle estensioni già ratificate da ADR-0014 e ADR-0020 nella validazione bulk del giorno (CHG-2026-04-30-001) ma rimaste "side-decision sotto-dichiarate". Errata corrige secondarie su ADR-0014 e ADR-0020 per allineamento testuale dello stato corrente.

### Changed
- `scripts/hooks/pre-commit`: nuova **Verifica 3** dopo i check governance — se in staging ci sono `*.py`, `pyproject.toml` o `uv.lock`, invoca `scripts/hooks/pre-commit-app` (ADR-0014) se eseguibile; **graceful skip** se assente (per supportare la fase pre-bootstrap codice senza falsi blocker).
- `scripts/hooks/commit-msg`: nuovo **bypass cumulativo** per il bot CI di reindex GitNexus — marker `[skip ci]` **+** author email `github-actions[bot]@users.noreply.github.com`. Marker da solo non basta (commit umani con `[skip ci]` continuano a essere validati normalmente).
- `docs/decisions/ADR-0006-git-hooks-enforcement.md`: frontmatter `errata:` esteso; sezioni "Hook 1: pre-commit" e "Hook 2: commit-msg" estese con nota sulle Verifiche 3 ed Esenzioni; sezione `## Errata` aggiunta in coda con riferimento a CHG-003.
- `docs/decisions/ADR-0014-stack-linguaggio-quality-gates.md`: errata corrige (frase "verrà aggiornato... alla prima introduzione" → "è stato aggiornato in CHG-003... graceful skip"); frontmatter `errata:` esteso; sezione `## Errata` aggiunta.
- `docs/decisions/ADR-0020-cicd-github-actions.md`: errata corrige (frase "va aggiornato... applicata alla prima introduzione di codice CI" → stato corrente + dettaglio bypass cumulativo); frontmatter `errata:` esteso; sezione `## Errata` aggiunta.

### Added
- `docs/changes/2026-04-30-003-errata-adr-0006-hooks-extension.md`

## [0.9.0] — 2026-04-30 — Stack `Frozen` (ADR di stack 0013–0021 promulgati)

Pietra miliare. Tutte le aree precedentemente in gap (stack tecnologico, struttura, CI/CD, test strategy applicativa, logging) sono ora coperte da ADR `Active`. Repo in stato di **purezza infrastrutturale**: zero codice applicativo, ADR cardine pronti per il bootstrap del primo modulo. **HARD STOP** richiesto dal Leader post-tag `milestone/stack-frozen-v0.9.0` per consentire il clone di `Atena-Core`.

### Added
- `ADR-0013`: Project Structure — `src-layout` + `uv` come tool packaging, 8 aree consentite sotto `src/talos/`
- `ADR-0014`: Stack Linguaggio & Quality Gates — Python 3.11 + ruff strict + mypy strict + pytest + pre-commit applicativo
- `ADR-0015`: Stack Persistenza — PostgreSQL 16 + SQLAlchemy 2.0 sync + Alembic + Zero-Trust (RLS + 3 ruoli + audit_log) + pg_dump retention 7gg; **schema iniziale incluso come Allegato A** (10 tabelle)
- `ADR-0016`: Stack UI — Streamlit + multi-page + caching strategy (`@st.cache_data ttl=600` su Keepa + bottone "Forza Aggiornamento") + idempotency su side-effect + dark mode default
- `ADR-0017`: Stack Acquisizione Dati — Keepa (libreria community wrapped) + Playwright sync + Tesseract; fallback chain R-01; rate limit hard configurabile; soglia OCR 70 default; PA-API 5 escluso da MVP
- `ADR-0018`: Algoritmo VGP & Tetris — moduli `vgp/`, `tetris/`, `formulas/`; **pandas** (non polars) + Numpy vettoriale; errore esplicito su edge case Fee_FBA L11b; greedy con Priorità=∞ per locked-in
- `ADR-0019`: Test Strategy Applicativa — pytest con marker (unit/integration/golden/governance/slow); **golden dataset Samsung 1000 righe sintetico validato dal Leader**; coverage ≥90% core / ≥85% totale; **Hypothesis limitato a `vgp/normalize.py` + `vgp/score.py`**
- `ADR-0020`: CI/CD Pipeline — GitHub Actions (4 workflow); **single-push diretto su `main` + CI come gate**; GitNexus reindex automatizzato post-merge come bot; GitHub Secrets per `KEEPA_API_KEY` + Postgres test
- `ADR-0021`: Logging & Telemetria — `structlog` JSON + catalogo eventi canonici (10 eventi); enforcement R-01 sia statico (grep) sia dinamico (test capture handler); rotazione 10MB×7
- `docs/changes/2026-04-30-001-promulgazione-adr-stack-0013-0021.md`

### Changed
- `docs/decisions/INDEX.md`: 9 nuove righe nel registro + 9 nuovi nodi nel grafo dipendenze (cluster ADR di stack); aree di codice coperte aggiornate (gap stack/CI-CD/struttura/test/logging tutti chiusi)
- `docs/decisions/FILE-ADR-MAP.md`: nuova sezione "Codice Applicativo" con path vincolanti per ogni area (`src/talos/io_/keepa_client.py` → ADR-0017, ecc.); CI/CD workflow path; gap noti aggiornati
- `docs/STATUS.md`: ESP-007 chiusa, ISS-002 chiusa, HARD-STOP attivato; header e Stato in Una Riga riscritti
- `ROADMAP.md`: obiettivo #8 Completato; #10 (clone Atena-Core) e #11 (bootstrap primo modulo) aggiunti; meta-blocchi A/B/C chiusi; D/E/F aggiornati; G/H/I/J nuovi (post-MVP)

### Tooling — Integrazione GitNexus condivisa (CHG-2026-04-30-002)

- `CLAUDE.md`: blocco `<!-- gitnexus:start -->…end -->` aggiunto (auto-iniettato da `gitnexus init`)
- `AGENTS.md` aggiunto come gemello multi-agent (Cursor/Cline/Aider)
- `.claude/skills/gitnexus/` (6 skill: exploring, impact-analysis, debugging, refactoring, guide, cli) committate per allineamento futuri Claude
- `.gitignore` aggiunto: esclude `.gitnexus/` runtime locale (lock SQLite, WAL)
- `git rm --cached .gitnexus/lbug` + `lbug.wal` — smesso di tracciare i lock SQLite (erano in repo per errore)
- `scripts/hooks/{pre-commit,commit-msg}`: cambio modalità a `100755` (executable bit ripristinato; comportamento immutato)
- `docs/changes/2026-04-30-002-integrazione-tooling-gitnexus.md`

### Tag

- `milestone/stack-frozen-v0.9.0` — restore point pre-codice (decisione Leader, ADR-0003); fonte di clone per `Atena-Core`

## [0.8.0] — 2026-04-29 — TALOS Vision `Frozen`

Pietra miliare del progetto. La vision di TALOS (Scaler 500k) è ufficialmente **`Frozen`** dopo 6 round di Iterating e 26 lacune chiuse. Sblocca lo step [6] di ADR-0012: proposta di scomposizione in ADR di stack.

### Changed
- `PROJECT-RAW.md`: `frontmatter.status: Iterating → Frozen`, `frozen_at: 2026-04-29`, `qa_rounds: 5 → 6`; header e pipeline note allineati; nuovo blocco Round 6 nel Q&A Log con dichiarazione verbatim del Leader; cronologia stati aggiornata ([CHG-2026-04-29-009](docs/changes/2026-04-29-009-talos-frozen-declaration.md))
- `docs/STATUS.md`: ESP-006 chiusa, ESP-007 (proposta scomposizione) aperta, TAG-001 (milestone tag) suggerito; Nota al Prossimo Claude allineata al regime post-Frozen (Errata Corrige obbligatoria per modifiche, niente edit diretti)
- `ROADMAP.md`: obiettivo #7 marcato Completato; #8 In corso

### Added
- `docs/changes/2026-04-29-009-talos-frozen-declaration.md`

## [0.7.4] — 2026-04-29 — TALOS Iterating Round 5 (sweep finale, 0 lacune aperte)

### Changed
- `PROJECT-RAW.md`: chiuse tutte le 17 lacune residue in un colpo (L01, L02, L03, L05, L07, L09, L09b, L10, L11b, L13, L14, L15, L16, L17, L19, L22, L24); default proposti accettati al 100% tranne L02 = Opzione (a) budget di sessione e L14 = Streamlit; **formula manuale Fee_FBA fornita verbatim dal Leader** e incisa in sez. 6.3 Formula 1 per L11b; tabelle 8.1/8.2 popolate con rischi+mitigazioni; refusi L09 (Veto ROI = R-08) e L09b (Tetris = R-06) corretti inline; `qa_rounds: 5`; **0 lacune aperte (26/26 chiuse)** ([CHG-2026-04-29-008](docs/changes/2026-04-29-008-talos-iterating-round-5-sweep-finale.md))
- `docs/STATUS.md`, `ROADMAP.md`: Round 5 registrato; ESP-005 chiusa, ESP-006 (transizione Frozen) aperta
- Vision pronta per dichiarazione esplicita di `Iterating → Frozen` da parte del Leader

### Added
- `docs/changes/2026-04-29-008-talos-iterating-round-5-sweep-finale.md`

## [0.7.3+1] — 2026-04-29 — Fork transition

### Changed
- `git remote origin` riallineato da `santacrocefrancesco00-ux/Atena` (repo del padre, non scrivibile dal Leader operativo `matteo891`) a `matteo891/Atena` (fork operativo)
- `docs/STATUS.md`: link al repository aggiornato di conseguenza (commit `2abe28e`)

## [0.7.3] — 2026-04-29 — TALOS Iterating Round 4 (normalizzazione VGP)

### Changed
- `PROJECT-RAW.md`: chiusa L04b (normalizzazione **min-max su [0,1]** dei tre termini VGP sul listino di sessione, prima dei pesi 40/40/20); `qa_rounds: 4`; **17 aperte, 0 critiche residue** ([CHG-2026-04-29-007](docs/changes/2026-04-29-007-talos-iterating-round-4.md))
- `docs/STATUS.md`, `ROADMAP.md`: Round 4 registrato; vision pronta per sweep finale → Frozen
- `memory/MEMORY.md` + `memory/feedback_concisione_documentale.md`: ricreati (erano referenziati in CHG-006 ma assenti su filesystem — directory memory `~/.claude/...` fuori dal repo, non versionata)

### Added
- `docs/changes/2026-04-29-007-talos-iterating-round-4.md`

## [0.7.2] — 2026-04-29 — TALOS Iterating Round 3 (formula VGP)

### Changed
- `PROJECT-RAW.md`: chiuse L04 (formula VGP `(ROI*0.4)+(Vel*0.4)+(Cash_Profit*0.2)`) e L21 (Keepa out-of-scope per Talos); aperta L04b critica (normalizzazione scale) ([CHG-2026-04-29-006](docs/changes/2026-04-29-006-talos-iterating-round-3.md)); `qa_rounds: 3`; 18 aperte (1 critica L04b)
- `docs/STATUS.md`, `ROADMAP.md`: Round 3 registrato
- Direttiva del Leader sulla concisione documentale salvata come **memory feedback** durevole

### Added
- `docs/changes/2026-04-29-006-talos-iterating-round-3.md`
- `memory/feedback_concisione_documentale.md` (auto-memory)

## [0.7.1] — 2026-04-29 — TALOS Iterating Round 2

### Changed
- `PROJECT-RAW.md`: 6 lacune chiuse in Round 2 (L06 Samsung-only modulare, L08 scraping Amazon, L11 lookup Keepa primario, L12 Referral_Fee lookup+override, L18 Tesseract locale, L20 criteri di completamento misurabili accettati); 1 sub-lacuna nuova aperta (L11b formula manuale Fee_FBA); frontmatter `qa_rounds: 2`; sezione 9 ristrutturata in Aperte/Chiuse; Q&A Log esteso con Round 2 verbatim ([CHG-2026-04-29-005](docs/changes/2026-04-29-005-talos-iterating-round-2.md))
- `docs/STATUS.md`: Round 2 registrato, 19 lacune aperte (2 critiche L04/L21), prossima azione = Round 3
- `ROADMAP.md`: log validazioni esteso con Round 2

### Added
- `docs/changes/2026-04-29-005-talos-iterating-round-2.md` — change document Round 2

### Lacune critiche residue
- **L04** Formula del VGP Score (bottleneck dell'MVP)
- **L21** Keepa: subscription, campi, costo, rate limit (collegata a L11/L11b)

## [0.7.0] — 2026-04-29 — TALOS Vision Exposition (Round 1)

### Added
- **Codename del progetto: TALOS (Scaler 500k)** — Hedge Fund algoritmico automatizzato applicato al modello FBA Wholesale High-Ticket
- `docs/changes/2026-04-29-004-talos-exposition-iterating.md` — change document della prima esposizione

### Changed
- `PROJECT-RAW.md`: trascrizione verbatim integrale della bozza esposta dal Leader, mappatura 14+1 sezioni → 11 sezioni template, 24 lacune raccolte (8 critiche, 12 importanti, 4 di forma); status `Draft → Iterating`; frontmatter aggiornato (`qa_rounds: 1`, `codename: TALOS`, `tagline: "Scaler 500k"`)
- `docs/STATUS.md`: stato corrente = Iterating Round 1 completato, Round 2 (chiusura lacune critiche) in attesa Leader
- `ROADMAP.md`: obiettivo #7 in corso — esposizione completata, lacune mappate

### Lacune critiche da risolvere prima del Frozen
- **L04** Formula del VGP Score (non definita)
- **L08** Lookup Amazon (scraping vs PA-API)
- **L11/L12** Sorgente Fee_FBA e Referral_Fee
- **L18** Tecnologia OCR/Vision per file non-strutturati
- **L20** Criteri di completamento misurabili
- **L21** Keepa: subscription, campi, costo, rate limit
- **L06** Estrattore Samsung-only: scope MVP e roadmap

## [0.6.0] — 2026-04-29 — Vision Capture Protocol

### Added
- `ADR-0012`: Project Vision Capture & Distillation — protocollo formale per esporre, affinare e congelare la bozza concettuale del progetto via `PROJECT-RAW.md` ([CHG-2026-04-29-003](docs/changes/2026-04-29-003-vision-capture-adr.md))
- `PROJECT-RAW.md` (root): template vuoto in stato `Draft`, 11 sezioni fisse, 16 lacune iniziali precompilate, Q&A Log vuoto, regola "lacune mai completate" applicata
- `docs/changes/2026-04-29-003-vision-capture-adr.md` — change document della promulgazione

### Changed
- `docs/decisions/INDEX.md`: aggiunto ADR-0012 al registro, grafo dipendenze esteso, `PROJECT-RAW.md` registrato in "Aree di Codice Coperte"
- `docs/decisions/FILE-ADR-MAP.md`: `PROJECT-RAW.md` mappato sotto ADR-0012; ROADMAP esteso con dipendenza secondaria ADR-0012
- `ROADMAP.md`: obiettivo #6 (vision capture protocol) completato; #7 (esposizione Leader → Iterating) in attesa; #8 (Frozen → scomposizione → ADR di stack) successivo; meta-blocco F aggiunto
- `docs/STATUS.md`: stato vision capture, prossima azione = esposizione bozza Leader

## [0.5.0] — 2026-04-29 — Governance Hardening

Audit completo del sistema di governance richiesto dal Leader. Rilevati 5 buchi seri (B1–B5), 9 sviste minori (M1–M9) e 3 policy mancanti (P1–P3). Risolti integralmente in questo release.

### Added
- `ADR-0009`: Errata Corrige & Hardening Patch — meccanismo formale per correggere refusi e marcare sezioni obsolete senza supersessione completa ([CHG-2026-04-29-002](docs/changes/2026-04-29-002-hardening-governance.md))
- `ADR-0010`: Self-Briefing Hardening & STATUS Anchoring — Step 0 di verifica `core.hooksPath` (bloccante), header `Ultimo aggiornamento` in STATUS.md, regola di anchoring per ogni claim, fonte unica della sequenza di re-briefing ([CHG-2026-04-29-002](docs/changes/2026-04-29-002-hardening-governance.md))
- `ADR-0011`: Operational Policies — push immediato post-commit, branch policy fase governance, definizione formale di test manuali documentati per file di governance/infrastruttura ([CHG-2026-04-29-002](docs/changes/2026-04-29-002-hardening-governance.md))
- `docs/changes/2026-04-29-002-hardening-governance.md` — change document del hardening
- Frontmatter ADR esteso con campi opzionali `errata:` e `hardening_patches:` (append-only)
- Sezione `## Errata` in coda agli ADR modificati

### Changed
- `scripts/hooks/pre-commit`: aggiunta `## Test di Conformità` alla lista delle sezioni obbligatorie per nuovi ADR (B3)
- `scripts/hooks/commit-msg`: classifier dei file in staging anche per prefissi docs/chore/ci (B2); verifica esistenza fisica del change document referenziato dal CHG-ID (M7); presenza obbligatoria di ADR-NNNN nel footer (M6)
- `docs/decisions/INDEX.md`: aggiunti ADR-0009/0010/0011, grafo dipendenze esteso, status `Active¹` per ADR-0004 (con hardening patch), issues ISS-001/002 spostate qui per visibilità
- `docs/decisions/FILE-ADR-MAP.md`: aggiunto `docs/STATUS.md` (governato da ADR-0008 + ADR-0010), corretto `.gitattributes` (governato da ADR-0006, non più "triviale"), nuova sezione "Push, Branch, Tag" (M4, M5)
- `docs/STATUS.md`: header `Ultimo aggiornamento` + ancore verificabili su tutti i claim, aggiornamento integrale alla nuova realtà di governance
- `CLAUDE.md`: Self-Briefing con Step 0 bloccante, riferimento esplicito ad ADR-0010 come fonte unica della sequenza, sezione "Tipi di test ammessi" (ADR-0011), branch `main` (corretta), push policy esplicita
- `ROADMAP.md`: obiettivo "Hardening governance v0.5.0" completato; rinvio "Branch policy v2" alla fase codice applicativo

### Errata Corrige (ADR-0009)
- `ADR-0003`: tabella "Tipologie di Checkpoint" — `master` corretto in `main` (M1). Sezione `## Errata` aggiunta.
- `docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md`: numerazione "ADR 0001–0007" corretta in "ADR 0001–0008" (3 occorrenze); riferimento milestone tag corretto (M2). Sezione `## Errata` aggiunta.

### Hardening Patches (ADR-0009)
- `ADR-0004` sezione "Flusso di Re-Briefing": marcata superseduta da ADR-0010 con blocco di intestazione esplicito (B1). Status di ADR-0004 in INDEX.md aggiornato a `Active¹`. Sezione `## Errata` aggiunta.

## [0.4.0] — 2026-04-29

### Added
- `ADR-0008`: Anti-Allucinazione Protocol — regole hard contro invenzione di coordinate, degrado silenzioso, stato non verificato ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `docs/STATUS.md` — documento di stato vivo: re-entry in < 60 secondi, issues noti, "Nota al Prossimo Claude"

### Changed
- `CLAUDE.md`: Self-Briefing ottimizzato (STATUS.md come step 1), Anti-Allucinazione inline, Setup Repository, formato commit
- `docs/decisions/INDEX.md`: ADR-0008 aggiunto, ISS-001 segnalato, STATUS.md mappato
- `ROADMAP.md`: obiettivo #3 completato, #4 (fix GitNexus ISS-001) aggiunto, log aggiornato

## [0.3.0] — 2026-04-29

### Added
- `ADR-0005`: Commit Message Convention — footer con CHG-ID e ADR-ID in ogni commit non-triviale ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `ADR-0006`: Git Hooks Enforcement — pre-commit e commit-msg per enforcement meccanico dei protocolli ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `ADR-0007`: GitNexus come Planimetria Architetturale — knowledge graph del codice, briefing O(query) ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `docs/decisions/FILE-ADR-MAP.md` — indice inverso file → ADR per navigazione bidirezionale ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `scripts/hooks/pre-commit` — blocca commit senza change doc o ADR malformati/non-indicizzati ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `scripts/hooks/commit-msg` — blocca commit senza CHG-ID nel message ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `scripts/setup-hooks.sh` — script di attivazione hook, eseguire dopo ogni clone ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md` — primo change document del progetto

### Changed
- `docs/decisions/INDEX.md` aggiornato con ADR-0005, 0006, 0007, grafo dipendenze esteso, aree coperte complete
- `CLAUDE.md` aggiornato con Setup Repository e commit format (ADR-0005, ADR-0006)

## [0.2.0] — 2026-04-29

### Added
- `ADR-0001`: Meta-Architettura del Sistema ADR — definisce template, naming, ciclo di vita e mappa neurale di tutti gli ADR.
- `ADR-0002`: Test Gate Protocol — nessun commit non-triviale senza test passante e permesso esplicito del Leader.
- `ADR-0003`: Restore Point Strategy su GitHub — checkpoint ogni 5 commit significativi, milestone tag per ogni ADR implementato.
- `ADR-0004`: Cross-Reference Documentation — change document obbligatorio per ogni modifica non-triviale in `docs/changes/`.
- `docs/decisions/TEMPLATE.md` — template riutilizzabile per nuovi ADR.
- `docs/decisions/INDEX.md` — mappa neurale relazionale di tutti gli ADR attivi.
- `docs/changes/TEMPLATE.md` — template per i change document.

### Changed
- `CLAUDE.md` aggiornato: Self-Briefing esteso con step 5 (change documents recenti), Ciclo di Modifica espanso con test gate e checkpoint, nuova sezione Protocolli Operativi.
- `ROADMAP.md` aggiornato: obiettivo #2 completato, meta-blocchi futuri strutturati con ADR necessari.

## [0.1.0] — 2026-04-29

### Added
- Inizializzazione dell'infrastruttura dogmatica base.
- Creazione di `CLAUDE.md` con le Rules of Engagement e il protocollo di Self-Briefing obbligatorio.
- Predisposizione della cassaforte delle leggi `docs/decisions/` (vuota, pronta per la promulgazione degli ADR).
- Creazione di `CHANGELOG.md` (questo file).
- Creazione di `ROADMAP.md` con struttura operativa e vincoli di validazione GitNexus.
