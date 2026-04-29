---
status: Draft
owner: Leader
started: 2026-04-29
last_iteration: 2026-04-29
frozen_at: —
qa_rounds: 0
---

# PROJECT-RAW — Vision del Progetto

> **Documento governato da [ADR-0012](docs/decisions/ADR-0012-project-vision-capture.md).**
> Status corrente: `Draft` — il Leader esporrà la bozza nella prossima sessione conversazionale.
>
> **Regola anti-allucinazione (vincolante):** ogni sezione vuota o punto ancora vago deve essere marcato `[LACUNA: <domanda concreta>]` e mai completato con prosa inferita. Le lacune vengono raccolte nella sezione 9 e funzionano come agenda dei round di Q&A.
>
> **Pipeline (ADR-0012 sezione "Pipeline Operativa"):**
> 1. Leader espone → Claude trascrive in `Draft`
> 2. Claude raccoglie lacune e pone domande
> 3. `Iterating`: round Q&A, sezioni si riempiono, Q&A Log cresce
> 4. Leader dichiara `Frozen`
> 5. Claude propone scomposizione in chat (ADR di architettura + task ROADMAP)
> 6. Leader valida proposta per proposta → ADR/ROADMAP aggiornati
> 7. Da Frozen in poi: modifiche solo via Errata Corrige (ADR-0009) o transizione documentata a `Iterating`

---

## 1. Cosa è

[da raccogliere — il Leader esporrà la bozza nella prossima sessione conversazionale]

[LACUNA: definizione del progetto in una riga (elevator pitch). Domanda da porre: "Se dovessi descriverlo in una frase di massimo 20 parole, cosa diresti?"]

[LACUNA: paragrafo descrittivo di contesto. Domanda da porre: "Qual è la categoria/dominio del progetto (es. tool dev, app utente, libreria, infra interna)?"]

---

## 2. Perché

[da raccogliere]

[LACUNA: motivazione fondante. Domanda da porre: "Quale problema concreto stai cercando di risolvere, o quale opportunità stai cercando di cogliere?"]

[LACUNA: alternative considerate e scartate. Domanda da porre: "Esistono già soluzioni a questo problema? Perché non bastano?"]

---

## 3. Per chi

[da raccogliere]

[LACUNA: utenti target. Domanda da porre: "Chi userà questo progetto? È per te stesso, per un team, per pubblico esterno?"]

[LACUNA: stakeholder. Domanda da porre: "Oltre agli utenti finali, chi altro è coinvolto (clienti paganti, sponsor, comunità open source)?"]

---

## 4. Cosa fa

[da raccogliere]

[LACUNA: funzionalità chiave. Domanda da porre: "Elenca i 3-5 comportamenti più importanti che il sistema deve avere."]

[LACUNA: scenario d'uso primario. Domanda da porre: "Descrivi un giorno tipo di un utente che usa il sistema, dall'inizio alla fine."]

---

## 5. Cosa NON fa

[da raccogliere]

[LACUNA: out-of-scope espliciti. Domanda da porre: "Cosa NON deve fare? Quali tentazioni di feature creep vuoi escludere fin dall'inizio?"]

---

## 6. Vincoli e requisiti

[da raccogliere]

[LACUNA: vincoli tecnici. Domanda da porre: "Ci sono linguaggi, framework, piattaforme obbligatori o esclusi? Vincoli di performance, latenza, scala?"]

[LACUNA: vincoli di business o tempo. Domanda da porre: "Ci sono deadline? Budget? Requisiti normativi (privacy, sicurezza)?"]

[LACUNA: vincoli sull'ambiente operativo. Domanda da porre: "Dove gira (cloud, on-prem, edge, locale)? Online/offline? Multi-utente?"]

---

## 7. Successo misurabile

[da raccogliere]

[LACUNA: criteri di completamento. Domanda da porre: "Come capisci che il progetto 'funziona'? Quali metriche, KPI, test di accettazione?"]

[LACUNA: orizzonte di successo. Domanda da porre: "C'è un MVP? Un v1 'completo'? Una visione di lungo termine separata dalla v1?"]

---

## 8. Rischi noti

[da raccogliere]

[LACUNA: rischi tecnici. Domanda da porre: "Cosa potrebbe rompere il progetto tecnicamente? Dipendenze fragili? Aree con incertezza alta?"]

[LACUNA: rischi non tecnici. Domanda da porre: "Cosa potrebbe rendere il progetto inutile o invalidato anche se tecnicamente funzionasse?"]

---

## 9. Lacune Aperte

> Sezione **live**: cresce mentre Claude trascrive il `Draft`, decresce durante `Iterating` man mano che il Leader risponde. Deve essere vuota (o contenere solo lacune accettate consapevolmente) prima del `Frozen`.

| # | Lacuna | Sezione di destinazione | Round Q&A | Status |
|---|---|---|---|---|
| L01 | [LACUNA: definizione in una riga] | 1 | — | aperta |
| L02 | [LACUNA: categoria/dominio] | 1 | — | aperta |
| L03 | [LACUNA: problema o opportunità] | 2 | — | aperta |
| L04 | [LACUNA: alternative scartate] | 2 | — | aperta |
| L05 | [LACUNA: utenti target] | 3 | — | aperta |
| L06 | [LACUNA: stakeholder] | 3 | — | aperta |
| L07 | [LACUNA: funzionalità chiave] | 4 | — | aperta |
| L08 | [LACUNA: scenario d'uso primario] | 4 | — | aperta |
| L09 | [LACUNA: out-of-scope] | 5 | — | aperta |
| L10 | [LACUNA: vincoli tecnici] | 6 | — | aperta |
| L11 | [LACUNA: vincoli business/tempo] | 6 | — | aperta |
| L12 | [LACUNA: ambiente operativo] | 6 | — | aperta |
| L13 | [LACUNA: criteri di completamento] | 7 | — | aperta |
| L14 | [LACUNA: orizzonte di successo / MVP] | 7 | — | aperta |
| L15 | [LACUNA: rischi tecnici] | 8 | — | aperta |
| L16 | [LACUNA: rischi non tecnici] | 8 | — | aperta |

**Totale lacune aperte:** 16 (tutte iniziali, da chiudere durante l'esposizione e i round Q&A)

---

## 10. Q&A Log

> Cronologia di tutte le domande poste da Claude e delle risposte del Leader durante `Iterating`. Append-only, mai cancellata. Ogni voce ha round, data, domanda esatta, risposta esatta, lacune chiuse.

| Round | Data | Domanda | Risposta del Leader | Lacune chiuse |
|---|---|---|---|---|
| — | — | — | — | — |

_Nessun round eseguito — file in stato `Draft`, esposizione iniziale non ancora avvenuta._

---

## 11. Refs

[da raccogliere — eventuali link, documenti, screenshot, ispirazioni esterne che il Leader vuole conservare come contesto]

---

## Cronologia Stati

| Data | Status | Evento |
|---|---|---|
| 2026-04-29 | Draft | File creato (CHG-2026-04-29-003, ratifica ADR-0012) — pronto per esposizione |
