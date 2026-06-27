# 출력물의 규격 준수를 검사해 비규격 출력을 차단하는 검증 모듈 (TRD §5, §7)
from __future__ import annotations
import json

import jsonschema

from .schema import JSON_SCHEMA


class ValidationError(ValueError):
    pass


def validate_json(data) -> None:
    """JSON 문자열 또는 dict가 스키마를 만족하는지 검사."""
    if isinstance(data, str):
        data = json.loads(data)
    try:
        jsonschema.validate(data, JSON_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"JSON 스키마 위반: {e.message}") from e


def validate_markdown(md: str) -> None:
    """System Prompt §5 필수 구조(제목/안내문/구분선)를 검사."""
    lines = md.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValidationError("첫 줄은 '# 문서제목'이어야 함")
    if "*본 문서 분석 결과는 원본의 레이아웃을 기반으로 작성되었습니다.*" not in md:
        raise ValidationError("필수 안내문 누락")
    if "---" not in md:
        raise ValidationError("구분선(---) 누락")
