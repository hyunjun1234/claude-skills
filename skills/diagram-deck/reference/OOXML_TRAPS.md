# PowerPoint 손상 함정

python-pptx 로 XML 을 직접 손대면 **LibreOffice 는 열리는데 PowerPoint 는 손상으로 판정**하는
파일이 나온다. 실제로 겪은 것만 적는다. `scripts/check_ooxml.py` 가 전부 잡는다.

## 1. `a:rPr` 자식 요소 순서

`CT_TextCharacterProperties` 의 자식 순서는 스키마가 강제한다:

```
ln → (fill) → (effect) → highlight → (uLn) → (uFill) → latin → ea → cs → sym → hlink… → rtl → extLst
```

한글 글꼴을 넣으려고 `a:ea`/`a:cs` 를 추가할 때 **latin → cs → ea** 가 되기 쉽다. 그러면 손상이다.

```python
# 틀림 — 두 번 다 latin 뒤에 넣어서 latin, cs, ea 가 된다
for tag in ("a:ea", "a:cs"):
    el = etree.SubElement(rPr, qn(tag)); latin.addnext(el)

# 맞음 — 역순으로 넣어야 latin, ea, cs 가 된다
latin.addnext(cs)
latin.addnext(ea)
```

## 2. 좌표는 정수

`ST_Coordinate` 는 `xsd:long` 이다. `x="2670596.6"` 같은 실수는 위반이다.
계산 결과를 그대로 쓰지 말고 반드시 `int(round(v))` 를 거친다(`deck.E()`).

## 3. 줄바꿈은 `<a:br/>`

`run.text = "a\nb"` 는 `<a:t>a\nb</a:t>` 를 만든다. DrawingML 에서 `<a:t>` 안의 개행은
줄바꿈이 아니라 공백처럼 처리된다 — **파일은 열리는데 한 줄로 이어 그려진다.**
`_Paragraph.add_line_break()` 로 `<a:br/>` 를 넣어야 한다.

## 4. 그 밖에 확인하는 것

- 슬라이드 안 `p:cNvPr/@id` 중복
- `a:ln` 안 `headEnd` → `tailEnd` 순서
- `p:spPr` 의 `xfrm → geom → fill → ln → effectLst` 순서
- `[Content_Types].xml` 에 쓰는 이미지 확장자가 선언돼 있는지

## 5. 왜 이런 게 조용히 통과하나

python-pptx 는 스키마 검증을 하지 않는다. LibreOffice 는 관대하다.
PowerPoint(특히 macOS)만 엄격하다. 그래서 **내기 전에 `check_ooxml.py` 를 돌리는 것 말고는
잡을 방법이 없다.**
