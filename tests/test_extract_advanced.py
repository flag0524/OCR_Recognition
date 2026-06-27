# 다단 읽기순서 + 페이지 횡단 표 병합 E2E 추출 테스트
from ocr_docintel.extract_pdf import extract


def test_two_column_reading_order(two_column_pdf):
    doc = extract(two_column_pdf)
    paras = [str(e.content) for e in sorted(doc.elements, key=lambda x: x.order)
             if e.type in ("paragraph", "heading")]
    text = " ".join(paras)
    # 좌단 두 줄이 우단보다 먼저 등장해야 한다.
    assert text.index("LEFT") < text.index("RIGHT")
    # 좌단 내부 순서: one 먼저.
    assert text.index("LEFT one") < text.index("LEFT two")


def test_cross_page_table_merged(cross_page_table_pdf):
    doc = extract(cross_page_table_pdf)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1, "두 페이지 표가 하나로 병합되어야 함"
    t = tables[0]
    assert t.source.spans_pages is True
    assert t.source.page == [1, 2]
    flat = [cell for row in t.content for cell in row]
    # 양 페이지 데이터가 모두 포함.
    for v in ("A", "B", "C", "D"):
        assert v in flat
