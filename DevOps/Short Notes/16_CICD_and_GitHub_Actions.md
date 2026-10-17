# ⚡ S16 · CI/CD & GitHub Actions

> *Revision card.* Full notes → [Session 16](../16_CICD_and_GitHub_Actions.md)

---

## 🔑 One-line core

***A workflow is `WHEN` + `WHAT`.*** Jobs are **parallel, each on a fresh VM**; steps are
**sequential in one VM**. `needs:` is the gate.

---

## 🔁 CI vs CD

| | |
|---|---|
| **CI** | every push → auto build + test |
| **CD** = Delivery | always deployable, **human approves prod** ⭐ most companies |
| **CD** = Deployment | passing tests → straight to prod |

---

## 📄 Anatomy

```yaml
name: CI
on:                               # WHEN
  push:        { branches: [main] }
  pull_request:{ branches: [main] }
  workflow_dispatch:              # manual button
  schedule: [{ cron: '0 0 * * *' }]   # ⚠️ UTC, default branch only

concurrency:                      # ⭐ cancel superseded runs
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:                             # WHAT
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4       # ⭐ ALWAYS FIRST
      - uses: actions/setup-python@v5
        with: { python-version: '3.12', cache: 'pip' }
      - run: pip install -r requirements.txt
      - run: pytest -v
```

---

## 🧱 Jobs vs steps

| Job | Step |
|---|---|
| its **own fresh VM** | runs in the job's VM |
| **parallel** by default | always **sequential** |
| `needs:` to sequence | — |
| share files via **artifacts** | share files freely |

| | |
|---|---|
| `run:` | a shell command |
| `uses:` | a prebuilt action |
| `with:` | parameters to `uses:` |
| `if:` | condition |

> ⚠️ **Each `run:` is a new shell.** `cd foo` does **not** persist — use
> `working-directory:` or one `run: |` block. Env vars: write to `$GITHUB_ENV`.

---

## 🖥️ Runners

| GitHub-hosted | Self-hosted |
|---|---|
| **fresh VM every job** | persistent machine |
| free for public repos | your hardware |
| pre-installed: git, docker, python, node, java, go, aws, **kubectl, helm** | custom tooling, GPU, private network |
| | ⚠️ **never attach to a public repo** |

---

## 🧮 Matrix

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

⚠️ Multi-dimensional matrices multiply: 3 OS × 3 versions = **9 runners per push**.

---

## 🔑 Secrets

```yaml
- env: { DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }} }
  run: echo "$DOCKER_PASSWORD" | docker login -u u --password-stdin
```

| Scope | Available to |
|---|---|
| **Repository** | all workflows |
| **Environment** | ⭐ only jobs with `environment: production` (+ approval gates) |
| Organization | selected repos |

| | |
|---|---|
| `secrets.*` | encrypted, **masked** in logs, unreadable after saving |
| `vars.*` | plaintext config — regions, cluster names |
| **`GITHUB_TOKEN`** | ⭐ auto-provided, run-scoped; shape it with `permissions:` |

> ⚠️ **Masking is literal substring matching** — base64'd or line-split secrets are **not**
> masked. It's a safety net, not a control.
> ⚠️ **Fork PRs get no secrets** — by design.

---

## 📦 Artifacts

```yaml
- uses: actions/upload-artifact@v4
  if: always()                      # ⭐ upload even when the tests FAILED
  with: { name: test-results, path: test-results/, retention-days: 7 }

# later job
- needs: build                      # ⭐ required to download
- uses: actions/download-artifact@v4
  with: { name: test-results }
```

Retention: default 90 days, range 1–90.

---

## ⚡ Make it fast

```yaml
- uses: actions/setup-python@v5
  with: { cache: 'pip' }            # ⭐ one line

- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

⭐ The key hashes the **lockfile** — change a dependency, change the key. Plus:
`concurrency`, path filters, shallow checkout.

---

## 🧭 Contexts

| | |
|---|---|
| `github.sha` `.ref_name` `.actor` `.repository` `.event_name` | the event |
| `needs.build.outputs.tag` | ⭐ a value from an earlier job |
| `matrix.*` `runner.os` `vars.*` `secrets.*` | the rest |

```bash
echo "KEY=val"  >> "$GITHUB_ENV"       # env var for LATER steps
echo "key=val"  >> "$GITHUB_OUTPUT"    # this step's output
echo "## Done"  >> "$GITHUB_STEP_SUMMARY"
```

> ⭐ Tag images with `${GITHUB_SHA::7}`, never `:latest`.

---

## 🚀 Deploy stage

```yaml
deploy:
  needs: [test, build]
  if: github.ref == 'refs/heads/main'    # ⭐ PRs test, never deploy
  environment: production                 # ⭐ approval gate = Continuous Delivery
  steps:
    - run: helm upgrade --install app ./chart --set image.tag=${GITHUB_SHA::7} --atomic
```

**OIDC — stop storing cloud keys:**

```yaml
permissions: { id-token: write, contents: read }
- uses: aws-actions/configure-aws-credentials@v4
  with: { role-to-assume: arn:aws:iam::…:role/gha, aws-region: ap-south-1 }
```

---

## 🐞 Debug

```bash
gh run list ; gh run view <id> --log-failed ; gh run watch
```

| Symptom | Cause |
|---|---|
| never runs | wrong path/branch filter, bad YAML, cron not on default branch |
| `No such file` | **missing `actions/checkout`** |
| secret empty | fork PR, wrong name, or missing `environment:` |
| `cd` had no effect | each `run:` is a new shell |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Pipeline slow, work is 5 min? | **cache deps**, parallelise, add `concurrency` |
| `uses` vs `run`? | prebuilt action vs shell |
| Share files between jobs? | **artifacts** (+ `needs:`) |
| Stop PRs deploying? | `if: github.ref == 'refs/heads/main'` |
| Avoid storing AWS keys? | **OIDC** |

---

⬅️ [S15](./15_Helm.md) · ➡️ [S17 · DevSecOps](./17_Complete_CICD_and_DevSecOps.md)
