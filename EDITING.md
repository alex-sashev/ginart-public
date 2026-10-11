# How to edit the GinArt website

You never touch the design. All text lives in the `content/` folder:

| What you want to change | File |
|---|---|
| Phone, hours, address, menu, Facebook/Instagram | `content/site.yml` |
| Homepage sections (texts, pictures, show/hide a section) | `content/home.yml` |
| The 3 main areas: Диагностика, Бременност, Хирургия | `content/pages/diagnostika.md`, `bremennost.md`, `hirurgia.md` |
| Articles and guides („За пациентите“) | `content/articles/<article-name>.md` |
| Prices | `content/prices.yml` |
| A doctor's profile | `content/doctors/kovachev.md`, `content/doctors/ganovska.md` |
| Any other page (services, contact, tips, about) | `content/pages/<page-name>.md` |

Pictures go in `static/images/` and are referenced as `/images/<file-name>`.

## Option 1 — edit on GitHub (works now)
1. Open the file on github.com/alex-sashev/GinArt, click the ✏️ pencil.
2. Change the text. Keep the structure (`name: value`, the dashes, the indentation).
3. Click **Commit changes**. Cloudflare rebuilds the site; it's live in ~1 minute.

## Option 2 — Pages CMS (forms, no code)
1. Go to https://app.pagescms.org, sign in with GitHub, install the Pages CMS app on the `GinArt` repo.
2. Open the repo — you get forms in Bulgarian: Начална страница, Страници и услуги, Специалисти, Цени, Данни за кабинета.
3. Save — same as committing; the site updates in ~1 minute.

## Writing page text (Markdown)
- `## Heading` — a section heading
- `- item` — a bullet point
- `**bold**` — bold text
- `[text](/ceni/)` — a link
- Leave an empty line between paragraphs.

## Adding a new service page
Copy any service file in `content/pages/` (e.g. `kolposkopiya.md`), rename it (the file name becomes the web address: `novo.md` → `/novo/`), change the text. Set `section:` to `diagnostika`, `bremennost` or `hirurgia` — the service then appears automatically on the homepage card, that area's page and the Services page. `order:` sets its position.

## Writing an article („За пациентите“)
Copy any file in `content/articles/`, rename it, change the text. Fill in:
- `heading` — the title; `excerpt` — 1–2 sentences for the card
- `category` — e.g. Профилактика, Симптоми, Бременност, Подготовка за преглед, След процедура (new categories appear as filter buttons automatically)
- `date` — newest articles show first; the 3 newest appear on the homepage
- `image` — optional

**Do's and don'ts:** put `{.do}`, `{.dont}` or `{.warn}` after a heading, and the list under it gets green ✓, plum ✕ or orange ! styling:

```
## Какво да направите {.do}
- Запишете час след края на менструацията

## Какво да избягвате {.dont}
- Тампони 1–2 дни преди прегледа

## Обадете се на лекар, ако {.warn}
- Имате висока температура
```

Every article ends automatically with a "this does not replace a consultation" note and the booking button.

## Hide a homepage section
In `content/home.yml` set `show: false` under that section.
