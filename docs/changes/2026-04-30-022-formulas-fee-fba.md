---
id: CHG-2026-04-30-022
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Pending
commit: TBD
adr_ref: ADR-0018, ADR-0014, ADR-0013, ADR-0019
---

## What

**Prima formula applicativa di Talos**: `fee_fba_manual(buy_box_eur)` — implementazione **verbatim** della formula manuale Fee_FBA L11b chiusa nel Round 5 della esposizione vision (PROJECT-RAW.md sez. 6.3 Formula 1). Inaugura l'area `src/talos/formulas/` (vuota fino ad ora).

Funzione **pura** (no I/O, no DB, no env): può essere scritta senza dipendere da `config/` (CHG-023+) o da pool DB. È il **primo vertical slice di logica di prodotto**: prima di questo CHG, nessun file in `src/talos/` toccava il dominio Talos (tutto era infrastruttura).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/formulas/__init__.py` | nuovo | Package marker + re-export `fee_fba_manual` |
| `src/talos/formulas/fee_fba.py` | nuovo | `fee_fba_manual(buy_box_eur: float) -> float` verbatim L11b + ValueError R-01 NO SILENT DROPS |
| `tests/unit/test_fee_fba.py` | nuovo | Snapshot values + monotonia + edge case ValueError + boundary scorporato==100 |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Entry `src/talos/formulas/fee_fba.py` → ADR-0018 + ADR-0019 |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; ~170 test PASS (163 + ~7 nuovi).

## Why

L'esposizione TALOS Round 5 (CHG-2026-04-29-008) ha chiuso L11b con la **formula manuale Fee_FBA verbatim del Leader** (PROJECT-RAW.md):

```
fee_fba = (((prezzo_buy_box / 1.22) - 100) * 0.0816 + 7.14) * 1.03 + 6.68
```

Questa formula è il **fallback obbligatorio** se Keepa non espone Fee_FBA (rischio ToS Amazon o piano Keepa insufficiente — sez. 8.1 di PROJECT-RAW.md). È la base per F1 (Cash Inflow), che a sua volta alimenta F2 (Cash Profit) e ROI, che alimenta il VGP score, che alimenta il Tetris allocator.

In altre parole: **senza fee_fba, il VGP score è inattendibile**. Iniziare dalla formula più atomica e verbatim del Leader è la scelta di minor rischio per fissare il pattern del primo modulo applicativo.

L'edge case `scorporato < 100` solleva `ValueError` esplicito (NO SILENT DROPS, R-01) — decisione documentata in ADR-0018 e ratificata dal Leader come *"non blocca per Samsung MVP (sempre sopra)"*.

## How

### `src/talos/formulas/fee_fba.py`

Implementazione verbatim ADR-0018 (sez. "Edge case formula Fee_FBA L11b"), pulita per il quality gate:

```python
def fee_fba_manual(buy_box_eur: float) -> float:
    if buy_box_eur < 0:
        raise ValueError(...)
    scorporato = buy_box_eur / 1.22
    if scorporato < 100:
        raise ValueError(...)  # R-01 NO SILENT DROPS
    return ((scorporato - 100) * 0.0816 + 7.14) * 1.03 + 6.68
```

**Decisioni:**
- **`float`** (no `Decimal`): coerente con ADR-0018 esempio. Errore di arrotondamento su 4 operazioni resta < 0.01 EUR su valori realistici. Errata corrige ammessa se emergeranno problemi numerici.
- **Validazione difensiva esplicita** (R-01): nessun NaN/None/0 silenzioso ritorna; sempre `ValueError` con messaggio diagnostico.
- **`buy_box_eur` annotato `float`**: il call site passerà `Decimal` dai modelli ORM → cast a float esplicito al boundary. Coerenza zero-cost.
- **Soglia `scorporato < 100`** (non `≤`): `scorporato==100` produce `(0 * 0.0816 + 7.14) * 1.03 + 6.68 = 14.0342 EUR`, valore valido. La soglia stretta `<` è coerente con l'intent del Leader ("sopra 100 EUR netti").

### Snapshot values pre-calcolati (test)

| buy_box (EUR) | scorporato | fee_fba (EUR) |
|---|---|---|
| 122.00 | 100.00 (boundary) | 14.0342 |
| 200.00 | 163.93 | 19.4078 |
| 500.00 | 409.84 | 40.0753 |
| 1000.00 | 819.67 | 74.5212 |
| 121.99 | 99.99 | **ValueError** |
| 100.00 | 81.97 | **ValueError** |
| 0 | 0 | **ValueError** |
| -1 | n/a | **ValueError** |

I valori snapshot sono tolerance-based (1e-3 EUR) — fissano il **comportamento osservabile** della formula, non i bit floating-point.

### Test plan

7 test unit (`tests/unit/test_fee_fba.py`):
1. `test_snapshot_value_at_200_eur`: `fee_fba_manual(200.0) ≈ 19.4078` con tolerance 1e-3.
2. `test_snapshot_value_at_500_eur`: `40.0753`.
3. `test_snapshot_value_at_1000_eur`: `74.5212`.
4. `test_boundary_scorporato_exactly_100`: `buy_box=122.0` → `≈14.0342` (boundary inclusivo nel valid range).
5. `test_monotonicity`: `buy_box1 > buy_box2 ⇒ fee_fba1 > fee_fba2` su 5 valori.
6. `test_raises_when_scorporato_below_100`: `buy_box=121.99` → `ValueError` con messaggio che cita `scorporato`.
7. `test_raises_on_negative_buy_box`: `buy_box=-1` → `ValueError`.

Niente test parametrizzato pesante: la formula è semplice, snapshot bastano.

### Out-of-scope

- **Versione vettoriale (Numpy/pandas)** per il listino di sessione: F1 vettoriale è in scope di un futuro CHG (`vgp/normalize.py` o `formulas/cash_inflow.py`).
- **`Decimal` / arrotondamento finanziario** (Numeric(12,2)): valutazione di sensibilità in errata corrige se servirà.
- **Lookup primario via Keepa**: la formula manuale è il **fallback** (R-01). Lookup Keepa è scope `io_/keepa_client.py`.
- **F1, F2, F3, F4, F5**: prossime formule. Una al giorno con golden test.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (21 source files) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~170 PASS |

**Rischi residui:**
- Test snapshot fragili a precision changes (es. cambio di `1.22` → `1.220` da parte del Leader): mitigazione via tolerance 1e-3. Errata corrige di L11b dovrebbe aggiornare anche i test snapshot.
- `float` accumula errore su catene lunghe: per la **singola formula** è trascurabile. Quando F1+F2+ROI+VGP saranno concatenate, va valutato se il drift entra in tolerance dei test golden Samsung. Decisione rinviata.
- Soglia `scorporato < 100` (stretta): se in futuro emergesse un caso BuyBox=121.999... con scorporato 99.9991, si solleverebbe ValueError. Atteso (R-01: meglio fallire che produrre dati impliciti).

## Refs

- ADR: ADR-0018 (algoritmo VGP/Tetris — sez. "Edge case formula Fee_FBA L11b" è il riferimento implementativo), ADR-0014 (mypy/ruff strict), ADR-0013 (struttura `formulas/`), ADR-0019 (test unit pattern)
- Predecessore: CHG-2026-04-30-021 (DB bootstrap — chiude la fase infrastruttura DB; questo CHG inaugura la fase logica applicativa)
- Vision verbatim: PROJECT-RAW.md sez. 6.3 Formula 1 (L11b CHIUSA Round 5)
- Successore atteso: F1 `cash_inflow.py` (consuma `fee_fba` + buy_box + referral_fee)
- Commit: TBD (in attesa di permesso esplicito Leader)
