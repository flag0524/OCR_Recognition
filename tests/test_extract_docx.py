# DOCX 파서 테스트
from ocr_docintel.extract_docx import extract
from ocr_docintel.pipeline import process


def test_headings_and_emphasis(docx_file):
    doc = extract(docx_file)
    assert doc.source_format == "docx"
    assert doc.document_title == "문서 제목"
    h1 = [e for e in doc.elements if e.type == "heading" and e.level == 1]
    h2 = [e for e in doc.elements if e.type == "heading" and e.level == 2]
    assert h1 and h2
    # 굵게 강조가 마크다운으로 변환.
    para = next(e for e in doc.elements if e.type == "paragraph" and "강조" in str(e.content))
    assert "**굵게**" in para.content


def test_list_and_table(docx_file):
    doc = extract(docx_file)
    lists = [e for e in doc.elements if e.type == "list"]
    assert any("첫째 항목" in str(e.content) for e in lists)
    tables = [e for e in doc.elements if e.type == "table"]
    assert tables and tables[0].content[0] == ["헤더A", "헤더B"]


def test_docx_e2e(docx_file):
    res = process(docx_file, use_llm=False)
    assert res.markdown.startswith("# 문서 제목")
    assert "## 개요" in res.markdown
