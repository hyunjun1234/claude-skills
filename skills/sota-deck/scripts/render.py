#!/usr/bin/env python3
"""pptx 를 PDF 와 슬라이드 그림으로 렌더하고, 두 장씩 세로로 붙인 검수용 대지를 만든다.

    python3 render.py /abs/deck.pptx /abs/render_dir [--dpi 110]

결과: render_dir/deck.pdf, s-01.jpg ..., pair-01-02.jpg ...
렌더는 LibreOffice 로 한다. PowerPoint 와 줄바꿈 위치가 조금 다를 수 있으니(글꼴 대체)
꽉 찬 글자는 여유를 두고 판단한다. 먼저 setup_fonts.py 로 템플릿 글꼴을 깔아 둔다.
"""
import glob
import os
import shutil
import subprocess
import sys


def find_soffice():
    """(명령 목록) 을 돌려준다. 샌드박스에서는 맨 soffice 가 멈출 수 있어 pptx 스킬의 감싸개를 먼저 쓴다."""
    env = os.environ.get("SOFFICE")
    if env:
        return [env]
    home = os.path.expanduser("~")
    wrappers = sorted(glob.glob(os.path.join(home, ".claude", "skills", "**", "pptx", "scripts", "office",
                                             "soffice.py"), recursive=True))
    wrappers += sorted(glob.glob("/root/.claude/skills/**/pptx/scripts/office/soffice.py", recursive=True))
    if wrappers:
        return [sys.executable, wrappers[0]]
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return [p]
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.exists(mac):
        return [mac]
    return None


def to_images(pdf, out, dpi):
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-jpeg", "-r", str(dpi), pdf, os.path.join(out, "s")],
                       stderr=subprocess.DEVNULL, check=True)
    else:
        import fitz   # PyMuPDF
        doc = fitz.open(pdf)
        for k, page in enumerate(doc, 1):
            page.get_pixmap(dpi=dpi).save(os.path.join(out, f"s-{k:02d}.jpg"))
    imgs = sorted(glob.glob(os.path.join(out, "s-*.jpg")))
    # pdftoppm 은 쪽수에 따라 s-1.jpg 또는 s-01.jpg 로 쓴다. 두 자리로 맞춘다
    fixed = []
    for f in imgs:
        n = int(os.path.basename(f)[2:-4])
        g = os.path.join(out, f"s-{n:02d}.jpg")
        if f != g:
            os.replace(f, g)
        fixed.append(g)
    return sorted(fixed)


def pairs(imgs, out):
    from PIL import Image
    made = []
    for k in range(0, len(imgs), 2):
        a = Image.open(imgs[k])
        b = Image.open(imgs[k + 1]) if k + 1 < len(imgs) else None
        h = a.height + (b.height + 10 if b else 0)
        im = Image.new("RGB", (a.width, h), "white")
        im.paste(a, (0, 0))
        if b:
            im.paste(b, (0, a.height + 10))
        name = os.path.join(out, f"pair-{k + 1:02d}-{k + 2:02d}.jpg" if b else f"pair-{k + 1:02d}.jpg")
        im.save(name, quality=85)
        made.append(name)
    return made


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    deck, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    dpi = int(sys.argv[sys.argv.index("--dpi") + 1]) if "--dpi" in sys.argv else 110
    cmd = find_soffice()
    if not cmd:
        sys.exit("❌ LibreOffice(soffice)가 없다. 렌더 검수를 못 한다. "
                 "macOS: brew install --cask libreoffice / Debian: sudo apt install libreoffice-impress")
    if os.path.isdir(out):
        for f in glob.glob(os.path.join(out, "*")):
            if os.path.isfile(f):
                os.remove(f)
    os.makedirs(out, exist_ok=True)
    shutil.copy(deck, os.path.join(out, "deck.pptx"))
    subprocess.run(cmd + ["--headless", "--convert-to", "pdf", "deck.pptx"], cwd=out,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    pdf = os.path.join(out, "deck.pdf")
    if not os.path.exists(pdf):
        sys.exit(f"❌ PDF 변환 실패: {' '.join(cmd)}")
    imgs = to_images(pdf, out, dpi)
    made = pairs(imgs, out)
    print(f"PDF {pdf}")
    print(f"슬라이드 그림 {len(imgs)}장, 두 장씩 대지 {len(made)}장:")
    for m in made:
        print("  " + m)


if __name__ == "__main__":
    main()
