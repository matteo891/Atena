"""Unit test `talos.ui.document_parser` (CHG-2026-05-02-007)."""

from __future__ import annotations

import io

import pytest

from talos.ui.document_parser import SUPPORTED_SUFFIXES, parse_uploaded_document

pytestmark = pytest.mark.unit


def test_unsupported_suffix_raises() -> None:
    buf = io.BytesIO(b"x")
    with pytest.raises(ValueError, match="Formato non supportato"):
        parse_uploaded_document(buf, "txt")


def test_csv_dispatch() -> None:
    buf = io.BytesIO(b"descrizione,prezzo\nGalaxy S24,549\nGalaxy A54,329\n")
    df = parse_uploaded_document(buf, "csv")
    assert list(df.columns) == ["descrizione", "prezzo"]
    assert len(df) == 2


def test_xlsx_dispatch() -> None:
    from openpyxl import Workbook  # noqa: PLC0415

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["descrizione", "prezzo"])
    ws.append(["Galaxy S24", 549])
    ws.append(["Galaxy A54", 329])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    df = parse_uploaded_document(buf, "xlsx")
    assert list(df.columns) == ["descrizione", "prezzo"]
    assert len(df) == 2
    assert df.iloc[0]["descrizione"] == "Galaxy S24"
    assert int(df.iloc[0]["prezzo"]) == 549


def test_docx_dispatch_with_table() -> None:
    import docx  # noqa: PLC0415

    document = docx.Document()
    table = document.add_table(rows=3, cols=2)
    table.rows[0].cells[0].text = "descrizione"
    table.rows[0].cells[1].text = "prezzo"
    table.rows[1].cells[0].text = "Galaxy S24"
    table.rows[1].cells[1].text = "549"
    table.rows[2].cells[0].text = "Galaxy A54"
    table.rows[2].cells[1].text = "329"
    buf = io.BytesIO()
    document.save(buf)
    buf.seek(0)
    df = parse_uploaded_document(buf, "docx")
    assert list(df.columns) == ["descrizione", "prezzo"]
    assert len(df) == 2


def test_docx_no_matching_table_raises() -> None:
    import docx  # noqa: PLC0415

    document = docx.Document()
    document.add_paragraph("Solo testo, no tabelle.")
    buf = io.BytesIO()
    document.save(buf)
    buf.seek(0)
    with pytest.raises(ValueError, match="DOCX senza tabelle"):
        parse_uploaded_document(buf, "docx")


def test_supported_suffixes_includes_all_formats() -> None:
    assert {"csv", "xlsx", "pdf", "docx"}.issubset(SUPPORTED_SUFFIXES)
