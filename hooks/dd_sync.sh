#!/usr/bin/env bash
# Stop 훅(비동기) — 스킬 저장소에 생긴 변경을 자동으로 커밋하고 푸시한다.
# 푸시해야 다른 기계·다른 환경에 반영된다. 여기까지 해야 "자동 업그레이드"다.
#
# 안전장치
#   - 추적 대상 경로만 담는다. `git add -A` 는 쓰지 않는다(.claude/worktrees 같은 것이 딸려 들어간다).
#   - master(또는 main) 이고, 머지/리베이스 중이 아닐 때만 움직인다.
#   - 푸시가 거절되면 자동 리베이스를 시도하지 않는다. 로그만 남기고 손을 뗀다.
#   - 저장소에 `.no-autosync` 파일이 있거나 DD_AUTOSYNC=0 이면 아무것도 하지 않는다.
set -uo pipefail
IN=$(cat 2>/dev/null || true)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
. "$DIR/common.sh"

[ "${DD_AUTOSYNC:-1}" = "0" ] && exit 0
REPO=$(dd_repo)
[ -d "$REPO/.git" ] || exit 0
[ -f "$REPO/.no-autosync" ] && exit 0

BR=$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
case "$BR" in
    master|main) ;;
    *) dd_log "sync: 건너뜀 — 브랜치가 $BR"; exit 0 ;;
esac
GD=$(git -C "$REPO" rev-parse --git-dir 2>/dev/null || echo "")
if [ -n "$GD" ]; then
    case "$GD" in /*) ;; *) GD="$REPO/$GD" ;; esac
    for m in MERGE_HEAD rebase-merge rebase-apply CHERRY_PICK_HEAD; do
        [ -e "$GD/$m" ] && { dd_log "sync: 건너뜀 — $m 진행 중"; exit 0; }
    done
fi

PATHS=(skills README.md install.sh .claude-plugin hooks)
EXIST=()
for p in "${PATHS[@]}"; do [ -e "$REPO/$p" ] && EXIST+=("$p"); done
[ ${#EXIST[@]} -eq 0 ] && exit 0

CHANGED=$(git -C "$REPO" status --porcelain -- "${EXIST[@]}" 2>/dev/null)
[ -z "$CHANGED" ] && exit 0

FILES=$(printf '%s\n' "$CHANGED" | awk '{print $NF}' | sed 's#^skills/##' | head -6 | paste -sd', ' -)
N=$(printf '%s\n' "$CHANGED" | grep -c . || echo 0)
git -C "$REPO" add -- "${EXIST[@]}" >/dev/null 2>&1 || { dd_log "sync: add 실패"; exit 0; }
git -C "$REPO" diff --cached --quiet && exit 0

MSG="auto: 스킬 변경 동기화 ($N개) — $FILES"
if git -C "$REPO" commit -q -m "$MSG" \
    -m "diagram-deck 자동 업그레이드 훅이 만든 커밋이다. 훅: hooks/dd_sync.sh" >/dev/null 2>&1; then
    dd_log "sync: 커밋 — $MSG"
else
    dd_log "sync: 커밋 실패"
    exit 0
fi

if git -C "$REPO" push -q 2>/dev/null; then
    dd_log "sync: 푸시 완료"
else
    dd_log "sync: 푸시 실패(원격이 앞서 있거나 오프라인). 수동으로 pull --rebase 후 push 하라"
fi
exit 0
