# 파일 시그니처(매직 넘버)와 확장자로 입력 포맷을 식별하는 모듈 (TRD §3.1)
from __future__ import annotations
from pathlib import Path

# 매직 넘버 → 포맷명. ZIP 컨테이너(docx/xlsx)는 확장자로 2차 분기.
_SIGNATURES = {
    b"%PDF": "pdf",
    b"PK\x03\x04": "zip",  # docx/xlsx 컨테이너
    b"\xd0\xcf\x11\xe0": "ole",  # 구 hwp/doc/xls (OLE)
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
}

SUPPORTED = {"pdf", "docx", "xlsx", "hwp", "image"}


class UnsupportedFormatError(ValueError):
    """미지원 포맷일 때 즉시 분기시키는 예외 (TRD §6)."""


def identify(path: str | Path) -> str:
    """파일 포맷을 반환. 미지원이면 UnsupportedFormatError."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)

    head = p.read_bytes()[:8]
    ext = p.suffix.lower().lstrip(".")

    sig = None
    for magic, name in _SIGNATURES.items():
        if head.startswith(magic):
            sig = name
            break

    if sig == "pdf":
        return "pdf"
    if sig in ("png", "jpg"):
        return "image"
    if sig == "zip":
        if ext in ("docx", "xlsx"):
            return ext
        raise UnsupportedFormatError(f"미지원 ZIP 기반 포맷: .{ext}")
    if sig == "ole" and ext == "hwp":
        return "hwp"

    raise UnsupportedFormatError(f"미지원 포맷 (sig={sig}, ext=.{ext})")
