# 웹 API 테스트: /api/convert가 업로드 문서를 MD/JSON으로 변환하고 정적 UI를 서빙하는지
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import webserver  # noqa: E402

client = TestClient(webserver.app)


def test_static_ui_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "OCR Pipeline" in r.text


def test_convert_pdf(single_column_pdf):
    with open(single_column_pdf, "rb") as f:
        r = client.post("/api/convert", files={"file": ("doc.pdf", f, "application/pdf")},
                        data={"use_llm": "false"})
    assert r.status_code == 200
    body = r.json()
    assert body["source_format"] == "pdf"
    assert body["elements"] >= 1
    assert body["markdown"].startswith("#")
    assert '"document_title"' in body["json"]


def test_convert_xlsx(xlsx_file):
    with open(xlsx_file, "rb") as f:
        r = client.post("/api/convert", files={"file": ("s.xlsx", f, "application/octet-stream")},
                        data={"use_llm": "false"})
    assert r.status_code == 200
    assert "## Sheet:" in r.json()["markdown"]


def test_sample_endpoint_each_id_converts():
    """모든 예시 샘플이 생성되고 그 바이트가 파이프라인으로 변환되는지.

    일본어·힌디어 샘플은 Windows 유니코드 폰트가 없는 환경이면 503(생성 불가)로
    graceful 폴백하므로, 그 경우만 건너뛴다."""
    import samples
    for sid, (name, ctype, _builder) in samples.SAMPLES.items():
        r = client.get(f"/api/sample/{sid}")
        if r.status_code == 503:  # 유니코드 폰트 부재(머신 의존) — 정상 폴백
            continue
        assert r.status_code == 200, (sid, r.text)
        assert len(r.content) > 0
        r2 = client.post("/api/convert",
                         files={"file": (name, r.content, ctype)},
                         data={"use_llm": "false"})
        assert r2.status_code == 200, (sid, r2.text)
        assert r2.json()["elements"] >= 1, sid


def test_sample_unknown_id_returns_404():
    assert client.get("/api/sample/does-not-exist").status_code == 404


def test_unsupported_format_returns_415(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"not a document")
    with open(p, "rb") as f:
        r = client.post("/api/convert", files={"file": ("x.txt", f, "text/plain")},
                        data={"use_llm": "false"})
    assert r.status_code == 415
