

def test_multipage_pdf_is_stacked(tmp_path):
    import pymupdf as fitz

    from snap2sheet.ocr import _render_pdf

    single = tmp_path / "one.pdf"
    doc = fitz.open(); page = doc.new_page(); page.insert_text((72, 72), "One"); doc.save(single); doc.close()
    first = _render_pdf(single).shape[0]

    multi = tmp_path / "two.pdf"
    doc = fitz.open()
    for text in ("One", "Two"):
        page = doc.new_page(); page.insert_text((72, 72), text)
    doc.save(multi); doc.close()
    assert _render_pdf(multi).shape[0] > first
