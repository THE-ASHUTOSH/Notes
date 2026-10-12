#!/usr/bin/env python3
"""Build a plain static HTML site from the markdown notes.

    python site/build.py            -> writes site/dist/
    python site/build.py -o docs    -> writes docs/ instead

Output is ordinary .html + one .css file. No server, no framework, no runtime
markdown parsing: every page is finished HTML, so it works by double-clicking
index.html and deploys to GitHub Pages as-is.

The .md files remain the single source of truth — re-run this after editing them.
"""

import argparse
import html
import io
import os
import re
import shutil
import sys

try:
    from markdown_it import MarkdownIt
except ImportError:
    sys.exit("Missing dependency. Run:  pip install -r site/requirements.txt")

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SITE_TITLE = "Programming Notes"
# Files that are in the repo but not published as pages (site/, .github/ ...)
# link out to GitHub instead of dangling.
REPO_URL = "https://github.com/THE-ASHUTOSH/Notes/blob/main"
SKIP_DIRS = {".git", ".github", "site", "dist", "docs", "node_modules",
             "__pycache__", ".vscode", ".idea"}

BLURBS = {
    "DevOps": "Linux → Docker → Kubernetes → CI/CD → Terraform → GitOps",
    "HLD": "High-level system design",
    "LLD": "Low-level design & OOP",
    "DSA": "Data structures & algorithms",
    "RAG": "Retrieval-augmented generation",
    "Advance JS": "JavaScript internals",
}

# Fence languages Pygments names differently, or has no lexer for.
LANG_ALIAS = {
    "hcl": "terraform", "tf": "terraform",
    "text": None, "promql": None, "gitignore": None, "dockerignore": None,
    "sh": "bash", "shell": "bash", "console": "console",
    "yml": "yaml", "jsx": "javascript", "tsx": "typescript",
}

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
SESSION_RE = re.compile(r"^Session\s+(\d+)\s*[—–-]\s*(.+)$")
NUM_RE = re.compile(r"^(\d+)[_\-. ]+")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def gh_slug(text):
    """GitHub's heading-anchor algorithm, so in-file TOC links keep working."""
    s = text.lower()
    s = re.sub(r"<[^>]*>", "", s)
    s = re.sub(r"[^\w \-]", "", s, flags=re.UNICODE)   # drop punctuation + emoji
    s = re.sub(r"[^a-z0-9 _-]", "", s)                 # drop remaining non-latin
    return s.replace(" ", "-")                         # no trimming: GitHub keeps
                                                       # the hyphen a leading/trailing
                                                       # emoji leaves behind


def url_slug(text):
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s or "x"


def strip_trailing_emoji(s):
    return re.sub(r"\s+[^\w\s().,&/'\"-]+$", "", s).strip()


def read(path):
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #

class Note:
    __slots__ = ("section", "rel", "src", "num", "title", "out", "href")


def title_of(src, filename):
    m = H1_RE.search(read(src)[:4096])
    raw = m.group(1).strip() if m else os.path.splitext(filename)[0].replace("_", " ")
    raw = strip_trailing_emoji(raw)
    num = ""
    sm = SESSION_RE.match(raw)
    if sm:
        num, raw = sm.group(1).zfill(2), sm.group(2).strip()
    else:
        fm = NUM_RE.match(filename)
        if fm:
            num = fm.group(1)
    return num, raw


def discover():
    sections = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        if not os.path.isdir(path) or name in SKIP_DIRS or name.startswith("."):
            continue

        found = []
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            if os.path.isfile(full) and entry.lower().endswith(".md"):
                found.append((entry, full))
            elif os.path.isdir(full) and entry not in SKIP_DIRS:
                for sub in sorted(os.listdir(full)):
                    if sub.lower().endswith(".md"):
                        found.append((f"{entry}/{sub}", os.path.join(full, sub)))

        def sort_key(item):
            rel = item[0]
            leaf = rel.rsplit("/", 1)[-1]
            if leaf.lower() == "readme.md" and "/" not in rel:
                return (0, "", "")
            m = NUM_RE.match(leaf)
            return (1, m.group(1).zfill(4) if m else "zzzz", rel.lower())

        found.sort(key=sort_key)

        sec_slug = url_slug(name)
        notes, used = [], set()
        for rel, full in found:
            leaf = rel.rsplit("/", 1)[-1]
            num, title = title_of(full, leaf)
            if leaf.lower() == "readme.md" and "/" not in rel:
                num, title = "", "Overview"

            base = url_slug(os.path.splitext(rel)[0])
            out, n = base, 2
            while out in used:
                out, n = f"{base}-{n}", n + 1
            used.add(out)

            note = Note()
            note.section, note.rel, note.src = name, rel, full
            note.num, note.title = num, title
            note.out = f"{sec_slug}/{out}.html"
            note.href = note.out
            notes.append(note)

        sections.append({"name": name, "slug": sec_slug,
                         "blurb": BLURBS.get(name, ""), "notes": notes})

    sections.sort(key=lambda s: (0 if s["notes"] else 1, s["name"].lower()))
    return sections


# --------------------------------------------------------------------------- #
# markdown -> html
# --------------------------------------------------------------------------- #

def make_renderer(note_dir, link_map):
    """note_dir: the note's folder, relative to the repo root.
    link_map: repo-relative '<Section>/<file>.md' -> output href ('devops/x.html')."""
    md = MarkdownIt("default")
    headings = []
    seen = {}        # slug -> times used, for GitHub's -1 / -2 suffixes
    stack = []       # resolved ids, so heading_close reuses heading_open's

    def fence(self, tokens, idx, options, env):
        token = tokens[idx]
        info = (token.info or "").strip().split()
        lang = info[0].lower() if info else ""
        lexer_name = LANG_ALIAS.get(lang, lang) if lang else None

        body = None
        if lexer_name:
            try:
                lexer = get_lexer_by_name(lexer_name, stripnl=False)
                body = highlight(token.content, lexer,
                                 HtmlFormatter(nowrap=True))
            except (ClassNotFound, ValueError):
                body = None
        if body is None:
            body = html.escape(token.content)

        # ASCII diagrams and unlabelled blocks get a quieter treatment
        plain = lang in ("", "text", "plaintext")
        label = "" if plain else html.escape(lang)
        return (
            f'<div class="codeblock{" plain" if plain else ""}">'
            '<div class="bar">'
            + (f'<span class="lang">{label}</span>' if label else "")
            + '<button class="copy" type="button" aria-label="Copy code">Copy</button>'
            "</div>"
            + f'<pre class="highlight"><code>{body}</code></pre>'
            "</div>\n"
        )

    def heading_open(self, tokens, idx, options, env):
        token = tokens[idx]
        raw = tokens[idx + 1].content
        base = gh_slug(raw)
        n = seen.get(base, 0)
        seen[base] = n + 1
        hid = base if n == 0 else f"{base}-{n}"
        stack.append(hid)
        level = int(token.tag[1])
        if level in (2, 3):
            headings.append((level, hid, strip_trailing_emoji(raw) or raw))
        return f'<{token.tag} id="{html.escape(hid, quote=True)}">'

    def heading_close(self, tokens, idx, options, env):
        tag = tokens[idx].tag
        level = int(tag[1])
        if level <= 4:
            hid = stack.pop() if stack else ""
            return (f'<a class="anchor" href="#{html.escape(hid, quote=True)}"'
                    f' aria-label="Link to this section">#</a></{tag}>\n')
        return f"</{tag}>\n"

    def link_open(self, tokens, idx, options, env):
        token = tokens[idx]
        href = token.attrGet("href") or ""
        if re.match(r"^(https?:|mailto:)", href, re.I):
            token.attrSet("target", "_blank")
            token.attrSet("rel", "noopener noreferrer")
        elif not href.startswith("#"):
            m = re.match(r"^([^#?]+\.md)(#.*)?$", href, re.I)
            if m:
                key = os.path.normpath(os.path.join(note_dir, m[1])).replace("\\", "/")
                target = link_map.get(key)
                if target:
                    token.attrSet("href", "../" + target + (m[2] or ""))
                else:
                    token.attrSet("href", f"{REPO_URL}/{key}")
                    token.attrSet("target", "_blank")
                    token.attrSet("rel", "noopener noreferrer")
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("fence", fence)
    md.add_render_rule("heading_open", heading_open)
    md.add_render_rule("heading_close", heading_close)
    md.add_render_rule("link_open", link_open)
    return md, headings


INLINE_JS = r"""
(function () {
  var root = document.documentElement;

  /* theme ---------------------------------------------------------------- */
  var btn = document.getElementById('theme');
  if (btn) btn.addEventListener('click', function () {
    var cur = root.getAttribute('data-theme');
    var dark = cur ? cur === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
  });

  /* mobile drawer -------------------------------------------------------- */
  var side = document.getElementById('nav');
  var menu = document.getElementById('menu-btn');
  var scrim = document.getElementById('scrim');
  function drawer(open) {
    if (!side) return;
    side.classList.toggle('open', open);
    if (scrim) scrim.hidden = !open;
    if (menu) menu.setAttribute('aria-expanded', String(open));
  }
  if (menu) menu.addEventListener('click', function () { drawer(!side.classList.contains('open')); });
  if (scrim) scrim.addEventListener('click', function () { drawer(false); });

  /* sidebar filter ------------------------------------------------------- */
  var f = document.getElementById('filter');
  if (f) f.addEventListener('input', function () {
    var q = f.value.trim().toLowerCase();
    document.querySelectorAll('#nav a').forEach(function (a) {
      a.hidden = !!q && a.textContent.toLowerCase().indexOf(q) === -1;
    });
    document.querySelectorAll('#nav .group').forEach(function (g) {
      g.hidden = !!q && !g.querySelector('a:not([hidden])');
    });
  });

  /* copy buttons --------------------------------------------------------- */
  document.querySelectorAll('.copy').forEach(function (b) {
    b.addEventListener('click', function () {
      var c = b.closest('.codeblock').querySelector('code');
      var done = function () {
        b.textContent = 'Copied'; b.classList.add('done');
        setTimeout(function () { b.textContent = 'Copy'; b.classList.remove('done'); }, 1600);
      };
      if (navigator.clipboard) navigator.clipboard.writeText(c.innerText).then(done, function () { b.textContent = 'Ctrl+C'; });
      else b.textContent = 'Ctrl+C';
    });
  });

  /* reading progress + table-of-contents scroll-spy ---------------------- */
  var bar = document.getElementById('progress');
  var links = [].slice.call(document.querySelectorAll('.toc a'));
  var heads = links.map(function (a) { return document.getElementById(decodeURIComponent(a.hash.slice(1))); });
  var ticking = false;

  function onScroll() {
    if (bar) {
      var h = document.documentElement.scrollHeight - innerHeight;
      bar.style.width = (h > 0 ? Math.min(100, (scrollY / h) * 100) : 0) + '%';
    }
    if (links.length) {
      var best = 0;
      for (var i = 0; i < heads.length; i++) {
        if (heads[i] && heads[i].getBoundingClientRect().top <= 120) best = i;
      }
      links.forEach(function (a, i) { a.classList.toggle('active', i === best); });
      var act = links[best];
      if (act && act.offsetParent) {
        var box = act.closest('.toc');
        var top = act.offsetTop - box.offsetTop;
        if (top < box.scrollTop || top > box.scrollTop + box.clientHeight - 40) {
          box.scrollTop = top - box.clientHeight / 2;
        }
      }
    }
    ticking = false;
  }
  addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  /* keyboard ------------------------------------------------------------- */
  addEventListener('keydown', function (e) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
    if (e.key === '/' && !typing) { e.preventDefault(); if (f) { f.focus(); f.select(); } return; }
    if (e.key === 'Escape') { if (typing) e.target.blur(); drawer(false); return; }
    if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
    var go = function (sel) { var a = document.querySelector(sel); if (a) location.href = a.href; };
    if (e.key === 'ArrowLeft') go('.pager a.prev');
    if (e.key === 'ArrowRight') go('.pager a.next');
  });
})();
"""

# Keep the theme flash-free: this runs before the stylesheet paints.
THEME_BOOT = ("<script>try{var t=localStorage.getItem('theme');"
              "if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}</script>")

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Inter:wght@400;500;600;700;800&'
    'family=JetBrains+Mono:wght@400;500;600&display=swap">'
)

# One accent colour per section, so the sidebar and cards are scannable.
SECTION_HUES = {
    "DevOps": "#6366f1",
    "HLD": "#0ea5e9",
    "LLD": "#14b8a6",
    "DSA": "#f59e0b",
    "RAG": "#ec4899",
    "Advance JS": "#eab308",
}
HUE_CYCLE = ["#6366f1", "#0ea5e9", "#14b8a6", "#f59e0b", "#ec4899", "#eab308", "#8b5cf6"]


def hue_for(name, i):
    return SECTION_HUES.get(name, HUE_CYCLE[i % len(HUE_CYCLE)])


# --------------------------------------------------------------------------- #
# html post-processing
# --------------------------------------------------------------------------- #

CALLOUTS = [
    ("⭐", "star"),      # ⭐
    ("⚠", "warn"),      # ⚠️
    ("\U0001f4a1", "tip"),   # 💡
    ("\U0001f41b", "bug"),   # 🐛
    ("\U0001f4b0", "cost"),  # 💰
    ("\U0001f4cc", "tip"),   # 📌
]


def decorate(body):
    """Turn plain markdown output into the richer markup the stylesheet expects."""

    # 1. tables need a scroll container so wide ones don't blow out the column
    body = re.sub(r"<table>", '<div class="table-wrap"><table>', body)
    body = re.sub(r"</table>", "</table></div>", body)

    # 2. emoji-led blockquotes become labelled callouts
    def as_callout(m):
        inner = m.group(1)
        head = re.sub(r"<[^>]+>", "", inner).lstrip()
        for marker, cls in CALLOUTS:
            if head.startswith(marker):
                return f'<blockquote class="callout {cls}">{inner}</blockquote>'
        return m.group(0)

    body = re.sub(r"<blockquote>(.*?)</blockquote>", as_callout, body, flags=re.S)

    # 3. the opening "Topics / Repo" quote is the page lede
    body = re.sub(r"<blockquote>(\s*<p><strong>Topics:</strong>)",
                  r'<blockquote class="lede">\1', body, count=1)

    return body


# --------------------------------------------------------------------------- #
# page template
# --------------------------------------------------------------------------- #

def nav_html(sections, depth, active=None):
    up = "../" * depth
    out = []
    for i, sec in enumerate(sections):
        out.append(f'<div class="group" style="--sec:{hue_for(sec["name"], i)}">')
        out.append(f'<h2>{html.escape(sec["name"])}'
                   f'<span class="count">{len(sec["notes"]) or "—"}</span></h2>')
        if not sec["notes"]:
            out.append('<p class="empty">Coming soon</p>')
        for n in sec["notes"]:
            cls = ' class="active"' if n is active else ""
            num = f'<span class="num">{html.escape(n.num)}</span>' if n.num else '<span class="num"></span>'
            out.append(f'<a href="{up}{n.href}"{cls}>{num}'
                       f'<span>{html.escape(n.title)}</span></a>')
        out.append("</div>")
    return "\n".join(out)


def page(sections, depth, title, body, active=None, toc_html="", pager_html="",
         body_class=""):
    up = "../" * depth
    desc = ("Study notes on DevOps, system design and more — kept as markdown, "
            "published as a readable site.")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>%F0%9F%93%98</text></svg>">
{FONTS}
<link rel="stylesheet" href="{up}assets/style.css">
{THEME_BOOT}
</head>
<body class="{body_class}">
<a class="skip" href="#doc">Skip to content</a>
<div id="progress" class="progress"></div>

<header class="topbar">
  <button id="menu-btn" class="icon-btn" type="button" aria-label="Toggle navigation" aria-expanded="false">&#9776;</button>
  <a class="brand" href="{up}index.html"><span class="logo">&#128218;</span><span class="name">{html.escape(SITE_TITLE)}</span></a>
  <div class="spacer"></div>
  <input id="filter" type="search" placeholder="Filter notes&hellip;  /" aria-label="Filter notes" autocomplete="off">
  <button id="theme" class="icon-btn" type="button" aria-label="Toggle colour theme" title="Toggle theme">&#9681;</button>
</header>

<div class="layout">
  <nav id="nav" class="sidebar" aria-label="Notes navigation">
{nav_html(sections, depth, active)}
    <p class="nav-foot"><kbd>/</kbd> filter &middot; <kbd>&larr;</kbd><kbd>&rarr;</kbd> move between notes<br>
    Generated from the markdown in this repository.</p>
  </nav>

  <main id="doc" class="doc">
    <article class="markdown">
{body}
    </article>
{pager_html}
  </main>

{toc_html}
</div>

<div id="scrim" class="scrim" hidden></div>
<script>{INLINE_JS}</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# css
# --------------------------------------------------------------------------- #

def build_css():
    base = read(os.path.join(HERE, "style.css"))
    light = HtmlFormatter(style="default").get_style_defs(".highlight")
    dark_attr = HtmlFormatter(style="github-dark").get_style_defs(
        ':root[data-theme="dark"] .highlight')
    dark_media = HtmlFormatter(style="github-dark").get_style_defs(
        ':root:not([data-theme="light"]) .highlight')
    return (
        base
        + "\n\n/* ---------- pygments: light ---------- */\n" + light
        + "\n\n/* ---------- pygments: dark ---------- */\n" + dark_attr
        + "\n\n@media (prefers-color-scheme: dark) {\n" + dark_media + "\n}\n"
    )


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def build(outdir):
    sections = discover()
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)

    write(os.path.join(outdir, "assets", "style.css"), build_css())
    write(os.path.join(outdir, ".nojekyll"), "")

    flat = [n for s in sections for n in s["notes"]]

    # Every note, keyed by its path relative to the repo root, so links can
    # cross sections (e.g. HLD/README.md -> ../DevOps/README.md).
    link_map = {f'{n.section}/{n.rel}': n.href for n in flat}

    # --- notes -------------------------------------------------------------
    for si, sec in enumerate(sections):
        hue = hue_for(sec["name"], si)
        for note in sec["notes"]:
            note_dir = os.path.dirname(f'{note.section}/{note.rel}')
            md, headings = make_renderer(note_dir, link_map)
            body = decorate(md.render(read(note.src)))

            toc = ""
            if len(headings) > 1:
                items = "".join(
                    f'<a class="h{lvl}" href="#{html.escape(hid, quote=True)}">'
                    f"{html.escape(txt)}</a>"
                    for lvl, hid, txt in headings)
                toc = ('<aside class="toc" aria-label="On this page">'
                       f"<h2>On this page</h2><nav>{items}</nav></aside>")

            i = flat.index(note)
            prev_n = flat[i - 1] if i > 0 else None
            next_n = flat[i + 1] if i + 1 < len(flat) else None
            parts = []
            if prev_n:
                parts.append(
                    f'<a class="prev" href="../{prev_n.href}">'
                    f'<span class="label">&larr; Previous</span>'
                    f'<span class="title">{html.escape(prev_n.title)}</span></a>')
            if next_n:
                parts.append(
                    f'<a class="next" href="../{next_n.href}">'
                    f'<span class="label">Next &rarr;</span>'
                    f'<span class="title">{html.escape(next_n.title)}</span></a>')
            pager = (f'<nav class="pager" aria-label="Previous and next note">'
                     f'{"".join(parts)}</nav>') if parts else ""

            write(os.path.join(outdir, *note.href.split("/")),
                  page(sections, 1, f"{note.title} · {SITE_TITLE}",
                       body, note, toc, pager))

    # --- home --------------------------------------------------------------
    cards = []
    for i, s in enumerate(sections):
        hue = hue_for(s["name"], i)
        target = s["notes"][0].href if s["notes"] else "#tracks"
        count = (f'{len(s["notes"])} note' + ("" if len(s["notes"]) == 1 else "s")
                 if s["notes"] else "Coming soon")
        soon = "" if s["notes"] else " soon"
        blurb = (f'<span class="b">{html.escape(s["blurb"])}</span>'
                 if s["blurb"] else "")
        cards.append(
            f'<a class="home-card{soon}" href="{target}" style="--sec:{hue}">'
            f'<span class="n">{count}</span>'
            f'<strong>{html.escape(s["name"])}</strong>{blurb}</a>')

    tracks = []
    for i, s in enumerate(sections):
        if not s["notes"]:
            continue
        hue = hue_for(s["name"], i)
        items = "".join(
            f'<li><a href="{n.href}"><span class="num">{html.escape(n.num) or "&bull;"}</span>'
            f'<span>{html.escape(n.title)}</span></a></li>' for n in s["notes"])
        tracks.append(f'<section class="track" style="--sec:{hue}">'
                      f'<h3>{html.escape(s["name"])}</h3>'
                      f'<ul class="tracklist">{items}</ul></section>')

    n_notes = len(flat)
    n_secs = sum(1 for s in sections if s["notes"])
    words = sum(len(read(n.src).split()) for n in flat)

    home_body = f"""<header class="hero">
<h1>Programming Notes</h1>
<p>Long-form study notes on DevOps, system design and the rest &mdash; written as plain
markdown in this repository, published here as something nicer to read.</p>
<div class="stats">
  <span class="stat"><b>{n_notes}</b> notes</span>
  <span class="stat"><b>{n_secs}</b> tracks</span>
  <span class="stat"><b>{words // 1000}k</b> words</span>
</div>
</header>

<div class="home-grid">{''.join(cards)}</div>

<h2 id="tracks">Everything, in order</h2>
{''.join(tracks)}"""

    write(os.path.join(outdir, "index.html"),
          page(sections, 0, SITE_TITLE, home_body, body_class="home"))

    print(f"built {os.path.relpath(outdir, ROOT)} — {n_notes + 1} pages "
          f"({n_notes} notes, {len(sections)} sections, ~{words // 1000}k words)")
    for s in sections:
        print(f"  {s['name']:<12} {len(s['notes'])}")

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "dist"),
                    help="output directory (default: site/dist)")
    args = ap.parse_args()
    build(os.path.abspath(args.out))


if __name__ == "__main__":
    main()
