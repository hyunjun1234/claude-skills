#!/usr/bin/env bash
# diagram-deck 자동 업그레이드 훅 공용 함수.
# 훅은 사용자의 모든 프롬프트·모든 세션에서 돈다. 관계없는 경우 빨리 조용히 끝내는 것이 제1 원칙이다.

# HOME 이 없는 환경에서 set -u 로 죽지 않게 한다
: "${HOME:=$(cd ~ 2>/dev/null && pwd || echo /tmp)}"
export HOME
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

dd_fingerprint() {
    # LESSONS.md 의 내용 지문. git 이 없어도, 원래부터 더러웠어도 정확히 판정하려면
    # "요청을 받은 그 순간의 내용"과 비교해야 한다. cksum 은 어디에나 있다.
    local f
    f=$(dd_lessons)
    [ -f "$f" ] || { printf 'none'; return; }
    cksum "$f" 2>/dev/null | awk '{print $1 "-" $2}' || printf 'err'
}

dd_log() {
    # 리다이렉션 실패는 `cmd >f 2>/dev/null` 로 못 막는다 — >f 가 먼저 평가된다.
    # 서브셸로 감싸야 조용해진다. 훅이 사용자 터미널에 잡음을 내면 안 된다.
    ( mkdir -p "$DD_STATE" && printf '%s %s\n' "$(date -Is)" "$*" >> "$DD_STATE/hooks.log" ) 2>/dev/null || true
}
