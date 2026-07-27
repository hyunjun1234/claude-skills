---
name: diagram-deck
description: |
  HTML/SVG 로 도해(diagram)를 그려 PPTX·PDF 로 만들거나, 기존 HTML·PDF 를 PPTX 로 변환할 때 쓴다.
  글자만 많은 슬라이드를 그림으로 바꿔 달라거나, 발표자료·설명자료에 도표·구조도·흐름도·타임라인·
  비교도를 넣어 달라거나, 만든 PPT 가 PowerPoint 에서 "복구" 경고를 낼 때도 이 스킬을 쓴다.
  Use for: html to pptx, pdf to pptx, svg diagram, 도해, 그림 슬라이드, 발표자료 그림, deck.
---

# diagram-deck — HTML/SVG 도해로 PPTX·PDF 만들기

**목표는 "글을 그림으로 바꾸는 것"이다.** 상자 몇 개 늘어놓는 게 아니라, 보는 순간 구조가 잡히는
도해를 그린다. 그리고 **PowerPoint 가 손상 경고를 내지 않는 파일**을 낸다.

## 0. 시작 전에 반드시 읽을 것

1. `${CLAUDE_SKILL_DIR}/LESSONS.md` — **사용자 피드백으로 누적된 규칙.** 가장 먼저 읽어라.
   여기 적힌 것은 과거에 실제로 지적받은 것이므로 예외 없이 지킨다.
2. `${CLAUDE_SKILL_DIR}/reference/SVG_RULES.md` — SVG 작성 규약(팔레트·글자폭 계산·금지 요소).
3. `${CLAUDE_SKILL_DIR}/reference/OOXML_TRAPS.md` — PowerPoint 손상 함정.
4. `${CLAUDE_SKILL_DIR}/examples/reference-deck.html` — 잘 그린 예시. 표현 방식을 여기서 익힌다.

## 1. 환경 준비

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup_env.sh
```

`~/.cache/diagram-deck/venv` 에 python-pptx · weasyprint · pymupdf · pillow 를 깔고 경로를 출력한다.
이후 모든 파이썬 명령은 그 venv 의 python 으로 돌린다. 이미 있으면 그냥 넘어간다.

## 2. 무엇을 만드는지 먼저 정한다

| 요청 | 경로 |
|---|---|
| "이 내용을 그림으로 그려서 PPT" | §3 도해 작성 → §5 덱 조립 |
| "HTML 로 그려서 PDF" | §3 도해 작성 → §4 HTML→PDF |
| "이 PDF 를 PPTX 로" | §6 PDF→PPTX |
| "기존 PPT 의 글 슬라이드를 그림으로" | §3 + §5 (해당 슬라이드만 교체) |
| "PowerPoint 가 복구하라고 한다" | §7 검증 루프부터 |

## 3. 도해 작성 — SVG 를 직접 쓴다

`reference/SVG_RULES.md` 를 그대로 따른다. 요점만:

- 루트는 `<svg viewBox="0 0 W H" xmlns="http://www.w3.org/2000/svg">`. **viewBox 필수**, W 880~980 / H 260~520.
- `<style>` · `class=` · `<marker>` · `<foreignObject>` · 외부 이미지 **금지**. 전부 표현 속성으로.
- 글꼴은 루트 `<g font-family="Noto Sans CJK KR">` 하나로. 고정폭은 `Noto Sans Mono CJK KR`.
- **흰 배경 사각형을 깔지 마라.** 깔면 여백 트림이 안 돼 PPT 선택 박스가 그림보다 커진다.
- 글자 폭 어림: 한글 1자 ≈ 글자크기, 영문·숫자 1자 ≈ 글자크기 × 0.5. 상자보다 12pt 이상 여유.

렌더:

```bash
$PY ${CLAUDE_SKILL_DIR}/scripts/svg2png.py            # 자체 시험
# 실제로는 파이썬에서 import 해서 쓴다
#   from svg2png import render
#   w, h, in_w, in_h = render(svg_markup, "out.png")   # 흰 여백을 잘라낸 PNG
```

`render()` 가 **여백을 잘라낸다.** 이것이 "선택 박스가 쓸데없이 크지 않게"의 핵심이다.
잘린 크기 = PPT 안 그림 도형 크기 = 선택 박스 크기가 된다.

## 4. HTML → PDF

문서형(여러 쪽)이면 HTML 한 파일에 `.page` 단위로 쓰고 WeasyPrint 로 변환한다.

```bash
$PY -c "from weasyprint import HTML; HTML('doc.html').write_pdf('out.pdf')"
```

- `@page { size: 297mm 210mm; margin: 12mm 14mm; }` 처럼 쪽 크기를 정한다.
- 쪽마다 `.page { page-break-after: always; height: <쪽높이 - 여백>; }` 로 높이를 **고정**한다.
- **변환 후 쪽수를 반드시 확인한다.** 내용이 넘치면 조용히 다음 쪽으로 흘러 쪽수가 늘어난다.
  설계한 쪽수와 다르면 그림 영역 높이나 설명량을 줄여 다시 만든다.

## 5. PPTX 조립

`scripts/deck.py` 를 쓴다. 16:9, 자동 글자 크기, 한글 East-Asian 폰트, 넘침 검출이 들어 있다.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
import deck
d = deck.Deck("제목", "부제\n둘째 줄", "꼬리말")
d.section("1", "부 제목", "설명")          # 부 표지
d.part = "1부 · 부 제목"                    # 이후 슬라이드 머리말
d.bullets("제목", [{"t": "내용"}, {"t": "하위", "lv": 1}], callout="핵심 한 줄")
d.diagram("제목", "그림.png", [{"t": "그림이 말하지 못하는 것만"}])   # ← 도해 객체
d.table("제목", ["열1", "열2"], [["가", "나"]])
d.code("제목", ["fn main() {", "}"], caption="예제")
d.twocol("제목", [{"t": "왼쪽"}], [{"t": "오른쪽"}], heads=["A", "B"])
d.big("한 문장 강조", "부연")
d.save("out.pptx")
print(deck.OVERFLOW)      # 비어 있어야 정상
```

- `d.diagram()` 은 그림을 **테두리 없는 독립 객체**로 넣는다. 사용자가 직접 옮기고 크기를 바꿀 수 있다.
- 그림이 가로로 길면(비율 ≥ 2.55) 위에 그림·아래에 설명, 아니면 왼쪽 그림·오른쪽 설명으로 자동 배치된다.
- **설명이 안 들어가면 다음 장으로 나눠라.** 억지로 우겨넣지 마라.

## 6. PDF → PPTX

```bash
$PY ${CLAUDE_SKILL_DIR}/scripts/pdf2pptx.py in.pdf out.pptx 200
```

- 쪽마다 고해상도 PNG 로 렌더해 슬라이드에 전면 배치한다.
- **슬라이드 크기를 원본 쪽 크기와 같게** 잡으므로 여백도 잘림도 왜곡도 없다.
- 슬라이드에는 그림 도형 하나만 둔다(숨은 텍스트 상자 금지 — 손상 위험과 선택 박스 문제를 동시에 만든다).
- 쪽 텍스트는 발표자 노트에 넣어 검색이 되게 한다.

## 7. ★ 검증 루프 — 통과할 때까지 돈다

**만들었으면 반드시 돌린다. 통과 못 하면 고쳐서 다시 돌린다. 통과 전에는 사용자에게 내지 않는다.**

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/verify.sh out.pptx
```

검사 항목과 대응:

| 검사 | 실패하면 |
|---|---|
| OOXML 요소 순서 (`a:rPr` 는 latin→ea→cs) | `reference/OOXML_TRAPS.md` §1. `deck.style()` 을 쓰면 자동으로 맞는다 |
| 좌표가 정수 EMU 인가 | `deck.E()` 를 통과시킨다. 실수 좌표는 PowerPoint 가 손상으로 본다 |
| 슬라이드 밖으로 나간 도형 | 좌표 계산을 고친다 |
| 글자 세로 넘침 | 슬라이드를 나누거나 글을 줄인다 |
| 라벨 가로 넘침 | 상자를 넓히거나 글자를 줄인다 |
| 글자 있는 도형끼리 겹침 | 배치를 고친다 |
| `deck.OVERFLOW` 가 비었는가 | 자동 분할이 안 먹은 경우다. 내용을 나눈다 |

도해를 여러 장 만들었으면 **눈으로도 본다**:

```bash
$PY ${CLAUDE_SKILL_DIR}/scripts/contact_sheet.py index.json sheet.png 9
```

대지를 Read 로 직접 보고, 글자가 상자를 넘거나 겹치거나 빈약한 그림은 다시 그린다.
**검사기가 통과해도 눈으로 이상하면 다시 그린다.**

## 8. 낼 때

- 만든 파일과 **재생성 소스**(HTML/SVG·스크립트·내용 JSON)를 함께 남긴다.
- 검증 결과를 사용자에게 그대로 보고한다. "통과했다"가 아니라 **무엇을 검사해서 몇 건이었는지** 적는다.

## 9. 사용자가 그림을 고쳐 달라고 하면

`diagram-deck-upgrade` 스킬을 쓴다. 고치기만 하고 끝내면 같은 지적을 또 받는다.
**고친 뒤 그 교훈을 `LESSONS.md` 에 남기고 커밋·푸시까지 하는 것**이 그 스킬이 하는 일이다.
