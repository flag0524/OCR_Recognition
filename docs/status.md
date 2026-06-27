<!-- 현재 진행 상태와 다음 작업을 추적하는 문서 -->
# status.md — 진행 상태

| 항목 | 내용 |
| :--- | :--- |
| 최종 갱신 | 2026-06-26 |
| 현재 단계 | 다중 포맷 + 스캔 OCR + HWP 표 + 웹 UI 연동 완료 |
| 릴리스 가능 여부 | ✅ (pytest 52 passed, 1 skipped=실LLM API, KPI 합격선 충족) |

## 1. 진행 현황

| # | 작업 | 상태 |
| :--- | :--- | :--- |
| 1 | 문서체계 4종(goal/plan/status/tests) | ✅ 완료 |
| 2 | checklist.md / context-notes.md | ✅ 완료 |
| 3 | IR 모델 + 포맷 식별 | ✅ 완료 |
| 4 | 텍스트 PDF 추출기 | ✅ 완료 |
| 5 | 직렬화(MD/JSON) + 검증 | ✅ 완료 |
| 6 | 맥락 LLM + 폴백 | ✅ 완료 |
| 7 | E2E 골든셋 회귀 + KPI | ✅ 완료 |
| 8 | CLI | ✅ 완료 |

## 2. KPI 현황 (tests.md 기준, test_pipeline.py 측정)

| KPI | 합격선 | 현재 |
| :--- | :--- | :--- |
| CER | ≤ 1% | ✅ 충족 (단단 본문) |
| 표 셀 일치율 | ≥ 95% | ✅ 충족 (단순표 100%) |
| 읽기순서 | ≥ 90% | ✅ 충족 (제목→본문 순서) |
| 요소 누락 | 0 | ✅ 충족 |
| 스키마 준수 | 100% | ✅ 충족 |

## 3. 완료된 고급 구조 (2026-06-26 2차)

- ✅ 다단 정밀화: `layout.py` gap 기반 컬럼 경계 검출 → 좌단 전체→우단 전체 읽기순서.
- ✅ 표 병합셀 정규화: `tables.normalize_table` (None→빈칸, 직사각형 패딩).
- ✅ 페이지 횡단 표 병합: `tables.merge_cross_page` (연속 페이지·동일 열수, `spans_pages`).
- ✅ Claude API 맥락 단계 운영 검증: 가짜 클라이언트로 grounded 수용/거부·폴백·코드펜스 파싱 검증, 실호출은 키 보유 시만 스모크.

## 5. 완료된 다중 포맷 + over-merge 정밀화 (2026-06-26 3차)

- ✅ 스캔 OCR: `ocr_scan.py` (pytesseract). 텍스트 없는 PDF 페이지 자동 OCR 폴백 + 이미지 파일(PNG/JPG) 경로. 실호출은 Tesseract 바이너리 있을 때만(현재 미설치 → skip).
- ✅ DOCX 파서: `extract_docx.py` (제목 레벨/목록 들여쓰기/bold·italic·underline/표, 문서 순서 보존).
- ✅ XLSX 파서: `extract_xlsx.py` (다중시트 `## Sheet:`, 병합셀 대표값+빈칸).
- ✅ HWP 파서: `extract_hwp.py` (pyhwp 텍스트 단락 best-effort, 표/스타일은 후속).
- ✅ over-merge 정밀화: `tables.merge_cross_page`에 헤더 반복 제거 + 페이지 가장자리 근접성 가드.
- ✅ `identify.py` 이미지 시그니처(PNG/JPG) 추가, `pipeline` 포맷 분기.

## 6. 스캔 OCR 실측 + HWP 표 복원 (2026-06-26 4차)

- ✅ 스캔 OCR 실측: Tesseract 5.4.0(kor+eng) 자동 경로 인식(`_resolve_tesseract_cmd`, PATH 밖 설치 경로 탐색). psm 4 + gap 기반 한국어 글자 결합으로 공백 정규화 CER ≈ 3~10%(합성 프록시). `test_scan_kpi.py`가 실측 게이트(≤12%, 영문 ≤5%).
- ✅ HWP 표 복원: pyhwp XHTML 변환(`HTMLTransform`)→`_parse_xhtml`로 표(`<table>`)·단락 순서 보존 추출, 실패 시 평문 폴백. 순수 파서는 합성 XHTML로 검증.
- ✅ 이미지 입력 E2E: PNG→OCR→MD/JSON 한국어 정상.

## 7. 웹 UI 연동 (2026-06-26 5차)

- ✅ claude.ai/design "화면 디자인 요청"(Airbnb 재해석) 디자인을 실제 연동 웹앱으로 구현.
- `webui/`: index.html(상단바·업로드·Configuration·Results) + ocr-screen.css(디자인 토큰 원본) + app.js(업로드/드래그/Run/마크다운 렌더/다크모드).
- `webserver.py`: FastAPI. `POST /api/convert`가 업로드 문서를 `pipeline.process`로 변환해 MD/JSON 반환, 정적 UI 서빙. 모델 Fast/Balanced=결정론, Accurate=LLM 맥락.
- 실행: `python webserver.py` → http://127.0.0.1:8000. 테스트 `test_webapi.py`(4건) TestClient로 검증.

## 8. 다음 작업 (여전히 범위 밖)

- 실제 스캔 문서 골든셋(원본+그라운드트루스) 확보 후 CER ≤ 3% 정식 측정(현재는 합성 렌더 프록시).
- 실 .hwp 샘플로 표 복원 E2E 회귀(현재 순수 파서만 검증).
- 전폭 표가 단 사이에 끼는 페이지의 컬럼 검출 정밀도.
- 알려진 소소한 중복: 1레벨 제목이 문서 제목과 본문에 동시 노출(개선 여지).

## 4. 의사결정 로그

- 2026-06-26: 실행범위=문서체계+MVP, 기술노선=LLM API 하이브리드, 우선포맷=텍스트 PDF (사용자 확정).
