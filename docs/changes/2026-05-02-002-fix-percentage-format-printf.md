---
id: CHG-2026-05-02-002
date: 2026-05-02
author: Claude (su autorizzazione Leader, modalità "macina" round 7 cont — fix urgente bug introdotto in CHG-2026-05-02-001)
status: Draft
commit: TBD
adr_ref: ADR-0016, ADR-0014, ADR-0019
---

## What

**Fix urgente bug rendering "SyntaxError" in rosso** sulle colonne `roi`,
`vgp_score`, `*_norm`, `referral_fee_*`, `fee_pct` nelle tabelle
`st.dataframe` post-CHG-2026-05-02-001.

Causa root: Streamlit 1.57 `NumberColumn.format` accetta **printf-style**
(sprintf-js) o preset stringa (`"plain"`/`"localized"`/`"percent"`/`"dollar"`/
`"euro"`/`"yen"`/`"accounting"`/`"compact"`/`"scientific"`/`"engineering"`/
`"bytes"`), **NON d3-format**. Il valore `"0.0%"` introdotto in CHG-001 è
parsato come SyntaxError dal renderer browser. Il preset `"percent"` mostra
il valore raw + `%` (es. `0.225` → `"0.225%"`), NON moltiplica ×100.

Fix corretto: pre-moltiplicare ×100 le colonne percentage in una **vista**
del DataFrame (no mutation dell'originale) + format printf-style `"%.1f%%"`
per il suffisso. Helper unificato `_percentage_view(df) -> (df_display, cfg)`
che ritorna l'originale senza copy se nessuna colonna percentage (no-op).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | `_pct_column_config` ora usa `format="%.1f%%"` (printf, era d3 `"0.0%"`). + helper nuovo `_percentage_view(df) -> (df_display: pd.DataFrame, column_config: dict)` con copy + `* 100.0` solo sulle colonne percentage. 11 callsite `st.dataframe` aggiornati a `df_view, cfg = _percentage_view(df); st.dataframe(df_view, ..., column_config=cfg)`. |
| `tests/unit/test_ui_dashboard.py` | modificato | + 3 test mock-only `_percentage_view`: moltiplica ×100 solo le colonne percentage; df senza colonne percentage ritorna originale (no copy); df originale non viene mutato (anche con colonne percentage presenti). |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **716 PASS** unit/gov/golden (era 713, +3 nuovi).
- **138 PASS** integration (invariato).
- **854 PASS** totali.

Detect_changes: 12 simboli touched, 2 file (dashboard + test),
**0 processi affetti**, **risk LOW**.

## Why

Bug introdotto in CHG-2026-05-02-001 e rilevato live in browser dal Leader
("in panchina e listino enriched roi e vpg sono flaggati in rosso e danno
syntaxerror") immediatamente al refresh post-CHG-001. Diagnostica empirica:
verificato Streamlit 1.57.0 documentation `NumberColumn(format=...)` accetta
solo printf-style + preset stringa, niente d3-format. Il preset `"percent"`
ha semantica diversa (no auto-x100).

Pattern di fix:
1. **Vista del DF**: `df.copy()` + `*= 100.0` sulle colonne percentage.
   Originale invariato (R-01 audit / debug data integrity).
2. **No-op se nessuna colonna percentage**: ritorno `df` originale senza
   copy. Tabelle storico sessioni / preview risoluzione invariate
   (zero overhead).
3. **Format printf `"%.1f%%"`**: 1 decimale + suffisso `%` letterale
   (sprintf-js parsa `%%` come escape). Streamlit 1.57 lo render
   correttamente.

### Decisioni di design

1. **Copy invece di view+SettingWithCopy**: `pandas` `df.copy()` è O(n)
   ma sicuro. Per dataframe di MVP (3-100 righe), overhead irrilevante.
   Pattern coerente con `df_display` esplicito.

2. **`.astype(float) * 100.0`**: garantisce float64 anche se la colonna
   originale è `Decimal` o `object` mixed. Defensive contro listini
   con tipi non standard.

3. **Helper `_percentage_view` ritorna tuple `(df, cfg)`**: 1 chiamata,
   2 valori correlati. Pattern pythonico (vs duplicare la logica
   "che colonne moltiplicare" sia in `_pct_column_config` che in
   `_percentage_view`).

4. **`_pct_column_config` mantiene la firma pre-CHG-001**: ancora
   esposto per i test, riutilizzato internamente da `_percentage_view`.
   Single source of truth resta `_PERCENTAGE_COLUMNS` frozenset.

5. **No-op su df senza colonne percentage = `return df, {}`**: identità
   stretta (`df_view is df`). Test sentinel verifica.

6. **3 test sentinel**: scaling correctness, no-op safety, no-mutation
   guarantee. Coprono il contratto pubblico del helper.

7. **Bug NON regredisce su test esistenti**: i 4 test `_pct_column_config`
   continuano a passare (signature/keys invariate, solo il `format`
   value dentro NumberColumn è cambiato — non testato direttamente).

8. **Streamlit version pinned `>=1.40` (pyproject)**: il fix funziona
   da 1.40+. Nessuna regressione ipotetica su versioni future:
   printf-style è API stabile.

### Out-of-scope

- **Refactor unico helper sostituendo `_pct_column_config`**: scope
  CHG futuro. Oggi entrambi convivono per compatibilità test.
- **Cambio di approccio a preset Streamlit `"percent"`**: bocciato,
  semantica `(value × 100)` non corrispondente.
- **Test integration con `streamlit.testing.v1.AppTest`**: richiede
  setup dedicato, scope CHG futuro.

## How

### `dashboard.py` (highlight diff)

```diff
 def _pct_column_config(columns) -> dict[str, Any]:
-    return {col: st.column_config.NumberColumn(format="0.0%")
+    return {col: st.column_config.NumberColumn(format="%.1f%%")
             for col in columns if col in _PERCENTAGE_COLUMNS}


+def _percentage_view(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
+    pct_cols = [c for c in df.columns if c in _PERCENTAGE_COLUMNS]
+    if not pct_cols:
+        return df, {}
+    df_display = df.copy()
+    for col in pct_cols:
+        df_display[col] = df_display[col].astype(float) * 100.0
+    return df_display, _pct_column_config(pct_cols)


 # 11 callsite uniformi:
-st.dataframe(df, column_config=_pct_column_config(df.columns))
+df_view, cfg = _percentage_view(df)
+st.dataframe(df_view, column_config=cfg)
```

### Test sentinella (highlight)

```python
def test_percentage_view_multiplies_by_100_only_pct_columns():
    df = pd.DataFrame({
        "asin": ["B0AAA"],
        "cost_eur": [100.0],
        "roi": [0.225],
        "vgp_score": [0.85],
    })
    df_view, cfg = _percentage_view(df)
    assert df_view["cost_eur"].tolist() == [100.0]  # invariato
    assert df_view["roi"].tolist() == [22.5]  # x100
    assert df_view["vgp_score"].tolist() == [85.0]
    assert set(cfg.keys()) == {"roi", "vgp_score"}


def test_percentage_view_does_not_mutate_input():
    df = pd.DataFrame({"roi": [0.225]})
    df_view, _ = _percentage_view(df)
    assert df["roi"].tolist() == [0.225]  # originale invariato
    assert df_view["roi"].tolist() == [22.5]
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 138 files already formatted |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Dashboard dedicated | `uv run pytest tests/unit/test_ui_dashboard.py -q` | **17 PASS** (era 14, +3 nuovi) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **716 PASS** (era 713, +3) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (`_percentage_view` nuovo simbolo) | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 12 simboli / 2 file, **0 processi affetti**, **risk LOW** |
| **Validazione browser** | Streamlit live: refresh dashboard → ROI/VGP visibili come `XX.X%` senza errori rossi | scope post-commit (Leader) |

**Rischi residui:**

- **Copy DataFrame**: O(n) per ogni `st.dataframe` con colonne percentage.
  Per MVP CFO (10-1000 righe) overhead irrilevante. Per scale futuri
  (>10k righe) considerare lazy view (scope CHG futuro).
- **`.astype(float)` può fallire** su tipi totalmente non numerici:
  improbabile (le colonne `_PERCENTAGE_COLUMNS` sono float64 dalla
  pipeline, verificato empiricamente su `enriched_df.dtypes`).
- **Test sentinel verifica solo le keys + scaling**: non testa il format
  string interno `NumberColumn` (attributo privato Streamlit non
  pubblico). Validazione live in browser obbligatoria post-merge.
- **Streamlit minor version upgrade**: se 1.58+ cambia il default
  `NumberColumn` parser (improbabile ma possibile), il format string
  potrebbe richiedere adattamento. Locked-down dependency in pyproject.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/dashboard.py`,
  `tests/unit/` ✓ (aree ADR-0013 + ADR-0016).
- **ADR-0016 (UI Streamlit)**: `column_config` è feature canonica.
  Format string allineato a Streamlit docs ufficiali (sprintf-js).
- **ADR-0014 (mypy/ruff strict)**: 0 issues.
- **ADR-0019 (test strategy)**: unit puri ✓ + helper testabile.
- **R-01 NO SILENT DROPS** (ADR-0021): nessuna data loss; copia non
  altera l'originale. Audit trail valore raw preservato.
- **Backward compat**: signature `_pct_column_config` invariata. I 4
  test esistenti continuano a passare. `_percentage_view` è nuovo
  simbolo public-style (nessun caller esterno, scoping interno
  dashboard).
- **Sicurezza**: zero secrets/PII; no nuove deps; no migration DB.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 12 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +3**: 716 unit/gov/golden + 138 integration = **854
  PASS**.
- **🎯 UX percentuali Path B' MVP CFO funzionante**: ROI/VGP
  finalmente leggibili come `22.5%`. Pipeline interna invariata
  (frazione decimale ovunque, blast radius zero su formule/test/DB).
- **Code health**: -1 bug rendering immediato; +1 helper più
  ergonomico (`_percentage_view` 1-call, 2-return); +1 test no-mutation
  guarantee.

## Refs

- ADR: ADR-0016 (UI Streamlit), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test strategy).
- Predecessore immediato:
  - CHG-2026-05-02-001 (UX percentuali Path B' — introduzione del
    bug d3-format `"0.0%"` non supportato da Streamlit 1.57).
- Bug rilevato live in browser dal Leader 2026-05-02 round 7 cont:
  "in panchina e listino enriched roi e vpg sono flaggati in rosso
  e danno syntaxerror".
- Causa root verificata empiricamente: Streamlit 1.57.0 docs
  `NumberColumn.format` accetta solo printf-style (sprintf-js) +
  preset stringa, no d3-format.
- Successore atteso: nessuno specifico. Possibili rotte CHG-help-text
  CSV ("prezzo = costo fornitore") oppure micro-CHG `_pct_column_config`
  cleanup (rimuovere helper duplicato in favore solo di
  `_percentage_view`).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: TBD (backfill hash post-commit).
