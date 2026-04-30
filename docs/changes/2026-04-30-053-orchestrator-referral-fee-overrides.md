---
id: CHG-2026-04-30-053
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Committed
commit: 1178389
adr_ref: ADR-0018, ADR-0014, ADR-0019
---

## What

Integra il lookup per categoria di `Referral_Fee` (CHG-051) nel motore
`run_session`. `SessionInput` accetta un kwarg opzionale
`referral_fee_overrides: dict[str, float] | None` (mappa
`category_node → fee_pct`); l'orchestratore risolve la fee per ogni
riga via `_resolve_referral_fee` e usa il valore risolto in
`cash_inflow_eur`.

L12 PROJECT-RAW Round 5 — *"Referral_Fee: lookup categoria + override
manuale configurabile"* — chiusa anche lato pipeline (oltre che lato
configurazione persistente in CHG-050/051). Un eventuale orchestratore
chiamato dalla UI può ora caricare la mappa via
`list_category_referral_fees(db, tenant_id)` (CHG-051) e passarla a
`SessionInput`. Lookup hierarchy:

1. `overrides[row["category_node"]]` se overrides non vuoto, colonna
   presente, categoria in mappa.
2. fallback `row["referral_fee_pct"]` (raw del listino — comportamento
   pre-CHG).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/orchestrator.py` | modificato | + `CATEGORY_NODE_COLUMN = "category_node"` costante; + `_resolve_referral_fee(row, overrides)`; `SessionInput` esteso con `referral_fee_overrides: dict[str, float] \| None = None`; `_enrich_listino` accetta `referral_fee_overrides`, aggiunge colonna `referral_fee_resolved` (sempre, anche senza overrides), usa `referral_fee_resolved` in `cash_inflow_eur` invece di `referral_fee_pct`; `run_session` propaga `inp.referral_fee_overrides` a `_enrich_listino`. |
| `tests/unit/test_orchestrator_referral_fee_override.py` | nuovo | 6 test (None overrides → raw; no category col → raw; category in mappa → override; category fuori mappa → raw; end-to-end cash_inflow modificato; legacy listino; overrides vuoto = None). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **467 PASS**
(387 unit/governance/golden + 80 integration).

## Why

CHG-051 ha aperto la primitiva di persistenza `Referral_Fee` per
categoria, ma il motore di sessione **non la consumava**. Il loop
"CFO modifica fee per categoria → run_session usa fee aggiornata"
non era chiuso senza preprocessing manuale del listino lato caller.

Senza questo CHG:
- Il CFO doveva ri-emettere il `referral_fee_pct` corretto in ogni
  riga del listino raw prima di chiamare `run_session`.
- L'extractor futuro (`io_/extract`, ADR-0017) avrebbe dovuto
  bake-in la fee per categoria al momento dell'estrazione, perdendo
  la possibilità di override runtime.
- Persistenza e pipeline restavano disaccoppiate.

### Decisioni di design

1. **Kwarg opzionale, default `None`**: zero rotture per i caller
   esistenti (test, UI dashboard, golden). I listini "legacy" senza
   colonna `category_node` continuano a funzionare identici.

2. **`referral_fee_resolved` colonna SEMPRE presente** (anche senza
   overrides): l'`enriched_df` finale ha la colonna come audit trail.
   Senza overrides, è identica al `referral_fee_pct`. Pattern consente
   ai consumer downstream di sapere "che fee è stata usata davvero"
   senza ricalcolare.

3. **Lookup hierarchy NULL-safe**: `cat is not None and cat in overrides`.
   Categorie `NaN`/`None` → fallback raw. Pattern coerente con il
   resto del codice che tratta gracefully colonne opzionali.

4. **`overrides={}` (dict vuoto) si comporta come `None`**: la
   condizione `if overrides` valuta `{}` come falsy. Volontario:
   un caller può "resettare" gli override passando un dict vuoto e
   ottenere il comportamento legacy.

5. **No nuova colonna richiesta**: `category_node` resta opzionale.
   L'extractor (`io_/extract`) la emetterà popolata in futuro;
   per ora i listini sintetici la possono includere ad-hoc per test.

6. **No UI integration in questo CHG**: la UI continua a passare
   `SessionInput` senza `referral_fee_overrides`. Integrazione UI
   (caricare overrides da DB + passarli a `run_session`) è scope
   CHG futuro post `io_/extract` (quando l'extractor emetterà
   `category_node`).

### Out-of-scope

- **Lookup hierarchy estesa** (ASIN-specific override > category > raw):
  scope futuro se PROJECT-RAW lo richiederà. Per ora solo category.
- **UI integration**: il caller `dashboard.py` non passa overrides
  ancora. Scope post `io_/extract`.
- **Vettorializzazione**: `_resolve_referral_fee` resta `apply` row-wise.
  Vettoriale via `pd.Series.map(overrides).fillna(row["referral_fee_pct"])`
  è errata corrige post-MVP se profiling lo impone (vincolo 8.1
  ADR-0018).
- **Logging telemetry "override_applied"**: gli override sono silent.
  Aggiungere evento `vgp.referral_fee_override_applied` è errata
  corrige al catalogo ADR-0021.

## How

### `_resolve_referral_fee` (highlight)

```python
CATEGORY_NODE_COLUMN: Final[str] = "category_node"

def _resolve_referral_fee(row, overrides):
    if overrides and CATEGORY_NODE_COLUMN in row.index:
        cat = row[CATEGORY_NODE_COLUMN]
        if cat is not None and cat in overrides:
            return float(overrides[cat])
    return float(row["referral_fee_pct"])
```

### `_enrich_listino` (highlight)

```python
def _enrich_listino(listino_raw, *, velocity_target_days, lot_size,
                    referral_fee_overrides=None):
    out = listino_raw.copy()
    out["fee_fba_eur"] = out["buy_box_eur"].apply(fee_fba_manual)
    out["referral_fee_resolved"] = out.apply(
        lambda r: _resolve_referral_fee(r, referral_fee_overrides),
        axis=1,
    )
    out["cash_inflow_eur"] = out.apply(
        lambda r: cash_inflow_eur(
            buy_box_eur=float(r["buy_box_eur"]),
            fee_fba_eur=float(r["fee_fba_eur"]),
            referral_fee_rate=float(r["referral_fee_resolved"]),  # <- resolved, non raw
        ),
        axis=1,
    )
    # ... resto invariato
```

### Test plan (6 unit)

1. `test_resolve_referral_fee_no_overrides_uses_raw`
2. `test_resolve_referral_fee_no_category_col_uses_raw`
3. `test_resolve_referral_fee_category_in_map_uses_override`
4. `test_resolve_referral_fee_category_not_in_map_fallback_raw`
5. `test_run_session_applies_overrides_to_cash_inflow` — Books
   (fee scontata) → cash_inflow > raw; Electronics (fee maggiorata)
   → cash_inflow < raw
6. `test_run_session_legacy_listino_without_category_node` — fallback
   raw, no break
7. `test_run_session_empty_overrides_dict_uses_raw` — `{}` ≡ `None`

(7 test totali — il CHG-053 ne ha 7, non 6 come scritto sopra; refuso
nel summary del What. Letterale.)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 95 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **387 PASS** (380 + 7) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **80 PASS** (invariato) |

**Rischi residui:**
- **Behavioral change in `_enrich_listino`**: la colonna `cash_inflow_eur`
  ora dipende da `referral_fee_resolved` (era `referral_fee_pct`).
  Senza overrides, `referral_fee_resolved == referral_fee_pct` per
  costruzione, quindi i golden test passano invariati. Confermato dai
  380 test pre-esistenti tutti verdi.
- **`overrides={}` (dict vuoto)** trattato come `None`: documentato.
  Caller che vuole semantica "esplicitamente nessun override" può
  passare `{}` o `None` indifferentemente.
- **No persistenza di `referral_fee_resolved` nel `vgp_results`**: la
  colonna è in `enriched_df` ma non in DB. CHG futuro `save_session_result`
  potrebbe persisterla se serve audit storico.

## Test di Conformità

- **Path codice applicativo:** `src/talos/orchestrator.py` ✓ (top-level
  consentito da decisione Leader CHG-039 opzione A).
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `_resolve_referral_fee`
  mappa ad ADR-0018 (orchestrator) — coerente con `_enrich_listino`.
- **Backward compat:** signature `SessionInput`/`_enrich_listino`
  estesa con kwarg opzionale, default = comportamento pre-CHG.
- **Impact analysis pre-edit:** risk LOW (1 caller diretto:
  `run_session`); 0 processi affected.

## Impact

**L12 chiusa anche lato pipeline**. Il flusso completo è:

```
[CFO modifica fee per categoria]
  ↓ (UI form)
[set_config_override_numeric — CHG-050]
  ↓
[DB config_overrides UPSERT]
  ↓ (al run_session successivo)
[list_category_referral_fees → dict — CHG-051]
  ↓
[SessionInput.referral_fee_overrides — CHG-053]
  ↓
[_resolve_referral_fee → cash_inflow_eur]
```

Manca solo l'aggancio UI (passare `overrides` ricavati al `run_session`),
ma quello è scope post `io_/extract` (l'extractor è il consumatore reale
di `category_node`).

## Refs

- ADR: ADR-0018 (orchestrator + R-01..R-09), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test pattern).
- Predecessori: CHG-2026-04-30-039 (orchestrator end-to-end),
  CHG-2026-04-30-050 (config_repository numeric),
  CHG-2026-04-30-051 (`list_category_referral_fees`).
- Vision verbatim: PROJECT-RAW.md L12 Round 5 (Referral_Fee
  configurabile per categoria).
- Successore atteso: UI integration (`dashboard.py` carica overrides +
  passa a `run_session`) post `io_/extract`; lookup hierarchy
  ASIN-level; vettorializzazione.
- Commit: `1178389`.
