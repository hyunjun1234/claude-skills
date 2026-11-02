#!/usr/bin/env python3
"""diagram-deck/LESSONS.md 에서 템플릿 덱에도 걸리는 항목만 뽑아 보여 준다.

    python3 lessons.py          # 적용 항목 전문
    python3 lessons.py --list   # 번호와 제목만 (건너뛰는 항목 포함)

교훈은 diagram-deck/LESSONS.md 한 곳에만 쌓는다(훅이 그 파일을 지킨다). 여기서는 SVG 도해,
HTML/PDF 변환, 캡처 그림에만 해당하는 항목을 뺄 뿐이다. 새로 생긴 항목은 기본으로 포함된다.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS = os.environ.get("DIAGRAM_DECK_LESSONS") or os.path.normpath(
    os.path.join(HERE, "..", "..", "diagram-deck", "LESSONS.md"))

# 템플릿 덱(python-pptx 네이티브 도형)과 무관한 항목. 이유를 같이 적는다.
SKIP = {
    "L-04": "SVG 를 PNG 로 구울 때의 선택 박스",
    "L-05": "그림 파일 배치",
    "L-09": "HTML 을 PDF 로 바꿀 때 쪽수",
    "L-10": "PDF 글꼴 임베드",
    "L-11": "PDF 에서 그림 뽑기",
    "L-12": "PDF 에서 그림 뽑기",
    "L-13": "SVG 표현 기준 (L-32 로 대체됨)",
    "L-14": "HTML, PDF 변환 경로",
    "L-15": "svg2shapes 사용법",
    "L-16": "SVG 축척과 최소 pt",
    "L-18": "SVG 안 제목 중복",
    "L-23": "SVG 머리글 접두 중복",
    "L-25": "diagram_svg 간격 상수",
    "L-44": "SVG 이스케이프",
    "L-45": "SVG 규격 사전 점검",
    "L-48": "SVG 폭과 높이 일괄 점검",
    "L-49": "되돌려 비교 2%",
    "L-53": "diagram_svg name 인자",
    "L-54": "터미널 화면 캡처",
}


def blocks(text):
    """(번호, 제목, 본문) 목록. '### L-NN 제목' 부터 다음 '##' 머리까지."""
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"^### (L-\d+)\s+(.*)$", ln)
        if m:
            if cur:
                out.append(cur)
            cur = [m.group(1), m.group(2), [ln]]
        elif ln.startswith("## ") or ln.startswith("# "):
            if cur:
                out.append(cur)
            cur = None
        elif cur:
            cur[2].append(ln)
    if cur:
        out.append(cur)
    return out


def main():
    if not os.path.exists(LESSONS):
        sys.exit(f"❌ {LESSONS} 가 없다. diagram-deck 스킬이 같은 저장소에 있어야 한다")
    bs = blocks(open(LESSONS, encoding="utf-8").read())
    if "--list" in sys.argv:
        for num, title, _ in bs:
            why = SKIP.get(num)
            print(f"{'건너뜀 ' if why else '적용   '}{num} {title}" + (f"  ({why})" if why else ""))
        return
    use = [b for b in bs if b[0] not in SKIP]
    print(f"# diagram-deck/LESSONS.md 중 템플릿 덱에 걸리는 {len(use)}항목 (건너뜀 {len(bs) - len(use)})\n")
    for _, _, body in use:
        print("\n".join(body).rstrip() + "\n")


if __name__ == "__main__":
    main()
