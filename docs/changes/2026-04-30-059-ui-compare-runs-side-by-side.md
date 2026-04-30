---
id: CHG-2026-04-30-059
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Pending
commit: pending
adr_ref: ADR-0016, ADR-0014, ADR-0019
---

## What

Sostituisce il rendering "solo replay" del sub-expander "What-if
Re-allocate" (CHG-057) con un confronto side-by-side **originale vs
replay**. Il CFO vede subito quanto e' migliorato/peggiorato il
Cart rispetto al run salvato.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/dashboard.py` | modificato | + helper puro `compare_session_kpis(loaded, replayed) -> dict[str, dict[str, float]]` (testabile senza Streamlit). + `_render_compare_view(loaded, replayed)` due colonne con metric `Budget`, `Saturazione` (`delta` in punti percentuali), `Budget T+1` (originale = "—" perche' non persistito), `# Cart / Panchina` (`delta`). `_render_replay_what_if` ora riceve `LoadedSession` invece di `(session_id, original_budget)` e chiama `_render_compare_view` invece di `_render_replay_result`. `_render_replay_result` rimosso (sostituito). |
| `src/talos/ui/__init__.py` | modificato | + re-export `compare_session_kpis`. |
| `tests/unit/test_compare_session_kpis.py` | nuovo | 5 test puri (no Streamlit): output struttura due blocchi; saturation originale derivata da `cost_total / budget`; `budget_t1` originale NaN placeholder; replayed usa `Cart.budget`/`Cart.saturation`; budget=0 originale → saturation=0 no division-by-zero. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **494 PASS**
(394 unit/governance/golden + 100 integration).

## Why

CHG-057 mostrava SOLO il replay nuovo dopo il click "Re-allocate".
Il CFO doveva ricordare a memoria i KPI originali per fare il
confronto mentale → frizione UX.

Senza side-by-side:
- Differenze "non ovvie" (es. saturazione 75% vs 78%) sono invisibili
  al colpo d'occhio.
- Il valore del replay (sapere QUANTO e' diverso) non e' immediato.
- Decisioni su "il replay vale la pena" sono arbitrarie.

Con side-by-side + `delta` Streamlit:
- "Saturazione +5.2 pp" mostrato immediatamente.
- "Cart +3 item" mostrato immediatamente.
- Il valore del what-if e' tangibile.

### Decisioni di design

1. **Helper puro `compare_session_kpis`**: testabile senza Streamlit
   (necessario per tests/unit). Il render UI legge il dict.

2. **`budget_t1` originale = `NaN`**: il `LoadedSession` non ha
   `budget_t1` (CHG-052 nota out-of-scope: "non persistito"). NaN e'
   placeholder esplicito. Frontend rendera' "—" (`st.metric("...",
   "—")`). NaN vs `None`: NaN e' tipizzato `float`, evita union types
   nel return signature.

3. **Saturazione originale derivata da `cart_rows`**: il
   `LoadedSession` ha `cart_rows` con `cost_total` per ogni item.
   `sum(cost_total) / budget` (cap a 1.0) ricostruisce la
   saturazione senza modificare il modello DB.

4. **Streamlit `delta` parameter**: i KPI replayed mostrano `delta`
   relativo all'originale. Saturazione: punti percentuali (`pp`).
   Budget: differenza assoluta EUR. Cart count: int. Streamlit lo
   colora rosso (negativo) / verde (positivo) automaticamente.

5. **`isinstance(cost, (int, float))` invece di `float(row.get(...))`**:
   mypy strict si lamentava di `Generator has incompatible item type`
   con `dict[str, object]`. Il narrowing esplicito chiude il gap
   senza `# type: ignore`.

6. **`_render_replay_result` rimosso**: il nuovo `_render_compare_view`
   subsume il caso "solo replay" (basta non guardare la colonna
   originale). Niente codice morto.

7. **`LoadedSession` invece di `(session_id, original_budget)`**: il
   CHG-057 passava solo l'id; per il compare serve l'oggetto intero
   (cart_rows). Refactor di signature `_render_replay_what_if` —
   caller `_render_loaded_session_detail` aggiornato.

### Out-of-scope

- **Diff a livello ASIN** (cart originale ∩/∪/− cart replay):
  scope futuro UX power-user. Per ora confronto KPI aggregati.
- **Salvare il replay come nuova sessione**: bloccato da
  `upsert_session` decisione Leader.
- **Storico dei replay** ("hai esplorato 5 scenari"): scope futuro.
- **`SessionResult` per il vero "side-by-side panchina"**: il replay
  mostra solo Cart al confronto. Aggiungere panchina raddoppia
  il rumore visivo. Errata UX se richiesto.

## How

### `compare_session_kpis` (highlight)

```python
def compare_session_kpis(loaded, replayed):
    original_budget = float(loaded.summary.budget_eur)
    original_total = 0.0
    for row in loaded.cart_rows:
        cost = row.get("cost_total")
        if isinstance(cost, (int, float)):
            original_total += float(cost)
    original_saturation = (
        min(original_total / original_budget, 1.0) if original_budget > 0 else 0.0
    )
    return {
        "original": {
            "budget": original_budget,
            "saturation": original_saturation,
            "budget_t1": float("nan"),  # non persistito
            "cart_count": float(len(loaded.cart_rows)),
            "panchina_count": float(len(loaded.panchina_rows)),
        },
        "replayed": {
            "budget": float(replayed.cart.budget),
            "saturation": float(replayed.cart.saturation),
            "budget_t1": float(replayed.budget_t1),
            "cart_count": float(len(replayed.cart.items)),
            "panchina_count": float(len(replayed.panchina)),
        },
    }
```

### Test plan (5 unit)

1. `test_compare_returns_two_blocks` — struttura output
2. `test_compare_original_saturation_computed_from_cart_rows` —
   3000/5000 = 0.6
3. `test_compare_original_budget_t1_is_nan_placeholder` — NaN check
4. `test_compare_replayed_uses_replayed_budget_and_saturation` —
   1500/2000 = 0.75
5. `test_compare_zero_budget_original_saturation_zero` — no div/0

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 101 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **394 PASS** (389 + 5) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **100 PASS** (invariato) |

**Rischi residui:**
- **`budget_t1` originale come "—"**: non e' un valore mancante
  per bug, e' una limitazione architetturale (non persistito).
  Documentato nel docstring + caption UI futura.
- **Saturazione originale ricostruita**: dipende dalla coerenza tra
  `summary.budget_eur` e `sum(cart_rows.cost_total)`. Round-trip
  garantito da CHG-045 (test esistenti).
- **Streamlit `delta` con saturation negative**: se il replay ha
  saturazione < originale, il delta sara' negativo (rosso).
  Comportamento corretto MA un CFO potrebbe leggerlo come "peggio"
  quando in realta' un budget piu' alto causa saturazione piu' bassa
  by design. Caption UI scope futuro UX.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/dashboard.py` ✓.
- **Test unit sotto `tests/unit/`:** ✓ helper puro testabile (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `compare_session_kpis`
  + `_render_compare_view` mappano ad ADR-0016 (UI Streamlit).
- **Backward compat:** signature di `_render_replay_what_if`
  cambiata internamente; caller `_render_loaded_session_detail`
  aggiornato. Niente API pubblica (sono helper privati `_`).
- **Impact analysis pre-edit:** `_render_replay_what_if` 1 caller
  (`_render_loaded_session_detail`); risk LOW, modifica additiva.

## Impact

**Pattern UX "what-if comparison" attivo**: il CFO ora vede
immediatamente il delta tra scenario originale e replay. Coerente
con la cultura cruscotto militare (PROJECT-RAW: "griglie e slider").

`replay_session` (CHG-056) ha 2 consumer: programmatico (test) +
UI side-by-side (CHG-059). Pattern estendibile a confronti
"sessione A vs sessione B" (compare runs storici, scope futuro).

## Refs

- ADR: ADR-0016 (UI Streamlit), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test pattern unit).
- Predecessori: CHG-2026-04-30-052 (`load_session_full`),
  CHG-2026-04-30-056 (`replay_session`), CHG-2026-04-30-057 (UI
  consumer base), CHG-2026-04-30-058 (telemetria).
- Successore atteso: diff a livello ASIN (cart originale ∩/∪/−
  cart replay); compare runs storici (sessione A vs sessione B);
  storico replay (`session.replayed` aggregato).
- Commit: pending (backfill).
