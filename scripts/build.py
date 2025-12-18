#!/usr/bin/env python3
import os, re, sys, shutil, datetime, pathlib, yaml
from pathlib import Path
from email.utils import format_datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown as md

ROOT = Path(__file__).resolve().parent.parent
SRC_POSTS = ROOT / "posts"
DIST = ROOT / "dist"
TPL_DIR = ROOT / "templates"

def load_site():
    with open(ROOT / "site.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def parse_frontmatter(text):
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        data = yaml.safe_load(fm) or {}
        return data, body.strip()
    return {}, text

def md_to_html(text):
    return md.markdown(
        text,
        extensions=[
            "fenced_code",
            "codehilite",
            "tables",
            "toc",
            "attr_list",
            "sane_lists",
            "smarty",
            "admonition",
            "footnotes",
            "def_list",
        ],
        extension_configs={
            "codehilite": {"guess_lang": False, "cssclass": "codehilite"},
            "toc": {"permalink": " "},
        },
        output_format="html5",
    )

def calculate_reading_time(text):
    # Strip HTML tags for word count
    clean_text = re.sub(r'<[^>]+>', '', text)
    words = len(clean_text.split())
    # ~200 wpm
    minutes = max(1, round(words / 200))
    return words, minutes

def render(tpl, **ctx):
    env = Environment(
        loader=FileSystemLoader(TPL_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(tpl)
    return template.render(**ctx)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def copy_static(site):
    # styles.css
    shutil.copy2(ROOT / "static" / "styles.css", DIST / "styles.css")
    # 404.html (static passthrough)
    shutil.copy2(ROOT / "static" / "404.html", DIST / "404.html")

def build_about(site):
    src = ROOT / "about.md"
    if src.exists():
        raw = src.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        html = md_to_html(body)
        out = render("post.html",
                     base_url=site.get("base_url",""),
                     site_name=site["site_name"],
                     author=site["author"],
                     tagline=site.get("tagline",""),
                     title=fm.get("title","about"),
                     description=fm.get("description","about"),
                     content=html,
                     iso_date="",
                     human_date="",
                     year=datetime.date.today().year)
        (DIST / "about.html").write_text(out, encoding="utf-8")

def build_posts(site):
    posts = []
    for p in sorted(SRC_POSTS.glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        title = fm.get("title") or p.stem
        slug = fm.get("slug") or re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-")
        date_str = fm.get("date") or datetime.date.today().isoformat()
        dt = datetime.datetime.fromisoformat(str(date_str))
        human_date = dt.strftime("%b %d, %Y")
        iso_date = dt.date().isoformat()
        html = md_to_html(body)
        word_count, reading_time = calculate_reading_time(html)

        out_html = render("post.html",
                          base_url=site.get("base_url",""),
                          site_name=site["site_name"],
                          author=site["author"],
                          tagline=site.get("tagline",""),
                          title=title + " — " + site["site_name"],
                          description=fm.get("description",""),
                          content=html,
                          iso_date=iso_date,
                          human_date=human_date,
                          word_count=word_count,
                          reading_time=reading_time,
                          year=datetime.date.today().year)

        out_path = DIST / "posts" / f"{slug}.html"
        ensure_dir(out_path.parent)
        out_path.write_text(out_html, encoding="utf-8")

        posts.append({
            "title": title,
            "slug": slug,
            "date": dt,
            "iso_date": iso_date,
            "human_date": human_date,
            "rfc2822": format_datetime(dt),
            "description": fm.get("description",""),
        })
    # new to old
    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts

def build_index(site, posts):
    html = render("index.html",
                  base_url=site.get("base_url",""),
                  site_name=site["site_name"],
                  author=site["author"],
                  tagline=site.get("tagline",""),
                  title=site["site_name"],
                  description=site.get("description",""),
                  posts=posts,
                  work_links=site.get("work_links", []),
                  other_links=site.get("other_links", []),
                  year=datetime.date.today().year)
    (DIST / "index.html").write_text(html, encoding="utf-8")

def build_feed(site, posts):
    xml = render("feed.xml",
                 base_url=site.get("base_url",""),
                 site_name=site["site_name"],
                 description=site.get("description",""),
                 posts=posts)
    (DIST / "feed.xml").write_text(xml, encoding="utf-8")

def main():
    site = load_site()
    if DIST.exists():
        shutil.rmtree(DIST)
    ensure_dir(DIST)

    copy_static(site)
    build_about(site)
    posts = build_posts(site)
    build_index(site, posts)
    build_feed(site, posts)
    print(f"Built {len(posts)} posts → {DIST}")

if __name__ == "__main__":
    main()
