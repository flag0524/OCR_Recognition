<!-- 작업 중 내린 결정과 그 근거를 누적 기록하는 문서 -->
# context-notes.md

## 2026-06-26

### 결정
- **실행 범위**: 문서체계 4종 + 실행가능 MVP (사용자 확정).
- **기술 노선**: LLM API 하이브리드. 라이브러리(PyMuPDF/pdfplumber)로 좌표·구조를 결정론적으로 확보하고, Claude API는 맥락(읽기순서/제목레벨/표헤더/캡션)만 담당. 개발계획서 §4.1 하이브리드 정신에 부합.
- **우선 포맷**: 텍스트 레이어 PDF (스캔 OCR/HWP/DOCX/XLSX는 인터페이스만 예약).

### 근거
- 환경이 Windows 단일 노드라 GPU 기반 PaddleOCR/로컬 VLM 스택은 설치·운용 비용이 큼 → 순수 Python 휠 + API 노선이 합리적.
- 테스트 재현성을 위해 **LLM 단계는 폴백 필수**. 키 없이도 결정론적 경로로 파이프라인이 끝까지 동작해야 CI 회귀가 성립(개발계획서 §8).

### grounded 추출 설계
- LLM에는 IR의 좌표 블록 텍스트만 전달하고, "새 텍스트 생성 금지, 재배열·분류만" 지시. hallucination 차단(개발계획서 §4.1, §9).

### 미해결/후속
- 표 병합셀·다중헤더, 페이지 횡단 병합은 MVP 제외.
- HWP는 한국어 전용 포맷이라 별도 파서(hwp5 등) 필요 — 후속.

## 2026-06-26 (2차 — 고급 구조)

### 다단 정밀화
- 기존 "페이지 중앙 고정 분할"을 gap 기반 컬럼 검출(`layout.detect_column_boundaries`)로 교체.
- 전폭(>60% page_width) 블록은 컬럼 추정에서 제외해 표·제목이 좌우단을 합쳐버리는 문제 방지.
- 한계: 전폭 표가 단 사이에 끼면 단 구분이 흐려질 수 있음(후속 정밀화 대상).

### 표 병합셀 / 페이지 횡단
- pdfplumber는 병합셀 확장부를 None으로 반환 → `normalize_table`이 빈칸으로 보존(System Prompt §3.3 규칙과 일치).
- `merge_cross_page`: 인접(사이 요소 없음)·연속 페이지·동일 열수인 표만 병합. IR `Source.page`를 list로, `spans_pages=True`로 확장. JSON 스키마도 page를 [int|array|null]로 확장.
- 휴리스틱이라 over-merge 가능 — 헤더 반복 감지는 후속.

### LLM 운영 검증
- 실 API 키가 환경에 없어서, `refine(client=...)`로 가짜 클라이언트를 주입해 운영 로직을 결정론적으로 검증.
- 검증 항목: grounded 재분류 수용 / 텍스트 조작 거부 / 깨진 응답 폴백 / 코드펜스 파싱. 실호출 스모크는 ANTHROPIC_API_KEY 있을 때만 skipif 해제.

## 2026-06-26 (3차 — 다중 포맷 + over-merge 정밀화)

### over-merge 정밀화
- `is_continuation`에 page_heights(페이지→높이)와 edge_ratio(기본 0.5) 가드 추가. prev는 페이지 하단부(y1 ≥ ratio*H), nxt는 상단부(y0 ≤ (1-ratio)*H)일 때만 위치상 연속 인정.
- 헤더 반복(nxt.content[0]==prev.content[0])은 강한 연속 신호 → 위치 가드 면제, 병합 시 반복 헤더 1회만 유지.
- page_heights 미제공 시(라이브러리 외 호출) 기존 동작(동일 열수 병합) 유지 — 하위호환.

### 다중 포맷 파서
- DOCX(python-docx): body.iterchildren로 단락/표 문서 순서 보존. Heading N→레벨, List 스타일→들여쓰기 `-`, run의 bold/italic/underline→마크다운.
- XLSX(openpyxl): 시트별 `## Sheet:` 제목 + 표. merged_cells.ranges로 대표셀 외 빈칸 처리(FR-3). source.sheet 채움.
- HWP(pyhwp): TextTransform로 평문 추출 후 줄 단위 단락. 표/스타일 복원은 pyhwp 한계로 후속. 손상 파일은 HwpExtractError.
- 스캔 OCR(pytesseract): image_to_data를 (block,par)로 묶어 단락+bbox. 텍스트 없는 PDF 페이지는 200dpi 래스터화 후 OCR. Tesseract 바이너리/언어팩 부재 시 폴백·skip. source_format에 "image" 추가(스키마 enum 확장).

### 테스트 픽스처 전략
- DOCX/XLSX는 라이브러리로 즉석 생성 가능 → conftest 픽스처.
- HWP는 생성기가 없어 식별+손상파일 오류 경로만 검증. 스캔 OCR은 그룹화 로직을 합성 dict로 검증, 실 OCR은 skipif.

## 2026-06-26 (4차 — 스캔 OCR 실측 + HWP 표 복원)

### 스캔 OCR 실측
- Tesseract 5.4.0이 PATH엔 없지만 C:\Program Files\Tesseract-OCR에 설치+kor/eng 언어팩 보유. `_resolve_tesseract_cmd`로 TESSERACT_CMD→PATH→기본 경로 순 탐색해 pytesseract.tesseract_cmd 설정.
- 발견 1: image_to_data 기본 psm 3(자동 분할)은 합성/저해상도에서 한국어 줄을 통째로 누락. psm 4(가변 단일 컬럼)가 안정적 → `_DEFAULT_CONFIG="--psm 4"`.
- 발견 2: tesseract가 한국어를 글자 단위 '단어'로 쪼개 공백이 끼어듦. `_join_line`이 단어 bbox 간격(<글자높이*0.35)이면 붙이고 크면 공백 → 한국어 복원. line_num 기반 줄 결합 추가.
- KPI: 한국어 공백 분절은 OCR 본질 한계라 정확성(문자 인식)은 공백 정규화 CER로 측정. 합성 렌더는 편차가 커(0~16%) 게이트는 ≤12%, 영문 라인 ≤5%로 보수 설정. 실 스캔 골든셋은 후속.

### HWP 표 복원
- pyhwp HTMLTransform.transform_hwp5_to_xhtml로 표를 <table>로 받는다. `_parse_xhtml`(lxml)이 표/단락을 문서 순서로 추출, 표 내부 <p>는 셀이 흡수해 제외.
- 실패 시 TextTransform 평문 폴백 유지. 실 .hwp 생성기가 없어 순수 파서만 합성 XHTML로 회귀, E2E는 샘플 확보 시.

## 2026-06-26 (5차 — 웹 UI 연동)

### 출처
- /design-sync 명령으로 들어왔으나, 그 스킬(디자인시스템→claude.ai/design 업로드)은 이 작업과 방향이 반대라 절차 대신 목표만 차용. 사용자가 공유한 claude.ai/design 프로젝트("화면 디자인 요청", projectId 657336a6…)에서 DesignSync(get_file)로 OCR Configuration.html / ocr-screen.css / ocr-screen.js / OCR Pipeline.html을 읽어와 디자인을 확보.

### 구현 결정
- 사용자 선택: "실제 파이프라인 연동 웹앱". webui/(정적) + webserver.py(FastAPI).
- ocr-screen.css는 디자인 원본 그대로 보존(토큰 계약). index.html/app.js는 디자인 마크업·클래스를 충실히 재사용하되 업로드/Run/결과 렌더를 실제 동작으로 연결.
- 모델 매핑: Fast/Balanced→use_llm=false, Accurate→use_llm=true.
- 업로드는 TemporaryDirectory에 원본 파일명으로 저장 → 문서 제목이 임시파일명으로 나오는 문제 방지.

### 함정
- FastAPI: StaticFiles를 "/"에 html=True로 마운트하면 모든 경로를 잡으므로 /api 라우트를 먼저 등록하고 마운트는 마지막에.
- 검증 중 백그라운드 uvicorn이 포트 8000을 계속 점유해 stale 인스턴스가 404를 응답 → Get-NetTCPConnection으로 PID 종료 후 재기동. TestClient(test_webapi.py)는 포트 독립이라 신뢰적.
- 이 bash 환경엔 /tmp가 없음 → 로그 리디렉션은 스크래치패드 경로 사용.
