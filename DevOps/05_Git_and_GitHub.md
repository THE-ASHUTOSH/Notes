# Session 5 — Git & GitHub 🌿

> Git is the **source of truth** for everything in DevOps: application code, Dockerfiles,
> Kubernetes manifests, Terraform configs, CI/CD pipeline definitions. Every pipeline in later
> sessions is triggered by a **Git commit**, and GitOps takes this to its logical conclusion —
> *if it isn't in Git, it doesn't exist.*

---

## 📑 Table of Contents
1. [Git vs GitHub](#-git-vs-github)
2. [Why Version Control](#-why-version-control)
3. [How Git Works — The Three Areas](#-how-git-works--the-three-areas)
4. [Setup & Configuration](#-setup--configuration)
5. [Repository & Commits](#-repository--commits)
6. [Inspecting History](#-inspecting-history)
7. [Undoing Things](#-undoing-things)
8. [.gitignore](#-gitignore)
9. [Branching](#-branching)
10. [Merge vs Rebase](#-merge-vs-rebase)
11. [Merge Conflicts](#-merge-conflicts)
12. [Remotes: push, pull, fetch](#-remotes-push-pull--fetch)
13. [Pull Requests](#-pull-requests)
14. [Basic Git Workflow](#-the-basic-git-workflow)
15. [Branching Strategies](#-branching-strategies)
16. [Tags & Releases](#-tags--releases)
17. [Stash, Cherry-pick & Other Tools](#-stash-cherry-pick--other-useful-tools)
18. [Git in DevOps / CI-CD](#-git-in-the-devops-pipeline)
19. [Best Practices](#-best-practices)
20. [Cheat Sheet](#-quick-cheat-sheet)

---

## ⚖️ Git vs GitHub

These are constantly confused — and it's a standard interview question.

| | **Git** | **GitHub** |
|---|---|---|
| **What it is** | A **distributed version control system (DVCS)** — a *tool* | A **cloud hosting platform** for Git repositories — a *service* |
| **Where it runs** | **Locally**, on your machine (a CLI program) | On the **internet** (a website + API) |
| **Created** | 2005, by Linus Torvalds (for the Linux kernel) | 2008; owned by Microsoft since 2018 |
| **Needs internet?** | ❌ No — commit, branch, merge, view history all work offline | ✅ Yes |
| **Purpose** | Track changes, manage versions, branch and merge | Store remote copies, **collaborate**, review code, automate |
| **Alternatives** | Mercurial, SVN, Perforce | GitLab, Bitbucket, Azure Repos, Gitea |
| **Extras** | — | Pull Requests, Issues, Actions (CI/CD), Projects, Packages, Wiki, Releases, code scanning |

> 🧠 **Analogy:** **Git** is the camera; **GitHub** is Instagram.
> Git takes and stores the snapshots; GitHub is where you share them and people comment.

**Key insight — Git is *distributed*:** every clone is a **full copy** of the entire history, not
a thin checkout. That's why Git is fast offline and why there's no single point of failure.

---

## 🎯 Why Version Control

| Problem without VCS | What Git gives you |
|---|---|
| `report_final_v2_FINAL_actually_final.docx` | One linear, named history of every change |
| "Who broke this and when?" | `git log`, `git blame`, `git bisect` |
| "Can we go back to last Tuesday?" | `git checkout <commit>`, `git revert` |
| Two people editing the same file | Branching + merging (with conflict resolution) |
| "What exactly changed?" | `git diff` |
| Experimenting risks breaking main | Cheap, isolated branches |
| Manual code review over email | Pull Requests with inline comments |
| No audit trail for production changes | Every change is a signed, attributed commit ⭐ |

---

## 🧱 How Git Works — The Three Areas

Understanding this diagram makes 90% of Git commands obvious.

```
┌──────────────┐   git add    ┌──────────────┐  git commit  ┌──────────────┐   git push   ┌──────────────┐
│              │ ───────────▶ │              │ ───────────▶ │              │ ───────────▶ │              │
│  WORKING     │              │   STAGING    │              │    LOCAL     │              │   REMOTE     │
│  DIRECTORY   │              │  AREA (Index)│              │  REPOSITORY  │              │  (GitHub)    │
│              │ ◀─────────── │              │ ◀─────────── │   (.git/)    │ ◀─────────── │              │
└──────────────┘  git restore └──────────────┘  git reset   └──────────────┘ git pull/fetch└──────────────┘
   your files                 "what goes in           committed snapshots
   as you edit                 the next commit"        (with full history)
```

| Area | What it is | Check it with |
|---|---|---|
| **Working directory** | The actual files on disk you're editing | `git status`, `git diff` |
| **Staging area (index)** | A "shopping basket" of changes selected for the next commit ⭐ | `git status`, `git diff --staged` |
| **Local repository** | The `.git/` folder — all commits, branches, history | `git log` |
| **Remote repository** | The copy on GitHub/GitLab | `git remote -v` |

**Why a staging area?** It lets you commit **logically related** changes only. You may have fixed
a bug *and* renamed a variable — stage and commit them separately for a clean history.

**File states**
```
Untracked ──git add──▶ Staged ──git commit──▶ Unmodified ──edit──▶ Modified ──git add──▶ Staged ...
```

---

## ⚙️ Setup & Configuration

```bash
git --version

# ---- Identity (REQUIRED — appears in every commit) ----
git config --global user.name  "THE-ASHUTOSH"
git config --global user.email "ashutosh.kumar@scalerailabs.com"

# ---- Useful defaults ----
git config --global init.defaultBranch main       # ⭐ 'main' instead of 'master'
git config --global core.editor "code --wait"     # VS Code for commit messages
git config --global pull.rebase false             # merge on pull (or `true` to rebase)

# ---- Windows line endings (important!) ----
git config --global core.autocrlf input   # ⭐ store LF in the repo, avoids CRLF in .sh files

# ---- Inspect ----
git config --list                    # all settings
git config --list --show-origin      # where each setting comes from
git config user.email                # one value
```
Scopes, narrowest wins: `--local` (this repo, `.git/config`) → `--global` (this user, `~/.gitconfig`)
→ `--system` (all users).

**Handy aliases**
```bash
git config --global alias.st  status
git config --global alias.co  checkout
git config --global alias.br  branch
git config --global alias.lg  "log --oneline --graph --decorate --all"
# now: git lg
```

**Authentication to GitHub**
| Method | Notes |
|---|---|
| **HTTPS + Personal Access Token (PAT)** | Password auth is dead; generate a PAT and use it as the password |
| **SSH keys** ⭐ | `ssh-keygen -t ed25519 -C "you@example.com"` → add `~/.ssh/id_ed25519.pub` to GitHub → test with `ssh -T git@github.com` |
| **GitHub CLI** | `gh auth login` handles it interactively |

---

## 📁 Repository & Commits

### Creating a repository
```bash
# Option A — start locally
mkdir myproject && cd myproject
git init                      # ⭐ creates the .git/ directory
git remote add origin https://github.com/USER/myproject.git
git push -u origin main       # -u sets the upstream so later `git push` needs no args

# Option B — start from an existing remote
git clone https://github.com/USER/repo.git
git clone git@github.com:USER/repo.git          # via SSH
git clone --depth 1 https://.../repo.git        # ⭐ shallow clone (fast, CI-friendly)
git clone <url> myfolder                        # clone into a specific folder
git clone -b develop <url>                      # clone a specific branch
```

### Making commits
```bash
git status                    # ⭐ your most-used command
git status -s                 # short format

git add file.txt              # stage one file
git add .                     # ⭐ stage everything in the current dir & below
git add -A                    # stage everything in the repo (incl. deletions)
git add *.js                  # by pattern
git add -p                    # ⭐ interactively stage HUNKS of a file — great for clean commits

git commit -m "feat: add user login endpoint"
git commit -m "title" -m "longer body explaining WHY"
git commit -am "message"      # add (tracked files only) + commit in one step
git commit --amend            # ⭐ fix the LAST commit (message or forgotten file)
git commit --amend --no-edit  # amend keeping the same message
```

### Commit message convention (Conventional Commits)
```
<type>(<optional scope>): <short imperative summary>

<optional body — WHY, not what>

<optional footer — BREAKING CHANGE:, Closes #123>
```
| Type | Use for |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Restructuring without behaviour change |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `chore` | Build process, dependencies, tooling |
| `ci` | CI/CD configuration |

```
✅ feat(auth): add JWT refresh token endpoint
✅ fix(docker): bind server to 0.0.0.0 so the port mapping works
❌ update stuff
❌ asdf
❌ fixed it
```
> 💡 This convention is what enables **automated semantic versioning and changelogs** in CI.
> (Your notes repo already uses it: `feat:`, `docs:`.)

### What a commit actually is
```
commit 9088568...
├── SHA-1/SHA-256 hash   ← unique ID (the "commit id")
├── author + committer + timestamps
├── commit message
├── parent commit(s)     ← 2 parents = a merge commit
└── tree                 ← a full SNAPSHOT of the project at that moment
```
Git stores **snapshots**, not diffs (diffs are computed on demand). Commits are **immutable** —
"editing" one (amend/rebase) actually creates a *new* commit with a new hash.

**Pointers you'll see constantly**
| Ref | Meaning |
|---|---|
| `HEAD` | ⭐ The commit you're currently on (usually via a branch) |
| `HEAD~1` / `HEAD^` | One commit before HEAD |
| `HEAD~3` | Three commits back |
| `main` | The tip of the `main` branch |
| `origin/main` | Your **last-known** state of `main` on the remote |

---

## 🔍 Inspecting History

```bash
git log                              # full history
git log --oneline                    # ⭐ one line per commit
git log --oneline --graph --decorate --all    # ⭐⭐ visual branch graph
git log -5                           # last 5 commits
git log -p                           # with the actual diffs
git log --stat                       # files changed + counts
git log --author="THE-ASHUTOSH"
git log --since="2 weeks ago" --until="yesterday"
git log --grep="docker"              # search commit MESSAGES
git log -S "functionName"            # ⭐ search commits that added/removed CODE
git log main..feature                # commits in feature but not in main
git log --follow file.txt            # history across renames

git show <commit>                    # full details + diff of one commit
git show HEAD                        # the latest commit
git show HEAD:path/to/file           # a file's content at that commit

git diff                             # working dir vs staging (unstaged changes)
git diff --staged                    # ⭐ staging vs last commit (what you're about to commit)
git diff HEAD                        # everything vs last commit
git diff main feature                # compare two branches
git diff <c1> <c2> -- file.txt       # one file between two commits

git blame file.txt                   # ⭐ who last changed each line, and in which commit
git bisect start                     # ⭐ binary-search history to find the commit that broke it
git shortlog -sn                     # commit counts per author
git reflog                           # ⭐⭐ log of everywhere HEAD has been — your safety net
```

> 🛟 **`git reflog` is the undo of last resort.** Even after a bad `reset --hard` or a deleted
> branch, the commits are still there for ~90 days. Find the hash in the reflog and
> `git reset --hard <hash>` or `git checkout -b recovered <hash>`.

---

## ↩️ Undoing Things

This is where people panic — the key is knowing **which of the three areas** you want to change.

```bash
# ---- Unstage (keep the edits) ----
git restore --staged file.txt        # ⭐ modern
git reset HEAD file.txt              # older equivalent

# ---- Discard local edits (⚠️ DESTRUCTIVE) ----
git restore file.txt                 # ⭐ modern
git checkout -- file.txt             # older equivalent
git restore .                        # discard ALL uncommitted changes

# ---- Fix the last commit ----
git commit --amend -m "better message"
git commit --amend --no-edit         # add a forgotten file to the last commit

# ---- Undo commits ----
git reset --soft HEAD~1     # ⭐ undo commit, KEEP changes STAGED
git reset --mixed HEAD~1    # ⭐ undo commit, keep changes UNSTAGED (default)
git reset --hard HEAD~1     # ⚠️ undo commit AND DELETE the changes — no recovery via files

# ---- Undo a PUSHED commit safely ----
git revert <commit>         # ⭐⭐ creates a NEW commit that reverses it (history preserved)
git revert HEAD             # revert the most recent commit
git revert -m 1 <merge-sha> # revert a merge commit

# ---- Clean untracked files ----
git clean -n                # dry run — show what WOULD be deleted
git clean -fd               # ⚠️ delete untracked files (-f) and directories (-d)
```

### `reset` vs `revert` vs `restore` — the decision table
| Command | Changes history? | Safe on a shared/pushed branch? | Use when |
|---|---|---|---|
| **`git restore`** | No | ✅ Yes | Throw away uncommitted file changes |
| **`git reset`** | ✅ Yes (rewrites) | ❌ **No** | Clean up **local, unpushed** commits |
| **`git revert`** | No (adds a commit) | ✅ **Yes** | Undo something already **pushed** ⭐ |

> ⚠️ **Golden rule:** **never rewrite history that others have pulled.** On `main`/shared branches,
> always use `revert`. `reset`/`rebase`/`--force` belong on your own private feature branches.

---

## 🚫 .gitignore

Tells Git which files to **never track**. Put it at the repo root and **commit it**.

```gitignore
# --- Dependencies ---
node_modules/
venv/
__pycache__/
*.pyc

# --- Build output ---
dist/
build/
target/
*.jar
*.class

# --- Secrets ⭐ NEVER COMMIT THESE ---
.env
.env.*
*.pem
*.key
credentials.json
secrets.yaml
terraform.tfstate
terraform.tfstate.backup
.terraform/

# --- Logs & temp ---
*.log
logs/
tmp/
*.tmp

# --- OS / editor noise ---
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp
```

```bash
# Already committed something you shouldn't have?
git rm --cached .env          # ⭐ untrack it but keep it on disk
echo ".env" >> .gitignore
git commit -m "chore: stop tracking .env"

git check-ignore -v file      # why is this file ignored?
```

> 🚨 **Committed a secret? Rotate it immediately.** Removing the file in a later commit does
> **not** remove it from history — anyone can `git show` the old commit. Revoke/regenerate the
> credential, then optionally scrub history with `git filter-repo` or BFG.
> Prevention: **secret scanning** (Gitleaks, GitHub secret scanning) in CI — see the DevSecOps session.

Related: **`.dockerignore`** does the same job for Docker build contexts (Session 7).

---

## 🌿 Branching

> A **branch is just a movable pointer to a commit.** Creating one is instant and costs ~40 bytes —
> which is why Git workflows are branch-heavy.

```
                    ┌── C4 ── C5   ← feature/login (HEAD)
                    │
  C1 ── C2 ── C3 ───┤
                    │
                    └── C6         ← main
```

### Why branch?
- Develop features **in isolation** without destabilising `main`
- Keep `main` always **deployable**
- Enable **parallel work** by many people
- Provide a natural unit for **code review** (a PR = a branch)

### Commands
```bash
git branch                          # list local branches (* = current)
git branch -a                       # include remote-tracking branches
git branch -v                       # with the last commit on each
git branch --merged                 # branches already merged (safe to delete)

git branch feature/login            # create (but stay put)
git checkout feature/login          # switch
git checkout -b feature/login       # ⭐ create + switch (most used)
git switch -c feature/login         # ⭐ modern equivalent of the above
git switch main                     # modern `checkout` for branches
git checkout -                      # jump back to the previous branch

git branch -m old-name new-name     # rename
git branch -d feature/login         # delete (refuses if unmerged) ⭐ safe
git branch -D feature/login         # ⚠️ force delete
git push origin --delete feature/login   # delete the REMOTE branch

git checkout <commit-hash>          # ⚠️ "detached HEAD" — inspect only
```

### Naming conventions
```
feature/user-authentication      fix/login-redirect-loop
bugfix/JIRA-123-null-pointer     hotfix/payment-gateway-timeout
release/v1.2.0                   chore/upgrade-node-24
docs/api-reference               ci/add-trivy-scan
```
Keep them lowercase, hyphenated, descriptive, and prefix by type.

---

## 🔀 Merge vs Rebase

Both integrate changes from one branch into another — with very different **history shapes**.

### `git merge`
Joins two histories, creating a **merge commit** with two parents.

```
Before:                          After `git merge feature` on main:

      C4──C5  feature                  C4────C5
     /                                /        \
C1──C2──C3  main                C1──C2──C3──────M   main
                                                ↑ merge commit (2 parents)
```
```bash
git checkout main
git pull origin main                # ⭐ get the latest first
git merge feature/login
git merge --no-ff feature/login     # ⭐ always create a merge commit (preserves the branch shape)
git merge --squash feature/login    # combine ALL the branch's commits into one staged change
git merge --abort                   # bail out of a conflicted merge
```
**Fast-forward:** if `main` hasn't moved since the branch was created, Git just slides the pointer
forward — no merge commit at all.

### `git rebase`
**Replays** your commits on top of another branch, creating a **linear** history.

```
Before:                          After `git rebase main` on feature:

      C4──C5  feature                          C4'──C5'  feature
     /                                        /
C1──C2──C3  main                C1──C2──C3───┘   main
                                (C4/C5 are REWRITTEN with new hashes)
```
```bash
git checkout feature/login
git rebase main                     # replay my commits on top of the latest main
git rebase --continue               # after resolving a conflict
git rebase --skip
git rebase --abort                  # ⭐ get back to where you started
git pull --rebase origin main       # ⭐ rebase instead of merging on pull
```

### Comparison
| | **Merge** | **Rebase** |
|---|---|---|
| History | Preserved exactly (branchy) | **Rewritten** (linear) ⭐ |
| Extra commit | Creates a merge commit | No merge commit |
| Commit hashes | Unchanged | **Changed** (new commits) |
| `git log` readability | Shows the true story, can get noisy | Clean and linear |
| Safety on shared branches | ✅ Safe | ⚠️ **Dangerous** |
| Conflict resolution | Once, in the merge commit | Possibly **per replayed commit** |
| Traceability | Full audit trail | Loses the "when it branched" context |

### When to use which
```
✅ MERGE   — integrating a feature branch into main/shared branches
             (and always for anything already pushed & shared)
✅ REBASE  — updating YOUR OWN feature branch with the latest main
             cleaning up local commits before opening a PR
❌ NEVER   — rebase a branch that other people have already pulled
```

> ⚠️ **The Golden Rule of Rebasing:** *never rebase commits that exist outside your local repo.*
> Rewriting shared history forces everyone else into a painful recovery.

**Interactive rebase — tidy up before a PR**
```bash
git rebase -i HEAD~4     # ⭐ edit the last 4 commits
```
```
pick   a1b2c3  feat: add login form
squash d4e5f6  fix typo               ← squash: fold into the commit above
reword 7g8h9i  fix: validation        ← reword: change the message
drop   j1k2l3  debug print            ← drop: remove entirely
# also: edit (stop to amend), fixup (like squash, discard message)
```
> ℹ️ Interactive rebase is not available in this Claude Code environment, but you'll use it
> constantly in a normal terminal.

**Squash merge** — the popular middle ground: GitHub's "Squash and merge" collapses a whole PR
into a single clean commit on `main`, while the branch keeps its messy history.

---

## ⚔️ Merge Conflicts

A **conflict** happens when two branches change **the same lines of the same file** (or one edits
a file the other deleted) and Git can't decide automatically.

### What it looks like
```bash
$ git merge feature/login
Auto-merging src/app.js
CONFLICT (content): Merge conflict in src/app.js
Automatic merge failed; fix conflicts and then commit the result.
```

Git writes **conflict markers** into the file:
```javascript
function greet() {
<<<<<<< HEAD
  console.log("Hello from main");        // ← YOUR current branch
=======
  console.log("Hi from feature");        // ← the INCOMING branch
>>>>>>> feature/login
}
```

| Marker | Meaning |
|---|---|
| `<<<<<<< HEAD` | Start of **your** version (the branch you're on) |
| `=======` | Divider |
| `>>>>>>> branch-name` | End of the **incoming** version |

### Resolution workflow
```bash
# 1. See what's conflicted
git status                       # "Unmerged paths"
git diff                         # show the conflicts
git diff --name-only --diff-filter=U    # just the conflicted filenames

# 2. Open each file and EDIT it into the correct final state.
#    ⭐ Delete ALL THREE marker lines. Keep yours, theirs, or a blend.

# 3. Mark it resolved
git add src/app.js

# 4. Complete the operation
git commit                       # for a merge (message is pre-filled)
git rebase --continue            # for a rebase

# Escape hatches
git merge --abort                # ⭐ cancel the merge, back to before
git rebase --abort
```

**Shortcuts when you know which side wins**
```bash
git checkout --ours   file.txt   # keep MY version   (current branch)
git checkout --theirs file.txt   # keep THEIR version (incoming branch)
git add file.txt

git mergetool                    # launch a configured visual merge tool
```
> ⚠️ During a **rebase**, "ours" and "theirs" are **swapped** relative to a merge (because your
> commits are being replayed onto the other branch). Check with `git status` before relying on them.

### How to avoid conflicts
| Practice | Why it helps |
|---|---|
| ⭐ **Pull/rebase from `main` often** | Diverge less → smaller conflicts |
| **Small, short-lived branches** | Merge within a day or two, not a month |
| **Small, focused commits** | Easier to reason about a conflict |
| **Clear file/module ownership** | Two people rarely touch the same lines |
| **Agree on formatting (Prettier/ESLint/gofmt)** | Kills whole-file reformat conflicts |
| **Communicate before large refactors** | Avoid two people rewriting the same module |
| **Never commit generated files** (lock files aside) | `dist/`, `build/` conflict constantly |

---

## 🌍 Remotes: push, pull & fetch

```bash
git remote -v                                # ⭐ list remotes and URLs
git remote add origin https://github.com/USER/repo.git
git remote add upstream https://github.com/ORIGINAL/repo.git   # for forks
git remote set-url origin git@github.com:USER/repo.git         # switch HTTPS → SSH
git remote rename origin github
git remote remove upstream
git remote show origin                       # detailed info
```

```bash
# ---- Sending ----
git push                            # push the current branch to its upstream
git push origin main
git push -u origin feature/login    # ⭐ first push of a new branch (-u sets upstream)
git push --all origin
git push --tags                     # push tags too
git push --force-with-lease         # ⭐ safer force: refuses if the remote moved
git push --force                    # ⚠️ can destroy teammates' commits

# ---- Receiving ----
git fetch origin                    # ⭐ download commits, DON'T touch your files
git fetch --all --prune             # also delete stale remote-tracking branches
git pull                            # = fetch + merge
git pull --rebase                   # ⭐ = fetch + rebase (linear history)
```

### `fetch` vs `pull` — an important distinction
| | `git fetch` | `git pull` |
|---|---|---|
| Downloads remote commits | ✅ | ✅ |
| Modifies your working files | ❌ **No** | ✅ **Yes** |
| Can cause conflicts | ❌ No | ✅ Yes |
| Safety | ⭐ Always safe | Can surprise you |

```bash
# The cautious habit:
git fetch origin
git log HEAD..origin/main --oneline   # ⭐ see what's coming BEFORE you merge it
git merge origin/main
```

**Fork workflow (contributing to someone else's repo)**
```bash
# 1. Fork on GitHub, then clone YOUR fork
git clone git@github.com:YOU/repo.git && cd repo
# 2. Track the original
git remote add upstream https://github.com/ORIGINAL/repo.git
# 3. Stay in sync
git fetch upstream
git checkout main && git merge upstream/main && git push origin main
# 4. Branch, commit, push to YOUR fork, then open a PR to the original
```

---

## 🔄 Pull Requests

> A **Pull Request (PR)** — "Merge Request" on GitLab — is a **request to merge one branch into
> another**, wrapped in a review-and-discussion workflow. It is a **GitHub feature, not a Git one.**

### What a PR gives you
| Feature | Value |
|---|---|
| **Code review** | Line-by-line comments, suggestions, required approvals |
| **Automated checks** | ⭐ CI runs tests/lint/security scans on the PR before merge |
| **Discussion** | The *why* is recorded next to the *what* |
| **Diff view** | Exactly what changes, file by file |
| **Branch protection** | Block merges until checks pass and N reviewers approve |
| **Traceability** | "Closes #123" auto-links and closes the issue |
| **Knowledge sharing** | Juniors learn; the team stays aware of changes |

### Lifecycle
```
1. Branch      git checkout -b feature/login
2. Commit      small, focused commits
3. Push        git push -u origin feature/login
4. Open PR     GitHub → "Compare & pull request"
                 · title + description (what/why/how to test)
                 · link the issue: "Closes #42"
                 · request reviewers
5. CI runs     ⭐ build · unit tests · lint · SAST · image scan
6. Review      comments → push follow-up commits (the PR updates automatically)
7. Approve     required approvals granted, checks green ✅
8. Merge       Merge commit | Squash and merge | Rebase and merge
9. Cleanup     delete the branch (locally and on the remote)
```

### The three merge buttons on GitHub
| Option | Result on `main` | Use when |
|---|---|---|
| **Create a merge commit** | Keeps every commit + adds a merge commit | You want full history/traceability |
| **Squash and merge** ⭐ | All PR commits become **one** clean commit | Most teams' default — tidy `main` |
| **Rebase and merge** | Commits replayed linearly, no merge commit | You want linear history *and* individual commits |

### Writing a good PR
```markdown
## What
Adds a JWT refresh-token endpoint at POST /auth/refresh.

## Why
Access tokens expire in 15 min; users were being logged out mid-session (#142).

## How
- New `refreshToken` service with rotation
- Refresh tokens stored hashed in Redis with a 7-day TTL
- Added unit + integration tests

## How to test
1. `docker compose up`
2. `curl -XPOST localhost:5000/auth/login -d '{...}'`
3. `curl -XPOST localhost:5000/auth/refresh -H "Cookie: rt=..."`

Closes #142
```

**Reviewer etiquette:** review promptly, comment on the code (not the person), distinguish
blocking issues from nitpicks (`nit:`), and approve when it's *better*, not *perfect*.

**Branch protection rules** (Settings → Branches) — how `main` stays trustworthy:
- Require a pull request before merging
- Require **N** approvals
- ⭐ Require **status checks to pass** (this is where CI becomes a gate)
- Require branches to be up to date before merging
- Require conversation resolution
- Prohibit force pushes and deletions

---

## 🔁 The Basic Git Workflow

### Daily loop
```bash
# 1. Start from an up-to-date main
git checkout main
git pull origin main

# 2. Create a feature branch
git checkout -b feature/add-health-endpoint

# 3. Work → stage → commit (repeat in small steps)
git status
git add .
git commit -m "feat(api): add /health endpoint"

# 4. Keep up with main while you work
git fetch origin
git rebase origin/main          # (or: git merge origin/main)

# 5. Push
git push -u origin feature/add-health-endpoint

# 6. Open a PR on GitHub → CI runs → review → merge

# 7. Clean up
git checkout main
git pull origin main
git branch -d feature/add-health-endpoint
git push origin --delete feature/add-health-endpoint
```

### One-picture summary
```
   main:  A───B───C───────────────────M───▶
                    \               /
feature/x:           D───E───F─────┘
                     ↑           ↑
              checkout -b     PR → review → CI ✅ → merge
```

---

## 🗺️ Branching Strategies

### 1. GitHub Flow ⭐ (simple, CI/CD-friendly — start here)
```
main  ────●────●────●────●────▶   (always deployable, always releasable)
           \        /
   feature   ●──●──●   → PR → CI → merge → deploy
```
- One long-lived branch: **`main`**
- Short-lived feature branches, merged via PR
- Every merge to `main` can be deployed immediately
- ✅ Best fit for web apps with continuous deployment

### 2. Git Flow (heavier, release-oriented)
```
main     ──●───────────────●────────▶   production (tagged releases)
             \            /
release       ●─────●────●
             /
develop  ──●───●───●───●───●────────▶   integration branch
            \     /
feature      ●───●
hotfix   ──────────●──▶ (branches from main, merges to main AND develop)
```
Branches: `main`, `develop`, `feature/*`, `release/*`, `hotfix/*`.
✅ Good for versioned/on-prem software with scheduled releases; ❌ heavy for continuous delivery.

### 3. Trunk-Based Development (what elite teams do)
- Everyone commits to **trunk (`main`)** at least daily; branches live **hours**, not weeks
- Unfinished work hidden behind **feature flags**
- Requires strong automated testing
- ✅ Highest deployment frequency (best DORA metrics)

### 4. Environment branches
`main` → dev → staging → production. Simple to picture but prone to drift and
merge pain — **GitOps with per-environment *directories*** is now preferred over per-environment branches.

---

## 🏷️ Tags & Releases

Tags mark a specific commit permanently — usually a **release version**.

```bash
git tag                             # list tags
git tag v1.0.0                      # lightweight tag
git tag -a v1.0.0 -m "First release"   # ⭐ ANNOTATED tag (has author/date/message) — use this
git tag -a v1.0.0 <commit>          # tag an older commit
git show v1.0.0
git push origin v1.0.0              # ⭐ tags are NOT pushed by default
git push origin --tags              # push all tags
git tag -d v1.0.0                   # delete locally
git push origin --delete v1.0.0     # delete on the remote
git checkout v1.0.0                 # check out that exact release
git describe --tags                 # nearest tag to HEAD (great for build metadata)
```

**Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`**
| Part | Increment when | Example |
|---|---|---|
| **MAJOR** | Breaking changes | `1.4.2` → `2.0.0` |
| **MINOR** | New backwards-compatible features | `1.4.2` → `1.5.0` |
| **PATCH** | Backwards-compatible bug fixes | `1.4.2` → `1.4.3` |
| Pre-release | Suffix | `2.0.0-rc.1`, `2.0.0-beta` |

> 🐳 **Docker connection:** tag your images with the Git tag/SHA, never just `latest`:
> `myapp:1.4.2`, `myapp:${GITHUB_SHA::7}`. That's how you know *exactly* what's in production
> — and how you roll back.

---

## 🧰 Stash, Cherry-pick & Other Useful Tools

```bash
# ---- Stash: park uncommitted work temporarily ----
git stash                       # ⭐ shelve changes, clean the working dir
git stash -u                    # include untracked files
git stash save "wip: login form"
git stash list                  # stash@{0}, stash@{1}...
git stash pop                   # ⭐ re-apply the newest stash AND remove it
git stash apply stash@{1}       # re-apply but KEEP it in the list
git stash drop stash@{0}
git stash clear                 # ⚠️ delete all stashes
# Classic use: "I need to switch branches right now but I'm mid-change."

# ---- Cherry-pick: copy ONE commit onto the current branch ----
git cherry-pick <commit>        # ⭐ classic hotfix backport
git cherry-pick <c1> <c2>
git cherry-pick A..B            # a range
git cherry-pick --abort

# ---- Worktrees: multiple branches checked out at once ----
git worktree add ../hotfix hotfix/urgent
git worktree list
git worktree remove ../hotfix

# ---- Archive / export ----
git archive --format=zip HEAD > release.zip

# ---- Maintenance ----
git gc                          # garbage-collect / compress
git fsck                        # integrity check
git count-objects -vH           # repo size

# ---- Submodules (vendoring another repo) ----
git submodule add <url> path/
git submodule update --init --recursive
git clone --recurse-submodules <url>
```

---

## 🚀 Git in the DevOps Pipeline

Git is the **trigger and the source of truth** for everything that follows in this course.

```
     git push / PR opened
              │
              ▼
   ┌─────────────────────────┐
   │  GitHub Actions (CI)    │   .github/workflows/ci.yml — versioned IN the repo
   │  · checkout             │
   │  · lint + unit tests    │
   │  · SAST / SCA / secrets │
   │  · docker build         │
   │  · trivy image scan     │
   │  · push to registry     │   tagged with the Git SHA ⭐
   └───────────┬─────────────┘
               ▼
   ┌─────────────────────────┐
   │  CD / GitOps            │
   │  · update the manifest  │   another Git commit!
   │  · Argo CD reconciles   │   Git = desired state of the cluster
   └─────────────────────────┘
```

| DevOps concept | How Git enables it |
|---|---|
| **CI trigger** | `on: push` / `on: pull_request` events |
| **Pipeline as code** | Workflows live in `.github/workflows/` — versioned & reviewed |
| **Infrastructure as Code** | Terraform `.tf` files in Git; `plan` posted on the PR |
| **Image provenance** | Tag images with the commit SHA → every container traceable to a commit |
| **GitOps** | Argo CD reconciles the cluster to the repo; **rollback = `git revert`** ⭐ |
| **Auditability** | Every production change has an author, timestamp, diff and reviewer |
| **Secret scanning** | Gitleaks/GitHub scanning on every push |
| **Quality gates** | Branch protection + required status checks |

**GitHub Actions events you'll use:** `push`, `pull_request`, `workflow_dispatch` (manual),
`schedule` (cron), `release`.

---

## ✅ Best Practices

| # | Practice | Why |
|---|---|---|
| 1 | **Commit early, commit often** | Small commits are easy to review, revert and bisect |
| 2 | **One logical change per commit** | Clean history; `git revert` actually works |
| 3 | ⭐ **Write meaningful messages** (Conventional Commits) | History becomes documentation |
| 4 | **Never commit secrets** | Use `.env` + `.gitignore` + a secret manager |
| 5 | **Never commit generated artifacts** | `node_modules/`, `dist/`, `.terraform/` |
| 6 | ⭐ **Pull before you push** | Avoids needless conflicts |
| 7 | **Short-lived feature branches** | Merge within days, not weeks |
| 8 | **Always review via PR** | Even solo — it forces a self-review and runs CI |
| 9 | ⭐ **Never force-push shared branches** | Use `--force-with-lease` on your own branches only |
| 10 | **Protect `main`** | Required checks + approvals; keep it always deployable |
| 11 | **`revert` for pushed commits, `reset` only locally** | Don't rewrite shared history |
| 12 | **Tag releases with SemVer** | Traceable, rollback-able deployments |
| 13 | **`git status` before every commit** | Catch accidental additions |
| 14 | **`git config core.autocrlf input` on Windows** | Prevents CRLF breaking shell scripts |
| 15 | **Add a README + `.gitignore` on day one** | Cheap, permanently useful |

---

## 📋 Quick Cheat Sheet

```bash
# ---------- SETUP ----------
git config --global user.name "Name"
git config --global user.email "you@example.com"
git init | git clone <url>

# ---------- DAILY ----------
git status                  # what changed
git add . | git add -p      # stage all | stage interactively
git commit -m "feat: msg"   # commit
git log --oneline --graph --decorate --all
git diff | git diff --staged

# ---------- BRANCH ----------
git branch -a
git checkout -b feature/x   # create + switch (or: git switch -c)
git switch main
git branch -d feature/x
git push origin --delete feature/x

# ---------- INTEGRATE ----------
git merge feature/x         # preserve history (safe on shared)
git rebase main             # linear history (own branches only)
git merge --abort | git rebase --abort

# ---------- CONFLICTS ----------
git status                  # list conflicted files
# edit files, remove <<<<<<< ======= >>>>>>> markers
git add <file> && git commit        # (or git rebase --continue)
git checkout --ours/--theirs <file>

# ---------- REMOTE ----------
git remote -v
git fetch origin            # safe: download only
git pull [--rebase]         # fetch + merge/rebase
git push -u origin <branch>
git push --force-with-lease # safer force

# ---------- UNDO ----------
git restore <file>              # discard working-dir change
git restore --staged <file>     # unstage
git commit --amend              # fix last commit
git reset --soft HEAD~1         # undo commit, keep staged
git reset --hard HEAD~1         # ⚠️ undo commit + changes
git revert <commit>             # ⭐ safe undo of a PUSHED commit
git reflog                      # ⭐ recover "lost" commits

# ---------- HANDY ----------
git stash | git stash pop
git cherry-pick <commit>
git tag -a v1.0.0 -m "release" && git push origin v1.0.0
git blame <file>
git bisect start
```

---

## 🔗 References
- Official Git cheat sheet — https://git-scm.com/cheat-sheet
- GitHub education cheat sheet — https://education.github.com/git-cheat-sheet-education.pdf
- GeeksforGeeks Git cheat sheet — https://www.geeksforgeeks.org/git/git-cheat-sheet/
- Pro Git (free book) — https://git-scm.com/book/en/v2
- Conventional Commits — https://www.conventionalcommits.org/
- Learn Git Branching (interactive) — https://learngitbranching.js.org/
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
