#!/usr/bin/env bash
# diagram-deck 자동 업그레이드 훅 공용 함수.
# 훅은 사용자의 모든 프롬프트·모든 세션에서 돈다. 관계없는 경우 빨리 조용히 끝내는 것이 제1 원칙이다.

DD_STATE="${DD_STATE:-$HOME/.cache/diagram-deck/state}"

dd_repo() {
    # 스킬 저장소 위치. 심볼릭 링크를 따라가 실제 저장소를 찾는다.
    if [ -n "${DD_SKILLS_REPO:-}" ]; then
        printf '%s' "$DD_SKILLS_REPO"
        return
    fi
    local link="$HOME/.claude/skills/diagram-deck" real
    if [ -e "$link" ]; then
        real=$(cd "$link" 2>/dev/null && pwd -P) || real=""
        if [ -n "$real" ]; then
            real=$(git -C "$real" rev-parse --show-toplevel 2>/dev/null) || real=""
        fi
    fi
    printf '%s' "${real:-$HOME/claude-skills}"
}

dd_session() {
    # 훅 입력 JSON 에서 세션 id. 못 찾으면 부모 프로세스로 대체한다.
    local in="$1" sid
    sid=$(printf '%s' "$in" | jq -r '.session_id // .sessionId // empty' 2>/dev/null)
    [ -z "$sid" ] && sid="pid$PPID"
    # 파일명으로 쓰므로 안전한 문자만 남긴다
    printf '%s' "$sid" | tr -c 'A-Za-z0-9_-' '_'
}

dd_lessons() {
    printf '%s/skills/diagram-deck/LESSONS.md' "$(dd_repo)"
}

dd_log() {
    mkdir -p "$DD_STATE" 2>/dev/null || true
    printf '%s %s\n' "$(date -Is)" "$*" >> "$DD_STATE/hooks.log" 2>/dev/null || true
}
