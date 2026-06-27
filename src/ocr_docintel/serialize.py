# IR(Document)을 Markdown(System Prompt §5)과 JSON(TRD §4.4)으로 직렬화
from __future__ import annotations
import json

from .ir import Document

MD_HEADER_NOTE = "*본 문서 분석 결과는 원본의 레이아웃을 기반으로 작성되었습니다.*"


def _table_to_md(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    ncol = len(header)
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join(["---"] * ncol) + " |")
    for row in rows[1:]:
        cells = row + [""] * (ncol - len(row))
        lines.append("| " + " | ".join(cells[:ncol]) + " |")
    return "\n".join(lines)


def _primary_page(el) -> object:
    """요소의 대표 페이지. 페이지 횡단 병합(list)이면 첫 페이지."""
    p = el.source.page
    if isinstance(p, list):
        return p[0] if p else None
    return p


def to_markdown(doc: Document, paginate: bool = False) -> str:
    """System Prompt §5 구조의 마크다운 생성.

    paginate=True이면 페이지가 바뀔 때마다 구분자(`----- 페이지 N -----`)를 삽입한다.
    페이지 정보가 없는 포맷(xlsx/hwp 등)에서는 구분자가 생기지 않는다."""
    out = [f"# {doc.document_title}", "", MD_HEADER_NOTE, "", "---", ""]
    cur_page = None
    for el in sorted(doc.elements, key=lambda x: x.order):
        if paginate:
            pg = _primary_page(el)
            if pg is not None and pg != cur_page:
                cur_page = pg
                out += [f"----- 페이지 {pg} -----", ""]
        if el.type == "heading":
            level = min(max(el.level, 1), 4)
            out.append(f"{'#' * level} {el.content}")
        elif el.type == "paragraph":
            out.append(str(el.content))
        elif el.type == "list":
            out.append(str(el.content))
        elif el.type == "table":
            out.append(_table_to_md(el.content))
        elif el.type == "caption":
            out.append(f"> {el.content}")
        elif el.type == "image":
            out.append(f"![[Image/Chart]: {el.content}]")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def to_json(doc: Document, indent: int = 2) -> str:
    return json.dumps(doc.to_dict(), ensure_ascii=False, indent=indent)
