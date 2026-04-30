---
id: ADR-0016
title: Stack UI — Streamlit + Caching Strategy
date: 2026-04-29
status: Active
deciders: Leader
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

L14 (Round 5) ha ratificato Streamlit (vs Gradio) per il "cruscotto militare" di TALOS. Streamlit ha rerun-completo a ogni interazione utente: senza una caching strategy esplicita, ogni mossa dello slider Velocity Target ricalcola l'intera pipeline VGP→Tetris su 10k righe → app inusabile.

Inoltre la natura idempotente delle operazioni di UI (acquisto, lock-in) deve essere protetta dal pattern di rerun: un click accidentale + rerun non-atteso non deve generare doppio inserimento in `storico_ordini`.

Mancano: layout pagine, strategia di cache (TTL), pattern di idempotency, theme.

## Decisione

### Layout pagine (`st.Page` multi-page)

```
src/talos/ui/
├── dashboard.py            # entrypoint Streamlit (st.navigation)
├── pages/
│   ├── analisi.py         # Sessione di analisi (input listino + budget + slider)
│   ├── storico.py         # Storico ordini (R-03)
│   ├── panchina.py        # Panchina (R-09)
│   └── config.py          # Configurazione (Veto ROI %, Referral_Fee categoria, etc.)
├── components/
│   ├── grid.py            # tabella ASIN + lock-in toggle (R-04)
│   ├── slider.py          # Velocity Target slider (L05)
│   └── carrello.py        # carrello finale + bottone "ordina"
└── state.py                # session_state schema + helpers
```

### Caching strategy

| Risorsa | Decoratore | TTL | Razionale |
|---|---|---|---|
| Fetch Keepa per ASIN | `@st.cache_data(ttl=600)` | 10 minuti | Default; fee/buybox cambia in ore |
| DB engine SQLAlchemy | `@st.cache_resource` | nessuno | Singleton di sessione |
| Lookup categoria → Referral_Fee | `@st.cache_data(ttl=86400)` | 24 ore | Cambia raramente |
| Pipeline VGP→Tetris su listino+budget+velocity | `@st.cache_data(ttl=300)` con hash di input | 5 minuti | Limita rerun-completi su listino di sessione |

**Override manuale (decisione Leader):** bottone **"Forza Aggiornamento"** nella pagina `analisi.py` che invoca `st.cache_data.clear()` selettivamente sui fetch Keepa. Permette al CFO di validare un acquisto critico all'istante senza attendere la scadenza TTL.

### Session state

`st.session_state` come unico contenitore per:
- `budget_eur` (input utente)
- `velocity_target` (slider, default 15)
- `listino_uploaded` (riferimento al file caricato)
- `current_session_id` (chiave DB della sessione attiva)
- `locked_in_set` (set di ASIN locked-in nella sessione corrente, prima del commit DB)

### Idempotency su side-effect

Tutte le operazioni write (commit listino, ordina, lock-in toggle) seguono il pattern:

```python
if st.button("Ordina"):
    idem_key = f"ordina-{session_id}-{listino_hash}"
    if idem_key not in st.session_state.completed_ops:
        execute_order(session_id)
        st.session_state.completed_ops.add(idem_key)
        st.success("Ordine registrato")
    else:
        st.info("Ordine già registrato in questa sessione")
```

### Theme

**Streamlit default + dark mode come default utente** (`.streamlit/config.toml`):

```toml
[theme]
base = "dark"
primaryColor = "#FF4B4B"
```

Niente CSS custom in MVP. Decisione Leader: "niente fronzoli per l'MVP".

### RLS bootstrap di sessione

A ogni avvio Streamlit (`@st.cache_resource get_db_session`):
```python
session.execute(text("SET LOCAL talos.tenant_id = '1'"))
```
Attiva RLS (ADR-0015) per la sessione di connessione DB. Single-tenant in MVP, predisposto per multi-tenancy.

## Conseguenze

**Positive:**
- Performance: caching dimezza il tempo di rerun su input invariati; slider Velocity Target diventa fluido.
- Bottone "Forza Aggiornamento" copre il caso d'uso operativo critico del CFO.
- Idempotency previene errori da double-click.

**Negative / costi:**
- Cache invalidation è complicata: bug "stale cache" possibili. Necessario test esplicito (vedi sotto).
- Streamlit non è production-grade per più utenti concorrenti: in MVP single-user accettabile, oltre va valutata alternativa (FastAPI + frontend separato).
- `session_state` non persiste tra refresh hard del browser: il CFO deve sapere che ricaricare la pagina perde lo stato di sessione non committato.

**Effetti collaterali noti:**
- I test per la UI Streamlit richiedono `streamlit testing` (introdotto in 1.28+). ADR-0019 prevede test minimi per i componenti critici (non test UI completi).

## Test di Conformità

1. **Smoke test:** `uv run streamlit run src/talos/ui/dashboard.py --server.headless true` deve avviarsi senza errore in CI.
2. **Cache TTL:** test `tests/integration/test_ui_cache.py` simula due fetch Keepa per stesso ASIN entro 10 min → deve esserci 1 sola invocazione del client.
3. **Forza Aggiornamento:** stesso test, ma con `st.cache_data.clear()` chiamato → 2 invocazioni.
4. **Idempotency:** doppio click "Ordina" produce 1 sola riga in `storico_ordini`.
5. **RLS bootstrap:** verifica che la sessione UI di Streamlit non possa leggere righe di altri tenant.

## Cross-References

- ADR correlati: ADR-0013 (struttura), ADR-0014 (linguaggio), ADR-0015 (DB + RLS), ADR-0017 (acquisizione: Keepa), ADR-0018 (algoritmo: pipeline VGP→Tetris)
- Governa: `src/talos/ui/`, `.streamlit/config.toml`
- Impatta: l'esperienza CFO; integrazione DB con RLS attiva
- Test: `tests/integration/test_ui_*`, `tests/unit/test_ui_state.py`
- Commits: `<pending>`

## Rollback

Se Streamlit si rivela inadeguato (es. esigenza multi-utente concorrente):
1. Promulgare ADR-NNNN con `supersedes: ADR-0016`.
2. Stack candidato: FastAPI + React/Vue separati (più complesso, più robusto).
3. Mantenere `src/talos/ui/` come adapter: il core algoritmo (`vgp/`, `tetris/`) è UI-agnostico.
4. Migrare le pagine progressivamente (analisi → storico → panchina → config).
