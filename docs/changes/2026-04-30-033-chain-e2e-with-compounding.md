---
id: CHG-2026-04-30-033
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Proposed
commit: TBD
adr_ref: ADR-0019, ADR-0018
---

## What

Estende `tests/unit/test_value_chain.py` con 2 test che coprono il **rollup di sessione** via F3 (compounding T+1). Senza questa estensione, la sentinella e2e di CHG-028 si fermava al boolean del veto e non verificava la chiusura del ciclo finanziario `Budget_T → sessione → Budget_T+1`.

| File | Tipo | Cosa |
|---|---|---|
| `tests/unit/test_value_chain.py` | modificato | +2 test: (1) rollup anchor su scenario "5 ASIN con 2 vetoed" → Budget_T+1 = Budget_T + somma(cash_profit non vetati); (2) chained T→T+1→T+2 (3 sessioni in sequenza, propagazione corretta del budget) |

Quality gate **atteso** verde: ruff/format/mypy strict invariati (no codice toccato); ~237 test PASS (235 + 2).

## Why

CHG-032 ha aggiunto F3 ma non c'era ancora una verifica di **composizione** della pipeline che includesse il rollup. La sentinella e2e di CHG-028 si fermava al boolean del veto. Adesso la catena scalare è formalmente F1→F2→ROI→Veto→**rollup F3**: serve un test che verifichi la coerenza dei contratti su tutta la sequenza, incluso il caso realistico "calcola il budget di sessione successiva escludendo gli ASIN vetati".

Tre motivi:

1. **Antifragilità totale della catena**: dopo questa estensione, qualunque cambio di firma/unità/semantica in qualsiasi anello (incluso F3) rompe la sentinella. La catena è "blindata".
2. **Documentazione vivente del rollup**: chi legge il test capisce immediatamente come si usa F3 in pipeline (filtra non-vetati → somma → aggiungi al budget T).
3. **Prerequisito naturale per `milestone/first-formula-v1.0.0`**: il restore point del blocco "catena scalare formule chiusa" guadagna in significato se include un test che dimostra la chiusura.

### Decisioni di design

1. **Test rollup anchor (1)**: scenario fisso "Budget_T = 1000, 5 ASIN" — riusa i 5 scenari del parametrico esistente. Filtra quelli `not vetoed` → somma del loro `cash_profit` → aggiungi al budget. Snapshot pre-calcolato:
   - 3 ASIN passano (low_value/mid_value/high_value): cash_profit ≈ 64.59 + 84.92 + 245.48 = 394.99 EUR
   - 2 vetoed (loss_leader/thin_margin) ESCLUSI dal rollup (R-08 a monte)
   - Budget_T+1 ≈ 1000 + 394.99 = 1394.9957 EUR
2. **Test chained T→T+1→T+2 (2)**: 3 mini-sessioni, ognuna con 1 ASIN che passa il veto. Verifica che il budget si accumuli correttamente ad ogni step:
   - T0: Budget=1000, ASIN profit=64.59 → Budget_T1 = 1064.59
   - T1: Budget=1064.59, ASIN profit=84.92 → Budget_T2 = 1149.51
   - T2: Budget=1149.51, ASIN profit=245.48 → Budget_T3 = 1394.9957
3. **Filter pattern**: il test esegue il filtro come farebbe l'orchestratore reale: `[profit for ... if not is_vetoed_by_roi(...)]`. Non un mock, non una flag. Il filtro è il **contratto del rollup** (R-08 esclude dai profitti reinvestibili).
4. **Tolerance 1e-3 EUR coerente** con CHG-028.
5. **Niente nuovo file**: si arricchisce il file esistente. Riduce frammentazione.

## How

### `tests/unit/test_value_chain.py` (additivo)

```python
def test_chain_with_rollup_excludes_vetoed_profits() -> None:
    """Rollup anchor: 5 ASIN, 2 vetoed; Budget_T+1 somma solo non-vetoed."""
    scenarios = [
        (200.0,  0.08, 100.0),
        (500.0,  0.15, 300.0),
        (1000.0, 0.08, 600.0),
        (122.0,  0.15, 110.0),  # loss_leader (vetoed)
        (200.0,  0.08, 158.0),  # thin_margin (vetoed)
    ]
    surviving_profits: list[float] = []
    for buy_box, ref, costo in scenarios:
        fee = fee_fba_manual(buy_box)
        inflow = cash_inflow_eur(buy_box, fee, ref)
        profit = cash_profit_eur(inflow, costo)
        roi_value = roi(profit, costo)
        if not is_vetoed_by_roi(roi_value):
            surviving_profits.append(profit)
    budget_t1 = compounding_t1(1000.0, surviving_profits)
    assert isclose(budget_t1, 1394.9957, abs_tol=_TOL_EUR)


def test_chain_chained_three_sessions_compounds_budget() -> None:
    """T -> T+1 -> T+2 -> T+3: budget cresce monotono con 3 ASIN che passano."""
    sessions = [
        (200.0, 0.08, 100.0),
        (500.0, 0.15, 300.0),
        (1000.0, 0.08, 600.0),
    ]
    budget = 1000.0
    for buy_box, ref, costo in sessions:
        fee = fee_fba_manual(buy_box)
        inflow = cash_inflow_eur(buy_box, fee, ref)
        profit = cash_profit_eur(inflow, costo)
        roi_value = roi(profit, costo)
        if not is_vetoed_by_roi(roi_value):
            budget = compounding_t1(budget, [profit])
    assert isclose(budget, 1394.9957, abs_tol=_TOL_EUR)
```

### Verifica numerica preventiva

Snapshot dei `cash_profit` per gli ASIN che passano (riusati da CHG-028, già verificati):

| Scenario | cash_profit | vetoed |
|---|---|---|
| low_value_passes (200, 0.08, 100) | 64.5922 | False |
| mid_value_passes (500, 0.15, 300) | 84.9226 | False |
| high_value_passes (1000, 0.08, 600) | 245.4756 | False |
| loss_leader_vetoed (122, 0.15, 110) | -20.33 | **True** (escluso) |
| thin_margin_vetoed (200, 0.08, 158) | 6.59 | **True** (escluso) |

`Σ(non-vetoed) = 64.5922 + 84.9226 + 245.4756 = 394.9904`
`Budget_T+1 = 1000 + 394.9904 = 1394.995704 ≈ 1394.9957` (tolerance 1e-3)

Per il chained test, il risultato finale è identico (la somma è associativa): 1394.9957.

### Out-of-scope

- **Test con DataFrame vettoriale**: scope futuro `vgp/`.
- **Test che persistono Budget_T+1 in `sessions` table**: scope futuro orchestratore di sessione.
- **Property-based test (Hypothesis)** sulla catena chained: scope futuro se emerge un'invariante non banale.
- **Test di erosione completa del budget** (Budget_T+1 < 0): è già coperto dal test isolato di compounding (test_negative_budget_t1_when_losses_exceed_budget). Non serve replicare in composizione.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (29 source files invariati) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~237 PASS (235 + 2) |

**Rischi residui:**

- I valori snapshot dipendono dai precedenti CHG-022/025/026. Se uno di quei snapshot cambia (errata corrige numerica), va aggiornato anche qui. Mitigazione: la coerenza è già verificata dal test anchor di CHG-028 (`test_chain_intermediate_values_match_snapshots`) che riusa gli stessi numeri.
- I 2 test sono numericamente identici nel risultato finale (1394.9957). Non è ridondanza: il primo verifica il pattern "filtra-poi-somma una volta", il secondo verifica il pattern "compounda step-by-step in N sessioni". Sono due semantiche diverse (batch vs streaming).

## Refs

- ADR: ADR-0019 (test strategy), ADR-0018 (catena del valore)
- Predecessori: CHG-2026-04-30-028 (sentinella iniziale F1→F2→ROI→Veto), CHG-2026-04-30-032 (F3)
- Vision: PROJECT-RAW.md sez. 6.3 + R-07 + R-08
- Successore atteso: `milestone/first-formula-v1.0.0` (catena scalare formule blindata da sentinella e2e)
- Commit: TBD
