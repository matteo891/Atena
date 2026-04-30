"""Integration tests — DB reale, Playwright, OCR (ADR-0019, ADR-0015).

Inaugurato in CHG-2026-04-30-019 con i primi test runtime su Postgres reale
(RLS + trigger audit). Richiede env var `TALOS_DB_URL` per connettersi al DB;
in sua assenza i moduli skippano automaticamente al collection-time.
"""
