#!/usr/bin/env bash
# diagram-deck 실행 환경 준비. 이미 있으면 아무것도 하지 않는다.
# 시스템 파이썬을 건드리지 않으려고 전용 venv 를 쓴다(PEP 668 대응).
set -u
VENV="${DIAGRAM_DECK_VENV:-$HOME/.cache/diagram-deck/venv}"
PY="$VENV/bin/python"
PKGS="python-pptx weasyprint pymupdf pillow"

need=0
if [ ! -x "$PY" ]; then
  need=1
else
  "$PY" - <<'EOF' >/dev/null 2>&1 || need=1
import pptx, weasyprint, fitz, PIL
EOF
fi

if [ "$need" = 1 ]; then
  echo "[diagram-deck] 환경을 준비한다: $VENV"
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV" 2>&1 | tail -2
  "$VENV/bin/pip" install --quiet --upgrade pip 2>&1 | tail -1
  "$VENV/bin/pip" install --quiet $PKGS 2>&1 | tail -3
fi

"$PY" - <<'EOF'
import pptx, weasyprint, fitz, PIL
print(f"python-pptx {pptx.__version__} · weasyprint {weasyprint.__version__} · "
      f"pymupdf {fitz.__doc__.split()[1]} · pillow {PIL.__version__}")
EOF
rc=$?
if [ $rc -ne 0 ]; then
  echo "[diagram-deck] ❌ 준비 실패. weasyprint 는 libpango/libcairo 가 필요하다."
  echo "  Debian/Ubuntu: sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2"
  echo "  macOS:        brew install pango cairo gdk-pixbuf libffi"
  exit 1
fi

# 한글 글꼴 확인 — 없으면 PDF·PNG 의 한글이 깨진다
if command -v fc-list >/dev/null 2>&1; then
  if ! fc-list :lang=ko family 2>/dev/null | grep -qi "noto sans cjk"; then
    echo "[diagram-deck] ⚠ Noto Sans CJK KR 이 없다. 한글이 깨질 수 있다."
    echo "  Debian/Ubuntu: sudo apt install fonts-noto-cjk"
  fi
fi

echo "PY=$PY"
