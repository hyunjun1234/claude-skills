#!/usr/bin/env python3
"""렌더 검수용 글꼴을 깐다. 템플릿 글꼴(에스코어 드림 3 Light, 4 Regular, 5 Medium)이 없으면
LibreOffice 가 다른 글꼴로 바꿔 그려 줄바꿈 위치가 틀어지고, 검수가 헛돈다.

    python3 setup_fonts.py

- 이미 셋 다 있으면 아무것도 하지 않는다.
- npm 의 @noonnu/s-core-dream-3-light(woff)을 받아 otf 로 바꾸고, 같은 글리프에 이름만 바꾼
  4 Regular, 5 Medium 사본을 만든다. 실제 4, 5 굵기는 3 Light 보다 3~5% 넓다.
  그래서 검수 화면에서 꽉 찬 굵은 글자는 PowerPoint 에서 넘칠 수 있다고 보고 여유를 둔다.
- PowerPoint 는 pptx 에 들어 있는 글꼴을 쓰므로 이 단계는 렌더 검수에만 필요하다.
- fontTools 가 필요하다: pip install fonttools
"""
import glob
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

PKG = "@noonnu/s-core-dream-3-light"
TGZ_URL = "https://registry.npmjs.org/@noonnu/s-core-dream-3-light/-/s-core-dream-3-light-0.1.0.tgz"
WEIGHTS = [("3 Light", "3Light"), ("4 Regular", "4Regular"), ("5 Medium", "5Medium")]


def installed():
    if not shutil.which("fc-list"):
        return set()
    out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    return {w for w, _ in WEIGHTS if f"에스코어 드림 {w}" in out or f"S-Core Dream {w}" in out}


def font_dir():
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Fonts")
    return os.path.expanduser("~/.fonts")


def fetch_woff(tmp):
    data = None
    if shutil.which("npm"):
        r = subprocess.run(["npm", "pack", PKG, "--silent"], cwd=tmp, capture_output=True, text=True)
        tgz = glob.glob(os.path.join(tmp, "*.tgz"))
        if r.returncode == 0 and tgz:
            data = open(tgz[0], "rb").read()
    if data is None:
        data = urllib.request.urlopen(TGZ_URL, timeout=60).read()
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for m in tf.getmembers():
            if m.name.endswith(".woff"):
                return tf.extractfile(m).read()
    raise RuntimeError("패키지 안에 woff 가 없다")


def main():
    have = installed()
    if len(have) == len(WEIGHTS):
        print("✅ 에스코어 드림 3 Light, 4 Regular, 5 Medium 이 이미 있다")
        return
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        sys.exit("❌ fontTools 가 없다: pip install fonttools (또는 --break-system-packages)")
    dest = font_dir()
    os.makedirs(dest, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        woff = fetch_woff(tmp)
        for w, wp in WEIGHTS:
            if w in have:
                continue
            f = TTFont(io.BytesIO(woff))
            f.flavor = None
            for n in f["name"].names:
                if n.nameID in (1, 3, 4, 6, 17):
                    s = n.toUnicode().replace("3 Light", w).replace("3Light", wp)
                    n.string = s
            out = os.path.join(dest, f"S-CoreDream-{wp}.otf")
            f.save(out)
            print(f"설치 {out}")
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", dest], capture_output=True)
    left = {w for w, _ in WEIGHTS} - installed()
    print("✅ 완료" if not left or not shutil.which("fc-list") else f"⚠️ 아직 안 보이는 굵기: {sorted(left)}")


if __name__ == "__main__":
    main()
