# Session 10 — Pods, ReplicaSets & Deployments 🧱

> **Topics:** Pods · Pod Lifecycle · Labels & Selectors · ReplicaSets · Deployments · Scaling ·
> Rolling Updates · Rollbacks
>
> 📁 Repo: `session10-k8s-core-objects/` — core-object manifests, a **12-step Pod lifecycle lab**,
> four **deployment strategy** labs, and two intentionally broken manifests.

---

## 📑 Table of Contents
1. [Pods](#-pods)
2. [Multi-Container Pods](#-multi-container-pods)
3. [Pod Lifecycle](#-pod-lifecycle)
4. [The 12 Lifecycle Scenarios](#-the-12-lifecycle-scenarios-lab)
5. [Labels & Selectors](#-labels--selectors)
6. [ReplicaSets](#-replicasets)
7. [Deployments](#-deployments)
8. [Scaling](#-scaling)
9. [Rolling Updates](#-rolling-updates)
10. [Rollbacks](#-rollbacks)
11. [Deployment Strategies Compared](#-the-four-deployment-strategies)
12. [Blue-Green](#-blue-green-deployment)
13. [Canary](#-canary-deployment)
14. [Recreate](#-recreate-strategy)
15. [StatefulSets & DaemonSets](#-statefulsets--daemonsets)
16. [Troubleshooting Drills](#-troubleshooting-drills)
17. [Key Terms Recap](#-key-terms-recap)

---

## 📦 Pods

> ⭐ **A Pod is the smallest deployable unit in Kubernetes — not a container.**
> One or more containers that **share a network namespace, IP address, and storage volumes**, and
> are always scheduled onto the **same node**.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
spec:
  containers:
    - name: nginx
      image: nginx:latest
      ports:
        - containerPort: 80
```

**With resource requests and limits** (`pod/nginx-pod.yaml`):
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: yatri-demo-pod
  labels:
    app: yatri-demo
    tier: frontend
spec:
  containers:
    - name: nginx-container
      image: nginx:1.25-alpine
      ports:
        - containerPort: 80
      resources:
        requests:          # ⭐ what the SCHEDULER reserves
          cpu: "50m"
          memory: "64Mi"
        limits:            # ⭐ hard ceiling — exceed memory and you get OOMKilled
          cpu: "200m"
          memory: "128Mi"
```

| | `requests` | `limits` |
|---|---|---|
| Used by | ⭐ **The scheduler** (capacity planning) | ⭐ **The kubelet/kernel** (enforcement) |
| Meaning | "Guarantee me at least this" | "Never let me exceed this" |
| Exceeding CPU | — | Throttled |
| Exceeding memory | — | ⭐ **OOMKilled** (exit 137 — Session 6) |

> ⭐ **`50m` = 50 millicores = 0.05 of one CPU core.** `1000m` = 1 full core.

**Key Pod facts:**
- ⭐ **Pods are ephemeral and disposable** — they are never "repaired", only replaced.
- ⭐ **Every Pod gets its own IP**, and that IP **changes** when the Pod is recreated. This is
  precisely why Services exist (Session 11).
- Containers in a Pod reach each other on ⭐ **`localhost`** (shared network namespace).
- ⭐ **You rarely create bare Pods** — a bare Pod that dies stays dead. Use a Deployment.

---

## 🧩 Multi-Container Pods

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: app
      image: nginx
    - name: logger
      image: busybox
      command: ["sh", "-c", "while true; do echo log; sleep 5; done"]
```

```
   One Pod
     ├── app container      ⭐ shares: network (localhost), volumes, lifecycle
     └── sidecar container
```

**Common patterns:**
| Pattern | Example |
|---|---|
| ⭐ **Sidecar** | Log shipper, metrics exporter, service-mesh proxy (Envoy) |
| **Ambassador** | Proxy that simplifies outbound connections |
| **Adapter** | Reformats output into a standard shape |

> ⭐ **The rule: one container per Pod unless the containers must share a lifecycle, network, or
> filesystem.** A web server + its database are **not** a multi-container Pod — they scale
> independently and belong in separate Deployments.

**Init containers** run **to completion, in order, before** app containers start:
```yaml
spec:
  initContainers:
    - name: setup
      image: busybox:1.36
      command: ["sh", "-c", "echo 'Init container running'; sleep 10; echo 'Init complete'"]
  containers:
    - name: app
      image: nginx:1.27
```
```
   Init container runs first
           ↓
   Init completes
           ↓
   Main container starts        ⭐ used for migrations, waiting on dependencies, fetching config
```

---

## 🔄 Pod Lifecycle

### ⭐ Pod **phases** vs what `kubectl get pods` shows

> **`kubectl get pods` may display values such as** Pending · Running · Completed · Error ·
> CrashLoopBackOff · ImagePullBackOff · ContainerCreating · Terminating
>
> ⭐⭐ **These are NOT all official Pod phases.**

**The 5 official Pod phases:**
| Phase | Meaning |
|---|---|
| **Pending** | Accepted by the cluster, but not all containers are running (scheduling, image pull) |
| **Running** | Bound to a node, at least one container running |
| **Succeeded** | All containers terminated **successfully** and will not restart |
| **Failed** | All containers terminated, **at least one failed** |
| **Unknown** | The node's state couldn't be obtained |

**The 3 container states:**
| State | Meaning |
|---|---|
| **Waiting** | Pulling the image, waiting on a dependency (`CrashLoopBackOff`, `ImagePullBackOff` live here) |
| **Running** | Executing |
| **Terminated** | Finished, with an exit code and reason |

> ⭐ **So `CrashLoopBackOff` is a *container state reason*, not a Pod phase.** Knowing this is what
> lets you read `kubectl describe` properly.

```bash
kubectl get pods -w                                            # ⭐ watch phases change live
kubectl describe pod <pod>                                     # phase + container states + EVENTS
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[0].state}'
kubectl get pod <pod> -o yaml                                  # full status
```

---

## 🧪 The 12 Lifecycle Scenarios (lab)

`pod-lifecycle/` reproduces every state deliberately. **Run `kubectl get pods -w` in one terminal
and apply these from another.**

| # | File | What it demonstrates |
|---|---|---|
| 1 | `01-running.yaml` | Healthy `1/1 Running` |
| 2 | `02-pending.yaml` | ⭐ Requests **9Gi** memory → unschedulable → stuck **Pending** |
| 3 | `03-succeeded.yaml` | `exit 0` + `restartPolicy: Never` → **Completed** / phase **Succeeded** |
| 4 | `04-failed.yaml` | `exit 1` + `restartPolicy: Never` → **Error** / phase **Failed** |
| 5 | `05-crashloopbackoff.yaml` | Exits 1 repeatedly → restarts with ⭐ **exponential backoff** |
| 6 | `06-imagepullbackoff.yaml` | Nonsense image name → **ImagePullBackOff** |
| 7 | `07-readiness.yaml` | ⭐ **Running ≠ Ready** |
| 8 | `08-liveness.yaml` | Health file deleted after 20 s → probe fails → ⭐ **container restarts** |
| 9 | `09-startup.yaml` | App takes 30 s to start; startup probe protects it |
| 10 | `10-init-container.yaml` | Init runs to completion before the app |
| 11 | `11-multi-container.yaml` | `2/2` — two containers, two log streams |
| 12 | `12-termination.yaml` | ⭐ **Graceful shutdown** — traps SIGTERM, cleans up, exits |

### The instructive ones

**#2 Pending — the scheduler has nowhere to put it**
```yaml
resources:
  requests:
    cpu: "1"
    memory: "9Gi"      # ⭐ larger than any node → stays Pending forever
```
> ⭐ **Pending almost always means the scheduler failed**, and `kubectl describe pod` says exactly
> why in **Events** (`Insufficient memory`, `node(s) had taint`, `no nodes available`).

**#5 CrashLoopBackOff — the container starts, exits 1, restarts, and keeps failing**
```bash
kubectl describe pod lifecycle-crashloop
kubectl logs lifecycle-crashloop
kubectl logs lifecycle-crashloop --previous     # ⭐ logs from the CRASHED instance — the key flag
```
> ⭐ **`--previous` is the whole trick.** The current container just started and has no useful logs;
> the *dead* one holds the error. **BackOff** means Kubernetes is deliberately waiting longer
> between restarts (10 s, 20 s, 40 s… capped at 5 min).

**#7 Readiness — the teaching point of the whole lab**
> ⭐⭐ **`Running != Ready`**
>
> **Readiness answers: "Should this Pod receive traffic?"**

```
READY   STATUS
0/1     Running        ⭐ the container is alive, but the Service will NOT send it traffic
1/1     Running        ready
```

**#12 Graceful termination**
```yaml
spec:
  terminationGracePeriodSeconds: 20
  containers:
    - name: graceful-app
      command:
        - sh
        - -c
        - |
          trap 'echo "SIGTERM received; cleaning up..."; sleep 10; echo "Cleanup complete"; exit 0' TERM
          echo "Application running"
          while true; do sleep 2; done
```
> ⭐ **The same SIGTERM contract as Docker (Sessions 2 & 6):** Kubernetes sends **SIGTERM**, waits
> `terminationGracePeriodSeconds` (default **30**), then sends **SIGKILL**. Handle SIGTERM or your
> in-flight requests die.

### The six questions to ask for every scenario
> 1. What state/status do you see?
> 2. Is the container running?
> 3. Is the Pod ready?
> 4. Did the container restart?
> 5. Why did this happen?
> 6. Which command would you use to debug it?

> ⭐ **The three most useful debugging commands:**
> ```bash
> kubectl get pod <pod>
> kubectl describe pod <pod>
> kubectl logs <pod>
> ```

---

## 🏷️ Labels & Selectors

> ⭐ **Labels are how *everything* in Kubernetes finds everything else.** ReplicaSets find their
> Pods, Services find their endpoints, and you find your workloads — all by label.

```yaml
metadata:
  labels:
    app: yatri-backend
    tier: frontend
    version: v1
    track: stable
```

```bash
kubectl get pods --show-labels
kubectl get pods -l app=nginx                    # ⭐ equality
kubectl get pods -l 'version in (v1,v2)'         # set-based
kubectl get pods -l app=nginx,tier=frontend      # AND
kubectl label pod mypod env=prod                 # add
kubectl label pod mypod env-                     # remove
```

**The selector contract:**
```yaml
spec:
  selector:
    matchLabels:
      app: nginx        # ⭐ MUST match...
  template:
    metadata:
      labels:
        app: nginx      # ⭐ ...this, or the API server rejects the object
```

> ⭐ **Labels vs annotations:** labels are for **selection** (queryable, indexed); annotations are
> for **arbitrary metadata** (build IDs, ingress config) and cannot be selected on.

---

## 🔁 ReplicaSets

> **Keeps exactly *N* identical Pods running.** If one dies, it creates a replacement; if there's
> one too many, it deletes one.

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: nginx-rs
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:                     # ⭐ a Pod spec, embedded
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:latest
          ports:
            - containerPort: 80
```

> ⭐⭐ **You almost never create a ReplicaSet directly.** A ReplicaSet cannot update its Pods to a new
> image without being deleted and recreated. **Deployments manage ReplicaSets for you** — that's the
> entire reason Deployments exist.

```bash
kubectl get rs
kubectl delete pod <one-of-them>    # ⭐ watch it get recreated within seconds — self-healing
```

---

## 🚀 Deployments

> ⭐ **The object you actually use.** A Deployment manages ReplicaSets, and ReplicaSets manage Pods.

```
   Deployment
       │  creates & versions
       ▼
   ReplicaSet (v1)      ReplicaSet (v2)      ⭐ one RS per revision
       │                     │
       ▼                     ▼
   [Pod][Pod][Pod]       [Pod][Pod][Pod]
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
          ports:
            - containerPort: 80
```

```bash
kubectl apply -f deployment.yml
kubectl get deployments
kubectl get rs                                  # ⭐ see the ReplicaSet it created
kubectl rollout status deployment/nginx-deployment
kubectl describe deployment nginx-deployment
```

---

## 📈 Scaling

```bash
kubectl scale deployment nginx-deployment --replicas=5
kubectl get pods -w

# or declaratively — edit replicas in the YAML and:
kubectl apply -f deployment.yml
```

> ⭐ **Scaling is instant and cheap** because it only changes a number in etcd; the ReplicaSet
> controller does the rest. Automating this number is **HPA** (Session 13).

---

## 🔄 Rolling Updates

> ⭐ **The default strategy.** Instead of killing all old Pods at once (downtime), Kubernetes
> **incrementally replaces** old Pods with new ones while the Service stays alive throughout.

```
BEFORE UPDATE              DURING UPDATE              AFTER UPDATE
4 pods v1                  3 pods v1 + 1 pod v2       4 pods v2
[v1][v1][v1][v1]    ->     [v1][v1][v1][v2]    ->     [v2][v2][v2][v2]
  Users served               Users still served         Users on new version
```

### The two parameters that control it ⭐
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # ⭐ how many EXTRA pods may exist above the desired count
    maxUnavailable: 0  # ⭐ how many pods may be MISSING from the desired count
```

| Setting | Effect |
|---|---|
| `maxSurge: 1` | 4 desired + 1 surge = max **5** pods during rollout |
| ⭐ `maxUnavailable: 0` | Capacity **never drops below 4** |
| `maxSurge: 25%` | Percentages work too — cloud-cost efficient |
| `maxUnavailable: 1` | Faster rollout, brief 75% capacity |

### The mechanism
```
1. Start 1 new v2 pod (maxSurge: 1)
2. ⭐ WAIT until it passes its readinessProbe
3. Only then terminate 1 old v1 pod
4. Repeat until all pods are v2
   → at no point do 0 pods exist ⇒ zero downtime
```

> ⭐⭐ **The rollout only advances after the new Pod passes its readiness probe. Without a readiness
> probe, Kubernetes blindly moves forward and can route traffic to a broken Pod.** This is the
> single most important reason to define readiness probes.
>
> ⭐ **Always set `maxUnavailable: 0` for production workloads with SLAs.**

### Commands
```bash
kubectl apply -f deployment-v2.yaml            # trigger the rollout
kubectl rollout status deployment/app-rolling  # block until complete
kubectl get pods -l app=app-rolling -w         # ⭐ watch pods churn

# prove zero downtime from a second terminal:
while true; do curl -s http://$(minikube ip):30010 | grep VERSION; sleep 1; done
# → v1 … v1 … v2 … v2   ⭐ never an error

kubectl rollout pause  deployment/app-rolling  # ⭐ freeze mid-rollout
kubectl rollout resume deployment/app-rolling
```

> ⭐ Rolling updates are the backbone of **Continuous Delivery pipelines** in GitHub Actions,
> Argo CD and Tekton.

---

## ⏪ Rollbacks

```bash
kubectl rollout history deployment/app-rolling
```
```text
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```
```bash
kubectl rollout undo deployment/app-rolling               # ⭐ back one revision
kubectl rollout undo deployment/app-rolling --to-revision=1
kubectl rollout history deployment/app-rolling --revision=2   # inspect a revision
```

> ⭐ **Kubernetes keeps the last 10 revisions by default** (`revisionHistoryLimit: 10`) — that's what
> those old ReplicaSets scaled to 0 are for. **Rollback is one command** because the old ReplicaSet
> still exists; K8s just scales it back up.

### Why a broken rollout is safe ⭐
`troubleshooting/broken-image.yaml` deploys `yatri-backend:non-existent-tag-v999` with
`maxSurge: 1, maxUnavailable: 0`:
```
new surge pod → ImagePullBackOff → never becomes Ready
              → ⭐ rollout HALTS
              → old pods are never terminated (maxUnavailable: 0)
              → ⭐ the app keeps serving from v1 the whole time
```
> ⭐ **`maxUnavailable: 0` turns a bad deploy into a stalled deploy instead of an outage.**

---

## 📊 The Four Deployment Strategies

| Strategy | Downtime? | Resource overhead | Rollback speed | Best for |
|---|---|---|---|---|
| ⭐ **RollingUpdate** | **Zero** | Low (+25% during update) | Fast (`rollout undo`) | **Default** for stateless web apps & microservices |
| **Blue-Green** | **Zero** | ⭐ **High (200%)** | ⭐ **Instant** (change selector) | Mission-critical apps needing atomic cutover |
| **Canary** | **Zero** | Low (small canary pool) | Fast (scale canary to 0) | High-traffic services needing real-user validation |
| **Recreate** | ⭐ **Yes** | **Zero** (no surge) | Slower | Schema migrations, RWO volumes, dev environments |

### 🍽️ The restaurant analogy
| Strategy | Analogy |
|---|---|
| **Rolling Update** | Renovate room by room while the restaurant stays open |
| **Blue-Green** | Build a whole new restaurant across the street, then redirect customers |
| **Canary** | Open a tiny VIP tasting counter with the new menu for 10% of customers |
| **Recreate** | *"Closed for renovations 2 PM–5 PM."* Gut it, rebuild, reopen |

---

## 🔵🟢 Blue-Green Deployment

> **Two identical production environments side by side. Blue = live. Green = new version, fully
> deployed and tested but receiving zero traffic. Flip one switch — the Service selector — and 100%
> of traffic moves instantly.**

```
PHASE 1: Normal
  Users → [Service] → [BLUE v1] [BLUE v1] [BLUE v1]   (LIVE)
                      [GREEN v2][GREEN v2][GREEN v2]  (IDLE — warming up)

PHASE 2: Flip (kubectl apply service-green.yaml)
  Users → [Service] → [GREEN v2][GREEN v2][GREEN v2]  (NOW LIVE)
                      [BLUE v1] [BLUE v1] [BLUE v1]   (STANDBY — instant rollback)

PHASE 3: Rollback — just flip back  (under 5 seconds)
```

### Why, over a rolling update?
> **Problems with rolling update:** during the rollout **both v1 and v2 pods serve traffic
> simultaneously**. ⭐ **If v2 has a database schema migration incompatible with v1, mixed traffic
> causes data corruption.** You also can't load-test the new version with zero user impact.

**Benefits:** instant cutover (<5 s) · instant rollback (<5 s) · pre-production testing under real
cluster conditions · ⭐ **no mixed traffic — 100% on v1 or 100% on v2, never both**.

### The only thing that changes ⭐
```yaml
# service-blue.yaml            # service-green.yaml
spec:                          spec:
  selector:                      selector:
    app: myapp                     app: myapp
    slot: blue     ⭐ ────────▶     slot: green
```

```bash
kubectl apply -f deployment-blue.yaml -f deployment-green.yaml   # 6 pods total
kubectl apply -f service-blue.yaml                               # blue goes live

kubectl describe svc myapp-service | grep Selector   # app=myapp,slot=blue
kubectl get endpoints myapp-service                  # ⭐ 3 blue pod IPs

kubectl apply -f service-green.yaml                  # ⭐ THE SWITCH
kubectl get endpoints myapp-service                  # ⭐ now 3 green pod IPs

kubectl apply -f service-blue.yaml                   # rollback in <5 s
kubectl delete deployment app-blue                   # decommission once green is proven
```

> ⭐ **Costs 2× compute** — that's the price of instant switchover.
> ⭐ **Keep Blue running at least 24 hours** as your rollback net.
> ⭐ Preferred for **database schema changes**: migrate against Green *before* switching traffic.

---

## 🐤 Canary Deployment

> **Release to a small percentage of real users first; monitor; then shift more traffic.**
>
> *(From mining: canaries warned miners of toxic gas before it harmed them. Canary pods absorb
> defects before all users are impacted.)*

```
                  [SERVICE] (port 30030)
                       │
      [kube-proxy round-robins across ALL matching pods]
                       │
  ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬──────┐
  ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼
[stable ×9  v1                        ]  [canary ×1  v2]
      90% of requests                        10%
```

### ⭐ Traffic split is pure pod-count math
> **Kubernetes Services use round-robin across all matching endpoints. There are no traffic-weight
> settings.** The split is driven entirely by **pod ratio**:

| Stable | Canary | Total | Canary traffic |
|---|---|---|---|
| 9 | 1 | 10 | **10%** |
| 8 | 2 | 10 | 20% |
| 5 | 5 | 10 | 50% |
| 0 | 10 | 10 | 100% (promoted) |

### The critical label detail ⭐
> ⭐⭐ **The Service selects BOTH stable and canary pods using only the shared label
> (`app: myapp-canary`). The `track: stable` / `track: canary` labels are for human identification
> only — they are NOT used for routing.**

```bash
kubectl apply -f deployment-stable.yaml   # 9 replicas v1
kubectl apply -f service.yaml
kubectl apply -f deployment-canary.yaml   # 1 replica v2

# observe the split
for i in $(seq 1 20); do curl -s http://$(minikube ip):30030 | grep -o "STABLE v1\|CANARY v2"; done
# ⭐ ~1–2 CANARY hits out of 20

# shift to 30%
kubectl scale deployment app-canary --replicas=3
kubectl scale deployment app-stable --replicas=7

# 7A. promote
kubectl scale deployment app-canary --replicas=9 && kubectl scale deployment app-stable --replicas=0
# 7B. roll back
kubectl scale deployment app-canary --replicas=0 && kubectl scale deployment app-stable --replicas=9
```

> ⭐ **Native canary is approximate.** For precise percentages (e.g. exactly 5.3%) use
> **Argo Rollouts**, **Flagger**, or **NGINX Ingress weight annotations**.
>
> ⭐ **Monitor for at least one full traffic cycle (15–30 min in production)** before increasing.
> **Define alert thresholds BEFORE the canary goes live:** *"if canary error rate > 1% for 5 minutes,
> auto-rollback."*

---

## 🔻 Recreate Strategy

> **All-or-nothing: terminate every old Pod, wait until zero are running, then create the new ones.**

```
[v1][v1][v1]
     ↓  kubectl apply -f deployment-v2.yaml
[Terminating][Terminating][Terminating]
     ↓
[No pods running]   ⭐ DOWNTIME WINDOW (users get 502 / connection refused)
     ↓
[ContainerCreating] ×3
     ↓
[v2][v2][v2]
```

### Why would anyone *choose* downtime? ⭐
| Reason | Detail |
|---|---|
| ⭐ **Breaking schema migrations** | If v1 expects `phone_number` and v2 splits it into `country_code + national_number`, running both **corrupts data**. v1 must be fully down first |
| ⭐ **ReadWriteOnce volumes** | AWS EBS / GCP PD attach to **one node at a time**. A rolling update **deadlocks** — the old pod holds the volume lock. Recreate releases it first |
| **State-locked legacy apps** | License servers, single-writer queues that can't run multi-instance |
| **Resource constraints** | Dev/staging clusters without capacity to surge extra pods |

```bash
# watch the outage happen
while true; do curl -s --connect-timeout 1 http://localhost:30040 | grep -o 'VERSION: [^<]*' \
  || echo "[OUTAGE] Connection failed"; sleep 0.5; done
```
```text
VERSION: v1
VERSION: v1
[OUTAGE] Connection failed      ⭐ proof of the downtime window
[OUTAGE] Connection failed
VERSION: v2 (UPGRADED)
```

> ⭐ **That RWO volume point connects directly to Session 13** — access modes are a real constraint,
> not trivia.

---

## 🗃️ StatefulSets & DaemonSets

### StatefulSet — for stateful, identity-sensitive workloads
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: "mysql"          # ⭐ requires a HEADLESS service (Session 11)
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
        - name: mysql
          image: mysql:5.7
          ports:
            - containerPort: 3306
          env:
            - name: MYSQL_ROOT_PASSWORD
              value: "password"
          volumeMounts:
            - name: mysql-persistent-storage
              mountPath: /var/lib/mysql
  volumeClaimTemplates:          # ⭐ one PVC created PER POD automatically
    - metadata:
        name: mysql-persistent-storage
      spec:
        accessModes: [ "ReadWriteOnce" ]
        resources:
          requests:
            storage: 5Gi
```

| | **Deployment** | ⭐ **StatefulSet** |
|---|---|---|
| Pod names | Random (`nginx-7b5f9d4c6-5kghm`) | ⭐ **Ordinal & stable** (`mysql-0`, `mysql-1`, `mysql-2`) |
| Identity across restarts | None | ⭐ **Preserved** |
| Storage | Shared or none | ⭐ **One PVC per Pod** via `volumeClaimTemplates` |
| Start/stop order | Parallel | ⭐ **Ordered** (0, then 1, then 2) |
| DNS | Service only | ⭐ **Per-pod DNS** (`mysql-0.mysql.default.svc.cluster.local`) |
| Use for | Stateless apps | Databases, Kafka, ZooKeeper, Cassandra |

### DaemonSet — one Pod on **every** node
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-logging-agent
spec:
  selector:
    matchLabels:
      app: node-logging-agent
  template:
    metadata:
      labels:
        app: node-logging-agent
    spec:
      containers:
        - name: fluent-logger
          image: busybox:1.36
          command: ["sh", "-c", "while true; do echo \"[$(date)] Collecting host system metrics on $(hostname)\"; sleep 10; done"]
          resources:
            requests: { cpu: "10m", memory: "16Mi" }
            limits:   { cpu: "50m", memory: "32Mi" }
```
> ⭐ **No `replicas` field** — the count *is* the node count. Add a node, you automatically get a Pod.
> **Used for:** log collectors (Fluentd), metrics agents (node-exporter), CNI plugins, **kube-proxy
> itself**.

### Job & CronJob — run-to-completion work
> ⚠️ *Listed in the cheat sheet below but not in the repo's manifests — worth knowing, because this
> is the one workload family that is **supposed** to exit.*

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
spec:
  completions: 1          # how many successful pods are needed
  parallelism: 1          # how many run at once
  backoffLimit: 4         # ⭐ retries before the Job is marked Failed
  template:
    spec:
      restartPolicy: Never    # ⭐ MUST be Never or OnFailure — not Always
      containers:
        - name: migrate
          image: myapp:1.0
          command: ["python", "manage.py", "migrate"]
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: nightly-backup
spec:
  schedule: "0 2 * * *"                    # ⭐ standard cron syntax (Session 2)
  concurrencyPolicy: Forbid                # ⭐ don't start if the last run is still going
  successfulJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: backup
              image: backup-tool:1.0
```

> ⭐ **`restartPolicy: Always` is invalid for a Job** — "always restart" and "run to completion" are
> contradictory. A Deployment's Pods are `Always`; a Job's must be `Never` or `OnFailure`.
>
> ⭐ **Completed Job Pods are kept, not deleted**, so you can read their logs — which is why
> `kubectl get pods` slowly fills with `Completed` rows. Use `ttlSecondsAfterFinished` to auto-clean.
>
> 💡 **Session 12 connection:** a database migration Job is the usual companion to the **Recreate**
> strategy — run the migration Job to completion, *then* roll out the new version.

### The workload controller cheat sheet
| Controller | Guarantee |
|---|---|
| **Deployment** | N interchangeable stateless Pods, rolling updates |
| **ReplicaSet** | N Pods (managed *by* a Deployment) |
| **StatefulSet** | N Pods with **stable identity + own storage + ordering** |
| **DaemonSet** | **One Pod per node** |
| **Job** | Run N Pods **to completion** |
| **CronJob** | A Job **on a schedule** |

---

## 🔧 Troubleshooting Drills

### Drill 1 — Selector mismatch (`troubleshooting/selector-mismatch.yaml`)
```yaml
spec:
  selector:
    matchLabels:
      app: correct-app-name
  template:
    metadata:
      labels:
        app: wrong-app-name      # ⭐ BUG: does not match the selector above
```
> ⭐ **The API server rejects this at apply time** — `selector` does not match `template.metadata.labels`.
> A validation error, not a runtime one. **And note: `spec.selector` is immutable** on an existing
> Deployment — you must delete and recreate to change it.

### Drill 2 — Broken image rollout (`troubleshooting/broken-image.yaml`)
Covered above — the rollout **halts** while old Pods keep serving.

### The general debugging ladder
```bash
kubectl get pods                       # 1. what's the status?
kubectl describe pod <pod>             # 2. ⭐ read EVENTS at the bottom
kubectl logs <pod>                     # 3. app output
kubectl logs <pod> --previous          # 4. ⭐ CrashLoopBackOff → the dead container's logs
kubectl get events --sort-by=.lastTimestamp   # 5. cluster-wide timeline
kubectl exec -it <pod> -- sh           # 6. get inside
```

| Symptom | Likely cause |
|---|---|
| **Pending** | ⭐ Insufficient CPU/memory, taints, unbound PVC — `describe` says which |
| **ImagePullBackOff** | Wrong image name/tag, private registry needs `imagePullSecrets` |
| **CrashLoopBackOff** | ⭐ App exits on start — `logs --previous` |
| **0/1 Running** | ⭐ Readiness probe failing — app is up but not serving |
| **OOMKilled (137)** | Memory limit too low |
| **Rollout stuck** | New pods never become Ready — `rollout status` + `describe` |
| **Selector mismatch error** | `template.labels` ≠ `spec.selector.matchLabels` |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| ⭐ **Pod** | Smallest deployable unit; containers sharing **network, storage, node, lifecycle** |
| **containerPort** | Documentation only — doesn't publish anything |
| ⭐ **requests / limits** | Scheduler reservation / hard ceiling (memory over limit ⇒ **OOMKilled**) |
| **Millicore** | `50m` = 0.05 CPU |
| **Init container** | Runs to completion **before** app containers |
| **Sidecar** | Helper container sharing the Pod |
| ⭐ **Pod phase** | **Pending · Running · Succeeded · Failed · Unknown** — only these five |
| ⭐ **Container state** | Waiting · Running · Terminated (`CrashLoopBackOff` lives in **Waiting**) |
| ⭐ **Running ≠ Ready** | Readiness decides whether the Service sends traffic |
| **CrashLoopBackOff** | Repeated crash with **exponential backoff**; debug with `logs --previous` |
| ⭐ **Labels / selectors** | How every object finds every other object |
| **ReplicaSet** | Keeps N Pods alive; ⭐ managed *by* a Deployment, not by you |
| ⭐ **Deployment** | Manages ReplicaSets → rolling updates + rollbacks |
| ⭐ **maxSurge / maxUnavailable** | Extra pods allowed / missing pods allowed during a rollout |
| ⭐ **Readiness gates the rollout** | Without a readiness probe, K8s can promote a broken Pod |
| **revisionHistoryLimit** | Default **10** old ReplicaSets kept for rollback |
| **Blue-Green** | Two full environments; flip the Service **selector**; 2× cost, instant rollback |
| ⭐ **Canary** | Traffic split by **pod-count ratio** only; `track` labels are cosmetic |
| **Recreate** | Deliberate downtime — for **breaking migrations** and **RWO volumes** |
| **StatefulSet** | Stable ordinal names, per-pod PVC, ordered rollout, per-pod DNS |
| **DaemonSet** | One Pod per node; no `replicas` field |
| **Job / CronJob** | Run-to-completion / scheduled; ⭐ `restartPolicy` must be `Never` or `OnFailure` |
| **`backoffLimit`** | Job retries before being marked Failed |
| **`concurrencyPolicy: Forbid`** | Stops a CronJob overlapping with its previous run |
| **terminationGracePeriodSeconds** | SIGTERM → wait (default 30 s) → SIGKILL |

---

## 🎯 Session Takeaways

1. ⭐ **The Pod, not the container, is the unit** — shared IP, storage, node and lifecycle. Pods are
   **disposable**, and their **IPs change**, which is why Services exist.
2. ⭐ **One container per Pod unless they must share a lifecycle.** Sidecars yes; app + database no.
3. ⭐ **Only five Pod phases exist.** `CrashLoopBackOff` and `ImagePullBackOff` are **container state
   reasons**, not phases — knowing this makes `describe` readable.
4. ⭐ **`Running != Ready`.** Readiness decides traffic; liveness decides restarts.
5. ⭐ **`kubectl logs --previous` is the CrashLoopBackOff command** — the live container has no
   useful logs, the dead one does.
6. **Pending = the scheduler couldn't place it**, and `describe` Events tell you exactly why.
7. ⭐ **Labels are the universal glue**, and `selector` must match `template.labels` or the API server
   rejects the object outright.
8. ⭐ **Never create bare Pods or bare ReplicaSets — use a Deployment.** It versions ReplicaSets,
   which is what makes rollback one command.
9. ⭐⭐ **Rolling updates only advance when a new Pod passes readiness.** No readiness probe means
   Kubernetes will happily route traffic to a broken Pod.
10. ⭐ **`maxUnavailable: 0` converts a bad deploy into a stalled deploy rather than an outage** —
    exactly what the broken-image drill proves.
11. ⭐ **Pick the strategy by constraint:** Rolling (default) · Blue-Green (atomic cutover, no mixed
    traffic, 2× cost) · Canary (real-user validation, ratio-based) · **Recreate (when mixed versions
    would corrupt data, or an RWO volume can't be shared)**.
12. ⭐ **Canary traffic is pod-count ratio only** — there are no weights in a plain Service, and the
    `track` labels don't route anything.
13. **StatefulSets give identity + per-pod storage + ordering; DaemonSets give one Pod per node.**

---

## 🔗 References
- Instructor's Kubernetes repo — https://github.com/Nency-Ravaliya/Kubernetes
- Core objects — https://github.com/Nency-Ravaliya/Kubernetes/blob/main/core-objects.md
- Pod lifecycle — https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- Deployments — https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Course repo — https://github.com/Nency-Ravaliya/devops-heros

---

## ➡️ Next
**[Session 11 — Kubernetes Networking & Services](./11_Kubernetes_Networking_and_Services.md)**
