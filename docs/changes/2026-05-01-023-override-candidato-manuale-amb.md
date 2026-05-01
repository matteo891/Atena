---
id: CHG-2026-05-01-023
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 5 — A3 hardening flow descrizione+prezzo: override candidato manuale per righe ambigue)
status: Draft
commit: d699111
adr_ref: ADR-0017, ADR-0016, ADR-0014, ADR-0019
---

## What

Estende il flow descrizione+prezzo con **override candidato manuale**
per righe ambigue (memory `feedback_ambigui_con_confidence`
rafforzata: R-01 UX-side ora include scelta umana, non solo
visibility).

Pattern UX:
1. `ResolvedRow` espone `candidates: tuple[ResolutionCandidate, ...]`
   (top-N esaminati dal resolver, già disponibili in
   `ResolutionResult.candidates` da CHG-018).
2. Helper puro `apply_candidate_overrides(resolved, overrides)
   -> list[ResolvedRow]`: dato un dict `{idx: chosen_asin}`
   sostituisce `asin/confidence_pct/is_ambiguous/verified_buybox_eur`
   con quelli del candidato scelto + nota audit R-01.
3. UI `_render_ambiguous_candidate_overrides`: expander con
   `st.selectbox` top-N per ogni riga ambigua con N>1 candidati.
   Default = top-1 (selezione automatica resolver). Caption
   informativa che riassume il numero di override applicati.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + campo `ResolvedRow.candidates: tuple[ResolutionCandidate, ...] = field(default_factory=tuple)` (default backward compat). + helper puro `apply_candidate_overrides(resolved, overrides) -> list[ResolvedRow]` con nota audit R-01 esplicita su ogni override + ricalcolo `is_ambiguous` su nuova confidence. Override invalidi (idx out-of-range, asin non in candidates, redundant) sono no-op silenziosi. Propagation `result.candidates` -> `ResolvedRow.candidates` in `_resolved_row_from_result` (sia rami selected != None che selected == None). Cache hit branch resta con `candidates=()` (la cache non salva i candidates). Import `from talos.extract.asin_resolver import is_ambiguous as _is_ambiguous_threshold` per ricalcolo. |
| `src/talos/ui/dashboard.py` | modificato | + helper Streamlit `_render_ambiguous_candidate_overrides(resolved) -> dict[int, str]` (expander chiuso di default + selectbox per riga eligible: ambigua con `len(candidates) > 1`). + integrazione nel `_render_descrizione_prezzo_flow`: chiamata pre-preview per applicare override; preview e build operano su `resolved_with_overrides`. Caption finale espone numero di override applicati. Import `apply_candidate_overrides` lazy + `ResolvedRow` `TYPE_CHECKING`. |
| `tests/unit/test_listino_input.py` | modificato | + 8 test mock-only `apply_candidate_overrides`: empty no-op, swap completo (asin/buybox/confidence), is_ambiguous ricalcolo (boundary 70), nota audit append, asin invalido no-op, redundant no-op, isolazione idx specifico, idx out-of-range no-crash. + assertion `row.candidates == ()` nel test default-backward-compat. + helper `_candidate(...)` + `_ambiguous_resolved(...)` fixture. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **659
PASS** unit/gov/golden + 126 integration (no live) = **785 PASS**
no-live (era 777 a CHG-022, +8 nuovi A3). Con 7 test live skippabili
totale **792 PASS** (era 784).

## Why

CHG-020 ha consegnato il flow nuovo con esposizione di tutti i match
ambigui in tabella preview (R-01 UX-side: visibility). CHG-023 chiude
il loop: il CFO non solo *vede* i match ambigui, ma può *agire* su
di essi. Senza A3 il CFO con riga AMB ha 2 opzioni:
- accettare il top-1 automatico (rischio: scelta sbagliata se Amazon
  SERP ha ranking imperfetto);
- scartare la riga dal CSV e re-uploadare (overhead manuale).

Con A3:
- il CFO vede tutti i top-N candidati direttamente nella UI;
- può sostituire il top-1 con uno migliore in un click;
- l'audit trail (`notes`) registra l'override per esplicitare la
  scelta umana al consumatore downstream (orchestrator, persistenza).

Memory `feedback_ambigui_con_confidence.md` rafforzata:
*"match fuzzy a soglia bassa MAI skippati. Sempre esposti al CFO
con `confidence_pct` esplicito"*. CHG-023 estende: *"+ con possibilità
di override umano per riga ambigua quando il resolver ha più candidati"*.

### Decisioni di design

1. **Field `candidates` con default `()`**: backward compat 100%.
   Test esistenti CHG-020/022 invariati. Cache hit (no candidates
   disponibili) = tuple vuota, non interattiva. Riga con un solo
   candidato (top-1 unico) = anche non interattiva (l'override su
   un set di 1 elemento è meaningless).

2. **`apply_candidate_overrides` helper puro**: nessuna dipendenza
   Streamlit. Testabile via 8 test unit mock-only. Pattern coerente
   con `compare_session_kpis` (CHG-059), `parse_descrizione_prezzo_csv`
   (CHG-020).

3. **Override invalidi → no-op silenzioso (NOT raise)**: l'UX
   Streamlit potrebbe propagare un asin obsoleto se il CFO modifica
   il CSV fra "Risolvi" e "Conferma". Pattern coerente con
   `replay_session.locked_in_override` (CHG-056): meglio ignorare
   silenziosamente che far esplodere l'UI. Nota audit non aggiunta
   per override redundant/invalido (no rumore notes).

4. **`is_ambiguous` ricalcolato su nuova confidence**: il candidato
   alternativo può avere confidence sopra soglia 70 → la riga non
   è più ambigua. Coerente con la semantica del threshold
   (DEFAULT_AMBIGUOUS_THRESHOLD_PCT = 70 da CHG-016).

5. **`verified_buybox_eur` aggiornato dal candidato scelto**: ROI/VGP
   beneficia automaticamente del Buy Box del nuovo candidato. CHG-022
   feature ereditata.

6. **Nota audit "override manuale CFO"**: stringa esplicita,
   diversa dalle notes upstream del resolver. Permette al consumer
   downstream (audit log futuro) di filtrare le righe con scelta
   umana via grep `"override manuale CFO"`. Format:
   `"override manuale CFO: {chosen} (era {original})"`.

7. **UI `st.expander` chiuso di default**: il CFO che non vuole
   override non è disturbato dall'expander aperto. Il numero di
   righe ambigue è visibile nel titolo dell'expander
   (`"Override candidati ambigui (N righe sopra soglia AMB)"`).

8. **`format_func` selectbox compatto**: `"{asin} | {title:50} |
   conf {confidence_pct:.1f}%"`. Truncated title evita overflow
   visivo. Confidence esposta per scelta informata.

9. **Caption "Override CFO applicati: N"**: feedback immediato
   sulla scelta. Solo visibile se `n_overrides > 0` (no rumore).

10. **NO telemetria specifica `ui.override_applied`**: scope futuro
    (out-of-scope). Per ora il numero di override è visibile in
    `ui.resolve_confirmed.n_ambiguous` (alcune ambigue ora
    risolte da override). Errata catalogo additiva = scope CHG futuro
    se osservazione produzione mostra valore di tracking dedicato.

### Out-of-scope

- **Telemetria `ui.override_applied`**: errata catalogo ADR-0021
  additiva. Scope futuro.
- **Bulk override "Accetta tutti i top-2"**: gesto UX rapido per
  liste lunghe. Scope CHG futuro.
- **Override side-by-side con preview thumb / immagine prodotto**:
  miglioramento visuale UX. Scope futuro.
- **Persistenza override come "preferenza CFO"** (es. se CFO
  override `XX -> YY` 3 volte, propose YY come default): scope
  futuro learning loop.
- **Override per riga NON ambigua**: scope intenzionale escluso —
  l'UX espone selectbox solo per ambigue, le sicure (≥70) restano
  immutabili dalla preview. Caso d'uso opt-in scope futuro.

## How

### `ResolvedRow` esteso (highlight)

```python
@dataclass(frozen=True)
class ResolvedRow:
    # ... campi esistenti ...
    verified_buybox_eur: Decimal | None = None
    candidates: tuple[ResolutionCandidate, ...] = field(default_factory=tuple)  # CHG-023
```

### `apply_candidate_overrides` (highlight)

```python
def apply_candidate_overrides(resolved, overrides):
    out = []
    for idx, row in enumerate(resolved):
        chosen_asin = overrides.get(idx)
        if chosen_asin is None or chosen_asin == row.asin:
            out.append(row); continue
        match = next((c for c in row.candidates if c.asin == chosen_asin), None)
        if match is None:
            out.append(row); continue
        out.append(replace(row,
            asin=match.asin,
            confidence_pct=match.confidence_pct,
            is_ambiguous=_is_ambiguous_threshold(match.confidence_pct),
            verified_buybox_eur=match.buybox_eur,
            notes=(*row.notes, f"override manuale CFO: {match.asin} (era {row.asin})"),
        ))
    return out
```

### UI `_render_ambiguous_candidate_overrides` (highlight)

```python
eligible = [(idx, r) for idx, r in enumerate(resolved)
            if r.is_ambiguous and r.asin and len(r.candidates) > 1]
overrides = {}
with st.expander(f"Override candidati ambigui ({len(eligible)} righe)", expanded=False):
    for idx, row in eligible:
        current_idx = next((i for i, c in enumerate(row.candidates)
                            if c.asin == row.asin), 0)
        chosen = st.selectbox(
            f"`{row.descrizione[:60]}`",
            options=list(row.candidates),
            index=current_idx,
            format_func=lambda c: f"{c.asin} | {c.title[:50]} | conf {c.confidence_pct:.1f}%",
            key=f"override_select_{idx}",
        )
        if chosen.asin != row.asin:
            overrides[idx] = chosen.asin
return overrides
```

### Integrazione flow descrizione+prezzo (highlight)

```python
# pre-preview:
overrides = _render_ambiguous_candidate_overrides(resolved)
resolved_with_overrides = apply_candidate_overrides(resolved, overrides)
# preview + build operano su resolved_with_overrides
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **659 PASS** (era 651, +8 nuovi A3) |
| Integration (no live) | `TALOS_DB_URL=... uv run pytest tests/integration --ignore=test_live_*.py -q` | **126 PASS** (invariato) |

**Rischi residui:**
- **Streamlit `st.selectbox` keys collidono se idx ricicla**:
  pattern `key=f"override_select_{idx}"` è univoco fintanto che
  `resolved` è stabile fra render. Reset di `st.session_state.resolved_rows`
  (post-Conferma) genera nuovo idx-set, no collision.
- **Override su lista lunga (>30 ambigue)**: l'expander Streamlit
  potrebbe diventare scrollabile pesante. Mitigazione: il flow
  CHG-020 caps `max_candidates=3` (resolver), quindi `eligible`
  è limitato dalle righe input. Per liste >30 ambigue, scope futuro
  pagination.
- **Cache hit non interattiva**: il CFO con listino dominato da
  cache hit non ha la possibilità di override. Mitigazione UX:
  caption preview espone `cache_hit=Sì` per riga, il CFO può
  invalidare manualmente la cache (scope futuro: TTL +
  bottone "Invalida cache").
- **Override appended notes accumulate fra render**: `apply_*` è
  funzionale (ritorna nuova lista), `resolved` originale non
  muta. La nota audit appare solo nel `resolved_with_overrides`
  che viene passato a `build_listino_raw_from_resolved`. NON
  c'è leak persistente.
- **`format_func` lambda con loop var captures**: in Python loop
  var capture è classic gotcha (`lambda c: ...`); qui è OK
  perché `c` è il parametro del lambda (non chiusura su loop var).

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area ADR-0013
  consentita).
- **ADR-0017 vincoli rispettati:** `ResolutionCandidate` esistente
  riusato; nessuna modifica al canale resolver upstream.
- **ADR-0016 vincoli rispettati:** helper UI + helper puro
  testabile separati. `apply_candidate_overrides` zero deps Streamlit
  → 8 test unit puri.
- **Test unit puri:** ✓ (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `apply_candidate_overrides`
  → ADR-0017 (gateway UI per resolver). `_render_ambiguous_candidate_overrides`
  → ADR-0016 (UI Streamlit, helper render).
- **Backward compat:** Default `candidates=()` → tutti i caller
  esistenti invariati. Test CHG-020/022 verdi senza modifiche.
- **R-01 NO SILENT DROPS:**
  - tutti i candidati esposti in UI (CHG-018 R-01 UX-side preservato);
  - override audit trail in `notes` (nuova evidenza per audit);
  - override invalidi no-op silenzioso (no crash, ma anche no nota
    fittizia → coerente con principio "non confondere il CFO").
- **Sicurezza:** zero secrets, zero PII. ASIN/title/confidence sono
  dati pubblici Amazon.
- **Impact analysis pre-edit:** GitNexus risk LOW (`ResolvedRow`,
  `_render_descrizione_prezzo_flow` zero caller upstream esterni).
- **Detect changes pre-commit:** GitNexus risk LOW (4 file, 0
  processi affetti).
- **Memory `feedback_ambigui_con_confidence.md` onorata:** match
  ambigui ora esposti CON OPZIONE override umano = R-01 UX-side
  rafforzato.

## Impact

- **Hardening A3 chiuso**: il flow descrizione+prezzo è ora
  completo lato UX (visibility + scelta + audit trail).
- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (13/13
  viventi). `ui.override_applied` rinviato a errata futura.
- **Test suite +8 unit**: 659 unit/gov/golden (era 651).
- **MVP CFO target**: hardening A1+A2+A3 chiuso. Flow nuovo
  production-ready end-to-end + osservabile + scelta umana.
- **Pattern `apply_*_overrides` puro testabile**: replicabile per
  futuri override (es. categoria, fee).

## Refs

- ADR: ADR-0017 (`ResolutionCandidate` riusato), ADR-0016 (UI
  helper puri + render Streamlit), ADR-0014 (mypy/ruff strict +
  dataclass frozen + replace), ADR-0019 (test unit puri).
- Predecessori:
  - CHG-2026-05-01-018 (`_LiveAsinResolver`): producer di
    `ResolutionResult.candidates` propagato in CHG-023.
  - CHG-2026-05-01-016 (`is_ambiguous` threshold): riusato per
    ricalcolo dopo override.
  - CHG-2026-05-01-020 (UI flow descrizione+prezzo): consumer
    arricchito con A3.
  - CHG-2026-05-01-021/022 (A1/A2 telemetria + verified_buybox):
    chain di hardening.
- Memory: `feedback_ambigui_con_confidence.md` rafforzata
  (R-01 UX-side ora include scelta umana, non solo visibility).
- Successore atteso: nessuno specifico in scope hardening A1-A3.
  Possibili rotte (decisione Leader): (z) `structlog.bind`
  context tracing, (q) refactor UI multi-page ADR-0016, (β)
  `upsert_session` decisione semantica, (s) golden Samsung 1000 ASIN.
- Commit: `d699111`.
