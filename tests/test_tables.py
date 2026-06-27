# 표 병합셀 정규화 + 페이지 횡단 병합 단위 테스트
from ocr_docintel.ir import Element, Source
from ocr_docintel.tables import normalize_table, is_continuation, merge_cross_page


def test_normalize_none_to_blank():
    # 병합셀 확장부(None)는 빈 칸으로, 짧은 행은 패딩.
    rows = [["헤더", None, "값"], ["A", "B"]]
    out = normalize_table(rows)
    assert out == [["헤더", "", "값"], ["A", "B", ""]]


def test_normalize_newline_to_br():
    out = normalize_table([["줄1\n줄2"]])
    assert out == [["줄1<br>줄2"]]


def _table(order, page, rows):
    return Element(type="table", order=order, content=rows,
                   source=Source(page=page, bbox=[0, 0, 1, 1]))


def test_is_continuation_same_columns_next_page():
    t1 = _table(0, 1, [["a", "b"], ["1", "2"]])
    t2 = _table(1, 2, [["3", "4"]])
    assert is_continuation(t1, t2)


def test_is_continuation_rejects_different_columns():
    t1 = _table(0, 1, [["a", "b"]])
    t2 = _table(1, 2, [["x", "y", "z"]])
    assert not is_continuation(t1, t2)


def test_merge_cross_page():
    t1 = _table(0, 1, [["항목", "값"], ["A", "1"]])
    t2 = _table(1, 2, [["B", "2"]])
    merged = merge_cross_page([t1, t2])
    assert len(merged) == 1
    m = merged[0]
    assert m.content == [["항목", "값"], ["A", "1"], ["B", "2"]]
    assert m.source.page == [1, 2]
    assert m.source.spans_pages is True


def test_merge_keeps_non_adjacent_separate():
    # 사이에 단락이 끼면 병합하지 않는다.
    t1 = _table(0, 1, [["a", "b"]])
    para = Element(type="paragraph", order=1, content="중간 문단", source=Source(page=1))
    t2 = _table(2, 2, [["c", "d"]])
    merged = merge_cross_page([t1, para, t2])
    assert len([e for e in merged if e.type == "table"]) == 2
