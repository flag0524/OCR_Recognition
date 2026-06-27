# 스캔 OCR 실측 KPI 테스트 (Tesseract 설치 시). 합성 렌더 프록시 — 실 스캔 골든셋은 후속.
import os
import pytest

from ocr_docintel.ocr_scan import tesseract_available, ocr_image_elements

_FONT = "C:/Windows/Fonts/malgun.ttf"
pytestmark = [
    pytest.mark.skipif(not tesseract_available(), reason="Tesseract 미설치"),
    pytest.mark.skipif(not os.path.exists(_FONT), reason="한국어 폰트(malgun) 없음"),
]


def _lev(a, b):
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[n]


def _norm(s):
    return "".join(s.split())  # 공백 정규화: 한국어 단어 분절 영향 제거


def cer(gt, out, normalize=True):
    g, o = (_norm(gt), _norm(out)) if normalize else (gt, out)
    return _lev(g, o) / len(g) if g else 0.0


def _render(lines, size=56):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(_FONT, size)
    img = Image.new("RGB", (2000, 160 + len(lines) * (size + 90)), "white")
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        d.text((40, 40 + i * (size + 90)), ln, fill="black", font=f)
    return img


# 골든 스캔셋(합성): 한국어 문장 + 영문 1줄. 기대 텍스트를 그라운드 트루스로 고정.
GOLDEN = [
    "본 계약의 기간은 체결일로부터 일 년으로 한다.",
    "데이터 추출 결과 금액 합계가 일치한다.",
    "The OCR system extracts structured data accurately.",
]


def test_scan_character_accuracy():
    img = _render(GOLDEN)
    els = ocr_image_elements(img)
    out = "\n".join(str(e.content) for e in els)
    gt = "\n".join(GOLDEN)

    overall = cer(gt, out, normalize=True)
    # 정확성 원칙(문자 인식): 공백 정규화 CER ≤ 12% (합성 렌더 프록시 허용치).
    assert overall <= 0.12, f"normalized CER={overall:.4f} 출력={out!r}"

    # 영문 라인은 매우 안정적 → 별도로 엄격 검증(파이프라인 정상 동작 확인).
    eng_out = next((str(e.content) for e in els if "OCR" in str(e.content)), "")
    assert cer(GOLDEN[2], eng_out, normalize=True) <= 0.05


def test_scan_produces_grounded_bboxes():
    els = ocr_image_elements(_render(GOLDEN))
    assert els and all(e.source.bbox is not None and e.source.page == 1 for e in els)
