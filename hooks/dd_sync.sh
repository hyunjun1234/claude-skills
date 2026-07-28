#!/usr/bin/env bash
# Stop 훅(비동기) — 스킬 저장소에 생긴 변경을 자동으로 커밋하고 푸시한다.
# 푸시해야 다른 기계·다른 환경에 반영된다. 여기까지 해야 "자동 업그레이드"다.
#
# 원칙: **자동화는 사람이 되돌리기 어려운 일을 하지 않는다.**
#   - 삭제가 섞여 있으면 손대지 않는다. 실수로 지운 스킬이 원격까지 퍼지면 되돌리기 어렵다.
#   - 충돌·머지·리베이스·리버트 중이면 손대지 않는다.
#   - 이미 스테이징된 남의 파일은 건드리지 않는다(`commit --only`).
#   - 푸시가 거절되면 자동 리베이스를 시도하지 않는다. 로그만 남기고 손을 뗀다.
#   - 커다란 파일·비밀스러운 이름의 파일은 담지 않는다.
#   - `.no-autosync` 또는 DD_AUTOSYNC=0 이면 아무것도 하지 않는다.
set -uo pipefail
IN=$(cat 2>/dev/null || true)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
. "$DIR/common.sh"

[ "${DD_AUTOSYNC:-1}" = "0" ] && exit 0
REPO=$(dd_repo)
git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || exit 0    # 워크트리는 .git 이 파일이다
# 엉뚱한 저장소(예: git 으로 관리하는 dotfiles)에 커밋하지 않도록 신원을 확인한다
[ -f "$REPO/skills/diagram-deck/SKILL.md" ] || { dd_log "sync: 건너뜀 — 스킬 저장소가 아니다: $REPO"; exit 0; }
[ -f "$REPO/.no-autosync" ] && exit 0

BR=$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
case "$BR" in
    master|main) ;;
    *) dd_log "sync: 건너뜀 — 브랜치가 $BR"; exit 0 ;;
esac
GD=$(git -C "$REPO" rev-parse --absolute-git-dir 2>/dev/null || echo "")
if [ -n "$GD" ]; then
    for m in MERGE_HEAD REVERT_HEAD CHERRY_PICK_HEAD BISECT_LOG rebase-merge rebase-apply; do
        [ -e "$GD/$m" ] && { dd_log "sync: 건너뜀 — $m 진행 중"; exit 0; }
    done
fi

# 저장소 전체 상태를 받아 허용 접두어로 거른다.
# git 에 경로를 pathspec 으로 넘기면 (a) 없는 경로에서 에러가 나고
# (b) **삭제된 파일은 목록에서 빠져** 삭제를 못 알아챈다.
CHANGED=$(git -C "$REPO" status --porcelain 2>/dev/null | awk '
    { p = substr($0, 4)
      gsub(/^"|"$/, "", p)
      if (p ~ /^(skills\/|hooks\/|\.claude-plugin\/)/ || p == "README.md" || p == "install.sh") print }')
[ -z "$CHANGED" ] && exit 0

# 충돌 표시가 있으면 손대지 않는다
if printf '%s\n' "$CHANGED" | grep -qE '^(DD|AU|UD|UA|DU|AA|UU) '; then
    dd_log "sync: 건너뜀 — 충돌 상태 파일이 있다"; exit 0
fi
# 삭제·이름변경은 사람이 확인해야 한다
if printf '%s\n' "$CHANGED" | grep -qE '^( D|D |AD|RD|R |RM)'; then
    dd_log "sync: 건너뜀 — 삭제/이름변경이 섞여 있다. 직접 커밋하라"; exit 0
fi

# 담기 전에 위험한 파일을 거르고, **실제로 변한 파일만** 목록으로 만든다.
# 정적 경로 목록을 그대로 넘기면 git 이 모르는 경로(빈 디렉터리 등)에서
# `commit --only` 가 통째로 실패한다 — 그러면 자동 동기화가 조용히 죽는다.
CFILES=()
while IFS= read -r line; do
    [ -z "$line" ] && continue
    f=${line:3}
    f=${f%\"}; f=${f#\"}
    [ -z "$f" ] && continue
    full="$REPO/$f"
    case "$f" in
        *id_rsa*|*.pem|*.key|*.p12|*.env|*credential*|*secret*|*token*)
            dd_log "sync: 건너뜀 — 비밀스러운 이름의 파일: $f"; exit 0 ;;
    esac
    if [ -f "$full" ]; then
        sz=$(stat -c %s "$full" 2>/dev/null || stat -f %z "$full" 2>/dev/null || echo 0)
        if [ "${sz:-0}" -gt 5242880 ]; then
            dd_log "sync: 건너뜀 — 5MB 넘는 파일: $f ($sz)"; exit 0
        fi
    fi
    CFILES+=("$f")
done <<EOF
$CHANGED
EOF
[ ${#CFILES[@]} -eq 0 ] && exit 0

FILES=$(printf '%s\n' "${CFILES[@]}" | sed 's#^skills/##' | head -6 | paste -sd', ' -)
N=${#CFILES[@]}

git -C "$REPO" add -- "${CFILES[@]}" >/dev/null 2>&1 || { dd_log "sync: add 실패"; exit 0; }
MSG="auto: 스킬 변경 동기화 ($N개) — $FILES"
# --only 로 **이 파일들만** 커밋한다. 사용자가 다른 곳에 스테이징해 둔 것이 딸려 가지 않는다.
if git -C "$REPO" commit -q --only -m "$MSG" \
    -m "diagram-deck 자동 업그레이드 훅이 만든 커밋이다. 훅: hooks/dd_sync.sh" \
    -- "${CFILES[@]}" >/dev/null 2>&1; then
    dd_log "sync: 커밋 — $MSG"
else
    git -C "$REPO" reset -q -- "${CFILES[@]}" >/dev/null 2>&1 || true   # 인덱스를 원래대로
    dd_log "sync: 커밋 실패 — 스테이징 되돌림"
    exit 0
fi

# 응답 없는 원격에 매달리지 않는다(훅 타임아웃에 잘리면 상태가 반쯤 남는다)
if timeout 25 git -C "$REPO" push -q 2>/dev/null; then
    dd_log "sync: 푸시 완료"
else
    AHEAD=$(git -C "$REPO" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "?")
    dd_log "sync: 푸시 실패 — 로컬에 $AHEAD 커밋이 쌓였다. git pull --rebase && git push 하라"
fi
exit 0
