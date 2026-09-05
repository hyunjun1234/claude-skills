#!/usr/bin/env python3
"""덱에 들어갈 SVG **전부**의 내용 상자를 한 번에 잰다 (L-48, L-49).

한 그림만 넓거나 높으면 그 그림이 아니라 **다른 슬라이드**가 L-30 축척 불일치로 걸린다
(내용 폭이 큰 그림이 기준이 되어 나머지가 97% 로 보인다). 그래서 손댄 그림만이 아니라
덱의 SVG 전부를 매번 잰다. 높이도 본다 — 내용 높이가 예산을 넘으면 diagram_svg 가 높이에 맞춰
축소하므로 폭이 828 이어도 그 슬라이드가 좁아진다. 긴 글줄은 되돌려 비교(2%)를 넘기게 하므로 경고한다.

  python check_svgs.py <svg 디렉터리 또는 svg 파일...> [--width 828] [--height 234] [--min-font 10.5] [--max-text 60]

기준: 내용 폭 == width ±2 (viewBox 950 기준 x 16..844), 내용 높이 <= height, 글자 >= min-font → 어긋나면 exit 1.
글자 수 > max-text 인 <text> 는 경고만(되돌려 비교가 2% 를 넘으면 이것부터 줄인다).
"""
import argparse
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg2shapes import content_bbox  # noqa: E402


def check(path, width, height, min_font, max_text):
    svg = open(path, encoding="utf-8").read()
    ET.fromstring(svg)  # XML 이 깨졌으면 여기서 예외
    x0, y0, x1, y1 = content_bbox(svg)
    w, h = x1 - x0, y1 - y0
    fonts = [float(m) for m in re.findall(r'font-size="([0-9.]+)"', svg)]
    fmin = min(fonts) if fonts else float("inf")
    texts = [re.sub(r"<[^>]+>", "", t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)]
    long_texts = [t for t in texts if len(t) > max_text]
    bad = []
    if abs(w - width) > 2:
        bad.append(f"내용 폭 {w:.0f} ≠ {width:g} ({x0:.0f}..{x1:.0f})")
    if h > height:
        bad.append(f"내용 높이 {h:.0f} > {height:g} ({y0:.0f}..{y1:.0f})")
    if fmin < min_font:
        bad.append(f"최소 글자 {fmin:g} < {min_font:g}")
    return w, h, fmin, bad, long_texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--width", type=float, default=828)
    ap.add_argument("--height", type=float, default=234)
    ap.add_argument("--min-font", type=float, default=10.5)
    ap.add_argument("--max-text", type=int, default=60)
    a = ap.parse_args()
    files = []
    for p in a.paths:
        files += sorted(glob.glob(os.path.join(p, "*.svg"))) if os.path.isdir(p) else [p]
    if not files:
        print("SVG 없음")
        return 1
    fails = warns = 0
    for f in files:
        w, h, fmin, bad, long_texts = check(f, a.width, a.height, a.min_font, a.max_text)
        tag = "❌" if bad else ("⚠️ " if long_texts else "✅")
        extra = ("   " + "; ".join(bad)) if bad else ""
        if long_texts:
            extra += f"   긴 글줄 {len(long_texts)}개(>{a.max_text}자): '{long_texts[0][:30]}…'"
        print(f"{tag} {os.path.basename(f):28s} 폭 {w:6.1f}  높이 {h:6.1f}  글자 {fmin:>5g}{extra}")
        fails += bool(bad)
        warns += bool(long_texts)
    print(f"{'❌' if fails else '✅'} SVG {len(files)}개 중 어긋남 {fails}개, 긴 글줄 경고 {warns}개 "
          f"(기준: 폭 {a.width:g}±2, 높이 ≤ {a.height:g}, 글자 ≥ {a.min_font:g}, 글줄 ≤ {a.max_text}자)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
