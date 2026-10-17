# ⚡ S21 · Final DevOps Project

> *Revision card.* Full notes → [Session 21](../21_Final_DevOps_Project.md)

---

## 🔑 One-line core

***The chain is the deliverable.*** Each tool exists because the previous one created a
problem.

---

## 🔗 The whole pipeline

```
Developer
   │
Git / GitHub                         ← S05
   │
GitHub Actions                       ← S16
   ├── pytest
   ├── frontend build
   ├── docker build                  ← S06-07
   ├── Trivy scan                    ← S17
   └── push → GHCR
          │
     Terraform → AWS VPC + EKS       ← S18-19
          │
        Helm                         ← S15
          │
   ┌──────┴──────┐
Frontend     Backend                 ← S09-13
 React        FastAPI
   └──────┬──────┘
    PostgreSQL
          │
   Prometheus → Grafana              ← S20
          │
   …and S14 when it breaks
```

---

## 🩺 `/health` vs `/ready` — the distinction that matters

| | Question | Probe | Failure means |
|---|---|---|---|
| `/health` | *is the process alive?* | **liveness** | ⭐ **restart the container** |
| `/ready` | *can it serve traffic now?* | **readiness** | ⭐ **drop from endpoints** |

```python
@app.get("/health")
def health(): return {"status": "UP"}          # cheap, NO dependencies

@app.get("/ready")
def ready(db = Depends(get_db)):
    db.execute(select(func.count(Task.id)))    # ⭐ actually touches the DB
    return {"status": "READY"}
```

> ⚠️ **Never check the database in a liveness probe.** A DB blip then restarts your whole
> fleet — a recoverable outage becomes a self-inflicted one.

---

## 🐳 The two Dockerfiles

**Backend** — single stage, non-root:

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1   # ⭐ logs appear immediately
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --create-home --uid 10001 appuser
COPY app ./app
USER 10001                                        # ⭐
CMD ["sh","-c","alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

**Frontend** — multi-stage:

```dockerfile
FROM node:22-alpine AS build
RUN npm ci && npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

⭐ **~1.1 GB toolchain → ~50 MB runtime**, and far fewer CVEs.

> ⚠️ Running migrations in `CMD` means **every replica** tries to migrate. Correct
> pattern: a Helm **`pre-upgrade` hook Job** or an **initContainer**.

---

## 🚦 The four gates

```yaml
test:            {}                                   # 1
build-scan-push: { needs: test }                      # 2 ⭐ gate
  - trivy: { exit-code: '1', ignore-unfixed: true }   # 3 ⭐ gate
deploy:
  needs: build-scan-push
  if: github.ref == 'refs/heads/main'                 # 4 ⭐ PRs never deploy
  run: helm upgrade --install … --set image.tag=${{ github.sha }}
```

⭐ **`${{ github.sha }}` everywhere** — commit A → image A → release A. That traceability
is what makes rollback exact.

---

## ☁️ Terraform — two modules, ~60 resources

```hcl
module "vpc" {                           # 2 AZs
  public_subnets  = ["10.20.101.0/24", "10.20.102.0/24"]   # ALB + NAT
  private_subnets = ["10.20.1.0/24",   "10.20.2.0/24"]     # ⭐ worker nodes
  enable_nat_gateway = true
  single_nat_gateway = true              # ⚠️ cheaper, one AZ is an SPOF
}
module "eks" {
  subnet_ids = module.vpc.private_subnets
  eks_managed_node_groups = { main = { instance_types = ["t3.medium"], min_size = 2 } }
}
```

> 💰 **`terraform destroy` when done.** EKS control plane + 2 nodes + NAT + ALB is real
> money, billed hourly.
> 💡 In production the DB would be **RDS**, not a Pod.

---

## ☸️ Helm chart essentials

```yaml
replicaCount: 2
hpa: { enabled: true, minReplicas: 2, maxReplicas: 6, targetCPUUtilizationPercentage: 60 }
resources:
  requests: { cpu: 100m, memory: 256Mi }   # ⭐ MANDATORY for HPA
  limits:   { cpu: 500m, memory: 512Mi }
monitoring: { serviceMonitor: { enabled: true } }
```

⭐ **ServiceMonitor** = a CRD saying *"scrape Services with these labels"* — declarative
monitoring. Its `port` is the Service's **port NAME**, and the `release:` label must match
your Prometheus Operator release.

---

## 🐛 The bugs in the reference chart (find these)

| # | Bug |
|---|---|
| **1** | `_helpers.tpl` makes `fullname` = `<release>-taskboard`, so the Service is `taskboard-taskboard-backend` — but the **Ingress hard-codes `taskboard-backend`** → silent **503** |
| **2** | Ingress targets **port 8080**; the backend Service listens on **8000** |
| **3** | Frontend image never sets a non-root `USER` |
| **4** | Postgres is a **Deployment** with an **RWO PVC** — a rolling update deadlocks. Use a **StatefulSet** |
| **5** | `replicas:` hard-coded alongside an HPA — they fight on every upgrade |

> ⭐ **`helm template` would have shown bugs 1 and 2 in five seconds.** `helm install`
> reports *success* for both.

---

## 🎬 Demo path

app → `/docs` → DB → commit → CI → images → Trivy → GHCR → Terraform → `kubectl get pods`
→ `helm list` → Ingress → HPA under load → Grafana → **break something and fix it live**.

⭐ **That last step is the one that proves understanding.** Anyone can demo a green
pipeline.

---

## 🧭 Build order (always have something that runs)

```
1 app + tests locally
2 Dockerfiles + docker compose up
3 Git + CI that just runs tests
4 add build + push to GHCR with SHA tags
5 add Trivy with exit-code 1
6 Helm chart → deploy to KIND locally     ⭐ debug here, not on EKS
7 Terraform VPC + EKS → deploy there
8 Ingress + HPA
9 Prometheus + Grafana
10 break it on purpose
```

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| `/health` vs `/ready`? | alive (restart) vs serving (drop from endpoints) |
| Why SHA tags? | rollback, bisection, "what's running?" |
| Image built in job 1, missing in job 2? | **each job is a fresh VM** |
| HPA shows `<unknown>`? | no CPU **requests** / no Metrics Server |
| Ingress returns 503? | service **name or port** mismatch — `get endpoints` |
| Where do you debug a chart? | ⭐ **kind, before EKS** |

---

## 🏁 The course in one line each

```
01 why · 02-04 the ground · 05 source of truth · 06-08 package it
09-14 run, expose, scale, debug it · 15 package the packaging
16-17 automate & secure · 18-19 create what it runs on
20 see it & reconcile it · 21 all of it at once
```

---

⬅️ [S20](./20_Monitoring_Observability_GitOps.md) · ⬆️ [All short notes](./README.md)
