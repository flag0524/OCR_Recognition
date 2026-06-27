# E2E 골든셋 회귀 + KPI 측정 (tests.md §4). LLM 폴백 경로로 오프라인 검증.
from ocr_docintel.pipeline import process
from ocr_docintel.validate import validate_json, validate_markdown


def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[n]


def cer(expected: str, actual: str) -> float:
    if not expected:
        return 0.0
    return _levenshtein(expected, actual) / len(expected)


def test_e2e_single_column(single_column_pdf):
    res = process(single_column_pdf, use_llm=False)  # 폴백 경로
    # 스키마 준수 100%
    validate_json(res.json)
    validate_markdown(res.markdown)
    # CER: 기대 본문이 출력에 거의 그대로 들어있어야 함
    expected = "This is the first body paragraph of the report."
    para = next(e for e in res.document.elements
                if e.type == "paragraph" and "first body" in str(e.content))
    assert cer(expected, str(para.content).splitlines()[0]) <= 0.01
    # 읽기순서: 제목이 본문보다 앞
    orders = {e.type: e.order for e in res.document.elements if e.type in ("heading", "paragraph")}
    assert min(e.order for e in res.document.elements if e.type == "heading") \
        < min(e.order for e in res.document.elements if e.type == "paragraph")


def test_e2e_table(simple_table_pdf):
    res = process(simple_table_pdf, use_llm=False)
    validate_json(res.json)
    validate_markdown(res.markdown)
    tbl = next(e for e in res.document.elements if e.type == "table")
    exp = [["Item", "2024", "2025"], ["Sales", "120", "150"], ["Cost", "80", "90"]]
    # 표 셀 일치율 ≥ 95%
    total = sum(len(r) for r in exp)
    match = 0
    for er, ar in zip(exp, tbl.content):
        for ec, ac in zip(er, ar):
            if ec == ac:
                match += 1
    assert match / total >= 0.95
    # MD에 표가 GFM으로 들어감
    assert "| Item | 2024 | 2025 |" in res.markdown
