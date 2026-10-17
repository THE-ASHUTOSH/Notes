# site/ — the notes as a plain HTML site

A static-site generator that turns the repository's markdown notes into **ordinary `.html`
files plus one `.css` file**. No framework, no runtime markdown parsing, no server required:
every page is finished HTML, so it opens by double-clicking and deploys to GitHub Pages as-is.

The `.md` files stay the single source of truth — nothing here duplicates content.

```
site/
├── build.py          the generator
├── requirements.txt  markdown-it-py + Pygments
├── style.css         base stylesheet (Pygments colours are appended at build time)
└── dist/             generated output — gitignored, never edit by hand
```

---

## Run it locally

```bash
pip install -r site/requirements.txt    # once
python site/build.py
```

Then just open the file — no web server needed:

```bash
# Windows
start site\dist\index.html
# macOS
open site/dist/index.html
# Linux
xdg-open site/dist/index.html
```

Re-run `python site/build.py` after editing any note. Output goes somewhere else with `-o`:

```bash
python site/build.py --out _site
python site/build.py --out docs      # if you prefer the "deploy from /docs" Pages mode
```

---

## Deploy on GitHub Actions

`.github/workflows/pages.yml` is already set up. One-time repository setting:

> **Settings → Pages → Build and deployment → Source → GitHub Actions**

Then every push to `main` that touches a `.md` file or `site/` rebuilds and publishes to
`https://<user>.github.io/<repo>/`. You can also trigger it by hand from the **Actions** tab
(*Deploy notes site* → *Run workflow*).

What the workflow does:

```
checkout → setup-python → pip install -r site/requirements.txt
        → python site/build.py --out _site
        → upload-pages-artifact → deploy-pages
```

Nothing generated is committed; the artifact is built fresh each run.

---

## What you get

| | |
|---|---|
| **One page per note** | `dist/devops/14-kubernetes-troubleshooting.html` |
| **Callouts** | `> ⭐` / `> ⚠️` / `> 💡` / `> 🐛` / `> 💰` blockquotes render as labelled, colour-coded boxes — *Key point*, *Watch out*, *Note*, *Bug in source*, *Costs money* |
| **Session header** | The opening `> **Topics:** … 📁 Repo:` block becomes a tinted lede card |
| **Sidebar** | Every section and note, each track with its own accent colour, current page marked |
| **Contents** | Per-page, built from `##` / `###`, with scroll-spy highlighting the section you're reading |
| **Reading progress** | A thin bar across the top of the page |
| **Syntax highlighting** | Build-time Pygments — bash, YAML, Dockerfile, HCL/Terraform, Python, nginx, JSON… ASCII diagrams get a quieter treatment |
| **Tables** | Scroll containers with sticky headers, so the wide reference tables stay usable |
| **Prev / next** | Follows the course order; `←` / `→` on the keyboard |
| **Anchors** | GitHub-compatible, including `-1` / `-2` suffixes for repeated headings, so in-note TOC links work in both places |
| **Rewritten links** | `./15_Helm.md` becomes `15-helm.html`, including links that cross sections; anything not published as a page falls back to GitHub |
| **Dark / light** | Follows the system setting; the header button overrides it, remembered per browser |
| **Typography** | Inter and JetBrains Mono from Google Fonts, with full system fallbacks |
| **Short notes** | A `Short Notes/` sub-folder in any section becomes its own group in the sidebar, and its pages render on ruled paper in a handwritten face (Caveat) — tables and code stay in the normal legible fonts |
| **Responsive & printable** | Sidebar becomes a drawer on narrow screens; print CSS drops the chrome |

Sections with no markdown in them are listed as *Coming soon* rather than hidden.

### JavaScript

Roughly 90 lines of inline JS cover the theme toggle, the sidebar filter and drawer, the
copy buttons, the reading-progress bar, scroll-spy and keyboard shortcuts. **The site is
fully usable without it** — all content, navigation, highlighting and layout are plain HTML
and CSS.

There is no full-text search; the sidebar filter matches note titles. Use GitHub's own
search for content.

## Adding a new note

Drop a `.md` file into any top-level folder and re-run the build. `build.py` discovers
sections and notes automatically:

- Top-level folders become sections (one level of sub-folders is also scanned).
- The title comes from the file's `# H1`; `Session 7 — Docker Images` becomes number `07`,
  title *Docker Images*.
- `README.md` sorts first in its section and is labelled *Overview*.
- Everything else sorts by its numeric filename prefix, then alphabetically.

To change a section's one-line description, edit `BLURBS` at the top of `build.py`.

---

## Dependencies

- [markdown-it-py](https://markdown-it-py.readthedocs.io/) — CommonMark + GFM tables
- [Pygments](https://pygments.org/) — build-time syntax highlighting
