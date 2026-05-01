---
id: CHG-2026-05-01-007
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 2 attiva, Path B target)
status: Draft
commit: TBD
adr_ref: ADR-0017, ADR-0021, ADR-0014, ADR-0019
---

## What

Quick win Fase 1 Path B: estende la signature
`SamsungExtractor.match` con il kwarg opzionale
`asin: str | None = None`. Quando fornito, l'evento canonico
`extract.kill_switch` (catalogo ADR-0021) emette il valore reale
nel campo `extra["asin"]` invece del sentinel `<n/a>` introdotto
in CHG-2026-05-01-005 come placeholder.

Backward compat strict: il kwarg ha default `None`, quindi tutti
i caller esistenti (test_samsung_extractor + test_io_extract_telemetry
+ orchestratore + future fallback chain) continuano a funzionare
senza modifiche; passando `asin=None` esplicito si ottiene il
sentinel `"<n/a>"` (preservato).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/samsung.py` | modificato | + kwarg `asin: str | None = None` a `SamsungExtractor.match`. Docstring esteso con argomento + nota CHG-007. Espressione literal `"asin": "<n/a>"` sostituita da `"asin": asin if asin is not None else "<n/a>"` (sentinel preservato in default; asin reale popolato quando passato). |
| `tests/unit/test_io_extract_telemetry.py` | modificato | + 2 test nuovi: (1) `test_extract_kill_switch_uses_real_asin_when_provided` (asin="B0CN3VDM4G" -> rec.asin == "B0CN3VDM4G"); (2) `test_extract_kill_switch_explicit_none_asin_falls_back_to_sentinel` (asin=None esplicito -> rec.asin == "<n/a>"). + asserzione `rec.asin == "<n/a>"` aggiunta al test esistente `test_extract_kill_switch_event_emitted_on_model_mismatch` (sentinel preservato senza kwarg, backward compat verificata meccanicamente). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**641 PASS** (536 unit/governance/golden + 105 integration; era
639, +2 nuovi test).

## Why

In CHG-2026-05-01-005 la telemetria `extract.kill_switch` era
stata attivata con `asin="<n/a>"` perche' `SamsungExtractor.match`
non riceveva l'asin come kwarg (la signature era
`(*, supplier, amazon)`). Il sentinel era documentato come
"scope futuro integratore puo' wrappare con context completo".

Il quick win di Fase 1 Path B chiude il gap **senza** richiedere
setup di sistema:

1. La nota d'handoff 2026-05-01 elenca esplicitamente
   "Estensione signature `SamsungExtractor.match(asin)` per
   popolare correttamente il campo `asin` dell'evento
   `extract.kill_switch` (in CHG-005 e' sentinel `<n/a>`)" come
   item 3 del prossimo blocco strategico.
2. La fallback chain orchestratrice CHG-006 (`lookup_product`)
   conosce l'asin call-site; quando in Fase 3 l'integratore
   collegera' `lookup_product` -> `SamsungExtractor.match`,
   passare l'asin sara' un parametro gia' a portata di mano.
3. La modifica e' additiva (default=None) e l'impact GitNexus e'
   LOW (0 caller funzionali, backward compat strict).

### Decisioni di design

1. **Kwarg con default `None`, non required**: backward compat
   strict. Pattern coerente con `SamsungEntities` (tutti i campi
   opzionali) e con la signature originale di CHG-005. Caller
   che non hanno l'asin a portata di mano (test parametrici,
   call site senza context) non sono costretti a fornire un
   valore artificiale.

2. **Sentinel `<n/a>` preservato come fallback**: pattern
   coerente con CHG-005 (sentinel `<no-html>`/`<image>` su
   altri eventi del catalogo). Razionale: i log filtrabili per
   asin reale sono utili; quelli con sentinel sono comunque
   tracciabili come "asin non disponibile al call site",
   distinguibili da una assenza totale del campo.

3. **Espressione literal in `extra={...}`**: l'evento mantiene
   la chiave `"asin"` come literal nel dict; il valore e'
   calcolato inline (`asin if asin is not None else "<n/a>"`).
   Il governance test `test_log_events_catalog` rileva la
   stringa `"extract.kill_switch"` nel codice (literal
   obbligatorio per il grep). Aggiungere una costante non
   romperebbe il test ma aggiunge ridondanza non necessaria.

4. **Nessun rename del kwarg in `target_asin`/`amazon_asin`**:
   il dominio NLP del modulo e' Samsung-specific ma l'asin e'
   quello Amazon. Nominare il kwarg semplicemente `asin` segue
   la convenzione degli altri moduli `io_/extract` (KeepaClient,
   AmazonScraper, asin_master_writer usano tutti `asin`).

5. **Test su `_assert kill_records[0].asin == ...`**: pattern
   coerente con i test esistenti di telemetria (rec.reason /
   rec.expected etc.). caplog espone gli `extra` come attributi
   sull'oggetto `LogRecord` (`# type: ignore[attr-defined]`
   gia' presente nel pattern del file).

### Out-of-scope

- **Propagazione `asin` ad altri eventi**: per ora solo
  `extract.kill_switch`. Gli altri eventi del catalogo
  (`scrape.selector_fail`, `ocr.below_confidence`,
  `keepa.miss`/`rate_limit_hit`) hanno gia' l'asin (Keepa) o
  sentinel diverso (`<no-html>`/`<image>`) per ragioni
  strutturali del modulo. Ognuno di quelli verra' affrontato
  in Fase 3 se il setup di sistema lo richiede.
- **Integrazione `match` -> `lookup_product`**: la fallback
  chain CHG-006 non chiama `SamsungExtractor.match` (non
  estrae brand entities). L'integratore Fase 3 collegera' i
  due, e a quel punto passera' `asin` da `ProductData.asin`.
- **Errata catalogo ADR-0021**: la voce `extract.kill_switch`
  e' gia' nel catalogo (CHG-005). Nessuna modifica al catalogo
  qui — solo al codice che popola il campo.

## How

### `SamsungExtractor.match` (highlight)

```python
def match(
    self,
    *,
    supplier: SamsungEntities,
    amazon: SamsungEntities,
    asin: str | None = None,  # <-- nuovo CHG-007
) -> MatchResult:
    ...
    if model_mismatch_hard:
        _logger.debug(
            "extract.kill_switch",
            extra={
                "asin": asin if asin is not None else "<n/a>",  # <-- CHG-007
                "reason": "model_mismatch",
                "mismatch_field": "model",
                "expected": supplier.model,
                "actual": amazon.model,
            },
        )
    ...
```

### Test plan eseguito

2 nuovi test in `test_io_extract_telemetry.py`:

- `test_extract_kill_switch_uses_real_asin_when_provided`:
  passa `asin="B0CN3VDM4G"` -> verifica `rec.asin == "B0CN3VDM4G"`.
- `test_extract_kill_switch_explicit_none_asin_falls_back_to_sentinel`:
  passa `asin=None` esplicito -> verifica `rec.asin == "<n/a>"`.

+1 asserzione aggiunta al test esistente
`test_extract_kill_switch_event_emitted_on_model_mismatch`
(senza kwarg `asin` -> sentinel preservato; backward compat
verificata meccanicamente).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/extract/samsung.py tests/unit/test_io_extract_telemetry.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_io_extract_telemetry.py tests/unit/test_samsung_extractor.py` | 0 issues (50 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **536 PASS** (era 534, +2) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **105 PASS** (invariato) |

**Rischi residui:**
- **Caller esistenti che NON passano `asin`**: continuano a
  emettere il sentinel `<n/a>`. La transizione "tutti i caller
  passano l'asin reale" e' graduale (avviene quando l'integratore
  Fase 3 li wrappera' con il context).
- **`asin` tipato come `str | None`** (non `str` strict):
  permette `None` esplicito. Pattern coerente con
  `SamsungEntities.{model,ram_gb,...}` (tutti opzionali).
  Caller che vogliono fail-fast su `asin` mancante devono
  validarlo prima del call.

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/samsung.py` ✓
  (area `extract/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - SamsungExtractor unico modulo MVP (L06) — invariato ✓
  - Pipeline interna (L07) — invariata ✓
  - Status MATCH_SICURO/AMBIGUO/MISMATCH — invariato ✓
- **R-05 KILL-SWITCH HARDWARE:** logica invariata ✓ (model
  mismatch -> MISMATCH a prescindere). Solo il payload telemetria
  arricchito.
- **Catalogo ADR-0021:** nessuna modifica al catalogo
  (`extract.kill_switch` gia' presente da CHG-005). Modifica
  riguarda solo il valore del campo `asin` dell'extra payload.
- **Test unit caplog:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** modifica di kwarg
  esistente (signature additiva) -> ADR-0017 (modulo coperto).
- **Backward compat:** modifica additiva con default. Test
  esistente `test_extract_kill_switch_event_emitted_on_model_mismatch`
  passa con kwarg invariato + asserzione aggiunta verifica il
  sentinel preservato.
- **Impact analysis pre-edit:** GitNexus impact upstream su
  `SamsungExtractor.match` = 0 caller, risk LOW. detect_changes
  conferma 0 affected processes.

## Impact

- **`extract.kill_switch` ora trasporta asin reale quando il
  caller lo fornisce**: i log strutturati diventano filtrabili
  per asin (audit Per-asin del trigger R-05).
- **Fase 1 Path B avanzamento**: 2/N CHG (CHG-006 +
  CHG-007). Catena CHG 2026-05-01: 001..007.
- **Pronto per Fase 3 integratore**: quando la fallback chain
  collegera' `lookup_product` (CHG-006) ->
  `SamsungExtractor.match` (CHG-007), `match(supplier=...,
  amazon=..., asin=product.asin)` chiudera' il loop.
- **`pyproject.toml` invariato**.
- **Catalogo ADR-0021**: 10/11 viventi (invariato). Solo il
  payload `extract.kill_switch` e' arricchito.

## Refs

- ADR: ADR-0017 (canale extract), ADR-0021 (catalogo eventi
  canonici), ADR-0014 (mypy/ruff strict), ADR-0019 (test unit
  caplog pattern).
- Predecessori: CHG-2026-05-01-004 (`SamsungExtractor` +
  R-05), CHG-2026-05-01-005 (telemetria 5 eventi attivati con
  sentinel `<n/a>`).
- Sibling: CHG-2026-05-01-006 (fallback chain
  `lookup_product`, primo Fase 1 Path B; conosce l'asin
  call-site, sara' il caller naturale di `match(asin=...)` in
  Fase 3).
- Pattern caplog di riferimento: tutti i test in
  `tests/unit/test_io_extract_telemetry.py` (pattern
  `caplog.records[i].field` con `# type: ignore[attr-defined]`).
- Memory: `project_io_extract_design_decisions.md` (D4
  ratificata "default", Samsung match weighted sum + R-05
  hard).
- Successore atteso (Fase 3): integratore live che chiama
  `SamsungExtractor.match(supplier=..., amazon=...,
  asin=product_data.asin)` post `lookup_product`.
- Commit: TBD.
