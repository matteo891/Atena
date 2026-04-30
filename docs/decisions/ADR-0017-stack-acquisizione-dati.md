---
id: ADR-0017
title: Stack Acquisizione Dati — Keepa + Playwright + Tesseract
date: 2026-04-29
status: Active
deciders: Leader
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

L08 (scraping `amazon.it`), L11 (lookup Keepa primario + fallback formula manuale Fee_FBA), L18 (Tesseract OCR) e L21 (Keepa API consumate, piano gestito esternamente) hanno ratificato i tre canali di acquisizione dati. L17 ha inscritto i rischi non tecnici (ToS Amazon, single-vendor Keepa, etc.). L24 ha inscritto i rischi tecnici (throttling, drift, rotture scraping).

Manca la specifica dello **stack tecnico esatto** + pattern di fallback chain, rate limiting, soglie di confidenza. Senza questo ADR, ogni sviluppatore implementa il proprio adapter Keepa con convenzioni divergenti, e R-01 NO SILENT DROPS rischia di non essere applicato uniformemente.

## Decisione

### Canale 1 — Keepa API (primario)

- **Libreria:** `keepa` (community, mature, mantenuta) come dipendenza in `pyproject.toml`.
- **Wrapper interno:** `src/talos/io_/keepa_client.py` espone interfaccia `KeepaClient` con metodi `fetch_buybox(asin)`, `fetch_bsr(asin)`, `fetch_fee_fba(asin)`. La libreria community è **isolata dietro il wrapper** per facilitare future sostituzioni.
- **Backoff esponenziale:** retry su 429/5xx con `tenacity`, base 1s, max 60s, max 5 retry.
- **Rate limiting hard:** decisione Leader. Limite configurabile in `pyproject.toml` (es. `KEEPA_MAX_REQUESTS_PER_MINUTE = 60`). Implementato via `aiolimiter` (anche se sync, c'è la versione `pyrate-limiter`). **Eccedere il limite → blocco con error esplicito (R-01)**, non silenziamento.
- **Cache locale di sessione:** Streamlit `@st.cache_data(ttl=600)` sul wrapper (ADR-0016).

### Canale 2 — Scraping `amazon.it` (fallback su Keepa miss)

- **Libreria:** **Playwright** (sync API in modulo isolato `extract/amazon_scrape.py` per coerenza con SQLAlchemy sync di ADR-0015).
- **Selettori multipli con fallback:** ogni campo (titolo, BuyBox, prezzo) ha lista ordinata di selettori CSS; al primo match riuscito si esce. Il `selectors.yaml` versionato + facile da aggiornare quando Amazon cambia layout.
- **Cadence umana:** delay random `1.5–4s` tra richieste; user-agent realistico; no headless trasparente (`--headless=new`).
- **Nessuna automazione del cart:** scraping solo per **lookup informativo** (BuyBox, prezzo, ASIN da titolo). L'azione "ordina" del CFO genera un export, non un click su Amazon.
- **Logging strutturato:** ogni mismatch dei selettori → log `WARNING` con `selector`, `asin`, `html_snippet_hash`. Drift dei selettori monitorabile.

### Canale 3 — Tesseract OCR (file non strutturati: PDF, immagini, DOCX)

- **Libreria:** `pytesseract` come binding di Tesseract locale (sezione 4.3 + L18).
- **Pipeline:**
  1. PDF → `pdf2image` per convertire pagine in immagini PNG.
  2. DOCX → `python-docx` per estrazione testo strutturato (no OCR).
  3. IMG diretti → `PIL` + `pytesseract`.
  4. Soglia di confidenza (Tesseract `image_to_data` colonna `conf`): default **70/100**.
- **Sotto soglia → status `AMBIGUO`** (R-01 NO SILENT DROPS): la riga del listino non è scartata silenziosamente, viene marcata e mostrata al CFO per validazione manuale.
- **Configurabile:** soglia esposta in `config_overrides` (key `ocr_confidence_threshold`).

### Fallback chain

```
listino input
  → riga ha ASIN già strutturato?
       sì → KeepaClient.fetch(asin)
              succeeded? → use Keepa data
              miss/error → Playwright.scrape_amazon(asin)
                              succeeded? → use scraping data
                              fail → status 'AMBIGUO' + log
       no  → SamsungExtractor.parse_title(raw_title) → ottieni candidate ASIN
              → ricorsione sopra
```

Ogni livello di fallback **logga esplicitamente** il fallimento del precedente (R-01).

### Esclusioni MVP (decisione Leader)

- **PA-API 5 escluso** dall'MVP. Eventuale 4° canale legalmente solido valutato post-MVP se scraping diventa insostenibile.

### Configurazione

Tutte le config (rate limit, soglia OCR, delay scraping, percorsi Tesseract) in **`pyproject.toml`** sezione `[tool.talos.acquisition]` + override runtime via `pydantic-settings` (env `TALOS_KEEPA_RATE_LIMIT=60`).

### Segreti

- `KEEPA_API_KEY` → GitHub Secrets (CI) + `.env` locale (ignorato git).
- Nessuna password Amazon (scraping è non-autenticato, lookup pubblici).

## Conseguenze

**Positive:**
- Fallback chain robusta: anche con Keepa down, l'app degrada graziosamente a scraping; con scraping down, OCR locale resta disponibile.
- R-01 garantito a ogni livello: nessun dato è scartato silenziosamente.
- Playwright headless + cadence umana riduce (non elimina) il rischio detection lato Amazon.
- Wrapper KeepaClient permette sostituzione futura della libreria community senza rifare l'app.

**Negative / costi:**
- 3 canali = 3 punti di guasto da monitorare. Operativamente: dashboard di health-check post-MVP.
- Scraping è **fragile per natura**: i selettori `amazon.it` cambieranno e periodicamente romperanno il fallback. Necessaria pipeline di alerting.
- Playwright runtime ~150MB di Chromium scaricato; aumenta dimensione container.
- Rate limit hard può causare blocchi durante listino grande (1000+ ASIN): mitigare con batch + cache aggressiva.

**Effetti collaterali noti:**
- Il file `selectors.yaml` per Amazon è "configurazione vivente": modifiche frequenti, va trattato come asset operativo (non triviale, change document obbligatorio).
- Tesseract richiede installazione di sistema (`apt install tesseract-ocr ita-eng`) — documentare in `README.md`.

## Test di Conformità

1. **Mock Keepa:** test `tests/integration/test_keepa_client.py` con cassette VCR-style; verifica retry su 429 e blocco su rate limit eccesso.
2. **Selettori Amazon:** test `tests/integration/test_amazon_scrape.py` su HTML statici di esempio in `tests/golden/html/`; verifica fallback selettore su HTML modificato.
3. **Soglia OCR:** test `tests/integration/test_ocr_pipeline.py` su immagini con confidenza variabile; verifica che `confidence < 70` produca status `AMBIGUO`.
4. **Fallback chain end-to-end:** test simula Keepa down → scraping success, scraping down → OCR success, OCR fail → AMBIGUO con log strutturato.
5. **Rate limit enforcement:** test che verifica blocco esplicito (non silenzioso) al N+1° request entro la finestra.
6. **R-01 invariant:** test `tests/governance/test_no_silent_drops.py` fa grep su `\.drop\(` e fallisce su occorrenze fuori da commenti/log.

## Cross-References

- ADR correlati: ADR-0013 (struttura `io_/`, `extract/`), ADR-0014 (stack), ADR-0015 (persistenza ASIN master), ADR-0016 (caching UI), ADR-0018 (consumatore: VGP), ADR-0021 (logging strutturato dei mismatch)
- Governa: `src/talos/io_/keepa_client.py`, `src/talos/io_/scraper.py`, `src/talos/io_/ocr.py`, `src/talos/extract/`, `selectors.yaml`
- Impatta: ogni operazione di lookup esterno; rate limit; rischi non tecnici sez. 8.2 della vision
- Test: `tests/integration/test_keepa_client.py`, `test_amazon_scrape.py`, `test_ocr_pipeline.py`, `test_fallback_chain.py`, `tests/governance/test_no_silent_drops.py`
- Commits: `<pending>`

## Rollback

Se scraping `amazon.it` diventa insostenibile (es. Amazon blocca sistematicamente):
1. Errata Corrige: rimuovere Canale 2; degradare fallback chain a Keepa → OCR → AMBIGUO.
2. Promulgare ADR-NNNN per introdurre PA-API 5 come 2° canale legalmente solido.

Se Keepa cambia pricing/copertura e diventa inutilizzabile:
1. Rischio strategico maggiore (vedi 8.2). Possibili mitiganti:
   - Provider alternativo (es. Junglescout API, AMZScout API) come Canale 1bis.
   - Estensione Playwright per scraping più aggressivo (ma fragile).
2. Decisione Leader-driven con nuovo ADR.
