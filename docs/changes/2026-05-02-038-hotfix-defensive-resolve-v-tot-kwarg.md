---
id: CHG-2026-05-02-038
date: 2026-05-02
adr_ref: ADR-0017, ADR-0018, ADR-0019, ADR-0014
commit: TBD
---

## What

Hotfix bug live Leader 2026-05-02 round 7+ post CHG-037 deploy:

```
TypeError: resolve_v_tot() got an unexpected keyword argument 'drops_30'
File ".../listino_input.py", line 755, in build_listino_raw_from_resolved
    v_tot_resolved, v_tot_source = resolve_v_tot(
```

Defensive `try/except TypeError` in `build_listino_raw_from_resolved`
per tolleranza a `velocity_estimator.resolve_v_tot` legacy senza kwarg
`drops_30` (Streamlit hot-reload skew: `listino_input.py` ricaricato
con la signature nuova ma `velocity_estimator.py` ancora in versione
pre-CHG-034 in memoria).

| File | Cosa |
|---|---|
| `src/talos/ui/listino_input.py:build_listino_raw_from_resolved` | `try/except TypeError` wrapping della chiamata `resolve_v_tot(..., drops_30=...)`. Fallback alla signature legacy (senza `drops_30`) graceful. |

## Why

Streamlit hot-reload non garantisce ricarica atomica di tutti i
moduli importati. Quando il Leader ha applicato il deploy CHG-037,
`listino_input.py` è stato hot-reloaded con la chiamata `drops_30=`
ma `velocity_estimator.py` (caricato lazily in `talos.extract`) è
ancora il modulo vecchio in memoria del processo Streamlit → kwarg
non riconosciuto → TypeError.

Soluzione robusta: try/except `TypeError` con fallback alla signature
legacy. Il caller continua a chiamare la versione nuova; se fallisce
silenziosamente per skew, fallback alla versione vecchia (senza
drops_30). Behavior change: in caso di skew, drops_30 non viene
usato → fallback a BSR placeholder MVP (CHG-034 errata behavior
pre-deploy). Una volta che il Leader **riavvia completamente
Streamlit** (kill processo + restart), tutti i moduli sono freshly
loaded e la versione nuova è attiva → behavior CHG-036 ripristinato.

R-01: behavior degradato esplicito (fallback su BSR placeholder),
non drop silente.

## Tests

ruff/format/mypy strict OK. **TBD PASS** (+1 sentinel hotfix).

## Test di Conformità

- ADR-0017: `velocity_estimator.resolve_v_tot` API non rotta.
- ADR-0018 + CHG-034 errata: drops_30 path preferito quando
  disponibile, fallback BSR placeholder altrimenti.
- R-01 NO SILENT DROPS: fallback esplicito (no try-pass silente).

## Refs

- ADR-0017, CHG-034 (errata drops_30), CHG-036 (propagation), CHG-037
  (hotfix getattr ProductData simmetrico).
- Bug Leader live 2026-05-02 post-deploy CHG-037 (Streamlit hot-reload
  skew).
- Commit: TBD.
