#!/usr/bin/env bash
# diagram-deck 검증 루프. pptx 또는 pdf 를 받아 전 항목을 검사한다.
# 하나라도 실패하면 0 이 아닌 값으로 끝난다 — 통과할 때까지 고쳐서 다시 돌려라.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
VENV="${DIAGRAM_DECK_VENV:-$HOME/.cache/diagram-deck/venv}"
PY="$VENV/bin/python"
F="${1:?사용법: verify.sh <파일.pptx|파일.pdf> [기대쪽수]}"
WANT="${2:-}"
FAIL=0

[ -x "$PY" ] || { echo "❌ 환경이 없다. setup_env.sh 를 먼저 돌려라."; exit 2; }
[ -f "$F" ] || { echo "❌ 파일 없음: $F"; exit 2; }

hr(){ printf '%s\n' "------------------------------------------------------------"; }
case "$F" in
  *.pptx)
    hr; echo "1) OOXML 스키마 (요소 순서 · 중복 id)"
    "$PY" "$D/check_ooxml.py" "$F" || FAIL=$((FAIL+1))

    hr; echo "2) 좌표가 정수 EMU 인가"
    "$PY" - "$F" <<'EOF' || FAIL=$((FAIL+1))
import re, sys, zipfile
z = zipfile.ZipFile(sys.argv[1]); bad = tot = 0
for n in z.namelist():
    if not (n.startswith("ppt/slides/slide") or n.startswith("ppt/notesSlides/")):
        continue
    x = z.read(n).decode()
    for a in ("x", "y", "cx", "cy"):
        for v in re.findall(rf'\b{a}="([-\d.eE+]+)"', x):
            tot += 1
            if "." in v or "e" in v.lower():
                bad += 1
print(f"   좌표 {tot}개 중 소수 {bad}개")
sys.exit(1 if bad else 0)
EOF

    hr; echo "3) 줄바꿈이 <a:br/> 인가 (a:t 안 날 개행 금지)"
    "$PY" - "$F" <<'EOF' || FAIL=$((FAIL+1))
import re, sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
raw = sum(len(re.findall(r"<a:t>[^<]*\n[^<]*</a:t>", z.read(n).decode()))
          for n in z.namelist() if n.startswith("ppt/slides/slide"))
print(f"   a:t 안 날 개행 {raw}개")
sys.exit(1 if raw else 0)
EOF

    hr; echo "4) 레이아웃 (경계 이탈 · 넘침 · 겹침)"
    "$PY" "$D/check_layout.py" "$F" || FAIL=$((FAIL+1))

    hr; echo "5) 그림 종횡비 왜곡"
    "$PY" - "$F" <<'EOF' || FAIL=$((FAIL+1))
import sys
from pptx import Presentation
p = Presentation(sys.argv[1]); bad = n = 0
for s in p.slides:
    for sh in s.shapes:
        if sh.__class__.__name__ != "Picture":
            continue
        n += 1
        iw, ih = sh.image.size
        if ih and sh.height:
            err = abs((iw / ih) - (sh.width / sh.height)) / (iw / ih)
            if err >= 0.02:
                bad += 1
print(f"   그림 {n}개 중 왜곡 {bad}개")
sys.exit(1 if bad else 0)
EOF

    hr; echo "6) 네이티브 도해 그룹 (경계가 그림에 맞는가)"
    "$PY" - "$F" "$D" <<'EOF' || FAIL=$((FAIL+1))
import sys
sys.path.insert(0, sys.argv[2])
from pptx import Presentation
from check_shapes import check_group_tight
p = Presentation(sys.argv[1]); n = bad = kids = 0
for i, s in enumerate(p.slides, 1):
    for sh in s.shapes:
        if sh.shape_type != 6:          # GROUP
            continue
        n += 1
        kids += len(list(sh.shapes))
        m = check_group_tight(sh)
        if m:
            bad += 1
            print(f"   ❌ p{i} {sh.name}: {m}")
if n == 0:
    print("   네이티브 도해 없음 (건너뜀)")
else:
    print(f"   그룹 {n}개 · 자식 도형 {kids}개 · 경계 어긋남 {bad}개")
sys.exit(1 if bad else 0)
EOF
    ;;
  *.pdf)
    hr; echo "1) 쪽수 · 글꼴 임베드 · 한글 검색"
    "$PY" - "$F" "$WANT" <<'EOF' || FAIL=$((FAIL+1))
import sys, fitz
d = fitz.open(sys.argv[1]); want = sys.argv[2] if len(sys.argv) > 2 else ""
print(f"   쪽수 {d.page_count}, {d[0].rect.width:.0f}x{d[0].rect.height:.0f}pt")
bad = 0
if want and want.isdigit() and int(want) != d.page_count:
    print(f"   ❌ 기대 쪽수 {want} 와 다르다 — 내용이 넘쳐 흘렀을 수 있다")
    bad = 1
ext = [f for p in d for f in p.get_fonts(full=True) if not f[1]]
if ext:
    print(f"   ❌ 임베드 안 된 글꼴 {len(ext)}종")
    bad = 1
else:
    print("   글꼴 전부 임베드")
sys.exit(bad)
EOF
    ;;
  *) echo "❌ pptx 또는 pdf 만 검사한다"; exit 2 ;;
esac

hr
if [ "$FAIL" = 0 ]; then
  echo "✅ 전부 통과 — 내도 좋다"
else
  echo "❌ 실패 $FAIL 항목 — 고쳐서 다시 돌려라. 통과 전에는 사용자에게 내지 마라."
fi
exit $FAIL
