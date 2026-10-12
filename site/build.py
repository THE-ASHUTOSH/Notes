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

        label = html.escape(lang) if lang else ""
        return (
            '<div class="codeblock">'
            + (f'<span class="lang">{label}</span>' if label else "")
            + '<button class="copy" type="button" aria-label="Copy code">Copy</button>'
            + f'<pre class="highlight"><code>{body}</code></pre>'
            "</div>\n"
        )

    def heading_open(self, tokens, idx, options, env):
        token = tokens[idx]
        raw = tokens[idx + 1].content
        hid = gh_slug(raw)
        level = int(token.tag[1])
        if level in (2, 3):
            headings.append((level, hid, strip_trailing_emoji(raw) or raw))
        return f'<{token.tag} id="{html.escape(hid, quote=True)}">'

    def heading_close(self, tokens, idx, options, env):
        tag = tokens[idx].tag
        level = int(tag[1])
        if level <= 4:
            # the matching heading_open is two tokens back
            hid = gh_slug(tokens[idx - 1].content)
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
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("fence", fence)
    md.add_render_rule("heading_open", heading_open)
    md.add_render_rule("heading_close", heading_close)
    md.add_render_rule("link_open", link_open)
    return md, headings


# --------------------------------------------------------------------------- #
# page template
# --------------------------------------------------------------------------- #

INLINE_JS = """
(function(){
  var root=document.documentElement;
  try{var t=localStorage.getItem('theme'); if(t) root.setAttribute('data-theme',t);}catch(e){}
  var b=document.getElementById('theme');
  if(b) b.addEventListener('click',function(){
    var cur=root.getAttribute('data-theme');
    var dark=cur?cur==='dark':matchMedia('(prefers-color-scheme: dark)').matches;
    var next=dark?'light':'dark';
    root.setAttribute('data-theme',next);
    try{localStorage.setItem('theme',next);}catch(e){}
  });
  var f=document.getElementById('filter');
  if(f) f.addEventListener('input',function(){
    var q=f.value.toLowerCase();
    document.querySelectorAll('#nav a').forEach(function(a){
      a.hidden = q && a.textContent.toLowerCase().indexOf(q)===-1;
    });
    document.querySelectorAll('#nav .group').forEach(function(g){
      g.hidden = q && !g.querySelector('a:not([hidden])');
    });
  });
  document.querySelectorAll('.copy').forEach(function(btn){
    btn.addEventListener('click',function(){
      var c=btn.parentElement.querySelector('code');
      navigator.clipboard.writeText(c.innerText).then(function(){
        btn.textContent='Copied'; setTimeout(function(){btn.textContent='Copy';},1500);
      },function(){ btn.textContent='Ctrl+C'; });
    });
  });
})();
"""


def nav_html(sections, depth, active=None):
    up = "../" * depth
    out = []
    for sec in sections:
        out.append('<div class="group">')
        out.append(f'<h2>{html.escape(sec["name"])}'
                   f'<span class="count">{len(sec["notes"]) or ""}</span></h2>')
        if not sec["notes"]:
            out.append('<p class="empty">No notes yet.</p>')
        for n in sec["notes"]:
            cls = ' class="active"' if n is active else ""
            num = f'<span class="num">{html.escape(n.num)}</span>' if n.num else ""
            out.append(f'<a href="{up}{n.href}"{cls}>{num}{html.escape(n.title)}</a>')
        out.append("</div>")
    return "\n".join(out)


def page(sections, depth, title, body, active=None, toc_html="", pager_html=""):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>%F0%9F%93%98</text></svg>">
<link rel="stylesheet" href="{up}assets/style.css">
</head>
<body>
<a class="skip" href="#doc">Skip to content</a>

<header class="topbar">
  <a class="brand" href="{up}index.html">📘 <span>{html.escape(SITE_TITLE)}</span></a>
  <div class="spacer"></div>
  <input id="filter" type="search" placeholder="Filter notes…" aria-label="Filter notes" autocomplete="off">
  <button id="theme" class="icon-btn" type="button" aria-label="Toggle colour theme" title="Toggle theme">🌓</button>
</header>

<div class="layout">
  <nav id="nav" class="sidebar" aria-label="Notes navigation">
{nav_html(sections, depth, active)}
    <p class="nav-foot">Generated from the markdown files in this repository.</p>
  </nav>

  <main id="doc" class="doc">
    <article class="markdown">
{body}
    </article>
{pager_html}
  </main>

{toc_html}
</div>

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
    dark = HtmlFormatter(style="github-dark").get_style_defs(".highlight")
    dark_attr = HtmlFormatter(style="github-dark").get_style_defs(
        ':root[data-theme="dark"] .highlight')
    dark_media = HtmlFormatter(style="github-dark").get_style_defs(
        ':root:not([data-theme="light"]) .highlight')
    return (
        base
        + "\n\n/* ---------- pygments: light ---------- */\n" + light
        + '\n\n/* ---------- pygments: dark ---------- */\n' + dark_attr
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
    for sec in sections:
        for note in sec["notes"]:
            note_dir = os.path.dirname(f'{note.section}/{note.rel}')
            md, headings = make_renderer(note_dir, link_map)
            body = md.render(read(note.src))

            toc = ""
            if len(headings) > 1:
                items = "".join(
                    f'<a class="h{lvl}" href="#{html.escape(hid, quote=True)}">'
                    f"{html.escape(txt)}</a>"
                    for lvl, hid, txt in headings)
                toc = f'<aside class="toc"><h2>On this page</h2>{items}</aside>'

            i = flat.index(note)
            prev_n = flat[i - 1] if i > 0 else None
            next_n = flat[i + 1] if i + 1 < len(flat) else None
            parts = []
            if prev_n:
                parts.append(
                    f'<a class="prev" href="../{prev_n.href}">'
                    f'<span class="label">← Previous</span>'
                    f'<span class="title">{html.escape(prev_n.title)}</span></a>')
            if next_n:
                parts.append(
                    f'<a class="next" href="../{next_n.href}">'
                    f'<span class="label">Next →</span>'
                    f'<span class="title">{html.escape(next_n.title)}</span></a>')
            pager = f'<nav class="pager" aria-label="Previous and next note">{"".join(parts)}</nav>' if parts else ""

            write(os.path.join(outdir, *note.href.split("/")),
                  page(sections, 1, f"{note.title} · {SITE_TITLE}",
                       body, note, toc, pager))

    # --- home --------------------------------------------------------------
    cards = []
    for s in sections:
        target = s["notes"][0].href if s["notes"] else "#"
        count = (f'{len(s["notes"])} note' + ("" if len(s["notes"]) == 1 else "s")
                 if s["notes"] else "Coming soon")
        blurb = f' · {html.escape(s["blurb"])}' if s["blurb"] else ""
        cards.append(f'<a class="home-card" href="{target}">'
                     f'<strong>{html.escape(s["name"])}</strong>'
                     f"<span>{count}{blurb}</span></a>")

    home_body = f"""<h1>📘 {html.escape(SITE_TITLE)}</h1>
<p>Study notes kept as plain markdown in this repository. Every page here is generated from
the same <code>.md</code> file you can read on GitHub.</p>
<div class="home-grid">{''.join(cards)}</div>
<h2 id="tracks">Tracks</h2>
{''.join(
    f'<h3>{html.escape(s["name"])}</h3><ol class="tracklist">' +
    ''.join(f'<li><a href="{n.href}">{html.escape(n.title)}</a></li>' for n in s["notes"]) +
    '</ol>'
    for s in sections if s["notes"])}"""

    write(os.path.join(outdir, "index.html"),
          page(sections, 0, SITE_TITLE, home_body))

    total = len(flat)
    print(f"built {os.path.relpath(outdir, ROOT)} — {total + 1} pages "
          f"({total} notes, {len(sections)} sections)")
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
