# ⚡ S05 · Git & GitHub

> *Revision card.* Full notes → [Session 5](../05_Git_and_GitHub.md)

---

## 🔑 One-line core

***`merge` preserves history, `rebase` rewrites it. `revert` for pushed commits,
`reset` only for local ones.*** And `reflog` saves you.

---

## 🧱 The three areas

```
 working dir  ──git add──▶  staging (index)  ──git commit──▶  repository
      ▲                                                            │
      └────────────── git checkout / restore ──────────────────────┘
```

`git status` tells you which area everything is in. Learn to read it and Git stops being
mysterious.

---

## 🌿 Merge vs Rebase

| | `merge` | `rebase` |
|---|---|---|
| History | **preserved** + merge commit | **rewritten**, linear |
| Safe on | *shared branches* | *your own branches only* |
| Conflicts | once | possibly **per commit** |

> ⚠️ **Never rebase a branch someone else has pulled.**

---

## ↩️ Undoing — pick the right one

| Command | Use when |
|---|---|
| `git revert <sha>` | ⭐ commit is **pushed** — makes a new undo commit |
| `git reset --soft` | undo commit, keep staged |
| `git reset --mixed` | undo commit + unstage (default) |
| `git reset --hard` | ⚠️ **destroys working changes** |
| `git restore <f>` | discard file changes |
| `git reflog` | ⭐ **find "lost" commits** (~90 days) |

---

## 🔗 Remotes

| | |
|---|---|
| `git fetch` | download refs — **changes nothing locally** ✅ safe |
| `git pull` | fetch **+ merge** — touches your files |
| `git push` | upload |
| `git push --force-with-lease` | safer than `--force` |

```bash
git fetch && git log origin/main..HEAD     # what am I about to push?
```

---

## ⚔️ Conflicts

```
<<<<<<< HEAD
my version
=======
their version
>>>>>>> feature
```

Fix → `git add` → `git commit`. *Small, frequent merges make conflicts small.*

---

## 🗺️ Branching strategies

| | |
|---|---|
| **Git Flow** | main · develop · feature · release · hotfix — heavy |
| **GitHub Flow** | main + short-lived branches + PR — ⭐ most teams |
| **Trunk-based** | commit to main behind feature flags |

---

## 🏷️ Tags & SemVer

```
v  MAJOR . MINOR . PATCH
   breaking  feature  fix
```

```bash
git tag -a v1.4.2 -m "..."   &&   git push origin v1.4.2
```

CI releases on tags.

---

## 🚫 `.gitignore` — before the first commit

```gitignore
.env
node_modules/
__pycache__/
*.tfstate
*.log
```

> ⚠️ **A committed secret is in history forever. Rotate it — deleting the line does
> nothing.**

---

## ⚠️ Traps

- `pull` on dirty working tree → mess. `fetch` first.
- `reset --hard` on pushed commits breaks everyone's clone.
- Commit messages like *"fix"* — write *why*, imperative mood.

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Undo a **pushed** commit? | `git revert` |
| Recover a deleted branch? | `git reflog` → `git checkout -b x <sha>` |
| `fetch` vs `pull`? | download vs download **+ merge** |
| Rebase a shared branch? | **never** |
| Secret pushed? | **rotate first**, then clean history |

---

⬅️ [S04](./04_Networking_Fundamentals.md) · ➡️ [S06 · Docker](./06_Docker_Fundamentals.md)
