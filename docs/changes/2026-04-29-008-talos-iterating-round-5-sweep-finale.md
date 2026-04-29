---
id: CHG-2026-04-29-008
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Pending
commit: <pending>
adr_ref: ADR-0012
---

## What

Round 5 Q&A su `PROJECT-RAW.md` (TALOS) — **sweep finale**. Tutte le 17 lacune residue dell'Iterating sono state chiuse in un singolo blocco di risposte del Leader.

**Decisioni del Round 5:**

| # | Lacuna | Decisione |
|---|---|---|
| L01 | Stateless vs Storico/Panchina | Default confermato — Stateless = analisi di sessione senza dipendenze causali da sessioni precedenti; Storico/Panchina = archivio/lookup |
| L02 | Capitale `x` di partenza | **Opzione (a) — Budget di sessione** (precisato dal Leader): capitale fisicamente disponibile per la singola run del bot, fornito dall'utente (R-02). Non è il capitale teorico totale |
| L03 | Output commercialista | Default confermato — niente automatico, solo storico interno consultabile |
| L05 | Slider Velocity Target | Default confermato — range 7–30 gg, default 15, granularità 1 giorno |
| L07 | NLP vs Estrattore | Default confermato — un solo modulo `SamsungExtractor` con Filtro Kill-Switch come fase finale di validazione (Match Sicuro) |
| L09 | Refuso "Veto ROI (R-09)" | Default confermato — Veto ROI = R-08; refuso corretto inline in sez. 4.1.9 |
| L09b | Refuso "Tetris (R-07)" | Default confermato — Tetris = R-06; tabella già coerente, nessun edit residuo necessario |
| L10 | Soglia Veto ROI 8% | Default confermato — configurabile dal cruscotto, default 8%, persistita come config |
| **L11b** | **Formula manuale Fee_FBA** | **Fornita verbatim dal Leader** (vedi sezione How) — incisa in sez. 6.3 Formula 1 |
| L13 | Manual Override (R-04) UI | Default confermato — pulsante Lock-in + tabella ASIN locked_in modificabile + Priorità=∞ nel Tetris |
| L14 | Streamlit vs Gradio | **Streamlit** (precisato dal Leader): più solido per cruscotto gestionale interno con griglie/slider |
| L15 | PostgreSQL Zero-Trust | Default confermato — RLS + ruoli `talos_app`/`talos_admin` + no superuser nel pool app + audit log su tabelle critiche |
| L16 | Stack Python | Default confermato — SQLAlchemy 2.0 sync + Alembic + Playwright + Tesseract (oltre a pytest+ruff+mypy strict già fissati) |
| L17 | Rischi non tecnici (sez. 8.2) | Default confermato — 6 rischi inscritti con mitigazioni (ToS Amazon/fornitori, GDPR, single-vendor Keepa/JungleScout, Reverse Charge) |
| L19 | DOCS = `.docx`? | Default confermato — Microsoft Word `.docx` |
| L22 | Storico ordini | Default confermato — solo interno, alimentato dall'azione "ordina" |
| L24 | Rischi tecnici extra (sez. 8.1) | Default confermato — 5 rischi inscritti con mitigazioni (throttling Keepa, scraping breakage, OCR fail, ambiguità matcher, drift Keepa) |

**Conteggio finale lacune (cumulativo dei round 1–5):**

| Categoria | Originarie (Round 1) | Nuove emerse | Chiuse | Aperte residue |
|---|---|---|---|---|
| Critiche | 8 | +1 (L04b in R3) | 9 | 0 |
| Importanti | 12 | +1 (L11b in R2) | 13 | 0 |
| Forma | 4 | 0 | 4 | 0 |
| **Totale** | **24** | **+2** | **26** | **0** |

## Why

ADR-0012 step [3]–[4]: Iterating Round 5. Il Leader ha risposto a tutte le 17 domande del sweep in un singolo messaggio, accettando i default proposti da Claude tranne due precisazioni puntuali e fornendo la formula manuale richiesta da L11b.

**Pipeline ADR-0012 dopo Round 5:**
- Step [4] Sweep — completato.
- Step [5] Frozen — **NON automatico**. Richiede dichiarazione esplicita del Leader (*"dichiaro Frozen"* o equivalente). Claude non transitiona unilateralmente lo status del file da `Iterating` a `Frozen` anche con 0 lacune aperte: la disciplina anti-allucinazione (ADR-0008) e la regola "Lacune Mai Completate" (ADR-0012) impongono prudenza fino all'atto formale.

## How

### Risposta verbatim del Leader

> *"Ok ai default su tutta la linea, con queste due precisazioni per le domande senza default:
>
> 3. L02 Capitale di partenza: Opzione (a) - Intendo il budget di sessione (il capitale che ho fisicamente a disposizione per gli acquisti in quella specifica run del bot), non il capitale totale teorico.
>
> 9. L14 Interfaccia: Streamlit. Avendo a che fare con griglie di dati (gli ASIN), tabelle di comparazione e slider parametrici, Streamlit è molto più solido e indicato rispetto a Gradio per un cruscotto gestionale interno.
>
> Per tutto il resto (L01, L07, L05, L10, L13, L03, L22, L15, L16, L17, L24, L09, L09b, L19, L11b) confermo al 100% i tuoi default e le tue assunzioni.
>
> per quanto riguarda la formula, eccola: fee_fba = (((prezzo buy box/1,22-100)*0,0816)+7,14)*1,03+6,68"*

### Formula Fee_FBA inscritta (L11b)

```
fee_fba = (((prezzo_buy_box / 1.22) - 100) * 0.0816 + 7.14) * 1.03 + 6.68
```

Decomposizione (interpretazione di Claude, non vincolante per il calcolo che resta verbatim):
- `prezzo_buy_box / 1.22` → scorporo IVA 22%
- `... - 100` → soglia di applicazione della percentuale
- `... * 0.0816` → componente variabile (8.16%)
- `+ 7.14` → componente fissa intermedia
- `* 1.03` → margine 3%
- `+ 6.68` → componente fissa finale

Edge case noto: se `prezzo_buy_box / 1.22 < 100`, il termine `(p/1.22 - 100) * 0.0816` diventa negativo. Per smartphone Samsung (focus MVP) il BuyBox tipico è ben sopra la soglia, quindi non blocca il caso d'uso. Eventuali fasce di prezzo con comportamento diverso saranno tema di test fixture in fase implementativa, non di vision.

### Edit puntuali in `PROJECT-RAW.md`

- Frontmatter: `qa_rounds: 4 → 5`.
- Header: aggiunta riga Round 5 con conteggio finale 0/26 e nota su transizione Frozen pendente.
- Sezioni 1, 2, 3.2, 4.1.3, 4.1.5, 4.1.10, 4.3: marcate inline tutte le lacune chiuse con decisione finale.
- Sezione 4.1.9: refuso "Veto ROI (R-09)" corretto in "(R-08)" inline (chiusura L09).
- Sezione 6.1: chiusura L15 (Zero-Trust spec) e L16 (stack Python).
- Sezione 6.2: chiusure L09, L09b, L10, L13.
- Sezione 6.3 Formula 1: nuovo blocco L11b chiusa con formula verbatim del Leader, decomposizione, edge case, trigger del fallback.
- Sezione 6.4: chiusura L14 → Streamlit.
- Sezione 8.1: chiusura L24 con tabella rischi+mitigazioni inscritta.
- Sezione 8.2: chiusura L17 con tabella rischi+mitigazioni inscritta.
- Sezione 9: tabella Aperte vuotata (0 voci); tabella Chiuse aggiornata con tutte le 17 nuove decisioni in cima cronologico.
- Sezione 10: nuovo blocco Round 5 con risposta verbatim del Leader e tabella riassuntiva 5.01–5.17.
- Cronologia Stati: nuova riga Round 5.

### Aggiornamenti negli altri documenti

- `docs/STATUS.md`: header `Ultimo aggiornamento` (commit hash da backfillare), Stato in Una Riga (Iterating completato, in attesa Frozen), Appena Completato, In Sospeso (ESP-005 chiusa → ESP-006 aperta), tabella Decisioni ratificate ampliata, Nota al Prossimo Claude allineata, Issues Noti.
- `ROADMAP.md`: obiettivo #7 aggiornato (5 round, 0 aperte, in attesa Frozen), log validazioni esteso.
- `CHANGELOG.md`: nuova versione `[0.7.4]` in cima.

## Tests

Test manuali documentati (governance — ADR-0011).

| Test | Comando / Verifica | Esito |
|---|---|---|
| Frontmatter `qa_rounds: 5` | `grep '^qa_rounds:' PROJECT-RAW.md` | atteso PASS |
| Tutte le 17 lacune marcate "CHIUSA Round 5" | `grep -c 'CHIUSA Round 5' PROJECT-RAW.md` ≥ 17 | atteso PASS |
| Formula Fee_FBA verbatim presente | `grep -F 'fee_fba = (((prezzo_buy_box' PROJECT-RAW.md` | atteso PASS |
| L14 Streamlit confermato | `grep -F 'L14' PROJECT-RAW.md \| grep -c 'Streamlit'` ≥ 1 | atteso PASS |
| L02 Opzione (a) presente | `grep -F 'Opzione (a)' PROJECT-RAW.md` | atteso PASS |
| Refuso L09 corretto inline (R-08 in 4.1.9) | `grep -A1 'Plugin Panchina' PROJECT-RAW.md \| grep 'R-08'` | atteso PASS |
| Tabella Aperte vuota | `awk '/### Lacune Aperte/,/### Lacune Chiuse/' PROJECT-RAW.md \| grep -c 'L[0-9]'` = 0 | atteso PASS |
| Tabella Chiuse contiene tutte le 17 nuove + 9 storiche | conteggio righe tabella Chiuse | atteso PASS |
| Q&A Log Round 5 presente | `grep -c 'Round 5 — 2026-04-29' PROJECT-RAW.md` | atteso PASS |
| Cronologia Round 5 presente | `grep -c 'Round 5: sweep finale' PROJECT-RAW.md` | atteso PASS |
| Tabelle 8.1/8.2 popolate con rischi+mitigazioni | `grep -c '\| Mitigazione \|' PROJECT-RAW.md` ≥ 2 | atteso PASS |
| STATUS.md ESP-006 aperta | `grep 'ESP-006' docs/STATUS.md` | atteso PASS |
| ROADMAP log Round 5 + fork transition presenti | `grep -c 'Round 5\|matteo891/Atena' ROADMAP.md` ≥ 2 | atteso PASS |
| CHANGELOG `[0.7.4]` presente | `grep '\[0.7.4\]' CHANGELOG.md` | atteso PASS |

**Copertura:** verifica strutturale completa di Round 5. Validità delle decisioni (correttezza tecnica delle scelte di stack, formule, normalizzazione) sarà testata in fase di implementazione, sotto ADR di stack/algoritmo.

**Rischi residui:**
- Edge case formula Fee_FBA con BuyBox basso: non bloccante per MVP Samsung-only (BuyBox sempre alto). Da gestire con test fixture esplicito in fase implementativa.
- Eventuali ambiguità non emerse durante il sweep potranno emergere durante la scomposizione (step [6]) o in fase implementativa: la regola "Lacune Mai Completate" continua ad applicarsi anche post-Frozen (errata corrige + transizione documentata Iterating, ADR-0009).
- La transizione `Iterating → Frozen` è **un atto separato del Leader**: questo CHG documenta la chiusura del sweep, non il Frozen. Il prossimo CHG (probabilmente CHG-009) registrerà il Frozen quando il Leader lo dichiarerà esplicitamente.

## Refs

- ADR: ADR-0012
- Vision: `PROJECT-RAW.md`
- Predecessore: CHG-2026-04-29-007 (Round 4)
- Commit: `<pending>`
- Issue: ESP-005 (chiusa con questo CHG) → ESP-006 (transizione Frozen aperta)
