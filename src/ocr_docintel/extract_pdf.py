# 텍스트 레이어 PDF에서 블록·좌표·표를 결정론적으로 추출해 IR로 변환 (TRD §3.3 PDF)
from __future__ import annotations
from pathlib import Path
from collections import Counter

import fitz  # PyMuPDF
import pdfplumber

from .ir import Document, Element, Source
from .layout import detect_column_boundaries, reading_order_key
from .tables import normalize_table, merge_cross_page
from . import ocr_scan


def _font_size_to_level(size: float, body: float) -> int:
    """폰트 크기를 제목 레벨로 매핑. body보다 크면 제목, 아니면 0(본문)."""
    ratio = size / body if body else 1.0
    if ratio >= 1.6:
        return 1
    if ratio >= 1.35:
        return 2
    if ratio >= 1.15:
        return 3
    if ratio >= 1.05:
        return 4
    return 0


def _bbox_overlaps(a, b) -> bool:
    """[x0,y0,x1,y1] 두 사각형이 겹치는지."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def _extract_tables(pdf_path: Path):
    """pdfplumber로 페이지별 표를 추출. (page_index, bbox, rows) 리스트."""
    out = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for pi, page in enumerate(pdf.pages):
            for tbl in page.find_tables():
                rows = tbl.extract()
                # 병합셀 확장부(None)를 빈 칸으로 보존하며 직사각형 정규화.
                out.append((pi, list(tbl.bbox), normalize_table(rows)))
    return out


def extract(pdf_path: str | Path) -> Document:
    """텍스트 PDF → Document(IR). 읽기순서·제목레벨·표를 결정론적으로 채운다."""
    pdf_path = Path(pdf_path)
    tables = _extract_tables(pdf_path)
    doc = fitz.open(str(pdf_path))

    # 본문 폰트 크기 추정(최빈값).
    sizes = []
    for page in doc:
        for blk in page.get_text("dict")["blocks"]:
            for line in blk.get("lines", []):
                for span in line["spans"]:
                    sizes.append(round(span["size"], 1))
    body_size = Counter(sizes).most_common(1)[0][0] if sizes else 12.0

    elements: list[Element] = []
    order = 0
    title = pdf_path.stem
    page_heights: dict[int, float] = {}

    for pi, page in enumerate(doc):
        page_heights[pi + 1] = page.rect.height

        # 텍스트 레이어가 없는 스캔 페이지는 OCR 경로로 보낸다(TRD §3.2).
        if not page.get_text().strip() and ocr_scan.tesseract_available():
            import fitz as _fitz  # noqa
            from PIL import Image
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            for el in ocr_scan.ocr_image_elements(img, page_no=pi + 1, start_order=order):
                elements.append(el)
                order += 1
            continue

        page_tables = [t for t in tables if t[0] == pi]
        table_bboxes = [t[1] for t in page_tables]

        text_blocks = []
        for blk in page.get_text("dict")["blocks"]:
            if "lines" not in blk:
                continue
            # 표 영역과 겹치는 텍스트 블록은 표가 흡수하므로 제외.
            if any(_bbox_overlaps(blk["bbox"], tb) for tb in table_bboxes):
                continue
            text = ""
            max_size = 0.0
            for line in blk["lines"]:
                for span in line["spans"]:
                    text += span["text"]
                    max_size = max(max_size, span["size"])
                text += "\n"
            text = text.strip()
            if text:
                text_blocks.append({"bbox": blk["bbox"], "text": text, "size": max_size})

        # 표를 위치 기준 항목으로 합쳐 읽기순서 정렬.
        items = []
        for tb in text_blocks:
            items.append(("text", tb))
        for (_, bbox, rows) in page_tables:
            items.append(("table", {"bbox": bbox, "rows": rows}))

        # 다단 정밀화: 텍스트 블록에서 컬럼 경계를 검출해 읽기 순서를 정한다.
        columns = detect_column_boundaries(text_blocks, page.rect.width)
        items.sort(key=lambda it: reading_order_key(it[1]["bbox"], columns))

        for kind, payload in items:
            if kind == "table":
                elements.append(Element(
                    type="table", order=order, level=0,
                    content=payload["rows"],
                    source=Source(page=pi + 1, bbox=[round(v, 1) for v in payload["bbox"]]),
                ))
            else:
                level = _font_size_to_level(payload["size"], body_size)
                etype = "heading" if level > 0 else "paragraph"
                # 첫 1레벨 제목은 문서 제목 후보.
                if etype == "heading" and level == 1 and title == pdf_path.stem:
                    title = payload["text"].splitlines()[0]
                elements.append(Element(
                    type=etype, order=order, level=level,
                    content=payload["text"],
                    source=Source(page=pi + 1, bbox=[round(v, 1) for v in payload["bbox"]]),
                ))
            order += 1

    doc.close()
    # 페이지 횡단 연속 표 병합(개발계획서 §6.1 spans_pages, 위치/헤더 기반 over-merge 방지).
    elements = merge_cross_page(elements, page_heights=page_heights)
    return Document(document_title=title, source_format="pdf", elements=elements)
