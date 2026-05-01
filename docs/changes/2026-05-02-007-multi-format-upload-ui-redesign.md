---
id: CHG-2026-05-02-007
date: 2026-05-02
adr_ref: ADR-0016, ADR-0017, ADR-0019, ADR-0014
commit: TBD
---

## What

Burst valore CFO: input multi-formato + UI redesign + cache reset.

| File | Cosa |
|---|---|
| `src/talos/ui/document_parser.py` | nuovo modulo: dispatcher `parse_uploaded_document(uploaded, suffix)` per CSV/XLSX/PDF/DOCX. PDF via pdfplumber tabelle native; DOCX prima tabella con header `descrizione+prezzo`; XLSX prima sheet. |
| `pyproject.toml` | + deps `pdfplumber>=0.11`, `openpyxl>=3.1`, `python-docx>=1.1`. + mypy override `ignore_missing_imports` per `pdfplumber`/`docx`. |
| `.streamlit/config.toml` | nuovo: theme dark + accent oro tenue (`#C9A961`), font serif, toolbar minimal. |
| `src/talos/ui/dashboard.py` | UI redesign: header brand TALOS con filetto oro + tagline; CSS injection (tipografia, metric, bottoni, sidebar). File uploader accetta CSV/XLSX/PDF/DOCX in entrambi i flow. Sidebar expander "Manutenzione cache" con bottone svuota cache. Bottone "Esegui sessione" `type="primary"`. Helper `try_clear_description_cache(factory) -> (ok, n_rimosse, err)`. |
| `tests/unit/test_document_parser.py` | nuovo: 6 test (suffix non supportato / CSV / XLSX / DOCX con tabella / DOCX senza tabella / lock contract suffixes). |
| `tests/governance/test_log_events_catalog.py` | `_EXEMPT_FILES` + `document_parser.py` (continue benigno: skip pagine vuote in loop interno; R-01 effettivo via ValueError al confine). |

## Tests

ruff/format/mypy strict OK. Pytest **875 PASS** (737 unit/gov/golden + 138 integration). Risk LOW (additive, no formule core).

## Refs

- ADR-0016 (UI Streamlit), ADR-0017 (acquisizione dati), ADR-0019 (test).
- Predecessori: CHG-2026-05-02-{001..006}.
- Direttive Leader: "supporto xlsx/docx/pdf oltre csv" + "ingegnerizza UI bella sobria miracolosa".
- Commit: TBD.
