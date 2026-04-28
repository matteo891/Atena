# File-to-ADR Map — Indice Inverso

Navigazione inversa: da un file qualsiasi al suo ADR di riferimento.

> **Regola (ADR-0001):** Aggiornare questa mappa ogni volta che si aggiunge un nuovo componente o un nuovo ADR copre un file esistente. La colonna "ADR Primario" indica il vincolo architetturale principale; la colonna "ADR Secondari" indica i protocolli operativi che si applicano.

**Come usarla:**
- Stai per toccare un file? Cerca qui il suo ADR e leggilo prima.
- Non trovi il file? → Gap ADR. Segnala al Leader prima di procedere (CLAUDE.md — Gap ADR).

---

## Governance e Infrastruttura Documentale

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `CLAUDE.md` | ADR-0001 | tutti | Rules of Engagement; modificare solo con ADR di supporto |
| `ROADMAP.md` | ADR-0001 | — | Aggiornare ad ogni ADR ratificato |
| `CHANGELOG.md` | ADR-0003, ADR-0004 | ADR-0005 | Checkpoint log + change summary con link CHG |
| `docs/decisions/ADR-*.md` | ADR-0001 | — | Ogni ADR segue TEMPLATE.md; vedi INDEX.md |
| `docs/decisions/INDEX.md` | ADR-0001 | — | Aggiornare prima della ratifica di ogni nuovo ADR |
| `docs/decisions/FILE-ADR-MAP.md` | ADR-0001 | — | Questo file; aggiornare ad ogni nuovo componente |
| `docs/decisions/TEMPLATE.md` | ADR-0001 | — | Template ADR; modificare solo con nuovo ADR meta |
| `docs/changes/*.md` | ADR-0004 | ADR-0005 | Change documents; un file per modifica non-triviale |
| `docs/changes/TEMPLATE.md` | ADR-0004 | — | Template change doc; non è un change document reale |

## Git e CI/CD

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| `scripts/hooks/pre-commit` | ADR-0006 | ADR-0001, ADR-0002, ADR-0004 | Enforcement meccanico change doc + struttura ADR |
| `scripts/hooks/commit-msg` | ADR-0006 | ADR-0005 | Enforcement meccanico commit convention |
| `scripts/setup-hooks.sh` | ADR-0006 | — | Eseguire dopo ogni clone |
| `.gitnexus/` | ADR-0007 | — | Database GitNexus; non modificare manualmente |
| `.gitignore` | — | — | Triviale; nessun ADR |

## Codice Applicativo

> Vuoto — il progetto non ha ancora codice sorgente applicativo.
> Aggiornare questa sezione man mano che i componenti vengono introdotti con i rispettivi ADR.

| File / Pattern | ADR Primario | ADR Secondari | Note |
|---|---|---|---|
| — | — | — | Da definire dal Leader |

---

## Gap Noti (Aree Senza Copertura ADR)

| Area | Gap | Azione Richiesta |
|---|---|---|
| Stack tecnologico | Nessun ADR | Leader deve definire il linguaggio/framework |
| CI/CD pipeline | Nessun ADR | Leader deve definire il workflow di deployment |
| Struttura directory del codice | Nessun ADR | Dipende dallo stack; da definire con ADR architecture |
