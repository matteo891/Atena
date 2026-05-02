"""Catalogo eventi canonici (ADR-0021).

Ogni evento di scarto/esclusione/modifica nei moduli applicativi deve usare
una di queste costanti come `event_name` di `structlog`. Il test
`tests/governance/test_log_events_catalog.py` verifica che ogni modulo
che usa `.drop(` / `.skip(` / `continue` abbia almeno una chiamata a
un evento del catalogo (R-01 NO SILENT DROPS dinamico).

Aggiungere un evento al catalogo richiede change document ed è side-effect
di un nuovo modulo applicativo. Rimuoverlo richiede supersessione di ADR-0021.

**Campi context-bound (CHG-2026-05-01-037, B1.4)**: i campi
`request_id`, `tenant_id`, `session_id`, `listino_hash` sono ereditati
automaticamente dal pipeline `merge_contextvars` quando un caller più
esterno chiama `bind_request_context` / `bind_session_context`. Non
sono più richiesti come `extra` esplicito sui singoli emit. Le tuple
qui sotto elencano solo i campi event-specific (NON ereditati). Vedi
ADR-0021 sezione "Campi context-bound".
"""

from typing import Final

# ── Catalogo eventi canonici (17 voci) ──────────────────────────────────────
# Mapping: event_name → tuple di campi obbligatori event-specific (NON
# context-bound). I campi context-bound (request_id, tenant_id, session_id,
# listino_hash) sono ereditati dal bind helper e non vanno più passati
# esplicitamente come kwargs/extra. Il test di governance verifica solo la
# presenza dell'evento; il rispetto dei campi event-specific è disciplina
# dei chiamanti (eventualmente promuovibile a verifica statica via mypy).

CANONICAL_EVENTS: Final[dict[str, tuple[str, ...]]] = {
    # Estrazione (ADR-0017 / 0018) — SamsungExtractor + filtro Kill-Switch
    "extract.kill_switch": ("asin", "reason", "mismatch_field", "expected", "actual"),
    # Algoritmo VGP (ADR-0018) — veto e kill-switch
    "vgp.veto_roi_failed": ("asin", "roi_pct", "threshold"),
    "vgp.kill_switch_zero": ("asin", "match_status"),
    # Tetris allocator (ADR-0018) — saturazione + panchina
    "tetris.skipped_budget": ("asin", "cost", "budget_remaining"),
    "panchina.archived": ("asin", "vgp_score"),
    # Acquisizione dati Keepa (ADR-0017)
    "keepa.miss": ("asin", "error_type", "retry_count"),
    "keepa.rate_limit_hit": ("requests_in_window", "limit"),
    # Scraping Amazon (ADR-0017)
    "scrape.selector_fail": ("asin", "selector_name", "html_snippet_hash"),
    # OCR Tesseract (ADR-0017)
    "ocr.below_confidence": ("file", "confidence", "threshold", "text_extracted"),
    # Persistenza (ADR-0015) — replica del trigger DB audit_log
    "db.audit_log_write": ("actor", "table", "op", "row_id"),
    # Orchestrator (ADR-0018) — replay what-if (errata CHG-2026-04-30-058)
    "session.replayed": ("asin_count", "locked_in_count", "budget", "budget_t1"),
    # UI flow descrizione+prezzo (ADR-0016) — errata CHG-2026-05-01-021
    "ui.resolve_started": ("n_rows", "has_factory"),
    "ui.resolve_confirmed": ("n_total", "n_resolved", "n_ambiguous"),
    # UI flow descrizione+prezzo — errata CHG-2026-05-01-024
    "ui.override_applied": ("n_overrides", "n_eligible"),
    "ui.resolve_failed": ("reason", "n_rows"),
    # Cache `description_resolutions` (ADR-0015) — errata CHG-2026-05-01-025
    # CHG-2026-05-01-037 (B1.4): tenant_id rimosso dalla tupla — ora ereditato
    # dal bind UI (`bind_request_context(tenant_id=DEFAULT_TENANT_ID)` in
    # `_render_descrizione_prezzo_flow`). Resta `table` come unico campo
    # event-specific.
    "cache.hit": ("table",),
    "cache.miss": ("table",),
    # Velocity estimator (ADR-0017 + 0018) — errata CHG-2026-05-02-005
    # Emesso quando V_tot viene stimato dal BSR (CSV non specifica v_tot
    # esplicito). Audit aggregabile: distribuzione fonte v_tot per sessione.
    "v_tot.estimated_from_bsr": ("asin", "bsr", "v_tot_estimated"),
    # Persistenza sessione (ADR-0015 + 0016) — errata CHG-2026-05-02-010
    # Emesso post-save in `try_persist_session` per audit aggregato:
    # quante sessioni persistite, distribuzione cart size, etc.
    "session.persisted": ("session_id", "n_cart_items", "n_panchina_items"),
    # Risk filter Amazon Presence (ADR-0024) — errata CHG-2026-05-02-031
    # Emesso da `compute_vgp_score` quando un ASIN viene vetato perché
    # Amazon detiene la BuyBox per > AMAZON_PRESENCE_MAX_SHARE (0.25).
    "vgp.amazon_dominant_seller": ("asin", "amazon_share", "threshold"),
}

# Costanti tipizzate per uso applicativo (autocompletamento + refactor-safe).
EVENT_EXTRACT_KILL_SWITCH: Final[str] = "extract.kill_switch"
EVENT_VGP_VETO_ROI_FAILED: Final[str] = "vgp.veto_roi_failed"
EVENT_VGP_KILL_SWITCH_ZERO: Final[str] = "vgp.kill_switch_zero"
EVENT_TETRIS_SKIPPED_BUDGET: Final[str] = "tetris.skipped_budget"
EVENT_PANCHINA_ARCHIVED: Final[str] = "panchina.archived"
EVENT_KEEPA_MISS: Final[str] = "keepa.miss"
EVENT_KEEPA_RATE_LIMIT_HIT: Final[str] = "keepa.rate_limit_hit"
EVENT_SCRAPE_SELECTOR_FAIL: Final[str] = "scrape.selector_fail"
EVENT_OCR_BELOW_CONFIDENCE: Final[str] = "ocr.below_confidence"
EVENT_DB_AUDIT_LOG_WRITE: Final[str] = "db.audit_log_write"
EVENT_SESSION_REPLAYED: Final[str] = "session.replayed"
EVENT_UI_RESOLVE_STARTED: Final[str] = "ui.resolve_started"
EVENT_UI_RESOLVE_CONFIRMED: Final[str] = "ui.resolve_confirmed"
EVENT_UI_OVERRIDE_APPLIED: Final[str] = "ui.override_applied"
EVENT_UI_RESOLVE_FAILED: Final[str] = "ui.resolve_failed"
EVENT_CACHE_HIT: Final[str] = "cache.hit"
EVENT_CACHE_MISS: Final[str] = "cache.miss"
EVENT_V_TOT_ESTIMATED_FROM_BSR: Final[str] = "v_tot.estimated_from_bsr"
EVENT_SESSION_PERSISTED: Final[str] = "session.persisted"
EVENT_VGP_AMAZON_DOMINANT_SELLER: Final[str] = "vgp.amazon_dominant_seller"
