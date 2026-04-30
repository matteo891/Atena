---
id: CHG-2026-04-30-040
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0016, ADR-0014, ADR-0013, ADR-0019
---

## What

Inaugura `src/talos/ui/` con dashboard Streamlit **mono-page MVP**:
sidebar parametri sessione + file upload CSV listino + chiamata
`run_session` + output metric/tabelle. **Primo strato visivo del CFO**.

Streamlit aggiunto come prima dipendenza UI (`streamlit>=1.40,<2`).
Refactor multi-page ADR-0016 compliant (`pages/`, `components/`,
`state.py`) e' scope di CHG successivi.

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | +`streamlit>=1.40.0,<2` (runtime) |
| `uv.lock` | modificato | +27 pacchetti transitive (streamlit core, pydeck, pyarrow, etc) |
| `src/talos/ui/__init__.py` | nuovo | Package marker; re-export `parse_locked_in`, `DEFAULT_BUDGET_EUR` |
| `src/talos/ui/dashboard.py` | nuovo | Entrypoint Streamlit + helper testabili (`parse_locked_in`, render functions, `main()`) |
| `tests/unit/test_ui_dashboard.py` | nuovo | 8 test (smoke + parse_locked_in: simple/empty/only_commas/strip/filter/single + re-export __init__) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `ui/__init__.py` e `ui/dashboard.py` |

Quality gate **verde**: ruff (all checks), ruff format (78 files OK),
mypy strict (38 source files, 0 issues), pytest **353 PASS** (345 + 8).

## Why

Pipeline e2e (CHG-039) e' funzionale ma "headless" — accessibile solo
via codice/test. Per il salto qualitativo verso "build USABILE dal CFO"
(memory `project_mvp_progress_estimate.md`) serve uno strato visivo:
input listino + slider parametri + bottone "Esegui" + output Cart/Panchina/Budget.

Streamlit ratificato in ADR-0016 (L14 Round 5: *"Avendo a che fare con
griglie di dati, tabelle di comparazione e slider parametrici, Streamlit
e' molto piu' solido e indicato rispetto a Gradio"*).

### Decisioni di design

1. **Mono-page invece di multi-page ADR-0016**: lo split in `pages/analisi.py`,
   `pages/storico.py`, `pages/panchina.py`, `pages/config.py` + `components/`
   + `state.py` e' scope di CHG successivo (refactor). MVP dimostrabile
   subito con un singolo file. Conformita' formale ad ADR-0016 sara'
   raggiunta progressivamente; il dashboard mono-page e' un sottoinsieme
   strict del layout completo.
2. **Helper `parse_locked_in` esposto e testabile**: le interazioni
   Streamlit non sono direttamente testabili senza `streamlit.testing.v1.AppTest`,
   quindi estraiamo la logica pura (parsing input testuale) in funzione
   pubblica isolata. Test snapshot + edge cases (empty, only commas, strip,
   filter empty).
3. **`run_session` chiamato direttamente**: niente caching in MVP (nessun
   `@st.cache_data`/`@st.cache_resource` per ora). Caching e' scope refactor
   ADR-0016 quando emergera' lentezza percepita (slider Velocity Target su
   listini >> 500 righe).
4. **`InsufficientBudgetError` + `ValueError` catturati e mostrati come
   `st.error`**: lo Streamlit non deve crashare per errori di input. Il
   caller (CFO) vede il messaggio e corregge a monte.
5. **Bottone "Esegui Sessione" obbligatorio**: l'esecuzione non si triggera
   automaticamente al caricamento del CSV. Anteprima 20 righe finche' non
   premi il bottone. Coerente con l'idempotency principle (ADR-0016
   *"bottone Forza Aggiornamento"*).
6. **Streamlit `>=1.40`**: per accesso al `st.testing.v1.AppTest` API
   (futuro test dedicato), `st.navigation` (futuro multi-page), e
   `column_config` (futuro tooltip). Versione conservativa.
7. **`# pragma: no cover - UI-only`** sulle branch di errore: il tracking
   coverage di Streamlit `st.error` richiede AppTest setup. Pragma chiaro
   per evitare coverage debt artificiale.
8. **`page_icon=":dart:"`** invece di emoji literal: la regola
   "Only use emojis if the user explicitly requests it" si applica al
   testo prodotto da me, non all'API Streamlit (che richiede emoji shortcode
   per `page_icon`). Compromesso conservativo: shortcode invece di emoji
   literal.

### Out-of-scope

- **Multi-page split ADR-0016**: refactor in `pages/` + `components/` +
  `state.py` + `st.navigation`.
- **Caching `@st.cache_data` / `@st.cache_resource`**: ADR-0016 sez.
  "Caching strategy".
- **RLS bootstrap di sessione DB**: ADR-0016 + ADR-0015 (`SET LOCAL
  talos.tenant_id = '1'` su connessione). Richiede prima la persistenza.
- **Test Streamlit reali** (`st.testing.v1.AppTest`): scope CHG dedicato
  (richiede setup fixture + asserzioni su widget tree).
- **Manual Override UI** (R-04 lock-in toggle dalla griglia): scope CHG
  successivo (`components/grid.py`).
- **Cell editor / sortable tables**: scope refactor ADR-0016.

## How

### `src/talos/ui/dashboard.py` (highlight)

```python
def main() -> None:
    st.set_page_config(page_title="TALOS — Cruscotto Sessione", layout="wide")
    st.title("TALOS — Scaler 500k")

    budget, vel_target, veto, lot = _render_sidebar()
    uploaded = st.file_uploader("Carica Listino (CSV)", type=["csv"])
    locked_in = parse_locked_in(st.text_input("ASIN Locked-in"))

    if uploaded is None:
        st.info("Carica un CSV per iniziare.")
        return

    listino = pd.read_csv(uploaded)
    if not st.button("Esegui Sessione"):
        st.dataframe(listino.head(20))
        return

    result = run_session(SessionInput(listino_raw=listino, budget=budget, ...))
    _render_metrics(result.cart.saturation, result.budget_t1)
    _render_cart_table([...])
    _render_panchina_table(result.panchina)
```

### Test plan (8)

1. `test_dashboard_module_imports` — smoke: import + callable + default value
2. `test_parse_locked_in_simple` — caso base
3. `test_parse_locked_in_empty_string` — vuoto
4. `test_parse_locked_in_only_commas` — solo virgole/spazi
5. `test_parse_locked_in_strip_whitespace` — whitespace handling
6. `test_parse_locked_in_filters_empty` — filter empty tokens
7. `test_parse_locked_in_single_asin` — un solo ASIN
8. `test_dashboard_re_exports_in_init` — `talos.ui` re-esporta i simboli

### Lancio app (manuale)

```bash
uv run streamlit run src/talos/ui/dashboard.py
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 78 files already formatted |
| Type | `uv run mypy src/` | ✅ 38 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ **353 PASS** (345 + 8) |
| Smoke runtime | `uv run streamlit run src/talos/ui/dashboard.py` | ⚠️ NON eseguito qui (richiede browser interattivo + listino CSV reale; Leader puo' lanciare manualmente) |

**Rischi residui:**
- **Smoke runtime non testato in questo CHG**: il modulo si importa
  (governance test passa) ma il rendering effettivo Streamlit non e'
  verificato. Mitigazione: il Leader puo' lanciare manualmente con un
  listino CSV di prova; oppure CHG futuro con `streamlit.testing.v1.AppTest`.
- **Pesantezza dipendenze transitive**: streamlit porta 27 pacchetti
  (pydeck, pyarrow, watchdog, ecc). Aumenta il footprint dell'install
  significativamente. Accettabile per MVP single-user; rivedibile
  post-MVP se si vuole separare il "core algoritmico" dall'UI in pacchetti
  distinti.
- **No caching**: rerun completo a ogni interazione widget. Su listino
  100-500 righe l'enrichment con apply puo' impiegare 1-3s, percepibile
  ma accettabile MVP. Errata corrige post-MVP per `@st.cache_data` con
  invalidazione su input change.

## Impact

**Salto qualitativo verso build CFO usabile**. Stato MVP:
- Pipeline algoritmica: ~95% (manca solo persistenza + extract reale)
- Percorso utente: ~30% (UI minimale + manca flusso autenticazione/storico)

`talos.orchestrator.run_session` ha il primo caller "umano" (CFO via
browser). Niente persistenza (la sessione si perde al refresh), niente
storico ordini, niente lock-in toggle dalla griglia — tutto questo e'
backlog per CHG futuri.

`gitnexus_detect_changes`: rilevera' i nuovi simboli al prossimo
`gitnexus analyze` post-merge.

## Refs

- ADR: ADR-0016 (Stack UI Streamlit + caching strategy), ADR-0014
  (mypy/ruff strict), ADR-0013 (struttura `ui/`), ADR-0019 (test pattern unit)
- Predecessore: CHG-2026-04-30-039 (orchestratore `run_session`)
- Vision verbatim: PROJECT-RAW.md L14 Round 5 (Streamlit ratificato)
- Successore atteso: refactor multi-page ADR-0016 (`pages/`, `components/`,
  `state.py`); persistenza `SessionResult` in DB; manual override grid;
  caching strategy
- Commit: `[pending]`
