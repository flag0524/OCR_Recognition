# 페이지 횡단 over-merge 정밀화 테스트 (헤더 반복 제거 + 위치 근접성)
from ocr_docintel.ir import Element, Source
from ocr_docintel.tables import merge_cross_page, is_continuation


def _t(order, page, rows, bbox):
    return Element(type="table", order=order, content=rows, source=Source(page=page, bbox=bbox))


def test_repeated_header_dropped():
    # 연속 표가 헤더를 반복하면 병합 시 1회만 남긴다.
    h = ["항목", "값"]
    t1 = _t(0, 1, [h, ["A", "1"]], [0, 700, 100, 780])
    t2 = _t(1, 2, [h, ["B", "2"]], [0, 20, 100, 100])
    merged = merge_cross_page([t1, t2], page_heights={1: 800, 2: 800})
    assert len(merged) == 1
    assert merged[0].content == [h, ["A", "1"], ["B", "2"]]


def test_position_guard_blocks_unrelated():
    # 같은 열 수·연속 페이지라도 prev가 상단에서 끝나고 nxt가 하단에서 시작하면 병합 거부.
    t1 = _t(0, 1, [["a", "b"], ["1", "2"]], [0, 100, 100, 200])  # 상단에서 끝남(하단부 아님)
    t2 = _t(1, 2, [["3", "4"]], [0, 600, 100, 700])             # 하단에서 시작(상단부 아님)
    merged = merge_cross_page([t1, t2], page_heights={1: 800, 2: 800})
    assert len([e for e in merged if e.type == "table"]) == 2


def test_position_guard_allows_boundary():
    # 헤더 반복은 없지만 prev 하단 + nxt 상단이면 병합.
    t1 = _t(0, 1, [["a", "b"], ["1", "2"]], [0, 720, 100, 790])
    t2 = _t(1, 2, [["3", "4"]], [0, 15, 100, 90])
    merged = merge_cross_page([t1, t2], page_heights={1: 800, 2: 800})
    assert len(merged) == 1
    assert merged[0].source.spans_pages is True


def test_no_geometry_falls_back_to_columns():
    # page_heights 없으면 기존 동작(동일 열수면 병합) 유지.
    t1 = _t(0, 1, [["a", "b"]], None)
    t2 = _t(1, 2, [["c", "d"]], None)
    assert is_continuation(t1, t2)
