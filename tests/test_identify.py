# 포맷 식별 단위 테스트
import pytest
from ocr_docintel.identify import identify, UnsupportedFormatError


def test_pdf_signature(single_column_pdf):
    assert identify(single_column_pdf) == "pdf"


def test_unsupported(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"hello world not a pdf")
    with pytest.raises(UnsupportedFormatError):
        identify(f)


def test_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        identify(tmp_path / "nope.pdf")
