# Session 17 — Complete CI/CD & DevSecOps 🔐

> **Topics:** Docker Build in Pipeline · Container Registry · Kubernetes Deployment · SAST ·
> SCA · Secret Scanning · Container Image Scanning · Security Gates
>
> 📁 Repo: `session-17-devsecops/` — folders `02-container-registry` → `08-security-gates`
> plus a complete `demo/` ("hey-cicd") Flask app with a seven-job `devsecops.yml` pipeline.

[Session 16](./16_CICD_and_GitHub_Actions.md) built a pipeline that proves the code *works*.
This one makes it prove the code is *safe* — and, crucially, **stops the pipeline when it
isn't**. Running a scanner is easy; acting on its result is DevSecOps.

---

## 📑 Table of Contents

1. [What DevSecOps Actually Means](#-what-devsecops-actually-means)
2. [The Four Scan Types](#-the-four-scan-types)
3. [Docker Build in the Pipeline](#-docker-build-in-the-pipeline)
4. [Container Registry (GHCR)](#-container-registry-ghcr)
5. [SAST — Static Application Security Testing](#-sast--static-application-security-testing)
6. [SCA — Software Composition Analysis](#-sca--software-composition-analysis)
7. [Secret Scanning](#-secret-scanning)
8. [Container Image Scanning (Trivy)](#-container-image-scanning-trivy)
9. [Security Gates](#-security-gates)
10. [Kubernetes Deployment from a Pipeline](#-kubernetes-deployment-from-a-pipeline)
11. [The Complete Pipeline (`devsecops.yml`)](#-the-complete-pipeline-devsecopsyml)
12. [Hardening the image itself](#-hardening-the-image-itself)
13. [Beyond the lab: DAST, SBOM, signing, policy](#-beyond-the-lab-dast-sbom-signing-policy)
14. [Key Terms Recap](#-key-terms-recap)
15. [Session Takeaways](#-session-takeaways)

---

## 🛡️ What DevSecOps Actually Means

The old model: build for six months, hand it to a security team for a two-week audit, panic.
A finding at that point costs 10–100× what it costs at commit time, because the design is
already set and the deadline has already passed.

**DevSecOps = shift security left**: every security check becomes a pipeline stage, running on
every commit, owned by the people who wrote the code.

```
Detect  ──▶  Evaluate  ──▶  Enforce  ──▶  Remediate  ──▶  Deploy
  │            │              │
scanners    policy      ⭐ the gate
```

⭐ **The mindset shift:** the goal is not to *run* security tools. It's to let their results
**control delivery according to a defined policy**. A scanner whose output nobody acts on is
a log file, not a control.

> This is the DevSecOps/shift-left idea introduced back in
> [Session 1](./01_Introduction_to_DevOps_and_Microservices.md), now made concrete.

---

## 🔎 The Four Scan Types

The single most important table in this session — know which tool looks at *what*:

| Scan | Looks at | Finds | Tool here |
|---|---|---|---|
| **SAST** | **your source code** | SQL injection, XSS, unsafe `eval`, hardcoded crypto | **CodeQL** |
| **SCA** | **your dependencies** | known CVEs in Flask, requests, lodash… | **pip-audit** |
| **Secret scanning** | **code + git history** | API keys, tokens, private keys | **GitHub Secret Scanning** |
| **Image scanning** | **the built container image** | vulnerable OS packages & libraries | **Trivy** |

```
Source code      ──▶  SAST
Dependencies     ──▶  SCA
Credentials      ──▶  Secret scanning
Container image  ──▶  Image scanning
```

⭐ **They don't overlap, and you need all four.** Your source can be spotless (SAST clean),
every dependency current (SCA clean), and the image still ship a critical OpenSSL CVE from the
base image. Each one sees a layer the others can't.

---

## 🐳 Docker Build in the Pipeline

```yaml
- name: Build Docker image
  run: docker build -t session17-python:${{ github.sha }} .
```

⭐ **Tag with `${{ github.sha }}`, never `:latest`.** The tag is the only link between "what is
running" and "which commit produced it". With `:latest` you can't roll back with confidence,
can't reproduce a bug, and can't answer "is the fix deployed?".

> ⚠️ **Jobs don't share a Docker daemon.** Each job is a fresh VM
> ([Session 16](./16_CICD_and_GitHub_Actions.md)), so an image built in `docker-build` does
> **not** exist in `image-scan`. The repo's pipeline handles this by simply rebuilding — which
> works and is honest, but wastes time. Better options:
> - build once and `docker save` → upload as an artifact → `docker load` in the next job, or
> - ⭐ **merge build + scan + push into one job** (fewest moving parts), or
> - push to the registry first with a `pr-<sha>` tag and scan it there.

For real pipelines, use Buildx with a layer cache:

```yaml
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v6
  with:
    push: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

---

## 📦 Container Registry (GHCR)

An image on the runner's disk is useless — Kubernetes pulls from a **registry**.

```
Docker Build ──▶ Image ──▶ GHCR ──▶ Kubernetes
```

```text
ghcr.io/OWNER/REPOSITORY:TAG
ghcr.io/my-user/session17-devsecops-python:8a72f31
```

```yaml
permissions:
  contents: read
  packages: write          # ⭐ required to publish to GHCR

steps:
  - name: Login to GHCR
    uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}    # ⭐ no secret to create

  - run: |
      docker build -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
      docker push    ghcr.io/${{ github.repository }}:${{ github.sha }}
```

⭐ **GHCR + `GITHUB_TOKEN` means zero stored registry credentials.** Docker Hub needs a
`DOCKERHUB_TOKEN` secret (and has anonymous pull rate limits); GHCR comes free with the repo.

> 🐛 The repo is inconsistent here: `02-container-registry/README.md` teaches GHCR, but the
> `demo/devsecops.yml` `push` job logs in to **Docker Hub** with a hard-coded username and a
> `DOCKERHUB_TOKEN` secret. Either is fine in practice — just pick one. GHCR is the simpler
> teaching choice, and a hard-coded username in YAML should be `vars.DOCKERHUB_USERNAME`.

Verify afterwards: repo → **Packages** → confirm the tag matches the commit SHA.

---

## 🧬 SAST — Static Application Security Testing

Analyses **source code without running it**, looking for dangerous patterns.

```
Source Code ──▶ SAST Tool ──▶ Security Analysis ──▶ Findings
```

```yaml
sast:
  name: SAST - CodeQL
  runs-on: ubuntu-latest
  permissions:
    contents: read
    security-events: write       # ⭐ needed to publish to the Security tab
  steps:
    - uses: actions/checkout@v4
    - uses: github/codeql-action/init@v3
      with:
        languages: python
    - uses: github/codeql-action/analyze@v3
```

Results land in repo → **Security → Code scanning**, with file and line. CodeQL is free for
public repos and supports Python, JS/TS, Java, Go, C/C++, C#, Ruby, Swift, Kotlin.

Other SAST tools you'll meet: **Bandit** (Python-specific, fast), **Semgrep** (rule-based,
language-agnostic), **SonarQube** (quality + security), **gosec**, **ESLint security plugins**.

> ⚠️ **A clean SAST result does not mean the application is secure.** SAST cannot see runtime
> behaviour, business-logic flaws, or broken authorisation — and it produces false positives,
> which is why a gate on SAST needs a policy ("block on `error` severity") rather than
> "block on anything".

---

## 📚 SCA — Software Composition Analysis

Your code is maybe 10% of what ships. The other 90% is dependencies — and their CVEs are
*public*, which makes them the easiest thing in the world for an attacker to look up.

```
SAST → your source code
SCA  → your dependencies
```

```bash
pip install pip-audit
pip-audit                      # reads requirements.txt / the environment
pip-audit --fix                # bump to fixed versions where possible
```

```yaml
sca:
  name: SCA - Dependency Scan
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pip-audit
    - run: pip-audit
```

### Remediation flow

```
Vulnerability found ──▶ identify package + version ──▶ find the fixed version
   ──▶ update the dependency ──▶ run tests ──▶ re-run SCA
```

⭐ **"Run tests" is not optional.** A security bump is still a dependency upgrade and can
break you. This is exactly why SCA belongs *in* the pipeline, next to the tests.

Equivalents elsewhere: `npm audit` / `yarn audit`, `govulncheck`, OWASP Dependency-Check,
Snyk, and **Dependabot** (GitHub's built-in — it opens the upgrade PR for you, which is strictly
better than a report nobody reads).

> ⭐ **Lockfiles matter.** `requirements.txt` with `==` pins, `package-lock.json`,
> `Chart.lock` — without them, SCA scanned one version and production runs another.

---

## 🔑 Secret Scanning

```python
AWS_ACCESS_KEY = "real-secret-value"       # ❌ never
```

```python
import os
api_key = os.getenv("API_KEY")             # ✅
```

```yaml
${{ secrets.API_KEY }}                      # ✅ in GitHub Actions
```

What counts as a secret: API keys, passwords, access tokens, private keys, cloud credentials,
database connection strings.

**GitHub Secret Scanning** matches known credential patterns in repository content;
**push protection** can block a supported secret *before* it reaches the remote. Enable both
(Settings → Code security). Other tools: **gitleaks**, **trufflehog**, **detect-secrets**
(the last works nicely as a pre-commit hook — the earliest possible gate).

### ⭐ If a real secret leaks, deleting the line is not a fix

```
Secret exposed
     ↓
1. REVOKE / ROTATE the credential   ← do this FIRST, immediately
     ↓
2. Remove it from code and history as required
     ↓
3. Check logs for unauthorised use
     ↓
4. Store the replacement properly (secret manager / Actions secret)
```

**Why rotation first:** a pushed commit is public the instant it lands. Bots scrape GitHub for
credentials within *seconds*. Rewriting history (`git filter-repo`, BFG) doesn't help — forks,
clones, caches and the GitHub events API already have it. **Assume it is compromised.**

Three questions worth being able to answer:
1. *Why not store secrets in source code?* Git keeps everything forever, and anyone with read
   access — or any fork — has them.
2. *Actions secret vs source-code secret?* An Actions secret is encrypted at rest, injected at
   runtime, masked in logs, and never in the repo. A source-code secret is plaintext, permanent,
   and distributed with every clone.
3. *A real cloud key got pushed?* Rotate first, then clean, then audit for use.

---

## 🖼️ Container Image Scanning (Trivy)

Your code can be clean while the image is not. The image also contains:

- OS packages (`glibc`, `openssl`, `zlib`…)
- Language runtime and its libraries
- Anything the base image shipped

```bash
docker build -t session17-python:1.0 .
trivy image session17-python:1.0

trivy image --severity HIGH,CRITICAL session17-python:1.0

# ⭐ make it a GATE
trivy image --severity HIGH,CRITICAL --exit-code 1 session17-python:1.0
```

```
Docker Build ──▶ Trivy Scan ──▶ findings?
                                 ╱      ╲
                              FAIL      PASS
                               ↓          ↓
                              STOP     Continue
```

⭐ **`--exit-code 1` is the whole difference between a report and a gate.** Without it Trivy
prints a wall of CVEs, exits 0, and the pipeline cheerfully deploys.

> 🐛 The repo's `demo/devsecops.yml` runs
> `trivy image --severity HIGH,CRITICAL session17-python:${{ github.sha }}` — **without
> `--exit-code 1`**. So despite the `08-security-gates` lesson, that job can never fail the
> pipeline. Add the flag to make the lab match the lesson.

Practical flags:

```bash
trivy image --ignore-unfixed ...          # ⭐ only CVEs that actually have a patch
trivy image --exit-code 1 --severity CRITICAL ...   # start strict-but-achievable
trivy fs .                                 # scan the filesystem / repo
trivy config .                             # ⭐ misconfigured Dockerfiles, K8s YAML, Terraform
```

Or use the action, which also uploads to the Security tab:

```yaml
- uses: aquasecurity/trivy-action@0.28.0
  with:
    image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
    severity: HIGH,CRITICAL
    exit-code: '1'
    ignore-unfixed: true
```

> ⚠️ `HIGH,CRITICAL` is a **classroom threshold, not a security policy**. Real thresholds
> depend on exposure and risk appetite. `--ignore-unfixed` is the pragmatic starting point —
> blocking on a CVE with no available patch just teaches the team to bypass the gate.

**The cheapest fix is almost always a smaller base image.** `python:3.12-slim` → `-alpine` or
distroless removes most of the CVE surface, because most findings are in OS packages your app
never calls ([Session 7](./07_Docker_Images_and_Dockerfile.md)).

---

## 🚧 Security Gates

A scan **finds** a problem. A gate **decides what happens next**.

```
Without a gate:                     With a gate:
  SCA finds vulnerability             Security check
        ↓                                   ↓
  Pipeline continues                   ┌────┴────┐
        ↓                            PASS      FAIL
  Build → Push → Deploy  😬            ↓         ↓
                                   Continue    STOP
```

In GitHub Actions the gate is built from two things:

1. **`needs:`** — the dependency graph
2. **a non-zero exit code** — the failure signal

```yaml
docker-build: { needs: [test, sast, sca] }
image-scan:   { needs: [docker-build] }
push:         { needs: [image-scan] }
deploy:       { needs: [push] }
```

```
Git Push
   ↓
Unit Tests ──┐
SAST ────────┼──▶ Docker Build ──▶ Image Scan ──▶ GATE ──┬── FAIL → STOP
SCA ─────────┘                                            └── PASS
                                                               ↓
                                                          GHCR Push
                                                               ↓
                                                      Kubernetes Deploy
                                                               ↓
                                                     Rollout Verification
```

⭐ Note that **test, SAST and SCA run in parallel** — they're independent, so all three
failures surface in one run instead of one per push.

### What to gate on

| Check | Typical pipeline behaviour |
|---|---|
| Unit tests | ⭐ Always blocking |
| Build | Always blocking (it can't continue anyway) |
| SAST | Blocking per policy (e.g. `error` severity only) |
| SCA | Blocking per policy (e.g. HIGH+ **with a fix available**) |
| Secret scanning | Push protection blocks at push time |
| Image scan | Blocking above a defined severity |
| Registry push | Blocking — no image, nothing to deploy |
| K8s rollout | ⭐ Blocking — `rollout status` must succeed |

> ⚠️ **Gate design is a real decision, not a default.** Too loose and it's theatre; too strict
> and developers add `continue-on-error: true` and you've lost the signal entirely. Start with
> *critical, fixable* findings blocking and everything else reporting, then tighten.

---

## ☸️ Kubernetes Deployment from a Pipeline

**`k8s/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devsecops-python
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devsecops-python
  template:
    metadata:
      labels:
        app: devsecops-python
    spec:
      containers:
        - name: devsecops-python
          image: ghcr.io/OWNER/REPOSITORY:TAG
          ports:
            - containerPort: 5000
          readinessProbe:
            httpGet: { path: /health, port: 5000 }
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet: { path: /health, port: 5000 }
            initialDelaySeconds: 10
            periodSeconds: 20
```

⭐ The probes aren't decoration. Without a **readiness** probe, `kubectl rollout status`
returns success as soon as the containers *start*, so a broken deploy reports green
([Session 13](./13_Kubernetes_Storage_HPA_and_Probes.md)).

**`k8s/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: devsecops-python-service
spec:
  type: NodePort
  selector:
    app: devsecops-python
  ports:
    - port: 5000
      targetPort: 5000
      nodePort: 30080
```

```bash
kubectl apply -f k8s/
kubectl get deployment,pods,service
kubectl port-forward svc/devsecops-python-service 8080:5000
curl http://localhost:8080/health
```

### The deploy job

```yaml
deploy:
  needs: [push]
  runs-on: ubuntu-latest
  environment: { name: development }
  steps:
    - uses: actions/checkout@v4
    - uses: azure/setup-kubectl@v4
      with: { version: latest }

    - name: Configure Kubernetes
      run: |
        mkdir -p ~/.kube
        echo "${{ secrets.KUBE_CONFIG }}" | base64 --decode > ~/.kube/config

    - name: Update application image
      run: |
        kubectl set image deployment/devsecops-python \
          devsecops-python=ghcr.io/${{ github.repository }}:${{ github.sha }}

    - name: Wait for rollout
      run: kubectl rollout status deployment/devsecops-python     # ⭐ the real gate

    - run: kubectl get deployment devsecops-python && kubectl get pods
```

Two ways to point a Deployment at the new image:

| Approach | Note |
|---|---|
| `kubectl set image` | Imperative, quick — but the cluster now differs from Git ⚠️ |
| `sed` the tag into the YAML, then `kubectl apply` | What the demo does; keeps YAML authoritative |
| ⭐ `helm upgrade --install --set image.tag=$SHA --atomic` | [Session 15](./15_Helm.md) — versioned, with automatic rollback |
| ⭐⭐ Commit the tag to a Git repo, let **Argo CD** sync | [Session 20](./20_Monitoring_Observability_and_GitOps.md) — the cluster never needs a credential |

### ⚠️ The classroom caveat (and a real production truth)

A GitHub-hosted runner **cannot reach Kubernetes on your laptop** (Docker Desktop, Kind,
minikube) — it's a VM in a datacentre, your cluster is behind NAT.

```
GitHub Actions  ──▶  Build + Security + GHCR     ✅ works
Local Kubernetes ──▶  manual deployment practice  ✅ works
GitHub Actions  ──▶  your laptop's cluster        ❌ never
```

Real options: a reachable cloud cluster, a **self-hosted runner** inside the network, or —
best — **GitOps pull-based deployment**, where an agent *inside* the cluster pulls changes and
no inbound access is ever needed. The demo sidesteps it neatly by spinning up a throwaway Kind
cluster **on the runner itself** (`helm/kind-action`) purely to prove the manifests apply.

---

## 🧷 The Complete Pipeline (`devsecops.yml`)

The demo's seven jobs, end to end:

```
Push to GitHub
      │
 ┌────▼────┐
 │ 1 Tests │  pytest --cov            ─┐
 └─────────┘                           │
 ┌─────────┐                           ├─ parallel
 │ 2 SAST  │  CodeQL                   │
 └─────────┘                           │
 ┌─────────┐                           │
 │ 3 SCA   │  pip-audit               ─┘
      │  (all three must pass)
 ┌────▼────┐
 │ 4 Build │  docker build
 └────┬────┘
 ┌────▼────┐
 │ 5 Scan  │  Trivy HIGH,CRITICAL
 └────┬────┘
 ┌────▼────┐
 │ 6 Push  │  registry (GHCR / Docker Hub)
 └────┬────┘   only on push to main
 ┌────▼────┐
 │7 Deploy │  kubectl apply + rollout status + curl smoke test
 └─────────┘
```

Key fragments:

```yaml
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=app --cov-report=term-missing

  docker-build:
    needs: [test, sast, sca]           # ⭐ the gate
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t session17-python:${{ github.sha }} .

  deploy:
    needs: [push]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'   # ⭐ never from a PR
    steps:
      - uses: helm/kind-action@v1.10.0        # throwaway cluster on the runner
      - run: sed -i "s|__IMAGE_TAG__|${{ github.sha }}|g" k8s/deployment.yaml
      - run: kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
      - run: kubectl rollout status deployment/session17-python --timeout=60s
      - run: |
          kubectl port-forward service/session17-python 5001:80 &
          sleep 3
          curl -s http://localhost:5001/api/status      # ⭐ smoke test
```

⭐ Two details worth copying:
- **`if: github.ref == 'refs/heads/main' && github.event_name == 'push'`** — a PR must run
  every check but must never deploy.
- **The `curl` smoke test after rollout.** "The Pods are Ready" and "the app answers correctly"
  are different claims. Verify the second one.

The app itself (`hey-cicd`) is a Flask dashboard with `/health`, `/api/status`,
`/api/greet/<name>`, `/api/add`, `/api/calculate` and `/api/pipeline/run`, covered by 8 pytest
tests — small enough to read, real enough to scan.

---

## 🧱 Hardening the image itself

The demo's Dockerfile is minimal and makes a useful before/after:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
EXPOSE 5001
CMD ["python", "app/app.py"]
```

✅ It gets the big thing right — `COPY requirements.txt` **before** the source, so the
dependency layer stays cached ([Session 7](./07_Docker_Images_and_Dockerfile.md)).

What a scanner-friendly version adds:

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt    # ⭐ don't ship the pip cache

COPY app ./app

RUN useradd -m -u 10001 appuser                        # ⭐ non-root
USER appuser

EXPOSE 5001
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:5001/health')"
CMD ["python", "app/app.py"]
```

| Change | Why |
|---|---|
| `USER appuser` | ⭐ Container escape as root = root on the node. Biggest single win. |
| `--no-cache-dir` | Smaller image, fewer files for a scanner to flag |
| Pinned versions in `requirements.txt` | Reproducible builds; SCA scans what actually ships |
| `-slim` / `-alpine` / distroless | Fewer OS packages = dramatically fewer CVEs |
| `HEALTHCHECK` | Docker-level liveness; mirrors the K8s probe |

And in Kubernetes, the manifest-level equivalent:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: { drop: ["ALL"] }
```

> `trivy config .` will flag most of these omissions in your Dockerfile and K8s YAML
> automatically — misconfiguration scanning, alongside vulnerability scanning.

---

## 🔭 Beyond the lab: DAST, SBOM, signing, policy

| Practice | What it adds |
|---|---|
| **DAST** (OWASP ZAP) | Tests the **running** app — the one thing SAST structurally cannot do |
| **SBOM** (`syft`, `trivy sbom`) | A machine-readable parts list of the image. When the next Log4Shell lands, you answer "are we affected?" in seconds instead of weeks |
| **Image signing** (Sigstore **cosign**) | Proves *this* image came from *your* pipeline — supply-chain integrity |
| **Admission policy** (OPA Gatekeeper, Kyverno) | The cluster itself refuses unsigned / root / unscanned images |
| **IaC scanning** (`trivy config`, tfsec, Checkov) | Finds the public S3 bucket before Terraform creates it ([Session 18](./18_Terraform_and_IaC.md)) |
| **Dependabot / Renovate** | Opens the upgrade PR instead of filing a report |
| **Branch protection** | Required status checks — ⭐ the gate that stops a human merging past the pipeline |
| **OWASP Top 10** | The shared vocabulary for what all of this is defending against |

⭐ **Defence in depth:** pre-commit hook → CI gates → registry scan → admission control →
runtime monitoring. Any single layer will be bypassed eventually; the stack is the control.

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **DevSecOps** | Security as an automated, every-commit pipeline stage owned by developers |
| **Shift left** | Find problems at commit time, where they're 10–100× cheaper to fix |
| **SAST** | Static analysis of **source code**; CodeQL, Bandit, Semgrep |
| **SCA** | Scanning **dependencies** for known CVEs; pip-audit, npm audit, Dependabot |
| **Secret scanning** | Detecting credentials in code/history; push protection blocks them pre-push |
| **Image scanning** | CVEs in the built **container image**'s OS and language packages; Trivy |
| **DAST** | Testing the **running** application; OWASP ZAP |
| **CVE** | A publicly catalogued vulnerability with a severity rating |
| **Security gate** | A check whose failure **stops** the pipeline — `needs:` + a non-zero exit code |
| **`--exit-code 1`** | ⭐ What turns a Trivy report into a gate |
| **GHCR** | GitHub Container Registry; authenticates with the free `GITHUB_TOKEN` |
| **`packages: write`** | The workflow permission required to publish to GHCR |
| **`kubectl set image`** | Imperative image update that triggers a rolling update |
| **`kubectl rollout status`** | Blocks until the rollout completes — the deploy-stage gate |
| **SBOM** | Software Bill of Materials — the image's parts list |
| **cosign** | Sigstore tool for signing and verifying container images |

---

## 🎯 Session Takeaways

1. ⭐ **Four scans, four different layers: SAST = your code, SCA = your dependencies, secret scanning = your credentials, image scanning = your container.** You need all four.
2. ⭐ **A scan is not a gate.** `--exit-code 1` plus `needs:` is what actually stops a bad build — and the repo's own Trivy step is missing it.
3. **Run test, SAST and SCA in parallel; everything else sequentially behind `needs:`.** One run surfaces every problem.
4. ⭐ **Tag images with the commit SHA.** `:latest` makes rollback, reproduction and "is the fix live?" unanswerable.
5. **Each job is a fresh VM** — an image built in one job doesn't exist in the next. Rebuild, pass it as an artifact, or merge the jobs.
6. **GHCR + `GITHUB_TOKEN` + `packages: write`** gives you a registry with no stored credentials.
7. ⭐ **A leaked secret is compromised the moment it's pushed. Rotate first**, then clean history, then audit. Deleting the line does nothing.
8. **`kubectl rollout status` is the deploy gate**, and it's only honest if readiness probes exist. Add a `curl` smoke test after it.
9. **`if: github.ref == 'refs/heads/main' && github.event_name == 'push'`** — PRs run every check, deploy nothing.
10. ⭐ **The cheapest security fix is a smaller base image and a non-root `USER`.** Most CVEs live in OS packages you never call.
11. **A clean SAST run does not mean secure.** No single tool sees business logic, runtime behaviour and dependencies at once.
12. **Set thresholds you'll actually keep** (`--severity HIGH,CRITICAL --ignore-unfixed` is a sane start). A gate everyone bypasses is worse than no gate.

---

## 🔗 References

- GitHub Container Registry — https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- Automatic token authentication — https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- CodeQL / code scanning — https://docs.github.com/en/code-security/code-scanning
- Secret scanning & push protection — https://docs.github.com/en/code-security/secret-scanning
- Dependabot — https://docs.github.com/en/code-security/dependabot
- pip-audit — https://pypi.org/project/pip-audit/
- Trivy — https://trivy.dev/ · https://aquasecurity.github.io/trivy/
- `kubectl set image` / rolling updates — https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Pod Security Standards — https://kubernetes.io/docs/concepts/security/pod-security-standards/
- OWASP Top 10 — https://owasp.org/www-project-top-ten/
- OWASP ZAP (DAST) — https://www.zaproxy.org/
- Sigstore / cosign — https://docs.sigstore.dev/

---

## ➡️ Next

[Session 18 — Terraform & Infrastructure as Code](./18_Terraform_and_IaC.md) — the pipeline
can now build, scan and deploy. Next: create the infrastructure it deploys onto, in code.
