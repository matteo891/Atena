---
id: CHG-2026-05-01-004
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" sessione attivata 2026-04-30 sera, prosegue oltre mezzanotte)
status: Draft
commit: 2140ab4
adr_ref: ADR-0017, ADR-0018, ADR-0014, ADR-0019, ADR-0021
---

## What

Aggiunge `SamsungExtractor` a `src/talos/extract/` — quarto CHG
del blocco `io_/extract` Samsung (ADR-0017 + R-05 PROJECT-RAW).
Inaugura il package `extract/`. SamsungExtractor implementa
l'estrazione NLP pipeline (PROJECT-RAW L07): tokenize -> estrai
entita' -> applica whitelist 5G -> confronta lati fornitore/Amazon
-> emit `MATCH_SICURO` / `AMBIGUO` / `MISMATCH`.

R-05 KILL-SWITCH HARDWARE: modello mismatch (entrambi non None
ma diversi) forza `MatchStatus.MISMATCH` a prescindere dalla
confidence aggregata. Il caller (orchestrator + vgp.score, CHG-005
integratore) forza `vgp_score=0` e logga l'evento canonico
`extract.kill_switch` (ADR-0021 dormiente).

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | + dep `rapidfuzz>=3.0,<4` (D4.a NLP fuzzy matching). Trascina niente (rapidfuzz e' standalone). |
| `src/talos/extract/__init__.py` | nuovo | Re-export `SamsungExtractor`, `SamsungEntities`, `MatchResult`, `MatchStatus`, `load_whitelist`, costanti default (`DEFAULT_WHITELIST_YAML`, `DEFAULT_FIELD_WEIGHTS`, `DEFAULT_CONFIDENCE_*`, `DEFAULT_COLOR_FUZZY_THRESHOLD`). Inaugura il package `extract/` (ADR-0013 area consentita). |
| `src/talos/extract/samsung_whitelist.yaml` | nuovo | Whitelist versionata D4.b: `models_5g` (20 voci: Galaxy S22-S24, A15-A55, Z Fold/Flip 4-5), `ram_gb_canonical` ([4,6,8,12,16]), `rom_gb_canonical` ([64,128,256,512,1024]), `colors_canonical` (17 colori Samsung ufficiali: Titanium/Phantom/Onyx/Marble/Cobalt/Awesome series). |
| `src/talos/extract/samsung.py` | nuovo | Costanti `DEFAULT_WHITELIST_YAML` (Path), `DEFAULT_FIELD_WEIGHTS` (model=3, ram=2, rom=2, color=1, conn=1), `DEFAULT_CONFIDENCE_SICURO_THRESHOLD=0.85`, `DEFAULT_CONFIDENCE_AMBIGUO_THRESHOLD=0.50`, `DEFAULT_COLOR_FUZZY_THRESHOLD=80`. `class MatchStatus(StrEnum)`: `SICURO`/`AMBIGUO`/`MISMATCH`. `@dataclass(frozen=True) SamsungEntities(model, ram_gb, rom_gb, color, connectivity, enterprise)` (tutti opzionali). `@dataclass(frozen=True) MatchResult(status, confidence, matched_fields, mismatched_fields)`. `_Whitelist` privato + `load_whitelist(path)` con validazione schema. Regex compilate riusabili (`_RAM_PATTERN`, `_RAM_INLINE_PATTERN`, `_ROM_GB_PATTERN`, `_CONNECTIVITY_PATTERN`, `_ENTERPRISE_PATTERN`). `SamsungExtractor(*, whitelist_path, field_weights, sicuro_threshold, ambiguo_threshold, color_fuzzy_threshold)` con: `parse_title(raw)` -> `SamsungEntities`; `_extract_model` (longest-match dalla whitelist, S24 Ultra prima di S24); `_extract_ram` (regex `\d{1,2}GB RAM` + filtro whitelist canonica + fallback inline `12+256`); `_extract_rom` (regex `\d{2,4}GB` skip se seguito da RAM + filtro whitelist + fallback inline); `_extract_color` (`rapidfuzz.process.extractOne` partial_ratio con soglia configurabile); `_extract_connectivity` (4G/5G/LTE -> 4G); `match(*, supplier, amazon)` -> `MatchResult` con weighted sum + R-05 hard su model mismatch. |
| `tests/unit/test_samsung_extractor.py` | nuovo | 31 test unit (whitelist YAML default in repo + tmp_path fixture, niente network): 3 `load_whitelist` (default valido + missing keys raise + non-mapping raise); 3 construction (default + invalid thresholds + invalid color threshold); 3 model extraction (S24 base / longest-match S24 Ultra / unknown -> None); 3 RAM/ROM (RAM keyword / ROM separato / inline `12+256` / not in whitelist -> None); 3 color (canonical exact / fuzzy match con soglia 70 / no match con soglia 95); 4 connectivity parametrici (5G/4G/LTE/none); 2 enterprise (set/unset); 7 match (perfect SICURO / partial AMBIGUO / weak MISMATCH / **R-05 model mismatch hard** / model None side / custom weights SICURO / MatchResult frozen); 2 end-to-end (realistic SICURO / R-05 trigger). |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | + 4 nuove righe sotto `src/talos/extract/`: package marker, samsung.py descrittivo, samsung_whitelist.yaml schema, riga sintetica del modulo. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**609 PASS** (509 unit/governance/golden + 100 integration).
Delta unit: +31 (`test_samsung_extractor.py`).

## Why

R-05 KILL-SWITCH HARDWARE (PROJECT-RAW riga 223 verbatim):
*"Mismatch NLP forza VGP a 0"*. Senza un estrattore strutturato,
il caller deve fare matching ad hoc su titoli grezzi -> R-05 viene
applicato in modo inconsistente -> falsi positivi/negativi sul
carrello.

L07 (PROJECT-RAW Round 5): l'estrattore Samsung integra il filtro
NLP Kill-Switch come fase finale di validazione interna allo
stesso modulo (NON un modulo separato). Implementazione
modulare candidate per `BrandExtractor` interface astratta
(L06: estensione multi-brand post-MVP).

CHG-2026-05-01-004 e' il **quarto CHG del blocco `io_/extract`
Samsung** (4-5 attesi, decisioni Leader D1-D5 ratificate "default"
2026-04-30 sera). D4 applicata in questo CHG.

### Decisioni di design (D4 ratificata)

1. **D4.a NLP: C = regex + rapidfuzz**: regex Python per estrazione
   strutturata (modello, RAM, ROM, connettivita', enterprise);
   `rapidfuzz.process.extractOne` con `fuzz.partial_ratio` per
   matching colore tollerante a varianti minori (capitalizzazione,
   abbreviazioni, accenti). No spaCy: trasparenza > resilienza
   marginale, dep leggera (~3 MB rapidfuzz vs ~200 MB spaCy
   modello italiano).

2. **D4.b Whitelist 5G: C = YAML versionato**:
   `extract/samsung_whitelist.yaml`. Patch operativa rapida (no
   redeploy per aggiungere modelli). Schema strutturato:
   `models_5g`, `ram_gb_canonical`, `rom_gb_canonical`,
   `colors_canonical`. Il filtro implicito: solo modelli in
   whitelist sono Samsung 5G validi -> match con valori esterni
   produce `model=None` -> R-05 implicito a valle (modello mancante
   -> match degraded).

3. **D4.c Confidence: B = weighted sum**: pesi configurabili al
   constructor. Default ratificato: `model=3, ram_gb=2, rom_gb=2,
   color=1, connectivity=1` (totale 9). Soglie:
   `sicuro_threshold=0.85` (>= 7.65/9 punti) e
   `ambiguo_threshold=0.50` (>= 4.5/9 punti). Sotto -> MISMATCH
   (R-05 trigger soft via low confidence).

4. **R-05 hard model mismatch**: separato dalla soglia confidence.
   Se `supplier.model != amazon.model` (entrambi non None),
   ritorna `MISMATCH` a prescindere dalla confidence aggregata.
   Razionale: due Samsung diversi (S24 vs S23) sono prodotti
   distinti, non variazioni di colore. La soglia confidence non
   puo' compensare la mismatch del modello (gerarchia di campi).

5. **Longest-match per modello**: ordinamento whitelist per
   lunghezza DESC (`Galaxy S24 Ultra` prima di `Galaxy S24`).
   Evita falsi positivi su prefissi.

6. **RAM/ROM con filtro whitelist canonica**: il regex `\d{1,2}GB`
   matcha qualsiasi numero (es. il "24" di "S24" se mal-tokenizzato).
   Il filtro `value in whitelist.ram_gb_canonical` esclude valori
   non plausibili (limita falsi positivi).

7. **Pattern inline `12+256`**: variante compact `RAM+ROM` usata
   da alcuni listini. Estratta come fallback dopo i pattern
   espliciti.

8. **`StrEnum` per `MatchStatus`**: serializza naturalmente in
   JSON/log strutturati. Coerente con `OcrStatus` (CHG-003).

9. **Enterprise come flag separato (non pesato)**: PROJECT-RAW
   menziona Enterprise come SKU discriminante MA scope CHG-004
   minimal NON include Enterprise nel calcolo confidence (peso
   default 0). Caller potra' override via `field_weights` per
   includerlo in CHG futuri.

### Out-of-scope

- **`BrandExtractor` interface astratta**: rinviata post-MVP (L06).
  `SamsungExtractor` e' l'unica implementazione concreta in MVP.
- **AppleExtractor / XiaomiExtractor**: post-MVP.
- **Inferenza RAM da contesto** ("smaller=RAM larger=ROM" su 2
  numeri "GB" senza keyword): scope CHG futuro. Il test
  end-to-end documenta il workaround richiesto al caller.
- **Telemetria evento `extract.kill_switch`**: catalogo ADR-0021
  (dormiente). Attivata nell'integratore CHG-005 quando
  l'orchestrator chiama `match` e gestisce il `MISMATCH`.
- **Spell correction su modello via rapidfuzz**: scope futuro
  (es. "S24Ultra" senza spazio non matcha "Galaxy S24 Ultra"
  attualmente).
- **Cache di `parse_title`**: scope futuro (Streamlit
  `@st.cache_data`).
- **Persistenza `MatchResult` su DB**: scope orchestratore /
  integratore CHG-005 (eventuale colonna `match_status` su
  `vgp_results`).

## How

### `_extract_model` longest-match (highlight)

```python
def _extract_model(self, text):
    text_lower = text.lower()
    candidates = sorted(self._whitelist.models_5g, key=len, reverse=True)
    for model in candidates:
        if model.lower() in text_lower:
            return model
    return None
```

### `_extract_color` rapidfuzz (highlight)

```python
def _extract_color(self, text):
    best = process.extractOne(
        text,
        self._whitelist.colors_canonical,
        scorer=fuzz.partial_ratio,
        score_cutoff=self._color_fuzzy_threshold,
    )
    return str(best[0]) if best else None
```

### `match` con R-05 hard (highlight)

```python
def match(self, *, supplier, amazon):
    model_mismatch_hard = (
        supplier.model is not None and amazon.model is not None
        and supplier.model != amazon.model
    )
    # Calcolo weighted sum su tutti i campi disponibili
    score = sum(
        weights[f] for f in fields
        if sup_value is not None == amz_value is not None
        and sup_value == amz_value
    )
    confidence = score / sum(weights.values())
    if model_mismatch_hard:
        return MatchResult(status=MatchStatus.MISMATCH, ...)  # R-05
    if confidence >= sicuro_threshold:
        status = MatchStatus.SICURO
    elif confidence >= ambiguo_threshold:
        status = MatchStatus.AMBIGUO
    else:
        status = MatchStatus.MISMATCH
    return MatchResult(status, confidence, matched_fields, mismatched_fields)
```

### Test plan eseguito

31 unit test su `samsung.py` + `samsung_whitelist.yaml`:

- 3 `load_whitelist` (default valido / missing keys / non-mapping)
- 3 construction (default + invalid thresholds + invalid color)
- 3 model (S24 base / longest S24 Ultra / unknown -> None)
- 3 RAM/ROM (RAM keyword / ROM separato / inline `12+256` /
  RAM 999 not whitelist -> None)
- 3 color rapidfuzz (canonical exact / fuzzy "Titanium Blk" / no match)
- 4 connectivity parametrici (5G / 4G / LTE -> 4G / none)
- 2 enterprise flag (set / unset)
- 7 match (perfect SICURO / 7/9 AMBIGUO / 2/9 MISMATCH /
  **R-05 model mismatch** / model None side soft / custom
  weights SICURO / MatchResult frozen)
- 2 end-to-end (realistic SICURO / R-05 trigger MISMATCH)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/extract/ tests/unit/test_samsung_extractor.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_samsung_extractor.py` | 0 issues (47 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **509 PASS** (era 478, +31) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **100 PASS** (invariato) |

**Rischi residui:**
- **Estrazione RAM senza keyword 'RAM'**: titoli con due "GB"
  consecutivi (es. "256GB 12GB Black") senza la keyword "RAM"
  espressa producono `ram_gb=None`. Workaround: il caller
  normalizza il titolo a monte; CHG futuro estendera' con
  dispatch "smaller=RAM larger=ROM" sulle whitelist canoniche.
  Documentato nel test `test_end_to_end_supplier_amazon_match_realistic`.
- **rapidfuzz partial_ratio su colori brevi**: il fuzzy match
  con soglia bassa puo' produrre falsi positivi (es. "Black"
  matcha "Titanium Black"). Soglia default 80 e' conservativa.
- **R-05 hard solo su model mismatch**: NON scatta su mismatch
  RAM/ROM (es. fornitore 256GB vs Amazon 512GB diverso prodotto?).
  Decisione conservativa: solo il modello e' R-05 hard;
  altri mismatch contribuiscono alla confidence (-> AMBIGUO o
  MISMATCH soft).
- **Whitelist `models_5g` parziale**: Galaxy S25 e modelli futuri
  non saranno estratti finche' non aggiunti al YAML. Patch
  operativa rapida via PR / CHG.
- **Enterprise non pesato di default**: il flag c'e' ma non
  contribuisce alla confidence. Caller puo' override `field_weights`
  per includere `enterprise: N`. Dual-SKU consumer/enterprise
  Samsung resta visibile ma non discriminante in CHG-004.

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/__init__.py`,
  `src/talos/extract/samsung.py`, `src/talos/extract/samsung_whitelist.yaml`
  ✓ (area `extract/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - SamsungExtractor unico modulo MVP (L06) ✓
  - Pipeline interna (L07): tokenize -> estrai -> whitelist 5G
    -> confronta -> emit ✓
  - Status MATCH_SICURO / AMBIGUO / MISMATCH ✓ (verbatim)
- **R-05 KILL-SWITCH HARDWARE rispettato:** model mismatch ->
  MISMATCH a prescindere ✓ (caller forza VGP=0 in CHG-005).
- **R-01 NO SILENT DROPS (governance test):** ✓
  (`extract.kill_switch` menzionato esplicitamente nel
  docstring; il governance test cerca la stringa).
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `SamsungExtractor`,
  `SamsungEntities`, `MatchStatus`, `MatchResult`,
  `load_whitelist` -> ADR-0017 + ADR-0018 (R-05).
- **Backward compat:** modulo nuovo, niente break.
- **Impact analysis pre-edit:** primo file in `extract/`
  (zero caller esistenti).

## Impact

- **Quarto CHG del blocco `io_/extract` Samsung chiuso.**
  Resta CHG-005 = integratore (live adapters Keepa/Playwright/
  Tesseract + asin_master writer + fallback chain end-to-end +
  telemetria 5 eventi dormienti).
- **`pyproject.toml` cresce di 1 dep applicativa**: `rapidfuzz`
  (~3 MB, standalone, zero trascinamenti).
- **`src/talos/extract/` package inaugurato.** Schema atteso:
  `BrandExtractor` (futura abstract) + `SamsungExtractor` +
  multi-brand post-MVP.
- **5 eventi dormienti ADR-0021** (`keepa.miss`,
  `keepa.rate_limit_hit`, `scrape.selector_fail`,
  `ocr.below_confidence`, `extract.kill_switch`) sono ora **tutti
  citati** nei docstring dei rispettivi moduli (anche dormienti).
  Attivazione runtime in CHG-005.
- **`MatchStatus.MISMATCH` -> R-05 hard**: il caller (orchestrator
  + vgp.score) deve forzare `vgp_score=0` per quella riga e
  loggare `extract.kill_switch`. Pattern integrazione in CHG-005.
- **Avanzamento blocco `io_/extract` Samsung: 4/5**.

## Refs

- ADR: ADR-0017 (canale extract), ADR-0018 (R-05 KILL-SWITCH),
  ADR-0014 (mypy/ruff strict), ADR-0019 (test unit pattern),
  ADR-0021 (catalogo eventi `extract.kill_switch` dormiente).
- Predecessori: CHG-2026-05-01-001 (`KeepaClient`),
  CHG-2026-05-01-002 (`AmazonScraper`), CHG-2026-05-01-003
  (`OcrPipeline`) — pattern adapter + R-01 + skeleton coerente.
- Successore atteso: CHG-2026-05-01-005 = integratore fallback
  chain (live adapters + asin_master writer + telemetria 5 eventi
  + orchestrator integration con R-05 hard).
- Memory: `project_io_extract_design_decisions.md` (D4 ratificata
  "default").
- PROJECT-RAW: L06 (Samsung MVP), L07 (pipeline interna), R-05
  (KILL-SWITCH), riga 223.
- Commit: `2140ab4`.
