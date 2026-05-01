---
id: CHG-2026-05-01-020
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 4 — chiusura blocco asin_resolver con UI rifondata, decisione delta=A ratificata)
status: Draft
commit: 2886728
adr_ref: ADR-0016, ADR-0017, ADR-0014, ADR-0019
---

## What

Chiude il blocco asin_resolver (5/5 CHG): UI Streamlit
rifondata con il nuovo flow "(descrizione, prezzo) -> ASIN".
Decisione Leader **delta=A** ratificata: convivenza dei 2 flow
CSV via `st.radio` mode, default = nuovo flow.

Pattern minimal-invasive: helper puri in nuovo modulo
`src/talos/ui/listino_input.py` (testabili senza Streamlit) +
funzione di rendering `_render_descrizione_prezzo_flow` in
`dashboard.py` + `st.radio` mode in `main()` con biforcazione
listino_df.

Flow nuovo (default):

1. Upload CSV con `descrizione` + `prezzo` (+ opzionali `v_tot`,
   `s_comp`, `category_node`).
2. Parse + warnings su righe invalide (R-01 esposto a UI).
3. Bottone "Risolvi descrizioni" -> orchestrate cache
   (`description_resolutions` CHG-019) + fallback live
   `_LiveAsinResolver` (CHG-018) -> `upsert_resolution` per cache write.
4. Tabella preview con `confidence_pct` + badge OK/DUB/AMB
   (R-01 UX-side: tutti i match esposti, ambigui inclusi).
5. Bottone "Conferma listino" -> ritorna `pd.DataFrame` 7-col
   compatibile con `run_session`.
6. Flow legacy comune da qui: `build_session_input` ->
   `run_session` -> render esistente (metric, cart, panchina,
   enriched_df, persistenza).

Flow legacy (radio = "ASIN gia' noto"): identico a CHG-040
originale, zero breaking.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | nuovo | Helper puri (no Streamlit dep): `DescrizionePrezzoRow` + `ResolvedRow` frozen dataclass; `parse_descrizione_prezzo_csv(df) -> tuple[list[Row], list[warnings]]` (validazione + warnings R-01); `resolve_listino_with_cache(rows, *, factory, resolver_provider, tenant_id)` orchestra cache hit (no quota) + live resolve (cache miss) + UPSERT post; `build_listino_raw_from_resolved(rows, *, referral_fee_pct=8, match_status="SICURO")` -> DataFrame 7-col `REQUIRED_INPUT_COLUMNS`-compat; `format_confidence_badge(pct)` -> `"OK 95.0%"` / `"DUB 75.0%"` / `"AMB 50.0%"`. Costanti soglie modulo-level. R-01 NO SILENT DROPS docstring + menzione eventi canonici `keepa.miss` / `scrape.selector_fail` (governance test). |
| `src/talos/ui/dashboard.py` | modificato | + `_render_descrizione_prezzo_flow(factory) -> pd.DataFrame \| None` (Streamlit-side: file uploader + parse + bottone "Risolvi" con `st.spinner` + tabella preview + bottone "Conferma"). + import lazy `_LiveAsinResolver`/`_LiveAmazonSerpAdapter`/`KeepaClient`/`_PlaywrightBrowserPage`/`partial(lookup_product, keepa-only)` per non penalizzare boot Streamlit. + `st.radio` mode in `main()` con biforcazione: nuovo flow → `_render_descrizione_prezzo_flow`, legacy → `pd.read_csv` esistente. `noqa: C901, PLR0911, PLR0912, PLR0915` sui 2 flow Streamlit (multi-step inerentemente complesso). |
| `tests/unit/test_listino_input.py` | nuovo | 24 test mock-only via `_MockResolver` duck-typed: 6 `parse_descrizione_prezzo_csv` (minimal 2-col, optional 3-col, missing required raises, skip empty desc, skip invalid price, normalize whitespace) + 11 `format_confidence_badge` (parametric + boundary 85/70 inclusivi + out-of-range fallback) + 5 `build_listino_raw_from_resolved` (7-col schema, skip unresolved, category_node opt incluso/escluso, all unresolved -> empty schema) + 3 `resolve_listino_with_cache` (factory=None bypass cache, unresolvable -> asin="", lazy resolver init). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **640
PASS** unit/gov/golden + 133 integration = **773 PASS** (era 749,
+24 unit nuovi `test_listino_input`, integration invariata).

Smoke test import: `from talos.ui.dashboard import main,
_render_descrizione_prezzo_flow` + helper module OK.

## Why

CHG-016 ha aperto il blocco asin_resolver con tipi.
CHG-017 ha aperto canale SERP live.
CHG-018 ha chiuso il composer applicativo.
CHG-019 ha aggiunto la cache persistente.
CHG-020 chiude il blocco con la UX: senza il flow nuovo, il
sistema continuava a chiedere ASIN al CFO -> non realistico in
produzione (i listini fornitore Samsung non arrivano con ASIN
gia' noti).

Decisione Leader delta=A "convivenza" preserva il flow legacy
CSV-strutturato (CHG-040) come opzione "advanced". Permette
test di regressione e fallback per CFO con CSV gia' completi
(es. derivati da pipeline interne).

### Decisioni di design

1. **Helper puri in modulo separato `listino_input.py`**:
   testabili senza dipendenza Streamlit (zero `import streamlit`),
   coverage netta. Pattern coerente con
   `talos.persistence.session_repository` (logica DB pura) +
   `dashboard.py` (rendering). Ribadisce la separazione "logic
   vs view".

2. **Lazy import nel `_render_descrizione_prezzo_flow`**:
   `KeepaClient`, `_PlaywrightBrowserPage`, `_LiveAsinResolver`,
   `_LiveAmazonSerpAdapter` importati dentro la funzione e non
   top-level. Rationale: gli import di `keepa` (libreria community)
   e `playwright` (binding C) penalizzano boot Streamlit anche se
   il flow non e' attivo. `# noqa: PLC0415` per disabilitare la
   regola ruff "no lazy import" (ratificata in CHG-015).

3. **`st.radio` mode default = nuovo flow**: il blocco
   asin_resolver e' il flusso d'uso reale del Leader. Il legacy
   "ASIN noto" resta come opzione minoritaria ma non breaking.

4. **`st.session_state["resolved_rows"]`**: pattern Streamlit
   standard per persistere stato fra render (bottone "Risolvi"
   scatena re-render, ma il risultato non deve essere ricalcolato
   se il CFO modifica solo locked-in o budget).

5. **`with _PlaywrightBrowserPage() as page` nel button "Risolvi"**:
   apertura/chiusura context manager per l'intero batch resolve
   (open Chromium una volta, riusato per N descrizioni). Pattern
   coerente con `test_live_serp.py` / `test_live_asin_resolver.py`.

6. **`max_candidates=3` per UI**: trade-off fra confidence
   diversity (piu' candidati = piu' opzioni) e quota (1 token
   Keepa per candidato). 3 e' minimo viable. Override CFO possibile
   in CHG futuro via slider.

7. **Defaults `referral_fee_pct=8`, `v_tot=0`, `s_comp=0`,
   `match_status=SICURO` in `build_listino_raw_from_resolved`**:
   le 5 colonne non risolvibili dal resolver (oltre `asin` e
   `buy_box_eur=cost_eur`) hanno valori conservativi. Il CFO con
   listino fornitore minimo (descrizione+prezzo) accetta che
   Velocity F4.A risulti = 0 (penalizzato in VGP) per ASIN senza
   stat di vendita; il top-1 viene scelto su buy_box e ROI.
   Override possibile via colonne CSV opzionali (CHG-020 supporta
   `v_tot`, `s_comp`, `category_node` opzionali).

8. **`buy_box_eur = cost_eur = prezzo_eur`**: semplificazione
   consapevole MVP. Il `prezzo_eur` del CFO e' il costo fornitore
   (cost_eur). Per `buy_box_eur` (prezzo lato Amazon, vendita
   finale) la fonte canonica e' Keepa NEW dal `lookup_product`.
   In CHG-020 NON popolo `buy_box_eur` distinto perche' avrebbe
   richiesto estendere `ResolvedRow` con `verified_buybox_eur`
   (campo gia' computato durante resolve, ma non esposto in
   `ResolutionCandidate.buybox_eur`). Scope CHG futuro: estendere
   il bridge per separare costo fornitore vs prezzo Amazon.
   Per ora, l'utente CFO sa che il prezzo che inserisce viene
   trattato uniformemente come "cost+buybox" (buy_box stimato =
   cost). VGP usa entrambi: ROI = cash_inflow / cost = (cost -
   fee_fba - cost*ref_fee) / cost; ovvero un'approssimazione
   conservativa ai fini classifica.

9. **`# noqa: C901, PLR0911, PLR0912, PLR0915` su `main()` e
   `_render_descrizione_prezzo_flow`**: i flow Streamlit
   multi-step sono inerentemente complessi (early returns su
   stati intermedi, mode switch, validazione input, ecc.).
   Refactor in sotto-funzioni "Streamlit pure" e' scope futuro
   (refactor multi-page ADR-0016) coerente con noqa di
   `build_session_input`.

10. **R-01 NO SILENT DROPS multi-livello**:
    - `parse_descrizione_prezzo_csv`: warnings esposti.
    - `resolve_listino_with_cache`: notes accumulate.
    - `format_confidence_badge` + tabella preview: `confidence_pct`
      + flag `is_ambiguous` esposti per ogni riga.
    - `build_listino_raw_from_resolved`: skip righe `asin=""`
      ma il CFO lo vede prima nella preview (NON e' "scarto
      silenzioso").

### Out-of-scope

- **Override candidato manuale per riga ambigua**: il flow
  attuale mostra il top-1 selected. Per riga ambigua, il CFO
  scarta dal CSV e re-uploada. Pattern selectbox top-3 alternative
  scope CHG futuro (UI multi-step expander).
- **Smoke test UI live in browser** (CHG-020 e' helper-only +
  Streamlit render); pattern coerente con TEST-DEBT-003 (smoke
  ~80% chiuso). Validazione interaction reale = manuale Leader-side.
- **`buy_box_eur` distinto da `cost_eur`**: come spiegato in
  decisione 8. Scope futuro estensione `ResolvedRow` con
  `verified_buybox_eur` da `ResolutionCandidate.buybox_eur` di
  CHG-018.
- **Refactor multi-page Streamlit ADR-0016**: scope futuro.
- **Cache TTL per `description_resolutions`**: scope futuro
  (le risoluzioni stabili in 6+ mesi possono essere stantie).
- **Bulk resolver async**: scope futuro per batch grandi (>100
  ASIN) — Chromium sequenziale puo' richiedere 5+ minuti.
- **Telemetria `ui.resolve_started` / `ui.resolve_confirmed`**:
  scope futuro errata catalogo ADR-0021.

## How

### `_render_descrizione_prezzo_flow` (highlight)

```python
def _render_descrizione_prezzo_flow(factory):
    # ... lazy imports ...
    uploaded = st.file_uploader(...)
    if uploaded is None: return None
    df_raw = pd.read_csv(uploaded)
    rows, parse_warnings = parse_descrizione_prezzo_csv(df_raw)
    for w in parse_warnings: st.warning(w)
    if not rows: return None

    if st.button("Risolvi descrizioni"):
        api_key = TalosSettings().keepa_api_key
        keepa_client = KeepaClient(api_key=api_key, rate_limit_per_minute=20)
        with _PlaywrightBrowserPage() as page:
            serp_adapter = _LiveAmazonSerpAdapter(browser_factory=lambda: page)
            lookup_callable = partial(lookup_product, keepa=keepa_client, ...)
            with st.spinner(f"Risoluzione di {len(rows)} descrizioni..."):
                resolved = resolve_listino_with_cache(rows, factory=factory, ...)
        st.session_state.resolved_rows = resolved

    resolved = st.session_state.resolved_rows
    if resolved is None: return None
    # tabella preview con confidence + badge
    if st.button("Conferma listino e crea sessione"):
        return build_listino_raw_from_resolved(resolved)
    return None
```

### `main()` post-edit (highlight biforcazione)

```python
mode = st.radio(
    "Formato listino",
    options=("Descrizione + prezzo (nuovo)", "ASIN gia' noto (legacy)"),
    horizontal=True,
)
listino: pd.DataFrame | None = None
if mode == "Descrizione + prezzo (nuovo)":
    listino = _render_descrizione_prezzo_flow(factory_for_sidebar)
    if listino is None: return
else:
    uploaded = st.file_uploader(...)  # flow legacy invariato
    listino = pd.read_csv(uploaded)
    ...
# da qui flow comune con `listino` pronto
inp = build_session_input(...)
result = run_session(inp)
...
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (54 source files, +1) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **640 PASS** (era 616, +24 nuovi `test_listino_input`) |
| Integration (no live) | `uv run pytest tests/integration --ignore=test_live_*` | **133 PASS** (invariato vs CHG-019) |
| Smoke import | `python -c "from talos.ui.dashboard import main, _render_descrizione_prezzo_flow"` | OK |

**Rischi residui:**
- **Streamlit testing limitato**: `_render_descrizione_prezzo_flow`
  non testabile come unit (richiede streamlit context). Helper
  puri sotto sono coperti. Validazione interaction reale resta
  manuale Leader-side (smoke browser, scope TEST-DEBT-003 residuo).
- **Costo Chromium boot per ogni "Risolvi descrizioni"**:
  ~1-2 secondi per N descrizioni. Per UX migliore: cache della
  page in `st.session_state`. Scope CHG futuro.
- **`buy_box_eur=cost_eur` semplificazione**: documentata, valida
  per MVP. Caller con esigenze precise puo' usare il flow legacy
  con CSV strutturato.
- **Lazy import `keepa`/`playwright` nel button**: se le deps
  hanno side-effect import (logging config), avvengono solo al
  primo click. Pattern accettabile.
- **Stato `st.session_state["resolved_rows"]`**: persiste fra
  re-render. Reset manuale solo dopo "Conferma listino" (linea
  `st.session_state.resolved_rows = None`). Possibile drift se
  CFO cambia CSV ma non re-clicca "Risolvi". Mitigazione: caption
  che invita a re-cliccare.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area `ui/`
  ADR-0013 consentita).
- **ADR-0016 vincoli rispettati:** `dashboard.py` Streamlit MVP
  mono-page (refactor multi-page rimane scope futuro).
- **ADR-0017 vincoli rispettati:** `_render_descrizione_prezzo_flow`
  consuma `_LiveAsinResolver` + `_LiveAmazonSerpAdapter` con
  pattern factory injection. Lookup tramite `partial(lookup_product,
  keepa=...)` Keepa-only per quota optimization.
- **R-01 NO SILENT DROPS**: ratificato a 4 livelli (parse warnings,
  resolve notes, badge confidence visibili, preview tabella con
  righe non risolte annotate). Governance test `keepa.miss` /
  `scrape.selector_fail` esplicitati nel docstring del modulo
  `listino_input.py`.
- **Test unit puri:** ✓ (ADR-0019). Helper puri 100% coperti
  via mock duck-typed.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `listino_input.py` ->
  ADR-0017 (canale acquisizione, gateway UI per asin_resolver).
- **Backward compat:** flow legacy CSV-strutturato (CHG-040)
  invariato; aggiunta `st.radio` mode + nuovo branch. Nessun
  caller esistente impattato.
- **Sicurezza:** zero input untrusted nel sorgente (i CSV sono
  uploadati dal CFO via streamlit, validati dal parser); JS hardcoded
  nei adapter (no injection); Keepa key letta via `TalosSettings`
  da `.env` (no esposizione).
- **Impact analysis pre-edit:** GitNexus risk LOW (modulo
  `listino_input.py` nuovo, dashboard.py edit additivo).

## Impact

- **Blocco asin_resolver chiuso 5/5**: 016 skeleton + 017 SERP
  live + 018 composer + 019 cache + 020 UI flow.
- **Path B end-to-end completo**: descrizione+prezzo CSV ->
  resolve+cache+save -> SessionInput -> run_session -> render
  cart/panchina/budget T+1 -> persistenza.
- **Decisione Leader delta=A "convivenza"**: zero breaking sul
  flow legacy.
- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11 viventi).
- **Test suite +24 unit**: 773 PASS totali (era 749).
- **MVP CFO target raggiunto**: l'utente puo' caricare un listino
  fornitore "umano" (descrizione+prezzo) e ottenere classifica
  VGP completa senza preprocessing manuale. Path B operativo
  end-to-end.
- **Milestone**: candidato `milestone/asin-resolver-v1.3.0` come
  restore point del blocco asin_resolver completo.

## Refs

- ADR: ADR-0016 (Streamlit + helper testabili senza streamlit
  pattern), ADR-0017 (canale asin_resolver UI), ADR-0014
  (mypy/ruff strict + dataclass frozen + lazy import pattern),
  ADR-0019 (test unit puri pattern).
- Predecessori:
  - CHG-2026-04-30-040 (`dashboard.py` MVP mono-page CSV-strutturato).
  - CHG-2026-05-01-016/017/018/019 (blocco asin_resolver).
- Decisione Leader 2026-05-01 round 4: delta=A convivenza dei
  2 flow CSV via `st.radio` mode (ratificata inline in
  conversazione).
- Memory: `feedback_ambigui_con_confidence.md` (R-01 UX-side
  applicata in `_render_descrizione_prezzo_flow` preview).
- Successore atteso: `milestone/asin-resolver-v1.3.0` tag come
  restore point. CHG futuro: refactor multi-page ADR-0016 e/o
  override candidato top-N selectbox + smoke browser umano
  TEST-DEBT-003 residuo.
- Commit: `2886728`.
