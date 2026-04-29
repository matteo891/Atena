# ROADMAP

Tracker operativo del progetto. Ogni voce deve essere tracciabile a un ADR validato e ratificato dal Leader.

> **Regola vincolante:** Nessuna modifica architetturale viene registrata in questo documento prima di essere stata ratificata dal Leader come ADR in `docs/decisions/`. La validazione GitNexus è opzionale fintanto che ISS-001 è aperta (vedi STATUS.md).

---

## Obiettivi Attuali

| # | Obiettivo | ADR di riferimento | Stato |
|---|-----------|-------------------|-------|
| 1 | Inizializzazione infrastruttura dogmatica | — | Completato |
| 2 | Promulgazione ADR fondativi (0001–0004) | ADR-0001–0004 | Completato |
| 3 | Promulgazione ADR enforcement + anti-allucinazione (0005–0008) | ADR-0005–0008 | Completato |
| 4 | Hardening governance v0.5.0 — fix audit (B1–B5, M1–M9, P1–P3) | ADR-0009, ADR-0010, ADR-0011 | Completato (commit `416ab87`) |
| 5 | Verdetto: sistema governance a prova di bomba per fase pre-codice | tutti 0001–0011 | Confermato — sistema in produzione |
| 6 | Vision capture protocol — ADR-0012 + PROJECT-RAW.md template `Draft` | ADR-0012 | Completato (CHG-2026-04-29-003) |
| 7 | Esposizione bozza dal Leader → riempimento PROJECT-RAW.md `Draft → Iterating` | ADR-0012 | Round 1+2+3+4 (CHG-004/005/006/007). 17 aperte, **0 critiche**. Manca solo lo sweep importanti+forma per il Frozen |
| 8 | `Frozen` PROJECT-RAW.md → proposta scomposizione (Claude) → validazione Leader → ADR di stack | ADR-0012, ADR di stack da promulgare | Sbloccabile appena lo sweep importanti+forma di #7 è completato |
| 9 | Fork repo su PC operativo Leader + verifica `gitnexus analyze` (ISS-001) | ADR-0007 | Rinviato — bloccato da setup PC operativo |
| 10 | Prima linea di codice applicativo | ADR di stack (da promulgare) | Bloccante: dipende da #8 |

---

## Implementazioni in Corso

_Nessuna implementazione di codice attiva al momento. Sessione 2026-04-29: hardening governance — in attesa approvazione Leader per il commit di chiusura._

---

## Meta-Blocchi Futuri

_Decisioni architetturali future da discutere e formalizzare tramite ADR prima dell'implementazione._

| # | Tema | ADR necessario | Note |
|---|------|---------------|------|
| A | Stack tecnologico | Da promulgare | Da definire dal Leader, popolato dalla scomposizione del PROJECT-RAW Frozen (ADR-0012) |
| B | Struttura directory codice applicativo | Da promulgare | Dipende dallo stack |
| C | CI/CD pipeline | Da promulgare | Dipende dallo stack |
| D | Branch policy v2 (multi-branch / PR / branch protection) | Da promulgare | Rinviata da ADR-0011; rivedere all'introduzione del primo modulo applicativo |
| E | GitNexus operativo da PC del Leader | ADR-0007 (esistente, in attesa) | Eseguire `gitnexus analyze` post-fork |
| F | Task operativi derivati dal PROJECT-RAW Frozen | Da promulgare individualmente | Popolati post-step [7] della pipeline ADR-0012 |

---

## Log delle Validazioni

| Data | Modifica | ADR | Validato da |
|------|----------|-----|-------------|
| 2026-04-29 | Inizializzazione infrastruttura | — | Leader |
| 2026-04-29 | Promulgazione ADR fondativi 0001–0004 + protocolli operativi | ADR-0001–0004 | Leader |
| 2026-04-29 | Promulgazione ADR 0005–0008 + git hooks + enforcement + anti-allucinazione | ADR-0005–0008 | Leader |
| 2026-04-29 | Hardening governance v0.5.0 — ADR-0009/0010/0011 + errata + hardening patch + hook rinforzati | ADR-0009, ADR-0010, ADR-0011 | Leader (CHG-2026-04-29-002, commit `416ab87`) |
| 2026-04-29 | Vision capture protocol — ADR-0012 + PROJECT-RAW.md template Draft | ADR-0012 | Leader (CHG-2026-04-29-003) |
| 2026-04-29 | TALOS — prima esposizione bozza, trascrizione verbatim, 24 lacune (Iterating Round 1) | ADR-0012 | Leader (CHG-2026-04-29-004) |
| 2026-04-29 | TALOS — Round 2 Q&A: chiuse 6 critiche (Tesseract, scraping, Keepa primario, Referral lookup+override, criteri completamento, Samsung-only modulare); aperta L11b. 19 aperte (2 critiche residue) | ADR-0012 | Leader (CHG-2026-04-29-005) |
| 2026-04-29 | TALOS — Round 3 Q&A: chiuse L04 (formula VGP) + L21 (Keepa out-of-scope); aperta L04b critica (normalizzazione scale). 18 aperte (1 critica). Direttiva concisione registrata come memory | ADR-0012 | Leader (CHG-2026-04-29-006) |
| 2026-04-29 | TALOS — Round 4 Q&A: chiusa L04b (normalizzazione min-max [0,1] dei tre termini VGP). 17 aperte, **0 critiche residue**. Vision pronta per sweep finale → Frozen | ADR-0012 | Leader (CHG-2026-04-29-007) |
