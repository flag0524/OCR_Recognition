# 다단 컬럼 검출 단위 테스트
from ocr_docintel.layout import detect_column_boundaries, column_index, reading_order_key


def _b(x0, y0, x1, y1):
    return {"bbox": [x0, y0, x1, y1]}


def test_single_column():
    blocks = [_b(72, 100, 300, 120), _b(72, 130, 300, 150)]
    cols = detect_column_boundaries(blocks, page_width=595)
    assert len(cols) == 1


def test_two_columns():
    # 좌 컬럼(72~280), 우 컬럼(320~520), 그 사이 큰 gap.
    blocks = [_b(72, 100, 280, 120), _b(72, 130, 280, 150),
              _b(320, 100, 520, 120), _b(320, 130, 520, 150)]
    cols = detect_column_boundaries(blocks, page_width=595)
    assert len(cols) == 2
    assert column_index([72, 100, 280, 120], cols) == 0
    assert column_index([320, 100, 520, 120], cols) == 1


def test_reading_order_left_column_first():
    blocks = [_b(72, 100, 280, 120), _b(320, 90, 520, 110)]
    cols = detect_column_boundaries(blocks, page_width=595)
    # 우측이 더 위(y=90)지만 좌측 컬럼이 먼저 와야 한다.
    keys = sorted(blocks, key=lambda b: reading_order_key(b["bbox"], cols))
    assert keys[0]["bbox"][0] == 72


def test_wide_block_excluded():
    # 전폭 표 같은 블록은 컬럼 추정에서 제외 → 좁은 두 블록으로 2컬럼 유지.
    blocks = [_b(72, 100, 280, 120), _b(320, 100, 520, 120), _b(72, 200, 520, 260)]
    cols = detect_column_boundaries(blocks, page_width=595)
    assert len(cols) == 2
