---
id: CHG-2026-05-01-024
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" estesa round 5+ — manutenzione + telemetria additiva flow descrizione+prezzo)
status: Draft
commit: pending
adr_ref: ADR-0021, ADR-0016, ADR-0014, ADR-0019, ADR-0007
---

## What

Errata additiva al catalogo eventi canonici ADR-0021 + emit applicativo
nei 2 ulteriori siti del flow descrizione+prezzo non coperti dalle
errate precedenti (CHG-021/022/023). Chiude il gap di osservabilità
end-to-end: ora il flow emette telemetria sui **5 momenti chiave**
(start, fail, override, confirm, replay).

| Evento | Modulo | Campi obbligatori | Sito di emit |
|---|---|---|---|
| `ui.override_applied` | `ui/dashboard.py` | `n_overrides`, `n_eligible` | post `apply_candidate_overrides` se il CFO ha applicato almeno 1 override |
| `ui.resolve_failed` | `ui/dashboard.py` | `reason`, `n_rows` | button "Risolvi descrizioni" pre-`return None` su `api_key is None` |

**Bonus governance:** auto-aggiornamento stats GitNexus in
`AGENTS.md`/`CLAUDE.md` (4769→4770 nodes) post reindex di manutenzione
inizio sessione (Node v22.22.2; pattern coerente con CHG-2026-05-01-023
auto-update commit `1de31e3`). Indice ora `lastCommit == HEAD` post
manutenzione round 5+.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/observability/events.py` | modificato | + 2 voci `CANONICAL_EVENTS` (`ui.override_applied`, `ui.resolve_failed`) + 2 costanti `EVENT_*`. Catalogo passa da **13 a 15 voci**. Header docstring aggiornato (commento "13 voci" → "15 voci"). |
| `src/talos/ui/dashboard.py` | modificato | + 2 helper puri `_emit_ui_override_applied(*, n_overrides, n_eligible)` / `_emit_ui_resolve_failed(*, reason, n_rows)`. Emit inline ai 2 siti: (1) `_render_descrizione_prezzo_flow` button "Risolvi descrizioni" — emit `ui.resolve_failed` PRE `st.error` quando `api_key is None`; (2) post `apply_candidate_overrides` — emit `ui.override_applied` se `overrides` non vuoto, calcolando `n_eligible` come righe `is_ambiguous and asin and len(candidates) > 1`. |
| `docs/decisions/ADR-0021-logging-telemetria.md` | modificato | + voce `## Errata` 2026-05-01 CHG-024 con tabella 2 nuovi eventi + razionale (adoption rate A3 + fail-mode coverage). Coerente con pattern errata CHG-021/058 (additivo, no supersessione). |
| `tests/unit/test_dashboard_telemetry_resolve.py` | modificato | + 4 test caplog (2 per `_emit_ui_override_applied`: happy path 2/5 + edge full adoption 3/3; 2 per `_emit_ui_resolve_failed`: reason `keepa_key_missing` + reason `exception` per dimostrare enum-string aperta). + assertions sulle 2 nuove voci nel test "catalog contains new entries". Docstring header aggiornato (CHG-021 → CHG-021/024). |
| `tests/unit/test_events_catalog.py` | modificato | `_EXPECTED_EVENTS` esteso a 15 voci con commento ancorante CHG-024. Snapshot test invariato semanticamente (compara `set(CANONICAL_EVENTS.keys()) == _EXPECTED_EVENTS`). |
| `AGENTS.md` | modificato | Auto-update gitnexus stats post reindex: 4769 → 4770 nodes. |
| `CLAUDE.md` | modificato | Auto-update gitnexus stats post reindex: 4769 → 4770 nodes. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest unit:
**663 PASS** unit/gov/golden (era 659, +4 nuovi telemetry). Pytest
integration: **138 PASS** (incl. live tesseract/playwright/keepa/serp/asin_resolver
attivi end-to-end). **801 PASS** totali.

> Nota onesta: STATUS round 5 chiusura riportava "126 integration"
> ma il count effettivo no-live di questa sessione è 122 (138 totali
> meno 5 file `test_live_*`). Il diff `git diff b46b9ef HEAD --
> tests/ src/` è vuoto: la discrepanza è di conteggio storico, non
> di regressione. Il numero non regredisce post-CHG-024.

## Why

Il flow descrizione+prezzo CHG-020 + hardening CHG-021/022/023 emette
oggi `ui.resolve_started` e `ui.resolve_confirmed`. Restano 2 siti di
produzione **silenziosi**:

1. **Fail pre-resolve** (Keepa key missing): il CFO clicca "Risolvi",
   l'UI mostra `st.error`, ma in produzione non c'è traccia. Senza
   `ui.resolve_failed`:
   - non si distingue "fail Keepa key" da "il CFO non ha cliccato mai";
   - la quota Keepa missing è invisibile (non si sa quanti CFO hanno
     tentato senza chiave configurata);
   - una regressione che spingesse `api_key` a `None` su CFO con chiave
     valida sarebbe diagnosticabile solo via reclamo manuale.

2. **Override applicato** (A3 CHG-023): il CFO può sostituire il top-1
   automatico del resolver per le righe ambigue. Senza `ui.override_applied`:
   - non si misura l'**adoption rate** del feature A3 (quanti CFO usano
     l'override vs quanti accettano il top-1);
   - non si sa il rapporto `n_overrides / n_eligible` (% di righe
     ambigue effettivamente cambiate dal CFO);
   - decisione "A3 è valore o complicazione UX inutile" non quantificabile.

CHG-024 chiude il loop. Il flow ora è **end-to-end osservabile**.

### Decisioni di design

1. **`reason` come enum-string aperta vs Enum tipizzato**: pattern
   coerente con il catalogo esistente — gli event names sono stringhe
   letterali grep-friendly per il governance test. `reason="keepa_key_missing"`
   è il primo valore in produzione; valori futuri (`"exception"`,
   `"rate_limit"`) si aggiungono additivamente senza rompere il
   contratto. Enum richiederebbe import + sync col catalogo + duplicazione.

2. **Emit `ui.override_applied` SOLO se `overrides` non vuoto**: niente
   rumore quando il CFO non override nulla. Coerente con la caption
   UI che mostra "Override CFO applicati: N" solo se `n_overrides > 0`
   (CHG-023 decisione 9). Simmetria UX↔telemetria.

3. **`n_eligible` calcolato inline al sito di emit, non dentro l'helper**:
   l'helper `_emit_ui_override_applied` resta puro (zero dipendenze
   `ResolvedRow`). Il calcolo è 1 list comp + sum, leggibile inline.
   Pattern coerente con `n_resolved`/`n_total` calcolati inline pre
   `_emit_ui_resolve_confirmed` (CHG-021).

4. **`_emit_ui_resolve_failed` PRE `st.error`**: sequenza importante
   — prima telemetria (lo stato è "in fail"), poi UX feedback. Se
   `st.error` per qualche futuro motivo dovesse fallire (Streamlit
   internal exception), la telemetria è già emessa e il diagnosing
   rimane possibile.

5. **Helper puri (no inline `_logger.debug`)**: pattern consolidato
   CHG-021/058. Permette test caplog senza Streamlit context.

6. **DEBUG level**: coerente con tutti gli altri 13 eventi viventi
   del catalogo. INFO sarebbe semanticamente più corretto per
   `ui.resolve_failed` (è un fail "atteso", non un edge case), ma
   il catalogo ha già stabilito DEBUG come livello uniforme — coerenza
   batte semantica granulare per ora.

7. **Catalogo passa 13 → 15 voci**: errata additiva (pattern CHG-021/058),
   non supersessione. Regola ADR-0001 non si applica a modifiche
   additive di cataloghi.

8. **Auto-update GitNexus stats incluso nel CHG**: coerente con il
   commit pattern `1de31e3` (auto-update post CHG-023). Lo includo
   nello stesso commit di CHG-024 per economizzare la catena governance
   (1 commit invece di 2). ADR-0007 nel footer copre.

### Out-of-scope

- **Telemetria sub-eventi `ui.override_applied.changed`**: oggi
  l'evento è singolo per render. Tracking granulare per riga
  (chosen_asin, original_asin per ogni override) = noise eccessivo.
  Scope futuro se osservazione produzione mostra utilità.
- **`ui.resolve_failed` con `error_type`/`error_message` granulari**:
  oggi `reason` è enum-string. Estensione a campi `exception_class`/
  `exception_msg` quando il path "exception" sarà davvero implementato
  (fail-mode oltre `keepa_key_missing`).
- **Refactor `dashboard.py` per importare `EVENT_*` costanti invece
  di stringhe letterali**: scope futuro (out-of-scope CHG-021 dec. 6).
  Pattern governance test grep richiede stringhe letterali.
- **Dashboard observability "live event stream" lato CFO**: errata
  catalogo non basta, serve UI dedicata. Scope futuro multi-page B2.
- **`ui.override_reverted`**: scope futuro se il pattern UX evolve
  (oggi `apply_candidate_overrides` accetta solo override forward, non
  revert distinguibili).

## How

### `events.py` (highlight 2 nuove voci)

```python
CANONICAL_EVENTS: Final[dict[str, tuple[str, ...]]] = {
    # ... 13 voci esistenti ...
    # UI flow descrizione+prezzo — errata CHG-2026-05-01-024
    "ui.override_applied": ("n_overrides", "n_eligible"),
    "ui.resolve_failed": ("reason", "n_rows"),
}

EVENT_UI_OVERRIDE_APPLIED: Final[str] = "ui.override_applied"
EVENT_UI_RESOLVE_FAILED: Final[str] = "ui.resolve_failed"
```

### `dashboard.py` (highlight helper + emit)

```python
def _emit_ui_override_applied(*, n_overrides: int, n_eligible: int) -> None:
    _logger.debug(
        "ui.override_applied",
        extra={"n_overrides": n_overrides, "n_eligible": n_eligible},
    )


def _emit_ui_resolve_failed(*, reason: str, n_rows: int) -> None:
    _logger.debug(
        "ui.resolve_failed",
        extra={"reason": reason, "n_rows": n_rows},
    )

# Sito 1: button "Risolvi descrizioni"
if st.button("Risolvi descrizioni", key="resolve_descriptions_btn"):
    api_key = TalosSettings().keepa_api_key
    if api_key is None:
        _emit_ui_resolve_failed(reason="keepa_key_missing", n_rows=len(rows))
        st.error("TALOS_KEEPA_API_KEY non impostata. ...")
        return None
    _emit_ui_resolve_started(...)
    # ... resolver loop ...

# Sito 2: post apply_candidate_overrides
overrides = _render_ambiguous_candidate_overrides(resolved)
resolved_with_overrides = apply_candidate_overrides(resolved, overrides)
if overrides:
    n_eligible = sum(
        1 for r in resolved if r.is_ambiguous and r.asin and len(r.candidates) > 1
    )
    _emit_ui_override_applied(n_overrides=len(overrides), n_eligible=n_eligible)
```

### Test caplog (highlight pattern enum-string aperta)

```python
def test_resolve_failed_open_reason_enum(caplog):
    """`reason` è enum-string aperta: nuovi valori additivi non rompono il contratto."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.dashboard"):
        _emit_ui_resolve_failed(reason="exception", n_rows=20)
    records = [r for r in caplog.records if r.message == EVENT_UI_RESOLVE_FAILED]
    assert len(records) == 1
    assert records[0].reason == "exception"
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 1 file reformatted (dashboard.py wrap n_eligible) |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria mirata + governance | `uv run pytest tests/unit/test_dashboard_telemetry_resolve.py tests/unit/test_events_catalog.py tests/governance -v` | **13 PASS** (9 telemetry + 2 catalog + 2 governance) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **663 PASS** (era 659, +4 nuovi telemetry) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (16 live attivi end-to-end) |

**Rischi residui:**
- **Helper puri non testano lo `st.button` invocation**: il test
  copre l'emit ma non il "click → emit" Streamlit-side. Validazione
  interaction reale = manuale Leader-side (smoke browser TEST-DEBT-003
  residuo ~20%).
- **`n_eligible` può divergere da `_render_ambiguous_candidate_overrides`
  se la logica dell'helper Streamlit cambia**: il calcolo inline
  replica la condizione `is_ambiguous and asin and len(candidates) > 1`.
  Se l'helper Streamlit estende il filtro (es. nuovo flag), l'inline
  va aggiornato. Mitigazione: la condizione è stabile in CHG-023 e
  cambiare richiederebbe nuovo CHG che dovrebbe coprire entrambi i siti.
- **`reason="exception"` è documentato ma non emesso oggi**: lo
  emette il test, ma in produzione il path exception non è ancora
  implementato. Scope futuro errata se serve.
- **Drift dict ↔ ADR**: il governance snapshot `_EXPECTED_EVENTS`
  protegge da drift, ma il test non verifica meccanicamente che ogni
  evento del dict sia anche nell'ADR. Disciplina umana.

## Test di Conformità

- **Path codice applicativo:** `src/talos/observability/`,
  `src/talos/ui/` ✓ (aree ADR-0013 consentite).
- **ADR-0021 vincoli rispettati:**
  - Catalogo eventi canonici esteso via errata additiva (pattern
    CHG-021/058) — no supersessione necessaria.
  - Campi obbligatori per ogni nuovo evento esposti come `tuple`.
  - Modulo emittente documentato in errata.
  - DEBUG level coerente.
  - R-01 NO SILENT DROPS dinamico verde post-modifica.
- **ADR-0016 vincoli rispettati:** helper puri testabili senza
  Streamlit (pattern CHG-040/057/059/021).
- **Test unit puri:** ✓ (ADR-0019). 4 test caplog senza dipendenza Streamlit.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:**
  `_emit_ui_override_applied` / `_emit_ui_resolve_failed` →
  ADR-0016 (UI) + ADR-0021 (telemetria). Costanti `EVENT_UI_*` →
  ADR-0021.
- **Backward compat:** modifica additiva 100%; emit esistenti
  (`ui.resolve_started`, `ui.resolve_confirmed`) invariati. Nessun
  cambiamento di firma su simboli pubblici.
- **Sicurezza:** zero secrets nei campi log; `n_overrides`,
  `n_eligible`, `n_rows`, `reason` enum-string sono dati operativi
  non sensibili.
- **Impact analysis pre-edit:** `gitnexus_impact CANONICAL_EVENTS`
  ambiguo (Property/Variable). Dict di costanti, blast radius solo
  importatori. Risk LOW. `_render_descrizione_prezzo_flow` zero caller
  upstream.
- **Detect changes pre-commit:** `gitnexus_detect_changes` risk
  **LOW** (15 simboli touched, 0 processi affetti, 7 file).
- **GitNexus reindex eseguito** (manutenzione inizio sessione, ADR-0007):
  4770 nodes, lastCommit == HEAD pre-CHG-024.
- **Governance auto-update incluso (`AGENTS.md` / `CLAUDE.md`)**:
  pattern `1de31e3` post-CHG-023 replicato; footer ADR-0007 copre.

## Impact

- **Catalogo ADR-0021: 15/15 viventi** (era 13/13). +2 voci UI.
- **Hardening flow descrizione+prezzo end-to-end osservabile**: 5/5
  momenti chiave (start, fail, override, confirm, replay) emettono
  telemetria canonica.
- **`pyproject.toml` invariato** (no nuove deps).
- **Test suite +4 unit**: 663 unit/gov/golden (era 659).
- **MVP CFO target**: hardening incrementale; il flow descrizione+prezzo
  resta production-ready, ora con copertura osservabilità completa.
- **Pattern emit-helper-puro**: ulteriormente consolidato (CHG-021 →
  CHG-024 stessa firma `*, kw=...` + `_logger.debug` + dict `extra`).
- **Memoria `project_mvp_progress_estimate.md` refresh** (parte di
  manutenzione pre-CHG): da ~85% post-checkpoint-11 a ~93-94% Path B'
  post round 5 + ~96% Path B' post CHG-024.
- **GitNexus indice**: lastCommit == HEAD post-reindex manutenzione.
  Auto-stats AGENTS/CLAUDE 4769→4770 incluse nel commit.

## Refs

- ADR: ADR-0021 (catalogo eventi canonici, errata additiva pattern
  CHG-021/058), ADR-0016 (UI Streamlit + helper puri), ADR-0014
  (mypy/ruff strict + dataclass), ADR-0019 (test unit caplog), ADR-0007
  (auto-update stats GitNexus).
- Predecessori:
  - CHG-2026-05-01-021 (telemetria UI A1): pattern emit-helper-puro
    ereditato + bonus drift `session.replayed`.
  - CHG-2026-05-01-022 (verified_buybox A2): hardening flow.
  - CHG-2026-05-01-023 (override candidato A3): consumer della nuova
    telemetria `ui.override_applied`.
  - CHG-2026-05-01-020 (UI flow descrizione+prezzo): origine del flow
    coperto da telemetria.
  - CHG-2026-04-30-058 (drift `session.replayed`): pattern errata
    additiva ereditato.
- Memory: `project_mvp_progress_estimate.md` rifrescato (era STALE
  post round 5). `feedback_concisione_documentale.md` rispettato (errata
  snella + 4 test mirati + change doc auto-contenuto).
- Successore atteso: nessuno specifico in scope hardening telemetria.
  Possibili rotte (decisione Leader): (B1) `structlog.bind` context
  tracing, (B2) refactor UI multi-page ADR-0016, (β) `upsert_session`
  decisione semantica, (POLICY-001) Velocity bsr_chain.
- Commit: pending.
