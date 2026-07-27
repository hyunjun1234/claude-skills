# 도해(SVG) 작성 규약

TCP 논문 분석 PPT 의 글 위주 슬라이드를 **그림 슬라이드**로 바꾼다.
너는 SVG 마크업을 직접 쓴다. 그 SVG 는 WeasyPrint 로 렌더돼 여백이 잘린 PNG 가 되고,
PPT 에 **그림 객체**로 들어간다.

참고 작품(사용자가 좋다고 한 것): `/home/jun/RNGD-proj/Model_Benchmark/rngd-npu/vISA/_ppt_src/TCP-계층도.html`
— 반드시 Read 해서 표현 방식을 익혀라.

---

## 1. 무조건 지킬 것 (어기면 렌더가 깨진다)

1. **루트는 `<svg viewBox="0 0 W H" xmlns="http://www.w3.org/2000/svg">` 로 시작한다.**
   `viewBox` 는 필수다. `width`/`height` 속성은 쓰지 마라(렌더러가 넣는다).
   **W 는 880~980, H 는 260~520** 사이로 잡아라. 단위는 pt 다.
2. **`<style>` 태그·CSS 클래스·`class=` 를 쓰지 마라.** 전부 표현 속성(presentation attribute)으로 써라.
   (`fill="#..."`, `stroke="#..."`, `font-size="13"` 처럼)
3. **`<foreignObject>`, `<marker>`, `<use>`, `<filter>`, 외부 이미지, 애니메이션 금지.**
   화살촉은 `<polygon>` 으로 직접 그려라.
4. **글꼴은 루트 `<g>` 에 `font-family="Noto Sans CJK KR"` 한 번만 걸어라.**
   고정폭이 필요하면 그 요소에만 `font-family="Noto Sans Mono CJK KR"`.
5. 텍스트는 `<text x= y= font-size= fill=>`. 가운데 정렬은 `text-anchor="middle"`,
   오른쪽 정렬은 `text-anchor="end"`. **`<text>` 안에서 줄바꿈은 안 된다** — 줄마다 `<text>` 를 따로 써라.
6. 배경을 흰색 사각형으로 깔지 마라. 배경이 있으면 여백 트림이 안 돼 선택 박스가 커진다.

## 2. 글자가 상자를 넘지 않게 하는 법 (가장 흔한 사고)

글자 폭 어림값: **한글 1자 ≈ font-size × 1.0**, **영문·숫자 1자 ≈ font-size × 0.5**, 공백 ≈ 0.5.

```
"Contraction Engine" (영문 18자) @ font-size 13  →  18 × 6.5 ≈ 117pt
"축약 엔진" (한글 4자 + 공백 1) @ font-size 13   →  4 × 13 + 6.5 ≈ 59pt
```

상자 폭보다 **최소 12pt 여유**를 남겨라. 안 되면 글자를 줄이거나 두 줄로 나눠라.
세로도 마찬가지다. 줄 간격은 font-size × 1.35 로 잡아라.

## 3. 팔레트 (계층도와 같은 색을 써라)

| 쓰임 | 색 |
|---|---|
| 본문 글자 | `#16202c` |
| 흐린 글자·설명 | `#5b6b7b` |
| 파랑 (주 강조·테두리) | `#0b5fc0` / 진한 `#083f80` |
| 파랑 배경 (연→진) | `#f4f8fd` `#e3eefb` `#dcebf9` `#cbe0f7` `#b8d4f3` |
| 주황 (대비·경고) | `#b45409`, 배경 `#fdebd3` |
| 초록 (좋음·결과) | `#1a7f37`, 배경 `#e2f4e8` |
| 빨강 (나쁨·병목) | `#b4222a`, 배경 `#fde8e8` |
| 회색 (부차) | `#5b6b7b`, 배경 `#eef2f7` |
| 선 | `#d6dee7` |
| 어두운 코드 상자 | 배경 `#0f1b2a`, 글자 `#e6edf3` |

## 4. 잘 되는 표현 방식

- **포함 관계**: 사각형을 겹쳐 중첩. 안쪽으로 갈수록 진한 파랑.
- **흐름**: 상자 + `<polygon>` 화살촉. 왼→오른쪽 또는 위→아래.
- **분할/배치**: 격자(작은 `<rect>` 반복). 색으로 그룹을 구분.
- **비교**: 좌우 2단. 왼쪽 파랑(좋음)/오른쪽 주황(나쁨) 또는 그 반대.
- **타임라인**: 가로 막대 여러 줄 + 눈금.
- **수치 비교**: 가로 막대 길이로. 값을 막대 옆에 글자로 반드시 적어라.
- **루프 중첩**: 사각형을 안으로 겹쳐 그리고 각 단에 축 이름.
- **표기법 해설**: 어두운 상자 안에 고정폭 글씨로 수식을 쓰고, 아래에 부분별 설명.

## 5. 작동 예 (그대로 흉내내도 좋다)

```svg
<svg viewBox="0 0 900 300" xmlns="http://www.w3.org/2000/svg">
  <g font-family="Noto Sans CJK KR">
    <rect x="20" y="30" width="240" height="120" rx="8" fill="#e3eefb" stroke="#0b5fc0" stroke-width="2"/>
    <text x="140" y="62" font-size="15" font-weight="700" fill="#083f80" text-anchor="middle">입력 텐서</text>
    <text x="140" y="86" font-size="12" fill="#16202c" text-anchor="middle">b × l × e</text>
    <text x="140" y="108" font-size="11" fill="#5b6b7b" text-anchor="middle">HBM 에 있다</text>

    <line x1="266" y1="90" x2="316" y2="90" stroke="#0b5fc0" stroke-width="2.4"/>
    <polygon points="314,83 332,90 314,97" fill="#0b5fc0"/>
    <text x="299" y="76" font-size="10.5" fill="#5b6b7b" text-anchor="middle">fetch</text>

    <rect x="340" y="30" width="240" height="120" rx="8" fill="#e2f4e8" stroke="#1a7f37" stroke-width="2"/>
    <text x="460" y="62" font-size="15" font-weight="700" fill="#1a7f37" text-anchor="middle">slice 안</text>
  </g>
</svg>
```

## 6. 그림과 함께 낼 것 — 요약된 설명

원래 슬라이드의 불릿을 **그림을 이해하는 데 꼭 필요한 것만** 3~6개로 줄여 낸다.
- 그림에 이미 그려진 내용을 글로 또 쓰지 마라. **그림이 말하지 못하는 것**만 남겨라.
  (근거가 되는 논문 문장, 수치의 출처, 주의사항, 함의)
- 원문의 수치·용어를 왜곡하지 마라. 논문에 없는 값을 만들지 마라.
- 문체는 평서형 '다'체.

## 7. 자체 점검

- [ ] `viewBox` 가 있고 W 880~980, H 260~520 인가
- [ ] `<style>`, `class=`, `<marker>`, `<foreignObject>` 가 없는가
- [ ] 모든 `<text>` 가 자기 상자 안에 들어가는가 (§2 어림셈)
- [ ] 흰 배경 사각형을 깔지 않았는가
- [ ] 태그가 전부 닫혔는가 (`<rect ... />` 처럼 자기닫힘 포함)
- [ ] 그림만 보고도 그 슬라이드의 요점이 전달되는가
