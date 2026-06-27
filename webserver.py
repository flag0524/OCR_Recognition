# OCR 파이프라인 웹 서버: 정적 UI 서빙 + 업로드 문서를 변환하는 /api/convert
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# src 레이아웃 패키지 import 경로 보장.
sys.path.insert(0, str(Path(__file__).parent / "src"))
from ocr_docintel.pipeline import process
from ocr_docintel.identify import UnsupportedFormatError
from ocr_docintel.ocr_scan import TesseractUnavailableError

WEBUI_DIR = Path(__file__).parent / "webui"

app = FastAPI(title="RUDA DocIntel — OCR Pipeline")


@app.post("/api/convert")
async def convert(file: UploadFile = File(...), use_llm: str = Form("false")):
    """업로드 문서를 구조 보존 추출해 Markdown/JSON으로 반환."""
    data = await file.read()
    # 원본 파일명을 보존해 문서 제목이 임시파일명으로 나오지 않도록 임시 디렉터리에 그대로 저장.
    safe_name = Path(file.filename or "upload").name
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / safe_name
        tmp_path.write_bytes(data)
        try:
            res = process(str(tmp_path), use_llm=(use_llm.lower() == "true"))
        except (UnsupportedFormatError, TesseractUnavailableError) as e:
            raise HTTPException(status_code=415, detail=str(e))
        except Exception as e:  # 손상 파일 등
            raise HTTPException(status_code=422, detail=f"변환 실패: {e}")

    return JSONResponse({
        "filename": file.filename,
        "source_format": res.document.source_format,
        "elements": len(res.document.elements),
        "markdown": res.markdown,
        "json": res.json,
    })


# 정적 UI (마지막에 마운트해 /api 라우트를 가리지 않도록).
app.mount("/", StaticFiles(directory=str(WEBUI_DIR), html=True), name="webui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
