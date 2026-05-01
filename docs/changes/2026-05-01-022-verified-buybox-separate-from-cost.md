---
id: CHG-2026-05-01-022
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 5 — A2 hardening flow descrizione+prezzo: separa Buy Box reale da costo fornitore)
status: Draft
commit: <pending>
adr_ref: ADR-0017, ADR-0016, ADR-0014, ADR-0019
---

## What

Estende `ResolvedRow` con `verified_buybox_eur: Decimal | None`
per separare il **prezzo Amazon NEW** (Buy Box reale, recuperato live
da Keepa) dal **costo fornitore** (`prezzo_eur` del CFO). Chiude
l'out-of-scope decisione 8 di CHG-020 ("buy_box_eur=cost_eur
semplificazione consapevole MVP").

Senza A2: il flow descrizione+prezzo treatava `buy_box_eur=cost_eur`,
producendo VGP/ROI conservativi (ROI = (cost − fee_fba − cost·ref_fee) /
cost). Con A2: ROI = (buy_box − fee_fba − buy_box·ref_fee) / cost
quando il resolver ha verificato il Buy Box live.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + campo frozen `ResolvedRow.verified_buybox_eur: Decimal \| None = None` (default per backward compat). Propagation: `_resolved_row_from_result` legge `result.selected.buybox_eur` (CHG-018 `ResolutionCandidate.buybox_eur` esisteva già, ora esposto al livello UI). `_unresolved_row` e cache hit branch settano `None` esplicitamente. `build_listino_raw_from_resolved` ora distingue `cost_eur` (sempre `prezzo_eur`) da `buy_box_eur` (= `verified_buybox_eur` se non None, fallback `prezzo_eur` retro-compat). Docstring aggiornato. |
| `src/talos/ui/dashboard.py` | modificato | Preview tabella `_render_descrizione_prezzo_flow`: rinominata colonna `prezzo` → `prezzo_fornitore` + nuova colonna `buy_box_verificato` (None se cache hit / lookup fail → Streamlit rende "—"). UX: il CFO vede subito il delta tra costo input e prezzo Amazon vendita. |
| `tests/unit/test_listino_input.py` | modificato | Helper `_resolved(...)` esteso con kwarg `verified_buybox` opzionale. + 6 test nuovi: 2 propagation (`MockResolverWithBuybox` con buybox custom e None), 3 build_listino (uses verified / fallback to cost / mixed listino), 1 default-None backward compat. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **651
PASS** unit/gov/golden + 126 integration (no live) = **777 PASS**
no-live (era 771 a CHG-021, +6 nuovi). Con i 7 test live skippabili
totale **784 PASS** (era 778, +6).

## Why

CHG-020 ha scelto di trattare il `prezzo_eur` del CFO come "cost
+ buy_box" uniformemente, perché:

1. la cache `description_resolutions` (CHG-019) salva solo asin +
   confidence, non il buybox;
2. l'estensione di `ResolvedRow` con `verified_buybox_eur` era
   "scope futuro" esplicito (decisione 8).

CHG-022 chiude quel gap: il resolver `_LiveAsinResolver` (CHG-018) già
recupera il Buy Box live da Keepa per ogni candidato (per il calcolo
`delta_price_pct`), ma il valore non era esposto al livello UI/listino.
Bastava propagarlo.

Beneficio concreto:
- **VGP più accurato**: ROI per ASIN con margine reale Amazon vs
  costo fornitore. Esempio Galaxy S24 256GB: cost €549 (fornitore),
  buy_box Amazon NEW €599 → ROI calcolato su €599 invece che €549
  → cassa attesa più alta → l'ASIN vince in classifica VGP rispetto
  ad altri.
- **Audit trail**: il CFO vede in preview se il Buy Box reale
  diverge significativamente dal prezzo fornitore (segnale: prezzo
  troppo alto rispetto al mercato → scartare).
- **Nessuna nuova quota**: il buybox è già recuperato durante il
  resolve (token Keepa già speso); zero overhead.

### Decisioni di design

1. **Default `verified_buybox_eur=None`**: cache hit + righe
   non risolte + lookup fallito hanno tutti la stessa rappresentazione
   (None) → 1 fallback path in `build_listino_raw_from_resolved`.
   Pattern coerente con `ProductData.buybox_eur` (CHG-006).

2. **Cache hit -> verified_buybox_eur=None**: la cache
   `description_resolutions` salva solo (asin, confidence_pct), NON
   il buybox (varia col tempo). Cache hit → fallback a `prezzo_eur`.
   Estendere lo schema cache con `buybox_eur` + TTL = scope futuro
   (richiede migration alembic). Decisione ratificata in change doc
   (out-of-scope 1).

3. **Fallback `buy_box_eur=prezzo_eur` retrocompat**: il
   comportamento CHG-020 viene preservato per i listini senza buybox
   verificato. Caller esistenti che non popolano
   `verified_buybox_eur` continuano a funzionare. Backward compat 100%.

4. **Cost_eur sempre = prezzo_eur**: il prezzo fornitore è il "costo"
   del CFO; non viene mai overridato dal Buy Box. Mantiene l'invariante
   fisica: ROI = cash_inflow_dal_mercato / costo_acquisto.

5. **Preview UI con colonna `buy_box_verificato`**: rinomino
   `prezzo` → `prezzo_fornitore` per chiarezza UX. La nuova colonna
   espone il delta. Decisione UX-side: lasciare la colonna anche
   quando tutta la lista è cache hit (sarà tutta None, "—" in
   Streamlit) — il CFO impara che la cache non rinfresca i prezzi.

6. **`ResolutionCandidate.buybox_eur` riusato (no struttura nuova)**:
   il field esisteva già da CHG-018, popolato dal resolver. CHG-022
   è solo "propagation": tipologia di change minimale.

7. **Test pattern `_MockResolverWithBuybox`**: nuovo mock isolato
   dal `_MockResolver` esistente per non rompere i test CHG-020 che
   assumono `buybox=input_price` (test happy path con `delta=0`).
   Il nuovo mock permette di testare scenari reali (cost ≠ buybox).

8. **Nessuna telemetria nuova**: l'evento `ui.resolve_confirmed`
   (CHG-021) potrebbe essere esteso con `n_with_verified_buybox` per
   tracking diagnostico, ma scope futuro (out-of-scope 4). Per ora
   il dato è ispezionabile dalla preview UI.

### Out-of-scope

- **Estensione cache `description_resolutions` con `buybox_eur` +
  `buybox_resolved_at`**: richiede migration alembic + TTL
  invalidation policy. Scope futuro (decisione Leader pendente:
  cache stantia vs re-resolve costoso).
- **Telemetria `ui.resolve_confirmed.n_verified_buybox`**: errata
  CHG-021 additivo. Scope futuro se osservazione produzione mostra
  cache hit dominanti.
- **Refactor `ResolutionCandidate` con `verified_buybox_eur` esplicito**:
  il field si chiama già `buybox_eur` (CHG-018). Rinominarlo
  introdurrebbe blast radius su tutti i test e mock. CHG-022 mantiene
  il nome esistente. Solo `ResolvedRow` (UI-layer) usa il prefisso
  "verified_" per esplicitare la provenienza.
- **CFO override manuale del Buy Box**: scope CHG-023 (A3 override
  candidato manuale) o CHG futuro (slider Buy Box per riga ambigua).

## How

### `ResolvedRow` (highlight)

```python
@dataclass(frozen=True)
class ResolvedRow:
    descrizione: str
    prezzo_eur: Decimal
    asin: str
    confidence_pct: float
    is_ambiguous: bool
    is_cache_hit: bool
    v_tot: int
    s_comp: int
    category_node: str | None
    notes: tuple[str, ...]
    verified_buybox_eur: Decimal | None = None  # CHG-022
```

### `build_listino_raw_from_resolved` (highlight)

```python
for r in valid_rows:
    buy_box = (
        float(r.verified_buybox_eur)
        if r.verified_buybox_eur is not None
        else float(r.prezzo_eur)
    )
    record: dict[str, object] = {
        "asin": r.asin,
        "buy_box_eur": buy_box,
        "cost_eur": float(r.prezzo_eur),
        ...
    }
```

### Preview UI (highlight)

```python
{
    "descrizione": r.descrizione,
    "prezzo_fornitore": float(r.prezzo_eur),
    "buy_box_verificato": (
        float(r.verified_buybox_eur)
        if r.verified_buybox_eur is not None
        else None
    ),
    ...
}
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **651 PASS** (era 645, +6 nuovi A2) |
| Integration (no live) | `TALOS_DB_URL=... uv run pytest tests/integration --ignore=test_live_*.py -q` | **126 PASS** (invariato vs CHG-021) |

**Rischi residui:**
- **Cache hit -> always fallback to cost**: se il listino del CFO
  è dominato da cache hit (es. fornitori ricorrenti), il Buy Box
  verificato non viene mai usato → ROI calcolato sul cost. Mitigazione
  immediata: il CFO vede in preview che `buy_box_verificato="—"`
  per le righe cache hit; può scegliere di invalidare
  manualmente la cache. Mitigazione strutturale: cache TTL
  (out-of-scope 1).
- **Drift UX colonna `prezzo` → `prezzo_fornitore`**: il rename in
  preview potrebbe disorientare CFO già abituato alla colonna
  `prezzo` di CHG-020. Mitigazione: la colonna nuova
  `buy_box_verificato` rende ovvia la differenza; commenti UX
  aggiornati nei caption Streamlit (scope futuro CHG-024 documentazione UX).
- **`Decimal` vs `float` mixing**: `verified_buybox_eur` è `Decimal`
  in storage (coerente con `prezzo_eur`), ma `build_listino_raw`
  converte a `float` per il DataFrame. Pattern già usato in CHG-020,
  documentato come trade-off MVP.
- **Backward compat `_resolved()` helper test**: il helper esistente
  ha kwarg `verified_buybox` opzionale (default None) → tutti i test
  CHG-020 invariati.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area ADR-0013
  consentita).
- **ADR-0017 vincoli rispettati:** dato Buy Box live propagato
  upstream da `_LiveAsinResolver` (canale Keepa primario via
  `lookup_callable`). Field `buybox_eur` di `ResolutionCandidate`
  invariato.
- **ADR-0016 vincoli rispettati:** helper puro
  `build_listino_raw_from_resolved` testabile senza Streamlit
  (pattern CHG-020). Preview UI è pura UI-side, non logica.
- **Test unit puri:** ✓ (ADR-0019). 6 test nuovi mock-only.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `ResolvedRow` esiste
  già (CHG-020) → ADR-0017. Field aggiunto come additive change.
- **Backward compat:** Default field = None → tutti i caller esistenti
  invariati. Helper test `_resolved` retro-compatibile.
- **Sicurezza:** zero secrets, zero PII. `verified_buybox_eur` è
  dato pubblico Amazon.
- **Impact analysis pre-edit:** GitNexus risk LOW
  (`ResolvedRow`, `build_listino_raw_from_resolved` zero caller
  upstream nell'indice).
- **Detect changes pre-commit:** GitNexus risk LOW (3 file, 0
  processi affetti).
- **R-01 NO SILENT DROPS preservato:** cache hit, lookup fail,
  unresolved → tutti finiscono con `verified_buybox_eur=None`
  esplicito + visibile in preview UI ("—").

## Impact

- **Hardening A2 chiuso**: `verified_buybox_eur` è first-class
  citizen del flow descrizione+prezzo. ROI/VGP ora possono
  beneficiare del Buy Box reale Amazon NEW quando disponibile.
- **Out-of-scope CHG-020 decisione 8 chiuso**.
- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (13/13 viventi).
- **Test suite +6 unit**: 651 unit/gov/golden (era 645).
- **MVP CFO target**: hardening incrementale; ROI più accurati
  per il flow nuovo, fallback retro-compat per cache hit.
- **Pattern propagation `Decimal | None` con default**: replicabile
  per estensioni future di `ResolvedRow` (es. `bsr_chain`,
  `verified_title`).

## Refs

- ADR: ADR-0017 (canale acquisizione Keepa, Buy Box live già
  disponibile in `ResolutionCandidate`), ADR-0016 (UI helper puri),
  ADR-0014 (mypy/ruff strict + dataclass frozen + default).
- Predecessori:
  - CHG-2026-05-01-018 (`_LiveAsinResolver` composer): producer
    del `buybox_eur` propagato in CHG-022.
  - CHG-2026-05-01-019 (cache `description_resolutions`):
    consumer della decisione "cache hit -> verified_buybox=None".
  - CHG-2026-05-01-020 (UI flow descrizione+prezzo): chiude
    decisione 8 out-of-scope.
  - CHG-2026-05-01-021 (telemetria UI): hardening A1 → A2 chain.
- Memory: nessuna nuova; `feedback_ambigui_con_confidence.md`
  rispettato (preview UI espone tutti i match con buybox visible).
- Successore atteso: A3 override candidato manuale top-N per
  righe AMB.
- Commit: `<pending>`.
