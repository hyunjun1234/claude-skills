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

변환은 **두 갈래뿐**이다. `HTML → PPTX` 와 `PDF → PPTX`.
HTML 을 PDF 로 바꿔 놓고 다시 PPTX 로 가는 식으로 **단계를 늘리지 마라.**

| 요청 | 경로 |
|---|---|
| "이 내용을 그림으로 그려서 PPT" | §3 도해 작성 → §5 덱 조립 (**네이티브 도형**) |
| "HTML 을 PPT 로" | **§4 `html2pptx.py`** — 한 번에. 중간 PDF 파일을 만들지 않는다 |
| "PDF 를 PPT 로" | **§4 `pdf2pptx.py`** — 한 번에 |
| "HTML 로 PDF 만" | §4 아래의 PDF 전용 항목 |
| "기존 PPT 의 글 슬라이드를 그림으로" | §3 + §5 (해당 슬라이드만 교체) |
| "PowerPoint 가 복구하라고 한다" | §6 검증 루프부터 |

**§4(변환)와 §5(조립)는 다른 일이다.** §4 는 이미 있는 문서를 **쪽 통째로** 슬라이드에 옮기는 것이고,
§5 는 슬라이드를 처음부터 짜는 것이다.

**사용자가 그림을 고칠 수 있어야 하면 §5 다.** §4 는 쪽 전체가 그림 한 장이 되어 아무것도 못 고친다.

## 3. 도해 작성 — SVG 를 직접 쓴다

`reference/SVG_RULES.md` 를 그대로 따른다. 요점만:

- 루트는 `<svg viewBox="0 0 W H" xmlns="http://www.w3.org/2000/svg">`. **viewBox 필수**, W 880~980 / H 260~520.
- `<style>` · `class=` · `<marker>` · `<foreignObject>` · 외부 이미지 **금지**. 전부 표현 속성으로.
- 글꼴은 루트 `<g font-family="Noto Sans CJK KR">` 하나로. 고정폭은 `Noto Sans Mono CJK KR`.
- **흰 배경 사각형을 깔지 마라.** 깔면 여백 트림이 안 돼 PPT 선택 박스가 그림보다 커진다.
- 글자 폭 어림: 한글 1자 ≈ 글자크기, 영문·숫자 1자 ≈ 글자크기 × 0.5. 상자보다 12pt 이상 여유.

### 3-1. 슬라이드에 넣기 — **PNG 로 굽지 마라**

내가 그린 SVG 는 **네이티브 PowerPoint 도형**으로 넣는다. 상자·화살표·글자가 각각 도형이라
사용자가 글자를 고치고 색을 바꾸고 상자를 옮길 수 있다. PNG 로 구우면 통짜라 아무것도 못 고친다(L-15).

```python
from svg2shapes import add_svg_shapes
g, w, h, n, min_pt = add_svg_shapes(slide.shapes, svg, left, top, width=W, height=H)
#   g       그룹 도형 (경계 = 자식 경계, 선택 박스가 딱 맞는다)
#   n       만들어진 도형 개수
#   min_pt  그림 안 가장 작은 글자가 슬라이드에서 몇 pt 인가  ← 6.5 밑이면 배치를 바꿔라(L-16)
```

덱을 짤 때는 `deck.Deck.diagram_svg()` 가 이걸 감싸 놓았다. §5 참고.

`svg2png.render()`(여백 잘라낸 PNG)는 **검수용 대지**를 만들거나 그림을 파일로 따로 내야 할 때만 쓴다.

미리보기·자체 시험:

```bash
$PY ${CLAUDE_SKILL_DIR}/scripts/svg2shapes.py     # 데모 도해를 pptx 로
$PY ${CLAUDE_SKILL_DIR}/scripts/check_shapes.py   # 되돌려 그려 원본과 비교
```

## 4. 변환 — HTML → PPTX, PDF → PPTX

```bash
$PY <skill>/scripts/html2pptx.py in.html out.pptx [--dpi 200] [--no-notes] [--keep-pdf x.pdf]
$PY <skill>/scripts/pdf2pptx.py  in.pdf  out.pptx [--dpi 200] [--no-notes]
```

- **HTML 은 PDF 파일을 거치지 않는다.** WeasyPrint 가 낸 바이트를 메모리에서 바로 받아 쓴다.
  PDF 도 같이 갖고 싶을 때만 `--keep-pdf` 를 준다.
- 쪽마다 고해상도 PNG 로 렌더해 슬라이드에 전면 배치한다.
- **슬라이드 크기를 원본 쪽 크기와 같게** 잡으므로 여백도 잘림도 왜곡도 없다.
  (A4 가로면 11.69 × 8.27 in 슬라이드가 된다. 16:9 로 강제하면 좌우에 흰 여백이 생긴다.)
- 슬라이드에는 그림 도형 하나만 둔다. 숨은 텍스트 상자를 쓰지 마라 —
  손상 위험과 선택 박스 문제를 동시에 만든다.
- 쪽 텍스트는 발표자 노트에 넣어 검색이 되게 하고, 제목은 `p:cSld/@name` 으로 붙인다.
- 이 방식은 **쪽 전체가 하나의 그림**이 된다. 슬라이드 위 글자는 선택되지 않는다.
  글자를 살리고 그림만 객체로 넣고 싶으면 §5 로 가라.

**HTML → PDF 만 필요할 때**

```bash
$PY -c "from weasyprint import HTML; HTML('doc.html').write_pdf('out.pdf')"
```

- `@page { size: 297mm 210mm; margin: 12mm 14mm; }` 로 쪽 크기를 정한다.
- 쪽마다 `.page { page-break-after: always; height: <쪽높이 - 여백>; }` 로 높이를 **고정**한다.
- **변환 후 쪽수를 반드시 확인한다.** 넘치면 조용히 다음 쪽으로 흘러 쪽수가 늘어난다
  (9쪽 설계가 13쪽으로 나온 적이 있다). `verify.sh out.pdf <기대쪽수>` 로 대조한다.

## 5. PPTX 조립

`scripts/deck.py` 를 쓴다. 16:9, 자동 글자 크기, 한글 East-Asian 폰트, 넘침 검출이 들어 있다.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
import deck
d = deck.Deck("제목", "부제\n둘째 줄", "꼬리말")
d.section("1", "부 제목", "설명")          # 부 표지
d.part = "1부: 부 제목"                    # 이후 슬라이드 머리말
d.bullets("제목", [{"t": "내용"}, {"t": "하위", "lv": 1}], callout="핵심 한 줄")
s, n, min_pt, _ = d.diagram_svg("제목", svg_markup,          # ← 내가 그린 도해: 네이티브 도형
                                [{"t": "그림이 말하지 못하는 것만"}], callout="핵심 한 줄")
d.diagram("제목", "논문그림.png", [{"t": "…"}])              # ← 원본이 래스터일 때만
d.table("제목", ["열1", "열2"], [["가", "나"]])
d.code("제목", ["fn main() {", "}"], caption="예제")
d.twocol("제목", [{"t": "왼쪽"}], [{"t": "오른쪽"}], heads=["A", "B"])
d.big("한 문장 강조", "부연")
d.save("out.pptx")
print(deck.OVERFLOW)      # 비어 있어야 정상
```

- `d.diagram_svg()` 는 도해를 **슬라이드 폭 가득** 위에 놓고 설명을 아래 띠에 2단으로 깐다.
  옆에 나란히 놓지 않는다 — 그러면 그림이 반폭으로 줄어 안쪽 라벨이 5pt 가 된다(L-16).
  반환값의 `min_pt` 가 **6.5 미만이면 설명을 다음 장으로 빼고** 그림에 슬라이드를 통째로 준다.
- `d.diagram()`(PNG)은 테두리 없는 그림 객체 하나로 넣는다. 원본이 래스터일 때만 쓴다.
- **설명이 안 들어가면 다음 장으로 나눠라.** 억지로 우겨넣지 마라.

## 6. ★ 검증 루프 — 통과할 때까지 돈다

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

**네이티브 도해를 넣었으면 되돌려 비교한다.** 이게 도해 전용 검증 루프다.

```bash
$PY ${CLAUDE_SKILL_DIR}/scripts/check_shapes.py       # 자체 시험
```

파이썬에서 전수 검사:

```python
from check_shapes import compare, check_group_tight
diff, src_img, back_img = compare(원본_svg, 그룹도형)   # 0.02(2%) 넘으면 실패
assert not check_group_tight(그룹도형)                  # 그룹 경계 == 자식 경계
```

`compare()` 는 **pptx 에 실제로 들어간 도형 XML** 을 다시 SVG 로 그려 원본과 픽셀 비교한다.
요소가 빠지거나 좌표·색이 틀리면 차이로 드러난다.
한계: PowerPoint 자체 렌더러가 아니라 이 검사기의 해석이다. 좌표·색·누락은 잡지만
"PowerPoint 에서 글자가 상자를 넘는가"는 못 잡는다 — 그건 `check_layout.py` 가 본다.

도해를 여러 장 만들었으면 **눈으로도 본다**:

```bash
$PY ${CLAUDE_SKILL_DIR}/scripts/contact_sheet.py index.json sheet.png 9
```

대지를 Read 로 직접 보고, 글자가 상자를 넘거나 겹치거나 빈약한 그림은 다시 그린다.
**검사기가 통과해도 눈으로 이상하면 다시 그린다.**

## 7. 낼 때

- 만든 파일과 **재생성 소스**(HTML/SVG·스크립트·내용 JSON)를 함께 남긴다.
- 검증 결과를 사용자에게 그대로 보고한다. "통과했다"가 아니라 **무엇을 검사해서 몇 건이었는지** 적는다.

## 8. 사용자가 그림을 고쳐 달라고 하면

`diagram-deck-upgrade` 스킬을 쓴다. 고치기만 하고 끝내면 같은 지적을 또 받는다.
**고친 뒤 그 교훈을 `LESSONS.md` 에 남기고 커밋·푸시까지 하는 것**이 그 스킬이 하는 일이다.
