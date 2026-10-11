"""Refresh the SuperDoc ratings shown on the site.

Reads the SuperDoc link in each content/doctors/*.md,
fetches each public profile page and updates superdoc_rating / superdoc_count in
place. If a page can't be read, the old numbers are kept.

    python3 update_superdoc.py

Runs weekly on GitHub (.github/workflows/superdoc.yml).
"""
import html
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
FILES = [(p, "superdoc_url") for p in sorted((ROOT / "content/doctors").glob("*.md"))]


def fetch_rating(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (GinArt rating refresh)"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", "", page, flags=re.S)))
    m = re.search(r"Рейтинг\s+(\d[.,]\d)\s+([\d\s]+?)\s+оценки", text)
    if not m:
        raise ValueError("rating not found on page")
    return float(m.group(1).replace(",", ".")), int(re.sub(r"\s", "", m.group(2)))


def main():
    for path, key in FILES:
        text = path.read_text(encoding="utf-8")
        url = re.search(rf"^{key}:\s*(\S+)", text, re.M)
        if not url or "superdoc.bg" not in url.group(1):
            continue
        try:
            rating, count = fetch_rating(url.group(1))
        except Exception as e:
            print(f"skip {path.name}: {e}")
            continue
        new = re.sub(r"^superdoc_rating:.*$", f"superdoc_rating: {rating}", text, flags=re.M)
        new = re.sub(r"^superdoc_count:.*$", f"superdoc_count: {count}", new, flags=re.M)
        if new != text:
            path.write_text(new, encoding="utf-8")
        print(f"{path.name}: {rating} ({count} оценки)")


if __name__ == "__main__":
    main()
