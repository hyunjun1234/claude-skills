#!/usr/bin/env python3
"""슬라이드 유형 견본이자 이 스킬의 자체 시험. 함수 하나가 슬라이드 유형 하나다.
새 덱을 짤 때 맞는 함수를 복사해 내용만 바꾼다. 좌표는 인치, 본문은 X0..X1, Y0..Y1 안.

    python3 example_deck.py /abs/out/example.pptx [템플릿 경로]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sota import *  # noqa: F401,F403


def cover(d):
    """표지. 제목은 1~2줄, 부제 한 줄, 발표자."""
    d.title_slide(["로컬 문서 질의응답 앱", "구조와 코드 정리"], "sota-deck 예시 덱", "발표자 이름", notes=[
        "내 PC 안에서 문서를 찾아 답하는 앱을 예로 슬라이드 유형을 모았다",
        "순서: 구성, 흐름, 코드, 비교, 처리 방식, 설치, 추가 공부"])


def toc(d):
    """목차. 오른쪽 회색 열은 장 범위나 쪽 번호처럼 찾는 데 쓰는 보조 정보만."""
    d.contents([("01", "시스템 구성과 처리 흐름", "3 ~ 4"), ("02", "코드 분석", "5"),
                ("03", "검색 방식과 처리 방식", "6 ~ 7"), ("04", "설치 순서", "8"),
                ("05", "추가로 공부하면 좋은 개념", "9")],
               notes=["장마다 개념을 먼저 보이고 코드는 그 뒤에 둔다 (정의 다음 사용)"])


def system_map(d):
    """구성도: 바깥 컨테이너 + 안쪽 부품 + 양방향 화살표. 아래에 글머리 2~3줄."""
    s = d.slide("시스템 구성도", notes=[
        "브라우저는 앱 서버에만 말하고, 모델과 색인은 서버 안에서만 쓴다",
        "문서 폴더는 색인을 만들 때 한 번 읽는다. 질문할 때는 색인만 본다",
        "모든 부품이 같은 PC 에 있어 인터넷 없이 동작한다"])
    d.head(s, X0, 2.0, CW, "브라우저, 앱 서버, 문서 폴더의 연결")
    y0, H = 2.5, 2.1
    cy = y0 + H / 2
    node(s, X0, cy - 0.32, 1.5, 0.64, "Browser")
    harrow(s, X0 + 1.52, 2.95, cy, both=True)
    sx, ex = 2.97, 9.0
    box(s, sx, y0, ex - sx, H, fill=PALE)
    node(s, sx + 0.25, y0 + 0.15, ex - sx - 0.5, 0.66, "앱 서버", "FastAPI", dark=True)
    iw = (ex - sx - 0.5 - 0.36) / 3
    for k, (a, b) in enumerate([("검색기", "BM25, 임베딩"), ("색인", "문서 조각과 출처"), ("로컬 LLM", "Ollama")]):
        ix = sx + 0.25 + k * (iw + 0.18)
        node(s, ix, y0 + 1.2, iw, 0.72, a, b, fill=WHITE, line=LIGHT)
        varrow(s, ix + iw / 2, y0 + 0.83, y0 + 1.18, both=True)
    # 화살표 라벨이 들어갈 틈을 먼저 잡는다. 틈이 라벨보다 좁으면 뒤에 그린 상자가 라벨을 가린다
    harrow(s, 10.18, ex + 0.02, cy, label="색인 만들 때", label_w=1.1)
    node(s, 10.2, cy - 0.45, X1 - 10.2, 0.9, "문서 폴더", "PDF, DOCX, MD")
    bullets(s, X0, 4.85, CW, 1.4, [
        "질문 처리 중에는 문서 폴더를 다시 읽지 않는다. 색인만 검색한다",
        "모델 호출은 앱 서버 안에서만 한다. 브라우저에서 모델로 바로 가는 길이 없다"])


def pipeline(d):
    """처리 흐름: 같은 폭 상자 n 개 + 화살표, 아래에 단계별 표."""
    s = d.slide("질문 처리 흐름", notes=[
        "다섯 단계는 순서대로만 돈다. 앞 단계 출력이 다음 단계 입력이다",
        "근거가 없으면 생성 단계로 가지 않고 바로 '근거 없음' 을 돌려준다",
        "표의 출력 열이 다음 행의 입력 열과 같은지 보면 흐름이 맞는지 확인된다"])
    d.head(s, X0, 2.0, CW, "질문 하나가 답이 되기까지")
    steps = [("질문", "사용자 입력"), ("검색", "상위 4개 조각"), ("조립", "질문과 근거"),
             ("생성", "로컬 LLM"), ("근거 표시", "조각 출처")]
    n, gap = len(steps), 0.4
    w = (CW - (n - 1) * gap) / n
    for k, (a, b) in enumerate(steps):
        x = X0 + k * (w + gap)
        node(s, x, 2.5, w, 0.78, a, b, dark=(k == 3))
        if k < n - 1:
            harrow(s, x + w + 0.05, x + w + gap - 0.05, 2.89)
    d.head(s, X0, 3.55, CW, "단계별 입력과 출력", kind="표")
    table(s, X0, 3.97, CW, [2.0, 4.75, 4.75], [
        ["단계", "입력", "출력"],
        ["검색", "질문 문장", "점수 순 문서 조각 4개"],
        ["조립", "질문, 문서 조각", "프롬프트 한 개"],
        ["생성", "프롬프트", "답 문장"],
        ["근거 표시", "답 문장, 문서 조각", "답과 출처 목록"]], row_h=0.34)


def code_walk(d):
    """코드 분석: 왼쪽 코드(줄 끝 '# 1'), 오른쪽 같은 번호의 설명 글상자 하나."""
    s = d.slide("answer 함수 분석", notes=[
        "실제 소스를 그대로 싣고, 줄 끝 번호로 오른쪽 설명과 짝을 맞춘다",
        "근거가 없을 때 바로 돌아가는 2번이 이 앱의 핵심 안전장치다",
        "temperature 는 낮게 둬서 같은 질문에 답이 흔들리지 않게 한다"])
    d.code_block(s, X0, 2.0, 6.8, '''def answer(question: str, top_k: int = 4) -> dict:
    hits = index.search(question, k=top_k)           # 1
    if not hits:
        return {"text": "근거를 찾지 못했다", "sources": []}  # 2
    prompt = build_prompt(question, hits)             # 3
    text = llm.generate(prompt, temperature=0.2)      # 4
    return {"text": text,
            "sources": [h.doc_id for h in hits]}''', 'python', what="app/answer.py, 질문에 답하는 함수")
    numbered(s, 7.95, 2.42, X1 - 7.95, 1.9, [
        "질문과 가까운 문서 조각을 top_k 개 찾는다",
        "근거가 없으면 지어내지 않고 빈 출처로 돌아간다",
        "질문과 근거를 프롬프트 하나로 묶는다",
        "낮은 temperature 로 답을 만들고 출처를 같이 낸다"])
    # 코드 바로 아래에 그 코드가 만드는 흐름을 그린다 (코드와 그림을 짝지어 둔다, L-39)
    d.head(s, X0, 4.55, CW, "근거 유무에 따른 두 갈래")
    node(s, X0, 5.2, 2.0, 0.85, "검색 결과", "hits")
    for k, (a, b) in enumerate([("근거 있음", "조립, 생성"), ("근거 없음", "바로 반환")]):
        y = 5.0 + k * 0.85
        node(s, 3.55, y, 3.4, 0.6, a, b, dark=(k == 0))
        arrow(s, X0 + 2.02, 5.625, 3.53, y + 0.3)
        harrow(s, 6.97, 7.58, y + 0.3)
        node(s, 7.6, y, X1 - 7.6, 0.6, ["답과 출처 목록", "안내 문장과 빈 출처"][k])


def compare(d):
    """비교표 + 작은 흐름 그림. 표 아래에 요약 콜아웃을 달지 않는다 (L-42). 틀린 칸은 hl 로."""
    s = d.slide("검색 방식 비교", notes=[
        "BM25 는 낱말이 그대로 겹칠 때 강하고, 임베딩은 표현이 달라도 뜻이 가까우면 찾는다",
        "빨간 칸은 이 앱에서 실제로 문제가 된 약점이다 (모델 번호 같은 정확한 낱말)",
        "RRF 는 점수 대신 순위만 쓰므로 두 검색기의 점수 단위가 달라도 합칠 수 있다"])
    d.head(s, X0, 2.0, CW, "세 가지 검색 방식", kind="표")
    table(s, X0, 2.42, CW, [2.1, 3.3, 3.3, 2.8], [
        ["방식", "잘 찾는 것", "약한 것", "이 앱에서"],
        ["BM25", "같은 낱말이 나오는 문단", "다른 표현, 동의어", "기본 검색"],
        ["임베딩", "뜻이 가까운 문단", "모델 번호 같은 정확한 낱말", "보조 검색"],
        ["하이브리드", "둘의 장점", "설정이 하나 늘어남", "최종 순위"]], row_h=0.4, hl={(2, 2)})
    d.head(s, X0, 4.35, CW, "두 순위를 RRF 로 합치는 방법")
    node(s, X0, 4.85, 2.6, 0.62, "BM25 순위", "1, 2, 3")
    node(s, X0, 5.62, 2.6, 0.62, "임베딩 순위", "1, 2, 3")
    node(s, 4.6, 5.2, 3.1, 0.7, "RRF", "점수 = 합(1 / (60 + 순위))", dark=True)
    arrow(s, X0 + 2.62, 5.16, 4.58, 5.45)
    arrow(s, X0 + 2.62, 5.93, 4.58, 5.65)
    harrow(s, 7.72, 8.6, 5.55)
    node(s, 8.62, 5.2, X1 - 8.62, 0.7, "최종 순위", "상위 4개를 프롬프트에")


def patterns(d):
    """비교 카드: 열마다 남색 머리 + 작은 그림 + 한 줄 정의 + 흰 예제 상자."""
    s = d.slide("세 가지 처리 방식", notes=[
        "질문 처리를 모델 호출 몇 번으로 나누는지에 따라 세 가지로 볼 수 있다",
        "분기는 질문 종류를 먼저 고른다. 분류가 틀리면 엉뚱한 흐름으로 간다",
        "평가와 개선은 반복 횟수를 반드시 정한다. 정하지 않으면 끝나지 않을 수 있다"])
    d.head(s, X0, 2.0, CW, "처리 방식별 구조")
    cols = [("순차 연결", "앞 단계 출력을 다음 단계 입력으로 쓴다", "검색, 조립, 생성을 차례로 한다"),
            ("분기", "질문 종류에 따라 다른 흐름으로 보낸다", "설정 질문은 검색, 인사는 바로 답"),
            ("평가와 개선", "만든 답을 평가하고 고쳐 다시 낸다", "출처 없는 문장을 다시 쓴다 (최대 2회)")]
    cw, gap = (CW - 2 * 0.25) / 3, 0.25
    for k, (nm, desc, ex) in enumerate(cols):
        x0 = X0 + k * (cw + gap)
        box(s, x0, 2.45, cw, 3.55, fill=PALE)
        box(s, x0, 2.45, cw, 0.48, fill=NAVY, align=CEN, paras=[R(nm, font=F_MED, size=HEAD_PT, color=WHITE)])
        text(s, x0 + 0.15, 4.15, cw - 0.3, 0.5, [R(desc, size=BODY_PT)], align=CEN, anchor=MID_)
        box(s, x0 + 0.15, 4.8, cw - 0.3, 1.0, fill=WHITE, anchor=MID_, margins=(0.12, 0.08, 0.1, 0.08),
            paras=[{'runs': [R("예", font=F_MED, size=BODY_PT)], 'space_after': 3}, [R(ex, size=BODY_PT)]])
    # 순차 연결
    x0 = X0
    bw = (cw - 0.3 - 2 * 0.3) / 3
    for j, m in enumerate(["검색", "조립", "생성"]):
        node(s, x0 + 0.15 + j * (bw + 0.3), 3.25, bw, 0.55, m, fill=WHITE, line=LIGHT)
        if j < 2:
            arrow(s, x0 + 0.15 + j * (bw + 0.3) + bw + 0.03, 3.525, x0 + 0.15 + (j + 1) * (bw + 0.3) - 0.03, 3.525)
    # 분기
    x0 = X0 + cw + gap
    node(s, x0 + 0.2, 3.25, 1.1, 0.55, "분류", fill=WHITE, line=LIGHT)
    for j, (m, yy) in enumerate([("문서 검색", 3.05), ("바로 답", 3.62)]):
        node(s, x0 + 1.9, yy, cw - 2.1, 0.42, m, fill=WHITE, line=LIGHT, size=NODE_SUB_PT)
        arrow(s, x0 + 1.32, 3.525, x0 + 1.88, yy + 0.21)
    # 평가와 개선
    x0 = X0 + 2 * (cw + gap)
    node(s, x0 + 0.2, 3.2, 1.3, 0.55, "작성", fill=WHITE, line=LIGHT)
    node(s, x0 + cw - 1.5, 3.2, 1.3, 0.55, "평가", fill=WHITE, line=LIGHT)
    arrow(s, x0 + 1.52, 3.35, x0 + cw - 1.52, 3.35)
    arrow(s, x0 + cw - 1.52, 3.6, x0 + 1.52, 3.6)
    text(s, x0 + 1.5, 3.72, cw - 3.0, 0.3, [R("고칠 점", size=NODE_SUB_PT, color=GRAY)], align=CEN, anchor=MID_)


def rows(d):
    """행 흐름: 줄마다 왼쪽 남색 이름 상자 + 단계 상자들. 단계 수가 달라도 줄 끝을 맞춘다."""
    s = d.slide("설치 순서", notes=[
        "인터넷이 되는 PC 에서 필요한 것을 모두 받아 폴더 하나로 옮긴다",
        "대상 PC 는 인터넷 없이 설치하고, 재시작한 뒤 질문 하나로 확인한다",
        "실패하면 몇 번째 단계에서 멈췄는지와 오류 문장을 그대로 적어 둔다"])
    d.head(s, X0, 2.0, CW, "준비 PC 와 대상 PC 의 설치 단계")
    lines = [("준비 PC", "인터넷 연결", [("설치 파일", "Python, Ollama"), ("패키지", "pip download"),
                                          ("모델", "ollama pull"), ("묶기", "폴더 하나로")]),
             ("대상 PC", "인터넷 없음", [("설치", "--no-index"), ("모델 복사", "모델 폴더"),
                                         ("확인", "재시작 후 질문 1개")])]
    for k, (a, b, steps) in enumerate(lines):
        y = 2.5 + k * 1.15
        node(s, X0, y, 2.3, 0.9, a, b, dark=True)
        n, gap = len(steps), 0.42
        fx0 = 3.55
        w = (X1 - fx0 - (n - 1) * gap) / n
        for j, (t, u) in enumerate(steps):
            x = fx0 + j * (w + gap)
            node(s, x, y, w, 0.9, t, u)
            if j < n - 1:
                harrow(s, x + w + 0.05, x + w + gap - 0.05, y + 0.45)
    bullets(s, X0, 5.0, CW, 1.3, [
        "모델은 manifest 와 blob 폴더를 함께 옮겨야 한다",
        "확인은 앱과 Ollama 를 모두 재시작한 상태에서 한다"])


def study(d):
    """추가로 공부할 개념: 2 x 3 카드. 사용자가 원할 때만, 덱의 마지막 내용 슬라이드로."""
    s = d.slide("추가로 공부하면 좋은 개념", notes=[
        "예시 자료가 다루지 않지만 실제로 만들려면 필요한 것들이다",
        "급한 순서: 한국어 검색 품질, 문서 이해, 평가 방법"])
    cards = [("한국어 검색 품질", ["형태소 분석", "다국어 임베딩", "리랭커"]),
             ("문서 이해", ["표 추출", "스캔 문서 OCR", "그림 설명"]),
             ("평가 방법", ["검색 재현율", "근거 일치 판정", "회귀 시험"]),
             ("로컬 서빙", ["양자화", "배치 처리", "KV 캐시"]),
             ("보안", ["프롬프트 인젝션", "접근 권한", "로그 마스킹"]),
             ("운영", ["버전 기록", "승인 절차", "오프라인 설치"])]
    cw, gap = (CW - 2 * 0.22) / 3, 0.22
    for k, (t, items) in enumerate(cards):
        r_, c_ = divmod(k, 3)
        panel(s, X0 + c_ * (cw + gap), 2.0 + r_ * 2.3, cw, 2.1, t, items, anchor=MID_)


def main():
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath("example.pptx")
    d = Deck(sys.argv[2] if len(sys.argv) > 2 else None)
    for f in (cover, toc, system_map, pipeline, code_walk, compare, patterns, rows, study):
        f(d)
    d.closing("발표자 이름", notes=["질의응답"])
    d.save(out)


if __name__ == "__main__":
    main()
