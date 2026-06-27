# 직렬화 단위 테스트 (MD 구조 + JSON 스키마 키)
import json
from ocr_docintel.ir import Document, Element, Source
from ocr_docintel.serialize import to_markdown, to_json


def _doc():
    return Document(
        document_title="제목",
        source_format="pdf",
        elements=[
            Element(type="heading", order=0, level=1, content="제목", source=Source(page=1, bbox=[0, 0, 1, 1])),
            Element(type="paragraph", order=1, content="본문입니다.", source=Source(page=1, bbox=[0, 1, 1, 2])),
            Element(type="table", order=2, content=[["A", "B"], ["1", "2"]], source=Source(page=1, bbox=[0, 2, 1, 3])),
        ],
    )


def test_markdown_structure():
    md = to_markdown(_doc())
    assert md.startswith("# 제목")
    assert "*본 문서 분석 결과는 원본의 레이아웃을 기반으로 작성되었습니다.*" in md
    assert "---" in md
    assert "| A | B |" in md
    assert "| --- | --- |" in md


def _doc_multipage():
    return Document(
        document_title="제목",
        source_format="pdf",
        elements=[
            Element(type="heading", order=0, level=1, content="제목", source=Source(page=1)),
            Element(type="paragraph", order=1, content="1페이지 본문.", source=Source(page=1)),
            Element(type="paragraph", order=2, content="2페이지 본문.", source=Source(page=2)),
            Element(type="table", order=3, content=[["A", "B"]], source=Source(page=[2, 3], spans_pages=True)),
        ],
    )


def test_paginate_inserts_page_delimiters():
    md = to_markdown(_doc_multipage(), paginate=True)
    assert "----- 페이지 1 -----" in md
    assert "----- 페이지 2 -----" in md
    # 페이지 1 구분자가 2페이지 본문보다 앞에 와야 한다.
    assert md.index("----- 페이지 1 -----") < md.index("1페이지 본문.")
    assert md.index("----- 페이지 2 -----") < md.index("2페이지 본문.")
    # 페이지 횡단 표(page=[2,3])는 대표 페이지 2를 따라가므로 새 구분자를 만들지 않는다.
    assert md.count("----- 페이지 2 -----") == 1
    assert "----- 페이지 3 -----" not in md


def test_paginate_off_by_default():
    md = to_markdown(_doc_multipage())
    assert "----- 페이지" not in md


def test_json_keys():
    data = json.loads(to_json(_doc()))
    assert data["document_title"] == "제목"
    assert data["source_format"] == "pdf"
    assert data["elements"][0]["type"] == "heading"
    assert data["elements"][2]["content"] == [["A", "B"], ["1", "2"]]
