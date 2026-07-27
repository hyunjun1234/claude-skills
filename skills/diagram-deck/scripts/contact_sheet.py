#!/usr/bin/env python3
"""도해 검수용 대지 — 만든 그림들을 한 장(또는 몇 장)에 모아 눈으로 확인한다."""
import json
import math
import sys

from PIL import Image, ImageDraw

IDX = sys.argv[1]
OUT = sys.argv[2]
PER = int(sys.argv[3]) if len(sys.argv) > 3 else 9   # 대지 한 장에 담을 개수
TW = 900                                             # 축소 폭

items = json.load(open(IDX, encoding="utf-8"))
sheets = []
for k in range(0, len(items), PER):
    chunk = items[k:k + PER]
    cols = 3
    rows = math.ceil(len(chunk) / cols)
    thumbs = []
    for it in chunk:
        im = Image.open(it["png"]).convert("RGB")
        r = TW / im.width
        thumbs.append((it, im.resize((TW, max(1, int(im.height * r))), Image.LANCZOS)))
    rh = [max((t[1].height for t in thumbs[r * cols:(r + 1) * cols]), default=1)
          for r in range(rows)]
    H = sum(rh) + rows * 34 + 24
    sheet = Image.new("RGB", (cols * (TW + 16) + 16, H), "white")
    dr = ImageDraw.Draw(sheet)
    y = 12
    for r in range(rows):
        x = 12
        for it, im in thumbs[r * cols:(r + 1) * cols]:
            dr.rectangle([x - 2, y + 20, x + TW + 2, y + 22 + im.height], outline="#c8d2dc")
            dr.text((x, y), f"[{it['part']}#{it['index']:02d}] {it['title'][:64]}", fill="#b4222a")
            sheet.paste(im, (x, y + 22))
            x += TW + 16
        y += rh[r] + 34
    p = OUT if len(items) <= PER else OUT.replace(".png", f"_{k//PER+1}.png")
    sheet.save(p)
    sheets.append(p)
    print(f"{p}  {sheet.size[0]}x{sheet.size[1]}  ({len(chunk)}개)")
print(f"총 {len(items)}개 → 대지 {len(sheets)}장")
