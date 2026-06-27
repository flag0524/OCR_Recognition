# 텍스트 PDF 추출 단위 테스트
from ocr_docintel.extract_pdf import extract


def test_heading_and_paragraph(single_column_pdf):
    doc = extract(single_column_pdf)
    types = [e.type for e in sorted(doc.elements, key=lambda x: x.order)]
    assert "heading" in types
    assert "paragraph" in types
    # 가장 큰 폰트는 level 1.
    headings = [e for e in doc.elements if e.type == "heading"]
    assert any(e.level == 1 for e in headings)
    # 모든 요소에 좌표가 있다(grounded).
    assert all(e.source.bbox is not None for e in doc.elements)


def test_table_extracted(simple_table_pdf):
    doc = extract(simple_table_pdf)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    rows = tables[0].content
    assert rows[0] == ["Item", "2024", "2025"]
    assert ["Sales", "120", "150"] in rows
