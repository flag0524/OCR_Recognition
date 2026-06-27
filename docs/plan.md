<!-- 목표 달성을 위한 단계별 실행 계획과 아키텍처를 정의하는 문서 -->
# plan.md — 실행 계획 및 아키텍처

| 항목 | 내용 |
| :--- | :--- |
| 최종 갱신 | 2026-06-26 |
| 연관 | goal.md, status.md, tests.md |

## 1. MVP 아키텍처 (하이브리드 단방향 파이프라인)

개발계획서 §4 / TRD §2 의 6단계를 MVP로 축약했다.

```
[텍스트 PDF]
   │
   ▼
1. 포맷 식별        ── 시그니처(%PDF) + 확장자 검사
   │
   ▼
2. 결정론적 추출     ── PyMuPDF/pdfplumber: 텍스트 블록(좌표 bbox), 표 그리드, 이미지 위치
   │   (라이브러리)        → 중간표현 IR(Intermediate Representation) 생성
   ▼
3. 맥락 해석        ── Claude API: 읽기순서 교정, 제목 레벨 추론, 표 헤더 정규화, 캡션 분리
   │   (LLM, 폴백 有)     → grounded: IR 좌표 블록만 입력, 새 텍스트 생성 금지
   ▼
4. 정형 변환        ── IR → Markdown(System Prompt §5 구조) + JSON(TRD §4.4 스키마)
   │
   ▼
5. 출력 검증        ── JSON 스키마 + MD 구조 규격 검사, 비규격 차단
```

**핵심 결정**: LLM 단계는 선택적이다. API 키가 없거나 호출 실패 시 **결정론적 폴백**(좌표 기반 읽기순서 + 폰트 크기 기반 제목 레벨)으로 동작한다. 이로써 테스트는 오프라인에서 재현 가능하다(goal §5-4).

## 2. 모듈 구조

```
src/ocr_docintel/
  __init__.py
  pipeline.py        # 5단계 오케스트레이션
  identify.py        # 1. 포맷 식별 (시그니처/확장자)
  extract_pdf.py     # 2. 텍스트 PDF 결정론적 추출 → IR
  ir.py              # 중간표현(IR) 데이터클래스 (Element, Block, Table ...)
  context_llm.py     # 3. Claude API 맥락 해석 + 결정론적 폴백
  serialize.py       # 4. IR → Markdown / JSON
  validate.py        # 5. JSON 스키마 + MD 구조 검증
  schema.py          # TRD §4.4 JSON 스키마 정의
  cli.py             # CLI 진입점 (python -m ocr_docintel <file>)
tests/
  test_identify.py
  test_extract_pdf.py
  test_serialize.py
  test_validate.py
  test_pipeline.py   # 골든셋 회귀(E2E)
  conftest.py        # 샘플 PDF 생성 픽스처
  golden/            # 골든셋 입력 + 기대 출력
```

## 3. 단계별 실행 (verify 포함)

1. 문서체계 4종 작성 → verify: 파일 존재 + 내용 검토
2. IR 데이터모델 + 포맷식별 → verify: `test_identify` 통과
3. 텍스트 PDF 추출기 → verify: 샘플 PDF에서 블록/표 추출, `test_extract_pdf` 통과
4. 직렬화(MD/JSON) + 스키마 검증 → verify: `test_serialize`, `test_validate` 통과
5. 맥락 LLM + 폴백 → verify: 폴백 경로로 E2E 통과
6. E2E 골든셋 회귀 → verify: `test_pipeline` 통과, KPI 합격선 충족
7. CLI → verify: 실제 샘플 PDF 변환 수동 확인

## 4. 출력 규격 (불변 계약)

### 4.1 Markdown (System Prompt §5)
```markdown
# [문서 제목]
*본 문서 분석 결과는 원본의 레이아웃을 기반으로 작성되었습니다.*

---

## [세션/페이지/시트 제목]
[본문/표/이미지]
```
- 표: GFM 표, 셀 내 줄바꿈 `<br>`.
- 캡션: `> [그림 N] 설명`.
- 시각요소: `![[Image/Chart]: 요약]`.
- 개요/글머리: `-`, 들여쓰기 `    -`.

### 4.2 JSON (TRD §4.4)
`document_title`, `source_format`, `elements[]` (type/level/order/source{page,sheet,bbox}/content).

## 5. 의존성

- `pymupdf` (fitz): 텍스트 블록 + 좌표 + 이미지 위치.
- `pdfplumber`: 표 검출.
- `jsonschema`: 출력 검증.
- `anthropic`: LLM 맥락 단계(선택, 키 없으면 폴백).
- `pytest`, `reportlab`(테스트용 샘플 PDF 생성).

## 6. 리스크 / 대응 (개발계획서 §9 발췌)

| 리스크 | 대응 |
| :--- | :--- |
| LLM hallucination | grounded 추출(IR 좌표 블록만 입력), 폴백 결정론적 |
| API 키 부재로 테스트 불가 | 폴백 경로로 오프라인 테스트 보장 |
| 표 병합셀/다중헤더 | MVP는 단순표 우선, 복합표는 후속 |
| Windows 라이브러리 설치 | 순수 Python 휠 패키지만 사용(GPU 불요) |
