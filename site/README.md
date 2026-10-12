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
| **Sidebar** | Every section and note, with the current one highlighted |
| **Table of contents** | Per page, built from the `##` / `###` headings |
| **Prev / next** | Follows the course order |
| **Syntax highlighting** | Done at build time by Pygments — bash, YAML, Dockerfile, HCL/Terraform, Python, nginx, JSON… |
| **GitHub-compatible anchors** | `#-session-takeaways` resolves the same here as on GitHub, so in-note TOC links work |
| **Rewritten links** | `./15_Helm.md` becomes `15-helm.html`, including links that cross sections |
| **Dark / light** | Follows the system setting; the header button overrides it |
| **Responsive & printable** | Sidebar collapses on narrow screens; print CSS drops the chrome |

Sections with no markdown in them are listed as *Coming soon* rather than hidden.

### JavaScript

There is about 25 lines of inline JS for three conveniences: the theme toggle, the sidebar
filter box, and the copy-to-clipboard buttons. **The site is fully usable without it** — all
content, navigation and highlighting are plain HTML and CSS.

There is no full-text search; the sidebar filter matches note titles. Use GitHub's own search
for content.

---

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
