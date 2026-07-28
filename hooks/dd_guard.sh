#!/usr/bin/env bash
# Stop 훅 — 그림 수정 요청을 받은 세션인데 교훈이 기록되지 않았으면 한 번 막는다.
#
# 한 번만 막는다. 두 번째부터는 통과시킨다 — 판단이 틀렸을 때 사용자를 가두면 안 된다.
# (하니스의 CLAUDE_CODE_STOP_HOOK_BLOCK_CAP 과 별개로 자체 제한을 둔다.)
set -uo pipefail
IN=$(cat 2>/dev/null || true)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
. "$DIR/common.sh"

SID=$(dd_session "$IN")
PEND="$DD_STATE/$SID.pending"
BLOCKED="$DD_STATE/$SID.blocked"

[ -f "$PEND" ] || exit 0                 # 이 세션은 대상이 아니다
[ -f "$BLOCKED" ] && exit 0              # 이미 한 번 막았다

REPO=$(dd_repo)
LESSONS=$(dd_lessons)
[ -f "$LESSONS" ] || { rm -f "$PEND"; exit 0; }   # 스킬 저장소가 없으면 할 말이 없다

# 교훈이 기록됐는가 — 작업 트리가 변했거나, 표시 시각 이후 커밋됐거나
CHANGED=0
if [ -n "$(git -C "$REPO" status --porcelain -- 'skills/*/LESSONS.md' 2>/dev/null)" ]; then
    CHANGED=1
else
    MARK=$(stat -c %Y "$PEND" 2>/dev/null || stat -f %m "$PEND" 2>/dev/null || echo 0)
    LAST=$(git -C "$REPO" log -1 --format=%ct -- 'skills/*/LESSONS.md' 2>/dev/null || echo 0)
    [ "${LAST:-0}" -ge "${MARK:-0}" ] 2>/dev/null && CHANGED=1
fi

if [ "$CHANGED" = "1" ]; then
    rm -f "$PEND"
    dd_log "guard: session=$SID 교훈 기록 확인 — 통과"
    exit 0
fi

: > "$BLOCKED" 2>/dev/null || true
dd_log "guard: session=$SID 교훈 없음 — 1회 차단"
cat <<'JSON'
{"decision":"block","reason":"[diagram-deck 자동 업그레이드 훅] 이 세션은 그림·발표자료 수정 요청으로 시작했는데 LESSONS.md 에 남은 것이 없다.\n\n다음 중 하나를 하고 끝내라.\n(a) 재발할 수 있는 지적이면 `diagram-deck/LESSONS.md` 에 L-번호 항목을 추가한다 — 지적 / 원인 / 규칙(행동으로) / 검사. 기계로 잡히면 check_*.py 에 검사를 넣고 일부러 어긴 입력으로 걸리는지 확인한다.\n(b) 이 그림에만 해당하는 일회성 요청이면 LESSONS 에 넣지 말고, **왜 일회성인지 한 줄로 사용자에게 말한다.**\n(c) 애초에 그림 수정 요청이 아니었다면 그렇다고 한 줄 말하고 끝낸다.\n\n이 검사는 세션당 한 번만 막는다."}
JSON
