# Session 16 — CI/CD & GitHub Actions ⚙️

> **Topics:** CI vs CD · CI/CD Pipeline · GitHub Actions · Workflows · Jobs & Steps · Runners ·
> Secrets · Artifacts · Build & Test Pipeline
>
> 📁 Repo: `session-16-github-actions/` — ten numbered folders plus a full `demo/` project
> (a Python calculator with tests, `build.sh` and a working `ci.yml`).

Everything so far has been a command *you* typed. This session is where the machine starts
typing them for you: **`git push` → build → test → package → deploy**, with no human in the
loop until it's time to approve production.

---

## 📑 Table of Contents

1. [CI vs CD](#-ci-vs-cd)
2. [The Pipeline & Its Vocabulary](#-the-pipeline--its-vocabulary)
3. [What GitHub Actions Is](#-what-github-actions-is)
4. [Your First Workflow](#-your-first-workflow)
5. [Workflows & Triggers](#-workflows--triggers)
6. [Jobs & Steps](#-jobs--steps)
7. [Runners](#-runners)
8. [Matrix Builds](#-matrix-builds)
9. [Secrets](#-secrets)
10. [Artifacts](#-artifacts)
11. [Caching — making pipelines fast](#-caching--making-pipelines-fast)
12. [Contexts & Expressions](#-contexts--expressions)
13. [Full Build & Test Pipeline (the demo project)](#-full-build--test-pipeline-the-demo-project)
14. [Beyond the lab: environments, reusable workflows, OIDC](#-beyond-the-lab-environments-reusable-workflows-oidc)
15. [Deploying from a pipeline](#-deploying-from-a-pipeline)
16. [Debugging workflows](#-debugging-workflows)
17. [Key Terms Recap](#-key-terms-recap)
18. [Session Takeaways](#-session-takeaways)

---

## 🔁 CI vs CD

### CI — Continuous Integration

Every push triggers an automated **pull → build → test → report**.

```
Developer pushes  ──▶  CI: build + test  ──▶  PASS / FAIL
```

The problem it solves:

```
Without CI:                          With CI:
  Dev A works 2 weeks                  Dev A pushes
  Dev B works 2 weeks                  Tests run immediately
  They merge                           Failure caught the same hour
  Everything breaks                    Root cause is obvious
  Nobody knows why                     (the diff is 20 lines, not 2 weeks)
```

⭐ CI is not really about the tests — it's about **small, frequent integrations**. The tests
are what make small integrations safe.

### CD — two different things with the same initials

| | Continuous **Delivery** | Continuous **Deployment** |
|---|---|---|
| After CI passes | app is packaged and **ready** to deploy | app is **automatically deployed** |
| Production release | **human approval** | fully automatic |
| Who uses it | ⭐ most companies | mature teams with strong tests + monitoring |

```
CI                     Build + Test on every push
Continuous Delivery    Auto-package, manual deploy  ← the common choice
Continuous Deployment  Auto-package, auto-deploy
```

| CI | CD |
|---|---|
| Integrates code | Delivers / deploys code |
| Builds the application | Releases the application |
| Runs tests | Runs the deployment process |
| Finds problems early | Automates release |
| Developer-focused validation | Release-focused |

### Why it matters — the feedback loop

```
Without CI/CD:  bug introduced Monday → found Friday in QA → 4 days of lost context
With CI/CD:     bug introduced Monday → found Monday 10:03 → fixed before lunch
```

---

## 🏗️ The Pipeline & Its Vocabulary

```
Code Push ──▶ Build ──▶ Test ──▶ Package ──▶ Deploy
```

Each stage is a **gate**. If it fails, nothing downstream runs — that is the entire value.

| Stage | Does | Fails when |
|---|---|---|
| **Source / Checkout** | pull the code from Git | — |
| **Build** | compile / package | code doesn't compile |
| **Test** | unit, integration, lint | an assertion or style rule fails |
| **Artifact** | produce Docker image / JAR / dist | build output missing |
| **Deploy** | push to staging or production | env/config problem |

### Vocabulary (used by every CI system, not just GitHub)

| Term | Meaning |
|---|---|
| **Pipeline** | the whole automated workflow |
| **Stage** | a logical group of work (build, test, deploy) |
| **Job** | a unit of work that runs on **one machine** |
| **Step** | a single command or action inside a job |
| **Runner** | the machine that executes jobs |
| **Artifact** | a file produced by a job (binary, image, report) |
| **Trigger** | the event that starts the pipeline |

### Linear vs parallel

```
Linear:    Build ──▶ Test ──▶ Deploy

Parallel:          ┌── Unit Tests ──┐
          Build ───┤                ├── Deploy
                   └── Lint ────────┘
```

⭐ Parallel where you can, sequential where you must. Lint and unit tests don't need each
other; deploy needs both.

---

## 🐙 What GitHub Actions Is

An automation platform **built into GitHub** — no server to run, no external service.

```
Jenkins   → you maintain the server
CircleCI  → external service, separate account
GitLab CI → separate platform

GitHub Actions → a YAML file in .github/workflows/ ; GitHub runs it
```

How a run happens:

```
1. You commit a YAML file to .github/workflows/
2. You push
3. GitHub matches the trigger
4. GitHub allocates a runner VM
5. The runner clones the repo
6. The runner executes each step
7. GitHub shows logs + status (and blocks the PR if it failed)
```

```
Repository/
└── .github/
    └── workflows/
        ├── build.yml      ← every push
        ├── deploy.yml     ← on release
        └── nightly.yml    ← cron
```

GitHub reads **every** `.yml`/`.yaml` file in `.github/workflows/`, and each one runs
independently.

---

## 👋 Your First Workflow

`.github/workflows/hello.yml`:

```yaml
name: Hello World          # display name in the Actions tab

on: push                   # trigger

jobs:
  say-hello:               # job id
    runs-on: ubuntu-latest # which runner
    steps:
      - name: Print message
        run: echo "Hello from GitHub Actions"
```

```bash
mkdir -p .github/workflows
git add .github/ && git commit -m "Add hello world workflow" && git push
```

Repo → **Actions** tab → click the run → read the logs.

The anatomy, once:

```yaml
name:              # workflow display name
on:                # WHEN  — the trigger
jobs:              # WHAT  — the work
  <job-id>:
    runs-on:       # which machine
    steps:
      - name:      # step display name
        run:       # a shell command
        uses:      # OR a pre-built action
```

⭐ **A workflow is `WHEN` + `WHAT`.** Everything else is detail.

---

## ⏰ Workflows & Triggers

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'       # every day at 00:00 UTC
  workflow_dispatch:          # adds a "Run workflow" button in the UI
```

| Trigger | Fires when |
|---|---|
| `push` | commits pushed to matching branches/tags |
| `pull_request` | a PR is opened, synchronised or reopened |
| `schedule` | a cron expression matches (**UTC only**) |
| `workflow_dispatch` | you click the button (can take `inputs`) |
| `release` | a release is published |
| `workflow_call` | another workflow calls this one (reusable) |
| `issue_comment`, `issues`, … | repo activity |

### Path filters — don't run the build for a typo in the README

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - '!**.md'          # ignore markdown-only changes
```

### Workflow-level env and run names

```yaml
name: CI Pipeline
run-name: "Build ${{ github.ref_name }} by ${{ github.actor }}"

env:
  APP_NAME: notes-app
  PYTHON_VERSION: '3.11'
```

### Concurrency — cancel superseded runs

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

⭐ Push three times in a minute and without this you pay for three full runs, two of which are
already obsolete. Add it to every PR workflow.

> ⚠️ `pull_request` from a **fork** runs with a read-only `GITHUB_TOKEN` and **no secrets** —
> deliberately, so a stranger's PR can't steal your credentials. Don't try to work around it;
> that's the hole `pull_request_target` opens.

---

## 🧱 Jobs & Steps

```
Workflow
 ├── job: build  ──▶ steps: checkout, install, compile   (runner A)
 └── job: test   ──▶ steps: checkout, install, pytest    (runner B)
```

| Job | Step |
|---|---|
| Larger unit | Smaller unit |
| Contains steps | Executes one task |
| **Gets its own runner (own VM)** | Runs inside the job |
| Can depend on other jobs (`needs`) | Always sequential within the job |
| ⭐ **Jobs run in parallel by default** | ⭐ **Steps always run in order** |

### `run` vs `uses`

```yaml
- name: Install dependencies
  run: pip install -r requirements.txt     # shell command

- name: Checkout code
  uses: actions/checkout@v4                # a pre-built action
```

⭐ **`actions/checkout` is not optional.** The runner starts with an *empty* workspace —
without it, your repo isn't there. Forgetting it is the #1 beginner error.

### `with:` passes parameters to an action

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
```

### Sequencing jobs with `needs`

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps: [{ run: echo "Building..." }]

  test:
    needs: build
    runs-on: ubuntu-latest
    steps: [{ run: echo "Testing..." }]

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps: [{ run: echo "Deploying..." }]
```

```
build ──▶ test ──▶ deploy
```

`needs` can take a list — `needs: [lint, test]` waits for both.

### Conditions, env and multi-line

```yaml
- name: Deploy only on main
  if: github.ref == 'refs/heads/main'
  run: echo "Deploying to production"

- name: Build with variables
  env:
    BUILD_VERSION: "1.0.0"
  run: echo "Building $BUILD_VERSION"

- name: Install and test
  run: |                       # ⭐ YAML block scalar = multiple shell lines
    pip install -r requirements.txt
    pytest --verbose
```

Useful `if` forms:

```yaml
if: success()            # default — previous steps passed
if: failure()            # only when something failed
if: always()             # ⭐ run even on failure (use for uploading test reports)
if: github.event_name == 'pull_request'
```

> ⚠️ Each `run:` step is a **separate shell**. `cd foo` in step 1 does not persist into step 2
> — use `working-directory:`, or chain commands in one `run: |` block.
> Env vars don't persist either; write them to `$GITHUB_ENV` to pass them along.

---

## 🖥️ Runners

```yaml
runs-on: ubuntu-latest
```

```
Workflow starts ─▶ GitHub finds a runner ─▶ clones repo ─▶ runs steps ─▶ reports status
```

### GitHub-hosted

```
ubuntu-latest / ubuntu-22.04 / ubuntu-24.04    ← most common
windows-latest
macos-latest / macos-14
```

Pre-installed on `ubuntu-latest`: **Git, Docker, Python, Node.js, Java, Go, Ruby, AWS CLI,
kubectl, Helm** — you rarely need to install a standard tool.

⭐ **Every job gets a brand-new VM.** Clean, reproducible, no state leakage between runs —
and the reason jobs can't see each other's files without artifacts.

### Self-hosted

```yaml
runs-on: self-hosted
runs-on: [self-hosted, linux, gpu]     # label matching
```

| Use a self-hosted runner when | |
|---|---|
| Special hardware | GPU, lots of RAM |
| Private network access | internal DB, VPN, on-prem cluster |
| Custom software | licensed tooling |
| Cost | very large workloads |

Register: **Settings → Actions → Runners → New self-hosted runner**, then run the agent.

| | GitHub-hosted | Self-hosted |
|---|---|---|
| Lifetime | fresh VM every job | persistent machine |
| State | none | persists — **needs cleanup discipline** |
| Cost | free for public repos; minutes billed for private | your hardware |
| Security | isolated | ⚠️ **never** attach to a public repo — any fork's PR could run code on your box |

---

## 🧮 Matrix Builds

Run the same job across many configurations, in parallel:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false          # don't cancel the others when one fails
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pytest
```

Three parallel jobs. Multi-dimensional matrices multiply out:

```yaml
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [18, 20, 22]      # → 9 jobs
        exclude:
          - os: macos-latest
            node: 18
```

> ⚠️ Matrices get expensive fast. 3 OS × 3 versions = 9 runners for every push.

---

## 🔑 Secrets

```yaml
# ❌ NEVER
- run: aws configure set aws_access_key_id AKIAIOSFODNN7EXAMPLE
```

That's now in Git history **forever**, readable by everyone with repo access.

```
Stored encrypted in GitHub
        │
        ▼
Referenced as ${{ secrets.NAME }}
        │
        ▼
Injected into the runner at runtime
        │
        ▼
Masked (***) in all logs
```

**Create:** Settings → Secrets and variables → Actions → New repository secret.
⭐ You can never read the value back — only update or delete it.

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Login to Docker Hub
        env:
          DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
          DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
        run: |
          echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
```

⭐ `--password-stdin` keeps the secret out of the process list — same lesson as
[Session 6](./06_Docker_Fundamentals.md).

### Don't print secrets

```bash
echo "$DEMO_SECRET"                      # ❌ (masked, but don't rely on it)

if [ -n "$DEMO_SECRET" ]; then           # ✅ check presence, not value
  echo "Secret is available."
else
  echo "Secret is not configured."; exit 1
fi
```

> ⚠️ Masking is **literal substring matching**. A base64'd, JSON-wrapped or line-split secret
> will **not** be masked. Treat masking as a safety net, never a control.

### Scopes

| Scope | Available to |
|---|---|
| **Repository** secrets | all workflows in the repo |
| **Environment** secrets | ⭐ only jobs that declare `environment: production` |
| **Organization** secrets | selected repos across the org |

```yaml
jobs:
  deploy:
    environment: production     # unlocks that env's secrets + approval rules
    runs-on: ubuntu-latest
```

### Secrets vs variables

`secrets.*` is encrypted and masked. `vars.*` (Settings → Variables) is plaintext config —
region names, cluster names, image names. Use `vars` for anything that isn't sensitive.

### Secrets you'll meet

```text
DOCKER_USERNAME / DOCKER_PASSWORD   Docker Hub (use an access token, not your password)
AWS_ACCESS_KEY_ID / AWS_SECRET_...  AWS
KUBECONFIG                          base64-encoded kubeconfig
SLACK_WEBHOOK_URL                   notifications
GITHUB_TOKEN                        ⭐ provided automatically — do not create it
```

### `GITHUB_TOKEN`

Minted fresh for each run, scoped to the repo, and expires when the run ends.

```yaml
permissions:
  contents: read
  packages: write        # ⭐ least privilege — declare only what you need

steps:
  - run: |
      echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
      docker push ghcr.io/${{ github.repository }}/myapp:latest
```

That's how you push to **GHCR** without creating a single secret.

---

## 📦 Artifacts

A file or directory produced by a run that you want to keep.

```
Problem:  build job compiles → test job needs the output → different machines → no shared disk
Solution: build uploads an artifact, test downloads it
```

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: mkdir dist && echo "built" > dist/app.txt
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/
          retention-days: 7

  test:
    needs: build                       # ⭐ required to get the previous job's artifact
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/
      - run: cat dist/app.txt
```

### Test reports — always upload them

```yaml
- run: pytest --junitxml=test-results/results.xml
- uses: actions/upload-artifact@v4
  if: always()                 # ⭐ upload even when the tests FAILED
  with:
    name: test-report
    path: test-results/
```

⭐ `if: always()` on report uploads. Without it, the one run you most need the report from —
the failing one — produces nothing.

### A Docker image as an artifact

```yaml
- run: docker build -t myapp:latest . && docker save myapp:latest > myapp.tar
- uses: actions/upload-artifact@v4
  with: { name: docker-image, path: myapp.tar }

# later job
- uses: actions/download-artifact@v4
  with: { name: docker-image }
- run: docker load < myapp.tar
```

| Retention | |
|---|---|
| Default | 90 days |
| Range | 1–90 days (free), up to 400 (enterprise) |

> **Artifact ≠ Git.** Git stores *source*; artifacts store *build output*. Never commit build
> output — that's what `.gitignore` ([Session 5](./05_Git_and_GitHub.md)) is for.
> For images, the registry is the real artifact store; `upload-artifact` is for reports and
> small build outputs.

---

## ⚡ Caching — making pipelines fast

The most common interview question here is *"your pipeline takes 45 minutes but only 5 minutes
is real work — fix it."* The answer is caching, parallelism and smaller images.

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: ${{ runner.os }}-pip-
```

Or let the setup action do it:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'            # ⭐ one line, same effect
```

⭐ The key contains a **hash of the lockfile** — change a dependency and the cache key changes,
so you never restore a stale cache. Exactly the Docker layer-cache idea from
[Session 7](./07_Docker_Images_and_Dockerfile.md).

Other wins: `fail-fast: false` only when you need it, `concurrency` to cancel stale runs,
path filters, `--depth 1` checkouts, and Buildx cache for Docker builds.

---

## 🧩 Contexts & Expressions

`${{ }}` reads from **contexts**:

| Context | Example | Gives |
|---|---|---|
| `github` | `github.ref_name`, `github.sha`, `github.actor`, `github.repository`, `github.event_name` | repo & event info |
| `secrets` | `secrets.DOCKER_PASSWORD` | encrypted secrets |
| `vars` | `vars.AWS_REGION` | plaintext config |
| `env` | `env.APP_NAME` | env vars |
| `job` / `steps` | `steps.build.outputs.tag` | step outputs |
| `runner` | `runner.os`, `runner.temp` | runner info |
| `matrix` | `matrix.python-version` | current matrix cell |
| `needs` | `needs.build.outputs.image` | ⭐ outputs from an earlier job |

Passing a value between jobs:

```yaml
jobs:
  build:
    outputs:
      tag: ${{ steps.meta.outputs.tag }}
    steps:
      - id: meta
        run: echo "tag=${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"
  deploy:
    needs: build
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.tag }}"
```

Special files the runner watches:

```bash
echo "KEY=value"      >> "$GITHUB_ENV"      # env var for LATER steps
echo "key=value"      >> "$GITHUB_OUTPUT"   # this step's output
echo "## Summary"     >> "$GITHUB_STEP_SUMMARY"   # markdown on the run page
echo "/opt/mytool/bin" >> "$GITHUB_PATH"    # add to PATH
```

⭐ Use `${GITHUB_SHA::7}` as your image tag. `:latest` in a pipeline means you can never say
which commit is running in production.

---

## 🧪 Full Build & Test Pipeline (the demo project)

The `demo/` project is a Python calculator with tests, a build script and a two-job pipeline.

**`app/calculator.py`**

```python
def add(a, b):      return a + b
def subtract(a, b): return a - b
def multiply(a, b): return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

**`tests/test_calculator.py`**

```python
import pytest
from app.calculator import add, subtract, divide

def test_add():       assert add(2, 3) == 5
def test_subtract():  assert subtract(10, 4) == 6
def test_divide():    assert divide(10, 2) == 5.0

def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)
```

**`requirements.txt`**

```text
pytest==7.4.0
pytest-cov==4.1.0
flake8==6.1.0
```

**`build.sh`** — note `set -e` from [Session 3](./03_Shell_Scripting.md); without it a failed
`cp` would still report a successful build.

```bash
#!/bin/bash
set -e
echo "Starting build..."
rm -rf build && mkdir -p build
cp app/calculator.py build/
cat > build/build-info.txt <<EOF
Application: Session 16 Calculator
Build Status: SUCCESS
Build Date: $(date)
EOF
echo "Build completed successfully."
```

**`.github/workflows/ci.yml`**

```yaml
name: Python CI Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    name: Test Application
    runs-on: ubuntu-latest
    steps:
      - name: Checkout source code
        uses: actions/checkout@v6
      - name: Setup Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest -v

  build:
    name: Build Application
    needs: test                  # ⭐ the gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
      - name: Build application
        run: |
          chmod +x build.sh
          ./build.sh
      - name: Show build output
        run: ls -la build && cat build/build-info.txt
      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: calculator-build
          path: build/
```

### A richer variant (lint + test + coverage)

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: 'pip' }
      - run: pip install flake8
      - run: flake8 app.py tests/

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: 'pip' }
      - run: pip install -r requirements.txt
      - run: |
          pytest tests/ \
            --junitxml=test-results/results.xml \
            --cov=app --cov-report=xml:coverage.xml --cov-report=term-missing
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: test-results/, retention-days: 7 }
```

### ⭐ Run it locally first

```bash
pip install -r requirements.txt
flake8 app.py tests/
pytest -v --cov=app --cov-report=term-missing
```

A pipeline is only a script someone else runs. If it doesn't work on your laptop it won't work
on the runner — and debugging it there costs a push-and-wait every attempt.

### Watch it catch a bug

```python
def add(a, b):
    return a - b        # intentionally wrong
```

```text
CI Pipeline
  └── Test Application   ✗   FAILED tests/test_calculator.py::test_add - assert -1 == 5
  └── Build Application  ⊘   skipped (needs: test)
```

⭐ **That skipped build is the whole point.** The broken code physically cannot reach the
artifact, let alone production.

---

## 🚀 Beyond the lab: environments, reusable workflows, OIDC

### Environments & manual approval — this is Continuous *Delivery*

```yaml
jobs:
  deploy-prod:
    environment:
      name: production
      url: https://app.example.com
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh
```

Settings → Environments → **Required reviewers** turns the job into a gate that waits for a
human click. That one setting is the line between Delivery and Deployment.

### Reusable workflows — don't copy-paste YAML across 30 repos

```yaml
# .github/workflows/reusable-ci.yml
on:
  workflow_call:
    inputs:
      python-version: { type: string, default: '3.11' }
    secrets:
      REGISTRY_TOKEN: { required: true }
```

```yaml
# a consuming repo
jobs:
  ci:
    uses: my-org/.github/.github/workflows/reusable-ci.yml@v1
    with:  { python-version: '3.12' }
    secrets: inherit
```

**Composite actions** (`action.yml` with `runs.using: composite`) do the same for a group of
*steps* rather than a whole job.

### OIDC — stop storing cloud keys entirely ⭐

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789012:role/github-actions
      aws-region: ap-south-1
```

GitHub mints a short-lived OIDC token; AWS/Azure/GCP trade it for temporary credentials.
**No long-lived `AWS_SECRET_ACCESS_KEY` in your repo at all.** This is the modern best
practice and worth raising in any interview — it eliminates the single most leaked secret class.

### Security hygiene for actions

```yaml
- uses: actions/checkout@v4                                    # tag — convenient
- uses: actions/checkout@b4ffde6...   # ⭐ full SHA — immutable, supply-chain safe
```

A third-party action runs **arbitrary code with access to your workflow's secrets**. Pin
third-party actions to a commit SHA, set `permissions:` to least privilege, and prefer
official `actions/*` where you can.

---

## 📤 Deploying from a pipeline

Where everything in this course converges:

```yaml
  deploy:
    needs: [test, build]
    if: github.ref == 'refs/heads/main'
    environment: production
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GHCR
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Build & push image
        run: |
          IMAGE=ghcr.io/${{ github.repository }}:${GITHUB_SHA::7}
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
          echo "IMAGE=$IMAGE" >> "$GITHUB_ENV"

      - name: Configure kubectl
        run: echo "${{ secrets.KUBECONFIG }}" | base64 -d > "$HOME/.kube/config"

      - name: Deploy with Helm            # ⭐ Session 15
        run: |
          helm upgrade --install notes ./charts/notes \
            -n production --create-namespace \
            -f charts/notes/values-prod.yaml \
            --set image.tag=${GITHUB_SHA::7} \
            --atomic --timeout 5m
```

```
Session 5 Git  ─▶ 7 Dockerfile ─▶ 16 Actions ─▶ 15 Helm ─▶ 9–13 Kubernetes
```

---

## 🐞 Debugging workflows

```bash
gh workflow list                  # all workflows
gh workflow run build.yml         # trigger a workflow_dispatch
gh run list                       # recent runs
gh run view <run-id> --log        # full logs
gh run view <run-id> --log-failed # ⭐ only the failing step
gh run watch                      # follow a run live
act --list                        # run workflows locally (nektos/act)
```

| Symptom | Cause |
|---|---|
| Workflow never runs | File not in `.github/workflows/`, bad YAML, wrong branch filter, or it's not on the **default branch** (for `schedule`) |
| `No such file or directory` | Missing `actions/checkout` |
| Secret is empty | Fork PR, wrong name (case-sensitive), or an environment secret without `environment:` |
| Works locally, fails in CI | Uncommitted file, or a tool version difference — pin versions |
| `cd` had no effect | Each `run:` is a new shell — use `working-directory:` |
| Permission denied on a script | `chmod +x` it, and commit the bit: `git update-index --chmod=+x build.sh` |
| Cron never fires | `schedule` only runs from the **default branch**, in **UTC**, and can be delayed under load |

Enable step debug logging: set repo secret/variable `ACTIONS_STEP_DEBUG` = `true`.

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **CI** | Every push triggers automated build + test |
| **Continuous Delivery** | Always deployable; production release needs a human |
| **Continuous Deployment** | Passing tests deploy straight to production |
| **Workflow** | A YAML file in `.github/workflows/`; `WHEN` (`on:`) + `WHAT` (`jobs:`) |
| **Job** | Steps that run together on **one** runner; parallel with other jobs by default |
| **Step** | One `run:` command or one `uses:` action; always sequential in a job |
| **Runner** | The machine executing a job; GitHub-hosted (fresh VM) or self-hosted |
| **Action** | A reusable unit invoked with `uses:`, parameterised with `with:` |
| **`needs:`** | Declares a job dependency — turns parallel into a DAG |
| **Artifact** | A file saved from a run; shared between jobs, downloadable for 1–90 days |
| **Secret** | Encrypted value, injected at runtime, masked in logs, unreadable after saving |
| **`GITHUB_TOKEN`** | Auto-provided, run-scoped token; shape it with `permissions:` |
| **Matrix** | `strategy.matrix` — the same job across many configurations in parallel |
| **Context** | `${{ github.* }}`, `${{ secrets.* }}`, `${{ needs.* }}`, … |
| **Environment** | Named deploy target carrying its own secrets and approval rules |
| **OIDC** | Short-lived cloud credentials via federated identity — no stored keys |
| **Concurrency group** | Cancels superseded runs of the same workflow+ref |

---

## 🎯 Session Takeaways

1. ⭐ **CI = build + test on every push. CD = Delivery (manual approve) or Deployment (fully automatic).** Most companies run Delivery.
2. **A workflow is `WHEN` + `WHAT`** — `on:` plus `jobs:`, in `.github/workflows/`.
3. ⭐ **Jobs are parallel by default and each gets a fresh VM; steps are sequential in one VM.** `needs:` sequences jobs; artifacts move files between them.
4. **`actions/checkout` first, always.** The runner starts empty.
5. ⭐ **`needs:` is the gate.** A failing test job means the build job never runs — that's CI working, not CI breaking.
6. **Never hardcode credentials.** `${{ secrets.X }}`, injected at runtime, masked in logs — and masking is a safety net, not a control.
7. **`GITHUB_TOKEN` is free and automatic** — use it for GHCR and repo operations, and scope it with `permissions:`.
8. ⭐ **`if: always()` on test-report uploads.** Otherwise the failing run gives you nothing to look at.
9. **Cache dependencies** (`cache: 'pip'`, `actions/cache` keyed on a lockfile hash) and add a `concurrency` group — the two cheapest speed-ups there are.
10. **Tag images with the commit SHA, never `:latest`.** You must be able to name what's in production.
11. **Run the pipeline's commands locally first.** Debugging by pushing is the slowest loop in software.
12. ⭐ **Pin third-party actions to a SHA and use OIDC instead of stored cloud keys** — a `uses:` line runs someone else's code next to your secrets.

---

## 🔗 References

- GitHub Actions docs — https://docs.github.com/en/actions
- Workflow syntax — https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- Triggering a workflow — https://docs.github.com/en/actions/using-workflows/triggering-a-workflow
- Contexts — https://docs.github.com/en/actions/learn-github-actions/contexts
- Using secrets — https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions
- Automatic token authentication — https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- OIDC hardening — https://docs.github.com/en/actions/deployment/security-hardening-your-deployments
- Storing workflow data as artifacts — https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow
- Self-hosted runners — https://docs.github.com/en/actions/hosting-your-own-runners
- Marketplace — https://github.com/marketplace?type=actions
- Martin Fowler, *Continuous Integration* — https://martinfowler.com/articles/continuousIntegration.html

---

## ➡️ Next

[Session 17 — Complete CI/CD & DevSecOps](./17_Complete_CICD_and_DevSecOps.md) — add the
security gates: SAST, SCA, secret scanning and image scanning.
