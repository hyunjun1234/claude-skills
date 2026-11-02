#!/usr/bin/env python3
"""sota-deck 검수. 템플릿 덱이 사용자 규칙을 지키는지 본다. 하나라도 걸리면 1로 끝난다.

    python3 check_deck.py /abs/deck.pptx [--allow-pictures]

이 스킬만의 검사(금지 문자, 메모, 글자 크기와 색, 글꼴, 이름표 번호, 그림 개체) 다음에
diagram-deck 의 check_ooxml.py, check_layout.py 를 돌린다. check_layout 은 내용 슬라이드만 남긴
사본으로 돌린다. 표지, 목차, 마무리는 템플릿 모양이라 같은 유형 크기 검사(L-47)에서 헛걸린다.
"""
import os
import re
import subprocess
import sys
import tempfile
import zipfile

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sota  # noqa: E402

CONTENT_LAYOUT = "제목만"
DD = os.environ.get("DIAGRAM_DECK_SCRIPTS") or os.path.normpath(
    os.path.join(HERE, "..", "..", "diagram-deck", "scripts"))
HEAD_RX = re.compile(r"^(그림|코드|표) (\d+): ")
IN = 914400

fails = 0


def report(name, items, fmt=str, warn=False):
    global fails
    mark = "✅" if not items else ("⚠️ " if warn else "❌")
    print(f"{mark} {name}: {len(items)}건")
    for it in items[:15]:
        print("   " + fmt(it))
    if len(items) > 15:
        print(f"   외 {len(items) - 15}건")
    if items and not warn:
        fails += 1


def walk(shapes):
    for sh in shapes:
        if sh.shape_type == 6:          # 그룹
            yield from walk(sh.shapes)
        else:
            yield sh


def runs_of(sh):
    """(문단, run, 표 안인가, 표 머리인가)"""
    if sh.has_text_frame:
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                yield p, r, False, False
    if getattr(sh, "has_table", False) and sh.has_table:
        for ri, row in enumerate(sh.table.rows):
            for c in row.cells:
                for p in c.text_frame.paragraphs:
                    for r in p.runs:
                        yield p, r, True, ri == 0


def latin(r):
    rPr = r._r.find(qn("a:rPr"))
    if rPr is None:
        return None
    el = rPr.find(qn("a:latin"))
    return el.get("typeface") if el is not None else None


def color(r):
    rPr = r._r.find(qn("a:rPr"))
    if rPr is None:
        return None
    sf = rPr.find(qn("a:solidFill"))
    if sf is None:
        return None
    c = sf.find(qn("a:srgbClr"))
    return c.get("val").upper() if c is not None else "(테마색)"


def has_bullet(p):
    pPr = p._p.find(qn("a:pPr"))
    return pPr is not None and pPr.find(qn("a:buChar")) is not None


def text_rect(sh):
    """글이 실제로 차지하는 영역 어림(EMU). 정렬과 세로 맞춤을 따른다."""
    tf = sh.text_frame
    ml, mr = tf.margin_left or 0, tf.margin_right or 0
    mt, mb = tf.margin_top or 0, tf.margin_bottom or 0
    inner = max((sh.width - ml - mr) / IN, 0.1)
    tw = th = 0.0
    align = None
    for p in tf.paragraphs:
        sizes = [r.font.size.pt for r in p.runs if r.font.size]
        fs = max(sizes) if sizes else 18.0
        mono = any(latin(r) == sota.F_CODE for r in p.runs)
        w = sota.est_width(p.text, fs, mono)
        n = max(1, -(-int(w * 1000) // int(inner * 1000)))
        tw = max(tw, min(w, inner))
        th += n * fs * 1.2 / 72 + ((p.space_after.pt if p.space_after is not None else 0) / 72)
        align = align or p.alignment
    tw, th = int(tw * IN), int(th * IN)
    if align == PP_ALIGN.CENTER:
        left = sh.left + ml + (sh.width - ml - mr - tw) // 2
    elif align == PP_ALIGN.RIGHT:
        left = sh.left + sh.width - mr - tw
    else:
        left = sh.left + ml
    anchor = tf.vertical_anchor
    if anchor == MSO_ANCHOR.MIDDLE:
        top = sh.top + mt + (sh.height - mt - mb - th) // 2
    elif anchor == MSO_ANCHOR.BOTTOM:
        top = sh.top + sh.height - mb - th
    else:
        top = sh.top + mt
    return left, top, left + tw, top + th


def one(s):
    return " ".join((s or "").split())


def solid(sh):
    try:
        return sh.shape_type == 1 and sh.fill.type == 1      # AUTO_SHAPE, SOLID
    except Exception:
        return False


def hidden_texts(slide, tol=int(0.03 * IN)):
    """글 위에 나중에 그린 채움 도형이 덮는지 본다. 화살표 라벨 틈이 좁으면 생긴다."""
    shapes = [sh for sh in walk(slide.shapes) if sh.left is not None and sh.width]
    hits = []
    for k, sh in enumerate(shapes):
        if not sh.has_text_frame or not sh.text_frame.text.strip():
            continue
        l, t, r, b = text_rect(sh)
        for o in shapes[k + 1:]:
            if not solid(o):
                continue
            ox = min(r, o.left + o.width) - max(l, o.left)
            oy = min(b, o.top + o.height) - max(t, o.top)
            if ox > tol and oy > tol:
                cover = o.text_frame.text if o.has_text_frame else ""
                hits.append((one(sh.text_frame.text)[:30], one(cover)[:20] or o.name))
                break
    return hits


def main(path, allow_pics=False):
    prs = Presentation(path)
    slides = list(prs.slides)
    content = [i for i, s in enumerate(slides, 1) if s.slide_layout.name == CONTENT_LAYOUT]
    print(f"슬라이드 {len(slides)}장 (내용 {len(content)}장) 검사: {path}\n")

    bad_ch, small, fonts, colors, notes_bad, title_long, hidden = [], [], [], [], [], [], []
    roles = {"표 본문": {}, "표 머리": {}, "코드": {}, "글머리": {}, "이름표": {}, "부제": {}}
    heads = {"그림": [], "코드": [], "표": []}

    for i, s in enumerate(slides, 1):
        is_content = i in content
        for sh in walk(s.shapes):
            is_title = sh.is_placeholder and sh.placeholder_format.type in (1, 3)   # TITLE, CENTER_TITLE
            whole = sh.text_frame.text.strip() if sh.has_text_frame else ""
            m = HEAD_RX.match(whole)
            if m and is_content:
                heads[m.group(1)].append((i, int(m.group(2))))
            top = (sh.top or 0) / IN
            is_sub = is_content and sh.has_text_frame and 1.3 <= top <= 1.5 and not is_title
            if is_content and is_title and whole and sota.est_width(whole, 32) > 11.2:
                title_long.append((i, whole))
            for p, r, in_tbl, tbl_head in runs_of(sh):
                t = r.text
                for ch, nm in sota.bad_chars(t):
                    bad_ch.append((i, ch, nm, t.strip()[:40]))
                pt = r.font.size.pt if r.font.size else None
                if pt is not None and pt < sota.MIN_PT and t.strip():
                    small.append((i, pt, t.strip()[:40]))
                f = latin(r)
                if f and f not in sota.FONTS:
                    fonts.append((i, f, t.strip()[:30]))
                mono = f == sota.F_CODE
                if is_content and not is_title and not mono and t.strip():
                    c = color(r)
                    if c and c not in sota.TEXT_COLORS:
                        colors.append((i, c, t.strip()[:30]))
                if not is_content or pt is None or not t.strip():
                    continue
                if in_tbl:
                    roles["표 머리" if tbl_head else "표 본문"].setdefault(pt, set()).add(i)
                elif mono:
                    roles["코드"].setdefault(pt, set()).add(i)
                elif m:
                    roles["이름표"].setdefault(pt, set()).add(i)
                elif is_sub:
                    roles["부제"].setdefault(pt, set()).add(i)
                elif has_bullet(p):
                    roles["글머리"].setdefault(pt, set()).add(i)
        if is_content:
            hidden += [(i,) + h for h in hidden_texts(s)]
        # 메모
        notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
        for ch, nm in sota.bad_chars(notes):
            bad_ch.append((i, ch, nm, "(메모) " + notes.strip()[:30]))
        if is_content:
            lines = [x for x in notes.split("\n") if x.strip()]
            if not lines:
                notes_bad.append((i, "메모 없음"))
            elif any(not x.startswith("- ") for x in lines):
                notes_bad.append((i, "'- ' 로 시작하지 않는 줄이 있다"))
            elif len(lines) > 8:
                notes_bad.append((i, f"{len(lines)}줄. 짧게 줄인다(3~6줄)"))

    report("금지 문자 (가운뎃점, 줄표, 화살표 문자, 체크, 원문자, 참고표, 말줄임표, 이모지)", bad_ch,
           lambda x: f"p{x[0]:2d} '{x[1]}' {x[2]}: {x[3]}")
    report(f"{sota.MIN_PT}pt 보다 작은 글자", small, lambda x: f"p{x[0]:2d} {x[1]}pt: {x[2]}")
    report("템플릿 밖 글꼴", fonts, lambda x: f"p{x[0]:2d} {x[1]}: {x[2]}")
    report("허용 밖 글자색 (잉크, 회색, 흰색만. 강조는 굵기로, L-32)", colors, lambda x: f"p{x[0]:2d} #{x[1]}: {x[2]}")
    report("발표자 메모", notes_bad, lambda x: f"p{x[0]:2d} {x[1]}")
    report("제목이 한 줄을 넘음 (32pt 기준 어림)", title_long, lambda x: f"p{x[0]:2d} {x[1]}")
    report("글이 나중에 그린 채움 도형에 가려짐 (L-27, L-35)", hidden,
           lambda x: f"p{x[0]:2d} '{x[1]}' 을 '{x[2]}' 가 덮음")
    uneven = [(k, {pt: sorted(v) for pt, v in d.items()}) for k, d in roles.items() if len(d) > 1]
    report("같은 역할인데 글자 크기가 다름 (L-30, L-47)", uneven,
           lambda x: f"{x[0]}: " + ", ".join(f"{pt}pt p{v}" for pt, v in sorted(x[1].items())))
    hb = []
    for kind, lst in heads.items():
        nums = [n for _, n in lst]
        if nums != list(range(1, len(nums) + 1)):
            hb.append((kind, lst))
    report("이름표 번호가 1부터 차례대로가 아님 (그림 N, 코드 N, 표 N)", hb,
           lambda x: f"{x[0]}: " + ", ".join(f"p{i} {n}" for i, n in x[1]))

    # 그림 개체, 좌표, 날 개행
    z = zipfile.ZipFile(path)
    pics, frac, rawlf = [], 0, 0
    for n in z.namelist():
        if not re.match(r"ppt/slides/slide\d+\.xml$", n):
            continue
        x = z.read(n).decode("utf-8")
        k = x.count("<p:pic>") + x.count("<p:pic ")
        if k:
            pics.append((n.split("/")[-1], k))
        for a in ("x", "y", "cx", "cy"):
            frac += sum(1 for v in re.findall(rf'\b{a}="([-\d.eE+]+)"', x) if "." in v or "e" in v.lower())
        rawlf += len(re.findall(r"<a:t>[^<]*\n[^<]*</a:t>", x))
    if allow_pics:
        report("그림 개체 (허용됨)", pics, lambda x: f"{x[0]} {x[1]}개", warn=True)
    else:
        report("그림 개체 (아이콘, 그림 파일 금지. 사용자가 준 그림이면 --allow-pictures)", pics,
               lambda x: f"{x[0]} {x[1]}개")
    report("소수 좌표 (정수 EMU 여야 한다, L-02)", [frac] if frac else [], lambda x: f"{x}개")
    report("<a:t> 안 날 개행 (L-03)", [rawlf] if rawlf else [], lambda x: f"{x}개")

    # diagram-deck 검사기
    print()
    if not os.path.isdir(DD):
        print(f"⚠️  diagram-deck 검사기가 없다({DD}). OOXML 순서와 레이아웃 검사를 건너뛴다")
        return
    r = subprocess.run([sys.executable, os.path.join(DD, "check_ooxml.py"), path], capture_output=True, text=True)
    print("[diagram-deck check_ooxml]")
    print("\n".join(ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()))
    if r.returncode:
        fails_add()

    prs2 = Presentation(path)
    lst = prs2.slides._sldIdLst
    for sid, s in zip(list(lst), list(prs2.slides)):
        if s.slide_layout.name != CONTENT_LAYOUT:
            prs2.part.drop_rel(sid.rId)
            lst.remove(sid)
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "content_only.pptx")
        prs2.save(tmp)
        r = subprocess.run([sys.executable, os.path.join(DD, "check_layout.py"), tmp],
                           capture_output=True, text=True)
    print("\n[diagram-deck check_layout, 내용 슬라이드만. p 번호는 내용 슬라이드 순번]")
    out = r.stdout.splitlines()
    keep, show = [], False
    for ln in out:
        if ln.startswith("⚠"):
            show = True
            keep.append(ln)
        elif ln.startswith("✅") or not ln.strip():
            show = False
        elif show or ln.startswith("총") or ln.startswith("슬라이드"):
            keep.append(ln)
    print("\n".join(keep) if keep else "(출력 없음)")
    if r.stderr.strip():
        print(r.stderr.strip()[-800:])
    if r.returncode:
        fails_add()


def fails_add():
    global fails
    fails += 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(os.path.abspath(sys.argv[1]), allow_pics="--allow-pictures" in sys.argv)
    print("\n" + ("✅ 전부 통과" if fails == 0 else f"❌ 실패 {fails}항목. 고쳐서 다시 돌린다. 통과 전에는 내지 않는다"))
    sys.exit(1 if fails else 0)
