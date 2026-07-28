#!/usr/bin/env bash
# UserPromptSubmit 훅 — 그림/발표자료에 대한 **수정 요청**을 감지해
# diagram-deck-upgrade 스킬로 보내고, 이 세션을 "교훈 기록 대상"으로 표시한다.
#
# 왜 훅인가: 모델이 기억해서 업그레이드 스킬을 부르는 구조는 자동이 아니다. 잊으면 끝이다.
# 하니스가 매 프롬프트마다 강제해야 자동이 된다.
set -uo pipefail
IN=$(cat 2>/dev/null || true)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
. "$DIR/common.sh"

# 프롬프트 추출 — 키 이름이 버전마다 다를 수 있으므로 실패하면 원문 전체로 훑는다
P=$(printf '%s' "$IN" | jq -r '.prompt // .user_prompt // .message // .content // empty' 2>/dev/null)
[ -z "$P" ] && P="$IN"

# 1) 그림/발표자료 이야기인가
ART='그림|도해|도표|다이어그램|삽화|슬라이드|발표자료|장표|피피티|[Pp][Pp][Tt]|pptx|PPTX|deck|diagram|figure'
# 2) 고쳐 달라는 것인가 (만들어 달라가 아니라)
FIX='고쳐|고치|수정|바꿔|바꾸|이상해|이상하|겹쳐|겹치|넘쳐|넘치|잘렸|잘려|깨져|깨지|틀렸|틀린|안 맞|안맞|어긋|다시 그|다시그|키워|줄여|작게|크게|흐릿|안 보|안보이|위치|정렬|빼줘|말고|아니라|왜 이|복구|repair|broken|fix|wrong|overlap|too small|too big'

echo "$P" | grep -qE "$ART" || exit 0
echo "$P" | grep -qE "$FIX" || exit 0

SID=$(dd_session "$IN")
mkdir -p "$DD_STATE" 2>/dev/null || true
# 세션 표시 파일이 쌓이지 않게 오래된 것은 버린다
find "$DD_STATE" -maxdepth 1 -name '*.pending' -o -name '*.blocked' 2>/dev/null \
    | while read -r f; do [ -n "$f" ] && [ -z "$(find "$f" -newermt '-7 days' 2>/dev/null)" ] && rm -f "$f"; done
: > "$DD_STATE/$SID.pending" 2>/dev/null || true
rm -f "$DD_STATE/$SID.blocked" 2>/dev/null || true
dd_log "detect: session=$SID 그림 수정 요청으로 판단"

# 오탐이어도 해가 없도록 **조건부 지시**로 넣는다.
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"[diagram-deck 자동 업그레이드 훅]\n이 요청이 네가 만든 그림·도해·발표자료에 대한 **수정 요청**이라면, 다음을 반드시 지켜라. 그림 이야기가 아니라면 이 블록은 무시해라.\n\n1. 고치기 전에 Skill 도구로 `diagram-deck-upgrade` 를 호출한다.\n2. 고친 뒤 `diagram-deck` 의 `LESSONS.md` 에 재발 방지 규칙을 L-번호로 추가한다.\n   일회성 요청(이 그림만의 사정)이면 추가하지 않는다 — 대신 왜 일회성인지 사용자에게 한 줄로 말한다.\n3. 기계로 잡을 수 있는 규칙이면 `scripts/check_*.py` 에 검사를 넣고, **일부러 어긴 입력으로 걸리는지 확인**한다.\n4. 검증 루프(`scripts/verify.sh`)를 통과시킨 뒤에 낸다.\n\n교훈을 남기지 않고 턴을 끝내려 하면 Stop 훅이 막는다."}}
JSON
