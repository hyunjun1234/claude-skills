#!/usr/bin/env python3
"""PDF → PPTX (직접 변환).

  pdf2pptx.py in.pdf out.pptx [--dpi 200] [--no-notes]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topptx import pdf_to_pptx, report  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--dpi", type=int, default=200)
ap.add_argument("--no-notes", action="store_true")
a = ap.parse_args()

info = pdf_to_pptx(a.src, a.out, a.dpi, not a.no_notes)
report(info, a.src, a.out)
