"""Build the GinArt website.

Reads the editable content in content/ and renders it with the templates in
templates/ into dist/, which is what Cloudflare Pages publishes.

    python3 build.py            # build once into dist/
    python3 build.py --serve    # build, then preview on http://localhost:8000

Optional settings (used by the GitHub Pages preview):
    BASE_PATH=/ginart-public   site lives under a sub-folder, e.g. alex-sashev.github.io/ginart-public/
    PREVIEW=1           add "noindex" so search engines skip the preview
"""
import os
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
DIST = ROOT / "dist"
BASE = os.environ.get("BASE_PATH", "").rstrip("/")
PREVIEW = os.environ.get("PREVIEW") == "1"


def with_base(text):
    """Prefix site-absolute links (/ceni/, /images/...) with BASE_PATH."""
    if not BASE:
        return text
    text = re.sub(r'((?:href|src)=")/(?!/)', rf"\1{BASE}/", text)
    return re.sub(r"url\(/(?!/)", f"url({BASE}/", text)


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_md(path):
    """A Markdown file with a YAML block between --- lines at the top."""
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        _, front, body = text.split("---", 2)
        meta = yaml.safe_load(front) or {}
    meta["slug"] = path.stem
    meta["body"] = markdown.markdown(body.strip(), extensions=["extra", "sane_lists"])
    return meta


def as_list(value):
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def write(url, html):
    out = DIST / url.strip("/") / "index.html" if url != "/404" else DIST / "404.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(with_base(html), encoding="utf-8")


def build():
    site = load_yaml(CONTENT / "site.yml")
    home = load_yaml(CONTENT / "home.yml")
    prices = load_yaml(CONTENT / "prices.yml")
    doctors = sorted((load_md(p) for p in (CONTENT / "doctors").glob("*.md")),
                     key=lambda d: d.get("order", 99))
    pages = [load_md(p) for p in (CONTENT / "pages").glob("*.md")]
    pages = [p for p in pages if not p.get("hidden")]
    by_order = lambda p: (p.get("order", 99), p.get("heading", ""))
    services = sorted((p for p in pages if p.get("type") == "service"), key=by_order)

    # The main sections (Диагностика, Бременност, Хирургия) and the services in each.
    # A service names its section(s) with "section: diagnostika" or a list.
    sections = sorted((p for p in pages if p.get("template") == "section"), key=by_order)
    for sec in sections:
        sec["services"] = [s for s in services if sec["slug"] in as_list(s.get("section"))]
    for s in services:
        s["sections"] = [sec for sec in sections if sec["slug"] in as_list(s.get("section"))]

    articles = [load_md(p) for p in (CONTENT / "articles").glob("*.md")]
    articles = sorted((a for a in articles if not a.get("hidden")),
                      key=lambda a: str(a.get("date", "")), reverse=True)
    categories = list(dict.fromkeys(a["category"] for a in articles if a.get("category")))

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    common = dict(preview=PREVIEW, site=site, home=home, doctors=doctors, services=services, prices=prices,
                  sections=sections, articles=articles, categories=categories)

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST)
    for css in DIST.glob("*.css"):
        css.write_text(with_base(css.read_text(encoding="utf-8")), encoding="utf-8")

    write("/", env.get_template("home.html").render(page={"slug": "home"}, **common))
    for page in pages:
        template = page.get("template", "page") + ".html"
        write(f"/{page['slug']}/", env.get_template(template).render(page=page, **common))
    for article in articles:
        write(f"/za-pacientite/{article['slug']}/",
              env.get_template("article.html").render(page=article, **common))
    write("/404", env.get_template("404.html").render(page={"slug": "404"}, **common))

    print(f"Built {len(pages) + len(articles) + 2} pages into {DIST.relative_to(ROOT)}/")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools
        import http.server

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIST)
        print("Preview: http://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
