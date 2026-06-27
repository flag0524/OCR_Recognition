# 스캔 이미지/텍스트 없는 PDF 페이지를 Tesseract OCR로 추출하는 모듈 (TRD §3.2, PRD FR-1)
from __future__ import annotations
import os
import shutil
from pathlib import Path

from .ir import Document, Element, Source

# 한국어+영문 혼용 우선, 실패 시 기본 언어로 폴백(개발계획서 §2.3 한/영 혼용).
_DEFAULT_LANG = "kor+eng"

# PATH에 없을 때 탐색할 Windows 기본 설치 경로.
_WINDOWS_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _resolve_tesseract_cmd():
    """pytesseract가 쓸 바이너리 경로를 해석. PATH 우선, 없으면 알려진 설치 경로."""
    import pytesseract
    env = os.environ.get("TESSERACT_CMD")
    candidates = ([env] if env else []) + [shutil.which("tesseract")] + list(_WINDOWS_CANDIDATES)
    for c in candidates:
        if c and Path(c).exists():
            pytesseract.pytesseract.tesseract_cmd = c
            return c
    return pytesseract.pytesseract.tesseract_cmd  # 기본값(PATH) 시도


def tesseract_available() -> bool:
    """Tesseract 바이너리 설치 여부(PATH 밖 기본 설치 경로 포함)."""
    try:
        import pytesseract
        _resolve_tesseract_cmd()
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


class TesseractUnavailableError(RuntimeError):
    """Tesseract 미설치 시 명확히 분기(TRD §6)."""


def _join_line(words, gap_ratio=0.35):
    """한 줄의 단어들을 좌표 간격 기반으로 결합.

    tesseract는 한국어를 글자 단위 '단어'로 쪼개므로, 인접 단어 간 간격이
    글자 높이의 gap_ratio 미만이면 붙이고(예: 대+한→대한), 크면 공백을 둔다.
    """
    words = sorted(words, key=lambda w: w["x"])
    if not words:
        return ""
    avg_h = sum(w["h"] for w in words) / len(words)
    out = words[0]["t"]
    for prev, cur in zip(words, words[1:]):
        gap = cur["x"] - (prev["x"] + prev["w"])
        out += (" " if gap > gap_ratio * avg_h else "") + cur["t"]
    return out


def _words_to_paragraphs(data, page_no, start_order):
    """image_to_data 결과를 (block,par) 단락 Element로 묶는다. 좌표 보존(grounded)."""
    groups: dict[tuple, dict] = {}
    n = len(data["text"])
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        key = (data["block_num"][i], data["par_num"][i])
        line = data["line_num"][i]
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        g = groups.setdefault(key, {"lines": {}, "x0": x, "y0": y, "x1": x + w, "y1": y + h})
        g["lines"].setdefault(line, []).append({"t": txt, "x": x, "y": y, "w": w, "h": h})
        g["x0"], g["y0"] = min(g["x0"], x), min(g["y0"], y)
        g["x1"], g["y1"] = max(g["x1"], x + w), max(g["y1"], y + h)

    elements = []
    order = start_order
    for key in sorted(groups):  # (block, par) 순 = 읽기 순서
        g = groups[key]
        text = " ".join(_join_line(g["lines"][ln]) for ln in sorted(g["lines"]))
        elements.append(Element(
            type="paragraph", order=order, level=0, content=text,
            source=Source(page=page_no, bbox=[float(g["x0"]), float(g["y0"]),
                                              float(g["x1"]), float(g["y1"])]),
        ))
        order += 1
    return elements


# psm 4(가변 크기 단일 컬럼): 한국어 인쇄체에서 psm 3(자동)보다 안정적.
_DEFAULT_CONFIG = "--psm 4"


def ocr_image_elements(image, page_no=1, start_order=0, lang=_DEFAULT_LANG, config=_DEFAULT_CONFIG):
    """PIL 이미지 → 단락 Element 목록. lang 미설치 시 기본 언어로 폴백."""
    if not tesseract_available():
        raise TesseractUnavailableError("Tesseract 바이너리가 설치되어 있지 않습니다.")
    import pytesseract
    from pytesseract import Output
    try:
        data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=Output.DICT)
    except pytesseract.TesseractError:
        data = pytesseract.image_to_data(image, config=config, output_type=Output.DICT)  # 언어팩 폴백
    return _words_to_paragraphs(data, page_no, start_order)


def extract_image(path: str | Path) -> Document:
    """이미지 파일(PNG/JPG 등) → Document(IR)."""
    from PIL import Image
    path = Path(path)
    with Image.open(path) as img:
        elements = ocr_image_elements(img.convert("RGB"), page_no=1)
    return Document(document_title=path.stem, source_format="image", elements=elements)
