# CLI 진입점: python -m ocr_docintel <pdf> [-o out_dir] [--no-llm]
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from .pipeline import process
from .identify import UnsupportedFormatError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ocr_docintel", description="구조 보존 OCR (텍스트 PDF MVP)")
    ap.add_argument("input", help="입력 PDF 경로")
    ap.add_argument("-o", "--out", default=".", help="출력 디렉터리")
    ap.add_argument("--no-llm", action="store_true", help="LLM 맥락 단계 비활성(결정론적)")
    args = ap.parse_args(argv)

    try:
        res = process(args.input, use_llm=not args.no_llm)
    except (UnsupportedFormatError, FileNotFoundError) as e:
        print(f"[오류] {e}", file=sys.stderr)
        return 1

    stem = Path(args.input).stem
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{stem}.md").write_text(res.markdown, encoding="utf-8")
    (outdir / f"{stem}.json").write_text(res.json, encoding="utf-8")
    print(f"완료: {outdir / (stem + '.md')}, {outdir / (stem + '.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
