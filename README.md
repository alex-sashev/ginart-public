# GinArt — website

Website for GinArt, an obstetrics & gynaecology practice in Sofia. Design: "Option B" mockup (2026-09-17); content migrated from the old ginart.bg (2026-10-11). Same URLs as the old site, so existing links and Google rankings carry over.

**To edit text, see [EDITING.md](EDITING.md).**

## Layout
- `content/` — all editable text (YAML + Markdown)
- `templates/` — page layouts (Jinja2)
- `static/` — styles, script, images, `_redirects` (copied as-is)
- `build.py` — renders everything into `dist/`
- `.pages.yml` — Pages CMS editor config

## Build & preview locally
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python build.py --serve
```

## Deploy (Cloudflare Pages)
Workers & Pages → Create → Pages → Connect to Git → `alex-sashev/GinArt`
- Framework preset: **None**
- Build command: `pip install -r requirements.txt && python build.py`
- Build output directory: `dist`

Push to `main` = production; other branches get preview URLs.
