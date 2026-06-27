# Claude API로 IR의 맥락(읽기순서/제목레벨/캡션)을 교정하고, 키가 없으면 결정론적 폴백 (개발계획서 §4.1)
from __future__ import annotations
import os
import json

from .ir import Document, Element, Source

# grounded 원칙: LLM은 기존 블록의 재분류/재배열만 한다. 새 텍스트 생성 금지.
_SYSTEM = (
    "당신은 문서 구조 정규화기다. 입력으로 좌표가 있는 텍스트 요소 목록(JSON)을 받는다. "
    "각 요소의 텍스트(content)는 절대 변경하지 말고, type(heading/paragraph/caption)과 "
    "level(1~4, 본문은 0)과 order만 교정하라. 새 요소나 새 텍스트를 만들지 마라. "
    "결과는 입력과 동일 길이의 JSON 배열로만 출력한다."
)


def _llm_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def refine(doc: Document, use_llm: bool = True, model: str = "claude-opus-4-8", client=None) -> Document:
    """맥락 교정. LLM 사용 불가/실패 시 입력을 그대로 반환(결정론적 폴백).

    client를 주입하면 env 키 게이트를 건너뛴다(운영 로직 테스트용)."""
    if not use_llm:
        return doc
    if client is None:
        if not _llm_available():
            return doc

    try:
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        payload = [
            {"order": e.order, "type": e.type, "level": e.level,
             "content": e.content if isinstance(e.content, str) else "[TABLE]"}
            for e in sorted(doc.elements, key=lambda x: x.order)
            if e.type in ("heading", "paragraph", "caption")
        ]
        msg = client.messages.create(
            model=model, max_tokens=4096, system=_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
        text = msg.content[0].text.strip()
        # 코드펜스 제거.
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        refined = {item["order"]: item for item in json.loads(text)}
    except Exception:
        # 어떤 실패든 결정론적 결과를 보존(개발계획서 §9 hallucination/오류 대응).
        return doc

    # grounded 검증: 텍스트가 바뀌지 않은 교정만 수용.
    for el in doc.elements:
        r = refined.get(el.order)
        if not r:
            continue
        if isinstance(el.content, str) and r.get("content") == el.content:
            if r.get("type") in ("heading", "paragraph", "caption"):
                el.type = r["type"]
                el.level = int(r.get("level", el.level))
    return doc
