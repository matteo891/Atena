---
id: ADR-0018
title: Algoritmo VGP & Tetris — implementazione vettoriale Numpy
date: 2026-04-29
status: Active
deciders: Leader
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

Le decisioni di vision sull'algoritmo sono ratificate:
- L04 (Round 3): formula VGP `(ROI*0.4)+(Vel*0.4)+(Cash_Profit*0.2)`
- L04b (Round 4): normalizzazione **min-max [0,1]** sul listino di sessione
- L11b (Round 5): formula manuale Fee_FBA verbatim del Leader
- 9 Leggi R-01..R-09 vincolanti
- Vincolo 8.1: **vettorizzazione Numpy rigorosa** per gestire 10k righe senza colli di bottiglia RAM
- L05: slider Velocity Target 7–30 gg, default 15, granularità 1
- L10: Veto ROI configurabile, default 8%
- L13: Manual Override (Lock-in) Priorità=∞

Manca: layout dei moduli, contratti interni delle funzioni, scelta DataFrame, gestione edge case, struttura del Tetris come algoritmo (greedy DP-light vs altre varianti).

## Decisione

### Layout moduli (`src/talos/`)

```
vgp/
├── __init__.py
├── normalize.py        # min-max [0,1] sul listino di sessione (L04b)
├── score.py           # formula VGP + R-05 kill-switch
└── veto.py            # R-08 Veto ROI configurabile
tetris/
├── __init__.py
├── allocator.py       # R-06 saturazione 99.9% + R-04 Priorità=∞
└── panchina.py        # R-09 archiviazione
formulas/
├── __init__.py
├── cash_inflow.py     # F1: BuyBox - Fee_FBA - (BuyBox * Referral_Fee)
├── cash_profit.py     # F2: Cash Inflow - Costo_Fornitore
├── compounding.py     # F3: Budget T+1
├── velocity.py        # F4 + F4.A + F4.B (Q_m, Velocity Target)
├── lots.py            # F5: Floor(Qty_Target / 5) * 5
└── fee_fba.py         # formula manuale Fee_FBA L11b
```

### Scelta DataFrame: **pandas**

Razionale (decisione Leader): ergonomia con SQLAlchemy 2.0 (mappatura `pd.DataFrame ↔ ORM`), maturità su 10k righe (no bottleneck a questa scala), curva di apprendimento minima. **polars escluso dall'MVP**.

### Pipeline VGP (vettoriale, no loop Python)

```python
def compute_vgp_session(listino: pd.DataFrame, config: VgpConfig) -> pd.DataFrame:
    """
    Input:  listino con colonne ['asin', 'cost_eur', 'buy_box_eur', 'fee_fba_eur',
                                  'referral_fee_pct', 'v_tot', 's_comp', 'match_status']
    Output: DataFrame esteso con colonne VGP normalizzate + score + flags.
    """
    df = listino.copy()
    # F1, F2: cash inflow / cash profit
    df['cash_inflow_eur'] = df['buy_box_eur'] - df['fee_fba_eur'] - (df['buy_box_eur'] * df['referral_fee_pct'])
    df['cash_profit_eur'] = df['cash_inflow_eur'] - df['cost_eur']
    df['roi_pct']         = df['cash_profit_eur'] / df['cost_eur']
    # F4.A: Q_m
    df['q_m']             = df['v_tot'] / (df['s_comp'] + 1)
    df['velocity_monthly'] = df['q_m'] * 30 / config.velocity_target_days  # rotazione mensile attesa

    # R-05 KILL-SWITCH HARDWARE: dove match_status == 'KILLED' → vgp_score = 0
    kill_mask = df['match_status'] == 'KILLED'

    # L04b: normalizzazione min-max [0,1] sui termini del VGP
    for col_in, col_out in [('roi_pct', 'roi_norm'),
                             ('velocity_monthly', 'velocity_norm'),
                             ('cash_profit_eur', 'cash_profit_norm')]:
        df[col_out] = _min_max_normalize(df[col_in], kill_mask)

    # Formula VGP
    df['vgp_score'] = (df['roi_norm'] * 0.4) + (df['velocity_norm'] * 0.4) + (df['cash_profit_norm'] * 0.2)
    df.loc[kill_mask, 'vgp_score'] = 0.0  # R-05

    # R-08 Veto ROI configurabile
    df['veto_roi_passed'] = df['roi_pct'] >= config.veto_roi_threshold  # default 0.08
    df.loc[~df['veto_roi_passed'], 'vgp_score'] = 0.0

    # F4 + F5: quantità finale (lotti di 5)
    df['qty_target'] = (df['q_m'] * config.velocity_target_days / 30).astype(int)
    df['qty_final']  = (df['qty_target'] // 5) * 5

    return df.sort_values('vgp_score', ascending=False)
```

### `_min_max_normalize` (L04b)

```python
def _min_max_normalize(series: pd.Series, kill_mask: pd.Series) -> pd.Series:
    """Min-max [0,1] sul listino di sessione, escludendo righe KILLED dal calcolo
    di min/max (altrimenti VGP=0 forzato comprime la scala)."""
    eligible = series[~kill_mask]
    if len(eligible) == 0:
        return pd.Series(0.0, index=series.index)
    min_val, max_val = eligible.min(), eligible.max()
    if max_val == min_val:
        # Edge case: tutti i valori identici → termine non discrimina → 0 (convenzione L04b)
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)
```

### Edge case formula Fee_FBA (L11b)

Decisione Leader: **errore esplicito** (non silent drop, R-01).

```python
def fee_fba_manual(buy_box_eur: float) -> float:
    """Formula manuale Fee_FBA (L11b verbatim Leader)."""
    if buy_box_eur is None or buy_box_eur < 0:
        raise ValueError(f"buy_box_eur invalido: {buy_box_eur}")
    scorporato = buy_box_eur / 1.22
    if scorporato < 100:
        # Edge case: BuyBox sotto soglia. Leader ha confermato:
        # "non blocca per Samsung MVP (sempre sopra)". Errore esplicito per non-Samsung
        # post-MVP che potrebbero avere BuyBox basso.
        raise ValueError(
            f"buy_box_eur={buy_box_eur} sotto soglia: scorporato={scorporato:.2f} < 100. "
            f"Formula Fee_FBA L11b non garantita in questo range."
        )
    return ((scorporato - 100) * 0.0816 + 7.14) * 1.03 + 6.68
```

### Tetris Allocator (R-06 + R-04)

**Algoritmo greedy con Priorità=∞ pre-passo:**

```python
def allocate_tetris(vgp_df: pd.DataFrame, budget: float, locked_in: list[str]) -> Cart:
    """R-06 + R-04. Riempie il budget al 99.9% scorrendo VGP decrescente.
    Locked-in (R-04) hanno Priorità=∞ → entrano per primi a budget riservato."""
    cart = Cart(budget=budget)
    # Pass 1: Locked-in (R-04, Priorità ∞)
    for asin in locked_in:
        row = vgp_df[vgp_df['asin'] == asin].iloc[0]
        cost = row['cost_eur'] * row['qty_final']
        if cart.remaining < cost:
            raise InsufficientBudgetError(asin)
        cart.add(row, locked=True)
    # Pass 2: VGP decrescente, R-06 saturazione
    for _, row in vgp_df[~vgp_df['asin'].isin(locked_in)].iterrows():
        if row['vgp_score'] == 0:  # R-05 / R-08 esclusi
            continue
        cost = row['cost_eur'] * row['qty_final']
        if cart.remaining >= cost:
            cart.add(row)
            if cart.saturation >= 0.999:
                break
        # else: continue (R-06 "prosegue cercando item con VGP inferiore ma costo compatibile")
    return cart
```

### Panchina (R-09)

```python
def build_panchina(vgp_df: pd.DataFrame, cart: Cart) -> pd.DataFrame:
    """R-09: ASIN con vgp_score > 0 (quindi ROI ≥ 8% e match passato) NON nel cart,
    ordinati per vgp_score decrescente."""
    in_cart = set(cart.asin_list())
    return vgp_df[
        (vgp_df['vgp_score'] > 0) & (~vgp_df['asin'].isin(in_cart))
    ].sort_values('vgp_score', ascending=False)
```

### Reattività vettoriale (4.1.5)

Lo slider Velocity Target invalida il cache della pipeline (ADR-0016) e triggera ricalcolo full. Performance target: < 500ms su 10k righe (vettoriale Numpy garantisce).

### Property-based tests (Hypothesis, ADR-0019)

Su `vgp/normalize.py`: invariante `0 ≤ norm(x_i) ≤ 1` ∀ x_i, `norm(x_i) == 0` se `x_i == min` (escluso edge case max==min).
Su `vgp/score.py`: `vgp_score == 0` se `kill_mask` o `~veto_roi_passed`; `0 ≤ vgp_score ≤ 1` se attivo.

## Conseguenze

**Positive:**
- Pipeline pura: input invariati → output invariato → test golden byte-exact realizzabili (R-01).
- Vettoriale: 10k righe in <500ms.
- Decoupling chiaro: VGP non sa nulla di Tetris e viceversa.
- Edge case Fee_FBA gestito con errore esplicito → R-01 garantito.

**Negative / costi:**
- pandas su 10k+ righe può sentirsi: monitorare in produzione, eventuale Errata Corrige a polars.
- L'algoritmo Tetris è greedy, non ottimo: può lasciare cassa sul tavolo in casi patologici. Il vincolo "saturazione 99.9%" del Leader è soddisfatto in pratica ma non garantito teoricamente. Eventuale promotion a DP/ILP post-MVP.

**Effetti collaterali noti:**
- Il `VgpConfig` aggrega Veto ROI threshold + velocity_target + soglie di normalizzazione: cambio config = invalidazione cache + ricalcolo pipeline.
- I test golden devono essere mantenuti aggiornati a ogni modifica della formula: change document obbligatorio.

## Test di Conformità

1. **Golden test:** `tests/golden/test_samsung_1000.py` carica fixture byte-exact e verifica VGP+Cart+Panchina identici (no `pytest.approx`). Differenza di 1 cent → fail.
2. **Hypothesis su normalize:** invariante `0 ≤ norm ≤ 1`, idempotenza.
3. **Hypothesis su score:** `vgp_score == 0` con kill_switch o veto, range `[0, 1]` altrimenti.
4. **R-04 Lock-in:** test verifica che locked_in siano sempre nel cart finale, anche con budget tight.
5. **R-06 Saturazione:** test verifica saturazione `≥ 99.9%` su listino "saturabile".
6. **R-09 Panchina ordinata:** test verifica `vgp_score` decrescente in panchina.
7. **Edge case Fee_FBA:** test verifica `ValueError` su `buy_box_eur < 122` (scorporato < 100).
8. **No silent drops (R-01):** `tests/governance/test_no_silent_drops.py`.

## Cross-References

- ADR correlati: ADR-0013 (struttura `vgp/`, `tetris/`, `formulas/`), ADR-0014 (linguaggio, mypy strict), ADR-0015 (persistenza dei risultati), ADR-0016 (UI consumatrice), ADR-0017 (input dati), ADR-0019 (test golden + hypothesis), ADR-0021 (logging mismatch)
- Governa: `src/talos/vgp/`, `src/talos/tetris/`, `src/talos/formulas/`
- Impatta: il cuore del decisore. Ogni modifica richiede golden test aggiornato + change document.
- Test: `tests/golden/test_samsung_1000.py`, `tests/unit/test_vgp_*`, `tests/unit/test_tetris_*`
- Commits: `<pending>`

## Rollback

Se pandas + greedy si rivelano inadeguati:
1. Errata Corrige a ADR-0018: documentare bottleneck.
2. Promulgare ADR-NNNN per:
   - migrazione a polars (cambio import + .iterrows → .iter_rows lazy).
   - Tetris da greedy → DP/ILP via PuLP / OR-Tools (richiede dipendenza extra).
3. Mantenere golden dataset come oracolo di equivalenza.
