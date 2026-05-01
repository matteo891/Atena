"""Catalogo eventi canonici (ADR-0021).

Ogni evento di scarto/esclusione/modifica nei moduli applicativi deve usare
una di queste costanti come `event_name` di `structlog`. Il test
`tests/governance/test_log_events_catalog.py` verifica che ogni modulo
che usa `.drop(` / `.skip(` / `continue` abbia almeno una chiamata a
un evento del catalogo (R-01 NO SILENT DROPS dinamico).

Aggiungere un evento al catalogo richiede change document ed è side-effect
di un nuovo modulo applicativo. Rimuoverlo richiede supersessione di ADR-0021.
"""

from typing import Final

# ── Catalogo eventi canonici (13 voci) ──────────────────────────────────────
# Mapping: event_name → tuple di campi obbligatori da passare nel kwargs
# del logger. La tupla è il contratto che il chiamante deve onorare; il
# test di governance verificherà solo la presenza dell'evento, mentre il
# rispetto dei campi è disciplina dei chiamanti (eventualmente promuovibile
# a verifica statica via mypy in futuro).

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
