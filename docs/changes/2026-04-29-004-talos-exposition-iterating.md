---
id: CHG-2026-04-29-004
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Committed
commit: 44d53e7
adr_ref: ADR-0012
---

## What — Cosa è cambiato

Prima esposizione completa della vision di **TALOS (Scaler 500k)** da parte del Leader. Trascrizione verbatim integrale in `PROJECT-RAW.md` mappata sulle 11 sezioni del template ADR-0012, con sotto-sezioni 4.1.x, 6.x, 8.x per preservare la granularità della bozza originale. Status del file passato `Draft → Iterating`. Raccolte **24 lacune** (8 critiche, 12 importanti, 4 di forma — L09b conta separatamente da L09 perché entrambe sono refusi distinti nelle Leggi di Talos) in apparente violazione della dichiarazione del Leader ("Nessuna lacuna lasciata aperta"), giustificate dalla regola **"Lacune Mai Completate"** di ADR-0012.

**File modificato:**
- `PROJECT-RAW.md` — riscritto da template Draft a documento Iterating con contenuto reale.

**File aggiornati:**
- `docs/STATUS.md` — riflette lo stato Iterating del file vision.
- `ROADMAP.md` — obiettivo #7 in corso (Round 1 completato; Round 2 = chiusura lacune critiche, in attesa Leader).
- `CHANGELOG.md` — versione 0.7.0.

**File creati:**
- `docs/changes/2026-04-29-004-talos-exposition-iterating.md` — questo documento.

## Why — Perché

**ADR di riferimento:** [ADR-0012](../decisions/ADR-0012-project-vision-capture.md) — pipeline operativa step [1]–[2] (Leader espone → Claude scrive Draft → marca lacune).

**Motivazione del Leader.** Dopo aver autorizzato il restore point `milestone/vision-protocol-v0.6.0`, il Leader ha esposto la prima bozza completa di TALOS. Citazione verbatim del Leader: *"Nessuna lacuna lasciata aperta. Il dominio funzionale e matematico è stato definito con rigore assoluto."*

**Disciplina applicata da Claude.** ADR-0012 (regola "Lacune Mai Completate", vincolante e non negoziabile) impone di marcare ogni punto che richiede chiarimento, anche se il Leader lo ritiene chiaro. Claude ha rispettato il vincolo identificando 24 lacune. Le lacune **critiche** che bloccano qualsiasi MVP sono in particolare:

- **L04** — formula del **VGP Score** non definita (è il "monarca decisore" del sistema; senza formula il cuore di Talos non è specificabile)
- **L08** — lookup Amazon (scraping vs PA-API): scelta dello stack di networking + ToS Amazon
- **L11/L12** — sorgente di `Fee_FBA` e `Referral_Fee` nelle formule fiscali
- **L18** — tecnologia OCR/Vision per file non strutturati
- **L20** — traduzione misurabile del criterio "funziona senza errori"
- **L21** — Keepa: subscription, campi necessari, costi, rate limit
- **L06** — scope Samsung-only: solo MVP o permanente?

## How — Come

**Approccio tecnico (mappatura).**

Il Leader ha esposto 14+1 sezioni numerate (1-14, 16; sezione 15 saltata, marcata come LACUNA L17). Il template di PROJECT-RAW.md ha 11 sezioni fisse normate da ADR-0012. La mappatura applicata:

| Template (ADR-0012) | Bozza Leader |
|---|---|
| 1. Cosa è | 1 (verbatim) |
| 2. Perché | 2 |
| 3. Per chi | 3 (utenti) + 4 (stakeholder) come sotto-sezioni |
| 4. Cosa fa | 5 (funzionalità) + 6 (scenario) + 16 (Universal Ingestion) come 4.1/4.2/4.3 |
| 5. Cosa NON fa | 7 |
| 6. Vincoli e requisiti | 8 (tecnici) + 9 (Leggi R-01..R-09) + 10 (formule) + 11 (ambiente) come 6.1/6.2/6.3/6.4 |
| 7. Successo misurabile | 12 (criteri) + 13 (MVP) come 7.1/7.2 |
| 8. Rischi noti | 14 (tecnici) + [15 saltata, LACUNA L17] come 8.1/8.2 |
| 9. Lacune Aperte | 23 voci tabellate, ordinate per priorità |
| 10. Q&A Log | Round 1 registrato (esposizione iniziale + trascrizione) |
| 11. Refs | [da raccogliere — Keepa doc, dataset di esempio, riferimenti VGP] |

**Decisioni di trascrizione (maniacalità ADR-0012):**

- Le **citazioni verbatim** del Leader sono delimitate con `>` e marcate "Nota del Leader (verbatim)" per distinguerle da elaborazioni di Claude.
- Il **vocabolario** del Leader è preservato senza traduzione: "Hedge Fund algoritmico", "Compounding vettoriale", "VGP Score Monarchy", "Tetris", "Kill-Switch", "Velocity Target", "Reverse Charge", "Cash Drag", "Cash Inflow", "Stateless", "Just-in-Time", "Cruscotto militare", "Bin Packing", "Match Sicuro", "asimmetria benigna".
- Le **formule matematiche** sono incise testualmente in code blocks, mantenendo la divisione 4.A/4.B come dichiarata dal Leader.
- Le **Leggi R-01..R-09** sono tabellate fedelmente; due refusi numerici (L09, L09b) marcati come lacune di forma senza modifica del testo.

**Lacune marcate inline + indicizzate.** Ogni lacuna è marcata sia inline al punto di emergenza (es. dopo Fetch informazioni → L08+L21), sia raccolta nella sezione 9 "Lacune Aperte" con priorità, sezione di destinazione, round, status. La sezione 9 è il "registro vivo" su cui scendere a 0 prima del Frozen.

**Frontmatter aggiornato:**
```yaml
status: Iterating
qa_rounds: 1
codename: TALOS
tagline: Scaler 500k
```

## Tests

| Test | Tipo | Esito | Note |
|---|---|---|---|
| `PROJECT-RAW.md` ha frontmatter `status: Iterating` | Verifica strutturale (ADR-0011) | PASS atteso | grep |
| `qa_rounds: 1` aggiornato | Verifica strutturale | PASS atteso | grep |
| Tabella Lacune ha 24 voci (L01..L22 + L24 + L09b — L23 non assegnata) | Verifica strutturale | PASS atteso | grep + count |
| Codename TALOS presente nel frontmatter e titolo | Verifica strutturale | PASS atteso | grep |
| Q&A Log Round 1 presente | Verifica strutturale | PASS atteso | grep `Round 1 — 2026-04-29` |
| Cronologia Stati aggiornata | Verifica strutturale | PASS atteso | grep |
| Ogni "[LACUNA Lxx — ..." inline ha corrispondente entry in tabella sez. 9 | Verifica manuale | PASS — verificato in stesura | conteggio incrociato |
| Nessuna prosa inferita oltre alla trascrizione + lacune marcate | Verifica manuale | PASS — verificato in stesura | regola "Lacune Mai Completate" |

**Copertura stimata:** copre la trascrizione completa di Round 1. La validità delle lacune (cioè se il Leader le accetta come vere lacune) sarà verificata in Round 2.

**Rischi residui:**
- Il Leader potrebbe contestare alcune lacune (es. ritenere ovvio ciò che ho marcato come "forma"). In quel caso si chiudono nel Round 2 con risposta "non è una lacuna perché X" e si annota nel Q&A Log.
- La mappatura 14+1 → 11 sezioni potrebbe non riflettere perfettamente la priorità mentale del Leader. Modificabile via errata corrige (ADR-0009) o riallineamento in round successivi.

## Impact

- Il file di vision esiste come documento operativo e governato.
- Il Leader ha un'agenda di 23 punti per i prossimi round Q&A (priorità chiara: critiche prima).
- Il prossimo Claude che si briefa può immediatamente partire dal "stato della vision" senza ambiguità.
- L'MVP non è ancora specificabile finché L04 (formula VGP) non è chiusa — questo è il bottleneck dichiarato.
- ADR-0001 rispettato: nessuna decisione architetturale è stata presa; solo trascrizione + raccolta lacune. Le decisioni arriveranno post-Frozen via step [6]–[7] di ADR-0012.

## Refs

- ADR: [ADR-0012](../decisions/ADR-0012-project-vision-capture.md)
- Vision file: [PROJECT-RAW.md](../../PROJECT-RAW.md) (root)
- Commit: `44d53e7`
- Restore point precedente: tag `milestone/vision-protocol-v0.6.0` su `55ea55f`
- Issue / Task: ESP-001 (esposizione bozza) → in corso, non chiusa fino al Frozen
