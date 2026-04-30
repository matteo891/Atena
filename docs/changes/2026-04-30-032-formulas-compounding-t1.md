---
id: CHG-2026-04-30-032
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: eb04afb
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

**F3 Compounding T+1** — formula scalare verbatim PROJECT-RAW.md riga 280:

```
Budget_T+1 = Budget_T + Somma(Cash_Profit)
```

Chiude la catena scalare delle formule operative (F1 cash_inflow → F2 cash_profit → F3 compounding). Funzione pura, accetta iterabile di profitti per sessione T e ritorna il budget reinvestibile in T+1. Coerente con R-07 (VAT CREDIT COMPOUNDING — *"100% del bonifico Amazon è capitale reinvestibile"*).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/formulas/compounding.py` | nuovo | `compounding_t1(budget_t: float, cash_profits: Iterable[float]) -> float` — F3 verbatim |
| `src/talos/formulas/__init__.py` | modificato | Re-export `compounding_t1` + entry CHG-032 nel docstring |
| `tests/unit/test_compounding.py` | nuovo | 9 test: snapshot principale + lista vuota + soli positivi + soli negativi + mix + erosione budget oltre zero + generator/Iterable + 1 solo profitto + budget zero start |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Entry `src/talos/formulas/compounding.py` → ADR-0018 + ADR-0019 |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; ~235 test PASS (226 + 9).

## Why

F3 è il terzo (e ultimo) anello della catena scalare di formule operative. Senza F3 manca la chiusura del ciclo finanziario di sessione: `Budget_T → applica VGP/Tetris → registra Cash_Profit → Budget_T+1`. R-07 lega esplicitamente F3 al pattern *"100% reinvestibile"*: senza una funzione che materializzi il calcolo, il pattern resta documentale.

Inaugurare F3 ora (anziché versione vettoriale) segue il principio scope minimo già usato per F1/F2: prima funzione scalare pura testata in isolamento, poi versione `vgp/` su DataFrame di sessione. Versione scalare utile per:
- pipeline di rollup di fine sessione (somma profitti chiusi → budget T+1);
- debug singolo step di sessione;
- test parametrici di scenari multi-sessione (chained T+1, T+2, ...).

### Decisioni di design

1. **`Iterable[float]` invece di `list[float]`**: accetta qualsiasi iterabile (lista, tuple, generator, comprehension). Idiomatic Python, evita il fix collection-type al call site.
2. **Niente raise sui valori**: F3 è una somma — matematicamente sempre lecita. Budget negativo è una **continuità del compounding** (sessione fortemente in perdita erode il budget oltre zero). Pattern coerente con F1 (output negativo by design) e F2 (`cash_profit` può essere negativo). I gate sono altrove: il Veto R-08 a livello scalare, e il sizing del Tetris a livello di sessione.
3. **Lista vuota → `Budget_T+1 = Budget_T`**: somma vuota = 0, identità di `Budget_T`. Coerente: una sessione senza alcun profitto registrato non altera il budget.
4. **Output `float`**: niente `Decimal` per ora — coerente con F1/F2/ROI scalari. Tolerance management è scope test (snapshot 1e-3 EUR).
5. **Niente parametro `tax_rate` / scorpori**: R-07 è esplicita ("100% del bonifico Amazon è capitale reinvestibile"). L'IVA è già zero per Reverse Charge + credito infinito (PROJECT-RAW). F3 prende l'output di F2 verbatim, non lo trasforma.
6. **Nome `compounding_t1`** (non `budget_t1`): il nome documenta l'**operazione** (compounding step) più della grandezza ritornata. Convenzione coerente con `cash_inflow_eur`, `cash_profit_eur` (sostantivi descrittivi della grandezza calcolata), però qui prevale il termine R-07 verbatim ("compounding"). Boundary case di naming, accettato.

### Versione vettoriale fuori scope

Lo scenario realistico in produzione è "fine sessione → calcola Budget_T+1 da DataFrame di N risultati". Quella sarà `vgp/compounding.py` o `vgp/rollup.py` futuro su DataFrame Numpy/pandas. La scalare di questo CHG è il building block: la vettoriale può essere implementata come `compounding_t1(budget_t, df['cash_profit'].tolist())` o equivalente.

## How

### `src/talos/formulas/compounding.py`

```python
from __future__ import annotations
from typing import Iterable


def compounding_t1(budget_t: float, cash_profits: Iterable[float]) -> float:
    """F3 verbatim: Budget_T+1 = Budget_T + Somma(Cash_Profit).

    >>> compounding_t1(1000.0, [50.0, 30.0, -10.0])
    1070.0
    >>> compounding_t1(1000.0, [])
    1000.0
    """
    return budget_t + sum(cash_profits)
```

### Test plan (9 test)

1. `test_snapshot_mixed_profits` → `compounding_t1(1000.0, [50.0, 30.0, -10.0]) == 1070.0`
2. `test_empty_iterable_returns_budget_t` → `compounding_t1(1000.0, []) == 1000.0`
3. `test_only_positive_profits` → `compounding_t1(0.0, [100.0, 200.0, 50.0]) == 350.0`
4. `test_only_negative_profits` → `compounding_t1(500.0, [-200.0, -100.0]) == 200.0`
5. `test_negative_budget_t1_when_losses_exceed_budget` → `compounding_t1(100.0, [-150.0]) == -50.0`
6. `test_accepts_generator` → `compounding_t1(0.0, (x for x in [10.0, 20.0])) == 30.0`
7. `test_single_profit` → `compounding_t1(100.0, [50.0]) == 150.0`
8. `test_zero_budget_zero_profits` → `compounding_t1(0.0, []) == 0.0`
9. `test_consumes_iterable_once` → un generator dato in input deve essere consumato e funzionare (no double iteration)

### Out-of-scope

- **Versione vettoriale** (DataFrame): scope futuro `vgp/`.
- **Persistenza budget T+1**: scope futuro orchestratore di sessione (legge/scrive da `sessions` table).
- **Property-based test**: scope futuro se emergeranno invarianti utili (es. associatività della somma).
- **Test di catena F1→F2→F3**: la sentinella e2e (CHG-028) può essere estesa; scope separato.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (30 source files) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~235 PASS (226 + 9) |

**Rischi residui:**

- F3 in produzione richiede coerenza con il modello dati: `cash_profits` deve essere il `cash_profit` di **tutte le righe chiuse della sessione T** (incluso il "carrello Tetris" eseguito). Se il caller passa solo le righe non vetate o solo il top-VGP, il Budget_T+1 sarà inflato. Mitigazione: documentazione e contract test al primo orchestratore di sessione (scope futuro).
- Niente Decimal — accumulazione di errori float possibile su sessioni con migliaia di righe. Caso d'uso reale Talos: ~100-500 ASIN/sessione, errore < 1 cent. Accettabile. Migrazione a Decimal futura se emerge esigenza.
- `compounding_t1` non valida che `budget_t >= 0` di default — un budget negativo può essere passato e la funzione lo accetta (continuità). È un comportamento *deliberato* (vedere "Decisioni di design"), ma il caller deve sapere che non c'è gating.

## Refs

- ADR: ADR-0018 (algoritmo VGP/Tetris — F3 verbatim PROJECT-RAW), ADR-0014 (mypy/ruff strict), ADR-0013 (struttura `formulas/`), ADR-0019 (test pattern unit)
- Predecessori: CHG-2026-04-30-025 (F1 `cash_inflow_eur`), CHG-2026-04-30-026 (F2 `cash_profit_eur` + `roi`)
- Vision verbatim: PROJECT-RAW.md riga 280 (`Budget_T+1 = Budget_T + Somma(Cash_Profit)`) + R-07 riga 225 ("100% del bonifico Amazon è capitale reinvestibile")
- Successore atteso: estensione sentinella e2e con F3 (rollup di sessione); versione vettoriale `vgp/`; orchestratore di sessione che persiste `Budget_T+1`; eventuale `milestone/first-formula-v1.0.0` (catena scalare F1→F2→F3 + ROI + Veto chiusa)
- Commit: `eb04afb`
