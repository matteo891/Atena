---
id: CHG-2026-05-01-018
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 4 — chiusura motore asin_resolver applicativo)
status: Draft
commit: TBD
adr_ref: ADR-0017, ADR-0018, ADR-0014, ADR-0019
---

## What

Inaugura `_LiveAsinResolver` (private class in
`src/talos/extract/asin_resolver.py`) — composer concreto del
flusso `(descrizione, prezzo) → ASIN`. Implementa
`AsinResolverProtocol` (CHG-016) componendo:

1. `serp_adapter.search(description)` (CHG-017) -> top-N candidati
2. `lookup_callable(candidate.asin)` (di norma `lookup_product`
   CHG-006 con Keepa-only, no scraper Chromium) -> `ProductData`
   con `buybox_eur`
3. Per ogni candidato: `fuzzy_title_pct` via
   `rapidfuzz.fuzz.token_set_ratio(description, candidate.title)`
   + `delta_price_pct = |buybox - input_price| / input_price * 100`
4. `compute_confidence` (CHG-016) compone fuzzy 60% + price 40%
5. `selected` = candidato con max `confidence_pct`. Tie-break
   implicito su ordine SERP (top-1 vince a parita').

R-01 NO SILENT DROPS UX-side ratificato:
- `lookup` fallito per un candidato -> esposto con `buybox=None`
  + nota in `result.notes` ("candidato XYZ lookup failed: KeepaTransientError")
- SERP vuota -> `ResolutionResult(selected=None, candidates=(),
  is_ambiguous=True, notes=("zero risultati SERP",))`
- TUTTI i candidati esposti in `candidates`, mai scartati silenziosamente.
  Coerente con feedback Leader memory `feedback_ambigui_con_confidence.md`.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/asin_resolver.py` | modificato | + import `rapidfuzz.fuzz` runtime + `logging`. + helper `_fuzzy_title_ratio(description, title) -> float` (rapidfuzz token_set_ratio 0-100, robusto a ordine token / parole extra / duplicati). + helper `_delta_price_pct(buybox_eur, input_price_eur) -> float \| None` (None se buybox=None). + `_LiveAsinResolver` class con `__init__(serp_adapter, lookup_callable, *, max_candidates=5)` validation `max_candidates>0` + `resolve_description(description, input_price_eur) -> ResolutionResult` (validazione inputs + composizione 4 step + max confidence). |
| `tests/unit/test_asin_resolver_live.py` | nuovo | 12 test mock-only via `_FixedSerpAdapter` + `_make_lookup` helper: 3 validazione (max_candidates, description vuota, prezzo<=0), 6 composizione (zero SERP, happy path strong match, top-N picks max confidence, lookup failure expose with buybox=None, all lookups fail, propagazione max_candidates a SERP), 3 R-01 UX (low fuzzy expose, perfect fuzzy no price -> 60 ambiguous, propagazione description a SERP). |
| `tests/integration/test_live_asin_resolver.py` | nuovo | 1 test live end-to-end (skip module-level se Chromium o Keepa key assenti): "Samsung Galaxy S24 256GB Onyx Black" @ €549 -> top-1 starts with B0, fuzzy>30, confidence>50. Costo: 1 SERP + 3 Keepa = ~3 token. PASS in 7.29s. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **616
PASS** unit/gov/golden + 124 integration = **740 PASS** (era 727,
+12 unit + +1 integration live).

## Why

CHG-016 ha definito tipi + Protocol + helper puri.
CHG-017 ha aperto canale SERP live.
CHG-018 chiude il **motore applicativo** del resolver: l'unica
implementazione concreta del Protocol che compone i due livelli e
ratifica empiricamente che il flusso end-to-end funzioni.

Senza CHG-018, l'asin_resolver e' "tipi vuoti": niente puo'
risolvere una descrizione in un ASIN. Con CHG-018, il flusso d'uso
reale del Leader e' costruibile in produzione.

Decisione "lookup_callable iniettato come `Callable[[str], ProductData]`"
(non hardcoded `lookup_product`) e' deliberata:
- **Disaccoppiamento**: il resolver non sa nulla di Keepa o scraper.
- **Test mock-only**: passa una lambda che ritorna `ProductData`
  preconfezionato.
- **Flessibilita' caller**: in produzione `partial(lookup_product,
  keepa=client, scraper=None, page=None, ocr=None)` (Keepa-only,
  no Chromium overhead per N candidati). Caller avanzato puo'
  aggiungere scraper se vuole BSR multi-livello + verifica title
  arricchita.
- **Quota optimization**: lookup leggero per N candidati = ~N token
  Keepa per descrizione. Per batch 100 listino fornitore (top-3
  candidati ciascuno) = ~300 token Keepa + 100 SERP. Gestibile.

### Decisioni di design

1. **`fuzz.token_set_ratio` (non `partial_ratio` / `ratio`)**:
   - `token_set_ratio` ignora ordine + duplicati + parole extra.
   - "Galaxy S24 256GB Onyx" vs "Samsung Galaxy S24 5G 256GB Onyx
     Black" -> ratio ~85 (ottimo, anche se titolo Amazon piu' lungo).
   - `partial_ratio` premierebbe sostringhe contigue (rischioso con
     descrizioni fornitore disordinate).
   - `ratio` premia stesso ordine (troppo strict).
   - `token_set_ratio` e' lo standard "best-effort fuzzy" della
     comunita'.

2. **`lookup_callable` generic invece di `KeepaClient` direct**:
   - Permette varianti (Keepa-only veloce vs Keepa+scraper completo).
   - Test pure-Python senza dipendere da KeepaClient mock.
   - Caller decide policy (es. fallback a scraper se Keepa miss).

3. **Catch `Exception` generico nel try lookup**: il caller puo'
   passare qualunque callable; le sue eccezioni vanno tutte mappate
   a "buybox=None + nota". Eccezioni canoniche (KeepaTransientError,
   KeepaRateLimitExceededError, SelectorMissError, ...) hanno
   `type(exc).__name__` informativo nelle notes per debug.

4. **Selected = `max(candidates, key=confidence_pct)` con tie-break
   posizione SERP**: Python `max` mantiene il primo a parita' (sort
   stable). Ordine SERP gia' sorted by-relevance Amazon -> top-1
   vince a parita' di confidence. Coerente con "trust SERP ranking
   come prior".

5. **`is_ambiguous` calcolato sul `selected.confidence_pct` (non
   sull'aggregato)**: e' il flag UX per "il MIGLIOR candidato e' o
   non e' affidabile". Se selected ha confidence=50, l'utente vede
   "il match top e' ambiguo" e puo' override con un altro
   `candidate` proposto (UI scope CHG-020).

6. **Notes accumulate fallimenti**: pattern coerente con
   `ProductData.notes` (CHG-006). Audit trail compreso al CFO.

7. **Validation prezzo<=0 / descrizione vuota**: contratto chiaro
   con caller. Pattern coerente con `_LiveAmazonSerpAdapter.search`
   (CHG-017). Empty/zero non ha senso semantico (descrizione
   inesistente o prezzo "regalo" sono input rotti, non casi
   ambigui).

8. **Helper `_fuzzy_title_ratio` / `_delta_price_pct` privati
   modulo-level**: pure functions, testabili, riusabili. Pattern
   coerente con `_last_valid_value` (CHG-015), `parse_eur`
   (CHG-002).

9. **`max_candidates` default 5**: compromesso fra confidence
   (piu' candidati = piu' opzioni per CFO) e quota (1 token
   Keepa per candidato). 5 = ~1.5x il "top-3" comune in
   information retrieval.

10. **Test live "Galaxy S24 256GB Onyx Black"**: descrizione
    realistica fornitore Samsung. Permette anche di catturare
    drift confidence se in futuro Amazon SERP cambia ranking
    o se rapidfuzz cambia algoritmo. Pattern empirico (lezione
    CHG-013) ratificato.

### Out-of-scope

- **Cache `description_resolutions` UPSERT**: scope CHG-2026-05-01-019.
- **UI Streamlit nuovo flow upload + highlight confidence**:
  scope CHG-2026-05-01-020.
- **Bulk resolver `resolve_descriptions(rows)` -> list[ResolutionResult]**:
  pattern coerente con `lookup_products` (CHG-009), scope futuro.
  Per ora caller batch chiama `resolve_description` in loop.
- **Telemetria `asin_resolver.zero_serp` / `asin_resolver.ambiguous`**:
  scope futuro errata catalogo ADR-0021 quando il flusso e' in
  produzione e si vuole monitorare hit rate ambiguita'.
- **Keepa Product Search fallback se SERP fallisce**: scope CHG
  futuro. Per ora SERP-only canale (decisione 1=A round 4).
- **Concorrenza N description batch**: scope futuro asyncio.
- **Cache local del fuzzy_title_pct**: scope futuro se profiling
  rivela rapidfuzz come bottleneck.

## How

### `_LiveAsinResolver.resolve_description` (highlight)

```python
def resolve_description(self, description, input_price_eur):
    if not description.strip():
        raise ValueError("description vuota")
    if input_price_eur <= 0:
        raise ValueError(f"input_price_eur > 0 (got {input_price_eur})")

    serp_results = self._serp.search(description, max_results=self._max_candidates)
    if not serp_results:
        return ResolutionResult(
            description=description, input_price_eur=input_price_eur,
            selected=None, candidates=(), is_ambiguous=True,
            notes=("zero risultati SERP",),
        )

    notes, candidates = [], []
    for serp_item in serp_results:
        buybox = None
        try:
            buybox = self._lookup(serp_item.asin).buybox_eur
        except Exception as exc:
            notes.append(f"candidato {serp_item.asin} lookup failed: {type(exc).__name__}")
        fuzzy = _fuzzy_title_ratio(description, serp_item.title)
        delta = _delta_price_pct(buybox, input_price_eur)
        confidence = compute_confidence(fuzzy, delta)
        candidates.append(ResolutionCandidate(...))

    selected = max(candidates, key=lambda c: c.confidence_pct)
    return ResolutionResult(
        ..., selected=selected, candidates=tuple(candidates),
        is_ambiguous=is_ambiguous(selected.confidence_pct),
        notes=tuple(notes),
    )
```

### Live test (highlight)

```python
keepa_client = KeepaClient(api_key=key, rate_limit_per_minute=20)
page = _PlaywrightBrowserPage()
try:
    resolver = _LiveAsinResolver(
        serp_adapter=_LiveAmazonSerpAdapter(browser_factory=lambda: page),
        lookup_callable=partial(lookup_product, keepa=keepa_client,
                                scraper=None, page=None, ocr=None),
        max_candidates=3,
    )
    result = resolver.resolve_description(
        "Samsung Galaxy S24 256GB Onyx Black", Decimal("549.00"),
    )
finally:
    page.close()
assert result.selected.asin.startswith("B0")
assert result.selected.fuzzy_title_pct > 30
assert result.selected.confidence_pct > 50
```

PASS in 7.29s -> resolver end-to-end ratificato.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (51 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **616 PASS** (era 604, +12 nuovi `test_asin_resolver_live`) |
| Integration (skip live keepa, gia' verificato) | `uv run pytest tests/integration --ignore=tests/integration/test_live_keepa.py -q` | **124 PASS** (era 123, +1 live asin_resolver) |
| Live asin_resolver | `uv run pytest tests/integration/test_live_asin_resolver.py -v` | PASS in 7.29s su Galaxy S24 reale |

**Rischi residui:**
- **`fuzz.token_set_ratio` su descrizioni molto sintetiche**:
  "iPhone 15" matcherebbe alto contro decine di prodotti. Mitigazione:
  il prezzo e' il filtro discriminante (delta_price_pct). Caller
  CFO con descrizioni vague vede il `confidence_pct` basso e
  scarta/seleziona altro candidato.
- **`lookup_callable` Keepa-only + Keepa rate limit**: per batch
  grandi (100+ descrizioni × 3 candidati = 300 token), il rate
  limit `60/min` di default puo' triggerare
  `KeepaRateLimitExceededError`. Caller batch deve gestire
  pacing / retry. Per ora il resolver tratta queste eccezioni come
  "candidato senza prezzo" senza propagare.
- **SERP top-N saturate da sponsored / brand store**: Amazon a
  volte mostra > N risultati sponsored prima del prodotto vero.
  `max_candidates=5` puo' essere insufficiente. Mitigazione:
  CHG-017 skip risultati senza asin (banner). Eventuale aumento
  default a 10 valutabile post-osservazione produzione.
- **Tie-break stable Python `max`**: il tie-break su confidence
  uguale e' stabile sull'ordine di iterazione. Pattern testato.
- **Verifica live consuma quota Keepa**: 3 token/test. Se eseguita
  in CI ad ogni push, costo cumulativo. Mitigazione: skip
  module-level su CI senza secrets, eseguita solo localmente
  Leader-side.
- **`partial(lookup_product, ...)` con Decimal**: il pattern crea
  un nuovo callable. Stato condiviso (KeepaClient con rate limiter
  in-process) e' OK per single-process; multi-process richiederebbe
  fork-aware setup (scope futuro).

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/asin_resolver.py`
  ✓ (area `extract/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Composizione di canali esistenti (SERP + Keepa via lookup) ✓
  - R-01 NO SILENT DROPS UX-side: tutti i candidati esposti +
    `confidence_pct` espone fragilita' ✓
- **ADR-0018 R-01 (vettoriale): non applicabile (resolver e'
  per-row, non vettoriale).**
- **Test unit + integration live:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** modulo `asin_resolver`
  esistente (CHG-016) -> ADR-0017. `_LiveAsinResolver` privato
  (no re-export `__init__.py`).
- **Backward compat:** `AsinResolverProtocol` invariato; il
  `_LiveAsinResolver` lo soddisfa duck-typed.
- **Sicurezza:** zero input esterno arbitrary; le descrizioni
  passano da `serp_adapter.search` che fa URL encoding (CHG-017);
  `lookup_callable` injetta-dipendenze, non input.
- **Impact analysis pre-edit:** GitNexus risk LOW (modulo
  esistente, aggiunta classe nuova senza modificare API
  esistenti).

## Impact

- **Motore asin_resolver chiuso a livello applicativo**: 3/5 CHG
  attesi (016 skeleton + 017 SERP live + 018 composer live).
  Restano CHG-019 cache + CHG-020 UI.
- **Path B end-to-end completamente operativo end-to-end con
  descrizione+prezzo come input**: il flusso applicativo c'e' tutto.
  Manca solo il "wrapping" persistenza (cache hit) + UX (UI flow).
- **`pyproject.toml` invariato** (`rapidfuzz>=3,<4` gia' dep CHG-004).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11 viventi).
  CHG futuri introdurranno eventi `asin_resolver.*` via errata
  additiva quando il flusso e' in produzione.
- **Test suite cresce di +13** (12 unit + 1 integration live):
  740 PASS (era 727), zero regression.
- **Quota Keepa consumata in CHG-018**: ~3 token (test live
  resolver). Total sessione round 4: ~9 token Keepa.
- **5 CHG significativi nella sessione round 4**: 014/015/016/017/018.
  Soglia checkpoint raggiunta -> proposta `checkpoint/2026-05-01-14`
  imminente.

## Refs

- ADR: ADR-0017 (canale acquisizione, composizione di canali
  esistenti), ADR-0014 (mypy/ruff strict), ADR-0019 (test unit
  + integration live).
- Predecessori:
  - CHG-2026-05-01-016 (`AsinResolverProtocol` + tipi + helper
    puri).
  - CHG-2026-05-01-017 (`_LiveAmazonSerpAdapter`): canale SERP
    live consumato da `_LiveAsinResolver._serp`.
  - CHG-2026-05-01-006 (`lookup_product` fallback chain):
    consumer della verifica prezzo via `lookup_callable`.
  - CHG-2026-05-01-015 (`_LiveKeepaAdapter` live): driver del
    `lookup_product` Keepa-only nei test live.
  - CHG-2026-05-01-004 (`rapidfuzz` dep): `fuzz.token_set_ratio`
    riusato.
- Decisioni Leader 2026-05-01 round 4: 1=A SERP primario, 2=alpha-prime
  composizione fuzzy+price 60/40, 3=i-prime tutti i candidati esposti
  con confidence.
- Memory: `feedback_ambigui_con_confidence.md` (R-01 NO SILENT DROPS
  UX-side, fonte design `notes` accumulate + candidates esposti).
- Successore atteso: CHG-2026-05-01-019 (cache
  `description_resolutions` UPSERT con migration alembic +
  repository).
- Commit: TBD (backfill post-commit).
