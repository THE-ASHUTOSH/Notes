# Session 21 — Final DevOps Project 🎓

> **Topics:** Application → GitHub · Dockerize · CI/CD Pipeline · Security Scan ·
> Deploy to Kubernetes · Helm · Ingress · HPA · Monitoring · Troubleshooting
>
> 📁 Repo: `session21-python/` — **TaskBoard**, a React + FastAPI + PostgreSQL application
> carried all the way from `docker compose up` to a monitored EKS cluster.

Every previous session taught one tool. This one shows how a real application travels from a
developer's laptop to a monitored Kubernetes environment — and, just as importantly, what
breaks on the way.

---

## 📑 Table of Contents

1. [The Whole Pipeline at a Glance](#-the-whole-pipeline-at-a-glance)
2. [What the capstone integrates](#-what-the-capstone-integrates)
3. [The Application](#-the-application)
4. [Running it locally — Docker Compose](#-running-it-locally--docker-compose)
5. [Testing — the first gate](#-testing--the-first-gate)
6. [Docker — two very different images](#-docker--two-very-different-images)
7. [CI/CD — the three-stage pipeline](#-cicd--the-three-stage-pipeline)
8. [Terraform — VPC + EKS](#-terraform--vpc--eks)
9. [Kubernetes & the Helm chart](#-kubernetes--the-helm-chart)
10. [Ingress, HPA & the database](#-ingress-hpa--the-database)
11. [Monitoring — ServiceMonitor → Prometheus → Grafana](#-monitoring--servicemonitor--prometheus--grafana)
12. [Troubleshooting lab](#-troubleshooting-lab)
13. [⭐ Bugs in the reference chart (read this)](#-bugs-in-the-reference-chart-read-this)
14. [The demo path](#-the-demo-path)
15. [Building your own](#-building-your-own)
16. [Key Terms Recap](#-key-terms-recap)
17. [Session Takeaways](#-session-takeaways)

---

## 🗺️ The Whole Pipeline at a Glance

```text
Developer
   │
   ▼
Git / GitHub                                      ← Session 5
   │
   ▼
GitHub Actions                                    ← Session 16
   ├── pytest
   ├── frontend build
   ├── Docker build                               ← Sessions 6–7
   ├── Trivy scan                                 ← Session 17
   └── push images to GHCR
              │
              ▼
        Terraform                                 ← Sessions 18–19
              │
       AWS VPC + EKS
              │
              ▼
            Helm                                  ← Session 15
              │
      ┌───────┴────────┐
      │                │
   Frontend          Backend                      ← Sessions 9–13
    React            FastAPI
      │                │
      └──────┬─────────┘
             ▼
        PostgreSQL
             │
        Prometheus                                ← Session 20
             │
          Grafana
                                                  ← Session 14 when it breaks
```

⭐ **The point is not the tools; it's the chain.** Any single link failing stops delivery, and
each link exists because the one before it created a problem: containers needed orchestration,
orchestration needed packaging, packaging needed automation, automation needed security gates,
and all of it needed somewhere to run and something watching it.

---

## 🧩 What the capstone integrates

| Module | What it proves | Session |
|---|---|---|
| **Application** | Frontend + backend + database, ≥4 REST endpoints, migrations | — |
| **Testing** | pytest covering multiple endpoints, against a test DB | 3, 16 |
| **Git & GitHub** | Meaningful history, working `.gitignore` | 5 |
| **Docker** | Both images build; frontend is multi-stage; non-root | 6, 7 |
| **CI/CD** | Pipeline on push to `main`; tests gate the build; SHA-tagged images in GHCR | 16 |
| **DevSecOps** | Trivy on both images, failing on HIGH/CRITICAL | 17 |
| **Terraform** | VPC with public + private subnets, EKS with a node group, clean destroy | 18, 19 |
| **Kubernetes + Helm** | Chart deploys both tiers with Services, Ingress and ≥2 replicas | 9–13, 15 |
| **Observability** | `/metrics` scraped by Prometheus, visible in Grafana | 20 |
| **Documentation** | A README plus a live commit → pipeline → deployment demo | — |

---

## 🧱 The Application

**TaskBoard** — a SaaS-style project management app:

```text
React + Vite frontend  ·  FastAPI backend  ·  PostgreSQL
SQLAlchemy ORM  ·  Alembic migrations  ·  pytest
```

```text
session21-devops-capstone-final/
├── frontend/              React application and CSS
├── backend/
│   ├── app/               API, models, schemas, DB config
│   ├── tests/             pytest
│   └── alembic/           DB migrations
├── docker-compose.yml     full local stack
├── terraform/             AWS VPC + EKS
├── helm/taskboard/        Kubernetes package
├── k8s/                   namespace / bootstrap manifests
├── monitoring/            Prometheus/Grafana values
├── troubleshooting/       deliberately broken manifests
├── scripts/               load-test helpers
└── .github/workflows/     CI/CD
```

### The API

```text
GET    /                 service info
GET    /health           liveness
GET    /ready            readiness
GET    /metrics          Prometheus

GET    /api/tasks
GET    /api/tasks/stats
GET    /api/tasks/{id}
POST   /api/tasks
PUT    /api/tasks/{id}
DELETE /api/tasks/{id}
```

Swagger at `/docs`.

### ⭐ `/health` vs `/ready` — the distinction that matters

| Endpoint | Question | Used by | Failure means |
|---|---|---|---|
| `/health` | *Is the process alive?* | **liveness** probe | restart the container |
| `/ready` | *Can it serve traffic right now?* | **readiness** probe | remove from Service endpoints |

```python
@app.get("/health")
def health():
    return {"status": "UP"}                 # cheap — no dependencies

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(select(func.count(Task.id)))  # ⭐ actually touches the database
    return {"status": "READY"}
```

⭐ **Never check the database in a liveness probe.** If the DB blips, every Pod fails liveness
and Kubernetes restarts the entire fleet — turning a recoverable dependency outage into a
self-inflicted one. Readiness is the right place: pods leave the load balancer and come back
when the DB does. Straight from
[Session 13](./13_Kubernetes_Storage_HPA_and_Probes.md).

`/metrics` comes free from `prometheus_fastapi_instrumentator`:

```python
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

The browser calls `/api/tasks` and `/api/tasks/stats` and **never needs to know the backend's
hostname** — nginx (locally) and the Ingress (in Kubernetes) do the routing.

---

## 🐳 Running it locally — Docker Compose

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: taskboard
      POSTGRES_USER: taskboard
      POSTGRES_PASSWORD: taskboard
    ports: ["5432:5432"]
    volumes: ["postgres-data:/var/lib/postgresql/data"]   # ⭐ named volume = data survives

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg://taskboard:taskboard@postgres:5432/taskboard
    depends_on: [postgres]
    ports: ["8000:8000"]

  frontend:
    build: ./frontend
    depends_on: [backend]
    ports: ["3000:80"]

volumes:
  postgres-data:
```

```bash
docker compose up --build
#   http://localhost:3000        the app
#   http://localhost:8000/docs   Swagger
#   http://localhost:8000/health
#   http://localhost:8000/metrics

docker compose down        # keeps the DB volume
docker compose down -v     # ⭐ deletes it too
```

⭐ Everything from [Session 8](./08_Docker_Networking_Volumes_and_Compose.md):
service-name DNS (`@postgres:5432`), port mapping (`3000:80` — host 3000 to the container's
nginx on 80), and a **named volume** so your tasks survive a restart.

> ⚠️ `depends_on` waits for the container to **start**, not for Postgres to be **ready**.
> The backend's `alembic upgrade head` can race the database on a cold start. Fix with a
> healthcheck + `condition: service_healthy`, or a retry loop in the entrypoint.

### Running the backend directly

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://taskboard:taskboard@localhost:5432/taskboard'
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

---

## 🧪 Testing — the first gate

```bash
cd backend && pytest -q
```

```text
Bad code
  ↓
pytest fails
  ↓
Pipeline stops
  ↓
No broken image is promoted
```

⭐ Tests run **before** images are built and pushed — not after. A registry full of images
that failed their tests is worse than useless, because somebody will eventually deploy one.

Tests must run against a **test database or mock**, never production — which is also what
makes them safe to run on every push.

---

## 📦 Docker — two very different images

### Backend — single stage, non-root, migrate-then-serve

```dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --create-home --uid 10001 appuser
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
USER 10001
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

Everything from [Session 7](./07_Docker_Images_and_Dockerfile.md) is here:

| Line | Why |
|---|---|
| `COPY requirements.txt` before `COPY app` | ⭐ dependency layer stays cached when only code changes |
| `--no-cache-dir` | don't ship pip's cache |
| `PYTHONUNBUFFERED=1` | ⭐ logs appear immediately instead of sitting in a buffer — essential for `kubectl logs` |
| `USER 10001` | ⭐ non-root |
| `--host 0.0.0.0` | ⭐ listen on all interfaces; `127.0.0.1` would be unreachable from outside the container |

> ⚠️ Running `alembic upgrade head` in `CMD` means **every replica** tries to migrate on
> startup. Alembic takes a lock so it's survivable, but the correct pattern is a **Helm
> `pre-upgrade` hook Job** ([Session 15](./15_Helm.md)) or an **initContainer** — one migration,
> then the app pods start.

### Frontend — multi-stage

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

```text
Node → npm build → static dist/ → Nginx runtime image
```

⭐ **Node and npm never reach the final image.** A ~1.1 GB build toolchain collapses to a
~50 MB nginx image containing only static files — fewer megabytes *and* a far smaller CVE
surface for Trivy.

> 🐛 The frontend image **never sets a non-root `USER`**, although the project's own criteria
> require non-root for both images. Use `nginxinc/nginx-unprivileged:1.27-alpine` (listens on
> 8080) or add a `USER` plus writable `/var/cache/nginx`.

### `nginx.conf` — the local reverse proxy

```nginx
location / {
  try_files $uri /index.html;        # ⭐ SPA routing: deep links work on refresh
}
location /api/ {
  proxy_pass http://backend:8000;    # Compose service name
}
```

> ⚠️ `http://backend:8000` resolves in **Compose** (service `backend`), but in Kubernetes the
> Service is `<release>-taskboard-backend`. In the cluster the **Ingress** handles `/api`, so
> this block is dead weight there — and a trap if you expect the frontend to proxy.

---

## ⚙️ CI/CD — the three-stage pipeline

```text
TEST  →  BUILD + SECURITY SCAN + PUSH  →  DEPLOY
```

```yaml
name: TaskBoard Python CI/CD
on:
  push:         { branches: [main] }
  pull_request: { branches: [main] }
env:
  REGISTRY: ghcr.io

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
        working-directory: backend            # ⭐ each run: is a new shell — cd won't persist
      - run: pytest -q
        working-directory: backend
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: npm install && npm run build
        working-directory: frontend

  build-scan-push:
    needs: test                               # ⭐ GATE 1
    runs-on: ubuntu-latest
    permissions: { contents: read, packages: write }
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - run: |
          docker build -t ghcr.io/${{ github.repository_owner }}/taskboard-backend:${{ github.sha }}  ./backend
          docker build -t ghcr.io/${{ github.repository_owner }}/taskboard-frontend:${{ github.sha }} ./frontend
      - uses: aquasecurity/trivy-action@0.30.0
        with:
          image-ref: ghcr.io/${{ github.repository_owner }}/taskboard-backend:${{ github.sha }}
          severity: HIGH,CRITICAL
          ignore-unfixed: true
          exit-code: '1'                      # ⭐ GATE 2 — this is what makes it a gate
      # ... same for the frontend image ...
      - run: |
          docker push ghcr.io/${{ github.repository_owner }}/taskboard-backend:${{ github.sha }}
          docker push ghcr.io/${{ github.repository_owner }}/taskboard-frontend:${{ github.sha }}

  deploy:
    if: github.ref == 'refs/heads/main'       # ⭐ GATE 3 — PRs test but never deploy
    needs: build-scan-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v4
      - name: Configure kubectl
        env: { KUBE_CONFIG_DATA: '${{ secrets.KUBE_CONFIG_DATA }}' }
        run: mkdir -p ~/.kube && echo "$KUBE_CONFIG_DATA" | base64 -d > ~/.kube/config
      - run: |
          helm upgrade --install taskboard ./helm/taskboard -n taskboard --create-namespace \
            --set backend.tag=${{ github.sha }} \
            --set frontend.tag=${{ github.sha }} \
            --set backend.image=ghcr.io/${{ github.repository_owner }}/taskboard-backend \
            --set frontend.image=ghcr.io/${{ github.repository_owner }}/taskboard-frontend
```

⭐ **This pipeline does the three things [Session 17](./17_Complete_CICD_and_DevSecOps.md) said
to do**, including the one the earlier demo missed: `exit-code: '1'` on Trivy, so a
HIGH/CRITICAL finding actually **stops the push**. `ignore-unfixed: true` keeps it achievable.

⭐ **`${{ github.sha }}` as the tag, everywhere.**

```text
commit A → image A → release A
commit B → image B → release B
```

Traceability from a running Pod back to a line of source — and `helm rollback` becomes exact
rather than approximate.

⭐ **`helm upgrade --install`** — idempotent on the first deploy and the five-hundredth.

> 💡 Two improvements worth making: add `--atomic --wait --timeout 5m` so a failed rollout
> rolls itself back ([Session 15](./15_Helm.md)); and prefer `-f values-prod.yaml` over four
> `--set` flags, so the deployed configuration is reviewable in Git.

---

## ☁️ Terraform — VPC + EKS

Kubernetes manages workloads; it does **not** create the network it runs on.

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"
  name    = "taskboard-vpc"
  cidr    = "10.20.0.0/16"
  azs             = ["ap-south-1a", "ap-south-1b"]      # ⭐ two AZs
  private_subnets = ["10.20.1.0/24",   "10.20.2.0/24"]
  public_subnets  = ["10.20.101.0/24", "10.20.102.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true                              # ⭐ cheaper, but one AZ's NAT is an SPOF
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.37.1"
  cluster_name    = var.cluster_name
  cluster_version = "1.31"
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets                # ⭐ nodes are PRIVATE
  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true
  eks_managed_node_groups = {
    main = { instance_types = ["t3.medium"], min_size = 2, max_size = 4, desired_size = 2 }
  }
}
```

```bash
cd terraform
terraform init && terraform plan && terraform apply
aws eks update-kubeconfig --name <cluster_name> --region ap-south-1
terraform destroy          # ⭐⭐ EKS costs ~$0.10/hour for the control plane ALONE
```

⭐ This is exactly the production topology from
[Session 19](./19_Cloud_and_Terraform_in_Action.md): **public subnets** for the load balancer
and NAT, **private subnets** for the worker nodes, NAT for outbound image pulls. The nodes
have no inbound route from the internet at all.

⭐ And note the leverage: two `module` blocks produce ~60 AWS resources. That's what
[Session 18](./18_Terraform_and_IaC.md)'s modules buy you.

> 💰 **Destroy it.** An EKS control plane plus two `t3.medium` nodes plus a NAT Gateway and an
> ALB is real money, billed hourly, whether or not anyone is using it.

> 💡 In production the database would be **Amazon RDS**, not a Pod. The README raises the
> trade-off and it's the right question: Kubernetes is excellent at stateless workloads and
> merely adequate at stateful ones.

---

## ☸️ Kubernetes & the Helm chart

```bash
kubectl apply -f k8s/namespace.yaml

helm upgrade --install taskboard ./helm/taskboard \
  --namespace taskboard --create-namespace
```

```text
helm/taskboard/
├── Chart.yaml
├── values.yaml            defaults
├── values-dev.yaml        1 replica, ingress on, HPA off
├── values-prod.yaml
└── templates/
    ├── _helpers.tpl
    ├── backend-deployment.yaml    backend-service.yaml
    ├── frontend-deployment.yaml   frontend-service.yaml
    ├── postgres.yaml              Secret + Service + Deployment + PVC
    ├── ingress.yaml
    ├── hpa.yaml
    └── servicemonitor.yaml
```

**`values.yaml`**

```yaml
frontend: { image: ghcr.io/YOUR_ORG/taskboard-frontend, tag: latest }
backend:  { image: ghcr.io/YOUR_ORG/taskboard-backend,  tag: latest }
replicaCount: 2
postgres: { host: taskboard-postgres, database: taskboard, username: taskboard, password: taskboard }
ingress:  { enabled: false, host: taskboard.local }
hpa:      { enabled: true, minReplicas: 2, maxReplicas: 6, targetCPUUtilizationPercentage: 60 }
resources:
  requests: { cpu: 100m, memory: 256Mi }
  limits:   { cpu: 500m, memory: 512Mi }
monitoring: { serviceMonitor: { enabled: true } }
```

**`backend-deployment.yaml`** (the probes and resources are the parts that matter)

```yaml
          readinessProbe:
            httpGet: { path: /ready, port: 8000 }
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 20
            periodSeconds: 15
          resources:
{{ toYaml .Values.resources | indent 12 }}
```

⭐ **`resources.requests.cpu` is mandatory for HPA.** No CPU request ⇒ no utilisation
percentage to compute ⇒ HPA reports `<unknown>` and never scales
([Session 13](./13_Kubernetes_Storage_HPA_and_Probes.md)).

⭐ Note `liveness` has a **longer** `initialDelaySeconds` than `readiness` (20 vs 10) — the
right ordering. Reversed, Kubernetes kills the container while it's still legitimately
starting up. (A `startupProbe` is the cleaner answer for slow starters.)

---

## 🌐 Ingress, HPA & the database

### Ingress — path-based routing

```yaml
{{- if .Values.ingress.enabled }}
spec:
  ingressClassName: nginx
  rules:
  - host: taskboard.local
    http:
      paths:
      - { path: /api, pathType: Prefix, backend: { service: { name: taskboard-backend,  port: { number: 8080 } } } }
      - { path: /,    pathType: Prefix, backend: { service: { name: taskboard-frontend, port: { number: 80 } } } }
{{- end }}
```

```text
taskboard.local/      → React frontend
taskboard.local/api   → FastAPI backend
```

```bash
helm upgrade --install taskboard ./helm/taskboard -n taskboard -f helm/taskboard/values-dev.yaml
```

⭐ **An Ingress resource is only configuration.** Without an **Ingress Controller** installed,
nothing implements it and nothing happens
([Session 12](./12_Kubernetes_Ingress_ConfigMaps_and_Secrets.md)). Also add `taskboard.local`
to your `/etc/hosts`.

### HPA

```yaml
{{- if .Values.hpa.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: {{ include "taskboard.fullname" . }}-backend }
  minReplicas: 2
  maxReplicas: 6
  metrics: [{ type: Resource, resource: { name: cpu, target: { type: Utilization, averageUtilization: 60 } } }]
{{- end }}
```

```bash
kubectl get hpa -n taskboard
```

```text
low traffic → 2 Pods → high CPU → 3 → 4 → …
```

Needs **resource requests** *and* the **Metrics Server**. ⚠️ A few health checks won't move
the needle — use the load generator:

```bash
URL=http://taskboard.local/api/tasks ./scripts/load-test.sh
```

> 🐛 `scripts/load-test.sh` defaults to `/api/health`, but the backend serves `/health` at the
> root, not under `/api`. As written it hammers a 404. Point it at `/api/tasks`.

> ⚠️ **`replicas` and HPA conflict.** The Deployment template hard-codes
> `replicas: {{ .Values.replicaCount }}`, so every `helm upgrade` resets the replica count and
> the HPA has to scale back up. With an HPA, omit `replicas` from the template entirely.

### PostgreSQL in-cluster

```yaml
kind: Secret           # username/password via stringData  ⭐ good
kind: Service          # taskboard-postgres:5432
kind: Deployment       # postgres:16-alpine + pg_isready readiness probe  ⭐ good
kind: PersistentVolumeClaim   # 5Gi ReadWriteOnce
```

⭐ Credit where due: the chart puts credentials in a **Secret** referenced via `secretKeyRef`,
and uses `pg_isready` as a genuine readiness probe. Both correct.

> ⚠️ But it's a **Deployment** with a `ReadWriteOnce` PVC. The default `RollingUpdate` strategy
> tries to start a second Pod before terminating the first — and the second can't mount an
> RWO volume already attached to another node. The rollout hangs. **A database belongs in a
> `StatefulSet`** (or at minimum `strategy: Recreate`) —
> [Session 10](./10_Kubernetes_Pods_ReplicaSets_and_Deployments.md).
> The `DATABASE_URL` is also assembled from plaintext values into a **plain env var**, so the
> password shows up in `kubectl describe pod`. Reference the Secret directly instead.

---

## 📊 Monitoring — ServiceMonitor → Prometheus → Grafana

```yaml
{{- if .Values.monitoring.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  labels:
    release: kube-prometheus-stack       # ⭐ how Prometheus Operator finds it
spec:
  selector:
    matchLabels: { app: taskboard-backend }
  endpoints:
    - port: http                          # the NAMED port on the Service
      path: /metrics
      interval: 15s
{{- end }}
```

```text
FastAPI /metrics  ──scrape──▶  Prometheus  ──query──▶  Grafana
```

⭐ A **ServiceMonitor** is a CRD: instead of editing `prometheus.yml`, you declare *"scrape
Services with these labels"* and the Prometheus Operator regenerates the config. Declarative
monitoring — the same shift as declarative deployment.

⚠️ Two things must line up or nothing is scraped:
1. `endpoints.port` is the Service's **port name** (`http`), not a number — and
   `backend-service.yaml` does name it `http`. ✅
2. The `release:` label must match your actual Prometheus Operator release name.

Then ask the questions that matter ([Session 20](./20_Monitoring_Observability_and_GitOps.md)):
how many requests are arriving · which endpoint is slow · are errors increasing · is CPU
climbing · **is the HPA actually scaling?**

---

## 🔧 Troubleshooting lab

Two deliberately broken manifests — the two most common Kubernetes failures.

### Broken image

```bash
kubectl apply -f troubleshooting/broken-image.yaml
kubectl get pods
kubectl describe pod <pod-name>
kubectl get events --sort-by=.lastTimestamp
```

```text
ImagePullBackOff → describe Pod → Events → wrong image/tag → fix → verify
```

### Broken Service

```bash
kubectl apply -f troubleshooting/broken-service.yaml
kubectl get svc
kubectl get endpoints          # ⭐ <none> is the smoking gun
kubectl get pods --show-labels
```

⭐ **A Service selects Pods by label. No matching labels = no endpoints = no traffic** — and
every individual object looks perfectly healthy. Full method in
[Session 14](./14_Kubernetes_Troubleshooting.md).

---

## 🐛 Bugs in the reference chart (read this)

The chart has three real defects that will stop the deployment working. Finding them is
genuinely the most instructive part of the capstone.

### 1. ⭐ The Ingress points at service names that don't exist

```yaml
{{- define "taskboard.fullname" -}}{{ .Release.Name }}-taskboard{{- end }}
```

With `helm install taskboard ...`, `fullname` = **`taskboard-taskboard`**, so the backend
Service is created as **`taskboard-taskboard-backend`**. But the Ingress hard-codes
`taskboard-backend`. Result: `/api` returns **503**, with no error at install time.

```yaml
# fix
name: {{ include "taskboard.fullname" . }}-backend
```

(Likewise the HPA and frontend Service hard-code names while the Deployments use the helper —
mix templated and literal names and they drift apart. Pick one.)

### 2. ⭐ The Ingress uses the wrong port

```yaml
port: { number: 8080 }      # ❌ the backend Service listens on 8000
```

```yaml
port: { number: 8000 }      # ✅
```

Two bugs on the same line, and `helm install` reports success for both — ⭐ exactly why
`kubectl get endpoints` and a `curl` smoke test exist.

### 3. The frontend image runs as root

No `USER` directive, contrary to the project's own non-root requirement.

### Catch all of this before it ships

```bash
helm lint ./helm/taskboard
helm template taskboard ./helm/taskboard -f helm/taskboard/values-dev.yaml   # ⭐ read the names and ports
helm upgrade --install taskboard ./helm/taskboard --atomic --wait --timeout 5m
kubectl get endpoints -n taskboard
curl -H "Host: taskboard.local" http://<ingress-ip>/api/tasks
```

⭐ `helm template` would have shown both Ingress bugs in five seconds. That is the lesson.

---

## 🎬 The demo path

1. **Application** — open TaskBoard, create a task
2. **API** — `/docs`, exercise create/read/update/delete
3. **Database** — show the `tasks` table
4. **Git** — make a small change and commit it
5. **CI** — push, watch tests run
6. **Docker** — show both images
7. **Security** — show Trivy scanning them
8. **Registry** — the SHA-tagged images in GHCR
9. **Terraform** — the infrastructure code
10. **Kubernetes** — `kubectl get pods,svc -n taskboard`
11. **Helm** — `helm list -n taskboard`
12. **Ingress** — open the app through the hostname
13. **HPA** — `kubectl get hpa -n taskboard` under load
14. **Monitoring** — Prometheus targets `UP`, a live Grafana panel
15. **Failure** — break a Service or image and debug it live

⭐ Step 15 is the one that proves understanding. Anyone can demo a green pipeline; debugging a
red one on the spot is the actual skill.

---

## 🚀 Building your own

Pick your own domain — CRM, inventory, appointment booking, helpdesk, e-commerce admin, clinic
or restaurant management, employee management, LMS. **The DevOps layer may follow TaskBoard's
architecture; the application must be yours.**

| Layer | Minimum |
|---|---|
| **Application** | frontend + backend + PostgreSQL, ≥4 REST endpoints, responsive UI |
| **Engineering** | Git/GitHub with real history, automated tests, Docker |
| **DevOps** | GitHub Actions, security scan, container registry, Terraform, Kubernetes, Helm, Ingress, HPA, Prometheus/Grafana |

Suggested order — ⭐ **always have something that runs**:

```
1. App + tests locally
2. Dockerfiles + docker compose up
3. Git + a CI pipeline that just runs tests
4. Add build + push to GHCR with SHA tags
5. Add Trivy with exit-code 1
6. Helm chart; deploy to kind locally first      ← ⭐ debug here, not on EKS
7. Terraform VPC + EKS; deploy there
8. Ingress + HPA
9. Prometheus + Grafana
10. Break it on purpose and fix it
```

⭐ **Step 6 before step 7.** Every chart bug is cheaper to find on a local kind cluster than on
an EKS cluster billing you by the hour. And run `terraform destroy` the moment the demo ends.

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Capstone chain** | app → Git → CI → image → scan → registry → IaC → K8s → Helm → Ingress → HPA → monitoring |
| **`/health` vs `/ready`** | ⭐ Alive (liveness, restart) vs able to serve (readiness, remove from endpoints) |
| **Alembic** | SQLAlchemy migrations; `alembic upgrade head` |
| **Multi-stage build** | Build in one image, ship only the artefact in a minimal runtime image |
| **SHA tag** | `${{ github.sha }}` — traceability from a Pod to a commit |
| **GHCR** | GitHub Container Registry; `GITHUB_TOKEN` + `packages: write` |
| **`exit-code: '1'`** | ⭐ What makes a Trivy step a gate rather than a report |
| **`helm upgrade --install`** | Idempotent deploy for pipelines |
| **EKS managed node group** | AWS-managed worker nodes in the private subnets |
| **ServiceMonitor** | CRD telling the Prometheus Operator what to scrape |
| **`kubectl get endpoints`** | ⭐ First command when a Service returns nothing |
| **`helm template`** | ⭐ Renders the chart locally — catches name/port bugs before the cluster does |

---

## 🎯 Session Takeaways

1. ⭐ **The chain is the deliverable.** Each tool exists because the previous one created a problem; the value is the unbroken path from commit to monitored production.
2. ⭐ **`/health` is liveness, `/ready` is readiness — and never check the database in a liveness probe,** or a DB blip restarts your whole fleet.
3. **Tests gate the build; the build gates the push; the scan gates the registry; `main` gates the deploy.** Four `needs:`/`if:` lines, four real gates.
4. ⭐ **Tag every image with the commit SHA.** It's what makes rollback, bisection and "what's running?" answerable.
5. **Multi-stage builds** keep Node out of the frontend image — smaller *and* fewer CVEs.
6. **`exit-code: '1'` + `ignore-unfixed: true`** is the Trivy setting that is both strict and livable.
7. ⭐ **`helm template` before every deploy.** Both Ingress bugs in this chart are visible in the rendered output and invisible in `helm install`'s success message.
8. **Keep service names templated consistently.** Mixing `{{ include "x.fullname" . }}` with hard-coded names produces a chart that works only when the release is named exactly right.
9. ⭐ **No `resources.requests.cpu` ⇒ no HPA**, and a hard-coded `replicas:` alongside an HPA means they fight on every upgrade.
10. **A database wants a StatefulSet, not a Deployment with an RWO PVC** — and in production, a managed service.
11. ⭐ **Deploy to kind before EKS.** Debug on free infrastructure; `terraform destroy` the paid kind.
12. **Being able to debug it live is the skill.** A green pipeline proves the tools work; a fixed red one proves you do.

---

## 🔗 References

- FastAPI — https://fastapi.tiangolo.com/
- Alembic — https://alembic.sqlalchemy.org/
- `prometheus-fastapi-instrumentator` — https://github.com/trallnag/prometheus-fastapi-instrumentator
- Vite — https://vite.dev/
- Docker multi-stage builds — https://docs.docker.com/build/building/multi-stage/
- GitHub Actions — https://docs.github.com/en/actions
- Trivy action — https://github.com/aquasecurity/trivy-action
- `terraform-aws-modules/vpc` — https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest
- `terraform-aws-modules/eks` — https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest
- Amazon EKS — https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
- Helm — https://helm.sh/docs/
- Ingress NGINX controller — https://kubernetes.github.io/ingress-nginx/
- HPA — https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- Prometheus Operator ServiceMonitor — https://prometheus-operator.dev/docs/developer/getting-started/
- Configure probes — https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

---

## 🏁 End of the course

```text
01 DevOps & Microservices   ──▶  why
02–04 Linux · Shell · Networking  ──▶  the ground it all runs on
05 Git                      ──▶  the source of truth
06–08 Docker                ──▶  package it
09–14 Kubernetes            ──▶  run, expose, scale, debug it
15 Helm                     ──▶  package the packaging
16–17 CI/CD & DevSecOps     ──▶  automate and secure it
18–19 Terraform & Cloud     ──▶  create what it runs on
20 Monitoring & GitOps      ──▶  see it and reconcile it
21 Capstone                 ──▶  all of it, at once
```

⬅️ Back to the [DevOps index](./README.md).
