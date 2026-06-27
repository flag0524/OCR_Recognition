# 표 정규화(병합셀)와 페이지 횡단 표 병합을 담당하는 모듈 (PRD FR-3, 개발계획서 §6.1)
from __future__ import annotations

from .ir import Element


def normalize_table(rows):
    """표를 직사각형 그리드로 정규화. None(병합셀 확장부)은 빈 문자열로 둔다.

    System Prompt §3.3: 병합셀은 대표 셀에 값, 확장부는 빈 칸으로 표현.
    pdfplumber는 병합셀 확장부를 None으로 돌려주므로 그대로 ""로 보존한다.
    """
    if not rows:
        return rows
    ncol = max(len(r) for r in rows)
    out = []
    for r in rows:
        cells = [("" if c is None else str(c).replace("\n", "<br>")) for c in r]
        cells += [""] * (ncol - len(cells))
        out.append(cells)
    return out


def _near_bottom(bbox, page_h, ratio):
    """표 하단(y1)이 페이지 하단부에 있는지. pdfplumber 좌표는 상단 원점(y 증가=아래)."""
    return bbox is not None and page_h and bbox[3] >= ratio * page_h


def _near_top(bbox, page_h, ratio):
    """표 상단(y0)이 페이지 상단부에 있는지."""
    return bbox is not None and page_h and bbox[1] <= (1 - ratio) * page_h


def is_continuation(prev: Element, nxt: Element, page_heights=None, edge_ratio=0.5) -> bool:
    """nxt 표가 prev 표의 페이지 횡단 연속인지 판정.

    조건: 둘 다 표 · 연속 페이지 · 동일 열 수.
    page_heights(페이지→높이) 제공 시 추가로 prev는 페이지 하단부, nxt는 상단부에
    위치해야 함(over-merge 방지). 헤더 반복은 연속의 강한 신호로 위치 조건을 면제.
    """
    if prev.type != "table" or nxt.type != "table":
        return False
    pp, np_ = prev.source.page, nxt.source.page
    pp = pp[-1] if isinstance(pp, list) else pp  # 이미 병합된 경우 마지막 페이지 기준.
    if not isinstance(pp, int) or not isinstance(np_, int) or np_ != pp + 1:
        return False
    pncol = max((len(r) for r in prev.content), default=0)
    nncol = max((len(r) for r in nxt.content), default=0)
    if pncol != nncol or pncol == 0:
        return False

    header_repeats = bool(nxt.content) and bool(prev.content) and nxt.content[0] == prev.content[0]
    if header_repeats:
        return True  # 헤더가 반복되면 위치 무관하게 연속으로 본다.

    if page_heights:
        hp, hn = page_heights.get(pp), page_heights.get(np_)
        if not (_near_bottom(prev.source.bbox, hp, edge_ratio)
                and _near_top(nxt.source.bbox, hn, edge_ratio)):
            return False  # 페이지 경계에 붙지 않은 별개 표는 병합 거부.
    return True


def merge_cross_page(elements: list[Element], page_heights=None, edge_ratio=0.5) -> list[Element]:
    """연속 페이지의 연속 표를 하나로 병합. 인접한 표만 대상(사이에 다른 요소 없을 때).

    반복된 헤더 행은 병합 시 1회만 남긴다(over-merge 정밀화).
    """
    ordered = sorted(elements, key=lambda e: e.order)
    result: list[Element] = []
    for el in ordered:
        if result and is_continuation(result[-1], el, page_heights, edge_ratio):
            prev = result[-1]
            rows = el.content
            if rows and prev.content and rows[0] == prev.content[0]:
                rows = rows[1:]  # 반복 헤더 제거.
            prev.content = prev.content + rows
            pages = prev.source.page if isinstance(prev.source.page, list) else [prev.source.page]
            prev.source.page = pages + [el.source.page]
            prev.source.spans_pages = True
        else:
            result.append(el)
    for i, el in enumerate(result):
        el.order = i
    return result
