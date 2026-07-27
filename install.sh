#!/usr/bin/env bash
# claude-skills 설치 — ~/.claude/skills/<이름> 을 이 저장소로 심볼릭 링크한다.
#   bash install.sh                      개인 스킬로 설치 (모든 프로젝트에서 쓰임)
#   bash install.sh --project /path/repo 그 저장소의 .claude/skills/ 에 설치 (클라우드 세션용)
set -eu
REPO="$(cd "$(dirname "$0")" && pwd)"
MODE="personal"; TARGET_REPO=""

while [ $# -gt 0 ]; do
  case "$1" in
    --project) MODE="project"; TARGET_REPO="${2:?--project 뒤에 저장소 경로가 필요하다}"; shift 2 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "모르는 인자: $1"; exit 2 ;;
  esac
done

if [ "$MODE" = "personal" ]; then
  DEST="$HOME/.claude/skills"
else
  DEST="$TARGET_REPO/.claude/skills"
fi
mkdir -p "$DEST"

for d in "$REPO"/skills/*/; do
  name="$(basename "$d")"
  link="$DEST/$name"
  if [ -L "$link" ]; then
    rm "$link"
  elif [ -e "$link" ]; then
    echo "⚠ 이미 있음(링크 아님): $link — 건너뛴다"
    continue
  fi
  if [ "$MODE" = "personal" ]; then
    ln -s "$d" "$link"
    echo "링크: $link -> $d"
  else
    # 프로젝트에 커밋할 것이므로 실제 복사한다(다른 사람 기계엔 이 저장소가 없다)
    cp -r "$d" "$link"
    echo "복사: $link"
  fi
done

echo
bash "$REPO/skills/diagram-deck/scripts/setup_env.sh" || true

echo
echo "설치 완료 ($MODE)."
if [ "$MODE" = "personal" ]; then
  echo "  Claude Code 를 새로 켜면 /diagram-deck, /diagram-deck-upgrade 가 잡힌다."
  echo "  (스킬 디렉터리가 없던 상태에서 새로 만든 경우에만 재시작이 필요하다)"
else
  echo "  $TARGET_REPO 에서 git add .claude/skills && commit 하면 클라우드 세션에서도 쓰인다."
fi
