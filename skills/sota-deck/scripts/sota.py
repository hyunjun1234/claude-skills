# -*- coding: utf-8 -*-
"""SOTA 랩 템플릿(SOTA_ppt_template_v5.pptx) 위에 덱을 짜는 python-pptx 도구.

글자, 도형, 표, 코드를 전부 PowerPoint 네이티브 개체로 넣는다(그림 파일 없음).
금지 문자와 최소 글자 크기는 쓰는 순간 막는다. 검사기에서 알면 이미 늦다.

    import sys; sys.path.insert(0, "<skill>/scripts")
    from sota import *
    d = Deck()                                   # 템플릿 자동 탐색
    s = d.slide("시스템 구성도", notes=["...", "..."])
    d.head(s, X0, 2.0, CW, "앱과 모델의 연결")     # -> "그림 1: 앱과 모델의 연결"
    node(s, X0, 2.5, 2.0, 0.8, "Browser")
    d.save("/abs/out/deck.pptx")
"""
import copy
import glob
import os
import re

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE, PP_PLACEHOLDER
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
TEMPLATE_NAME = "SOTA_ppt_template_v5.pptx"

# ---------- 색: 무채 + 남색 계열(템플릿 강조색) + 빨강 계열(틀린 것 표시 채움만) (L-32) ----------
NAVY, BLUE, MID, SKY = "002060", "2F5597", "4472C4", "8FAADC"
LIGHT, PALE, PALE2 = "DAE3F3", "EEF3FA", "F7F9FC"
INK, GRAY, GRAY2, LGRAY, BG2, WHITE = "262626", "595959", "7F7F7F", "D9D9D9", "F2F2F2", "FFFFFF"
REDL, RED = "FCE8E8", "C00000"
SUBC = "D6E0F0"            # 남색 채움 위의 보조 글자
TEXT_COLORS = {INK, GRAY, GRAY2, WHITE, SUBC}   # 내용 슬라이드 글자에 허용하는 색

# ---------- 글꼴: 템플릿에 들어 있는 것 + 코드용 ----------
F_LIGHT = "에스코어 드림 3 Light"
F_REG = "에스코어 드림 4 Regular"
F_MED = "에스코어 드림 5 Medium"
F_CODE = "Consolas"
FONTS = {F_LIGHT, F_REG, F_MED, F_CODE, "Cambria"}

# ---------- 글자 크기: 역할마다 하나로 고정 (L-30, L-47). 안 들어가면 크기 말고 내용을 줄인다 ----------
SUB_PT = 14        # 제목 아래 회색 부제
HEAD_PT = 14       # "그림 N:", "코드 N:", "표 N:" 이름표
BODY_PT = 12       # 글머리, 번호 설명, 패널 본문
TABLE_PT = 12      # 표 본문과 머리
CODE_PT = 11       # 코드
NODE_PT = 12       # 도형 이름
NODE_SUB_PT = 11   # 도형 보조 줄, 화살표 라벨
MIN_PT = 11        # 이보다 작은 글자는 만들지 않는다 (L-33)

# ---------- 화면 틀 (인치) ----------
SLIDE_W, SLIDE_H = 13.333, 7.5
X0, X1 = 0.92, 12.42          # 본문 좌우 끝
CW = X1 - X0                  # 11.5
Y0, Y1 = 2.0, 6.6             # 본문 세로 범위 (부제는 1.40~1.76, 꼬리말은 6.95부터)

CEN, LEFT, RIGHT = PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.RIGHT
MID_, TOP_ = MSO_ANCHOR.MIDDLE, MSO_ANCHOR.TOP

# ---------- 금지 문자 (사용자 지적 + L-26, L-29, L-37) ----------
_FORBID = {
    "\u00b7": "가운뎃점", "\u318d": "가운뎃점", "\u2027": "가운뎃점",
    "\u2014": "줄표", "\u2013": "줄표", "\u2015": "줄표",
    "\u2260": "같지 않음 기호", "\u203b": "참고표", "\u2026": "말줄임표",
}
_FORBID_RANGES = [
    ("\u2190", "\u21ff", "화살표 문자"), ("\u27f0", "\u27ff", "화살표 문자"), ("\u2900", "\u297f", "화살표 문자"),
    ("\u2460", "\u24ff", "원문자"), ("\u2776", "\u2793", "원문자"),
    ("\u2600", "\u27bf", "기호, 체크 표시"), ("\U0001f300", "\U0001faff", "이모지"),
]


def bad_chars(s):
    """s 안의 금지 문자 목록 [(문자, 이름)]."""
    out = []
    for ch in s:
        name = _FORBID.get(ch)
        if name is None:
            for lo, hi, nm in _FORBID_RANGES:
                if lo <= ch <= hi:
                    name = nm
                    break
        if name:
            out.append((ch, name))
    return out


def guard(s, where="글"):
    bad = bad_chars(s or "")
    if bad:
        ch, name = bad[0]
        raise ValueError(f"{where}에 금지 문자 '{ch}'({name}): {s[:60]!r}. "
                         f"쉼표, 빗금, '1.' 번호, 코드 주석 '// 1', 또는 문장으로 바꾼다")


def rgb(h):
    return RGBColor.from_string(h)


def I(v):
    return Inches(v)


def est_width(text, pt, mono=False):
    """글 폭 어림(인치). 한글 1자 = 크기, 라틴 1자 = 크기 x 0.55 (고정폭은 0.6)."""
    w = 0.0
    for ch in text:
        if ord(ch) > 0x2E80:
            w += 1.0
        elif ch == " ":
            w += 0.3 if not mono else 0.6
        else:
            w += 0.6 if mono else 0.55
    return w * pt / 72.0


# ---------- 템플릿 찾기 ----------
def find_template(path=None):
    """인자 > SOTA_TEMPLATE 환경변수 > <skill>/assets > 현재 폴더 > 첨부 폴더 순으로 찾는다."""
    cands = [path, os.environ.get("SOTA_TEMPLATE"), os.path.join(SKILL_DIR, "assets", TEMPLATE_NAME)]
    cwd = os.getcwd()
    cands += sorted(glob.glob(os.path.join(cwd, "SOTA_ppt_template*.pptx")))
    cands += sorted(glob.glob(os.path.join(cwd, "*", "SOTA_ppt_template*.pptx")))
    cands += sorted(glob.glob("/mnt/user-data/uploads/**/SOTA_ppt_template*.pptx", recursive=True))
    for c in cands:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    raise FileNotFoundError(
        "SOTA 템플릿을 못 찾았다. 사용자에게 SOTA_ppt_template_v5.pptx 를 받아 Deck(경로) 로 넘기거나 "
        f"SOTA_TEMPLATE 환경변수, 또는 {os.path.join(SKILL_DIR, 'assets', TEMPLATE_NAME)} 에 둔다 "
        "(assets 의 pptx 는 .gitignore 로 저장소에 안 올라간다)")


# ---------- XML 수준 도우미 ----------
def _strip_style(shape):
    st = shape._element.find(qn('p:style'))
    if st is not None:
        shape._element.remove(st)


def set_run_font(run, font=F_LIGHT, size=None, color=None, bold=None):
    """글꼴은 latin, ea, cs 순서로 넣는다. 순서가 어긋나면 PowerPoint 가 손상으로 본다 (L-01)."""
    f = run.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if color is not None:
        f.color.rgb = rgb(color)
    rPr = run._r.get_or_add_rPr()
    for tag in ('a:latin', 'a:ea', 'a:cs'):
        for el in rPr.findall(qn(tag)):
            rPr.remove(el)
    etree.SubElement(rPr, qn('a:latin')).set('typeface', font)
    etree.SubElement(rPr, qn('a:ea')).set('typeface', font if font != F_CODE else F_LIGHT)
    etree.SubElement(rPr, qn('a:cs')).set('typeface', font)
    rPr.set('lang', 'ko-KR')
    rPr.set('altLang', 'en-US')
    rPr.set('dirty', '0')


def _para_props(p, align=None, space_before=None, space_after=None, line_spacing=None,
                bullet=None, indent=0.18, margin=0.0):
    pPr = p._p.get_or_add_pPr()
    pPr.set('latinLnBrk', '0')            # 영단어 중간에서 줄을 바꾸지 않는다
    if align is not None:
        p.alignment = align
    if space_before is not None:
        p.space_before = Pt(space_before)
    if space_after is not None:
        p.space_after = Pt(space_after)
    if line_spacing is not None:
        p.line_spacing = line_spacing
    for tag in ('a:buNone', 'a:buChar', 'a:buAutoNum', 'a:buFont', 'a:buClr'):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    if bullet:
        ch, bcol = bullet if isinstance(bullet, tuple) else (bullet, GRAY2)
        pPr.set('marL', str(int(Inches(margin + indent))))
        pPr.set('indent', str(-int(Inches(indent))))
        etree.SubElement(etree.SubElement(pPr, qn('a:buClr')), qn('a:srgbClr')).set('val', bcol)
        etree.SubElement(pPr, qn('a:buFont')).set('typeface', 'Arial')
        etree.SubElement(pPr, qn('a:buChar')).set('char', ch)
    else:
        if margin:
            pPr.set('marL', str(int(Inches(margin))))
            pPr.set('indent', '0')
        etree.SubElement(pPr, qn('a:buNone'))


def write_paras(tf, paras, size=BODY_PT, color=INK, font=F_LIGHT, align=LEFT,
                space_after=0, space_before=0, line_spacing=None):
    """paras: str('\\n' = 새 문단) 또는 문단 목록.
    문단: str | [run, ...] | dict(runs=, align=, size=, color=, font=, bullet=, space_after=, margin=)
    run: str | (글, {font, size, color, bold}).
    run 안의 '\\n' 은 문단으로 나눈다. <a:t> 안 날 개행은 줄바꿈이 아니다 (L-03)."""
    if isinstance(paras, str):
        paras = paras.split('\n')
    norm = []
    for para in paras:
        if isinstance(para, dict):
            pd = dict(para)
        elif isinstance(para, (list, tuple)) and not (len(para) == 2 and isinstance(para[0], str)
                                                      and isinstance(para[1], dict)):
            pd = {'runs': list(para)}
        else:
            pd = {'runs': [para]}
        runs = pd.get('runs', [])
        if isinstance(runs, (str, tuple)):
            runs = [runs]
        cur, chunks = [], []
        for r in runs:
            t, o = r if isinstance(r, tuple) else (r, {})
            for j, part in enumerate(t.split('\n')):
                if j:
                    chunks.append(cur)
                    cur = []
                cur.append((part, o))
        chunks.append(cur)
        for ch in chunks:
            q = dict(pd)
            q['runs'] = ch
            norm.append(q)
    for k, pd in enumerate(norm):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        _para_props(p, align=pd.get('align', align), space_before=pd.get('space_before', space_before),
                    space_after=pd.get('space_after', space_after),
                    line_spacing=pd.get('line_spacing', line_spacing), bullet=pd.get('bullet'),
                    indent=pd.get('indent', 0.18), margin=pd.get('margin', 0.0))
        psize, pcolor, pfont = pd.get('size', size), pd.get('color', color), pd.get('font', font)
        for t, o in (pd['runs'] or [('', {})]):
            guard(t)
            sz = o.get('size', psize)
            if sz < MIN_PT:
                raise ValueError(f"글자 {sz}pt 는 최소 {MIN_PT}pt 보다 작다: {t[:40]!r}. 내용을 줄이거나 상자를 키운다")
            run = p.add_run()
            run.text = t
            set_run_font(run, font=o.get('font', pfont), size=sz, color=o.get('color', pcolor), bold=o.get('bold'))
        endp = p._p.find(qn('a:endParaRPr'))
        if endp is None:
            endp = etree.SubElement(p._p, qn('a:endParaRPr'))
        endp.set('lang', 'ko-KR')
        endp.set('sz', str(int(psize * 100)))


def R(t, **o):
    """한 run: R("글", font=F_MED, size=12, color=INK, bold=True)."""
    return (t, o)


def _setup_tf(tf, margins=(0.06, 0.04, 0.06, 0.04), anchor=TOP_, wrap=True):
    tf.word_wrap = wrap
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = [I(m) for m in margins]
    tf.vertical_anchor = anchor
    tf.auto_size = MSO_AUTO_SIZE.NONE


# ---------- 기본 도형 ----------
def text(slide, x, y, w, h, paras, size=BODY_PT, color=INK, font=F_LIGHT, align=LEFT, anchor=TOP_,
         margins=(0.06, 0.04, 0.06, 0.04), space_after=0, line_spacing=None, name=None):
    tb = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    if name:
        tb.name = name
    _setup_tf(tb.text_frame, margins, anchor)
    write_paras(tb.text_frame, paras, size=size, color=color, font=font, align=align,
                space_after=space_after, line_spacing=line_spacing)
    return tb


def box(slide, x, y, w, h, fill=PALE, line=None, line_w=1.0, radius=0.05, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        paras=None, size=BODY_PT, color=INK, font=F_LIGHT, align=LEFT, anchor=MID_,
        margins=(0.1, 0.06, 0.1, 0.06), dash=False, space_after=0, name=None):
    shp = slide.shapes.add_shape(shape, I(x), I(y), I(w), I(h))
    _strip_style(shp)
    if name:
        shp.name = name
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        m = min(w, h)
        shp.adjustments[0] = max(0.0, min(0.5, radius / m)) if m > 0 else 0.1
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_w)
        if dash:
            shp.line.dash_style = MSO_LINE.DASH
    _setup_tf(shp.text_frame, margins, anchor)
    if paras is not None:
        write_paras(shp.text_frame, paras, size=size, color=color, font=font, align=align, space_after=space_after)
    return shp


def node(slide, x, y, w, h, title, sub=None, dark=False, fill=None, line=None, size=NODE_PT,
         sub_size=NODE_SUB_PT, align=CEN, dash=False):
    """도해의 상자: 이름 한 줄 + 보조 줄(문자열 또는 목록). 어두운 상자는 흰 글자.
    상자 글자는 라벨이다. 문장이 여러 줄이면 그림이 아니라 표나 글머리로 옮긴다 (L-24, L-41)."""
    f, tc, sc = (NAVY, WHITE, SUBC) if dark else (PALE, INK, GRAY)
    paras = [[R(title, font=F_MED, size=size, color=tc)]]
    for ln in ([] if sub is None else (sub if isinstance(sub, list) else [sub])):
        paras.append([R(ln, size=sub_size, color=sc)])
    return box(slide, x, y, w, h, fill=fill or f, line=line, align=align, dash=dash,
               margins=(0.06, 0.03, 0.06, 0.03), paras=paras)


def arrow(slide, x1, y1, x2, y2, color=GRAY2, width=1.5, both=False, dash=False):
    """직선 연결선 + 삼각 화살촉. 끝점은 도형 변에 맞춘다(덮어 숨기지 않는다, L-35)."""
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, I(x1), I(y1), I(x2), I(y2))
    _strip_style(c)
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if dash:
        c.line.dash_style = MSO_LINE.DASH
    ln = c.line._get_or_add_ln()
    if both:
        he = etree.SubElement(ln, qn('a:headEnd'))
        he.set('type', 'triangle'); he.set('w', 'med'); he.set('len', 'med')
    te = etree.SubElement(ln, qn('a:tailEnd'))
    te.set('type', 'triangle'); te.set('w', 'med'); te.set('len', 'med')
    return c


def harrow(slide, x1, x2, y, label=None, both=False, label_w=None, above=True):
    """가로 화살표 + 위(또는 아래) 라벨. 라벨은 화살표와 겹치지 않게 띄운다 (L-27)."""
    arrow(slide, x1, y, x2, y, both=both)
    if label:
        lw = label_w or abs(x2 - x1) + 0.3
        cx = (x1 + x2) / 2
        text(slide, cx - lw / 2, y - 0.33 if above else y + 0.05, lw, 0.28,
             [R(label, size=NODE_SUB_PT, color=INK)], align=CEN, anchor=MID_, margins=(0, 0, 0, 0))


def varrow(slide, x, y1, y2, both=False):
    arrow(slide, x, y1, x, y2, both=both)


def bullets(slide, x, y, w, h, items, size=BODY_PT, space=6, anchor=TOP_, color=INK):
    """설명은 상자 여러 개로 쪼개지 않고 글상자 하나에 글머리 기호로 (L-29)."""
    paras = [{'runs': [R(t, size=size, color=color)] if isinstance(t, str) else t,
              'bullet': ("•", GRAY2), 'space_after': space} for t in items]
    return text(slide, x, y, w, h, paras, size=size, anchor=anchor)


def numbered(slide, x, y, w, h, items, size=BODY_PT, space=8, anchor=TOP_):
    """코드의 '// 1' 표시와 짝을 이루는 번호 설명. 글상자 하나에 담는다."""
    paras = [{'runs': [R(f"{k}. ", font=F_MED, size=size), R(t, size=size)], 'space_after': space,
              'margin': 0.0} for k, t in enumerate(items, 1)]
    return text(slide, x, y, w, h, paras, size=size, anchor=anchor)


def panel(slide, x, y, w, h, title, items, fill=PALE, anchor=TOP_, size=BODY_PT, dark=False):
    """제목 한 줄 + 글머리 몇 줄을 담은 상자 하나 (카드 격자, 비교 칸)."""
    tc, ic, bc = (WHITE, WHITE, SKY) if dark else (INK, INK, GRAY2)
    paras = [{'runs': [R(title, font=F_MED, size=HEAD_PT, color=tc)], 'space_after': 6}]
    paras += [{'runs': [R(t, size=size, color=ic)], 'bullet': ("•", bc), 'space_after': 4} for t in items]
    return box(slide, x, y, w, h, fill=NAVY if dark else fill, anchor=anchor,
               margins=(0.18, 0.14, 0.14, 0.1), paras=paras)


# ---------- 코드 상자 (VS Code Dark+ 색) ----------
CODEBG, CODEFG = "1E1E1E", "D4D4D4"
_TOKCOL = {None: CODEFG, 'com': "6A9955", 'str': "CE9178", 'kw': "569CD6", 'type': "4EC9B0",
           'num': "B5CEA8", 'ann': "4EC9B0", 'key': "9CDCFE"}
_KW = {
    'python': r"\b(?:def|return|if|not|for|in|raise|from|import|class|None|True|False|and|or|else|elif|with|as|"
              r"assert|lambda|yield|try|except|while|break|continue|async|await)\b",
    'java': r"\b(?:public|private|protected|return|new|if|else|throw|record|interface|static|final|void|null|class|"
            r"extends|implements|for|default|boolean|int|double|this|try|catch|var|throws|while|break|continue|"
            r"true|false)\b",
    'ts': r"\b(?:const|let|await|async|new|return|if|else|function|import|from|export|type|interface)\b",
    'bash': r"(?:^|(?<=\s))(?:export|curl|python3|python|pip|cd|mkdir|java|sudo|bash|git|npm|ollama)\b",
}


def _tokens(line, lang):
    pats = []
    if lang in ('python', 'bash', 'yaml', 'tree'):
        pats.append(('com', r"#.*$"))
    if lang in ('java', 'ts'):
        pats.append(('com', r"//.*$"))
    if lang == 'json':
        pats.append(('key', r'"(?:[^"\\]|\\.)*"(?=\s*:)'))
    if lang in ('yaml', 'md'):
        pats.append(('key', r"^\s*(?:-\s+)?[\w.-]+(?=\s*:)"))
    if lang == 'md':
        pats.append(('com', r"^---\s*$"))
    pats.append(('str', r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''))
    if lang in ('python', 'java'):
        pats.append(('ann', r"@\w+"))
    if lang in _KW:
        pats.append(('kw', _KW[lang]))
    if lang == 'java':
        pats.append(('type', r"\b(?:UUID)\b|\b[A-Z][a-z][A-Za-z0-9]*\b"))
    if lang == 'python':
        pats.append(('type', r"\b(?:str|int|float|list|dict|set|tuple|bool|bytes|[A-Z][a-z][A-Za-z0-9]*)\b"))
    pats.append(('num', r"(?<![\w.])\d+(?:\.\d+)?(?![\w])"))
    rx = re.compile('|'.join(f"(?P<{n}>{p})" for n, p in pats), re.M)
    out, pos = [], 0
    for m in rx.finditer(line):
        if m.start() > pos:
            out.append((line[pos:m.start()], None))
        out.append((m.group(0), m.lastgroup))
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], None))
    return out


def code_h(src, size=CODE_PT):
    """코드 상자 높이(인치). 상자를 내용에 맞춰 빈 띠를 만들지 않는다."""
    n = len(src.strip('\n').split('\n'))
    return round(n * size * 1.2 / 72 + 0.3, 2)


def code(slide, x, y, w, h, src, lang='python', size=CODE_PT):
    """어두운 코드 상자. 줄 끝 주석 '// 1', '# 1' 로 오른쪽 번호 설명과 짝을 맞춘다.
    lang: python, java, ts, bash, json, yaml, md, tree, plain"""
    shp = box(slide, x, y, w, h, fill=CODEBG, radius=0.03, anchor=TOP_, margins=(0.16, 0.12, 0.12, 0.1))
    tf = shp.text_frame
    for k, ln in enumerate(src.strip('\n').split('\n')):
        guard(ln, "코드")
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        _para_props(p, align=LEFT, space_before=0, space_after=0)
        for t, kind in (_tokens(ln, lang) if ln and lang != 'plain' else [(ln, None)]):
            r = p.add_run()
            r.text = t
            set_run_font(r, font=F_CODE, size=size, color=_TOKCOL[kind])
        endp = etree.SubElement(p._p, qn('a:endParaRPr'))
        endp.set('lang', 'en-US')
        endp.set('sz', str(int(size * 100)))
    return shp


# ---------- 표 ----------
def table(slide, x, y, w, col_w, rows, row_h=0.36, header_h=0.38, size=TABLE_PT, align=None,
          first_col_bold=True, mono_cols=(), hl=(), fills=(PALE, PALE2)):
    """rows[0] 이 머리. hl={(행, 열)} 은 틀린 것 표시용 연한 빨강 채움(글자는 잉크 그대로).
    셀 글의 '\\n' 은 문단 나눔이다. 표 아래 '핵심' 설명 상자는 달지 않는다 (L-42)."""
    nr, nc = len(rows), len(rows[0])
    total = header_h + row_h * (nr - 1)
    gf = slide.shapes.add_table(nr, nc, I(x), I(y), I(w), I(total))
    tbl = gf.table
    tbl._tbl.tblPr.set('bandRow', '0')
    tbl._tbl.tblPr.set('firstRow', '1')
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = I(cw)
    for r in range(nr):
        tbl.rows[r].height = I(header_h if r == 0 else row_h)
        for c in range(nc):
            cell = tbl.cell(r, c)
            cell.margin_left, cell.margin_top, cell.margin_right, cell.margin_bottom = [I(m) for m in
                                                                                         (0.08, 0.03, 0.08, 0.03)]
            cell.vertical_anchor = MID_
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = rgb(NAVY)
            elif (r, c) in hl:
                cell.fill.fore_color.rgb = rgb(REDL)
            else:
                cell.fill.fore_color.rgb = rgb(fills[(r - 1) % len(fills)])
            val = rows[r][c]
            tf = cell.text_frame
            tf.word_wrap = True
            if r == 0:
                write_paras(tf, [val], size=size, color=WHITE, font=F_MED, align=CEN)
            else:
                al = align[c] if align else LEFT
                fnt = F_CODE if c in mono_cols else (F_REG if (c == 0 and first_col_bold) else F_LIGHT)
                write_paras(tf, val if isinstance(val, list) else [val], size=size, color=INK, font=fnt, align=al)
    return gf


# ---------- 덱 ----------
class Deck:
    """템플릿을 열고 예시 슬라이드를 지운 뒤 레이아웃으로 새 슬라이드를 붙인다."""
    LAYOUTS = ("제목 슬라이드", "목차", "제목만", "마무리")

    def __init__(self, template=None):
        self.template = find_template(template)
        self.prs = Presentation(self.template)
        lst = self.prs.slides._sldIdLst
        for sid in list(lst):
            self.prs.part.drop_rel(sid.rId)
            lst.remove(sid)
        self.layouts = {l.name: l for l in self.prs.slide_layouts}
        miss = [n for n in self.LAYOUTS if n not in self.layouts]
        if miss:
            raise ValueError(f"템플릿에 레이아웃 {miss} 가 없다. 있는 것: {list(self.layouts)}")
        self._id = 900
        self.count = {"그림": 0, "코드": 0, "표": 0}

    # 쪽 번호: python-pptx 는 레이아웃의 쪽 번호 자리를 슬라이드로 복사하지 않는다
    def _slide_number(self, s):
        n = len(self.prs.slides)
        for ph in s.slide_layout.placeholders:
            if ph.placeholder_format.type == PP_PLACEHOLDER.SLIDE_NUMBER:
                el = copy.deepcopy(ph._element)
                self._id += 1
                el.find('.//' + qn('p:cNvPr')).set('id', str(self._id))
                for t in el.iter(qn('a:t')):
                    t.text = str(n)
                s.shapes._spTree.append(el)
                return

    def _notes(self, s, notes):
        """발표자 메모: 줄마다 '- ' 로 시작하는 짧은 줄."""
        if not notes:
            return
        lines = notes.split('\n') if isinstance(notes, str) else list(notes)
        out = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            guard(ln, "발표자 메모")
            out.append(ln if ln.startswith("- ") else "- " + ln.lstrip("-").strip())
        s.notes_slide.notes_text_frame.text = "\n".join(out)

    @staticmethod
    def _drop(ph):
        ph._element.getparent().remove(ph._element)

    def title_slide(self, lines, subtitle=None, presenter=None, size=40, notes=None):
        """표지: 제목 1~2줄(size pt), 회색 부제, 발표자 이름."""
        s = self.prs.slides.add_slide(self.layouts["제목 슬라이드"])
        ph = {p.placeholder_format.idx: p for p in s.placeholders}
        t = ph[0]
        t.left, t.top, t.width, t.height = I(1.06), I(0.95), I(11.0), I(1.7)
        write_paras(t.text_frame, [[R(x, font=F_MED, size=size, color=NAVY)] for x in
                                   ([lines] if isinstance(lines, str) else lines)], size=size)
        p15 = ph.get(15)
        if p15 is not None:
            if subtitle:
                p15.left, p15.top, p15.width, p15.height = I(1.06), I(2.85), I(10.5), I(0.55)
                write_paras(p15.text_frame, [R(subtitle, size=24, color=GRAY)], size=24)
            else:
                self._drop(p15)
        if 17 in ph:
            self._drop(ph[17])
        if 16 in ph:
            if presenter:
                p16 = ph[16]
                # 높이만 넣으면 xfrm 이 (0,0) 에서 새로 생겨 이름이 사라진다. 물려받은 위치를 같이 적는다
                l, t, w = p16.left, p16.top, p16.width
                p16.left, p16.top, p16.width, p16.height = l, t, w, I(0.44)
                write_paras(p16.text_frame, [R(presenter, size=20)], size=20)
            else:
                self._drop(ph[16])
        self._notes(s, notes)
        return s

    def contents(self, items, notes=None):
        """목차: items = [(번호, 이름, 오른쪽 보조글 또는 None), ...]. 6개까지 권장."""
        s = self.prs.slides.add_slide(self.layouts["목차"])
        for p in list(s.placeholders):
            self._drop(p)
        self._slide_number(s)
        step = min(0.8, 4.4 / max(1, len(items)))
        for i, it in enumerate(items):
            num, name = it[0], it[1]
            right = it[2] if len(it) > 2 else None
            y = 2.0 + i * step
            text(s, 0.85, y, 0.85, 0.6, [R(num, font=F_MED, size=28, color=NAVY)], anchor=MID_,
                 margins=(0.07, 0, 0, 0))
            text(s, 1.8, y, 8.2, 0.6, [R(name, font=F_REG, size=22, color=NAVY)], anchor=MID_)
            if right:
                text(s, 10.0, y, 2.42, 0.6, [R(right, size=15, color=GRAY2)], anchor=MID_, align=RIGHT)
        self._notes(s, notes)
        return s

    def slide(self, title, sub=None, notes=None):
        """내용 슬라이드(제목만 레이아웃). 제목은 명사구 (L-46). sub 는 회색 한 줄."""
        guard(title, "제목")
        s = self.prs.slides.add_slide(self.layouts["제목만"])
        for ph in list(s.placeholders):
            if ph.placeholder_format.idx != 0:
                self._drop(ph)
        s.shapes.title.text_frame.text = title
        for p in s.shapes.title.text_frame.paragraphs:
            p._p.get_or_add_pPr().set('latinLnBrk', '0')
        self._slide_number(s)
        if sub:
            text(s, X0, 1.4, CW, 0.36, [R(sub, size=SUB_PT, color=GRAY)], anchor=MID_, margins=(0.1, 0, 0.06, 0))
        self._notes(s, notes)
        return s

    def head(self, slide, x, y, w, what, kind="그림"):
        """'그림 N: 무엇을 그렸나' 이름표 (L-31, L-38). kind: 그림, 코드, 표. 덱 안에서 이어 번호."""
        self.count[kind] += 1
        return text(slide, x, y, w, 0.36, [R(f"{kind} {self.count[kind]}: {what}", font=F_MED, size=HEAD_PT,
                                              color=INK)], anchor=MID_, margins=(0.02, 0, 0, 0))

    def code_block(self, slide, x, y, w, src, lang='python', what=None, h=None, size=CODE_PT):
        """'코드 N: 파일, 무엇' 이름표 + 코드 상자. 이름표는 상자 밖 위에 둔다(안에 두면 글자끼리 겹친다).
        h 를 안 주면 줄 수에 맞춘다. 돌려주는 값: 코드 상자 아래 끝 y(인치)."""
        if what:
            self.head(slide, x, y, w, what, kind="코드")
            y += 0.42
        h = h or code_h(src, size)
        code(slide, x, y, w, h, src, lang, size=size)
        return y + h

    def closing(self, presenter=None, notes=None):
        s = self.prs.slides.add_slide(self.layouts["마무리"])
        for idx, p in {p.placeholder_format.idx: p for p in s.placeholders}.items():
            if idx == 13 and presenter:
                write_paras(p.text_frame, [R(presenter, size=20, color=SKY)], size=20)
            else:
                self._drop(p)
        self._notes(s, notes)
        return s

    def save(self, path):
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.prs.save(path)
        print(f"저장 {path} (슬라이드 {len(self.prs.slides)}장)")   # 이 줄을 먼저 확인한다 (L-43)
        return path
