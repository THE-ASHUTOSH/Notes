# Session 20 — Monitoring, Observability & GitOps 📊

> **Topics:** Monitoring vs Observability · Metrics, Logs & Traces · Prometheus · Grafana ·
> Introduction to GitOps · Git as Source of Truth · Argo CD · Continuous Deployment with GitOps
>
> 📁 Repo: `session20-monitoring-observability-gitops/` — eight folders: observability concepts,
> runnable Prometheus/Grafana Compose stacks, a GitOps repo example, a full Argo CD lab and a
> mini-project.

Two halves, one theme: **knowing what your system is actually doing**, and **making Git the
single statement of what it should be doing**.

---

## 📑 Table of Contents

1. [Monitoring vs Observability](#-monitoring-vs-observability)
2. [Metrics, Logs & Traces](#-metrics-logs--traces)
3. [Prometheus](#-prometheus)
4. [PromQL & Metric Types](#-promql--metric-types)
5. [Grafana](#-grafana)
6. [Alerting, Golden Signals & SLOs](#-alerting-golden-signals--slos)
7. [Introduction to GitOps](#-introduction-to-gitops)
8. [Git as Source of Truth](#-git-as-source-of-truth)
9. [Argo CD](#-argo-cd)
10. [GitOps in Action — the full lab](#-gitops-in-action--the-full-lab)
11. [Mini Project](#-mini-project)
12. [Beyond the lab: Loki, Jaeger, OpenTelemetry, Flux](#-beyond-the-lab-loki-jaeger-opentelemetry-flux)
13. [Key Terms Recap](#-key-terms-recap)
14. [Session Takeaways](#-session-takeaways)

---

## 🔭 Monitoring vs Observability

### Monitoring asks: *"Is the system healthy?"*

```text
CPU:        82%
Memory:     70%
Requests:   500/sec
Errors:     20/sec
Latency:    900ms
```

```text
IF error_rate > 5% THEN alert
```

⭐ Monitoring is excellent for **known** problems — the failure modes you anticipated and wrote
a dashboard for.

### Observability asks: *"Why is it behaving this way?"*

```text
Users: "The website is slow."
Monitoring: latency = 2s           ← tells you THAT
Observability:
  Request
   ├── API             500ms
   ├── User Service    200ms
   ├── Payment Service 100ms
   └── Database       1200ms       ← tells you WHERE
```

### The car analogy

| | |
|---|---|
| **Monitoring** | The dashboard light says *engine temperature HIGH*. Something is wrong. |
| **Observability** | You check coolant level, engine logs, temperature history, sensor readings. Now you know *why*. |

| Monitoring | Observability |
|---|---|
| Is something wrong? | Why is it wrong? |
| Known failure signals | Explore **unknown** problems |
| Dashboards & alerts | Metrics + logs + traces |
| Health view | Deep investigation |

⭐ **They are not competitors.** Monitoring tells you *when* to look; observability lets you
*find it*. Production needs both — and the distinction matters because a system can be fully
monitored and still completely opaque when something new breaks.

> Formally: observability is the property of being able to understand a system's internal
> state from its outputs — **without shipping new code to add a log line**. The test is
> whether you can answer a question you didn't think of in advance.

---

## 📶 Metrics, Logs & Traces

The three signals:

```text
Metrics = Numbers   →  HOW MUCH / HOW OFTEN
Logs    = Events    →  WHAT happened
Traces  = Journey   →  WHERE the time went
```

### 1. Metrics — numbers over time

```text
http_requests_total = 1200
http_request_duration_seconds = 0.25
cpu_usage, memory_usage, error_count
```

Cheap to store, easy to aggregate and alert on — but **no detail**. A spike tells you
something happened, not what.

### 2. Logs — discrete events

```text
2026-09-28 18:20:01 INFO  User logged in
2026-09-28 18:20:03 INFO  Payment started
2026-09-28 18:20:05 ERROR Database timeout
```

Rich detail, expensive at volume. ⭐ Use **structured logs** (JSON) with a `trace_id` field —
then logs and traces link up and you can jump from a slow request to its exact log lines.

### 3. Traces — one request across many services

```text
Trace ID: abc123

Browser
 ├── API Gateway       20ms
 ├── Order Service     80ms
 ├── Payment Service  120ms
 └── Database         600ms
                    ───────
                      820ms
```

⭐ In a microservices architecture ([Session 1](./01_Introduction_to_DevOps_and_Microservices.md))
traces are **essential**, not optional. With 15 services, "the request is slow" is unanswerable
without one — the whole point of splitting the monolith was that no single log file sees the
whole request any more.

### The cricket analogy

| Signal | Cricket |
|---|---|
| **Metrics** | Runs = 180, Wickets = 6, Run rate = 9.0 — **numbers** |
| **Logs** | *"Player X was bowled." "Player Y hit a six."* — **events** |
| **Traces** | Follow one delivery: bowler → ball → batsman → field → result — **journey** |

### Kubernetes demo

```bash
kind create cluster --name session20
kubectl apply -f 02-metrics-logs-traces/k8s-demo/
kubectl get pods
kubectl logs deployment/session20-demo
```

```text
Session 20 observability demo started
Request received
Health check OK
```

```bash
kubectl describe deployment session20-demo     # labels, replicas, image, events
kubectl delete -f 02-metrics-logs-traces/k8s-demo/
kind delete cluster --name session20
```

> 💡 The demo's `service.yaml` targets port 8080, but the busybox container only prints to
> stdout and listens on nothing — so the Service has no working backend. That's fine here
> (the lesson is **logs**), but it's a live example of the empty-endpoint situation from
> [Session 14](./14_Kubernetes_Troubleshooting.md).

---

## 🔥 Prometheus

> *"Prometheus goes around asking applications: give me your metrics."*

```text
Application
    │  exposes GET /metrics
    ▼
Prometheus  ──▶  time-series database
```

### ⭐ Pull, not push

Prometheus **scrapes** targets on an interval. That matters:

| Pull gives you | |
|---|---|
| `up` as a free health check | if the scrape fails, the target is down — no extra monitoring needed |
| No app-side config | the app just serves `/metrics`; Prometheus decides when to look |
| No thundering herd | Prometheus controls the rate, not thousands of clients |

(For short-lived jobs that die before a scrape, there's the **Pushgateway** — the exception
that proves the rule.)

### Run it

`docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus:v3.5.0
    container_name: session20-prometheus
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
```

`prometheus.yml`:

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["prometheus:9090"]      # ⭐ Prometheus scrapes itself
```

```bash
docker compose up -d
docker compose ps
```

Open <http://localhost:9090> (and `/metrics` to see Prometheus's own metrics).

> ⭐ `targets: ["prometheus:9090"]` resolves by **Compose service name** — the user-defined
> network DNS from [Session 8](./08_Docker_Networking_Volumes_and_Compose.md). `localhost`
> inside the container would mean the container itself.

### Vocabulary

```text
Prometheus
  ├── Target:  the thing being scraped
  ├── Scrape:  GET /metrics on an interval
  ├── Metric:  a named time series
  ├── Label:   key/value dimensions on a metric
  └── Query:   PromQL
```

Try in the UI: `up`, then `prometheus_http_requests_total`, then `process_cpu_seconds_total`.

```text
up{instance="prometheus:9090", job="prometheus"} 1
```

⭐ **`up` is the first query you ever run.** `1` = the target was scraped successfully, `0` =
it's down. One expression monitors every target in the cluster.

Answers to the lab's questions: Prometheus collects **metrics** · a scrape is collecting them ·
`up` is target health · PromQL is the query language · it's a **metrics** system, **not** log
storage.

---

## 🧮 PromQL & Metric Types

### The four metric types

| Type | Behaviour | Example |
|---|---|---|
| **Counter** | only goes up (resets to 0 on restart) | `http_requests_total` |
| **Gauge** | goes up and down | `memory_usage_bytes`, `queue_depth` |
| **Histogram** | bucketed observations; percentiles computed server-side | `http_request_duration_seconds` |
| **Summary** | percentiles computed client-side | latency quantiles |

⭐ **Never alert on a raw counter** — it only ever increases. Wrap it in `rate()`.

### PromQL you'll actually use

```promql
up                                                 # target health
sum(up)                                            # how many targets are up

rate(http_requests_total[5m])                      # ⭐ per-second rate over 5 min
sum(rate(http_requests_total[5m])) by (service)    # aggregate by label

sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))             # ⭐ error rate

histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le))   # p95 latency

container_memory_usage_bytes / container_spec_memory_limit_bytes # how close to OOM
```

⭐ **Percentiles, not averages.** A 200 ms average can hide 5% of users waiting 4 seconds.
p95/p99 is what your users actually feel.

### Exporters — metrics from things that can't be changed

| Exporter | Exposes |
|---|---|
| **node_exporter** | host CPU, memory, disk, network |
| **kube-state-metrics** | Kubernetes object state (deployments, pods, replicas) |
| **cAdvisor** / kubelet | per-container resource usage |
| **blackbox_exporter** | probes endpoints from outside |
| postgres / redis / nginx exporters | per-service internals |

In Kubernetes you'd normally install the whole stack at once —
`kube-prometheus-stack` via Helm ([Session 15](./15_Helm.md)) — which brings Prometheus,
Alertmanager, Grafana, node_exporter and kube-state-metrics with dashboards already wired up.

---

## 📈 Grafana

```text
Prometheus = Data
Grafana    = Beautiful dashboard
```

```text
Application ──▶ Prometheus ──▶ Metrics ──▶ Grafana ──▶ Dashboard
```

```yaml
services:
  prometheus:
    image: prom/prometheus:v3.5.0
    ports: ["9090:9090"]
    volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml:ro"]

  grafana:
    image: grafana/grafana:12.1.1
    ports: ["3000:3000"]
    depends_on: [prometheus]
```

```bash
docker compose up -d
```

- Prometheus → <http://localhost:9090>
- Grafana → <http://localhost:3000> (`admin` / `admin`, then change it)

### Add the data source

**Connections → Data sources → Add → Prometheus**, URL:

```text
http://prometheus:9090
```

⭐ **`http://prometheus:9090`, not `http://localhost:9090`.** Grafana reaches Prometheus by
**Compose service name** over the shared network. `localhost` inside the Grafana container is
Grafana. This is the single most common mistake in this lab, and it's the exact lesson from
[Session 8](./08_Docker_Networking_Volumes_and_Compose.md).

**Save & test** → *"Successfully queried the Prometheus API."*

### A first dashboard

**Dashboard → Add visualization → Prometheus → query `up` → Stat** → shows `1`.

```text
+----------------+----------------+
| CPU            | Memory         |
| 72%            | 61%            |
+----------------+----------------+
| Requests/sec   | Error Rate     |
| 150            | 1.2%           |
+----------------+----------------+
| Latency                         |
| 230 ms                          |
+---------------------------------+
```

> 💡 Grafana isn't Prometheus-only — it queries Loki (logs), Tempo/Jaeger (traces),
> CloudWatch, Elasticsearch and SQL databases, which is why it's the common pane of glass.
> Dashboards can be exported as JSON and committed to Git (dashboards-as-code).

```bash
docker compose down
```

> ⚠️ Neither Compose file declares a **volume**, so Prometheus data and your Grafana
> dashboards vanish on `docker compose down`. Fine for a lab; add named volumes
> ([Session 8](./08_Docker_Networking_Volumes_and_Compose.md)) for anything you want to keep.

---

## 🚨 Alerting, Golden Signals & SLOs

Not in the repo, but this is the half of monitoring that makes it useful at 3am.

### The Four Golden Signals (Google SRE)

| Signal | Question |
|---|---|
| **Latency** | How long do requests take? (split success vs error!) |
| **Traffic** | How much demand? |
| **Errors** | What fraction fail? |
| **Saturation** | How full is the system? |

Two shorthand methods: **RED** (Rate, Errors, Duration) for *services*; **USE**
(Utilisation, Saturation, Errors) for *resources*.

### Alertmanager

```yaml
groups:
  - name: app
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m                         # ⭐ must hold for 5 min — kills flapping
        labels:    { severity: critical }
        annotations:
          summary: "Error rate above 5% for 5 minutes"
```

Alertmanager handles **grouping, deduplication, silencing, inhibition** and routing to
Slack/PagerDuty/email.

⭐ **Alert on symptoms, not causes.** "Error rate > 5%" wakes someone for a real user problem.
"CPU > 80%" wakes them for something that might be completely fine. Every alert should be
**actionable** — if the answer is "nothing to do", delete the alert. Alert fatigue is how real
outages get ignored.

### SLI / SLO / Error budget

| Term | Meaning |
|---|---|
| **SLI** | The measurement — "% of requests served < 300ms" |
| **SLO** | The target — "99.9% of requests < 300ms over 30 days" |
| **Error budget** | ⭐ `100% − SLO` = 0.1% ≈ **43 minutes/month** of permitted failure |
| **SLA** | The contractual version, with financial consequences |

⭐ The error budget is what makes this more than paperwork: **budget left ⇒ ship features;
budget spent ⇒ stop and fix reliability.** It turns "how stable should we be?" from an
argument into a number.

---

## 🔁 Introduction to GitOps

> **Git describes the desired state of the system.**

```text
Traditional:                 GitOps:
  Developer                    Developer
     │                            │
  kubectl                       Git
     │                            │
  Kubernetes                   Argo CD
                                  │
                              Kubernetes
```

The developer changes **Git**. Argo CD notices. Argo CD syncs the cluster.

### ⭐ The four OpenGitOps principles

1. **Declarative** — the whole system is described declaratively.
2. **Versioned and immutable** — desired state is stored in Git, with full history.
3. **Pulled automatically** — agents pull the state; nobody pushes into the cluster.
4. **Continuously reconciled** — agents keep observing and correcting drift.

### Why Git

```text
History · Review · Diffs · Rollback point · Collaboration · Audit trail
```

```text
Monday:    replicas = 2
Tuesday:   replicas = 5
Wednesday: replicas = 2
```

Git records every one, with who and why.

### ⭐ Push vs pull — the security argument

| | **Push CD** (Session 17) | **Pull / GitOps** |
|---|---|---|
| Who initiates | the pipeline, from outside | an agent **inside** the cluster |
| Credentials | ⚠️ cluster creds live in the CI system | ⭐ **none leave the cluster** |
| Firewall | needs inbound access to the API server | outbound only |
| Drift | invisible until it bites | detected and corrected continuously |

That one row — *cluster credentials never leave the cluster* — is why GitOps won. It also
solves the "GitHub runner can't reach my cluster" problem from
[Session 17](./17_Complete_CICD_and_DevSecOps.md).

### Desired vs actual

```text
Git says:      replicas: 3     ← desired
Cluster has:   2 replicas      ← actual
Controller:    reconcile → 3
```

⭐ This is the exact **control loop** from
[Session 9](./09_Kubernetes_Fundamentals.md) — Kubernetes controllers reconcile Pods to
ReplicaSets; Argo CD reconciles the *cluster* to *Git*. One more turtle on the stack.

---

## 📒 Git as Source of Truth

```text
gitops-repo/
├── README.md
└── app/
    ├── deployment.yaml
    └── service.yaml
```

A real repository:

```text
my-company-gitops/
├── apps/
│   ├── payments/
│   ├── orders/
│   └── users/
└── environments/
    ├── dev/
    ├── staging/
    └── production/
```

```bash
cd gitops-repo && git init && git add . && git commit -m "Add application manifests"

# change desired state
#   replicas: 2  →  replicas: 3
git diff
# -  replicas: 2
# +  replicas: 3
git add . && git commit -m "Scale application to three replicas"
```

Now *"who changed the deployment?"* and *"what changed?"* both have answers, and
`git revert` is a rollback.

> 💡 **Separate the app repo from the config repo.** If the GitOps repo is the same one CI
> writes image tags into, every deploy commit retriggers CI. Two repos (or at least a
> dedicated branch/path) keeps the loop clean.

```text
Git  ──desired──▶  Argo CD  ──reconcile──▶  Kubernetes  (actual)
```

**Git is not the cluster.** Argo CD is the thing that connects them.

---

## 🐙 Argo CD

```text
You → git push → GitHub → Argo CD detects → Kubernetes updated automatically
```

### Install

```bash
kind create cluster --name session20
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl get pods -n argocd -w        # 2–5 min; images are large
```

```text
argocd-application-controller-0        1/1 Running     ← the reconciler
argocd-applicationset-controller-...   1/1 Running
argocd-dex-server-...                  1/1 Running     ← SSO
argocd-notifications-controller-...    1/1 Running
argocd-redis-...                       1/1 Running     ← cache
argocd-repo-server-...                 1/1 Running     ← clones & renders manifests
argocd-server-...                      1/1 Running     ← API + UI
```

### Access the UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

<https://localhost:8080> (accept the self-signed cert warning).

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

Login `admin` + that password. (⭐ That's a Kubernetes **Secret**, base64-encoded not
encrypted — [Session 12](./12_Kubernetes_Ingress_ConfigMaps_and_Secrets.md).)

### The `Application` resource — the one manual step

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: session20-app
  namespace: argocd
spec:
  project: default

  source:
    repoURL: https://github.com/Nency-Ravaliya/gitops-demo.git
    targetRevision: main
    path: app                     # ← the folder Argo CD watches

  destination:
    server: https://kubernetes.default.svc
    namespace: session20

  syncPolicy:
    automated:
      prune: true                 # ⭐ delete resources removed from Git
      selfHeal: true              # ⭐ revert manual kubectl changes
    syncOptions:
      - CreateNamespace=true
```

```bash
kubectl apply -f app/argocd-application.yaml      # you run this ONCE
```

| File | What it is | Who applies it |
|---|---|---|
| `app/deployment.yaml` | your application | **Argo CD**, from Git |
| `app/service.yaml` | exposes it | **Argo CD**, from Git |
| `argocd-application.yaml` | points Argo CD at the repo | ⭐ **you, once, manually** |

> ⭐ **The key confusion point:** you never `kubectl apply` the deployment or service again.
> You apply the `Application` once; from then on every change goes through `git push`.

> ⚠️ Keep `argocd-application.yaml` **outside** the watched `path:`. If it's inside `app/`,
> Argo CD renders the Application as one of its own managed workloads — an object that
> manages itself. (The repo's comments call this out explicitly.)

### `prune` and `selfHeal`

| Flag | Without it | With it |
|---|---|---|
| `prune: true` | deleting a file from Git leaves the resource running forever | the resource is deleted too |
| `selfHeal: true` | a manual `kubectl scale` sticks | ⭐ Argo CD reverts it within ~3 min |

⭐ `selfHeal` is what makes Git *actually* the source of truth rather than a polite suggestion.
It also permanently ends "someone changed something in prod and didn't tell anyone".

---

## 🧪 GitOps in Action — the full lab

```bash
kubectl get pods -n session20
kubectl get deployment session20-gitops-app -n session20
kubectl get applications -n argocd
```

```text
NAME            SYNC STATUS   HEALTH STATUS
session20-app   Synced        Healthy
```

⭐ Two independent statuses:
**Sync** = does the cluster match Git? **Health** = are the workloads actually working?
`Synced + Degraded` means Git deployed exactly what it said — and what it said is broken.

```bash
kubectl port-forward svc/session20-gitops-app -n session20 9090:80   # → http://localhost:9090
```

### Scale — by committing, not by `kubectl`

```yaml
# app/deployment.yaml
replicas: 5   →   replicas: 2
```

```bash
git add app/deployment.yaml
git commit -m "Scale down to 2 replicas"
git push
kubectl get pods -n session20 -w      # pods terminate within ~30s–3min
```

```text
NAME                   READY   UP-TO-DATE   AVAILABLE
session20-gitops-app   2/2     2            2
```

### The sync loop

```
  edit app/deployment.yaml, git push
                │
                ▼
         GitHub repository
                │
     Argo CD polls (~3 min default)
                │
                ▼
      ┌────────────────────┐
      │      Argo CD       │
      │ sees Git changed   │
      │ diffs desired vs   │
      │   actual cluster   │
      │ applies the delta  │
      └─────────┬──────────┘
                ▼
         Kubernetes (kind)
      namespace: session20
```

> 💡 The 3-minute poll is the default; a **webhook** from GitHub makes it near-instant.
> Click **Refresh**/**Sync** in the UI or `argocd app sync <name>` to force it.

### Troubleshooting

| Problem | Fix |
|---|---|
| App not in the namespace | `kubectl get applications -n argocd` — did you apply the Application? |
| `OutOfSync`, not syncing | `syncPolicy.automated` missing. Or force: `kubectl patch application <name> -n argocd --type merge -p '{"operation":{"sync":{}}}'` |
| `applicationset-controller` CrashLoopBackOff (`no matches for kind "ApplicationSet"`) | CRD missing — re-apply `install.yaml`, then `kubectl rollout restart deployment argocd-applicationset-controller -n argocd` |
| `Synced` but `Degraded` | Git is applied correctly; the **app** is broken → [Session 14](./14_Kubernetes_Troubleshooting.md) |

### Clean up

```bash
kubectl delete -f app/argocd-application.yaml
kind delete cluster --name session20
```

---

## 🎓 Mini Project

Combine **Kubernetes + Git + GitOps + Argo CD**:

```text
Git (desired) ──▶ Argo CD (sync) ──▶ Kubernetes ──▶ Application
```

**Build:** a Namespace, a Deployment (`replicas: 2`), a Service and an Argo CD Application.

```bash
# 1. cluster
kind create cluster --name session20

# 2. Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. push app/{namespace,deployment,service}.yaml to your own Git repo
#    ⭐ keep argocd-application.yaml OUT of that path

# 4. point the Application at your repoURL, then:
kubectl apply -f app/argocd-application.yaml
kubectl get applications -n argocd      # session20-mini  Synced  Healthy
kubectl get all -n session20
```

### ⭐ Step 7 — change Git, watch the cluster follow

```yaml
replicas: 2  →  replicas: 3
```

```bash
git add . && git commit -m "Scale application to three replicas" && git push
kubectl get deployment -n session20 -w        # → READY 3/3
```

### ⭐ Step 8 — prove self-healing

```bash
kubectl scale deployment session20-mini -n session20 --replicas=1
kubectl get deployment -n session20
```

Git still says `3`, `selfHeal: true` is on — **Argo CD puts it back to 3.** This is the
demonstration that matters:

```text
Git        = desired state
Kubernetes = actual state
Argo CD    = reconciler
```

### Final architecture

```text
Developer → Git Repo → (desired state) → Argo CD → (reconciliation) → Kubernetes
                                                                        ├── Deployment → Pods
                                                                        └── Service
```

### Viva questions you should be able to answer

Monitoring vs observability · metrics vs logs vs traces · what Prometheus is · what Grafana is
· what GitOps is · why Git is the source of truth · what Argo CD does · desired state · actual
state · reconciliation · self-healing · what happens when replicas change from 2 to 3 in Git.

---

## 🔭 Beyond the lab: Loki, Jaeger, OpenTelemetry, Flux

| Tool | Role |
|---|---|
| **Loki** | "Prometheus for logs" — indexes **labels**, not full text, so it's cheap. Grafana-native |
| **ELK / OpenSearch** | Full-text log search — powerful, heavier |
| **Jaeger / Tempo** | Distributed tracing backends |
| **OpenTelemetry (OTel)** | ⭐ The vendor-neutral standard for emitting metrics, logs **and** traces. Instrument once, switch backends freely |
| **Thanos / Mimir / Cortex** | Long-term, highly-available Prometheus storage |
| **Alertmanager** | Routing, grouping and silencing alerts |
| **Flux CD** | The other CNCF GitOps controller — no UI, more Git-native, smaller footprint |
| **Argo Rollouts** | Canary and blue-green on top of GitOps ([Session 10](./10_Kubernetes_Pods_ReplicaSets_and_Deployments.md)) |
| **Sealed Secrets / External Secrets / SOPS** | ⭐ How you put secrets in a Git repo safely |

### The secrets problem

GitOps says *everything in Git* — but a Kubernetes Secret is only base64. Three answers:

| Approach | How |
|---|---|
| **Sealed Secrets** | Encrypt with a cluster public key; only the in-cluster controller can decrypt. Safe to commit |
| **External Secrets Operator** | Git stores a *reference*; the operator fetches from Vault / AWS Secrets Manager |
| **SOPS + age/KMS** | Encrypt the values in place; Flux and Argo can decrypt at apply time |

### How the whole course fits together

```
Code (05 Git)
  → build & test (16 Actions)
  → scan (17 DevSecOps)
  → image (06–07 Docker) → registry
  → infrastructure (18–19 Terraform)
  → package (15 Helm)
  → run (09–13 Kubernetes)
  → observe (20 Prometheus/Grafana)
  → reconcile (20 Argo CD)
  → debug (14 Troubleshooting)
  → repeat
```

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Monitoring** | Known signals, dashboards, alerts — *is something wrong?* |
| **Observability** | Understanding internal state from outputs — *why is it wrong?* |
| **Metrics** | Numbers over time — how much / how often |
| **Logs** | Discrete events — what happened |
| **Traces** | One request's journey across services — where the time went |
| **Prometheus** | Pull-based time-series metrics database |
| **Scrape** | Prometheus fetching `/metrics` from a target |
| **`up`** | Built-in metric: 1 = target healthy, 0 = scrape failed |
| **PromQL** | Prometheus query language |
| **Counter / Gauge / Histogram** | Only-up / up-and-down / bucketed observations |
| **`rate()`** | ⭐ Per-second rate of a counter — always wrap counters in it |
| **Exporter** | Sidecar that exposes a third-party system's metrics |
| **Grafana** | Visualisation layer over Prometheus (and many other sources) |
| **Alertmanager** | Groups, dedupes, silences and routes alerts |
| **Golden Signals** | Latency, Traffic, Errors, Saturation |
| **SLI / SLO / Error budget** | Measurement / target / allowed failure |
| **GitOps** | Git is the declarative desired state; an in-cluster agent reconciles continuously |
| **Desired vs actual state** | What Git says vs what the cluster has |
| **Reconciliation** | Continuously moving actual toward desired |
| **Argo CD** | Kubernetes GitOps controller with a UI |
| **`Application` CRD** | Tells Argo CD which repo, path, revision and namespace |
| **`prune`** | Delete cluster resources removed from Git |
| **`selfHeal`** | ⭐ Revert manual cluster changes back to Git |
| **Sync vs Health** | Matches Git? vs actually working? |
| **Pull-based CD** | ⭐ Agent inside the cluster pulls — no cluster credentials in CI |

---

## 🎯 Session Takeaways

1. ⭐ **Monitoring tells you *when* something is wrong; observability tells you *why*.** Production needs both.
2. **Metrics = numbers, logs = events, traces = journey.** In microservices, traces aren't optional.
3. ⭐ **Prometheus pulls.** A failed scrape *is* the health signal — that's what `up` means.
4. **Grafana reaches Prometheus at `http://prometheus:9090`**, the Compose service name — not `localhost`.
5. ⭐ **Always `rate()` a counter, and alert on percentiles not averages.** An average hides your worst 5% of users.
6. **Alert on symptoms, not causes, with a `for:` duration.** Every alert must be actionable or deleted.
7. ⭐ **GitOps = Git is desired state + an in-cluster agent continuously reconciles.** Same control-loop idea as Kubernetes itself, one level up.
8. ⭐ **Pull beats push because cluster credentials never leave the cluster** — and it solves the "CI can't reach my cluster" problem.
9. **You apply the `Application` once. After that, every change is a `git push`.**
10. ⭐ **`selfHeal: true` is what makes Git authoritative** — a manual `kubectl scale` gets reverted. `prune: true` makes deletions real.
11. **Keep `argocd-application.yaml` outside the watched `path`,** or Argo CD manages its own manager.
12. **`Synced` ≠ `Healthy`.** Synced means Git was applied; Healthy means it works.
13. **Secrets need a dedicated answer** (Sealed Secrets / External Secrets / SOPS) before "everything in Git" is safe.

---

## 🔗 References

- Prometheus docs — https://prometheus.io/docs/
- PromQL basics — https://prometheus.io/docs/prometheus/latest/querying/basics/
- Alerting rules — https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
- Grafana docs — https://grafana.com/docs/grafana/latest/
- `kube-prometheus-stack` — https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
- Google SRE Book (Golden Signals, SLOs) — https://sre.google/sre-book/monitoring-distributed-systems/
- OpenTelemetry — https://opentelemetry.io/docs/
- Grafana Loki — https://grafana.com/docs/loki/latest/
- Jaeger — https://www.jaegertracing.io/docs/
- OpenGitOps principles — https://opengitops.dev/
- Argo CD — https://argo-cd.readthedocs.io/
- Argo CD `Application` spec — https://argo-cd.readthedocs.io/en/stable/operator-manual/application.yaml
- Flux CD — https://fluxcd.io/flux/
- Sealed Secrets — https://github.com/bitnami-labs/sealed-secrets
- kind — https://kind.sigs.k8s.io/

---

## ➡️ Next

[Session 21 — Final DevOps Project](./21_Final_DevOps_Project.md) — every session at once:
a real application, dockerised, tested in CI, scanned, published, packaged with Helm and
deployed to Kubernetes.
