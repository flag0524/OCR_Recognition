# 추출 결과의 중간표현(IR) 데이터모델 — 라이브러리/LLM/직렬화가 공유하는 단일 계약
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional

# 요소 타입은 TRD §4.4 스키마와 일치시킨다.
ELEMENT_TYPES = ("heading", "paragraph", "table", "image", "caption", "list")


@dataclass
class Source:
    """원본 위치 정보. bbox는 [x0, y0, x1, y1] (PDF 좌상단 기준).

    page는 단일 페이지(int) 또는 페이지 횡단 병합 시 페이지 목록(list[int])."""
    page: Optional[object] = None  # int | list[int] | None
    sheet: Optional[str] = None
    bbox: Optional[list[float]] = None
    spans_pages: bool = False  # 페이지 횡단 병합 표(개발계획서 §6.1)


@dataclass
class Element:
    """추출된 단일 구조 요소."""
    type: str
    order: int
    content: object  # 텍스트(str) 또는 표(list[list[str]])
    level: int = 0
    source: Source = field(default_factory=Source)

    def __post_init__(self):
        if self.type not in ELEMENT_TYPES:
            raise ValueError(f"미지원 요소 타입: {self.type}")

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "level": self.level,
            "order": self.order,
            "source": asdict(self.source),
            "content": self.content,
        }


@dataclass
class Document:
    """문서 전체 IR."""
    document_title: str
    source_format: str
    elements: list[Element] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "document_title": self.document_title,
            "source_format": self.source_format,
            "elements": [e.to_dict() for e in sorted(self.elements, key=lambda x: x.order)],
        }
