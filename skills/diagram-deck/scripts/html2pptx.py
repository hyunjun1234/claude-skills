#!/usr/bin/env python3
"""HTML → PPTX (직접 변환. 중간 PDF 파일을 만들지 않는다).

  html2pptx.py in.html out.pptx [--dpi 200] [--no-notes] [--keep-pdf out.pdf]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topptx import html_to_pptx, report  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--dpi", type=int, default=200)
ap.add_argument("--no-notes", action="store_true")
ap.add_argument("--keep-pdf", default=None, help="중간 PDF 도 남기고 싶을 때만")
a = ap.parse_args()

info = html_to_pptx(a.src, a.out, a.dpi, not a.no_notes, a.keep_pdf)
report(info, a.src, a.out)
