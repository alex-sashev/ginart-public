"""Export all website text into one Word document for the clinic to review.

    .venv/bin/python tools/content_review.py [output.docx]

Every row has a code (e.g. "pages/kolposkopiya · 3") that points to the exact
file and field, so the returned document can be applied back to content/.
"""
import re
import sys
from datetime import date
from pathlib import Path

import yaml
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
PREVIEW = "https://alex-sashev.github.io/ginart-public"

PLUM = RGBColor(0x6B, 0x23, 0x40)
GREY = RGBColor(0x80, 0x80, 0x80)
COLS = [Cm(2.4), Cm(4.0), Cm(10.5), Cm(9.6)]  # code | field | current | new  (landscape A4)


# ---------- reading content ----------

def load_yaml(p):
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def load_md(p):
    text = p.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        _, front, body = text.split("---", 2)
        meta = yaml.safe_load(front) or {}
    return meta, body.strip()


def body_blocks(body):
    """Split Markdown into blocks at '## ' headings: [(heading or None, lines)]."""
    blocks, head, lines = [], None, []
    for line in body.split("\n"):
        if line.startswith("## "):
            if head is not None or any(l.strip() for l in lines):
                blocks.append((head, lines))
            head, lines = line[3:].strip(), []
        else:
            lines.append(line)
    if head is not None or any(l.strip() for l in lines):
        blocks.append((head, lines))
    return blocks


MARKERS = {"{.do}": "  [✓ списък „направете“]", "{.dont}": "  [✕ списък „избягвайте“]",
           "{.warn}": "  [! предупреждение]"}


def clean_heading(h):
    for k, v in MARKERS.items():
        h = h.replace(k, v)
    return h.strip()


# ---------- Word helpers ----------

def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def add_inline(par, text, size=10, color=None):
    """Add text with **bold** and [link](url) → link text."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    for i, part in enumerate(re.split(r"\*\*", text)):
        if not part:
            continue
        run = par.add_run(part)
        run.bold = i % 2 == 1
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color


def cell_text(cell, lines, heading=None):
    """Fill a cell with a heading and Markdown-ish lines (paragraphs, - lists, ### subheads)."""
    cell.paragraphs[0].text = ""
    first = True

    def para():
        nonlocal first
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(3)
        return p

    if heading:
        r = para().add_run(clean_heading(heading))
        r.bold = True
        r.font.size = Pt(10.5)
        r.font.color.rgb = PLUM
    for line in lines:
        s = line.rstrip()
        if not s.strip():
            continue
        if s.startswith("### "):
            r = para().add_run(s[4:])
            r.bold = True
            r.font.size = Pt(10)
        elif re.match(r"^\s*[-*] ", s):
            indent = len(s) - len(s.lstrip())
            p = para()
            p.paragraph_format.left_indent = Cm(0.4 + 0.4 * (indent // 4))
            add_inline(p, "– " + s.strip()[2:])
        elif s.startswith("*") and s.endswith("*") and not s.startswith("**"):
            add_inline(para(), s.strip("*"), color=GREY)
        else:
            add_inline(para(), s.strip())


class Review:
    def __init__(self):
        self.doc = Document()
        sec = self.doc.sections[0]
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = Cm(29.7), Cm(21.0)
        for side in ("left_margin", "right_margin"):
            setattr(sec, side, Cm(1.6))
        sec.top_margin = sec.bottom_margin = Cm(1.5)
        st = self.doc.styles["Normal"]
        st.font.name = "Arial"
        st.font.size = Pt(10)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        for name, size in (("Heading 1", 18), ("Heading 2", 13.5)):
            h = self.doc.styles[name]
            h.font.name = "Arial"
            h.font.size = Pt(size)
            h.font.color.rgb = PLUM
            h.element.rPr.rFonts.set(qn("w:ascii"), "Arial")
            h.element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        footer = sec.footer.paragraphs[0]
        footer.text = f"ГинАрт — преглед на съдържанието на сайта · {date.today():%d.%m.%Y}"
        footer.runs[0].font.size = Pt(8)
        footer.runs[0].font.color.rgb = GREY
        self.table = None

    def page(self, title, url=None, note=None, first=False):
        if not first:
            self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.doc.add_heading(title, level=1)
        if url or note:
            p = self.doc.add_paragraph()
            if url:
                r = p.add_run(f"Страница на сайта: {PREVIEW}{url}")
                r.font.size = Pt(9)
                r.font.color.rgb = GREY
            if note:
                r = p.add_run(("\n" if url else "") + note)
                r.font.size = Pt(9)
                r.italic = True

    def section(self, title, note=None):
        self.doc.add_heading(title, level=2)
        if note:
            r = self.doc.add_paragraph().add_run(note)
            r.font.size = Pt(9)
            r.italic = True
        t = self.doc.add_table(rows=1, cols=4)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for col, w in zip(t.columns, COLS):
            col.width = w  # sets the table grid, which some viewers use instead of cell widths
        tblPr = t._tbl.tblPr
        tblW = tblPr.find(qn("w:tblW"))
        if tblW is None:
            tblW = OxmlElement("w:tblW")
            tblPr.append(tblW)
        tblW.set(qn("w:type"), "dxa")
        tblW.set(qn("w:w"), str(int(sum(w for w in COLS) / 635)))
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tblPr.append(layout)
        hdr = t.rows[0]
        repeat_header(hdr)
        for cell, w, label in zip(hdr.cells, COLS, ("Код", "Поле", "Текущ текст", "Нов текст / коментар")):
            cell.width = w
            shade(cell, "6B2340")
            r = cell.paragraphs[0].add_run(label)
            r.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        self.table = t

    def row(self, code, field, current=None, lines=None, heading=None):
        cells = self.table.add_row().cells
        for c, w in zip(cells, COLS):
            c.width = w
        r = cells[0].paragraphs[0].add_run(code)
        r.font.size = Pt(7.5)
        r.font.color.rgb = GREY
        r = cells[1].paragraphs[0].add_run(field)
        r.font.size = Pt(9.5)
        r.bold = True
        if lines is not None or heading:
            cell_text(cells[2], lines or [], heading)
        else:
            add_inline(cells[2].paragraphs[0], "" if current is None else str(current))
        shade(cells[3], "FFF8E7")

    def save(self, path):
        self.doc.save(path)


# ---------- building the document ----------

def md_page(rv, rel, meta, body, fields=True):
    """Rows for a Markdown page: heading, summary, SEO, then each text block."""
    if fields:
        rv.row(f"{rel} · heading", "Заглавие на страницата", meta.get("heading", ""))
        if "summary" in meta:
            rv.row(f"{rel} · summary", "Кратко описание (под заглавието и в картичките)", meta.get("summary", ""))
        if "excerpt" in meta:
            rv.row(f"{rel} · excerpt", "Кратко описание (в картичката)", meta.get("excerpt", ""))
        if "category" in meta:
            rv.row(f"{rel} · category", "Категория", meta.get("category", ""))
    for i, (head, lines) in enumerate(body_blocks(body), 1):
        rv.row(f"{rel} · {i}", f"Текст — част {i}", lines=lines, heading=head)
    if fields:
        rv.row(f"{rel} · title", "Заглавие в Google (таб на браузъра)", meta.get("title", ""))
        rv.row(f"{rel} · description", "Описание в Google", meta.get("description", ""))


def build(out):
    site = load_yaml(CONTENT / "site.yml")
    home = load_yaml(CONTENT / "home.yml")
    prices = load_yaml(CONTENT / "prices.yml")
    pages = {p.stem: load_md(p) for p in (CONTENT / "pages").glob("*.md")}
    services = sorted(((s, m) for s, (m, _) in pages.items() if m.get("type") == "service"),
                      key=lambda x: x[1].get("order", 99))
    sections = sorted(((s, m) for s, (m, _) in pages.items() if m.get("template") == "section"),
                      key=lambda x: x[1].get("order", 99))

    rv = Review()

    # --- instructions ---
    rv.doc.add_heading("ГинАрт — съдържание на новия сайт за преглед", level=1)
    intro = [
        f"Новият сайт (тестова версия): {PREVIEW}/",
        "Документът съдържа целия текст на сайта, подреден по страници и секции — в същия ред, в който се вижда на сайта.",
        "",
        "Как да работите с документа:",
        "1. Прочетете „Текущ текст“. Ако е наред — оставете колоната „Нов текст / коментар“ празна.",
        "2. Ако искате промяна — напишете новия текст в жълтата колона „Нов текст / коментар“. Може да е целият нов текст или само коментар (напр. „махнете второто изречение“).",
        "3. За да изтриете нещо — напишете ИЗТРИЙ.",
        "4. Не променяйте колоната „Код“ — по нея нанасяме промените на правилното място.",
        "5. Нови услуги, статии или страници — опишете ги в последния раздел „Нови неща и общи коментари“.",
        "6. Снимки — изпратете ги отделно (по имейл), като посочите за кое място са (раздел „Снимки“).",
        "",
        "Полетата „Заглавие в Google“ и „Описание в Google“ определят как изглежда страницата в резултатите от търсене в Google — по желание.",
        "",
        "English: this document lists all website text by page and section. Write changes in the yellow column, leave it empty if the text is fine, don't edit the Code column, and return the file.",
    ]
    for line in intro:
        p = rv.doc.add_paragraph()
        add_inline(p, line, size=10.5)
        p.paragraph_format.space_after = Pt(2)

    rv.section("Въпроси към кабинета", "Моля, отговорете в жълтата колона.")
    questions = [
        ("Q · prices", "Цени", "Липсват цени в € за хистероскопия, кюретаж и аборт (на сайта пише „обадете се за цена“). Какви са цените или да остане така?"),
        ("Q · phones", "Телефони", "Старият сайт споменава и 02/922 62 06 и 02/922 51 28. Активни ли са? Новият сайт показва само 0878 504 517."),
        ("Q · legal", "Политика за поверителност", "Моля, попълнете: наименование на юридическото лице, ЕИК и имейл за въпроси относно личните данни."),
        ("Q · services", "Липсващи услуги", "В профила на кабинета в SuperDoc има услуги, които ги няма на сайта: медикаментозен аборт, лазерна терапия (преканцерози, генитоуринарен синдром, вагинално подмладяване / инконтиненция), течно-базирана цитология, HPV-ДНК тест, епизиоскопия. Да ги добавим ли? Ако да — кратко описание за всяка."),
        ("Q · abortion", "Страница „Прекъсване на бременност“", "Текстът си противоречи (пише, че медикаментозният аборт „не е легализиран у нас“, а кабинетът го предлага). Моля, лекар да прегледа и коригира. Да остане ли страницата в „Бременност“?"),
        ("Q · social", "Социални мрежи", "Има ли страници във Facebook / Instagram? Моля, изпратете линковете."),
        ("Q · english", "Английска версия", "Нужна ли е версия на английски език?"),
        ("Q · articles", "Статии", "Какви теми искате за следващите статии в „За пациентите“ (напр. HPV, контрацепция, менопауза, бременност по седмици)? Кой ще ги пише?"),
    ]
    for code, field, text in questions:
        rv.row(code, field, text)

    # --- general details ---
    rv.page("Общи данни (на всички страници)", "/", "Показват се в горното меню, долната част на всяка страница и бутоните за записване.")
    rv.section("Данни за кабинета")
    for key, label in (("name", "Име"), ("tagline", "Слоган под логото"), ("phone", "Телефон за записване"),
                       ("hours", "Работно време"), ("booking_note", "Бележка за записването"),
                       ("address", "Адрес"), ("address_note", "Как да ни намерите"),
                       ("nzok_note", "Бележка за НЗОК"), ("book_button", "Текст на бутона за записване"),
                       ("description", "Описание в Google (общо)")):
        rv.row(f"site · {key}", label, site.get(key, ""))
    rv.row("site · facebook", "Facebook линк", site.get("facebook") or "(няма)")
    rv.row("site · instagram", "Instagram линк", site.get("instagram") or "(няма)")
    rv.section("Меню")
    for i, item in enumerate(site.get("menu", []), 1):
        rv.row(f"site · menu {i}", f"Меню — позиция {i}", f"{item['label']}  (→ {item['link']})")

    # --- home ---
    rv.page("Начална страница", "/", "Секциите са в реда, в който се виждат на сайта.")
    h = home["hero"]
    rv.section("1. Горна секция (голямата снимка)")
    rv.row("home · hero.eyebrow", "Малък надпис над заглавието", h["eyebrow"])
    rv.row("home · hero.heading", "Голямо заглавие", h["heading"])
    rv.row("home · hero.text", "Текст под заглавието", h["text"])
    rv.row("home · hero.book_button", "Бутон 1", h["book_button"])
    rv.row("home · hero.call_button", "Бутон 2", h["call_button"])
    rv.row("home · hero.handwritten", "Ръкописен текст до снимката", h["handwritten"].replace("<br>", " / "))
    for i, p in enumerate(h["points"], 1):
        rv.row(f"home · hero.points {i}", f"Предимство {i} (с икона)", p["text"])
    a = home["about"]
    rv.section("2. За ГинАрт")
    rv.row("home · about.eyebrow", "Малък надпис", a["eyebrow"])
    rv.row("home · about.heading", "Заглавие", a["heading"])
    rv.row("home · about.text", "Текст", a["text"])
    rv.row("home · about.button_text", "Бутон", a["button_text"])
    rv.row("home · about.handwritten", "Ръкописен текст", a["handwritten"].replace("<br>", " / "))
    rv.section("3. Нашите услуги", "Трите карти (Диагностика, Бременност, Хирургия) използват заглавието и краткото описание от страниците на направленията — редактирайте ги там.")
    rv.row("home · services.heading", "Заглавие на секцията", home["services"]["heading"])
    rv.section("4. Нашите специалисти", "Имената и текстовете на лекарите — вижте „Специалисти“. Оценките от SuperDoc се обновяват автоматично.")
    rv.row("home · doctors.heading", "Заглавие на секцията", home["doctors"]["heading"])
    rv.section("5. За пациентите", "Показват се трите най-нови статии (вижте „За пациентите“).")
    rv.row("home · patients.heading", "Заглавие на секцията", home["patients"]["heading"])
    c = home["cta"]
    rv.section("6. Лента за записване (в края на всяка страница)")
    rv.row("home · cta.heading", "Заглавие", c["heading"])
    rv.row("home · cta.text", "Текст", c["text"])
    rv.row("home · cta.button_text", "Бутон", c["button_text"])

    # --- areas + services ---
    for s, m in sections:
        meta, body = pages[s]
        rv.page(f"Направление: {m['heading']}", f"/{s}/")
        rv.section("Страница на направлението")
        md_page(rv, f"pages/{s}", meta, body)
        members = [(x, xm) for x, xm in services if s in (xm.get("section") if isinstance(xm.get("section"), list) else [xm.get("section")])]
        for x, xm in members:
            if s != (xm["section"][0] if isinstance(xm["section"], list) else xm["section"]):
                continue  # services listed under two areas appear only under the first
            meta2, body2 = pages[x]
            rv.section(f"Услуга: {xm['heading']}", f"Страница на сайта: {PREVIEW}/{x}/")
            md_page(rv, f"pages/{x}", meta2, body2)

    # --- doctors ---
    rv.page("Специалисти", "/specialisti/")
    for p in sorted((CONTENT / "doctors").glob("*.md"), key=lambda p: load_md(p)[0].get("order", 99)):
        meta, body = load_md(p)
        rel = f"doctors/{p.stem}"
        rv.section(meta["name"])
        rv.row(f"{rel} · name", "Име и титли", meta["name"])
        rv.row(f"{rel} · role", "Специалност", meta["role"])
        rv.row(f"{rel} · summary", "Кратък текст (начална страница)", meta["summary"])
        rv.row(f"{rel} · bio", "Биография", lines=body.split("\n"))

    # --- prices ---
    rv.page("Цени", "/ceni/", "За всяка цена: ако е вярна — оставете празно. Нова услуга — добавете в раздел „Нови неща“.")
    rv.section("Текстове")
    rv.row("prices · intro", "Текст над цените", prices["intro"])
    rv.row("prices · note", "Бележка под цените", prices["note"])
    for gi, g in enumerate(prices["groups"], 1):
        rv.section(f"Група: {g['title']}")
        rv.row(f"prices · group {gi}", "Име на групата", g["title"])
        for ii, it in enumerate(g["items"], 1):
            rv.row(f"prices · {gi}.{ii}", it["name"], it["price"])

    # --- patients / articles ---
    meta, body = pages["za-pacientite"]
    rv.page("За пациентите (статии)", "/za-pacientite/")
    rv.section("Страница със статиите")
    rv.row("pages/za-pacientite · heading", "Заглавие", meta["heading"])
    rv.row("pages/za-pacientite · summary", "Текст под заглавието", meta.get("summary", ""))
    arts = sorted((CONTENT / "articles").glob("*.md"), key=lambda p: str(load_md(p)[0].get("date", "")), reverse=True)
    for p in arts:
        meta, body = load_md(p)
        rv.section(f"Статия: {meta['heading']}", f"Страница на сайта: {PREVIEW}/za-pacientite/{p.stem}/")
        md_page(rv, f"articles/{p.stem}", meta, body)

    # --- other pages ---
    for slug, label in (("za-ginart", "За нас"), ("aparatura", "Апаратура"), ("uslugi", "Всички услуги"),
                        ("kontakt", "Контакти"), ("poveritelnost", "Политика за поверителност"),
                        ("biskvitki", "Политика за бисквитки")):
        meta, body = pages[slug]
        rv.page(label, f"/{slug}/")
        rv.section("Съдържание")
        md_page(rv, f"pages/{slug}", meta, body)

    # --- photos ---
    rv.page("Снимки", note="Изпратете новите снимки по имейл и посочете кода на мястото. Най-добре хоризонтални, добре осветени, поне 1600 px широки.")
    rv.section("Снимки на сайта")
    photos = [
        ("img · hero", "Начална страница — голяма снимка", "Примерна снимка на усмихната жена (от макета)."),
        ("img · about", "Начална страница — „За ГинАрт“", "Примерна снимка на рецепция (от макета, с надпис „GINART“ на латиница) — да се замени с реална снимка на кабинета."),
        ("img · kovachev", "Проф. д-р Стефан Ковачев", "Снимка от стария сайт (~2015 г.)."),
        ("img · ganovska", "Д-р Анита Гановска", "Снимка от стария сайт (~2015 г.)."),
        ("img · equipment", "Апаратура / Ехография", "Снимка на ехографа от стария сайт (~2012 г.)."),
        ("img · colposcope", "Колпоскопия", "Снимка от стария сайт."),
        ("img · pregnancy", "Бременност", "Снимка от стария сайт."),
        ("img · other", "Други", "Снимки на кабинета, екипа, чакалнята — ще ги използваме в „За нас“ и „Контакти“."),
    ]
    for code, field, text in photos:
        rv.row(code, field, text)

    # --- new things ---
    rv.page("Нови неща и общи коментари")
    rv.section("Нови услуги, статии, страници", "Опишете всичко ново: име, кратко описание, цена (ако има), към кое направление е.")
    for i in range(1, 7):
        rv.row(f"new · {i}", f"Ново {i}", "")
    rv.section("Общи коментари")
    for i in range(1, 4):
        rv.row(f"general · {i}", f"Коментар {i}", "")

    rv.save(out)
    print(f"Saved {out}")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "GinArt-sadarzhanie-za-pregled.docx"))
