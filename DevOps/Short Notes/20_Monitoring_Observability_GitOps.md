# ⚡ S20 · Monitoring, Observability & GitOps

> *Revision card.* Full notes → [Session 20](../20_Monitoring_Observability_and_GitOps.md)

---

## 🔑 One-line core

***Monitoring says WHEN. Observability says WHY.***
**GitOps = Git is desired state + an in-cluster agent reconciles, forever.**

---

## 🔭 Monitoring vs Observability

| Monitoring | Observability |
|---|---|
| *Is something wrong?* | *Why is it wrong?* |
| **known** failure signals | explore **unknown** problems |
| dashboards, alerts | metrics **+ logs + traces** |

🚗 Dashboard light says *engine hot* (monitoring) vs checking coolant, logs, history
(observability).

> ⭐ The real test: **can you answer a question you didn't think of in advance, without
> shipping new code?**

---

## 📶 The three signals

```
Metrics = numbers  →  HOW MUCH / HOW OFTEN
Logs    = events   →  WHAT happened
Traces  = journey  →  WHERE the time went
```

🏏 Cricket: *runs 180, RR 9.0* (metrics) · *"Player X bowled"* (logs) · *follow one
delivery* (traces).

> ⭐ In microservices, **traces are essential** — no single log file sees the whole request.
> 💡 Structured JSON logs with a `trace_id` field link logs ↔ traces.

---

## 🔥 Prometheus — **PULL**, not push

```
app exposes GET /metrics  ──scrape──▶  Prometheus (time-series DB)
```

| Pull gives you | |
|---|---|
| ⭐ **`up` for free** | scrape failed ⇒ target is down |
| no app-side config | the app just serves `/metrics` |
| no thundering herd | Prometheus controls the rate |

```yaml
global: { scrape_interval: 5s }
scrape_configs:
  - job_name: prometheus
    static_configs: [{ targets: ["prometheus:9090"] }]   # ⭐ service NAME, not localhost
```

| Vocabulary | |
|---|---|
| **target** | the thing scraped |
| **scrape** | `GET /metrics` on an interval |
| **label** | key/value dimensions |
| **PromQL** | the query language |

---

## 🧮 Metric types + PromQL

| Type | |
|---|---|
| **Counter** | only goes up (`http_requests_total`) |
| **Gauge** | up and down (`memory_usage_bytes`) |
| **Histogram** | buckets → server-side percentiles |
| Summary | client-side quantiles |

```promql
up                                            # 1 = healthy
rate(http_requests_total[5m])                 # ⭐ ALWAYS rate() a counter
sum(rate(http_requests_total[5m])) by (service)

sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))        # error rate

histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le))   # p95
```

> ⭐ **Percentiles, not averages.** A 200 ms average hides 5% of users waiting 4 seconds.

**Exporters:** node_exporter (host) · kube-state-metrics (K8s objects) · cAdvisor
(containers) · blackbox_exporter (probes).
💡 In K8s just install **`kube-prometheus-stack`** via Helm.

---

## 📈 Grafana

```
Prometheus = DATA        Grafana = PICTURE
```

Data source URL: **`http://prometheus:9090`** — ⭐ the **Compose service name**, not
`localhost` (inside the Grafana container, `localhost` *is* Grafana).

> ⚠️ No volumes in the Compose file ⇒ your dashboards vanish on `docker compose down`.

---

## 🚨 Alerting

**Four Golden Signals:** **Latency · Traffic · Errors · Saturation**
**RED** (services): Rate, Errors, Duration · **USE** (resources): Utilisation,
Saturation, Errors

```yaml
- alert: HighErrorRate
  expr: sum(rate(http_requests_total{status=~"5.."}[5m]))
        / sum(rate(http_requests_total[5m])) > 0.05
  for: 5m                      # ⭐ must HOLD — kills flapping
  labels: { severity: critical }
```

> ⭐ **Alert on symptoms, not causes.** *"Error rate > 5%"* wakes you for a real user
> problem; *"CPU > 80%"* wakes you for something that may be fine.
> ⚠️ **Every alert must be actionable** — alert fatigue is how real outages get ignored.

| | |
|---|---|
| **SLI** | the measurement |
| **SLO** | the target (99.9% < 300 ms / 30 days) |
| **Error budget** | ⭐ `100% − SLO` = 0.1% ≈ **43 min/month** |
| SLA | the contractual version |

⭐ **Budget left → ship features. Budget spent → stop and fix reliability.**

---

## 🔁 GitOps

```
Traditional:  dev → kubectl → cluster
GitOps:       dev → Git → Argo CD → cluster
```

**The four OpenGitOps principles:** declarative · versioned & immutable · **pulled
automatically** · continuously reconciled.

| | **Push CD** | **Pull / GitOps** |
|---|---|---|
| Initiated by | the pipeline, outside | an agent **inside** the cluster |
| Credentials | ⚠️ cluster creds live in CI | ⭐ **none leave the cluster** |
| Firewall | needs inbound to the API server | outbound only |
| Drift | invisible | **detected and corrected** |

> ⭐ Same control loop as Kubernetes itself (Session 9) — one level up.

---

## 🐙 Argo CD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl port-forward svc/argocd-server -n argocd 8080:443
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

```yaml
kind: Application
spec:
  source:      { repoURL: https://github.com/you/gitops.git, targetRevision: main, path: app }
  destination: { server: https://kubernetes.default.svc, namespace: demo }
  syncPolicy:
    automated: { prune: true, selfHeal: true }
    syncOptions: [ CreateNamespace=true ]
```

| | |
|---|---|
| `prune: true` | deleting a file from Git **deletes the resource** |
| **`selfHeal: true`** | ⭐ a manual `kubectl scale` is **reverted** — this is what makes Git authoritative |

> ⭐ **You apply the `Application` ONCE. After that, every change is a `git push`.**
> ⚠️ Keep `argocd-application.yaml` **outside** the watched `path:`, or Argo manages its
> own manager.

| Status | Means |
|---|---|
| **Sync** | does the cluster match Git? |
| **Health** | are the workloads actually working? |

⭐ `Synced + Degraded` = Git deployed exactly what it said, **and what it said is broken**.

💡 Default poll is **~3 min** — a webhook makes it instant.

---

## 🔐 Secrets in GitOps

| | |
|---|---|
| **Sealed Secrets** | encrypt with a cluster key; safe to commit |
| **External Secrets** | Git holds a *reference*; operator fetches from Vault / AWS SM |
| **SOPS + age/KMS** | encrypt values in place |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Push or pull? | Prometheus **pulls** |
| What does `up` mean? | 1 = scrape succeeded |
| Alert on a counter? | ⚠️ never raw — use `rate()` |
| Grafana can't reach Prometheus? | used `localhost` instead of the service name |
| What makes Git authoritative? | **`selfHeal: true`** |
| `Synced` but broken? | **Health ≠ Sync** |

---

⬅️ [S19](./19_Cloud_and_Terraform_in_Action.md) · ➡️ [S21 · Final Project](./21_Final_DevOps_Project.md)
