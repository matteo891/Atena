---
id: CHG-2026-05-02-001
date: 2026-05-02
author: Claude (su autorizzazione Leader, modalità "macina" round 7 — UX percentuali Path B' MVP CFO)
status: Draft
commit: 30649ef
adr_ref: ADR-0016, ADR-0014, ADR-0019, ADR-0018
---

## What

**Display percentuale (1 decimale) per tutte le colonne "frazione
decimale"** in `st.dataframe` + **input sidebar in % (8.0)** invece
di frazione (0.08) per `veto_threshold` e `referral_fee` form
categoria. La pipeline interna mantiene frazione (zero blast radius
su formule, test, DB, persistence).

Bug UX rilevato live dal Leader 2026-05-02 round 7: la dashboard
mostrava `roi=0.22` e `vgp_score=0.85` come decimali, ambigui per
il CFO ("è 22% o 0.22%?"). Decisione Leader ratificata: format
1 decimale (`"22.5%"`), conversione anche per il `veto_threshold`
sidebar, scope esteso ai `*_norm` intermedi.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | + costante `_PERCENTAGE_COLUMNS: frozenset[str]` (9 voci: `roi`, `vgp_score`, `vgp_score_raw`, `roi_norm`, `velocity_norm`, `cash_profit_norm`, `referral_fee_pct`, `referral_fee_resolved`, `fee_pct`). + helper `_pct_column_config(columns) -> dict[str, Any]` (Streamlit `NumberColumn(format="0.0%")` d3-format auto-x100). 11 chiamate `st.dataframe` aggiornate con `column_config=_pct_column_config(df.columns)`. Sidebar `veto_threshold`: slider in % (1.0-50.0, step 0.5, format `%.1f%%`), conversione `÷100` per la pipeline. Sidebar `referral_fee` form categoria: input in % (0-100, step 0.1, default 8.0), conversione `÷100` prima di `try_persist_category_referral_fee`. Reset al default mostra `8.0%` (era `0.08`). |
| `tests/unit/test_ui_dashboard.py` | modificato | + 4 test mock-only `_pct_column_config`: known columns mapped, no-op vuoto, intermediate `*_norm` inclusi, `confidence_pct` escluso (è già 0-100, badge stringa). |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **713 PASS** unit/gov/golden (era 709, +4 nuovi).
- **138 PASS** integration (invariato — nessuna toccata DB / formula).
- **851 PASS** totali.

Detect_changes: 24 simboli touched, 2 file (dashboard + test),
**0 processi affetti**, **risk LOW**.

## Why

La pipeline interna è correttamente in frazione decimale ovunque
(documentato in `vgp/score.py:77`: `roi` "frazione decimale, es.
0.15"; output `vgp_score ∈ [0, 1]`; `cash_inflow_eur` valida
`referral_fee_rate ∈ [0, 1]`). Il CFO però vede i raw float in
`st.dataframe` senza format e nel `number_input` sidebar: questo
crea ambiguità ("ROI 0.22" è 22% o 0.22%?).

Streamlit `NumberColumn(format="0.0%")` (sintassi d3-format)
applica automaticamente la moltiplicazione ×100 e aggiunge il
suffisso `%` solo nel display, lasciando il valore raw nel
DataFrame intatto. Pattern UI puro: zero blast radius su pipeline
/ test formule / persistence / migration.

Per la sidebar `veto_threshold`, la scelta è simmetrica: input in %
visivo (8.0 default), conversione `÷100` prima di passare alla
pipeline (`compute_vgp_score(..., veto_roi_threshold=0.08)`).
Stesso pattern per il form referral fee per categoria.

### Decisioni di design

1. **Format `"0.0%"` (d3, auto-x100) vs `"%.1f%%"` (Python, raw)**:
   d3 vince. Format `"0.0%"` mostra `22.5%` da `0.225` con 0 codice
   di pre-processing. `"%.1f%%"` mostrerebbe `0.2%` (sbagliato).

2. **`_PERCENTAGE_COLUMNS` come `frozenset` module-level**: lookup
   O(1), immutabile, single source of truth. Aggiunte future
   (`fee_fba_pct`, `velocity_pct` ecc.) sono one-line additions.

3. **Helper `_pct_column_config(columns)` accetta qualsiasi
   `Iterable[str]`**: `pd.Index | list[str] | tuple[str, ...]`.
   Sito di chiamata: `column_config=_pct_column_config(df.columns)`.
   Pattern uniforme su tutte le 11 chiamate `st.dataframe`.

4. **Return type `dict[str, Any]`**: Streamlit espone
   `st.column_config.NumberColumn(...)` come factory function ma
   non un public type alias per i column config values. `Any`
   evita import da `streamlit.elements.lib.column_types` (private).

5. **Scope esteso ai `*_norm` intermedi**: decisione Leader
   ratificata 2026-05-02. `roi_norm`, `velocity_norm`,
   `cash_profit_norm`, `vgp_score_raw` visibili nell'expander
   "Listino completo enriched (audit/debug)" — utili per il
   debugger, devono essere leggibili come %. Tutti in [0, 1] post
   min-max normalize.

6. **`confidence_pct` ESCLUSO**: è già 0-100 dalla
   `compute_confidence` (CHG-016) ed è renderizzato come badge
   stringa via `format_confidence_badge` (CHG-018), non passa
   per `column_config`. Test sentinel
   `test_pct_column_config_excludes_confidence_pct` blinda il
   contratto.

7. **Sidebar `veto_threshold` slider in %**: range `1.0-50.0`
   step `0.5`, default da DB convertito `× 100`. Conversion
   `÷ 100` prima di chiamare `try_persist_veto_roi_threshold`
   (DB resta in frazione, retro-compat 100%). Reset message
   aggiornato `f"{DEFAULT_ROI_VETO_THRESHOLD * 100:.1f}%"`.

8. **Form `referral_fee` per categoria**: input in % (0-100,
   step 0.1, default 8.0), conversion `÷ 100`. Nessuna modifica
   a `try_persist_category_referral_fee` (accetta sempre frazione).

9. **Test puramente sui keys del dict**: il VALUE è un'istanza
   `NumberColumn` con attributi privati Streamlit non
   ispezionabili in modo stabile. Verifica le KEYS = sufficiente
   per blindare il contratto del helper.

10. **Helper applicato anche a tabelle senza colonne percentage**
    (es. storico sessioni, preview risoluzione): `dict` vuoto
    `column_config={}` è no-op. Pattern uniforme = future-proof
    se le tabelle aggiungono colonne percentage.

### Out-of-scope

- **`saturation` metric** (`f"{saturation:.1%}"`): già formattato
  come `%` da Python f-string (CHG-040 originale). Invariato.
- **`confidence_pct`**: già 0-100, badge stringa. Invariato.
- **Custom format float-only colonne EUR** (`buy_box_eur`,
  `cost_eur`, `cost_total`): scope CHG futuro (formato `€`).
- **Migration valori DB**: nessun valore DB cambia (la frazione
  resta canonica a livello persistence).
- **Internazionalizzazione separator decimale**: scope CHG futuro
  (lingua CFO it_IT vs en_US).

## How

### `dashboard.py` (highlight)

```python
_PERCENTAGE_COLUMNS: frozenset[str] = frozenset({
    "roi", "vgp_score", "vgp_score_raw",
    "roi_norm", "velocity_norm", "cash_profit_norm",
    "referral_fee_pct", "referral_fee_resolved",
    "fee_pct",
})

def _pct_column_config(columns) -> dict[str, Any]:
    return {
        col: st.column_config.NumberColumn(format="0.0%")
        for col in columns
        if col in _PERCENTAGE_COLUMNS
    }

# 11 callsite uniformi:
st.dataframe(
    df,
    use_container_width=True,
    column_config=_pct_column_config(df.columns),
)
```

### Sidebar `veto_threshold` (highlight diff)

```diff
-veto_threshold = st.sidebar.slider(
-    "Veto ROI Minimo",
-    min_value=0.01, max_value=0.50, value=persisted, step=0.01,
-    format="%.2f",
-    help="...default 8%.",
-)
+veto_threshold_pct = st.sidebar.slider(
+    "Veto ROI Minimo (%)",
+    min_value=1.0, max_value=50.0, value=persisted * 100.0, step=0.5,
+    format="%.1f%%",
+    help="...default 8.0%.",
+)
+veto_threshold = veto_threshold_pct / 100.0
```

### Test sentinella (highlight)

```python
def test_pct_column_config_includes_norm_intermediates():
    cols = ["roi_norm", "velocity_norm", "cash_profit_norm", "vgp_score_raw"]
    cfg = _pct_column_config(cols)
    assert set(cfg.keys()) == {"roi_norm", "velocity_norm",
                                "cash_profit_norm", "vgp_score_raw"}

def test_pct_column_config_excludes_confidence_pct():
    cfg = _pct_column_config(["confidence_pct", "asin"])
    assert "confidence_pct" not in cfg
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed (1 RUF002 unicode auto-fixed) |
| Format | `uv run ruff format --check src/ tests/` | 138 files already formatted |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Dashboard dedicated | `uv run pytest tests/unit/test_ui_dashboard.py -q` | **14 PASS** (era 10, +4 nuovi) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **713 PASS** (era 709, +4) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (`_pct_column_config` nuovo simbolo) | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 24 simboli / 2 file, **0 processi affetti**, **risk LOW** |
| **Validazione browser** | Streamlit live: refresh dashboard → ROI/VGP visibili come `XX.X%` | scope post-commit (Leader) |

**Rischi residui:**

- **Nessuna validazione automatica del rendering Streamlit**:
  `streamlit.testing.v1.AppTest` non in scope CHG-040. Validazione
  manuale browser-side (Leader). Il test sentinel `_pct_column_config`
  copre la mappatura colonne ↔ format.
- **Sidebar slider step 0.5%**: default 8.0% va bene (multiple of
  step). Persisted threshold `0.083` → `8.3%` viene quantizzato a
  `8.5%` o `8.0%` dal slider (Streamlit snap-to-step). Trade-off
  accettato: granularità 0.5% sufficiente per CFO (vs precision DB
  intera).
- **`*_norm` colonne intermediate** sono in [0, 1] dopo min-max
  normalize, sempre. Non possono essere `> 1` o `< 0`. Format
  `"0.0%"` rende sempre valori `0.0%-100.0%` corretti.
- **Aggiunte future di colonne percentage**: 1-line edit in
  `_PERCENTAGE_COLUMNS` (frozenset). Pattern documentato.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/dashboard.py`,
  `tests/unit/` ✓ (aree ADR-0013 + ADR-0016).
- **ADR-0016 (UI Streamlit)**: `column_config` è feature
  `st.dataframe` introdotta nella versione `streamlit>=1.23` (in
  uso `>=1.40`). Pattern UI canonico Streamlit.
- **ADR-0018 (algoritmo VGP)**: pipeline `compute_vgp_score` /
  `cash_inflow_eur` invariate. Solo display.
- **ADR-0014 (mypy/ruff strict)**: 0 issues.
- **ADR-0019 (test strategy)**: unit puri ✓ + helper testabile in
  isolamento.
- **Backward compat 100%**: nessun caller esterno consuma
  `_pct_column_config` (private helper). Sidebar slider/input
  conversion è internal al render. DB persistence invariata
  (frazione).
- **Sicurezza**: zero secrets/PII; no nuove deps; no migration DB.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 24 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +4**: 713 unit/gov/golden + 138 integration = **851
  PASS**.
- **🎯 UX MVP CFO Path B' chiusa per percentuali**: ROI/VGP ora
  leggibili come "22.5%" invece di "0.225". Sidebar coerente
  ("8.0%" invece di "0.08"). Form referral fee categoria
  coerente.
- **Code health**: -1 ambiguità UX, +1 helper isolato testabile,
  +1 frozenset single source of truth.
- **Sblocca**: smoke browser CFO-side completo (TEST-DEBT-003,
  ora con UX percentuali corretta). Il CFO può leggere i KPI
  senza chiedere "è 22% o 0.22%?".

## Refs

- ADR: ADR-0016 (UI Streamlit), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test strategy), ADR-0018 (algoritmo VGP, pipeline
  invariata).
- Predecessori:
  - CHG-2026-04-30-040 (UI Streamlit dashboard MVP, primo render
    `st.dataframe` raw).
  - CHG-2026-04-30-035 (`compute_vgp_score` formula composita,
    pipeline canonica frazione).
  - CHG-2026-05-01-038 (fix unit drift `referral_fee_pct` —
    semantica frazione blindata da test sentinel).
  - CHG-2026-05-01-039 (cache hit fa fetch buybox live —
    sblocca pipeline VGP funzionante per testing UX percentuali).
- Bug UX rilevato live in browser dal Leader 2026-05-02 round 7
  (post CHG-039 quando finalmente la pipeline alloca davvero):
  "io noto che i numeri come roi e vgp che sono percentuali
  vengono espressi in decimale".
- Decisioni Leader 2026-05-02 round 7 ratificate:
  - "decimale" → format `"0.0%"` (1 decimale).
  - "anche veto" → sidebar slider in % con conversion ÷100.
  - "anche i norm intermedi" → scope esteso a `roi_norm`,
    `velocity_norm`, `cash_profit_norm`, `vgp_score_raw`.
- Successore atteso: nessuno specifico. Possibili rotte:
  CHG-041 candidato (formato `€` per colonne EUR), CHG-help
  text "prezzo = costo fornitore" (bug semantico CSV pre-CHG-039).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: `30649ef`.
