---
id: CHG-2026-04-30-026
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [da aggiornare post-commit]
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

**F2 Cash Profit + ROI**: terzo e quarto anello della catena del valore di Talos. Verbatim della Formula 2 (PROJECT-RAW.md sez. 6.3) + definizione ROI canonica (sez. 6.3 Formula VGP, riga "ROI_Percentuale — Rapporto tra utile e costo"):

```
Cash Profit = Cash Inflow − Costo_Fornitore        (F2)
ROI         = Cash Profit / Costo_Fornitore        (interpretazione standard FBA flipping)
```

ROI è il **gate** del Veto R-08 (soglia configurabile, default 8% — L10 chiusa Round 5). Questo CHG produce lo scalare ROI; il **veto** vero (gate `if roi < threshold: scarta`) è scope di un CHG separato che includerà soglia configurabile + telemetria evento canonico.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/formulas/cash_profit.py` | nuovo | `cash_profit_eur(cash_inflow_eur, costo_fornitore_eur) -> float` verbatim F2 + 1 validazione R-01 (`costo_fornitore_eur >= 0`) |
| `src/talos/formulas/roi.py` | nuovo | `roi(cash_profit_eur, costo_fornitore_eur) -> float` (frazione decimale) + 2 validazioni R-01 (`costo_fornitore_eur > 0` strict — division-by-zero proibita; negativi proibiti) |
| `src/talos/formulas/__init__.py` | modificato | Re-export `cash_profit_eur` + `roi` aggiunti a `__all__` |
| `tests/unit/test_cash_profit.py` | nuovo | 5 test (3 snapshot + boundary costo=0 + monotonia + raises negativo) |
| `tests/unit/test_roi.py` | nuovo | 8 test (3 snapshot + zero profit + negative ROI allowed + boundary 8% soglia veto + raises costo=0 + raises costo negativo) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Entry per `cash_profit.py` + `roi.py` → ADR-0018 + ADR-0019 |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; ~195 test PASS (182 + 13 nuovi).

## Why

CHG-022 ha scritto `fee_fba_manual` (isolato). CHG-025 ha collegato `fee_fba_manual → cash_inflow_eur`. Questo CHG estende la pila di altri due anelli:

```
fee_fba_manual ──┐
                 ▼
buy_box ────► cash_inflow_eur ────► cash_profit_eur ────► roi
referral_fee     (CHG-025)            (CHG-026 F2)         (CHG-026 ROI)
                                              ▲
                                  costo_fornitore (input config/UI)
```

Dopo questo CHG, la catena è **sufficiente** per:
1. **Veto R-08** (`roi < soglia` → scarta) — sblocca il primo filtro applicativo del Tetris.
2. **VGP score parziale** — due termini su tre (`norm(ROI) * 0.4 + norm(Cash_Profit) * 0.2`) sono calcolabili. Manca solo `norm(Velocity_Rotazione_Mensile)` che richiede F4/Q_m.
3. **`milestone/first-formula-v1.0.0`** diventa proponibile (scope futuro Leader).

### Decisioni di design

#### Cash Profit (F2)

1. **Funzione pura**, signature `cash_profit_eur(cash_inflow_eur, costo_fornitore_eur)`.
2. **`cash_inflow_eur` come scalar input, non calcolato qui.** Coerente con la separazione: F1 produce, F2 consuma. La composizione con `cash_inflow_eur` è onere del call site.
3. **`costo_fornitore_eur >= 0`**: lo zero è ammesso (campione gratuito dal fornitore = caso reale FBA). Negativo → `ValueError` R-01.
4. **`cash_inflow_eur` non validato per segno**: può essere qualsiasi float (è output di F1 che ammette negativi). Coerenza upstream.
5. **Output ammesso negativo** (vendita in perdita propaga). Stesso principio di F1.

#### ROI

1. **Funzione pura**, signature `roi(cash_profit_eur, costo_fornitore_eur)`.
2. **`costo_fornitore_eur > 0` strict**: lo zero è proibito (divisione per zero non ha significato matematico per "rapporto utile/costo"). Diversamente da F2 dove zero ha senso (campione gratuito → profit = inflow), qui è gate-out duro. R-01.
3. **Output frazione decimale, non percentuale**: `roi = 0.08` significa 8%. Convenzione esplicita nel docstring. Coerente con `referral_fee_rate` di CHG-025 (stesso dominio [0, 1] semanticamente, anche se ROI può sforare in entrambe le direzioni).
4. **ROI negativo ammesso**: ASIN che produce loss → `roi < 0`. Informazione necessaria per il Veto R-08 a valle (scartato dalla soglia 8% standard, ma il valore va calcolato e log-gato).
5. **`cash_profit_eur` non validato**: può essere qualsiasi float (output di F2).

#### Interpretazione ROI verbatim

Riga 343 PROJECT-RAW.md: *"ROI_Percentuale — Rapporto tra utile e costo (es. 0.15 per il 15%)"*. La definizione esplicita non c'è in PROJECT-RAW; la formula è inferita dalla convenzione **universale** del flipping FBA (`ROI = profit / cost-of-goods`). Mappatura:

- "utile" → `Cash_Profit` (F2): è l'utile netto post-fee.
- "costo" → `Costo_Fornitore`: è la spesa di acquisto, non altri costi (logistica, FBA fee — già scomputati in F1/F2).

Se questa interpretazione divergesse da quella attesa dal Leader, è materia di **Errata Corrige di ADR-0018** (non di questo CHG): la formula resterebbe `roi = profit / cost`, cambierebbe solo cosa entra come "cost" — al peggio si aggiunge un parametro `total_cost_eur` e la formula resta strutturalmente identica.

## How

### `src/talos/formulas/cash_profit.py`

```python
def cash_profit_eur(cash_inflow_eur: float, costo_fornitore_eur: float) -> float:
    if costo_fornitore_eur < 0: raise ValueError(...)
    return cash_inflow_eur - costo_fornitore_eur
```

### `src/talos/formulas/roi.py`

```python
def roi(cash_profit_eur: float, costo_fornitore_eur: float) -> float:
    if costo_fornitore_eur <= 0: raise ValueError(...)  # zero proibito (division-by-zero)
    return cash_profit_eur / costo_fornitore_eur
```

### Snapshot pre-calcolati

Composizione con CHG-025 (`cash_inflow_eur` snapshot):

| cash_inflow | costo | cash_profit | roi |
|---|---|---|---|
| 164.5922 | 100.00 | **64.5922** | **0.6459** |
| 384.9247 | 300.00 | **84.9247** | **0.2831** |
| 845.4788 | 600.00 | **245.4788** | **0.4091** |
| 200.0000 | 0.00 | **200.0000** | (ROI: ValueError) |
| 180.5922 | 200.00 | **−19.4078** | **−0.0970** (ROI negativo ammesso) |
| 8.00 (input diretto cash_profit) | 100.00 | — | **0.08** (boundary soglia veto R-08) |

Tolerance: 1e-3 (consistente con CHG-022/025); 1e-4 per ROI dove serve precisione frazionaria.

### Test plan

**`test_cash_profit.py` (5 test):**

1. `test_snapshot_low_value` → `(164.5922, 100.0) ≈ 64.5922`
2. `test_snapshot_mid_value` → `(384.9247, 300.0) ≈ 84.9247`
3. `test_snapshot_high_value` → `(845.4788, 600.0) ≈ 245.4788`
4. `test_zero_costo_fornitore_allowed` → `(200.0, 0.0) == 200.0` (campione gratuito)
5. `test_negative_cash_profit_allowed` → `(180.5922, 200.0) ≈ -19.4078`
6. `test_decreases_monotonically_with_costo` → 5 costi crescenti
7. `test_raises_on_negative_costo` → `(200, -1)` → ValueError

**`test_roi.py` (8 test):**

1. `test_snapshot_low_roi` → `(64.5922, 100.0) ≈ 0.6459`
2. `test_snapshot_mid_roi` → `(84.9247, 300.0) ≈ 0.2831`
3. `test_snapshot_high_roi` → `(245.4788, 600.0) ≈ 0.4091`
4. `test_zero_profit_yields_zero_roi` → `(0.0, 100.0) == 0.0`
5. `test_negative_roi_allowed` → `(-19.4078, 200.0) ≈ -0.0970` (loss propaga, no ValueError)
6. `test_boundary_at_eight_percent_threshold` → `(8.0, 100.0) ≈ 0.08` (soglia R-08 default)
7. `test_raises_on_zero_costo` → `(10.0, 0.0)` → ValueError "costo_fornitore_eur"
8. `test_raises_on_negative_costo` → `(10.0, -1.0)` → ValueError "costo_fornitore_eur"

Totale 7 + 8 = 15 nuovi test (non 13 come dichiarato sopra — riconto preciso post-edit).

### Out-of-scope

- **Veto R-08**: `if roi < threshold: scarta`. Soglia configurabile dal cruscotto (L10), default 8%. Scope futuro CHG, idealmente in `vgp/veto.py` o `formulas/veto.py` con telemetria evento canonico (R-01 + ADR-0021).
- **Versione vettoriale** Numpy/pandas (su listino di sessione): scope `vgp/normalize.py`.
- **F3 Compounding T+1** (`Budget_T+1 = Budget_T + Σ(Cash_Profit)`): scope futuro, accoppiato a Tetris allocator.
- **F4 Quantità Target a 15 giorni** (`Qty_Target = Q_m * 0.5`): scope futuro, accoppiato a Velocità + Q_m.
- **VGP score completo**: richiede F4/Q_m e Velocità (oggi mancanti).
- **`Decimal` per finanziario**: rinviata fino a evidenza di drift nei golden tests Samsung.
- **Errata di interpretazione ROI** se "costo" del Leader divergesse: scope ADR-0018, non questo CHG.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (24 source files) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~197 PASS (182 + 15 nuovi) |

**Rischi residui:**

- L'interpretazione "costo = Costo_Fornitore" è inferita, non verbatim. Se il Leader intende `costo = costo_fornitore + spese_logistiche + altri`, va aggiunta errata ADR-0018 + parametro aggiuntivo a `roi()`. La formula resta strutturalmente `profit / cost`.
- `costo_fornitore_eur=0` strict in ROI è scelta difendibile ma stretta: matematicamente la divisione per zero non ha senso, ma ci sono interpretazioni di "ROI infinito" per acquisti gratuiti rivenduti. La soglia R-08 8% comunque non gestirebbe quel caso. Decisione: ValueError esplicito > infinito implicito.
- Test snapshot tolerance 1e-3 può non bastare per ROI con costi grandi (es. 0.4091 con costo=600 → drift di 1e-6 EUR su cash_profit produce drift di ~1e-9 su ROI, dentro tolerance). Mitigazione: tolerance 1e-4 sui ROI.
- ROI è frazione decimale, non percentuale: errore "abbiamo 8% ma ottengo 0.08" è una trappola classica. Convenzione esplicita in docstring + esempio `0.15 = 15%` come ancora.

## Refs

- ADR: ADR-0018 (algoritmo VGP/Tetris — F2 + ROI per Veto R-08), ADR-0014 (mypy/ruff strict), ADR-0013 (struttura `formulas/`), ADR-0019 (test unit pattern)
- Predecessore: CHG-2026-04-30-025 (`cash_inflow_eur` — F1, secondo anello). Catena: F1 → F2 → ROI → R-08 (futuro).
- Vision verbatim: PROJECT-RAW.md sez. 6.3 Formula 2 + sez. 6.3 Formula VGP riga "ROI_Percentuale — Rapporto tra utile e costo (es. 0.15 per il 15%)"
- Successore atteso: Veto R-08 (gate funzionale + soglia configurabile + telemetria canonica) in CHG separato; oppure F4/Q_m + Velocità per chiudere il VGP score completo
- Commit: [da aggiornare post-commit]
