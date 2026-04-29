---
id: CHG-2026-04-29-005
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Committed
commit: b05ecbe
adr_ref: ADR-0012
---

## What — Cosa è cambiato

**Round 2 Q&A su PROJECT-RAW.md (TALOS).** Il Leader ha risposto a 6 delle 8 lacune critiche identificate in Round 1. Aggiornamento del file vision con:
- 6 lacune chiuse (L06, L08, L11, L12, L18, L20)
- 1 sub-lacuna nuova aperta (L11b — formula manuale Fee_FBA che il Leader fornirà)
- 2 lacune critiche residue (L04 formula VGP, L21 Keepa subscription)
- Frontmatter `qa_rounds: 1 → 2`
- Tabella lacune sezione 9 ristrutturata in "Aperte" (19) + "Chiuse" (6)
- Q&A Log sezione 10 esteso con Round 2 (6 voci dettagliate + 2 attese)
- Cronologia Stati estesa

**File creato:**
- `docs/changes/2026-04-29-005-talos-iterating-round-2.md` — questo documento

**File modificati:**
- `PROJECT-RAW.md` — chiusura inline di L06, L08, L11, L12, L18, L20; aggiornamento sez. 9, 10, frontmatter, header, cronologia
- `docs/STATUS.md` — Round 2 registrato, lacune residue elencate, prossima azione aggiornata
- `ROADMAP.md` — Round 2 completato, Round 3 in attesa
- `CHANGELOG.md` — versione 0.7.1

## Why — Perché

**ADR di riferimento:** [ADR-0012](../decisions/ADR-0012-project-vision-capture.md) — pipeline operativa step [3]–[4] (Iterating, round Q&A, Q&A Log cresce, lacune chiuse spostate dalla sezione 9).

**Risposte del Leader (verbatim, 2026-04-29):**
> *"l18 tesseract locale. l20 suggerito. l08 scraping. l06 quello che ti sembra meglio. l11 se possibile prendi da keepa, altrimenti utilizzi formula che ti darò dopo. l12 sia lookup che configurabile"*

**Decisione delegata su L06:** il Leader ha esplicitamente delegato a Claude la decisione su Estrattore Samsung-only ("quello che ti sembra meglio"). Claude ha deciso, sotto delega ratificata: **MVP Samsung-only + architettura modulare con interface `BrandExtractor`** (estensione futura via implementazioni concrete). Razionale: focus + scope ridotto + costo marginale del design modulare trascurabile vs versione monolitica.

## How — Come

**Approccio tecnico:**

Per ogni lacuna chiusa, modificato il commento `[LACUNA Lxx ...]` inline a `[Lxx — CHIUSA Round 2 (2026-04-29)]` con la decisione finale + implicazioni operative. Il testo originale della domanda è stato preservato come parte del log audit (la lacuna chiusa rimane visibile a chi legge la sezione, con il rationale del Leader esplicito).

La sezione 9 (Lacune Aperte) è stata ristrutturata in due tabelle:
1. **Aperte (19):** 2 critiche, 13 importanti (+ L11b nuova), 4 di forma. Ogni riga ha `Round aperto` per audit.
2. **Chiuse (6):** ID, round chiuso, decisione finale (sintesi).

La sezione 10 (Q&A Log) ha ricevuto un blocco Round 2 con tabella verbatim di domanda/risposta/decisione/stato per ognuna delle 8 lacune affrontate (6 chiuse + 2 attese).

Header del file aggiornato per riflettere lo stato corrente: 19 aperte, 2 critiche residue.

**Conteggio lacune dopo Round 2:**

| Pre-Round 2 | Chiuse Round 2 | Nuove Round 2 | Post-Round 2 |
|---|---|---|---|
| 24 (8 critiche, 12 importanti, 4 forma) | -6 (-6 critiche, 0 importanti, 0 forma) | +1 (0 critiche, +1 importante L11b, 0 forma) | **19** (2 critiche, 13 importanti, 4 forma) |

## Tests

| Test | Tipo | Esito | Note |
|---|---|---|---|
| Frontmatter `qa_rounds: 2` | Verifica strutturale (ADR-0011) | PASS atteso | grep |
| 6 entry "CHIUSA Round 2" inline nel testo | Verifica strutturale | PASS atteso | grep `CHIUSA Round 2` |
| Tabella "Lacune Aperte" ha 19 voci | Verifica strutturale | PASS atteso | conteggio |
| Tabella "Lacune Chiuse" ha 6 voci | Verifica strutturale | PASS atteso | conteggio |
| L11b presente come nuova lacuna | Verifica strutturale | PASS atteso | grep `L11b` |
| Q&A Log Round 2 presente | Verifica strutturale | PASS atteso | grep `Round 2 — 2026-04-29` |
| Risposte verbatim Leader incluse senza modifiche | Verifica manuale | PASS — verificato in stesura | confronto con messaggio Leader |
| Decisione su L06 ratificata via delega esplicita Leader | Verifica testuale | PASS — "quello che ti sembra meglio" è autorizzazione | `delega esplicita` nel testo |

**Copertura stimata:** copre la chiusura di Round 2. La validazione operativa delle decisioni (es. Tesseract effettivamente usato, scraping conforme ToS) sarà testata in fase di implementazione.

**Rischi residui:**
- L04 (VGP) e L21 (Keepa) sono ancora aperte. Senza queste, l'MVP non è specificabile. Il Leader le tratterà nel Round 3.
- L11b dipende da quando il Leader fornirà la formula manuale Fee_FBA. Marcata "CONDIZIONALE": diventa bloccante solo se Keepa non espone il campo.

## Impact

- Il file vision è più chiuso del 25% (6/24 lacune risolte in un round).
- Il Leader e Claude hanno un Q&A Log strutturato e verbatim per audit storico.
- 5 decisioni architetturali rilevanti sono ora ratificate (Tesseract, scraping Amazon, lookup Keepa primario, lookup categoria + override Referral_Fee, criteri di accettazione misurabili).
- Una decisione architetturale via delega: Samsung-only + modulare. Da elevare ad ADR di stack post-Frozen.
- Il prossimo Round (3) ha agenda chiara: L04, L21, poi sweep delle 13 importanti + 4 di forma.

## Refs

- ADR: [ADR-0012](../decisions/ADR-0012-project-vision-capture.md)
- Vision file: [PROJECT-RAW.md](../../PROJECT-RAW.md)
- Commit: `b05ecbe`
- Restore point: tag `milestone/vision-protocol-v0.6.0` su `55ea55f`
- Issue / Task: ESP-002 (Round 2 Q&A) → parzialmente chiusa, evolve in ESP-003 (Round 3 con L04 + L21)
