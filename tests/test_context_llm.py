# Claude API 맥락 단계 운영 검증: 가짜 클라이언트로 grounded 동작 확인 + 실호출은 키 있을 때만
import os
import json
import pytest

from ocr_docintel.ir import Document, Element, Source
from ocr_docintel.context_llm import refine


class _Resp:
    def __init__(self, text):
        self.content = [type("B", (), {"text": text})()]


class FakeClient:
    """messages.create를 흉내내는 가짜 Anthropic 클라이언트."""
    def __init__(self, reply):
        self._reply = reply
        self.calls = []

        outer = self

        class _Messages:
            def create(self, **kwargs):
                outer.calls.append(kwargs)
                return _Resp(outer._reply)
        self.messages = _Messages()


def _doc():
    return Document(
        document_title="d", source_format="pdf",
        elements=[
            Element(type="paragraph", order=0, content="Chapter Title",
                    source=Source(page=1, bbox=[0, 0, 1, 1])),
            Element(type="paragraph", order=1, content="본문 단락.",
                    source=Source(page=1, bbox=[0, 1, 1, 2])),
        ],
    )


def test_grounded_reclassification_accepted():
    # LLM이 첫 단락을 heading level1로 재분류(텍스트는 동일) → 수용.
    reply = json.dumps([
        {"order": 0, "type": "heading", "level": 1, "content": "Chapter Title"},
        {"order": 1, "type": "paragraph", "level": 0, "content": "본문 단락."},
    ])
    doc = refine(_doc(), client=FakeClient(reply))
    el0 = next(e for e in doc.elements if e.order == 0)
    assert el0.type == "heading" and el0.level == 1


def test_grounded_rejects_text_alteration():
    # LLM이 content를 바꾸면(hallucination) 무시하고 원본 유지.
    reply = json.dumps([
        {"order": 0, "type": "heading", "level": 1, "content": "조작된 제목"},
        {"order": 1, "type": "paragraph", "level": 0, "content": "본문 단락."},
    ])
    doc = refine(_doc(), client=FakeClient(reply))
    el0 = next(e for e in doc.elements if e.order == 0)
    assert el0.content == "Chapter Title"      # 텍스트 보존
    assert el0.type == "paragraph"             # 조작 교정 거부


def test_malformed_reply_falls_back():
    doc = refine(_doc(), client=FakeClient("이건 JSON이 아님"))
    assert all(e.type == "paragraph" for e in doc.elements)  # 폴백


def test_code_fence_reply_parsed():
    reply = "```json\n" + json.dumps([
        {"order": 0, "type": "heading", "level": 2, "content": "Chapter Title"},
    ]) + "\n```"
    doc = refine(_doc(), client=FakeClient(reply))
    el0 = next(e for e in doc.elements if e.order == 0)
    assert el0.type == "heading" and el0.level == 2


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"),
                    reason="실 API 키 없음 — 실호출 검증 생략")
def test_real_api_smoke():
    # 키가 있을 때만 도는 실호출 스모크: 파이프라인이 예외 없이 끝나는지.
    doc = refine(_doc(), use_llm=True)
    assert len(doc.elements) == 2
    assert all(isinstance(e.content, str) for e in doc.elements)
