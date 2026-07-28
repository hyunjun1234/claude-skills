#!/usr/bin/env bash
# UserPromptSubmit 훅 — 그림/발표자료에 대한 **수정 요청**을 감지해
# diagram-deck-upgrade 스킬로 보내고, 그 요청을 "교훈 기록 대상"으로 표시한다.
#
# 왜 훅인가: 모델이 기억해서 업그레이드 스킬을 부르는 구조는 자동이 아니다. 잊으면 끝이다.
# 하니스가 매 프롬프트마다 강제해야 자동이 된다.
#
# 감지 규칙 (오탐을 줄이려고 세 단계로 나눈다)
#   강신호  겹쳐·넘쳐·잘렸·고쳐… → 그 자체로 수정 요청이다
#   약신호  말고·위치·크게·색…   → 이것만으로는 모른다. **이 세션이 실제로 그림을 냈을 때만** 인정한다
#   생성    만들어줘·그려줘…      → 강신호가 없으면 수정이 아니라 생성이다. 발동하지 않는다
set -uo pipefail
IN=$(cat 2>/dev/null || true)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
. "$DIR/common.sh"

# 프롬프트만 본다. 못 찾으면 **아무것도 하지 않는다.**
# 훅 입력 JSON 전체로 매칭하면 cwd·transcript_path 에 든 'diagram' 같은 단어에
# 매 프롬프트가 걸린다(이 저장소에서 일할 때 항상 걸렸다).
P=$(printf '%s' "$IN" | jq -r '.prompt // .user_prompt // .message // .content // empty' 2>/dev/null)
if [ -z "$P" ]; then
    [ -f "$DD_STATE/.nokey" ] || { mkdir -p "$DD_STATE" 2>/dev/null && ( : > "$DD_STATE/.nokey" ) 2>/dev/null; \
        dd_log "detect: 훅 입력에서 프롬프트 키를 못 찾았다. 감지가 동작하지 않는다"; }
    exit 0
fi

# 라틴 낱말은 **왼쪽만** 경계로 잡는다. \b 를 오른쪽에도 걸면 한국어 조사가 붙은
# 'PPT에서' 가 안 걸린다(한글도 단어문자라 경계가 생기지 않는다).
# 왼쪽 경계만으로도 configure 안의 figure, deckard 안의 deck 은 걸러진다.
ART='그림|도해|도표|다이어그램|삽화|슬라이드|발표자료|장표|피피티|(^|[^A-Za-z])([Pp][Pp][Tt][Xx]?|[Dd]eck|[Dd]iagram|[Ff]igure|[Ss]lide)([^A-Za-z]|$)'
# 그림을 이미 낸 뒤에는 그림 **부품** 이름만 나와도 그 그림 이야기다
PART='화살표|상자|박스|라벨|범례|눈금|축|셀|글자|폰트|글꼴|제목|표지|여백|테두리|배경|줄바꿈|색상|색깔|색을|색으로|색 |개체|객체|도형|그룹|점선|실선|굵기'
STRONG='고쳐|고치|수정해|수정 해|겹쳐|겹치|겹친|겹칩|넘쳐|넘치|넘친|넘칩|잘렸|잘려|잘린|깨져|깨지|깨진|틀렸|틀린|어긋|흐릿|안 보여|안보여|이상해|이상하|안 맞|안맞|복구|다시 그려|다시그려|repair|broken|overlap|garbled|misaligned'
WEAK='위치|정렬|크게|작게|키워|줄여|색깔|색을|폰트|글꼴|바꿔|바꾸|빼줘|없애|옮겨'
# '말고·아니라' 는 너무 흔하다("PPT 말고 PDF로", "내일 아니라 모레").
# 그림 **부품**과 같이 나올 때만 수정 요청으로 본다.
WEAK_CONTRAST='말고|아니라|대신'
GEN='만들어|만들자|만들어줘|그려줘|그려 줘|작성해|작성 해|새로 만|초안|하나 뽑|제작|생성해'
# 스킬·코드 자체를 손보는 이야기는 그림 수정이 아니다 (이 저장소에서 일할 때 항상 걸렸다)
META='스킬|훅|후크|hook|스크립트|코드|리포|저장소|repo|\.sh|\.py|\.json|커밋|commit|정규식|regex|그림판|그림자'
# 물어보는 것은 고쳐 달라는 것이 아니다
ASK='어디|언제|누가|누구|얼마|몇 |뭐야|무엇|인가요|일까|있나|있어\?|맞아\?|되나'

SID=$(dd_session "$IN")
HAS_ART=0
[ -f "$DD_STATE/$SID.artifact" ] && HAS_ART=1

trig=0
kind=""
# 빈 줄로 나뉜 **문단** 단위로 본다.
#   줄 단위로 보면 "아래 그림 좀 봐줘 / 라벨이 상자를 넘쳐" 같은 진짜 요청을 놓치고,
#   글 전체로 보면 붙여넣은 로그의 경로와 딴 문장이 결합해 오탐이 난다.
BLOCKS=$(printf '%s\n' "$P" | awk 'BEGIN{RS="\n[ \t]*\n"} {gsub(/\n/," "); if (length($0)) printf "%s\036", $0}')
while IFS= read -r -d $'\036' b; do
    [ -z "$b" ] && continue
    printf '%s\n' "$b" | grep -qE "$META" && continue
    # 그림을 낸 뒤라면 부품 이름만 나와도, 강신호는 대상 이름이 없어도 그 그림 이야기다
    if printf '%s\n' "$b" | grep -qE "$ART"; then
        :
    elif [ "$HAS_ART" = "1" ] && printf '%s\n' "$b" | grep -qE "$PART|$STRONG"; then
        :
    else
        continue
    fi
    if printf '%s\n' "$b" | grep -qE "$STRONG"; then trig=1; kind="강신호"; break; fi
    printf '%s\n' "$b" | grep -qE "$GEN" && continue
    printf '%s\n' "$b" | grep -qE "$ASK" && continue
    if printf '%s\n' "$b" | grep -qE "$WEAK"; then trig=2; kind="약신호"; fi
    if printf '%s\n' "$b" | grep -qE "$WEAK_CONTRAST" && printf '%s\n' "$b" | grep -qE "$PART"; then
        trig=2; kind="약신호(대조)"
    fi
done <<EOF
$BLOCKS
EOF

[ "$trig" = "0" ] && exit 0
# 약신호는 이 세션이 실제로 그림·발표자료를 낸 뒤에만 인정한다 (dd_artifact.sh 가 표시한다)
[ "$trig" = "2" ] && [ "$HAS_ART" = "0" ] && exit 0
mkdir -p "$DD_STATE" 2>/dev/null || true

# 세션 표시 파일이 쌓이지 않게 오래된 것은 버린다
find "$DD_STATE" -maxdepth 1 \( -name '*.pending' -o -name '*.blocked' -o -name '*.artifact' \) 2>/dev/null \
    | while read -r f; do [ -n "$f" ] && [ -z "$(find "$f" -newermt '-7 days' 2>/dev/null)" ] && rm -f "$f"; done

( dd_fingerprint > "$DD_STATE/$SID.pending" ) 2>/dev/null || true
# 새 수정 요청이므로 차단 래치를 푼다 — 강제는 "수정 요청 한 건당 한 번"이다.
rm -f "$DD_STATE/$SID.blocked" 2>/dev/null || true
dd_log "detect: session=$SID $kind 로 그림 수정 요청 판단"

# 오탐이어도 해가 없도록 **조건부 지시**로 넣는다.
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"[diagram-deck 자동 업그레이드 훅]\n이 요청이 네가 만든 그림·도해·발표자료에 대한 **수정 요청**이라면, 다음을 반드시 지켜라. 그림 이야기가 아니라면 이 블록은 무시해라.\n\n1. 고치기 전에 Skill 도구로 `diagram-deck-upgrade` 를 호출한다.\n2. 고친 뒤 `diagram-deck` 의 `LESSONS.md` 에 재발 방지 규칙을 L-번호로 추가한다.\n   일회성 요청(이 그림만의 사정)이면 추가하지 않는다 — 대신 왜 일회성인지 사용자에게 한 줄로 말한다.\n3. 기계로 잡을 수 있는 규칙이면 `scripts/check_*.py` 에 검사를 넣고, **일부러 어긴 입력으로 걸리는지 확인**한다.\n4. 검증 루프(`scripts/verify.sh`)를 통과시킨 뒤에 낸다.\n\n교훈을 남기지 않고 턴을 끝내려 하면 Stop 훅이 한 번 막는다."}}
JSON
