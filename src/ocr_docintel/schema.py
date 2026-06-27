# TRD §4.4 JSON 출력 스키마 정의
JSON_SCHEMA = {
    "type": "object",
    "required": ["document_title", "source_format", "elements"],
    "properties": {
        "document_title": {"type": "string"},
        "source_format": {"enum": ["pdf", "hwp", "docx", "xlsx", "image"]},
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "level", "order", "source", "content"],
                "properties": {
                    "type": {"enum": ["heading", "paragraph", "table", "image", "caption", "list"]},
                    "level": {"type": "integer", "minimum": 0},
                    "order": {"type": "integer", "minimum": 0},
                    "source": {
                        "type": "object",
                        "properties": {
                            "page": {"type": ["integer", "array", "null"]},
                            "sheet": {"type": ["string", "null"]},
                            "bbox": {"type": ["array", "null"]},
                            "spans_pages": {"type": "boolean"},
                        },
                    },
                    "content": {"type": ["string", "array"]},
                },
            },
        },
    },
}
