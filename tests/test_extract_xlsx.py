# XLSX 파서 테스트 (병합셀 + 다중시트)
from ocr_docintel.extract_xlsx import extract
from ocr_docintel.pipeline import process


def test_multi_sheet(xlsx_file):
    doc = extract(xlsx_file)
    assert doc.source_format == "xlsx"
    sheet_headings = [e for e in doc.elements if e.type == "heading"]
    titles = [e.content for e in sheet_headings]
    assert "Sheet: 매출" in titles and "Sheet: 비용" in titles


def test_merged_cell_blanks(xlsx_file):
    doc = extract(xlsx_file)
    # 매출 시트 표: 병합 A4:C4 → 대표셀에 값, 나머지 빈칸.
    table = next(e for e in doc.elements if e.type == "table")
    merged_row = next(r for r in table.content if r and r[0] == "병합제목")
    assert merged_row[1] == "" and merged_row[2] == ""


def test_xlsx_e2e(xlsx_file):
    res = process(xlsx_file, use_llm=False)
    assert "## Sheet: 매출" in res.markdown
    assert "| 구분 | 2024 | 2025 |" in res.markdown
