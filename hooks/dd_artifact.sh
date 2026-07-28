#!/usr/bin/env bash
# PostToolUse 훅 — 이 세션이 그림·발표자료를 실제로 **만들었는지** 표시한다.
#
# 왜 필요한가: "이거 말고", "좀 크게", "위치가…" 같은 약한 말은 그 자체로는
# 수정 요청인지 알 수 없다. 방금 내가 그림을 냈다면 수정 요청이고, 아니면 아니다.
# 그 판단 근거를 남기는 것이 이 훅의 전부다.
set -uo pipefail
IN=$(cat 2>/dev/null || true)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
. "$DIR/common.sh"

# 도구가 건드린 경로/명령을 한 줄로 모은다
T=$(printf '%s' "$IN" | jq -r '
      [ .tool_input.file_path? // empty,
        .tool_input.command?   // empty,
        .tool_input.notebook_path? // empty,
        .tool_response.filePath?   // empty ] | join(" ")' 2>/dev/null)
[ -z "$T" ] && exit 0

# 발표자료·도해 산출물인가
echo "$T" | grep -qiE '\.(pptx|svg)([^a-z]|$)|diagram|도해|발표자료|_ppt_src|svg2shapes|deck\.py|contact_sheet' || exit 0

SID=$(dd_session "$IN")
mkdir -p "$DD_STATE" 2>/dev/null || true
( : > "$DD_STATE/$SID.artifact" ) 2>/dev/null || true
exit 0
