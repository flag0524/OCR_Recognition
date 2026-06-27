<!-- 프로젝트 소개·설치·사용법을 안내하는 README -->
# OCR 인식 시스템 (ocr-docintel)

다중 포맷 문서를 입력받아 **레이아웃·텍스트·표·이미지 구조를 보존한 Markdown + JSON**으로 변환하는 구조 보존 OCR 시스템.

라이브러리(PyMuPDF/pdfplumber 등)로 좌표·구조를 **결정론적으로** 추출하고, Claude API는 읽기순서·제목레벨·캡션 같은 **맥락만 교정**하는 하이브리드 구조다. LLM 단계는 선택적이며, API 키가 없으면 결정론적 결과를 그대로 반환하므로 키 없이도 전 과정이 동작한다.

## 지원 포맷

| 포맷 | 추출 방식 |
| :--- | :--- |
| 텍스트 PDF | 좌표 기반 텍스트·표 추출, 다단 읽기순서 복원 |
| 스캔 PDF / 이미지(PNG·JPG) | Tesseract OCR(kor+eng) 폴백 |
| DOCX | 제목 레벨·목록·서식·표, 문서 순서 보존 |
| XLSX | 다중 시트, 병합셀 정규화 |
| HWP | pyhwp XHTML 변환 → 표·단락 복원(실패 시 평문 폴백) |

## 핵심 기능

- 다단(컬럼) 읽기순서 복원 — gap 기반 컬럼 경계 검출
- 표 병합셀 정규화 및 페이지 횡단 표 병합
- LLM 맥락 교정(grounded extraction, 원문 텍스트 변경 금지)
- 출력 규격 검증(`validate.py`)을 릴리스 게이트로 적용

## 설치

```bash
pip install -e ".[dev]"            # 개발 의존성(pytest, reportlab 등) 포함
pip install -e ".[dev,llm]"       # + anthropic SDK(LLM 맥락 단계 실호출용)
pip install -e ".[dev,web]"       # + 웹 UI 의존성(fastapi, uvicorn 등)
```

선택적 의존성: `llm`, `docx`, `xlsx`, `ocr`, `hwp`, `web`.

> 스캔 OCR을 쓰려면 시스템에 **Tesseract 바이너리**가 필요하다. `TESSERACT_CMD` 환경변수 → PATH → Windows 기본 설치 경로(`C:\Program Files\Tesseract-OCR`) 순으로 자동 탐색한다. 미설치 시 스캔 페이지는 건너뛴다.

## 사용법

### CLI

```bash
python -m ocr_docintel <문서> -o <출력_디렉터리>            # LLM 맥락 단계 포함
python -m ocr_docintel <문서> -o <출력_디렉터리> --no-llm   # 결정론적 폴백만
```

출력은 변환된 `*.md`와 `*.json`이다.

### 웹 UI

```bash
pip install -e ".[dev,web]"
python webserver.py        # → http://127.0.0.1:8000
```

업로드 → 모델 선택(Fast/Balanced=결정론, Accurate=LLM 맥락) → 변환 결과(Markdown·JSON) 확인. API는 `POST /api/convert`(multipart: `file`, `use_llm`).

## 파이프라인

`src/ocr_docintel/pipeline.py`의 `process()`가 5단계 단방향 파이프라인을 오케스트레이션한다.

```
identify → extract_<fmt> → context_llm(refine) → serialize → validate
 (포맷식별)   (결정론적 추출)    (LLM 맥락 교정)       (MD/JSON)   (규격 검증)
```

`ir.py`의 `Document`/`Element`/`Source`가 모든 단계가 주고받는 단일 중간표현(IR) 계약이다. 새 요소 타입·필드를 추가하려면 `ir.py`(데이터모델) → `schema.py`(JSON 스키마) → `serialize.py`(MD 렌더링) 세 곳을 함께 고쳐야 한다.

## 테스트 / KPI

```bash
pytest -q                          # 전체 테스트
pytest tests/test_pipeline.py -q   # E2E + KPI 게이트만
```

테스트용 샘플 PDF는 `tests/conftest.py`가 reportlab으로 즉석 생성한다. KPI 게이트(골든셋 기준): CER ≤ 1%, 표 셀 일치율 ≥ 95%, 읽기순서 ≥ 90%, 요소 누락 0, 스키마 준수 100%. 합격선 미달 시 테스트 실패 = 릴리스 불가.

OCR·HWP·실 LLM 호출 테스트는 바이너리·키·샘플이 없으면 자동으로 skip된다.

## 프로젝트 구조

```
src/ocr_docintel/
  pipeline.py        # 5단계 파이프라인 오케스트레이션
  ir.py              # 중간표현(IR) 단일 계약
  identify.py        # 포맷 식별
  extract_pdf.py     # 텍스트 PDF 추출
  extract_docx.py    # DOCX 추출
  extract_xlsx.py    # XLSX 추출
  extract_hwp.py     # HWP 추출
  ocr_scan.py        # 스캔 PDF/이미지 OCR
  layout.py          # 다단 컬럼·읽기순서
  tables.py          # 병합셀 정규화·페이지 횡단 표 병합
  context_llm.py     # LLM 맥락 교정(grounded)
  serialize.py       # MD/JSON 직렬화
  schema.py          # JSON 스키마
  validate.py        # 출력 규격 검증(릴리스 게이트)
  cli.py             # CLI 진입점
webui/               # 웹 UI(index.html, ocr-screen.css, app.js)
webserver.py         # FastAPI 서버
docs/                # 요구사항·설계·검증·진행 상태 문서
```

## 문서

설계·검증 기준은 `docs/`에 있으며 코드보다 먼저 읽는 것을 권장한다.

- `docs/goal.md` — 3대 원칙(정확성/레이아웃 보존/무손실)과 KPI 합격선
- `docs/plan.md` — 아키텍처·모듈 구조·출력 규격 계약
- `docs/tests.md` — 검증 계층·골든셋·KPI 측정 방법
- `docs/status.md` — 현재 진행 상태(가장 먼저 확인)
