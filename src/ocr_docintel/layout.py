# 다단(multi-column) 레이아웃을 gap 기반으로 검출해 읽기 순서를 정밀화하는 모듈 (PRD FR-1)
from __future__ import annotations


def detect_column_boundaries(blocks, page_width, min_gap_ratio=0.05, wide_ratio=0.6):
    """텍스트 블록들의 x 범위에서 빈틈(gap)을 찾아 컬럼 경계를 반환.

    - 전폭(wide) 블록(표·제목 등 page_width*wide_ratio 이상)은 컬럼 추정에서 제외.
    - 인접 x구간 사이 간격이 page_width*min_gap_ratio 초과면 별도 컬럼으로 분리.
    반환: [(x0, x1), ...] 좌→우 정렬된 컬럼 구간. 검출 실패 시 단일 컬럼.
    """
    narrow = [
        b for b in blocks
        if (b["bbox"][2] - b["bbox"][0]) < wide_ratio * page_width
    ]
    if not narrow:
        return [(0.0, page_width)]

    intervals = sorted((b["bbox"][0], b["bbox"][2]) for b in narrow)
    gap = min_gap_ratio * page_width
    merged = [list(intervals[0])]
    for x0, x1 in intervals[1:]:
        if x0 <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    return [(a, b) for a, b in merged]


def column_index(bbox, columns):
    """블록 중심 x가 속한(또는 가장 가까운) 컬럼 인덱스를 반환."""
    cx = (bbox[0] + bbox[2]) / 2
    for i, (x0, x1) in enumerate(columns):
        if x0 <= cx <= x1:
            return i
    # 어떤 컬럼에도 안 들면 가장 가까운 컬럼.
    return min(
        range(len(columns)),
        key=lambda i: abs(cx - (columns[i][0] + columns[i][1]) / 2),
    )


def reading_order_key(bbox, columns):
    """다단 인식 읽기 순서 키: (컬럼 인덱스, y, x)."""
    return (column_index(bbox, columns), round(bbox[1], 1), round(bbox[0], 1))
