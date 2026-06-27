# 스캔 OCR 테스트: 그룹화 로직은 합성 데이터로, 실제 OCR은 Tesseract 있을 때만
import pytest
from ocr_docintel.ocr_scan import _words_to_paragraphs, tesseract_available, extract_image
from ocr_docintel.identify import identify


def test_words_to_paragraphs_grouping():
    # (block,par) 단위로 단락이 묶이고 bbox가 합쳐진다.
    data = {
        "text": ["문장", "하나", "다른", ""],
        "block_num": [1, 1, 2, 2],
        "par_num": [1, 1, 1, 1],
        "line_num": [1, 1, 1, 1],
        "left": [10, 60, 10, 0], "top": [20, 20, 80, 0],
        "width": [40, 40, 50, 0], "height": [15, 15, 15, 0],
    }
    els = _words_to_paragraphs(data, page_no=3, start_order=0)
    assert len(els) == 2
    assert els[0].content == "문장 하나"
    assert els[0].source.page == 3
    assert els[0].source.bbox == [10.0, 20.0, 100.0, 35.0]  # 두 단어 합친 영역
    assert els[1].content == "다른"


def test_image_signature_identified(tmp_path):
    from PIL import Image
    p = tmp_path / "scan.png"
    Image.new("RGB", (40, 40), "white").save(p)
    assert identify(p) == "image"


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract 바이너리 없음 — 실 OCR 생략")
def test_real_ocr_smoke(tmp_path):
    from PIL import Image, ImageDraw
    p = tmp_path / "hello.png"
    img = Image.new("RGB", (300, 80), "white")
    ImageDraw.Draw(img).text((10, 30), "HELLO", fill="black")
    img.save(p)
    doc = extract_image(p)
    assert any("HELLO" in str(e.content).upper() for e in doc.elements)
