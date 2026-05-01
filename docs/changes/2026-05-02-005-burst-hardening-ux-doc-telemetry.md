---
id: CHG-2026-05-02-005
date: 2026-05-02
author: Claude (modalità "ultra macinata burst medium" round 7 ratificata Leader)
status: Draft
adr_ref: ADR-0016, ADR-0021, ADR-0017, ADR-0018, ADR-0009, ADR-0019
commit: TBD
---

## What

**Burst hardening UX + documentazione + telemetria**: 5 fix correlati
post-CHG-003 (sblocco MVP V_tot estimator) per chiudere debiti UX/audit
emersi durante validazione live.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | + `st.warning` esplicito sotto subheader CSV: "il campo `prezzo` è il **costo fornitore**, NON il prezzo di vendita Amazon" (chiude bug semantico CSV emerso live). + caption sotto metric post-`run_session`: "V_tot sources (N ASIN): X da CSV, Y stimati da BSR, Z default zero". + help text uploader esteso con menzione BSR estimate. |
| `.gitignore` | modificato | + `test_*.csv` + `scratch_*.csv` (cleanup fixture untracked locali). |
| `src/talos/formulas/fee_fba.py` | modificato | Docstring esteso con **breakdown coefficienti** (`/1.22`, `100`, `0.0816`, `7.14`, `*1.03`, `+6.68`) + nota interpretativa onesta sul `*1.03` markup operativo (interpretazione speculativa, errata ADR-0018 quando avremo dati storici Amazon Italia). + commento per costante. Comportamento numerico **invariato** (zero formula change). |
| `src/talos/observability/events.py` | modificato | + voce catalogo `v_tot.estimated_from_bsr` con tupla `(asin, bsr, v_tot_estimated)` + costante `EVENT_V_TOT_ESTIMATED_FROM_BSR`. Catalogo: 17 → **18 voci**. |
| `src/talos/ui/listino_input.py` | modificato | Emit `_logger.debug("v_tot.estimated_from_bsr", ...)` in `build_listino_raw_from_resolved` quando `v_tot_source == V_TOT_SOURCE_BSR_ESTIMATE`. Audit aggregabile via LogCapture / log shipping production. |
| `tests/unit/test_events_catalog.py` | modificato | + 1 voce `_EXPECTED_EVENTS` (lock contract anti-drift). |
| `tests/unit/test_listino_input.py` | modificato | + 1 test sentinel emit `test_build_listino_emits_v_tot_estimated_from_bsr_event` (verifica che emit avvenga solo quando source è bsr_estimate, non per CSV o default_zero). |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **728 PASS** unit/gov/golden (era 727, +1 sentinel emit).
- **138 PASS** integration (invariato).
- **866 PASS** totali.

## Why

5 debiti emersi nelle sessioni di validazione live + review post-round 7:

1. **Bug semantico `prezzo` CSV** (#9 derivata): il CFO che testa per
   la prima volta cade nello stesso errore (mette prezzo Amazon →
   margine zero → ROI negativo → cart vuoto). Warning UI esplicito
   chiude il problema in 1 sguardo.
2. **Trasparenza V_tot source** (post CHG-003): il CFO vede solo i
   numeri, non capisce se v_tot=20 viene dal suo CSV o è stima MVP da
   BSR. Caption aggregato + colonna audit (già presente) + Help text
   uploader chiariscono la provenienza.
3. **Cleanup fixture untracked**: `test_*.csv` accumulati a livello di
   working dir potrebbero accidentalmente finire in commit; pattern
   `.gitignore` previene.
4. **Documentazione Fee_FBA `*1.03`** (falla #5 review): coefficiente
   non documentato in PROJECT-RAW. Aggiunto breakdown completo + nota
   onesta sull'interpretazione speculativa, marcata come "da ratificare
   dal Leader con dati storici Amazon Italia". Comportamento numerico
   invariato.
5. **Audit V_tot estimate** (post CHG-003): senza telemetria, il
   Leader non può aggregare quanti ASIN/sessioni dipendono dalla stima
   MVP placeholder vs CSV override. Evento canonico `v_tot.estimated_from_bsr`
   permette tracking aggregato (es. `% sessioni con >50% stimati = X` →
   indicatore di calibrazione necessaria).

## Tests

| Step | Esito |
|---|---|
| ruff/format/mypy strict | All passed (0 issues) |
| Unit/gov/golden | **728 PASS** (+1 sentinel) |
| Integration full (incl. live) | **138 PASS** invariato |
| Sentinel emit `v_tot.estimated_from_bsr` | mock-only: emit solo per source=bsr_estimate, non per CSV/default_zero |
| Sentinel catalog `_EXPECTED_EVENTS` | +1 voce (lock contract anti-drift) |
| Detect_changes | 0 processi affetti, risk LOW (fix UX/doc/telemetry, no formule core) |

## Test di Conformità

- ADR-0016 (UI Streamlit), ADR-0017 (Path B'), ADR-0018 (formule),
  ADR-0021 (catalogo eventi), ADR-0009 (errata corrige Fee_FBA doc),
  ADR-0019 (test strategy) ✓.
- R-01 NO SILENT DROPS: emit `v_tot.estimated_from_bsr` rende visibile
  ogni stima (audit trail).
- Comportamento runtime invariato 100% (warning UI + caption + emit
  telemetria sono additivi; doc Fee_FBA è solo testo).
- Catalogo ADR-0021: 17 → 18 voci (errata additiva, pattern coerente
  con CHG-024/025/037).
- `feedback_concisione_documentale.md` rispettato (CHG-005 ~80 righe).

## Refs

- ADR: ADR-0016, ADR-0017, ADR-0018, ADR-0021, ADR-0009, ADR-0019.
- Predecessore: CHG-2026-05-02-003 (V_tot estimator MVP — questo CHG
  ne completa l'audit + UX wrapper).
- Bug rilevato live in browser sessione round 7: confusione semantica
  `prezzo`. Falla #5 review: Fee_FBA `*1.03` non documentato.
- Successore atteso: errata ADR-0018 quando il Leader ratifica
  l'interpretazione canonica del `*1.03` (con dati Amazon Italia
  reali) + ricalibrazione V_tot estimator con ground truth.
- Commit: TBD.
