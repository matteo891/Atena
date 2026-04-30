---
id: CHG-2026-04-30-038
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: f693abc
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

Implementa **F4 + F4.A + F5 + velocity_monthly** in `src/talos/formulas/velocity.py`
— prerequisito dell'orchestratore di sessione end-to-end (CHG futuro).

Funzioni scalari pure verbatim PROJECT-RAW.md sez. 6.2:

- **F4.A** `q_m(v_tot, s_comp) = V_tot / (S_comp + 1)`
- **F4** `qty_target(q_m, days) = q_m * days / 30` (default 15 — L05)
- **F5** `qty_final(qty_target, lot_size=5) = Floor(qty_target / lot) * lot`
- **`velocity_monthly(q_m, days)`** = rotazione mensile attesa = `q_m * 30 / days`

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/formulas/velocity.py` | nuovo | 4 funzioni scalari + 2 costanti `DEFAULT_VELOCITY_TARGET_DAYS=15` / `DEFAULT_LOT_SIZE=5` |
| `src/talos/formulas/__init__.py` | modificato | +re-export delle 4 funzioni e 2 costanti |
| `tests/unit/test_velocity_quantity.py` | nuovo | 29 test (2 default + 6 q_m + 6 qty_target + 8 qty_final + 5 velocity_monthly + 2 composizione) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry `formulas/velocity.py` |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **325 PASS** (296 + 29).

## Why

L'orchestratore di sessione (prossimo step strategico) deve:
1. Ricevere il listino raw con colonne base (`buy_box_eur`, `cost_eur`,
   `referral_fee_pct`, `v_tot`, `s_comp`, `match_status`).
2. Calcolare F1 (`cash_inflow`), F2 (`cash_profit`), ROI, F4.A, F4, F5,
   `velocity_monthly` per riga.
3. Aggregare in DataFrame con tutte le colonne attese da `compute_vgp_score`.
4. Chiamare `compute_vgp_score` -> `allocate_tetris` -> `build_panchina` ->
   `compounding_t1`.

F1, F2, ROI, F3, fee_fba sono gia' coperti (CHG-022/025/026/032). Mancano F4/F4.A/F5
e `velocity_monthly` — questo CHG li aggiunge come funzioni scalari pure
testate in isolamento. La versione vettoriale (su pandas Series) sara'
"free" via broadcasting al call site dell'orchestratore.

### Decisioni di design

1. **`q_m` ritorna float** (non int): la divisione `V_tot / (S_comp+1)`
   non e' garantita intera (V_tot=100, S_comp=3 -> 25.0; V_tot=100,
   S_comp=2 -> 33.33). L'arrotondamento finale e' a F5.
2. **`qty_target` ritorna float** (non int): cast a int sarebbe prematuro;
   F5 fa Floor esplicito sui multipli di lot. Test
   `test_chain_with_floor_truncation` documenta `qty_target=12.5 -> qty_final=10`.
3. **`qty_final` ritorna int** (orderable): output finale = quantita' fisica
   ordinabile dal fornitore. `math.floor()` esplicito (non `int()` cast,
   per leggibilita' della semantica "Floor per cashflow").
4. **`DEFAULT_VELOCITY_TARGET_DAYS = 15`** verbatim L05 Round 5.
5. **`DEFAULT_LOT_SIZE = 5`** Samsung MVP. Override per altri brand
   (post-MVP) via parametro al call site.
6. **`_DAYS_PER_MONTH = 30`** costante privata: il "30" e' verbatim
   PROJECT-RAW.md riga 286 (`Qty_Target = Q_m * (15 / 30)`). Modifica via
   errata corrige.
7. **Validazione R-01 esplicita**: `v_tot >= 0`, `s_comp >= 0`,
   `q_m_value >= 0`, `qty_target_value >= 0`, `velocity_target_days > 0`,
   `lot_size > 0`. ValueError con messaggio. Boundary "0" ammesso (ASIN
   morto, no vendite).
8. **`velocity_monthly` separato da F4** (anche se algebricamente correlato):
   F4 ritorna pezzi fisici (per F5), `velocity_monthly` ritorna rotazioni
   adimensionali (per VGP). Semantiche diverse, mai mescolare le unita'.
9. **Vettorizzazione "free" via Series broadcasting**: `pd.Series.__truediv__`,
   `pd.Series.__floordiv__`, `numpy.floor` operano su Series senza .apply().
   L'orchestratore puo' usare le funzioni scalari come building block o
   replicare l'algebra inline su Series.

### Out-of-scope

- **Versione esplicita vettoriale** (`q_m_vec(v_tot_series, s_comp_series)`):
  semantica banale via broadcasting; aggiungere se emergera' un caller
  ridondante.
- **F4.B "Target a 15 Giorni dimezzato"**: documentazione PROJECT-RAW
  riga 308 (*"Talos dimezza la Quota Mensile per coprire 15 giorni"*) e'
  esattamente equivalente a `qty_target(q_m, 15)` = `q_m * 0.5`. F4.B
  non e' una formula separata, e' la specializzazione di F4 col default
  L05. Nessun simbolo nuovo.
- **F4 con velocity_target frazionario** (slider step < 1 giorno):
  ammesso dalla firma (`velocity_target_days: int`); attualmente int,
  potrebbe diventare float se UI lo richiede (errata futura).

## How

### `formulas/velocity.py` (highlight)

```python
DEFAULT_VELOCITY_TARGET_DAYS = 15
DEFAULT_LOT_SIZE = 5
_DAYS_PER_MONTH = 30

def q_m(v_tot, s_comp):
    return v_tot / (s_comp + 1)

def qty_target(q_m_value, velocity_target_days=15):
    return q_m_value * velocity_target_days / _DAYS_PER_MONTH

def qty_final(qty_target_value, lot_size=5):
    return math.floor(qty_target_value / lot_size) * lot_size

def velocity_monthly(q_m_value, velocity_target_days=15):
    return q_m_value * _DAYS_PER_MONTH / velocity_target_days
```

### Test plan (29)

- Default constants (2): 15, 5.
- F4.A q_m (6): no_competitors, one, many, zero_v_tot, negative_v_tot, negative_s_comp.
- F4 qty_target (6): default_15, 30, 7_min_slider, zero, invalid_q_m, invalid_velocity.
- F5 qty_final (8): exact_multiple, floor_to_lot, below_one_lot, zero, returns_int, custom_lot, invalid_lot, invalid_qty.
- velocity_monthly (5): 15_doubles_qm, 30_equals_qm, 7_days, zero_qm, invalid.
- Composizione (2): chain_no_truncation, chain_with_floor.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 73 files already formatted |
| Type | `uv run mypy src/` | ✅ 35 source files, 0 issues |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | ✅ **325 PASS** (296 + 29) |

**Rischi residui:**
- `velocity_monthly(q_m, 0)` raise: bene, ma se l'orchestratore non
  valida la slider UI, propaga l'errore. Mitigazione: validation Streamlit
  + check al primo punto di ingresso.
- `qty_target` ritorna float ma arrotondamenti float possono dare
  artifatti su `qty_target = q_m * 15/30` con q_m irrazionale: l'orchestratore
  passa output di `q_m` (gia' calcolato), il caso Samsung MVP ha numeri
  "puliti".
- `int * (15/30)` in Python: `15/30 = 0.5` esatto in float64. Nessun
  drift atteso.

## Impact

**Sblocca l'orchestratore di sessione**: tutti i building block scalari sono
ora disponibili. Il prossimo CHG implementera' `session.py` (o
`orchestrator.py`) con la pipeline `listino_raw -> calcoli per riga ->
compute_vgp_score -> sort -> allocate_tetris -> build_panchina ->
compounding_t1 -> output cruscotto`.

`compute_vgp_score` (CHG-035) accetta gia' una colonna `velocity_monthly`
come default parametro: il contratto e' allineato con questo CHG (zero
breaking changes).

## Refs

- ADR: ADR-0018 (formula completa F4/F4.A/F5 + velocity), ADR-0014
  (mypy/ruff strict), ADR-0013 (struttura `formulas/`), ADR-0019 (test pattern unit)
- Predecessori: CHG-2026-04-30-022/025/026/032 (catena scalare F1..F3 + ROI + fee_fba)
- Vision verbatim: PROJECT-RAW.md sez. 6.2 (F4 riga 286, F4.A riga 301, F5 riga 313) +
  L05 Round 5 (default 15 giorni)
- Successore atteso: orchestratore di sessione (CHG-039?) - pipeline
  end-to-end consumando tutte le formule + tetris
- Commit: `f693abc`
