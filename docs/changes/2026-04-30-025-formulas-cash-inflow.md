---
id: CHG-2026-04-30-025
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 2fb60a8
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

**F1 — Cash Inflow**: seconda formula applicativa di Talos, secondo passo della catena del valore (`fee_fba` → **`cash_inflow`** → `cash_profit` → `ROI` → `VGP score`). Funzione pura `cash_inflow_eur(buy_box_eur, fee_fba_eur, referral_fee_rate) -> float` che incarna verbatim la Formula 1 di PROJECT-RAW.md sez. 6.3:

```
Cash Inflow = BuyBox − Fee_FBA − (BuyBox * Referral_Fee)
```

Primo consumatore architetturalmente naturale di `fee_fba_manual` (CHG-022): chi userà `cash_inflow_eur` passerà come secondo argomento il valore restituito da `fee_fba_manual` (fallback) o da Keepa lookup (primario, ADR-0017).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/formulas/cash_inflow.py` | nuovo | `cash_inflow_eur(buy_box_eur, fee_fba_eur, referral_fee_rate) -> float` verbatim F1 + 3 validazioni R-01 (no negativi su buy_box/fee_fba; `referral_fee_rate` in [0, 1]) |
| `src/talos/formulas/__init__.py` | modificato | Re-export `cash_inflow_eur` aggiunto a `__all__` |
| `tests/unit/test_cash_inflow.py` | nuovo | 9 test (3 snapshot tolerance-based + 1 zero referral + 1 negative-cash-inflow-allowed + 1 monotonia + 2 raises su negativi + 1 parametrico raises su referral_fee fuori range) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Entry `src/talos/formulas/cash_inflow.py` → ADR-0018 + ADR-0019 |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; ~180 test PASS (171 + 9 nuovi).

## Why

CHG-022 ha attraversato la frontiera applicativa scrivendo `fee_fba_manual`. Il modulo è però **isolato**: GitNexus context conferma 0 incoming edges (nessun consumatore). Per essere utile, deve essere consumato in una catena di calcolo. F1 (Cash Inflow) è il primo anello: prende `fee_fba` come input e produce il **flusso di cassa per singola unità venduta**.

La sequenza causale del prodotto Talos (PROJECT-RAW.md sez. 6.3 + ADR-0018):

```
BuyBox + Fee_FBA + Referral_Fee  →  F1 Cash Inflow
                                              + Costo_Fornitore  →  F2 Cash Profit
                                                                              + Costo_Fornitore  →  ROI
                                                                                                            + Velocity + Cash_Profit_assoluto  →  VGP score
                                                                                                                                                                  →  Tetris allocation
```

`cash_inflow` è il **vincolo causale di uscita di fee_fba** e l'**input di F2**. Costruirlo sblocca F2 + ROI, che insieme bastano per il **veto ROI** (R-08) — il primo filtro applicativo del Tetris. È la formula a maggiore "valore di attivazione architetturale" per il prossimo CHG.

### Note di design (Leader verbatim + applicate)

1. **Zero scorporo IVA** (Leader, sez. 6.3): *"zero scorporo IVA per via del Reverse Charge + Credito infinito"*. La formula NON scorpora IVA dal BuyBox; opera su valore lordo. Coerente con il `+ 6.68` finale di L11b che è cap IVA-inclusivo. F1 e Fee_FBA viaggiano sulla stessa base lorda.
2. **`Fee_FBA` e `Referral_Fee` sono input, non calcoli interni.** Coerente con la separazione di responsabilità: F1 è una **formula combinatoria**, non un orchestratore. La logica primario→fallback per `Fee_FBA` (Keepa → `fee_fba_manual`) vive in `io_/keepa_client.py` (ADR-0017, scope futuro); la logica lookup categoria + override per `Referral_Fee` vive in `config/` o equivalente (L12, scope futuro). F1 si fida che gli arrivino già risolti.
3. **`referral_fee_rate` come frazione decimale [0, 1].** Convenzione esplicita nel docstring (`0.08 = 8%`). Out-of-range → `ValueError`.
4. **Output negativo ammesso (cash_inflow < 0).** "Vendita in perdita" è un fatto economico legittimo: ASIN sotto costo. Restituirlo invariato preserva l'informazione per il Veto ROI (R-08) e per il logging a valle. R-01 NO SILENT DROPS proibisce *valori impliciti o NaN*, non valori negativi calcolati esattamente.

## How

### `src/talos/formulas/cash_inflow.py`

```python
def cash_inflow_eur(
    buy_box_eur: float,
    fee_fba_eur: float,
    referral_fee_rate: float,
) -> float:
    if buy_box_eur < 0: raise ValueError(...)
    if fee_fba_eur < 0: raise ValueError(...)
    if not 0 <= referral_fee_rate <= 1: raise ValueError(...)
    return buy_box_eur - fee_fba_eur - (buy_box_eur * referral_fee_rate)
```

Implementazione verbatim della formula. Ordine di validazione: argomenti in posizione di chiamata, una `ValueError` per ognuno con messaggio diagnostico. Output mai gated (nessun `max(0, ...)` o `abs(...)`).

### Snapshot pre-calcolati

Calcolati componendo `fee_fba_manual` (snapshot CHG-022) con la formula F1:

| buy_box | fee_fba | referral | cash_inflow |
|---|---|---|---|
| 200.00 | 19.4078 | 0.08 | **164.5922** |
| 500.00 | 40.0753 | 0.15 | **384.9247** |
| 1000.00 | 74.5212 | 0.08 | **845.4788** |
| 200.00 | 19.4078 | 0.00 | **180.5922** (zero referral) |
| 100.00 | 80.0000 | 0.50 | **−30.0000** (vendita in perdita ammessa) |
| −1.00 | 10.00 | 0.08 | **ValueError** |
| 200.00 | −1.00 | 0.08 | **ValueError** |
| 200.00 | 19.4078 | −0.01 / 1.01 / 2.0 | **ValueError** (parametrico) |

Tolerance: 1e-3 EUR (consistente con CHG-022).

### Test plan (9 test)

1. `test_snapshot_low_value` → `cash_inflow_eur(200, 19.4078, 0.08) ≈ 164.5922`
2. `test_snapshot_mid_value` → `(500, 40.0753, 0.15) ≈ 384.9247`
3. `test_snapshot_high_value` → `(1000, 74.5212, 0.08) ≈ 845.4788`
4. `test_zero_referral_fee` → `(200, 19.4078, 0.0) ≈ 180.5922` (boundary inclusivo)
5. `test_negative_cash_inflow_allowed` → `(100, 80, 0.5) == -30.0` (no ValueError)
6. `test_decreases_with_referral_fee` → monotonia inversa su 5 rate crescenti
7. `test_raises_on_negative_buy_box` → `(-1, 10, 0.08)` → ValueError "buy_box_eur"
8. `test_raises_on_negative_fee_fba` → `(200, -1, 0.08)` → ValueError "fee_fba_eur"
9. `test_raises_on_referral_fee_out_of_range` (parametrico su `[-0.01, 1.01, 2.0]`) → ValueError "referral_fee_rate"

Niente integration: la formula è pura, no I/O.

### Out-of-scope

- **Versione vettoriale** (Numpy/pandas) per il listino di sessione: scope di `vgp/normalize.py` o equivalente, futuro CHG.
- **Lookup `Fee_FBA` da Keepa** (primario): scope `io_/keepa_client.py`, ADR-0017.
- **Lookup `Referral_Fee` per categoria** + override manuale: scope config layer + UI cruscotto, ADR-0016/0017.
- **Composizione di test end-to-end** (`fee_fba_manual` → `cash_inflow_eur` → ...): scope di un test "catena del valore" futuro, idealmente sotto `tests/golden/` quando il dataset Samsung sarà disponibile.
- **F2 Cash Profit + ROI**: prossimo CHG, naturale prosecuzione.
- **`Decimal` per i calcoli finanziari**: rinviata; `float` con tolerance 1e-3 è sufficiente fino a quando non emergono drift osservabili nei test golden.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (22 source files) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~180 PASS |

**Rischi residui:**

- Snapshot tests sensibili alla precisione di `fee_fba_manual` (tolleranza 1e-3 EUR). Eventuali errata corrige di L11b che modificassero le costanti propagano qui — i test snapshot vanno aggiornati di conseguenza.
- `float` su catena lunga (cash_inflow → cash_profit → ROI → VGP) può accumulare errori di arrotondamento a livelli osservabili. Decisione `float` vs `Decimal` rinviata fino a evidenza di drift nei golden tests Samsung.
- Output negativo è permesso by design. Se in futuro il Leader vorrà che cash_inflow ≤ 0 sia un errore (es. gating al boundary applicativo), serve errata di ADR-0018.
- `referral_fee_rate=1.0` esatto è ammesso (boundary inclusivo): produce `cash_inflow = -fee_fba_eur`. Caso degenerato ma matematicamente valido.

## Refs

- ADR: ADR-0018 (algoritmo VGP/Tetris — sez. F1), ADR-0014 (mypy/ruff strict), ADR-0013 (struttura `formulas/`), ADR-0019 (test unit pattern)
- Predecessore: CHG-2026-04-30-022 (`fee_fba_manual` — primo modulo applicativo, isolato; questo CHG lo collega alla catena del valore)
- Vision verbatim: PROJECT-RAW.md sez. 6.3 Formula 1
- Successore atteso: F2 Cash Profit + ROI in CHG separato (sblocca veto R-08)
- Commit: `2fb60a8`
