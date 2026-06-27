<!-- 검증 구조와 테스트 케이스, KPI 측정 방법을 정의하는 문서 -->
# tests.md — 검증 구조

| 항목 | 내용 |
| :--- | :--- |
| 최종 갱신 | 2026-06-26 |
| 연관 | goal.md(성공지표), plan.md |
| 실행 | `pytest` (프로젝트 루트) |

## 1. 검증 철학

TRD §7 에 따라 **포맷별 대표 샘플(골든셋)로 회귀 테스트**를 구성하고, 출력물은 **JSON/MD 스키마 유효성 검사를 통과해야 릴리스**한다. 모든 테스트는 LLM 폴백 경로로 **오프라인 재현 가능**해야 한다.

## 2. 테스트 계층

| 계층 | 파일 | 검증 대상 |
| :--- | :--- | :--- |
| 단위 | test_identify.py | 포맷 식별: %PDF 시그니처 인식, 미지원 포맷 오류 분기 |
| 단위 | test_extract_pdf.py | 텍스트 블록·좌표 추출, 표 그리드 복원, 읽기순서(좌상→우하) |
| 단위 | test_serialize.py | IR→MD 구조(System Prompt §5), IR→JSON 스키마 키 |
| 단위 | test_validate.py | 비규격 JSON/MD 차단, 규격 출력 통과 |
| 통합(E2E) | test_pipeline.py | 골든셋 PDF → MD+JSON, KPI 합격선 측정 |

## 3. 골든셋 (`tests/golden/`)

| ID | 입력 | 특성 | 기대 |
| :--- | :--- | :--- | :--- |
| G1 | single_column.pdf | 단단 본문 + 제목 2계층 | 제목 #/##, 단락 순서 |
| G2 | simple_table.pdf | 단순 표(헤더 1행) | GFM 표, 셀 일치 |
| G3 | caption_doc.pdf | 이미지 + 캡션 | `> [그림 N]` 분리, 이미지 태그 |

각 골든셋은 `<id>.pdf`(입력) + `<id>.expected.json`(기대 요소) 쌍으로 고정한다. 샘플 PDF는 `conftest.py`가 reportlab으로 생성하거나 사전 생성본을 커밋한다.

## 4. KPI 자동 측정 (test_pipeline.py)

| KPI | 측정 함수 | 합격선 |
| :--- | :--- | :--- |
| CER(문자오류율) | `cer(expected_text, actual_text)` | ≤ 1% |
| 표 셀 일치율 | `table_cell_match(exp, act)` | ≥ 95% |
| 읽기순서 일치율 | `order_match(exp_order, act_order)` | ≥ 90% |
| 요소 누락 건수 | `missing_elements(exp, act)` | 0 |
| 스키마 준수 | `validate_json/validate_md` | 100% 통과 |

CER = 레벤슈타인 거리 / 기대 문자 수. 합격선 미달 시 테스트 실패(빌드 게이트, 개발계획서 §8 자동 회귀).

## 5. 실행 절차

```bash
pip install -e ".[dev]"   # 또는 requirements 설치
pytest -q                 # 전체
pytest tests/test_pipeline.py -q   # E2E만
```

## 5.1 스캔 OCR 실측 KPI (test_scan_kpi.py)

Tesseract(kor+eng) 설치 시 동작. 한국어 단어 분절은 OCR 본질 한계라 **공백 정규화 CER**로 문자 인식 정확도를 측정한다. 현재 골든셋은 한국어 폰트(malgun) 합성 렌더 프록시이며, 실 스캔 문서 골든셋(CER ≤ 3% 목표)은 후속.

| 항목 | 합격선 |
| :--- | :--- |
| 공백 정규화 CER(전체) | ≤ 12% |
| 영문 라인 CER | ≤ 5% |
| 좌표(bbox)·페이지 보존 | 전 요소 |

미설치/폰트 부재 시 `skipif`로 자동 제외(빌드 비차단).

## 6. 합격 판정 (Gate)

- 단위/통합 전부 green.
- KPI 5개 모두 합격선 충족.
- 스키마 검증 100%.
- 위 3개 충족 시에만 `status.md`에 "릴리스 가능"으로 기록.
