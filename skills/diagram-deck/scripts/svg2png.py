#!/usr/bin/env python3
"""SVG(HTML) → 여백 없이 딱 맞게 잘린 PNG.

PPT 에 넣었을 때 선택 박스가 그림보다 커지지 않도록, 렌더 후 흰 여백을 전부 잘라낸다.
"""
import io
import os
import re

from PIL import Image
from weasyprint import HTML

DPI = 220


def render(svg: str, out_png: str, dpi: int = DPI, pad: int = 3) -> tuple:
    """svg 마크업을 받아 트림된 PNG 를 쓴다. (폭px, 높이px, 인치폭, 인치높이) 반환."""
    m = re.search(r'viewBox\s*=\s*["\']([\d.\-\s]+)["\']', svg)
    if not m:
        raise ValueError("viewBox 가 없다")
        # viewBox 는 필수다. 크기를 알아야 페이지를 딱 맞게 만든다.
    x0, y0, vw, vh = [float(v) for v in m.group(1).split()]
    # 페이지를 viewBox 와 같은 크기로 잡고 여백 0
    html = (
        '<meta charset="utf-8"><style>'
        f'@page{{size:{vw}pt {vh}pt;margin:0}}'
        'html,body{margin:0;padding:0;background:#fff}'
        'svg{display:block}'
        '</style>'
        + re.sub(r'<svg\b', f'<svg width="{vw}pt" height="{vh}pt"', svg, count=1)
    )
    import fitz
    pdf = HTML(string=html).write_pdf()
    doc = fitz.open("pdf", pdf)
    zoom = dpi / 72.0
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    # 흰 여백 트림 (거의 흰색까지 여백으로 본다)
    gray = im.convert("L")
    mask = gray.point(lambda v: 0 if v > 247 else 255)
    bbox = mask.getbbox()
    if bbox:
        l, t, r, b = bbox
        l = max(0, l - pad); t = max(0, t - pad)
        r = min(im.width, r + pad); b = min(im.height, b + pad)
        im = im.crop((l, t, r, b))
    im.save(out_png)
    return im.width, im.height, im.width / dpi, im.height / dpi


if __name__ == "__main__":
    demo = '''<svg viewBox="0 0 420 150" xmlns="http://www.w3.org/2000/svg" font-family="Noto Sans CJK KR">
      <rect x="10" y="10" width="180" height="70" rx="8" fill="#e3eefb" stroke="#0b5fc0" stroke-width="2"/>
      <text x="100" y="52" font-size="17" text-anchor="middle" fill="#083f80">슬라이스</text>
      <line x1="196" y1="45" x2="248" y2="45" stroke="#0b5fc0" stroke-width="2.4"/>
      <polygon points="246,38 262,45 246,52" fill="#0b5fc0"/>
      <rect x="270" y="10" width="140" height="70" rx="8" fill="#e2f4e8" stroke="#1a7f37" stroke-width="2"/>
      <text x="340" y="52" font-size="17" text-anchor="middle" fill="#1a7f37">연산 유닛</text>
    </svg>'''
    w, h, iw, ih = render(demo, "_svg_demo.png")
    print(f"viewBox 420x150pt → 트림 후 {w}x{h}px = {iw:.2f}x{ih:.2f}in @ {DPI}dpi")
    print(f"  (트림 안 했다면 {int(420/72*DPI)}x{int(150/72*DPI)}px 였을 것)")
