# 출력 검증 단위 테스트 (비규격 차단)
import pytest
from ocr_docintel.validate import validate_json, validate_markdown, ValidationError


def test_valid_json():
    validate_json({
        "document_title": "t", "source_format": "pdf",
        "elements": [{"type": "paragraph", "level": 0, "order": 0,
                      "source": {"page": 1, "sheet": None, "bbox": [0, 0, 1, 1]}, "content": "x"}],
    })


def test_invalid_json_type():
    with pytest.raises(ValidationError):
        validate_json({"document_title": "t", "source_format": "pdf",
                       "elements": [{"type": "bogus", "level": 0, "order": 0,
                                     "source": {}, "content": "x"}]})


def test_invalid_markdown():
    with pytest.raises(ValidationError):
        validate_markdown("그냥 텍스트")


def test_valid_markdown():
    md = "# 제목\n\n*본 문서 분석 결과는 원본의 레이아웃을 기반으로 작성되었습니다.*\n\n---\n\n본문\n"
    validate_markdown(md)
