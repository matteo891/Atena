---
id: CHG-2026-05-02-037
date: 2026-05-02
adr_ref: ADR-0017, ADR-0036, ADR-0019, ADR-0014
commit: 7581ffd
---

## What

Hotfix bug live Leader 2026-05-02 round 7+ post CHG-036 deploy:

```
AttributeError: 'ProductData' object has no attribute 'drops_30'
File ".../listino_input.py", line 509, in _fetch_buybox_live_or_none
    drops_30=product.drops_30,
```

Defensive `getattr(product, ..., None)` in 2 call sites che leggono i
3 nuovi campi Arsenale dal `ProductData`.

| File | Cosa |
|---|---|
| `src/talos/ui/listino_input.py:_fetch_buybox_live_or_none` | Tutti i 5 attributi letti via `getattr(product, "<name>", None)`. |
| `src/talos/extract/asin_resolver.py:_LiveAsinResolver.resolve_description` | Idem nel try-block lookup candidato SERP. |
| `tests/unit/test_listino_input.py` | + 1 test sentinel: `_fetch_buybox_live_or_none` con stub `ProductData`-like senza i 3 nuovi attributi → snapshot graceful con campi None. |

## Why

Streamlit `@st.cache_data` (o hot-reload) può servire oggetti
`ProductData` serializzati pre-CHG-035 senza i 3 attributi
`drops_30`/`buy_box_avg90`/`amazon_buybox_share`. Anche se i campi
hanno default `None` nel dataclass, gli oggetti deserializzati da
pickle vecchio non li hanno fisicamente nel `__dict__`.

Soluzione: defensive `getattr(obj, name, None)` invece di accesso
diretto. Zero behavior change su oggetti nuovi (default None già
ritornato), backwards-compat 100% con oggetti vecchi.

R-01: campi `None` graceful → filter pull-only skip esplicito (non
drop silente).

## Tests

ruff/format/mypy strict OK. **TBD PASS** (+1 test sentinel hotfix).

## Test di Conformità

- ADR-0017: `ProductData` API stabile, accesso defensive.
- ADR-0036 (CHG-036): propagation pull-only graceful preservata.
- R-01 NO SILENT DROPS: campi None esplicitati.

## Refs

- ADR-0017, CHG-035, CHG-036.
- Bug Leader live 2026-05-02 post-deploy CHG-036.
- Commit: `7581ffd`.
