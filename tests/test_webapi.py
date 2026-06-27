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


def test_unsupported_format_returns_415(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"not a document")
    with open(p, "rb") as f:
        r = client.post("/api/convert", files={"file": ("x.txt", f, "text/plain")},
                        data={"use_llm": "false"})
    assert r.status_code == 415
