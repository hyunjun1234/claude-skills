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

chmod +x "$REPO"/hooks/*.sh 2>/dev/null || true

# ── 자동 업그레이드 훅 등록 (개인 설치일 때만) ─────────────────────────────
# 스킬을 "부르면 도는" 것에서 "안 부르면 하니스가 부르는" 것으로 바꾼다.
if [ "$MODE" = "personal" ] && [ "${NO_HOOKS:-0}" != "1" ]; then
  S="$HOME/.claude/settings.json"
  if ! command -v jq >/dev/null 2>&1; then
    echo "⚠ jq 가 없어 훅 등록을 건너뛴다. jq 설치 후 다시 돌려라."
  else
    [ -f "$S" ] || echo '{}' > "$S"
    if ! jq -e . "$S" >/dev/null 2>&1; then
      echo "⚠ $S 가 깨진 JSON 이다. 훅 등록을 건너뛴다 — 먼저 고쳐라."
    else
      cp "$S" "$S.bak.$(date +%Y%m%d%H%M%S)"
      # 스크립트가 없으면 조용히 통과하도록 감싼다(pull 전이어도 안전)
      # 저장소의 **실제 경로**를 박는다. $HOME/claude-skills 로 하드코딩하면
      # 다른 경로에 clone 한 사람에게는 훅이 조용한 no-op 이 된다.
      w() { printf 'f="%s/hooks/%s"; if [ -x "$f" ]; then exec "$f"; else cat >/dev/null; fi' "$REPO" "$1"; }
      tmp="$(mktemp)"
      jq --arg detect "$(w dd_detect.sh)" \
         --arg guard  "$(w dd_guard.sh)" \
         --arg sync   "$(w dd_sync.sh)" \
         --arg art    "$(w dd_artifact.sh)" '
        # 우리가 넣은 것만 걷어내고 다시 넣는다 — 여러 번 돌려도 중복되지 않고,
        # 사용자가 따로 넣어 둔 훅은 건드리지 않는다.
        def strip($ev; $tags):
          (.hooks[$ev] // [])
          | map(.hooks |= map(select([ .command // "" | contains($tags[])] | any | not)))
          | map(select((.hooks | length) > 0));
        .hooks //= {}
        | .hooks.UserPromptSubmit = (strip("UserPromptSubmit"; ["dd_detect.sh"])
            + [{hooks: [{type: "command", command: $detect, timeout: 10}]}])
        | .hooks.PostToolUse = (strip("PostToolUse"; ["dd_artifact.sh"])
            + [{matcher: "Write|Edit|Bash|NotebookEdit",
                hooks: [{type: "command", command: $art, timeout: 10, async: true}]}])
        | .hooks.Stop = (strip("Stop"; ["dd_guard.sh", "dd_sync.sh"])
            + [{hooks: [
                {type: "command", command: $guard, timeout: 20},
                {type: "command", command: $sync,  timeout: 60, async: true}
              ]}])
      ' "$S" > "$tmp" && mv "$tmp" "$S" \
        && echo "훅 등록: UserPromptSubmit(감지) · PostToolUse(산출물 표시) · Stop(교훈 강제 + 자동 커밋·푸시)"
    fi
  fi
fi

echo
bash "$REPO/skills/diagram-deck/scripts/setup_env.sh" || true

echo
echo "설치 완료 ($MODE)."
if [ "$MODE" = "personal" ]; then
  echo "  Claude Code 를 새로 켜면 /diagram-deck, /diagram-deck-upgrade 가 잡힌다."
  echo "  (스킬 디렉터리가 없던 상태에서 새로 만든 경우에만 재시작이 필요하다)"
  echo "  훅을 끄려면: touch $REPO/.no-autosync (자동 푸시만) 또는 /hooks 에서 해제"
else
  echo "  $TARGET_REPO 에서 git add .claude/skills && commit 하면 클라우드 세션에서도 쓰인다."
  echo "  (훅은 개인 설치에서만 등록된다. NO_HOOKS=1 로 끌 수 있다)"
fi
