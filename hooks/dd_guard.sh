#!/usr/bin/env bash
# Stop 훅 — 그림 수정 요청을 받았는데 교훈이 기록되지 않았으면 한 번 막는다.
#
# 원칙: **막는 데 실패할 수 있으면 막지 않는다.** 래치를 못 남기면 다음 턴에도 또 막게 되고,
# 그러면 사용자가 갇힌다. 자동화가 사람을 가두는 것보다 한 번 놓치는 편이 낫다.
set -uo pipefail
IN=$(cat 2>/dev/null || true)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
. "$DIR/common.sh"

SID=$(dd_session "$IN")
PEND="$DD_STATE/$SID.pending"
BLOCKED="$DD_STATE/$SID.blocked"

[ -f "$PEND" ] || exit 0                 # 이 요청은 대상이 아니다
[ -f "$BLOCKED" ] && exit 0              # 이 요청은 이미 한 번 막았다

REPO=$(dd_repo)
LESSONS="$REPO/skills/diagram-deck/LESSONS.md"
# 엉뚱한 저장소를 건드리지 않도록 이 저장소가 맞는지 확인한다
[ -f "$LESSONS" ] || { ( rm -f "$PEND" ) 2>/dev/null; exit 0; }
[ -f "$REPO/skills/diagram-deck/SKILL.md" ] || { ( rm -f "$PEND" ) 2>/dev/null; exit 0; }

# **요청을 받은 그 순간의 내용**과 지금을 비교한다.
# git 상태나 파일 시각으로 보면 (a) 원래부터 수정돼 있던 LESSONS.md 가 그냥 통과하고
# (b) git 이 없는 설치에서는 영영 통과하지 못한다.
WAS=$(cat "$PEND" 2>/dev/null || echo "")
NOW=$(dd_fingerprint)
CHANGED=0
if [ -z "$WAS" ] || [ "$WAS" = "err" ]; then
    CHANGED=1                                    # 지문을 못 남겼으면 강제하지 않는다
elif [ "$WAS" != "$NOW" ]; then
    CHANGED=1
fi

if [ "$CHANGED" = "1" ]; then
    ( rm -f "$PEND" ) 2>/dev/null || true
    dd_log "guard: session=$SID 교훈 기록 확인 — 통과"
    exit 0
fi

# 래치를 남길 수 있을 때만 막는다 (fail-open)
if ! ( : > "$BLOCKED" ) 2>/dev/null || [ ! -f "$BLOCKED" ]; then
    dd_log "guard: session=$SID 래치를 못 남겨 차단하지 않음 ($DD_STATE 쓰기 불가)"
    ( rm -f "$PEND" ) 2>/dev/null || true
    exit 0
fi
dd_log "guard: session=$SID 교훈 없음 — 1회 차단"
cat <<'JSON'
{"decision":"block","reason":"[diagram-deck 자동 업그레이드 훅] 이 수정 요청에 대해 LESSONS.md 에 남은 것이 없다.\n\n다음 중 하나를 하고 끝내라.\n(a) 재발할 수 있는 지적이면 `diagram-deck/LESSONS.md` 에 L-번호 항목을 추가한다 — 지적 / 원인 / 규칙(행동으로) / 검사. 기계로 잡히면 check_*.py 에 검사를 넣고 일부러 어긴 입력으로 걸리는지 확인한다.\n(b) 이 그림에만 해당하는 일회성 요청이면 LESSONS 에 넣지 말고, **왜 일회성인지 한 줄로 사용자에게 말한다.**\n(c) 애초에 그림 수정 요청이 아니었다면 그렇다고 한 줄 말하고 끝낸다.\n\n이 검사는 수정 요청 한 건당 한 번만 막는다."}
JSON
