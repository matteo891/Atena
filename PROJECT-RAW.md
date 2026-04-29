---
status: Iterating
owner: Leader
started: 2026-04-29
last_iteration: 2026-04-29
frozen_at: —
qa_rounds: 5
codename: TALOS
tagline: Scaler 500k
---

# PROJECT-RAW — Vision del Progetto: TALOS (Scaler 500k)

> **Documento governato da [ADR-0012](docs/decisions/ADR-0012-project-vision-capture.md).**
> Status corrente: `Iterating` — il Leader ha esposto la prima bozza completa il 2026-04-29; trascrizione integrale + raccolta lacune in corso.
>
> **Nota del Leader (verbatim, 2026-04-29):** *"Nessuna lacuna lasciata aperta. Il dominio funzionale e matematico è stato definito con rigore assoluto."*
>
> **Nota di Claude (ADR-0012 regola "Lacune Mai Completate"):** rispettando la disciplina del documento, sono state comunque marcate **24 lacune o ambiguità** in Round 1 — alcune critiche (formula VGP non specificata; il "monarca decisore" del sistema), altre di forma (apparente refuso R-08 ↔ R-09; sezione 15 saltata). La regola obbliga a marcare anche lacune che il Leader può ritenere chiare: chiusura nei round Q&A successivi.
>
> **Round 2 (2026-04-29):** chiuse 6 lacune (L06, L08, L11, L12, L18, L20), aperta L11b condizionale.
> **Round 3 (2026-04-29):** chiuse L04 (formula VGP fornita), L21 (out-of-scope: piano Keepa è gestito esternamente dal Leader; Talos consuma le API). Aperta L04b (osservazione tecnica su normalizzazione delle scale nei termini della formula VGP). **18 lacune aperte** (1 critica: L04b).
> **Round 4 (2026-04-29):** chiusa L04b — il Leader decide di **normalizzare i tre termini su [0,1]** prima dei pesi 40/40/20 (*"tutti i dati devono pesare e collaborare"*). Nessuna critica residua: **17 lacune aperte** (0 critiche, 13 importanti, 4 di forma). Sweep importanti+forma → Frozen.
> **Round 5 (2026-04-29):** sweep finale completato. Chiuse tutte le 17 residue (default proposti da Claude accettati al 100% tranne L02 = Opzione (a) budget di sessione e L14 = Streamlit). Fornita anche la formula manuale Fee_FBA per L11b (non più condizionale, ma incisa). **0 lacune aperte. Vision matematicamente e architetturalmente specificata.** Pronta per dichiarazione esplicita di `Frozen` da parte del Leader.
>
> **Pipeline (ADR-0012):** Draft → **Iterating (qui, sweep completato)** → Frozen (in attesa dichiarazione esplicita Leader) → proposta scomposizione (in chat) → validazione Leader → ADR di stack + ROADMAP.

---

## 1. Cosa è

**Talos non è un software gestionale.** È un **Hedge Fund algoritmico automatizzato applicato al modello FBA Wholesale High-Ticket**.

È un **motore finanziario e di compounding vettoriale** che:
1. Acquisisce listini fornitori,
2. Li epura dai rischi hardware tramite NLP,
3. Calcola l'allocazione perfetta di un budget liquido.

**Natura strettamente Stateless:** il bot non ha memoria degli stati temporali o logistici (scaglionamenti); riceve un budget di sessione e un listino fresco, restituendo un'analisi **"Just-in-Time"** ottimizzata per il momento esatto dell'esecuzione.

> **[L01 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. "Stateless" si riferisce all'**analisi di sessione**: input = listino fresco + budget, nessuna dipendenza causale da sessioni precedenti. Storico Ordini e Panchina sono persistenze di **archivio/lookup**, mai input causale del calcolo VGP/Tetris.

---

## 2. Perché (Obiettivo di Business)

Per **scalare il capitale circolante da `x` (da definire) a 500k** annullando il **"Cash Drag"** e il **"Rischio Hardware"**.

L'essere umano non è in grado di calcolare a mente il **Bin Packing** su migliaia di referenze rispettando i vincoli logistici dei multipli di 5. La macchina sì.

> **[L02 — CHIUSA Round 5 (2026-04-29)]** — Risposta Leader: **Opzione (a) — Budget di sessione**. Il capitale `x` è il budget fisicamente disponibile per gli acquisti in **quella specifica run del bot**, non un capitale teorico totale. Implicazione MVP: il criterio di completamento si misura sull'output di una singola sessione (carrello generato + Panchina) a parità di listino e budget. Il valore numerico di `x` resta dinamico (R-02 BUDGET DINAMICO): è l'utente a fornirlo a ogni run.

---

## 3. Per chi

### 3.1 Utenti target

Un **singolo utente:** il **CFO/Hedge Fund Manager** dell'operazione e-commerce. L'interfaccia è un **"cruscotto militare"**.

### 3.2 Stakeholder

| Stakeholder | Cosa riceve |
|---|---|
| **L'Erario / Commercialista** | Riceve dati in **Reverse Charge senza che Talos generi XML**. |
| **Fornitori** | Ricevono **ordini logistici inattaccabili in multipli di 5**. |

> **[L03 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **Niente di automatico**: solo storico interno consultabile dall'utente (CFO). Coerente con out-of-scope fiscale (sezione 5). Implicazione: nessun export CSV/PDF/email programmato — la sincronizzazione con il commercialista resta **manuale e fuori da Talos**.

---

## 4. Cosa fa

### 4.1 Funzionalità chiave — Il Motore Fisico

#### 4.1.1 Fetch informazioni

Avviene tramite:
- **API di Keepa** (canale primario), oppure
- **Scansione di file JungleScout** in formato `csv` o `xlsx` (fallback).

Se si procede con il file di JungleScout, è necessario fare un **lookup del prodotto su Amazon** in base alla disponibilità mostrata nei listini fornitore somministrati.

> **[L08 — CHIUSA Round 2 (2026-04-29)]** — Decisione Leader: **scraping di amazon.it**. La libreria specifica (Selenium / Playwright / requests+BeautifulSoup) sarà oggetto di ADR di stack futuro. Implicazioni ToS Amazon da gestire (vedi anche L17 sui rischi non tecnici, sezione 8.2).

> **[L21 — CHIUSA Round 3 (2026-04-29)]** — Risposta Leader: il piano Keepa è **gestito esternamente** dal Leader, **out-of-scope per Talos**. Talos deve avere l'infrastruttura per usare le API Keepa ed estrarre ogni dato utile all'analisi; se un campo non è esposto dal piano corrente del Leader, il sistema fallisce con errore esplicito (R-01 NO SILENT DROPS) e il Leader sceglie se passare a piano superiore o attivare il fallback (es. L11b formula manuale Fee_FBA).

#### 4.1.2 Estrattore di entità (Regex specializzato)

Idea plausibile per ottenere sempre match perfetti:

> Un **"estrattore di entità"** (basato su espressioni regolari o Regex) **specializzato esclusivamente su smartphone Samsung**. Il suo compito è prendere una stringa di testo disordinata (come il titolo di un listino o di Amazon) e strutturarla in dati precisi.

**Cosa estrae:**
- modello base (es. `S24`, `Z FOLD`)
- spazio di archiviazione in GB/TB (supportando termini internazionali come `SPEICHER` o `GO`)
- RAM
- connettività (`4G` o `5G`)
- colore (normalizzandolo in macro-famiglie)
- versione **Enterprise** (sì/no)

**La validazione ("Match Sicuro"):** una funzione confronta i dati estratti dal fornitore con quelli di Amazon applicando regole di business severissime. Esempio: se la memoria (ROM) differisce, o se uno dei due lati non la specifica, il sistema **blocca il match definendolo "AMBIGUO"**.

**L'eccezione intelligente — Whitelist 5G:** include una whitelist di modelli nati nativamente come 5G (es. serie S22-S26 e Z Fold/Flip). Se il fornitore non scrive "5G" per un Galaxy S24, lo script sa che è un'omissione innocua (**asimmetria benigna**) e fa passare il match.

> **[L06 — CHIUSA Round 2 (2026-04-29) — Decisione delegata a Claude dal Leader: "quello che ti sembra meglio"]**
>
> **Decisione architetturale (ratificata dalla delega esplicita del Leader):**
> - **MVP Samsung-only:** l'estrattore opera **esclusivamente su smartphone Samsung** in MVP. I non-Samsung del listino sono scartati a monte con log esplicito (R-01 NO SILENT DROPS).
> - **Architettura modulare:** il modulo è progettato come una `BrandExtractor` interface astratta, con `SamsungExtractor` come unica implementazione concreta in MVP. Estensione futura via implementazioni `AppleExtractor`, `XiaomiExtractor`, `HuaweiExtractor` ecc. senza modifica della pipeline di matching/validazione.
> - **Razionale:** focus + scope ridotto + whitelist 5G già definita per Samsung; design del modulo a costo marginale aggiuntivo trascurabile vs versione monolitica; multi-brand in roadmap post-MVP non blocca l'MVP.

#### 4.1.3 Filtro NLP (Kill-Switch)

**Smembramento stringhe testuali per RAM / ROM / Rete / Edizione.**

> **[L07 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **Un solo modulo** (`SamsungExtractor`, da L06). Il "Filtro NLP Kill-Switch" è la **fase finale di validazione (Match Sicuro)** interna allo stesso modulo, che invoca **R-05 KILL-SWITCH HARDWARE** forzando VGP=0 in caso di mismatch. Architettura interna del modulo (pipeline): tokenize → estrai entità (modello/ROM/RAM/connettività/colore/Enterprise) → applica whitelist 5G → confronta lati fornitore/Amazon → emit "AMBIGUO" o "MATCH_SICURO" o "MISMATCH→VGP=0".

#### 4.1.4 VGP Score Monarchy (Calcolatore)

L'algoritmo di ranking è l'**unico ed esclusivo decisore**. L'analisi è **totalmente cieca**: ignora se un ASIN è un flagship o un accessorio; decide unicamente in base al **massimo coefficiente matematico di guadagno (VGP Score)**.

> **[L04 — CHIUSA Round 3 (2026-04-29)]** — formula VGP fornita dal Leader (vedi sezione 6.3 Formula VGP). Pesi: ROI 40% / Velocità 40% / Cash Profit 20%. **L04b CHIUSA Round 4 (2026-04-29)** — i tre termini sono normalizzati su [0,1] prima dei pesi.

#### 4.1.5 Reattività Vettoriale

Ricalcolo in tempo reale al mutare dello **slider Velocity Target**.

> **[L05 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. Lo slider Velocity Target è il controllo UI che modifica il numeratore della Formula 4 (`Qty_Target = Q_m * (Velocity / 30)`). **Range: 7–30 giorni. Default: 15** (allineato alla Formula 4 hardcoded). **Granularità: 1 giorno** (slider continuo a step 1). Allo spostamento dello slider il ricalcolo Reattivo Vettoriale (sez. 4.1.5) si propaga su tutto il VGP e sul Tetris.

#### 4.1.6 Allocatore Tetris

Funzione di saturazione del **budget di sessione**. Segue l'ordine decrescente di VGP per riempire il budget fornito dall'utente, **senza alcuna distinzione qualitativa tra i prodotti**. (Vedi R-06 per il dettaglio.)

#### 4.1.7 Formazione carrello

Generazione della lista della spesa sui criteri stabiliti. **Ogni ASIN di prodotto incasellato deve contenere un elemento ipertestuale cliccabile che punta direttamente alla rispettiva pagina prodotto su Amazon.it** (tramite ASIN). Scopo: debug per validazione manuale dei match e assegnazione dello stato di "match validato o meno".

#### 4.1.8 Esportatore Carrello

Generazione della lista della spesa **scaricabile, pronta per il fornitore**, se l'utente clicca il pulsante "ordina".

#### 4.1.9 Plugin Panchina (Archivio Opportunità)

Sezione di **stoccaggio dinamico** per ASIN validi ma non prioritari. Ogni articolo che:
- supera il **Kill-Switch hardware**
- supera il **Veto ROI (R-08)** (refuso del testo originale "R-09" corretto in Round 5 — vedi L09 chiusa)
- viene escluso dal carrello finale **per esaurimento del budget di sessione**

→ viene automaticamente archiviato qui.

La Panchina funge da **"lista d'attesa"** pronta per essere pescata in caso di aumento improvviso del budget o per la sessione di acquisto successiva.

#### 4.1.10 Storico ordini

I prodotti che hanno coinvolto ordini effettuati (messi in carrello, convalidati manualmente e poi esportati tramite pulsante "ordina") **non vanno dimenticati**. Sono memorizzati in una sezione apposita chiamata **"storico ordini"**, in una **lista a griglia** con i rispettivi:
- ASIN
- descrizione
- prezzo pagato
- quantità acquistate
- data

> **[L22 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. Lo Storico Ordini è alimentato **solo dall'azione "ordina" interna** a Talos (coerente con R-03 ORDER-DRIVEN MEMORY + natura Stateless). Nessuna sincronizzazione automatica da Amazon Seller Central. Ordini effettuati fuori da Talos (manuali, retroattivi) restano fuori dallo storico — è una scelta deliberata di scope MVP, non un bug.

### 4.2 Scenario d'uso primario

L'utente inserisce il listino e definisce il **Budget di Sessione** (es. 6.000€ per il primo scaglione logistico). Talos:
1. Analizza i dati di Keepa,
2. Ordina per **VGP Score**,
3. Applica la logica **Tetris** per saturare i resti,
4. Genera **due output distinti**:
   - **Il Carrello Definitivo** (saturato al 99.9%).
   - **La Panchina** (tutto il resto della selezione valida, ROI > 8%).

### 4.3 Modulo Universal Ingestion (Input Multi-formato)

Talos deve **annullare i tempi morti di inserimento dati**. L'interfaccia accetta listini in qualsiasi formato:

| Categoria | Formati | Logica |
|---|---|---|
| **Strutturati** | `XLSX`, `CSV` | Importazione diretta e immediata |
| **Non-strutturati** | `PDF`, `DOCS`, `TXT`, Immagini | Layer di estrazione intelligente (**OCR avanzato o Vision**) per ricostruire la tabella dati (ASIN, Titolo, Prezzo) e normalizzarla in un formato leggibile dal motore di calcolo prima di procedere con l'analisi VGP |

> **[L18 — CHIUSA Round 2 (2026-04-29)]** — Decisione Leader: **Tesseract locale**. Implicazioni: OCR open source, gratuito, dipendenza locale (no API esterne, no costi ricorrenti, no rate limit), qualità media — peggiore di GPT-4V/Claude V/Textract sui PDF deteriorati o scan a bassa risoluzione. Da gestire come rischio tecnico (vedi L24 e sezione 8.1).

> **[L19 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **`.docx` Microsoft Word**. Niente Google Docs export, niente Apple Pages.

---

## 5. Cosa NON fa (Out-of-Scope)

| Out-of-scope | Note |
|---|---|
| Gestione Contabile / Fiscale (Fatturazione SDI) | — |
| Sincronizzazione Multicanale (stile Linnworks) | — |
| Pre-Accounting (collegamento a conti bancari / QuickBooks) | — |

---

## 6. Vincoli e requisiti

### 6.1 Vincoli tecnici

| Vincolo | Specifica |
|---|---|
| **Linguaggio** | Python 3.10+, architettura modulare |
| **Database** | PostgreSQL (Zero-Trust) via Docker |
| **Governance** | Git Hooks e check `CLAUDE.md` obbligatori |

> **[L15 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **PostgreSQL "Zero-Trust" =** Row-Level Security attiva su tabelle sensibili + ruoli separati `talos_app` (CRUD) e `talos_admin` (DDL/migration) + nessun superuser nel pool applicativo + audit log su `storico_ordini`, `locked_in`, `config_overrides`. Specifica completa demandata all'ADR di stack DB.

> **[L16 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. Stack Python (oltre a pytest + ruff strict + mypy/pyright strict già fissati da L20): **SQLAlchemy 2.0 sync** (semplicità di test byte-exact > performance async per MVP); migrations con **Alembic**; HTTP/scraping Amazon con **Playwright** (resilienza moderna > Selenium); OCR **Tesseract** locale (già da L18). Dettaglio finale demandato a ADR di stack.

### 6.2 Le Leggi di Talos (Vincoli Business)

| ID | Nome | Regola |
|---|---|---|
| **R-01** | NO SILENT DROPS | Vietato usare `.drop()`; **ogni scarto deve essere loggato**. |
| **R-02** | BUDGET DINAMICO | Budget di sessione **sempre fornito dall'utente, mai hardcoded**. |
| **R-03** | ORDER-DRIVEN MEMORY | DB aggiornato **solo alla finalizzazione del carrello**. |
| **R-04** | MANUAL OVERRIDE | ASIN `locked_in` hanno **Priorità = ∞**. |
| **R-05** | KILL-SWITCH HARDWARE | Mismatch NLP **forza VGP a 0**. |
| **R-06** | TETRIS ALLOCATION | L'allocatore scorre la classifica VGP. Se un ASIN supera il budget residuo, prosegue (`continue`) cercando item con VGP inferiore ma costo compatibile, fino a saturare il budget di sessione al **99.9%**. |
| **R-07** | VAT CREDIT COMPOUNDING | **100% del bonifico Amazon è capitale reinvestibile.** |
| **R-08** | VETO ROI MINIMO | Nonostante la monarchia del VGP, viene applicato un **filtro di sbarramento assoluto**. Qualsiasi ASIN con un ROI stimato **inferiore all'8%** viene scartato a prescindere dal punteggio VGP. Protegge il capitale da oscillazioni di prezzo Amazon o fee impreviste, garantendo un margine di sicurezza minimo. |
| **R-09** | ARCHIVIAZIONE IN PANCHINA | Nessun ASIN con ROI ≥ 8% deve essere dimenticato. Al termine del ciclo di saturazione Tetris (R-06), il bot ha l'obbligo di generare un output secondario denominato **"Panchina"**. Questo file deve contenere tutti i prodotti idonei scartati unicamente per ragioni di **capienza finanziaria**, ordinati per VGP Score decrescente. |

> **[L09 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **Veto ROI = R-08** (refuso "R-09" del testo originale corretto inline in 4.1.9). Numerazione canonica delle Leggi: R-08 = VETO ROI MINIMO, R-09 = ARCHIVIAZIONE IN PANCHINA.

> **[L09b — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **Tetris = R-06** (refuso "Tetris (R-07)" del testo originale corretto al volo nella tabella di R-09 che già recita "Tetris (R-06)"; nessun edit residuo necessario). Numerazione canonica: R-06 = TETRIS ALLOCATION, R-07 = VAT CREDIT COMPOUNDING.

> **[L10 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **Soglia 8% configurabile dal cruscotto** con default 8%, persistita in DB come config (config layer, non transazione → R-03 non si applica). UI: campo numerico nel cruscotto militare con validazione (≥0, ≤100). Implementazione pratica demandata all'ADR di stack frontend.

> **[L13 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. **UI Manual Override:** pulsante "Lock-in" sull'ASIN nella griglia + tabella separata "ASIN locked_in" modificabile + persistenza DB. ASIN locked_in entrano nel Tetris con **Priorità=∞ prima** del normale ranking VGP, riservando il loro costo dal budget di sessione.

### 6.3 Formule Matematiche

> Nota del Leader (verbatim): *"Il budget di input per le analisi è dinamico e riferito alla singola sessione di acquisto. Non mi fido della memoria, quindi incido le formule nel documento raw."*

#### Formula 1 — Cash Inflow

```
Cash Inflow = BuyBox − Fee_FBA − (BuyBox * Referral_Fee)
```

**Nota del Leader:** *zero scorporo IVA per via del Reverse Charge + Credito infinito*.

> **[L11 — CHIUSA Round 2 (2026-04-29) — Risposta condizionale]** — Decisione Leader: **lookup primario da Keepa API**; se il campo non è disponibile/affidabile → **fallback a formula manuale** fornita dal Leader (vedi L11b chiusa).

> **[L11b — CHIUSA Round 5 (2026-04-29)]** — Formula manuale Fee_FBA fornita dal Leader (verbatim):
>
> ```
> fee_fba = (((prezzo_buy_box / 1.22) - 100) * 0.0816 + 7.14) * 1.03 + 6.68
> ```
>
> Decomposizione (interpretazione di Claude, non vincolante per il calcolo che resta verbatim):
> - `prezzo_buy_box / 1.22` → scorporo IVA 22%
> - `... - 100` → soglia di applicazione della percentuale variabile
> - `... * 0.0816` → componente variabile (8.16%)
> - `+ 7.14` → componente fissa intermedia
> - `* 1.03` → margine 3%
> - `+ 6.68` → componente fissa finale
>
> Edge case noto: se `prezzo_buy_box / 1.22 < 100`, il termine `(p/1.22 - 100) * 0.0816` diventa negativo. Per smartphone Samsung (focus MVP) il BuyBox tipico è ben sopra la soglia, quindi non blocca il caso d'uso. Eventuali fasce di prezzo con comportamento diverso saranno tema di test fixture in fase implementativa, non di vision.
>
> **Trigger del fallback:** la formula manuale si attiva se Keepa non espone `feeFBA` o equivalente nel piano subscription corrente del Leader. Logica primario→fallback (R-01 NO SILENT DROPS): tentativo Keepa → su miss/error → log esplicito + applica formula manuale.

> **[L12 — CHIUSA Round 2 (2026-04-29)]** — Decisione Leader: **sia lookup automatico per categoria sia override manuale configurabile dal cruscotto.** Strategia: lookup per nodo categoria Amazon come default (es. 8% per "Cell Phones & Accessories"); UI con campo override manuale per ASIN o per categoria, persistito in DB (R-03 ORDER-DRIVEN MEMORY non si applica perché è config, non transazione).

#### Formula 2 — Cash Profit

```
Cash Profit = Cash Inflow − Costo_Fornitore
```

#### Formula 3 — Compounding T+1

```
Budget_T+1 = Budget_T + Somma(Cash_Profit)
```

#### Formula 4 — Quantità Target a 15 giorni

```
Qty_Target = Q_m * (15 / 30)
```

> Nota del Leader: *"L'algoritmo non lavora su volumi generici, ma sulla capacità reale di assorbimento della BuyBox, limitando l'esposizione a una finestra di 15 giorni."*

##### Formula 4.A — Definizione della Quota Mensile (Q_m)

La Quota Mensile è la stima delle unità che spettano all'utente in base alla **concorrenza reale**. Non è il volume totale di Amazon, ma la "fetta di torta" competitiva.

| Variabile | Definizione |
|---|---|
| `V_tot` | Vendite totali mensili stimate per l'ASIN (Dati Keepa / BSR) |
| `S_comp` | Numero di venditori competitivi in BuyBox (entro il **2%** del prezzo minimo) |

```
Q_m = V_tot / (S_comp + 1)
```

> Nota del Leader: *"il +1 rappresenta l'ingresso dell'utente nella competizione."*

##### Formula 4.B — Target a 15 Giorni (Formula 4 modificata)

Talos **dimezza la Quota Mensile** per coprire esclusivamente un **Velocity Target di 15 giorni**, liberando l'altra metà del capitale per il Tetris.

#### Formula 5 — Quantità finale (lotti del fornitore)

```
Qty_Final = Floor(Qty_Target / 5) * 5
```

**Forzatura ai lotti del fornitore con arrotondamento sempre per difetto (Floor) per proteggere il cashflow.**

#### Formula MANCANTE — VGP Score

```
VGP = ???
```

**Formula VGP (chiusa Round 3 — risposta verbatim del Leader; normalizzazione chiusa Round 4):**

Forma canonica con normalizzazione preliminare dei tre termini:

```
VGP_Score = (norm(ROI_Percentuale) * 0.4)
          + (norm(Velocita_Rotazione_Mensile) * 0.4)
          + (norm(Cash_Profit_Assoluto) * 0.2)
```

dove `norm(x)` è la **normalizzazione min-max su [0,1] calcolata sul listino della sessione corrente**:

```
norm(x_i) = (x_i - min(x)) / (max(x) - min(x))
```

con `min(x)` e `max(x)` calcolati sull'insieme degli ASIN candidati della singola sessione di analisi (coerente con la natura Stateless di Talos: nessuna persistenza cross-sessione delle statistiche di normalizzazione).

Variabili:
- **ROI_Percentuale** — Rapporto tra utile e costo (es. `0.15` per il 15%). Peso 40% — *"garantisce la salute del capitale"*.
- **Velocita_Rotazione_Mensile** — Numero di volte che la quota `Q_m` ruota in 30 giorni. Peso 40% — *"il Cash Drag (soldi fermi) è il nemico n.1"*.
- **Cash_Profit_Assoluto** — Guadagno in € per singolo pezzo (= Cash Profit della Formula 2). Peso 20% — *"tie-breaker: a parità di ROI e Velocità, vince chi porta più cassa"*.

Pesi sommano a 1.0 ✓.

> **[L04b — CHIUSA Round 4 (2026-04-29)]** — Risposta Leader (verbatim): *"la decisione è quella di normalizzare i tre termini. tutti i dati devono pesare e collaborare"*. Decisione: **normalizzazione min-max su [0,1] sul listino di sessione** prima dei pesi 40/40/20. Conseguenza: i tre termini hanno contributo massimo identico (0.4, 0.4, 0.2 rispettivamente) e il ranking riflette i pesi dichiarati. Edge case noto: con `max(x) == min(x)` su un termine (es. tutto il listino ha lo stesso ROI), `norm` diventa 0/0 — convenzione: il termine vale 0 per tutti gli ASIN (il termine non discrimina, l'ordinamento dipende dagli altri due). La scelta tra min-max e z-score è risolta a favore di min-max: garantisce dominio [0,1] esatto e interpretabilità dei pesi; z-score è alternativa di sensibilità (non scelta) da rivalutare solo se emergono outlier che distorcono il ranking, in fase implementativa sotto ADR di stack.

### 6.4 Ambiente operativo

| Layer | Tecnologia |
|---|---|
| **Backend** | Container Docker locale (PostgreSQL + Python Data Science stack) |
| **Frontend** | **Streamlit** o **Gradio** (locale) per slider dinamici reattivi e tabellari |

> **[L14 — CHIUSA Round 5 (2026-04-29)]** — Risposta Leader: **Streamlit**. Razionale del Leader (verbatim): *"Avendo a che fare con griglie di dati (gli ASIN), tabelle di comparazione e slider parametrici, Streamlit è molto più solido e indicato rispetto a Gradio per un cruscotto gestionale interno."* Implicazioni operative: rerun completo a ogni interazione → strutturare il codice con caching (`@st.cache_data` per il fetch Keepa, `@st.cache_resource` per la sessione DB) e session_state per evitare ricalcoli inutili al variare dello slider Velocity Target.

### 6.5 Vincoli business / tempo

> [LACUNA L02 — già marcata]: capitale di partenza `x` da definire.

Nessun deadline temporale dichiarato esplicitamente.

---

## 7. Successo misurabile

### 7.1 Criteri di completamento

> Nota del Leader (verbatim): *"Il software è pronto quando funziona senza nessun errore, in perfetto ordine e senza rischi di allucinazioni o compromessi sbrigativi di struttura."*

> **[L20 — CHIUSA Round 2 (2026-04-29)]** — Decisione Leader: **suggerito accettato** ("l20 suggerito"). Set di criteri di completamento misurabili ratificato:
> 1. **Suite pytest** che copre tutti i moduli del motore di calcolo (acquisizione, NLP/Estrattore, VGP, Tetris, Panchina, Storico Ordini); copertura target da definire nell'ADR di test (suggerimento: ≥ 85% sulle funzioni dei moduli core).
> 2. **Fixture di listino noto** (es. 1.000 righe Samsung con costi/prezzi/Buy Box pre-fissati) con risultato VGP + carrello Tetris **atteso byte-exact**; il test fallisce se l'output devia di un singolo centesimo o ASIN.
> 3. **R-01 NO SILENT DROPS verificato staticamente:** test che fa grep nel codice di `\.drop\(` e fallisce se ne trova occorrenze (eccetto in commenti o stringhe di log esplicite).
> 4. **Lint zero warning** (linter da concordare in ADR di stack — candidato: `ruff` strict).
> 5. **Type checking strict:** `mypy --strict` o `pyright strict` zero errori (decisione strumento in ADR di stack).

### 7.2 Orizzonte di successo / MVP

> Nota del Leader (verbatim): *"Si intende la versione minima funzionante del software. Non serve che sia bello, serve che sia efficace. L'obiettivo dell'MVP è dimostrare che la pipeline 'Dato Fornitore → Analisi → Carrello' produce profitto reale senza errori di calcolo."*

**Definizione MVP:** acquisizione automatica del listino fornitore, arricchimento Keepa, filtraggio hardware e generazione del primo carrello secondo i criteri stabiliti.

> Osservazione: l'MVP è circolare con LACUNA L04 (formula VGP). Senza VGP non c'è "criterio stabilito" per generare il carrello. **Risolvere L04 è prerequisito di MVP definibile.**

---

## 8. Rischi noti

### 8.1 Rischi tecnici

| Rischio | Mitigazione dichiarata dal Leader |
|---|---|
| **Computazione del Bin Packing**: il ricalcolo al variare dello slider Velocity Target potrebbe causare colli di bottiglia nella RAM se il database sfiora le **10.000 righe** | **Vettorizzazione Numpy rigorosa** |

> **[L24 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. Rischi tecnici aggiuntivi inscritti nella tabella ufficiale 8.1:

| Rischio | Mitigazione |
|---|---|
| **Throttling Keepa API** (limite chiamate/sec, costi a tier) | Backoff esponenziale, batch dei lookup, cache locale dei dati di sessione |
| **Rotture scraping Amazon.it** (selettori HTML mutano) | Selettori multipli con fallback, log strutturato dei mismatch, alerting al CFO |
| **Falsi positivi/negativi OCR** (PDF deteriorati / scan bassa risoluzione) | Soglia di confidenza Tesseract; sotto soglia → status "AMBIGUO" e R-01 NO SILENT DROPS |
| **Ambiguità persistenti del matcher Samsung** ("AMBIGUO" del 4.1.2) | Esclusione esplicita dal carrello + log + revisione manuale dal cruscotto |
| **Drift dati Keepa** (BSR estimate ≠ realtà → V_tot sbagliato a cascata) | Audit periodico delle previsioni Q_m vs unità effettivamente vendute (storico ordini); flag di sospetto se |Δ| > soglia |

### 8.2 Rischi non tecnici (sezione 15 — saltata nella bozza originale)

> **[L17 — CHIUSA Round 5 (2026-04-29)]** — Confermato il default. La sezione 15 della bozza originale era una lacuna involontaria. Rischi non tecnici inscritti ufficialmente:

| Rischio | Mitigazione |
|---|---|
| **ToS Amazon** (scraping non sempre permesso, automazione del cart) | Scraping a basso rate (rispetto robots.txt e cadence umana), nessuna automazione del cart vero e proprio (l'export "ordina" è manuale dal CFO) |
| **ToS fornitori** (export ordini automatizzato) | Verifica preventiva contrattuale con ogni fornitore prima di abilitare l'esportazione automatica del carrello |
| **GDPR / privacy** sui dati clienti nei listini | Anonimizzazione/scarto dei campi non necessari al matching; storage minimo; nessuna persistenza dei dati personali oltre la finalizzazione dell'ordine |
| **Dipendenza single-vendor Keepa** (cambio prezzi, sparizione, throttling) | Fallback formula manuale Fee_FBA (L11b), monitor del piano subscription, possibilità futura di multi-source |
| **Dipendenza single-vendor JungleScout** (idem) | Fallback Keepa primario; possibilità futura di altri source provider |
| **Compliance Reverse Charge** | Validazione del flusso con commercialista prima della messa in produzione |

---

## 9. Lacune Aperte

> Sezione live in `Iterating`. Scende verso 0 prima del `Frozen`.
>
> **Round 5:** sweep finale completato. **0 lacune aperte.** Tutte le 26 lacune sollevate nei round 1–4 (24 originarie + L04b + L11b) sono chiuse. Vision pronta per dichiarazione esplicita di `Frozen` da parte del Leader.

### Lacune Aperte

Nessuna.

### Lacune Chiuse

| # | Round | Decisione |
|---|---|---|
| **L01** | **5** | **Stateless = analisi di sessione senza dipendenza causale da sessioni precedenti; Storico/Panchina sono archivio/lookup** |
| **L02** | **5** | **Budget di sessione (Opzione a): capitale fisicamente disponibile per la singola run, fornito dall'utente (R-02)** |
| **L03** | **5** | **Niente automatico verso il commercialista; solo storico interno consultabile** |
| **L05** | **5** | **Slider Velocity Target: range 7–30 giorni, default 15, granularità 1 giorno** |
| **L07** | **5** | **NLP+Estrattore = un solo modulo `SamsungExtractor` con Filtro Kill-Switch come fase finale di validazione** |
| **L09** | **5** | **Refuso confermato: Veto ROI = R-08 (testo originale "R-09" corretto inline)** |
| **L09b** | **5** | **Refuso confermato: Tetris = R-06 (la tabella di R-09 era già coerente, nessun edit residuo)** |
| **L10** | **5** | **Soglia Veto ROI configurabile dal cruscotto, default 8%, persistita come config** |
| **L11b** | **5** | **Formula manuale Fee_FBA fornita verbatim dal Leader (vedi sez. 6.3 Formula 1)** |
| **L13** | **5** | **Manual Override: pulsante Lock-in sulla griglia + tabella ASIN locked_in modificabile + Priorità=∞ nel Tetris** |
| **L14** | **5** | **Streamlit (più solido per cruscotto gestionale interno con griglie/slider)** |
| **L15** | **5** | **PostgreSQL Zero-Trust = RLS + ruoli `talos_app`/`talos_admin` + no superuser pool app + audit log** |
| **L16** | **5** | **Stack: SQLAlchemy 2.0 sync + Alembic + Playwright + Tesseract** |
| **L17** | **5** | **6 rischi non tecnici inscritti ufficialmente in 8.2 (ToS Amazon/fornitori, GDPR, single-vendor, Reverse Charge)** |
| **L19** | **5** | **DOCS = `.docx` Microsoft Word** |
| **L22** | **5** | **Storico ordini alimentato solo dall'azione "ordina" interna a Talos** |
| **L24** | **5** | **5 rischi tecnici extra inscritti ufficialmente in 8.1 con mitigazioni** |
| L04b | 4 | Normalizzazione min-max su [0,1] dei tre termini VGP sul listino di sessione, poi pesi 40/40/20 |
| L04 | 3 | Formula VGP fornita: `(ROI*0.4)+(Vel*0.4)+(Cash_Profit*0.2)` |
| L21 | 3 | Keepa: piano gestito esternamente dal Leader, out-of-scope per Talos |
| L06 | 2 | MVP Samsung-only + interface `BrandExtractor` modulare (delega) |
| L08 | 2 | Scraping `amazon.it` |
| L11 | 2 | Lookup primario Keepa + fallback formula manuale (chiusa con L11b) |
| L12 | 2 | Lookup categoria + override manuale configurabile |
| L18 | 2 | Tesseract locale |
| L20 | 2 | Pytest + fixture byte-exact + grep R-01 + ruff + mypy/pyright strict |

---

## 10. Q&A Log

> Cronologia append-only di tutte le domande poste da Claude e delle risposte del Leader durante `Iterating`. Mai cancellata. Ogni voce ha round, data, riferimento, esito.

### Round 1 — 2026-04-29 — Esposizione iniziale

| # | Tipo | Contenuto |
|---|---|---|
| 1.0 | Esposizione del Leader | Il Leader ha esposto la bozza completa di TALOS in un singolo blocco testuale strutturato in 14+1 sezioni (1-14, 16; sezione 15 omessa). Status del file passato `Draft → Iterating`. |
| 1.1 | Trascrizione | Claude ha trascritto verbatim il contenuto mappandolo sulle 11 sezioni del template ADR-0012, con sotto-sezioni 4.1.x, 6.x e 8.x per preservare la granularità della bozza. |
| 1.2 | Raccolta lacune | Claude ha identificato **24 lacune** in violazione apparente della dichiarazione del Leader ("nessuna lacuna aperta"), giustificate dalla regola "Lacune Mai Completate" di ADR-0012. Categorizzate in critiche/importanti/forma. |
| 1.3 | Lacune chiuse | 0. Tutte aperte, da chiudere nei round successivi. |

**Esito Round 1:** trascrizione integrale fatta, 24 lacune da risolvere. Il prossimo round è la prima tornata di Q&A (Round 2): il Leader risponde alle critiche prioritariamente.

---

### Round 2 — 2026-04-29 — Risposte alle lacune critiche (parziale)

> Risposte verbatim del Leader: *"l18 tesseract locale. l20 suggerito. l08 scraping. l06 quello che ti sembra meglio. l11 se possibile prendi da keepa, altrimenti utilizzi formula che ti darò dopo. l12 sia lookup che configurabile"*

| # | Lacuna | Domanda di Claude | Risposta del Leader (verbatim) | Decisione finale | Lacuna chiusa? |
|---|---|---|---|---|---|
| 2.1 | **L18** | OCR/Vision per file non strutturati: Tesseract / GPT-4V / Claude V / Textract? | *"l18 tesseract locale"* | Tesseract locale (open source, gratis, qualità media). Implicazioni: no API esterne, no costi ricorrenti, qualità degradata su PDF deteriorati (rischio L24) | ✅ chiusa |
| 2.2 | **L20** | Criteri di completamento misurabili — accetti il set proposto (pytest + fixture + grep R-01 + lint + type-check)? | *"l20 suggerito"* | Suggerito accettato integralmente: pytest con copertura target ≥ 85% (da confermare in ADR test), fixture byte-exact, grep `\.drop\(`, ruff strict, mypy/pyright strict | ✅ chiusa |
| 2.3 | **L08** | Lookup Amazon (fallback JungleScout): scraping `amazon.it` o PA-API 5? | *"l08 scraping"* | Scraping `amazon.it`. La libreria (Selenium / Playwright / requests+bs4) sarà oggetto di ADR di stack. Implicazioni ToS Amazon → aggrava L17 | ✅ chiusa |
| 2.4 | **L06** | Estrattore Samsung-only: scope MVP e roadmap multi-brand? | *"l06 quello che ti sembra meglio"* (delega esplicita) | Decisione di Claude (ratificata dalla delega): MVP Samsung-only + architettura modulare con interface `BrandExtractor` + implementazione `SamsungExtractor` come unica in MVP. Multi-brand post-MVP via nuove implementazioni | ✅ chiusa (per delega) |
| 2.5 | **L11** | `Fee_FBA`: hardcoded / Keepa / tabella manuale? | *"l11 se possibile prendi da keepa, altrimenti utilizzi formula che ti darò dopo"* | Lookup primario Keepa (campo da confermare con L21); se assente nel piano subscription scelto → fallback a formula manuale fornita dal Leader (apre **L11b**) | ✅ chiusa con sub-lacuna L11b |
| 2.6 | **L12** | `Referral_Fee`: hardcoded / configurabile / lookup? | *"l12 sia lookup che configurabile"* | Lookup automatico per categoria come default + override manuale per ASIN o categoria, persistito in DB (config layer, non transazione) | ✅ chiusa |
| 2.7 | **L04** | Formula del VGP Score? | (non risposta) | aperta — bottleneck dell'MVP | ❌ aperta |
| 2.8 | **L21** | Keepa: subscription/campi/costo/rate limit? | (non risposta) | aperta — collegata a L11 | ❌ aperta |

**Esito Round 2:**
- 6 lacune chiuse (L06, L08, L11, L12, L18, L20).
- 1 sub-lacuna nuova aperta (**L11b** — formula manuale Fee_FBA che il Leader fornirà).
- 2 critiche restano aperte (L04, L21).
- **Bottleneck per Frozen:** L04 (formula VGP).

**Prossimo round (Round 3) atteso:** chiusura di L04 e L21, poi sweep delle 13 importanti rimanenti + 4 di forma.

---

### Round 3 — 2026-04-29 — Formula VGP + Keepa out-of-scope + direttiva concisione

| # | Lacuna | Risposta Leader (verbatim) | Decisione | Stato |
|---|---|---|---|---|
| 3.1 | **L04** Formula VGP | `VGP = (ROI%*0.4)+(Velocità*0.4)+(Cash_Profit*0.2)` con definizioni dei tre termini | Formula incisa in sezione 6.3 | ✅ chiusa |
| 3.2 | **L21** Keepa | *"non penso debba interessarti, ci deve essere l'infrastruttura per usare le api di keepa ai miei scopi, come le ho è un fatto mio"* | Out-of-scope Talos (piano gestito dal Leader) | ✅ chiusa |
| 3.3 | **L04b** (nuova) | n/a — sollevata da Claude | Pesi 40/40/20 vs scale dei termini: senza normalizzazione Cash_Profit_Assoluto domina. Domanda al Leader: accettare o normalizzare? | ❌ aperta |
| 3.4 | Direttiva di stile | *"non fossilizzarti troppo sulle minuterie [...] tutto sia accessibile brieffabile e tracciato nelle modifiche non banali"* | Salvata come **memory feedback** durevole; applicata da CHG-006 in poi (CHG e tabelle più snelli) | feedback registrato |

**Esito Round 3:** 18 aperte (1 critica residua: L04b). Vicini al Frozen — manca decisione su normalizzazione VGP, poi sweep finale importanti+forma.

---

### Round 4 — 2026-04-29 — Chiusura L04b (normalizzazione VGP)

| # | Lacuna | Risposta Leader (verbatim) | Decisione | Stato |
|---|---|---|---|---|
| 4.1 | **L04b** Normalizzazione VGP | *"la decisione è quella di normalizzare i tre termini. tutti i dati devono pesare e collaborare"* | Normalizzazione **min-max su [0,1]** dei tre termini sul listino della singola sessione, poi applicazione dei pesi 40/40/20. Edge case `max==min` → termine vale 0. Coerente con natura Stateless di Talos | ✅ chiusa |

**Esito Round 4:** **0 critiche residue**, 17 aperte (13 importanti + 4 di forma + L11b condizionale). Il dominio matematico del decisore VGP è pienamente specificato. Prossimo passo: sweep delle importanti+forma → Frozen.

---

### Round 5 — 2026-04-29 — Sweep finale (chiusura totale)

> Risposta verbatim del Leader: *"Ok ai default su tutta la linea, con queste due precisazioni per le domande senza default: 3. L02 Capitale di partenza: Opzione (a) - Intendo il budget di sessione [...] non il capitale totale teorico. 9. L14 Interfaccia: Streamlit. Avendo a che fare con griglie di dati [...] Streamlit è molto più solido [...] Per tutto il resto (L01, L07, L05, L10, L13, L03, L22, L15, L16, L17, L24, L09, L09b, L19, L11b) confermo al 100% i tuoi default e le tue assunzioni. per quanto riguarda la formula, eccola: fee_fba = (((prezzo buy box/1,22-100)*0,0816)+7,14)*1,03+6,68"*

| # | Lacuna | Decisione finale | Stato |
|---|---|---|---|
| 5.01 | **L01** Stateless | Default confermato | ✅ chiusa |
| 5.02 | **L02** Capitale `x` | Opzione (a) — budget di sessione (precisato dal Leader) | ✅ chiusa |
| 5.03 | **L03** Output commercialista | Default confermato (niente automatico) | ✅ chiusa |
| 5.04 | **L05** Slider Velocity | Default confermato (7–30 gg, default 15, step 1) | ✅ chiusa |
| 5.05 | **L07** NLP vs Estrattore | Default confermato (un solo modulo) | ✅ chiusa |
| 5.06 | **L09** Refuso R-08 | Default confermato (Veto ROI = R-08) | ✅ chiusa |
| 5.07 | **L09b** Refuso R-06 | Default confermato (Tetris = R-06) | ✅ chiusa |
| 5.08 | **L10** Soglia Veto ROI | Default confermato (configurabile, default 8%) | ✅ chiusa |
| 5.09 | **L11b** Fee_FBA manuale | **Formula fornita verbatim dal Leader** — incisa in 6.3 Formula 1 | ✅ chiusa |
| 5.10 | **L13** Manual Override UI | Default confermato (Lock-in + tabella + Priorità=∞) | ✅ chiusa |
| 5.11 | **L14** Streamlit vs Gradio | **Streamlit** (precisato dal Leader) | ✅ chiusa |
| 5.12 | **L15** Postgres Zero-Trust | Default confermato (RLS + ruoli + audit) | ✅ chiusa |
| 5.13 | **L16** Stack Python | Default confermato (SQLAlchemy 2.0 sync + Alembic + Playwright + Tesseract) | ✅ chiusa |
| 5.14 | **L17** Rischi non tecnici | Default confermato (6 rischi inscritti in 8.2 con mitigazioni) | ✅ chiusa |
| 5.15 | **L19** DOCS = `.docx` | Default confermato | ✅ chiusa |
| 5.16 | **L22** Storico ordini | Default confermato (solo interno) | ✅ chiusa |
| 5.17 | **L24** Rischi tecnici extra | Default confermato (5 rischi inscritti in 8.1 con mitigazioni) | ✅ chiusa |

**Esito Round 5:** **0 lacune aperte. 0 critiche residue.** Tutte le 26 lacune sollevate nei round 1–4 sono chiuse. La vision di TALOS è matematicamente, architetturalmente e operativamente specificata. La pipeline ADR-0012 è pronta per la transizione esplicita `Iterating → Frozen` (step [5]) su dichiarazione del Leader. Solo dopo Frozen Claude può procedere allo step [6] (proposta scomposizione in chat).

---

## 11. Refs

> Riferimenti esterni (link, documenti, ispirazioni) che il Leader vuole conservare come contesto.

[da raccogliere — il Leader non ha citato riferimenti espliciti nella prima esposizione. Domande da porre nei round successivi:
- Dataset di esempio per il listino fornitore (un file reale anonimizzato)?
- Riferimenti Keepa API doc?
- Schema BSR/BuyBox di Amazon che il Leader vuole assumere come canonico?
- Riferimenti "Cash Drag", "VGP", "Hedge Fund applicato a FBA" — letteratura, articoli, sue note interne?]

---

## Cronologia Stati

| Data | Status | Evento |
|---|---|---|
| 2026-04-29 | Draft | File creato (CHG-2026-04-29-003, ratifica ADR-0012) — pronto per esposizione |
| 2026-04-29 | **Iterating** | Esposizione iniziale del Leader; trascrizione verbatim; 24 lacune raccolte (CHG-2026-04-29-004) |
| 2026-04-29 | **Iterating** | Round 2 Q&A: chiuse 6 lacune critiche (L06, L08, L11, L12, L18, L20), aperta L11b condizionale; 19 aperte (CHG-2026-04-29-005) |
| 2026-04-29 | **Iterating** | Round 3: chiuse L04 (formula VGP) + L21 (Keepa out-of-scope); aperta L04b (normalizzazione scale); direttiva concisione registrata; 18 aperte (CHG-2026-04-29-006) |
| 2026-04-29 | **Iterating** | Round 4: chiusa L04b (normalizzazione min-max [0,1] dei tre termini VGP); 0 critiche residue; 17 aperte (CHG-2026-04-29-007) |
| 2026-04-29 | **Iterating** | Round 5: sweep finale, chiuse tutte le 17 residue (default + L02=(a) + L14=Streamlit + formula Fee_FBA verbatim per L11b); 0 aperte (CHG-2026-04-29-008) |
