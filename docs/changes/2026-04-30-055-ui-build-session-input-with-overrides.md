---
id: CHG-2026-04-30-055
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Pending
commit: pending
adr_ref: ADR-0016, ADR-0018, ADR-0014, ADR-0019
---

## What

Introduce `build_session_input(factory, listino_raw, *, ...)` come
helper UI testabile che carica le `referral_fee_overrides` dal DB
(via `fetch_category_referral_fees_or_empty`) e costruisce un
`SessionInput` cablato con la mappa override per il tenant. La
dashboard `main()` adesso usa questo helper invece di costruire
`SessionInput` direttamente.

Il loop end-to-end **CFO modifica fee per categoria → DB
config_overrides → UI legge → SessionInput → orchestrator applica
override** è ora chiuso. Senza colonna `category_node` nel listino
raw (caso pre-extractor), gli override sono inerti e il comportamento
e' identico al pre-CHG (fail-safe).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | + `build_session_input(factory, listino_raw, *, budget, locked_in, velocity_target_days, veto_roi_threshold, lot_size, tenant_id=DEFAULT_TENANT_ID) -> SessionInput`. Carica overrides via fetch graceful (factory `None` → `{}` → `None` propagato). `main()` ora chiama `build_session_input(factory_for_sidebar, listino, ...)` invece di costruire `SessionInput(...)` direttamente. |
| `src/talos/ui/__init__.py` | modificato | + re-export `build_session_input`. |
| `tests/integration/test_build_session_input.py` | nuovo | 3 test integration: (1) factory=None → overrides=None (graceful); (2) override Books salvato in DB → SessionInput.referral_fee_overrides popolato + `run_session` produce `referral_fee_resolved=0.04` per BS01 e fallback raw 0.15 per EL02; (3) tenant inesistente → DB ritorna `{}` normalizzato a `None`. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **478 PASS**
(387 unit/governance/golden + 91 integration).

## Why

CHG-053 ha aggiunto `SessionInput.referral_fee_overrides` ma la
dashboard NON la riempiva: l'unico vero caller programmatico
(`run_session` da UI) passava `referral_fee_overrides=None` sempre.
Il loop persistenza ↔ pipeline restava tecnicamente aperto a livello
di codice.

Senza questo CHG:
- Il CFO salvava la fee per categoria via UI (CHG-051) ma il run
  successivo ignorava tutto.
- Il flusso di valore "fee modificata persiste tra rerun" funzionava
  solo per la soglia ROI (CHG-050), non per le referral fee.
- `referral_fee_overrides` era una primitiva senza consumer reale.

### Decisioni di design

1. **Helper esterno `build_session_input`** invece di logica inline
   in `main()`: testabile in isolamento (no Streamlit dependency),
   riutilizzabile in CHG futuri (es. multi-page o CLI).

2. **`overrides_floats or None`**: dict vuoto `{}` viene normalizzato
   a `None` esplicito. L'orchestratore tratta i due identici (CHG-053
   `if overrides`), ma `None` esprime meglio l'intent "nessun override
   registrato per il tenant".

3. **`tenant_id` propagato** come kwarg con default `DEFAULT_TENANT_ID`:
   coerente con tutte le altre helper UI (CHG-044+).

4. **Niente UI hint "X override caricati"**: l'utente vede già la
   tabella overrides in expander sidebar (CHG-051). Non serve una
   notifica al click "Esegui Sessione" che non aggiunge informazione.
   Audit visibile su `referral_fee_resolved` nell'`enriched_df` (CHG-053).

5. **Fail-safe quando colonna `category_node` assente**: il listino
   MVP (Samsung CSV pre-extractor) non ha `category_node`. Senza la
   colonna, `_resolve_referral_fee` (CHG-053) ritorna sempre il raw.
   L'helper carica gli override da DB ma sono inerti — comportamento
   equivalente al pre-CHG. Quando l'extractor sarà pronto e popolerà
   `category_node`, gli override si attiveranno automaticamente
   senza altre modifiche al codice.

6. **Tenant=88_888 sintetico per il test "empty"**: evita conflitto
   con tenant=1/77 usati altrove. Pattern coerente con CHG-054
   (tenant=99 per test UI helper).

### Out-of-scope

- **Caching `@st.cache_data`** sulla mappa overrides: scope refactor
  multi-page ADR-0016. Per ora ricarica ad ogni rerun (costo
  trascurabile, una query indicizzata su tabella piccola).
- **UI hint "X override caricati"** post-click: scope futuro UX se
  feedback richiesto.
- **CHG che assegna `category_node` ai listini sintetici di test**:
  i golden esistenti non hanno la colonna; restano deterministici
  perché in assenza di colonna gli override sono inerti.
- **Migrazione orchestrator → caching invocazione fetch overrides**:
  scope refactor multi-page se profiling lo richiederà.

## How

### `build_session_input` (highlight)

```python
def build_session_input(factory, listino_raw, *, budget, locked_in,
                       velocity_target_days, veto_roi_threshold, lot_size,
                       tenant_id=DEFAULT_TENANT_ID) -> SessionInput:
    overrides_floats = fetch_category_referral_fees_or_empty(
        factory, tenant_id=tenant_id,
    )
    overrides = overrides_floats or None
    return SessionInput(
        listino_raw=listino_raw,
        budget=budget,
        locked_in=locked_in,
        velocity_target_days=velocity_target_days,
        veto_roi_threshold=veto_roi_threshold,
        lot_size=lot_size,
        referral_fee_overrides=overrides,
    )
```

### `main()` wiring

```python
inp = build_session_input(
    factory_for_sidebar,
    listino,
    budget=budget,
    locked_in=locked_in,
    velocity_target_days=velocity_target,
    veto_roi_threshold=veto_threshold,
    lot_size=lot_size,
)
result = run_session(inp)
```

### Test plan (3 integration)

1. `test_build_session_input_with_factory_none_passes_no_overrides` —
   graceful: factory=None → overrides=None
2. `test_build_session_input_loads_overrides_from_db` — override Books
   salvato → SessionInput popolato + run_session usa override (audit
   `referral_fee_resolved`)
3. `test_build_session_input_empty_overrides_dict_normalized_to_none` —
   tenant inesistente → `{}` normalizzato a `None`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 97 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **387 PASS** (invariato) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **91 PASS** (88 + 3) |

**Rischi residui:**
- **Fetch overrides ad ogni rerun Streamlit**: nessun caching. Costo:
  1 query SELECT su `config_overrides` con WHERE indicizzata. Tipico
  < 5ms su LAN. Cache scope multi-page.
- **Override "fantasma" (categoria salvata, listino senza
  `category_node`)**: l'override si attiva solo per ASIN con
  categoria nel listino. Nessun warning UI; CFO può salvare un
  override "Books" per un listino senza colonna e non vedere
  effetto. Pattern documentato (fail-safe, non bug).
- **Test usa tenant=77 / 88_888**: il tenant 1 (default) ha già
  override "Books" in altri test. Tenant separati evitano cross-pollution.
  Cleanup paranoid finally + `set` UPSERT semantica rendono i test
  idempotenti.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/dashboard.py` ✓.
- **Test integration sotto `tests/integration/`:** ✓ (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `build_session_input` mappa
  ad ADR-0016 (UI Streamlit) — coerente con altri helper UI.
- **Backward compat:** `SessionInput` signature invariata.
  Comportamento dashboard senza factory DB invariato. Listini senza
  `category_node` invariati (gli override sono inerti).
- **Impact analysis pre-edit:** factory ↔ orchestrator non aveva
  caller upstream da rompere; modifiche solo additive sulla UI dashboard.

## Impact

**Loop architetturale CFO → DB → UI → orchestrator chiuso lato
referral fee per categoria**. Quando l'extractor (`io_/extract`) sarà
pronto e popolera `category_node`, l'attivazione completa avverrà
senza ulteriori modifiche. Fino ad allora, gli override sono persistiti
ma inerti (fail-safe documentato).

`gitnexus_detect_changes` segnala risk LOW additivo (un nuovo helper
+ una sostituzione del costruttore SessionInput in main()).

## Refs

- ADR: ADR-0016 (UI Streamlit), ADR-0018 (orchestrator), ADR-0014
  (mypy/ruff strict), ADR-0019 (test pattern).
- Predecessori: CHG-2026-04-30-051 (`list_category_referral_fees` +
  UI fetch helper); CHG-2026-04-30-053 (orchestrator overrides);
  CHG-2026-04-30-054 (DELETE + UI Reset).
- Successore atteso: caching `@st.cache_data` per la mappa overrides;
  attivazione completa con `io_/extract` (popola `category_node`);
  warning UI "override fantasma" se misalignment tenant ↔ listino.
- Commit: pending (backfill).
