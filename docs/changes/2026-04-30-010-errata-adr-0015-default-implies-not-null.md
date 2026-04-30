---
id: CHG-2026-04-30-010
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0009
---

## What

**Errata Corrige di ADR-0015** (Stack Persistenza). Sancisce formalmente la regola interpretativa dell'Allegato A:

> Qualsiasi colonna definita con un `DEFAULT` in Allegato A implica automaticamente il vincolo `NOT NULL` (`nullable=False`), per garantire allineamento DB/Typing.

| File | Tipo | Cambio |
|---|---|---|
| `docs/decisions/ADR-0015-stack-persistenza.md` | errata corrige | Frontmatter `errata:` esteso con voce CHG-010. Nuova sezione "Convenzione interpretativa" inserita prima del DDL dell'Allegato A. Sezione `## Errata` in coda con descrizione + motivazione. |

Nessun cambio al codice applicativo: i model `AnalysisSession` e `AsinMaster` (CHG-008/009) sono già conformi alla regola che ora è ratificata.

## Why

Decisione esplicita del Leader 2026-04-30 sulla open question dichiarata in CHG-009. Citazione verbatim:

> *"In merito alla tua Open Question, scelgo la risoluzione (a). Dal punto di vista architetturale, è fondamentale evitare l'ambiguità dei nullable type in Python per campi con un default deterministico."*

Conseguenze:
- I 2 model esistenti (`AnalysisSession`, `AsinMaster`) restano invariati e ora sono **formalmente** conformi.
- Gli 8 model successivi (8 tabelle restanti dell'Allegato A) seguiranno la regola **per costruzione**, non più come convenzione applicata in autonomia.
- Future PR/CHG su persistence che proporrebbero `Mapped[T | None]` su colonna con `DEFAULT` saranno **blockate** dalla regola formale (errata corrige di ADR-0015 ha precedenza sul testo letterale dell'Allegato A grazie a ADR-0009).

## How

### Modifica al testo di ADR-0015

**Posizione:** prima dell'inizio del blocco DDL `\`\`\`sql` dell'Allegato A.

**Contenuto inserito:** sotto-sezione `### Convenzione interpretativa (Errata Corrige 2026-04-30, CHG-2026-04-30-010)` con:
- regola vincolante (testo verbatim della decisione del Leader);
- razionale (allineamento Postgres `DEFAULT` → `NOT NULL` → typing Python `Mapped[T]` non-Optional);
- conseguenze operative (model esistenti conformi, model futuri tenuti alla regola, eccezione esplicita per colonne nullable senza default).

### Frontmatter `errata:`

Estesa con un solo elemento di lista:
```yaml
errata:
  - date: 2026-04-30
    chg: CHG-2026-04-30-010
    summary: "Sancita formalmente la convenzione interpretativa dell'Allegato A: ogni colonna definita con un `DEFAULT` implica automaticamente il vincolo `NOT NULL` (`nullable=False` nell'ORM). Garantisce allineamento DB ↔ Typing Python (no `Mapped[T | None]` per campi con default deterministico)."
```

### Sezione `## Errata` in coda

Nuova voce `### 2026-04-30 — CHG-2026-04-30-010` con i campi prescritti da ADR-0009: tipo, modifica, motivo, sostanza alterata.

### Disciplina ADR-0009

Verifica delle condizioni richieste per qualificare come errata corrige (non supersessione):

| Condizione | Esito |
|---|---|
| Non altera la decisione presa | ✅ Lo stack (PostgreSQL/SQLAlchemy 2.0 sync/Alembic/Zero-Trust) non cambia |
| Corregge un refuso o chiarisce un'incoerenza | ✅ Chiarisce ambiguità "DEFAULT senza NOT NULL letterale" → convenzione vincolante |
| Lascia inalterate `## Decisione` e `## Conseguenze` nel contenuto normativo | ✅ La nota è dentro l'Allegato A; nessun cambio alle 4 sezioni cardine |

L'errata è ammessa senza supersessione.

## Tests

Test manuali documentati (governance — ADR-0011). Modifica solo testuale a un ADR; nessun codice toccato.

| Test | Comando / Verifica | Esito |
|---|---|---|
| Frontmatter `errata:` aggiornato | `grep -A2 'CHG-2026-04-30-010' docs/decisions/ADR-0015-stack-persistenza.md` (frontmatter) | atteso PASS |
| Sezione "Convenzione interpretativa" presente | `grep '### Convenzione interpretativa' docs/decisions/ADR-0015-stack-persistenza.md` | atteso PASS |
| Sezione `## Errata` con voce CHG-010 | `grep -A1 '### 2026-04-30 — CHG-2026-04-30-010' docs/decisions/ADR-0015-stack-persistenza.md` | atteso PASS |
| Allegato A DDL letterale invariato | `grep -c 'CREATE TABLE' docs/decisions/ADR-0015-stack-persistenza.md` ≥ 10 (10 tabelle Allegato A) | atteso PASS |
| ADR-0015 ancora `Active` | `grep '^status: Active' docs/decisions/ADR-0015-stack-persistenza.md` | atteso PASS |
| Pre-commit hook simulato (sezioni ADR + struttura) | hook governance al commit reale | atteso PASS |
| Quality gate codice invariato | `uv run pytest tests/unit tests/governance -q` (no regressi) | atteso 36 passed |

**Copertura:** verifica strutturale completa dell'errata. Conformità retroattiva dei 2 model esistenti già verificata in CHG-008/009 (`nullable=False` su `started_at`, `enterprise`, `last_seen_at`).

**Rischi residui:**
- I prossimi 8 model dell'Allegato A devono applicare la regola. Disciplina del CHG che li introduce: il testo del CHG deve citare esplicitamente la regola se la colonna ha `DEFAULT`.
- Se in futuro emergerà un caso "DEFAULT con valore semantico nullable" (improbabile, ma possibile per `enterprise BOOLEAN DEFAULT NULL` o simili), servirà nuova errata o eccezione esplicita nel CHG.
- Il test `tests/unit/test_*.py` di ogni model verifica `not col.nullable` per le colonne con `server_default`. La regola è già enforced lato test.

## Refs

- ADR: ADR-0015 (errata corrige primaria), ADR-0009 (meccanismo)
- Predecessore: CHG-2026-04-30-009 (open question dichiarata)
- Successore atteso: CHG-2026-04-30-011 (`listino_items` model — primo modello con FK)
- Commit: `<pending>`
