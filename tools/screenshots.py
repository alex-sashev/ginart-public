"""Full-page desktop screenshots of every page, cut into slices for the review document.

    .venv/bin/python build.py --serve      # in one terminal (site on :8000)
    .venv/bin/python tools/screenshots.py [base_url]

Uses Google Chrome in headless mode. Slices go to review-shots/<page>/NN.jpg.
"""
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "review-shots"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH, SLICE = 1280, 900


def page_urls():
    urls = ["/"] + [f"/{p.stem}/" for p in (ROOT / "content/pages").glob("*.md")]
    urls += [f"/za-pacientite/{p.stem}/" for p in (ROOT / "content/articles").glob("*.md")]
    return urls


def key(url):
    return url.strip("/").replace("/", "__") or "home"


def capture(base, url, profile):
    png = OUT / f"{key(url)}.png"
    png.unlink(missing_ok=True)
    # Chrome writes the file but may not exit on its own, so wait for the file instead.
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--hide-scrollbars", "--disable-gpu", f"--user-data-dir={profile}",
         f"--window-size={WIDTH},12000", "--virtual-time-budget=4000", f"--screenshot={png}", base + url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if png.exists() and png.stat().st_size > 0:
            time.sleep(1)
            break
        time.sleep(0.5)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    return png


def crop_and_slice(png, url):
    im = Image.open(png).convert("RGB")
    w, h = im.size
    bg = im.getpixel((w - 5, h - 5))
    px = im.load()
    end = h
    for y in range(h - 1, 0, -1):
        if any(sum(abs(a - b) for a, b in zip(px[x, y], bg)) > 12 for x in range(0, w, 4)):
            end = min(h, y + 30)
            break
    im = im.crop((0, 0, w, end))
    folder = OUT / key(url)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.jpg"):
        old.unlink()
    n = 0
    for top in range(0, end, SLICE):
        part = im.crop((0, top, w, min(end, top + SLICE)))
        if part.size[1] < 60:
            continue
        n += 1
        part.save(folder / f"{n:02d}.jpg", quality=72, optimize=True)
    png.unlink()
    return n


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
    OUT.mkdir(exist_ok=True)
    profile = OUT / ".chrome-profile"
    for url in page_urls():
        png = capture(base, url, profile)
        if not png.exists():
            print(f"FAILED {url}")
            continue
        print(f"{url}: {crop_and_slice(png, url)} slices")


if __name__ == "__main__":
    main()
