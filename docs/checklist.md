<!-- 구체적 작업 항목을 체크박스로 추적하는 문서 -->
# checklist.md

## 문서체계
- [x] goal.md
- [x] plan.md
- [x] tests.md
- [x] status.md
- [x] checklist.md
- [x] context-notes.md

## 구현
- [x] 프로젝트 스캐폴딩(pyproject, 패키지 디렉터리)
- [x] ir.py — IR 데이터모델
- [x] identify.py — 포맷 식별 + test_identify
- [x] extract_pdf.py — 텍스트 PDF 추출 + test_extract_pdf
- [x] schema.py — JSON 스키마
- [x] serialize.py — MD/JSON 직렬화 + test_serialize
- [x] validate.py — 출력 검증 + test_validate
- [x] context_llm.py — Claude API 맥락 + 결정론적 폴백
- [x] pipeline.py — 5단계 오케스트레이션
- [x] cli.py — CLI 진입점
- [x] 골든셋 — conftest.py 픽스처(reportlab 생성)
- [x] test_pipeline.py — E2E + KPI 측정

## 다중 포맷 + over-merge 정밀화 (3차)
- [x] over-merge 정밀화 (헤더 반복 제거 + 페이지 가장자리 가드)
- [x] extract_xlsx.py — 다중시트/병합셀 + test_extract_xlsx
- [x] extract_docx.py — 제목/목록/강조/표 + test_extract_docx
- [x] ocr_scan.py — 스캔 OCR(이미지/텍스트없는 PDF) + test_ocr_scan
- [x] extract_hwp.py — pyhwp 텍스트 추출 + test_extract_hwp
- [x] identify.py 이미지 시그니처 + pipeline 포맷 분기

## 스캔 OCR 실측 + HWP 표 (4차)
- [x] Tesseract 경로 자동 인식(_resolve_tesseract_cmd)
- [x] 한국어 안정화: psm 4 + gap 기반 글자 결합
- [x] 스캔 OCR 실측 KPI(test_scan_kpi) — 공백정규화 CER 게이트
- [x] HWP XHTML 표 복원(_parse_xhtml) + 순수 파서 테스트
- [x] 이미지/스캔 E2E(PNG→MD/JSON) 한국어 확인

## 웹 UI 연동 (5차)
- [x] claude.ai/design 디자인 확보(DesignSync get_file)
- [x] webui/ocr-screen.css(디자인 토큰 원본) + index.html + app.js
- [x] webserver.py — FastAPI /api/convert + 정적 서빙
- [x] test_webapi.py(4건) + 라이브 서버 E2E(/, css, js, convert 200)

## 검증
- [x] pytest 전체 green (52 passed, 1 skipped=실LLM API)
- [x] KPI 합격선 충족(텍스트 PDF + 스캔 OCR)
- [x] CLI로 PDF·XLSX·이미지 변환 확인
- [x] status.md / context-notes.md / CLAUDE.md 최신화
