# HWP(한글) 문서에서 단락과 표를 추출하는 파서 (PRD FR-2, FR-5)
# 전략: pyhwp의 XHTML 변환으로 표(<table>)까지 복원하고, 실패 시 평문 텍스트로 폴백.
from __future__ import annotations
from pathlib import Path
import io

from lxml import html as lhtml

from .ir import Document, Element, Source
from .tables import normalize_table


class HwpExtractError(RuntimeError):
    """HWP 파싱 실패 시 명확히 분기(TRD §6)."""


def _table_rows(table_el):
    """<table> 요소를 2차원 문자열 그리드로. 셀 내 줄바꿈은 <br>."""
    rows = []
    for tr in table_el.iter("tr"):
        cells = []
        for cell in tr.xpath("./td|./th"):
            cells.append(cell.text_content().strip().replace("\n", "<br>"))
        if cells:
            rows.append(cells)
    return normalize_table(rows)


def _parse_xhtml(xhtml: str):
    """XHTML 문자열에서 (kind, payload)를 문서 순서대로 추출.

    표 내부 <p>는 표가 흡수하므로 별도 단락으로 내보내지 않는다.
    """
    root = lhtml.fromstring(xhtml)
    table_descendants = set()
    for t in root.iter("table"):
        for d in t.iter():
            if d is not t:
                table_descendants.add(d)

    results = []
    for el in root.iter():
        if el.tag == "table":
            rows = _table_rows(el)
            if rows:
                results.append(("table", rows))
        elif el in table_descendants:
            continue
        elif el.tag == "p":
            txt = el.text_content().strip()
            if txt:
                results.append(("para", txt))
    return results


def _xhtml_from_hwp(path: Path) -> str:
    from hwp5.xmlmodel import Hwp5File
    from hwp5.hwp5html import HTMLTransform
    buf = io.BytesIO()
    hwp = Hwp5File(str(path))
    try:
        HTMLTransform().transform_hwp5_to_xhtml(hwp, buf)
    finally:
        hwp.close()
    return buf.getvalue().decode("utf-8", errors="replace")


def _text_from_hwp(path: Path) -> str:
    from hwp5.xmlmodel import Hwp5File
    from hwp5.hwp5txt import TextTransform
    buf = io.BytesIO()
    hwp = Hwp5File(str(path))
    try:
        TextTransform().transform_hwp5_to_text(hwp, buf)
    finally:
        hwp.close()
    return buf.getvalue().decode("utf-8", errors="replace")


def _build(items_or_lines, path: Path) -> Document:
    elements: list[Element] = []
    order = 0
    for item in items_or_lines:
        kind, payload = item if isinstance(item, tuple) else ("para", item)
        if kind == "table":
            elements.append(Element(type="table", order=order, level=0,
                                    content=payload, source=Source()))
        else:
            elements.append(Element(type="paragraph", order=order, level=0,
                                    content=payload, source=Source()))
        order += 1
    return Document(document_title=path.stem, source_format="hwp", elements=elements)


def extract(path: str | Path) -> Document:
    """HWP → Document. 표 포함 XHTML 추출 우선, 실패 시 평문 단락 폴백."""
    path = Path(path)
    try:
        items = _parse_xhtml(_xhtml_from_hwp(path))
        return _build(items, path)
    except Exception:
        pass  # XHTML 변환 실패 → 평문 폴백 시도

    try:
        text = _text_from_hwp(path)
    except Exception as e:
        raise HwpExtractError(f"HWP 파싱 실패: {e}") from e
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return _build(lines, path)
