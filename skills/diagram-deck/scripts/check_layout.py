#!/usr/bin/env python3
"""슬라이드 레이아웃 점검 — 글자 넘침·도형 겹침·경계 이탈.

python-pptx 는 텍스트를 실제로 조판하지 않으므로, 글자 폭/높이를 추정해서 검사한다.
추정이라 완벽하진 않지만 '명백히 넘치는 것'은 잡는다.
"""
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

from pptx import Presentation
from pptx.util import Emu

EMU_IN = 914400.0
PT_EMU = 12700.0


def vlen(s):
    return sum(2 if ord(c) > 0x2E80 else 1 for c in s)


def _real_width(seg, fs, name, bold, ea=None):
    """실제 글꼴로 잰 폭(pt). 못 재면 None.

    반각 어림짐작은 영문 라벨에서 10% 넘게 틀려 헛경고를 만든다.
    도해 안 라벨은 폭에 딱 맞춰 상자를 잡으므로 정확히 재야 한다.
    한글은 `a:ea` 글꼴로 그려지므로 그 이름으로 재야 한다.
    """
    try:
        import os
        import sys as _s
        _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from svg2shapes import measure
        return measure(seg, fs, name or "맑은 고딕", bold, ea)
    except Exception:
        return None


def _ea_of(p):
    """문단 첫 run 의 East-Asian 타이프페이스."""
    from pptx.oxml.ns import qn
    for r in p.runs:
        rPr = r._r.find(qn("a:rPr"))
        if rPr is None:
            continue
        e = rPr.find(qn("a:ea"))
        if e is not None and e.get("typeface"):
            return e.get("typeface")
    return None


def est_size(shape):
    """(필요한 높이 pt, 가장 긴 줄의 폭 pt) 추정."""
    tf = shape.text_frame
    w_emu = shape.width or 0
    ml = tf.margin_left or 0
    mr = tf.margin_right or 0
    w_pt = max((w_emu - ml - mr) / PT_EMU, 10)
    total_h = 0.0
    max_w = 0.0
    for p in tf.paragraphs:
        sizes = [r.font.size.pt for r in p.runs if r.font.size is not None]
        fs = max(sizes) if sizes else 18.0
        mono = any((r.font.name or "") == "Consolas" for r in p.runs)
        per = fs * (0.55 if mono else 0.5)      # 반각 1칸의 폭
        fname = next((r.font.name for r in p.runs if r.font.name), None)
        fbold = any(bool(r.font.bold) for r in p.runs)
        fea = _ea_of(p)
        # p.text 는 <a:br/> 를 '\v' 로 준다 — 강제 줄바꿈으로 센다
        segs = (p.text or "").split("\v")
        lines = 0
        for seg in segs:
            line_w = _real_width(seg, fs, fname, fbold, fea) if seg else 0
            if line_w is None:
                line_w = vlen(seg) * per
            max_w = max(max_w, line_w)
            lines += max(1, int(line_w / w_pt) + (1 if line_w % w_pt else 0)) if seg else 1
        ls = p.line_spacing if isinstance(p.line_spacing, float) else 1.2
        sb = p.space_before.pt if p.space_before is not None else 0
        sa = p.space_after.pt if p.space_after is not None else 0
        total_h += lines * fs * ls + sb + sa
    mt = (tf.margin_top or 0) / PT_EMU
    mb = (tf.margin_bottom or 0) / PT_EMU
    return total_h + mt + mb, max_w


def boxes(slide):
    """그룹 **안쪽까지** 훑는다.

    도해를 네이티브 도형 그룹으로 넣으면 슬라이드 최상위에는 그룹 하나만 보인다.
    그룹을 안 열면 도해 슬라이드는 사실상 무검사가 된다.
    """
    out = []

    def walk(container, depth=0):
        for sh in container:
            if sh.shape_type == 6 and depth < 4:        # GROUP
                walk(sh.shapes, depth + 1)
                continue
            if sh.left is None or sh.top is None:
                continue
            txt = sh.text_frame.text.strip() if sh.has_text_frame else ""
            out.append({
                "sh": sh, "txt": txt, "in_group": depth > 0,
                "l": sh.left, "t": sh.top,
                "r": sh.left + (sh.width or 0), "b": sh.top + (sh.height or 0),
            })
    walk(slide.shapes)
    return out


_PUNCT = re.compile(r"[\s'\"“”‘’·,.…—\-()\[\]:;!?{}=+·]")


def _norm(s):
    return _PUNCT.sub("", s)


def _maxpt(sh):
    m = 0.0
    if not sh.has_text_frame:
        return m
    for p in sh.text_frame.paragraphs:
        for r in p.runs:
            if r.font.size:
                m = max(m, r.font.size.pt)
    return m


def dup_texts(bs, thr=0.80):
    """도해(그룹) 안 글자가 슬라이드 제목·핵심줄과 같은 말인지 본다.

    도해를 SVG 로 그릴 때 그림 안에 제목을 또 넣거나, 그림 아래 띠의 문장을
    콜아웃에 그대로 옮겨 적으면 한 슬라이드에 같은 말이 두 번 찍힌다(L-18).
    """
    inside = [b for b in bs if b["in_group"] and b["txt"]]
    if not inside:
        return []
    outside = [b for b in bs if not b["in_group"] and b["txt"]]
    refs = []
    titles = [(_maxpt(b["sh"]), b["txt"]) for b in outside]
    titles = [t for t in titles if t[0] >= 18]
    if titles:
        refs.append(("제목", max(titles, key=lambda t: t[0])[1]))
    for b in outside:
        if b["txt"].startswith("핵심"):
            refs.append(("핵심", b["txt"][2:].strip()))
    hits = []
    for label, ref in refs:
        rn = _norm(ref)
        if len(rn) < 8:
            continue
        for b in inside:
            tn = _norm(b["txt"])
            if len(tn) < 8:
                continue
            ratio = SequenceMatcher(None, rn, tn).ratio()
            if ratio >= thr:
                hits.append((label, ref[:36], b["txt"][:36], round(ratio, 2)))
    return hits


ABSOLUTES = ("공통", "전부", "모두", "아무도", "뿐", "항상", "그대로",
             "언제나", "절대", "유일", "전혀", "무조건")


def absolutes(bs):
    """전칭 표현을 뽑는다 — 상세 슬라이드가 붙으면 가장 먼저 거짓이 되는 표현이다(L-19).

    자동 판정은 못 한다. 사람이 눈으로 확인하라고 뽑아 주는 것이다.
    """
    hits = []
    for b in bs:
        t = b["txt"]
        if not t:
            continue
        # 도해 안 라벨과 '핵심' 한 줄만 본다. 본문 불릿까지 넣으면 잡음이 너무 많아
        # 아무도 안 읽는다 — 짧게 단정하는 자리가 위험한 자리다.
        if not b["in_group"] and not t.startswith("핵심"):
            continue
        for w in ABSOLUTES:
            if w in t:
                hits.append((w, t[:60], "도해" if b["in_group"] else "핵심"))
                break
    return hits


def overlap(a, b):
    ox = min(a["r"], b["r"]) - max(a["l"], b["l"])
    oy = min(a["b"], b["b"]) - max(a["t"], b["t"])
    if ox <= 0 or oy <= 0:
        return 0.0
    inter = ox * oy
    amin = min((a["r"] - a["l"]) * (a["b"] - a["t"]), (b["r"] - b["l"]) * (b["b"] - b["t"]))
    return inter / amin if amin else 0.0


def main(path):
    prs = Presentation(path)
    W, H = prs.slide_width, prs.slide_height
    over_h, over_w, collide, outside, dups = [], [], [], [], []
    for i, s in enumerate(prs.slides, 1):
        bs = boxes(s)
        for b in bs:
            sh = b["sh"]
            if b["l"] < -Emu(5000) or b["t"] < -Emu(5000) or b["r"] > W + Emu(20000) or b["b"] > H + Emu(20000):
                outside.append((i, b["txt"][:40], round(b["r"] / EMU_IN, 2), round(b["b"] / EMU_IN, 2)))
            if not b["txt"] or not sh.has_text_frame:
                continue
            need_h, need_w = est_size(sh)
            box_h = (sh.height or 0) / PT_EMU
            box_w = (sh.width or 0) / PT_EMU
            # 텍스트박스는 아래로 흘러넘쳐 아래 도형을 덮는다
            if need_h > box_h * 1.25 and need_h - box_h > 6:
                over_h.append((i, b["txt"][:44], round(need_h, 1), round(box_h, 1)))
            # 도형 라벨이 한 줄인데 폭을 넘으면 좌우로 삐져나온다
            if len(sh.text_frame.paragraphs) == 1 and need_w > box_w * 1.02 and box_h < 34:
                over_w.append((i, b["txt"][:44], round(need_w, 1), round(box_w, 1)))
        # 글자 있는 도형끼리 심하게 겹치는지
        tb = [b for b in bs if b["txt"]]
        for x in range(len(tb)):
            for y in range(x + 1, len(tb)):
                r = overlap(tb[x], tb[y])
                if r > 0.55:
                    collide.append((i, tb[x]["txt"][:26], tb[y]["txt"][:26], round(r, 2)))
        for h in dup_texts(bs):
            dups.append((i,) + h)

    def rep(name, items, fmt):
        print(f"\n{'✅' if not items else '⚠️ '} {name}: {len(items)}건")
        for it in items[:18]:
            print("   " + fmt(it))
        if len(items) > 18:
            print(f"   … 외 {len(items)-18}건")

    print(f"슬라이드 {len(prs.slides._sldIdLst)}장 검사")
    rep("슬라이드 경계 이탈", outside, lambda x: f"p{x[0]:3d} R{x[2]} B{x[3]}  '{x[1]}'")
    rep("세로 넘침(아래 도형을 덮을 수 있음)", over_h,
        lambda x: f"p{x[0]:3d} 필요 {x[2]}pt / 박스 {x[3]}pt  '{x[1]}'")
    rep("가로 넘침(라벨이 도형 밖으로)", over_w,
        lambda x: f"p{x[0]:3d} 필요 {x[2]}pt / 박스 {x[3]}pt  '{x[1]}'")
    rep("글자 있는 도형끼리 겹침", collide,
        lambda x: f"p{x[0]:3d} {x[3]:.0%}  '{x[1]}' ↔ '{x[2]}'")
    rep("도해 안 글자가 슬라이드 글자와 중복", dups,
        lambda x: f"p{x[0]:3d} {x[4]:.0%} {x[1]}  '{x[2]}' ↔ 도해 '{x[3]}'")
    bad = len(outside) + len(over_h) + len(over_w) + len(collide) + len(dups)
    print(f"\n{'✅ 레이아웃 문제 없음' if bad == 0 else f'총 {bad}건 확인 필요'}")
    return 1 if bad else 0


def report_absolutes(path):
    """검사가 아니라 검토 보조다. 전칭 표현이 있는 슬라이드를 모아 보여 준다."""
    prs = Presentation(path)
    n = 0
    for i, s_ in enumerate(prs.slides, 1):
        hits = absolutes(boxes(s_))
        if not hits:
            continue
        print(f"\np{i:3d}")
        for w, t, where in hits:
            n += 1
            print(f"   [{w}] ({where}) {t}")
    print(f"\n전칭 표현 {n}건 — 상세 슬라이드를 새로 넣었다면 이 문장들을 다시 읽어라(L-19).")
    return 0


if "--absolutes" in sys.argv:
    sys.exit(report_absolutes(sys.argv[1]))
sys.exit(main(sys.argv[1]))
