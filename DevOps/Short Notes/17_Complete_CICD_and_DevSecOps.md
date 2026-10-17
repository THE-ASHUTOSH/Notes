# ⚡ S17 · Complete CI/CD & DevSecOps

> *Revision card.* Full notes → [Session 17](../17_Complete_CICD_and_DevSecOps.md)

---

## 🔑 One-line core

***A scan is not a gate.*** `--exit-code 1` + `needs:` is what actually stops a bad build.

---

## 🔎 The four scans — know which sees what

| Scan | Looks at | Finds | Tool |
|---|---|---|---|
| **SAST** | **your source code** | SQLi, XSS, unsafe `eval` | **CodeQL**, Bandit, Semgrep |
| **SCA** | **your dependencies** | known CVEs in libraries | **pip-audit**, npm audit, Dependabot |
| **Secret scanning** | code **+ git history** | API keys, tokens | GitHub Secret Scanning, gitleaks |
| **Image scanning** | the **built container** | OS + library CVEs | **Trivy** |
| *(DAST)* | the **running app** | runtime / logic | OWASP ZAP |

> ⭐ **They do not overlap.** Clean source + current deps + a critical OpenSSL CVE in the
> base image is entirely possible.

---

## 🚧 The gate

```
Git push
   ├── test ──┐
   ├── SAST ──┼──▶ docker-build ──▶ image-scan ──▶ GATE ─┬─ FAIL → STOP
   └── SCA  ──┘                                           └─ PASS → push → deploy
```

```yaml
docker-build: { needs: [test, sast, sca] }   # ⭐ the gate
image-scan:   { needs: [docker-build] }
push:         { needs: [image-scan] }
deploy:       { needs: [push], if: github.ref == 'refs/heads/main' }
```

⭐ **test / SAST / SCA run in parallel** — one run surfaces all three failures.

---

## 🖼️ Trivy — report vs gate

```bash
trivy image myapp:tag                                        # a report
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:tag # ⭐ a GATE
trivy image --ignore-unfixed …     # only CVEs that HAVE a patch
trivy config .                     # ⭐ bad Dockerfiles / K8s YAML / Terraform
trivy fs .
```

> ⚠️ **Without `--exit-code 1` Trivy prints a wall of CVEs, exits 0, and the pipeline
> deploys happily.**
> ⚠️ `HIGH,CRITICAL` is a *starting threshold*, not a policy. `--ignore-unfixed` keeps it
> achievable — blocking on an unpatchable CVE just teaches people to bypass the gate.

⭐ **The cheapest fix is a smaller base image** — most findings are in OS packages your app
never calls.

---

## 📦 GHCR — zero stored credentials

```yaml
permissions: { contents: read, packages: write }   # ⭐ required

- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}          # ⭐ no secret to create
- run: |
    docker build -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
    docker push    ghcr.io/${{ github.repository }}:${{ github.sha }}
```

> ⚠️ **Jobs don't share a Docker daemon** — an image built in one job does **not** exist in
> the next. Rebuild, pass it as an artifact, or merge the jobs.

---

## 🔐 Secret leaked? The order matters

```
1. REVOKE / ROTATE          ⭐ FIRST, immediately
2. remove from code/history
3. audit logs for use
4. store the replacement properly
```

> ⚠️ **Deleting the line is not a fix.** Bots scrape GitHub within *seconds*; forks,
> clones, caches and the events API already have it. **Assume it is compromised.**

---

## ☸️ Deploy from CI

```yaml
- uses: azure/setup-kubectl@v4
- run: echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > ~/.kube/config
- run: kubectl set image deploy/app app=ghcr.io/${{ github.repository }}:${{ github.sha }}
- run: kubectl rollout status deploy/app      # ⭐ the real gate
- run: curl -sf http://localhost:5001/health  # ⭐ smoke test after rollout
```

| Way to deploy | Note |
|---|---|
| `kubectl set image` | quick — ⚠️ cluster now differs from Git |
| `sed` the tag + `kubectl apply` | YAML stays authoritative |
| ⭐ `helm upgrade --install --atomic` | versioned + auto-rollback |
| ⭐⭐ commit the tag, **Argo CD** syncs | cluster needs **no inbound credential** |

> ⚠️ **A GitHub-hosted runner cannot reach Kubernetes on your laptop.** Use a cloud
> cluster, a self-hosted runner, or GitOps.
> ⭐ `rollout status` is only honest if **readiness probes** exist.

---

## 🧱 Harden the image

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd -m -u 10001 appuser
USER appuser                 # ⭐ biggest single win
```

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: { drop: ["ALL"] }
```

---

## 🔭 Beyond the basics

| | Buys you |
|---|---|
| **SBOM** (`syft`, `trivy sbom`) | ⭐ answer *"are we affected?"* in seconds, not weeks |
| **cosign** | prove the image came from **your** pipeline |
| **OPA Gatekeeper / Kyverno** | the cluster refuses unsigned / root images |
| **Dependabot / Renovate** | opens the upgrade **PR**, not a report |
| **Branch protection** | ⭐ stops a human merging past the pipeline |

---

## ⚠️ Traps

- A scan without `--exit-code 1` is **theatre**
- `:latest` → you cannot say what's in production
- Auth at the edge + an open origin → the attacker **skips the edge**
- A clean SAST run ≠ secure (no runtime, no business logic)

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| SAST vs SCA? | your code vs your dependencies |
| Make Trivy block? | `--exit-code 1` |
| Push to GHCR needs? | `packages: write` + `GITHUB_TOKEN` |
| Secret pushed to GitHub? | **rotate first** |
| Deploy gate in K8s? | `kubectl rollout status` + a smoke test |

---

⬅️ [S16](./16_CICD_and_GitHub_Actions.md) · ➡️ [S18 · Terraform](./18_Terraform_and_IaC.md)
