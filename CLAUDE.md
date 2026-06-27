# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 상위 폴더(`../CLAUDE.md`)의 행동 지침(한국어 출력·문장 종결, 파일 헤더 주석, 문서체계 등)도 함께 적용된다.

## 프로젝트 개요

다중 포맷 문서를 입력받아 **레이아웃·텍스트·표·이미지 구조를 보존한 Markdown + JSON**으로 변환하는 구조 보존 OCR 시스템. 현재 지원 포맷: **텍스트 PDF, 스캔 PDF/이미지(OCR), DOCX, XLSX, HWP(텍스트)**. 고급 구조(다단 읽기순서·병합셀·페이지 횡단 표 병합·LLM 맥락 교정) 구현 완료.

요구사항·설계·검증 기준은 `docs/`에 문서화되어 있고 코드보다 먼저 읽어야 한다.
- `docs/goal.md` — 3대 원칙(정확성/레이아웃 보존/무손실)과 KPI 합격선
- `docs/plan.md` — 아키텍처·모듈 구조·출력 규격 계약
- `docs/tests.md` — 검증 계층·골든셋·KPI 측정 방법
- `docs/status.md` — 현재 진행 상태(가장 먼저 확인)
- 원본 요구문서: `docs/PRD_*.md`, `docs/TRD_*.md`, `docs/문서지능-OCR-개발계획서.md`, `docs/gemini-code-*.md`(출력 규격 System Prompt)

## 명령어

```bash
pip install -e ".[dev]"          # 개발 의존성(pytest, reportlab) 포함 설치
pip install -e ".[dev,llm]"      # + anthropic SDK(맥락 단계 실호출용)

pytest -q                        # 전체 테스트
pytest tests/test_pipeline.py -q # E2E + KPI 게이트만
pytest tests/test_layout.py::test_two_columns -q   # 단일 테스트

python -m ocr_docintel <pdf> -o <out_dir>          # 변환 실행(LLM 맥락 단계 포함)
python -m ocr_docintel <pdf> -o <out_dir> --no-llm # 결정론적 폴백만

pip install -e ".[dev,web]"   # 웹 UI 의존성(fastapi, uvicorn, python-multipart)
python webserver.py           # 웹 UI + API → http://127.0.0.1:8000
```

테스트용 샘플 PDF는 `tests/conftest.py`가 reportlab으로 즉석 생성하므로 별도 픽스처 파일이 없다. 골든셋을 추가할 때도 이 패턴을 따른다.

## 아키텍처 (핵심 설계 결정)

`src/ocr_docintel/pipeline.py`의 `process()`가 5단계 단방향 파이프라인을 오케스트레이션한다.

```
identify → extract_pdf → context_llm(refine) → serialize → validate
 (포맷식별)  (결정론적 추출)   (LLM 맥락 교정)      (MD/JSON)   (규격 검증)
```

설계를 이해하려면 다음 두 가지 불변 원칙이 핵심이다.

1. **하이브리드 = 결정론 + LLM, 단 LLM은 선택적.** 라이브러리(PyMuPDF/pdfplumber)로 좌표·구조를 결정론적으로 확보하고, Claude API는 읽기순서·제목레벨·캡션 같은 맥락만 교정한다. **`context_llm.refine()`은 API 키가 없거나 호출이 실패하면 입력 IR을 그대로 반환**한다. 따라서 전 파이프라인이 키 없이 끝까지 동작하고 테스트가 오프라인에서 재현된다(`--no-llm` 또는 키 부재 시 자동 폴백).

2. **Grounded extraction (hallucination 차단).** LLM에는 IR의 좌표 블록 텍스트만 전달하고 "텍스트 변경 금지, 재분류·재배열만" 지시한다. `refine()`은 응답이 원본 `content`를 바꾸지 않은 교정만 수용하고, 텍스트가 바뀐 응답은 거부한다. 이 계약을 깨는 변경은 금지.

### IR(중간표현)이 단일 계약

`ir.py`의 `Document`/`Element`/`Source`가 추출·LLM·직렬화·검증 모든 단계가 주고받는 유일한 자료구조다. 새 요소 타입이나 필드를 추가하려면 **세 곳을 함께 고쳐야 한다**: `ir.py`(데이터모델) → `schema.py`(JSON 스키마) → `serialize.py`(MD 렌더링). 한 곳만 바꾸면 `validate.py`가 차단한다.

- `Element.type`은 `ir.ELEMENT_TYPES`와 `schema.py`의 enum이 일치해야 한다.
- 페이지 횡단 병합 표는 `Source.page`가 리스트(`[1,2]`)이고 `spans_pages=True`다 — `page`는 int·array·null 모두 허용.

### 출력 규격은 협상 불가

`docs/gemini-code-*.md`(System Prompt §5)와 `TRD §4.4`가 정의한 Markdown 구조와 JSON 스키마는 고정 계약이다. `validate.py`가 릴리스 게이트로 비규격 출력을 차단하므로, 출력 형태를 바꾸려면 먼저 스키마/검증을 갱신해야 한다.

### 모듈 책임 분리

- `layout.py` — 다단 컬럼 경계를 gap으로 검출(전폭 블록 제외), 읽기순서 키 생성.
- `tables.py` — 병합셀 정규화(None→빈칸, 직사각형 패딩)와 연속 페이지 표 병합. 둘 다 IR 비의존 순수 함수라 단위 테스트가 쉽다.
- `extract_pdf.py` — 위 둘을 조합해 PDF→IR. 표 영역과 겹치는 텍스트 블록은 제외하고, 폰트 크기 최빈값을 본문 기준으로 제목 레벨을 추정한다.

## KPI 게이트

`tests/test_pipeline.py`가 골든셋에 대해 CER ≤ 1%, 표 셀 일치율 ≥ 95%, 읽기순서 ≥ 90%, 요소 누락 0, 스키마 100%를 측정한다. 합격선 미달 시 테스트 실패 = 릴리스 불가(`docs/tests.md` §6). 추출 로직을 바꾸면 이 게이트로 회귀를 확인한다.

## 웹 UI (`webui/` + `webserver.py`)

claude.ai/design에서 받은 Airbnb 재해석 디자인을 실제 파이프라인에 연동한 단일 화면 앱이다. `webserver.py`(FastAPI)가 `webui/`를 정적 서빙하고 `POST /api/convert`(multipart: `file`, `use_llm`)가 업로드를 임시 디렉터리에 원본 파일명으로 저장한 뒤 `pipeline.process`로 변환해 `{markdown, json, elements, source_format}`을 반환한다. UI의 모델 선택은 Fast/Balanced=`use_llm=false`, Accurate=`use_llm=true`로 매핑된다. `webui/ocr-screen.css`는 **디자인 원본 토큰**이므로 색·간격·라운드 값을 임의로 바꾸지 말 것(디자인 계약). 라우트 순서 주의: `/api/*` 라우트를 먼저 등록하고 `StaticFiles` 마운트(`/`)는 마지막에 둬야 API가 가려지지 않는다.

## 포맷 추가 방법

`pipeline.process()`는 `identify.identify()` 결과로 `extractors` 딕셔너리에서 포맷별 `extract()`를 고른다. 새 포맷은 (1) `identify.py`에 시그니처/확장자, (2) `extract_<fmt>.py`에 `extract(path) -> Document`, (3) `pipeline.extractors`에 등록, (4) 필요 시 `schema.py`의 `source_format` enum 확장으로 추가한다.

## 환경 의존 / 미설치 시 동작

두 경로는 외부 바이너리/키가 없으면 **graceful하게 폴백하거나 테스트를 skip**한다 — 둘 다 자동 감지한다.
- **스캔 OCR**: `ocr_scan._resolve_tesseract_cmd()`가 `TESSERACT_CMD`→PATH→Windows 기본 설치 경로(`C:\Program Files\Tesseract-OCR`) 순으로 바이너리를 찾는다(PATH에 없어도 자동 인식). 한국어는 psm 4 + `_join_line`의 gap 기반 글자 결합으로 복원(기본 psm 3는 한국어 줄을 누락하므로 바꾸지 말 것). 미설치 시 PDF 스캔 페이지 OCR은 건너뛰고 이미지 입력은 `TesseractUnavailableError`.
- **HWP**: `extract_hwp.py`는 pyhwp XHTML 변환→`_parse_xhtml`로 표·단락을 복원하고, 변환 실패 시 평문 텍스트로 폴백. 손상 파일은 `HwpExtractError`. 실 .hwp 생성기가 없어 순수 파서만 회귀 테스트한다.

OCR/HWP 테스트는 바이너리·키·폰트·샘플이 없으면 `skipif`로 자동 제외된다(`tests/test_scan_kpi.py`, `test_context_llm.py::test_real_api_smoke`). 남은 범위 밖: 실 스캔 골든셋 기반 CER ≤ 3% 정식 측정, 실 .hwp 표 복원 E2E.
