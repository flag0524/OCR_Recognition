# HWP 식별 + 손상 파일 오류 처리 테스트 (실제 HWP 생성기가 없어 best-effort 경로만 검증)
import pytest
from ocr_docintel.identify import identify
from ocr_docintel.extract_hwp import extract, HwpExtractError, _parse_xhtml


def _fake_hwp(tmp_path):
    # OLE 시그니처 + .hwp 확장자 → 식별은 hwp, 내용은 손상.
    p = tmp_path / "broken.hwp"
    p.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64)
    return p


def test_hwp_identified(tmp_path):
    assert identify(_fake_hwp(tmp_path)) == "hwp"


def test_corrupt_hwp_raises(tmp_path):
    with pytest.raises(HwpExtractError):
        extract(_fake_hwp(tmp_path))


# pyhwp가 생성하는 XHTML 표 구조를 파싱하는 순수 함수 검증(실 HWP 생성기 부재 대체).
_XHTML = """<html><body>
  <p>첫 번째 단락입니다.</p>
  <table>
    <tr><td>항목</td><td>값</td></tr>
    <tr><td>매출</td><td>120</td></tr>
  </table>
  <p>표 다음 단락.</p>
</body></html>"""


def test_parse_xhtml_order_and_table():
    items = _parse_xhtml(_XHTML)
    kinds = [k for k, _ in items]
    assert kinds == ["para", "table", "para"]  # 문서 순서 보존
    table = items[1][1]
    assert table == [["항목", "값"], ["매출", "120"]]


def test_parse_xhtml_excludes_inner_cell_paragraphs():
    # 셀 안의 <p>는 별도 단락으로 새지 않아야 한다.
    xhtml = "<html><body><table><tr><td><p>셀 안 문장</p></td></tr></table></body></html>"
    items = _parse_xhtml(xhtml)
    assert [k for k, _ in items] == ["table"]
    assert items[0][1] == [["셀 안 문장"]]
