---
id: CHG-2026-05-01-016
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 4 — apertura blocco asin_resolver post ratifica decisioni 1-5)
status: Draft
commit: TBD
adr_ref: ADR-0017, ADR-0014, ADR-0019
---

## What

Inaugura `src/talos/extract/asin_resolver.py` con tipi + Protocol +
helper di scoring, mock-testabile senza network. Primo CHG del
blocco "(descrizione, prezzo) -> ASIN" che sblocca il flusso d'uso
reale del Leader (listino fornitore senza ASIN -> pipeline VGP).

Decisioni Leader 2026-05-01 round 4 ratificate dopo discussione
empirica:

- **(1) A**: SERP Amazon primario (zero quota) + Keepa search
  fallback. Adapter live in CHG-2026-05-01-017+.
- **(2) alpha-prime**: top-1 SERP + verifica prezzo via
  `lookup_product` live. `confidence_pct` composito (fuzzy title
  60% + (1 - delta prezzo) 40%). NESSUN match scartato silente.
- **(3) i-prime**: tutti i match esposti in UI con
  `confidence_pct`. Soglia `DEFAULT_AMBIGUOUS_THRESHOLD_PCT=70`
  abilita solo flag `is_ambiguous` per highlight, NON e' threshold
  di scarto. Coerente con feedback Leader "match ambigui con
  confidence" (memory `feedback_ambigui_con_confidence.md`).
- **(4) a**: nuova tabella `description_resolutions` (UPSERT),
  scope CHG-2026-05-01-019.
- **(5) A**: input CSV/XLSX con colonne `descrizione` + `prezzo`,
  scope CHG-2026-05-01-020 (UI).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/asin_resolver.py` | nuovo | `ResolutionCandidate` frozen dataclass (asin, title, buybox_eur, fuzzy_title_pct, delta_price_pct, confidence_pct). `ResolutionResult` frozen dataclass (description, input_price_eur, selected, candidates, is_ambiguous default True, notes default empty tuple). `AsinResolverProtocol` con `resolve_description(description, input_price_eur) -> ResolutionResult`. Helper puri `compute_confidence(fuzzy_title_pct, delta_price_pct) -> float` (60/40 weighted, saturazione 0-100, R-01 ValueError su out-of-range) + `is_ambiguous(confidence_pct, *, threshold)`. Costanti modulo-level: `DEFAULT_AMBIGUOUS_THRESHOLD_PCT=70`, `CONFIDENCE_WEIGHT_TITLE=0.6`, `CONFIDENCE_WEIGHT_PRICE=0.4`, `_FUZZY_PCT_MIN/MAX`. |
| `src/talos/extract/__init__.py` | modificato | Re-export tipi e helper: `ResolutionCandidate`, `ResolutionResult`, `AsinResolverProtocol`, `compute_confidence`, `is_ambiguous`, costanti soglie/pesi. |
| `tests/unit/test_asin_resolver_skeleton.py` | nuovo | 20 test unit: 2 costanti di design (pesi sommano 1.0, threshold default 70), 8 test `compute_confidence` (perfect match, zero match, edge cases, saturation, lookup_failed=None, validation), 4 test `is_ambiguous` (default + custom threshold), 4 dataclass shape (frozen, default field, factory), 2 Protocol shape (mock duck-typed). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **587
PASS** unit/gov/golden + 122 integration = **709 PASS** (era 693,
+20 unit nuovi, integration invariata).

## Why

Il flusso d'uso reale del Leader (chiarito 2026-05-01 round 4):
l'utente carica un file con `descrizione` + `prezzo` per riga, NON
con ASIN. Il sistema risolve ogni riga in un ASIN candidato
verificato, prima di passare alla pipeline VGP esistente.

Architettura attuale (CHG-006/009/010) presuppone ASIN come
**input**: `acquire_and_persist(asin_list, ...)`,
`lookup_products(asin_list, ...)`. Lo stadio "description -> ASIN"
e' completamente assente. CHG-016 inaugura il modulo
`asin_resolver` come gap-fill, additivo e backward-compat strict
(la catena esistente non si rompe; resta in piedi per use case
"CSV con ASIN gia' noto", se mai servira').

Il pattern "tipi + Protocol + helper puri prima del live adapter"
e' lo stesso applicato a `KeepaClient` (CHG-001 skeleton),
`AmazonScraper` (CHG-002), `OcrPipeline` (CHG-003): permette di
costruire la catena di chiamate (resolver -> SERP adapter ->
lookup_product -> scoring) interamente con mock prima di toccare
network. CHG-017 introdurra' `_AmazonSerpAdapter` live.

Il dataclass `ResolutionCandidate` e' progettato per esporre tutti
gli ingredienti del confidence in modo trasparente alla UI (titolo
fuzzy, delta prezzo, confidence finale). Pattern coerente con
"honest reporter" applicato altrove. Il CFO vede ESATTAMENTE
perche' un match e' ambiguo, non solo che lo e'.

### Decisioni di design

1. **`compute_confidence` come pure function modulo-level**:
   testabile in isolamento con doctest + parametrici. Pattern
   coerente con `_last_valid_value` di Keepa adapter (CHG-015) e
   `parse_eur` di scraper (CHG-002). Le decisioni di pesatura
   restano in costanti modulo-level (riusabili da test e UI).

2. **`is_ambiguous` come funzione separata, NON metodo del
   dataclass**: il flag puo' cambiare con `threshold` diverso
   (futuro: caller passa threshold da `config_overrides`, L10-style).
   Mantenerlo separato evita di mutare lo stato del candidate per
   un'analisi UI.

3. **`ResolutionResult.is_ambiguous` default `True`**: posizione
   conservativa - meglio segnalare ambiguo per default e farlo
   smentire dal caller che il contrario. `selected=None` (zero
   risultati SERP) implica is_ambiguous=True coerentemente.

4. **`notes: tuple[str, ...]` invece di string singola**: pattern
   coerente con `ProductData.notes` (CHG-006). Audit trail di tutte
   le ragioni di ambiguita' / fallback / lookup failure.

5. **Pesi 60/40 (title/price)**: ratifica decisione Leader
   alpha-prime. Il titolo conta piu' del prezzo: i listini
   fornitore possono avere prezzi diversi dal Buy Box (sconti,
   promozioni, errori manuali del fornitore), ma se il titolo
   matcha bene siamo abbastanza sicuri dell'ASIN. Override-abile
   in costanti se serve modulazione futura.

6. **`fuzzy_title_pct` validato in [0, 100]**: contratto con
   `rapidfuzz` (gia' dep CHG-004). Il ratio rapidfuzz e' sempre in
   quel range. Validazione esplicita serve a catch rotture future
   se cambia libreria.

7. **`delta_price_pct: float | None`**: `None` esplicito quando il
   lookup live fallisce e non si ha buybox. Penalizza il candidato
   ma non lo butta. Pattern R-01 al livello UI (visibile come
   "prezzo non verificato" invece che scarto silente).

8. **`compute_confidence(80.0, None) = 48.0`** (verbatim docstring):
   title 80 -> 80*0.6 = 48; price=None -> 0*0.4 = 0; somma 48.
   Documentato come boundary case nel docstring.

9. **Doctest nel docstring**: pattern coerente con
   `fee_fba_manual` (CHG-022) e `min_max_normalize` (CHG-034).
   Self-documentation eseguibile.

10. **`_FUZZY_PCT_MIN/MAX` come costanti private**: sostituiscono
    magic 0/100 nei controlli (ruff PLR2004). Usati anche nella
    saturazione del price_score.

11. **Modulo collocato in `extract/`** (non `io_/`): scope = NLP/
    matching/scoring. Pattern coerente con `extract/samsung.py`
    (Samsung extractor) e `extract/asin_master_writer.py` (DB writer).
    `io_/serp_search.py` (CHG-017 atteso) sara' invece il pure adapter
    Playwright. Separazione: io_=ingestione raw, extract=composizione/
    semantica.

### Out-of-scope

- **`_AmazonSerpAdapter` live**: scope CHG-2026-05-01-017
  (Playwright SERP scraping `amazon.it/s?k=`).
- **Integrazione `lookup_product` per verifica prezzo**: scope
  CHG-2026-05-01-018.
- **Persistenza cache** `description_resolutions`: scope
  CHG-2026-05-01-019.
- **UI Streamlit nuovo flow upload**: scope CHG-2026-05-01-020.
- **Keepa Product Search fallback**: scope CHG futuro post-CHG-018
  se SERP scraping non basta.
- **Multi-resolver concurrent batch**: scope futuro
  (asyncio.gather su lista descrizioni).
- **Telemetria nuova**: nessun evento canonico in CHG-016.
  CHG-018 candidato per `asin_resolver.ambiguous` /
  `asin_resolver.no_match` / `asin_resolver.cache_hit` (errata
  catalogo ADR-0021 additiva, pattern CHG-058).

## How

### `compute_confidence` (highlight verbatim)

```python
def compute_confidence(
    fuzzy_title_pct: float,
    delta_price_pct: float | None,
) -> float:
    if not _FUZZY_PCT_MIN <= fuzzy_title_pct <= _FUZZY_PCT_MAX:
        raise ValueError(f"fuzzy_title_pct out of range [0,100]: {fuzzy_title_pct}")
    if delta_price_pct is not None and delta_price_pct < 0:
        raise ValueError(f"delta_price_pct negativo invalido: {delta_price_pct}")

    price_score = (
        0.0 if delta_price_pct is None
        else max(0.0, _FUZZY_PCT_MAX - delta_price_pct)
    )
    return (
        fuzzy_title_pct * CONFIDENCE_WEIGHT_TITLE
        + price_score * CONFIDENCE_WEIGHT_PRICE
    )
```

### `ResolutionResult` (highlight)

```python
@dataclass(frozen=True)
class ResolutionResult:
    description: str
    input_price_eur: Decimal
    selected: ResolutionCandidate | None
    candidates: tuple[ResolutionCandidate, ...] = field(default_factory=tuple)
    is_ambiguous: bool = True  # default conservativo
    notes: tuple[str, ...] = field(default_factory=tuple)
```

### Test plan eseguito (20 unit, no network)

- 2 costanti design (pesi sommano 1.0, threshold default 70)
- 8 `compute_confidence`: perfect/zero/strong/lookup_failed/saturation
  + 3 validation parametrici (out-of-range title) + 1 negative delta
  + 1 boundary delta=0
- 4 `is_ambiguous`: below/at/above default + custom threshold
- 3 dataclass shape (frozen, default ambiguous=True, with selected)
- 2 Protocol shape (mock duck-typed accettato come Protocol)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (50 source files, +1 vs CHG-015) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **587 PASS** (era 567, +20 nuovi `test_asin_resolver_skeleton`) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration --ignore=tests/integration/test_live_keepa.py -q` | **122 PASS** (invariato; live Keepa skipped per non consumare quota inutile) |

**Rischi residui:**
- **Pesi 60/40 hardcoded**: se l'evidenza empirica futura mostrera'
  che il prezzo conta piu' di 40% (es. listini fornitore molto
  fedeli al Buy Box), si possono modulare via costante. Trade-off
  noto.
- **Soglia ambiguita' 70**: scelta editoriale. Override-abile via
  parametro a `is_ambiguous(threshold=...)`. Eventuale
  configurabilita' DB-side (config_overrides) scope futuro.
- **`fuzzy_title_pct` saturato a 100**: se rapidfuzz introducesse
  scale diverse (es. token_set_ratio > 100 in alcune versioni),
  il validator alza ValueError. Pin minimo `rapidfuzz>=3,<4` (CHG-004)
  protegge.
- **`Decimal` solo in TYPE_CHECKING**: ruff TC003 richiesto. Le
  costruzioni `Decimal(...)` runtime sono nei test e in CHG futuri
  (importati lì runtime). Pattern coerente con scraper (CHG-002).

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/asin_resolver.py`
  ✓ (area `extract/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Pattern Adapter + Protocol per separazione network/logica ✓
  - R-01 NO SILENT DROPS: `is_ambiguous` flag UI, mai scarto.
    `compute_confidence` ValueError esplicito su input invalido.
- **Test unit puri:** ✓ (ADR-0019), no network, no DB, no fixture
  pesanti.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** modulo `asin_resolver`
  -> ADR-0017 (canale acquisizione descrizione->ASIN, estensione
  naturale dei 3 canali esistenti).
- **Backward compat strict:** modulo nuovo, nessun caller esistente
  toccato. `acquire_and_persist`/`lookup_product`/UI invarianti.
- **Sicurezza:** modulo non legge secrets, non fa network in
  CHG-016. Sicurezza dei live adapter scope CHG futuri.
- **Impact analysis pre-edit:** non applicabile (modulo nuovo, 0
  caller upstream). GitNexus dopo merge mostrera' che
  `asin_resolver` viene esposto via `talos.extract` re-export.

## Impact

- **Apertura blocco asin_resolver**: 1/5 CHG attesi (skeleton tipi).
  Restano CHG-017 (SERP adapter live), CHG-018 (`resolve_description`
  con lookup verification), CHG-019 (cache UPSERT), CHG-020 (UI flow).
- **Pattern "honest reporter"** applicato all'UX: il `confidence_pct`
  e' esposto, non aggregato in flag binari. Coerente con feedback
  Leader memory `feedback_ambigui_con_confidence.md`.
- **`pyproject.toml` invariato** (zero nuove deps in CHG-016;
  rapidfuzz gia' dep da CHG-004 sara' usato in CHG-017+).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11 viventi).
  CHG futuri introdurranno eventi `asin_resolver.*` via errata
  additiva.
- **Test suite cresce di +20 unit**: 587 PASS (was 567), zero
  regression in altri moduli.
- **Sblocco UX flusso reale Leader**: senza il blocco asin_resolver,
  il sistema chiede ASIN come input al CFO -> non realistico in
  produzione (i listini fornitore Samsung non arrivano con ASIN).

## Refs

- ADR: ADR-0017 (canale acquisizione, estensione descrizione->ASIN),
  ADR-0014 (mypy/ruff strict + dataclass frozen pattern), ADR-0019
  (test unit puri pattern).
- Predecessori:
  - CHG-2026-05-01-002 (`AmazonScraper` + `parse_eur` + Playwright
    skeleton): `_PlaywrightBrowserPage` riusabile per SERP adapter
    in CHG-017.
  - CHG-2026-05-01-004 (`SamsungExtractor` + `rapidfuzz`): pattern
    fuzzy ratio riutilizzato per `compute_confidence`.
  - CHG-2026-05-01-006 (`lookup_product` fallback chain): consumer
    della verifica prezzo in CHG-018.
  - CHG-2026-05-01-015 (`_LiveKeepaAdapter` live): consumer della
    verifica prezzo via `lookup_product` -> Keepa NEW + scraper.
- Decisioni Leader 2026-05-01 round 4: ratifica 1=A / 2=alpha-prime
  / 3=i-prime / 4=a / 5=A formulate dopo ratifica decisioni Keepa
  (A2/A/alpha'').
- Memory: `feedback_ambigui_con_confidence.md` (direttiva
  R-01 NO SILENT DROPS UX-side, fonte di is_ambiguous come flag
  visibile, non skip).
- Successore atteso: CHG-2026-05-01-017 `_AmazonSerpAdapter` live
  (Playwright SERP `amazon.it/s?k=<query>` -> top-N ASIN + titoli).
- Commit: TBD (backfill post-commit).
