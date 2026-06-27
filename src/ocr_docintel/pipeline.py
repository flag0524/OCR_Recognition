# 5단계 파이프라인 오케스트레이션: 식별→추출→맥락→직렬화→검증 (TRD §2)
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

from . import (identify, extract_pdf, extract_docx, extract_xlsx, extract_hwp,
               ocr_scan, context_llm, serialize, validate)
from .ir import Document


@dataclass
class Result:
    document: Document
    markdown: str
    json: str


def process(path: str | Path, use_llm: bool = True) -> Result:
    """입력 파일을 처리해 MD+JSON을 반환. 비규격 출력은 검증 단계에서 차단."""
    fmt = identify.identify(path)  # 1. 식별 (미지원이면 예외)
    extractors = {
        "pdf": extract_pdf.extract,      # 텍스트 PDF + 스캔 페이지 OCR 폴백
        "image": ocr_scan.extract_image,  # 스캔 이미지
        "docx": extract_docx.extract,
        "xlsx": extract_xlsx.extract,
        "hwp": extract_hwp.extract,
    }
    if fmt not in extractors:
        raise identify.UnsupportedFormatError(f"미지원 포맷: {fmt}")

    doc = extractors[fmt](path)                  # 2. 결정론적 추출
    doc = context_llm.refine(doc, use_llm=use_llm)  # 3. 맥락 교정(폴백)
    md = serialize.to_markdown(doc)              # 4. 직렬화
    js = serialize.to_json(doc)
    validate.validate_json(js)                   # 5. 검증
    validate.validate_markdown(md)
    return Result(document=doc, markdown=md, json=js)
