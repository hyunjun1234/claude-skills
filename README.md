# claude-skills

Claude Code 스킬 모음. 한 곳에서 관리하고 여러 기계에 심볼릭 링크로 붙인다.

| 스킬 | 하는 일 |
|---|---|
| [`diagram-deck`](skills/diagram-deck/) | SVG 로 도해를 그려 **PowerPoint 네이티브 도형**으로 슬라이드에 넣는다(상자·화살표·글자를 그대로 편집 가능). 문서 변환은 **`HTML → PPTX`** 와 **`PDF → PPTX`** 두 갈래(중간 PDF 파일 없음). 검증 루프 포함 |
| [`diagram-deck-upgrade`](skills/diagram-deck-upgrade/) | 그림 수정 요청을 받으면 고치고, **그 교훈을 `diagram-deck` 에 영구히 반영**한다 |

## 도해는 그림 파일이 아니라 도형으로 들어간다

```python
from svg2shapes import add_svg_shapes
g, w, h, n, min_pt = add_svg_shapes(slide.shapes, svg, left, top, width=W, height=H)
```

`<rect>` → 사각형, `<circle>` → 타원, `<line>` → 직선, `<polygon>` → 자유형, `<text>` → 글상자.
전체는 그룹 하나로 묶인다(옮길 땐 그룹째, 고칠 땐 안으로 들어가 개별 편집).
그룹 경계 = 자식 경계라서 선택 박스가 그림에 딱 맞는다.

검증은 **pptx 안 도형을 다시 SVG 로 되돌려 원본과 픽셀 비교**한다 — `scripts/check_shapes.py`.

## 설치

```bash
git clone https://github.com/<user>/claude-skills.git ~/claude-skills
bash ~/claude-skills/install.sh
```

`install.sh` 는 `~/.claude/skills/<이름>` 을 이 저장소로 **심볼릭 링크**한다.
Claude Code 는 심볼릭 링크를 따라가므로, 앞으로 `git pull` 만 하면 모든 프로젝트에 반영된다.

## 갱신

```bash
cd ~/claude-skills && git pull      # 다른 기계에서 올린 개선을 받아온다
```

## 어디까지 따라오는가 — 중요

| 환경 | `~/.claude/skills/` 를 읽나 | 어떻게 쓰나 |
|---|---|---|
| 이 기계의 Claude Code (모든 프로젝트·모든 세션) | **예** | 설치만 하면 끝. 파일 변경은 세션 재시작 없이 반영된다 |
| 다른 기계의 Claude Code | 그 기계의 것만 | `git clone` + `install.sh` 필요. 계정 로그인만으로는 안 따라온다 |
| Cowork · claude.ai 클라우드 세션 · routines | **아니오** | 아래 참고 |

**클로드 계정 로그인만으로는 이 스킬이 따라오지 않는다.** 공식 문서 기준으로
Cowork/클라우드 세션은 내 기계의 `~/.claude/skills/` 를 읽지 않고,
**claude.ai 계정에 등록된 스킬**을 세션 시작 시 동기화해 쓴다.
클라우드 세션에서 쓰려면 둘 중 하나가 필요하다.

1. **프로젝트에 심어 두기** — 그 저장소의 `.claude/skills/` 에 커밋하면 클라우드 세션이 읽는다.
   ```bash
   bash ~/claude-skills/install.sh --project /path/to/repo
   ```
2. **플러그인으로 선언하기** — 저장소의 `.claude/settings.json` 에 이 저장소를 플러그인으로 적으면
   세션 시작 때 설치된다. 이 저장소에는 `.claude-plugin/plugin.json` 이 들어 있다.

## 변환은 두 갈래뿐이다

```bash
PY=~/.cache/diagram-deck/venv/bin/python
$PY ~/.claude/skills/diagram-deck/scripts/html2pptx.py in.html out.pptx
$PY ~/.claude/skills/diagram-deck/scripts/pdf2pptx.py  in.pdf  out.pptx
```

`HTML → PPTX` 는 중간 PDF 파일을 만들지 않는다. PDF 도 함께 원하면 `--keep-pdf x.pdf`.

## 스킬이 스스로 자라는 방식

1. 그림을 만들 때 `diagram-deck` 이 `LESSONS.md` 를 먼저 읽는다.
2. 사용자가 수정을 요청하면 `diagram-deck-upgrade` 가 고친 뒤 **교훈을 `LESSONS.md` 에 추가**하고,
   기계로 잡을 수 있으면 `scripts/check_*.py` 에 검사를 넣는다.
3. **커밋·푸시까지 한다.** 푸시해야 다른 기계에 반영된다.

같은 기계의 다른 세션은 파일을 공유하므로 즉시 반영된다.
다른 기계는 `git pull` 시점에 반영된다.
