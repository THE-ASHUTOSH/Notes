# Session 13 — Storage, HPA & Probes 💾

> **Topics:** Volumes · PersistentVolume · PersistentVolumeClaim · StorageClass · HPA ·
> Metrics Server · Liveness Probe · Readiness Probe · Startup Probe
>
> 📁 Repo: `session13/` — `01-volumes`, `02-persistent-storage`, `03-storageclass`, `04-hpa`,
> `05-probes`, and a **mini-project** capstone combining all three pillars.

---

## 📑 Table of Contents
1. [Why Volumes](#-why-volumes)
2. [emptyDir](#-emptydir)
3. [hostPath](#-hostpath)
4. [PersistentVolume & PersistentVolumeClaim](#-persistentvolume--persistentvolumeclaim)
5. [Proving Persistence](#-proving-persistence)
6. [Access Modes](#-access-modes)
7. [StorageClass & Dynamic Provisioning](#-storageclass--dynamic-provisioning)
8. [HPA — Horizontal Pod Autoscaler](#-hpa--horizontal-pod-autoscaler)
9. [Metrics Server](#-metrics-server)
10. [Generating Load](#-generating-load)
11. [Probes](#-probes)
12. [Liveness / Readiness / Startup](#-the-three-probes)
13. [Probe Configuration](#-probe-configuration)
14. [Breaking Probes Deliberately](#-breaking-probes-deliberately)
15. [Mini Project](#-mini-project--production-ready-web-app)
16. [Key Terms Recap](#-key-terms-recap)

---

## 💿 Why Volumes

> **Normally, data written inside a container belongs to the container's filesystem. If the container
> is removed, that data can be lost.** A volume gives the container **another place** to store data.

```text
Container
    │
    │ writes data
    ▼
 Volume
```

> ⭐ **Exactly the Session-8 Docker lesson, one layer up.** There it was "data dies with the
> container"; here it's "data dies with the **Pod**" — and Pods are far more disposable, because
> Kubernetes reschedules them onto different nodes without asking.

---

## 📁 emptyDir

> **Creates an empty directory when the Pod starts.** All containers in that Pod can use it.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: emptydir-demo
spec:
  containers:
    - name: app
      image: nginx:1.27
      volumeMounts:
        - name: app-storage
          mountPath: /data
  volumes:
    - name: app-storage
      emptyDir: {}
```

```text
Pod
 ├── Container
 └── emptyDir
       └── /data
```

> ⭐⭐ **The important point: `emptyDir` exists as long as the POD exists.** Delete and recreate the
> Pod and the old data is gone.

### Proving it
```bash
kubectl apply -f emptydir-pod.yaml
kubectl exec -it emptydir-demo -- bash
  echo "Hello Kubernetes" > /data/message.txt
  cat /data/message.txt          # → Hello Kubernetes
  exit

kubectl delete pod emptydir-demo
kubectl apply -f emptydir-pod.yaml
kubectl exec emptydir-demo -- cat /data/message.txt
```
```text
cat: /data/message.txt: No such file or directory      ⭐ gone
```

> ⭐ **Note what `emptyDir` *does* survive: a container restart.** If the container crashes and the
> kubelet restarts it, the data is still there — only Pod deletion wipes it. That makes `emptyDir`
> genuinely useful for **scratch space, caches, and sharing files between containers in one Pod**.

---

## 🖥️ hostPath

> **Mounts a directory from the Kubernetes *node* into the Pod.**

```yaml
volumes:
  - name: host-storage
    hostPath:
      path: /tmp/hostpath-data
      type: DirectoryOrCreate
```

> ⭐ **`hostPath` is mainly useful for learning, local testing, and special node-level use cases.
> It is generally NOT the first choice for persistent application storage in a production cluster.**

**Why not:** the data is tied to **one specific node**. If the Pod is rescheduled elsewhere it sees
an empty (or different) directory — and mounting host paths is a **security risk**.

---

## 🗄️ PersistentVolume & PersistentVolumeClaim

### The problem
> If an application stores `student-data.txt`, `database-data`, `images` or `logs` inside a Pod and
> that Pod is deleted, **we don't want the data to disappear.**

### The two objects
```text
PV
 │ provides storage
 ▼
PVC
 │ requests storage
 ▼
Pod
```

| Object | Think of it as |
|---|---|
| ⭐ **PersistentVolume (PV)** | **Storage available in the cluster** (supply) |
| ⭐ **PersistentVolumeClaim (PVC)** | **A request for storage** (demand) |

> 🏨 **Analogy:** the PV is a **hotel room**; the PVC is a **booking request** ("1 room, 500 Mi,
> single occupancy"); **Bound** means the booking matched a room.

```yaml
# pv.yaml — the supply
apiVersion: v1
kind: PersistentVolume
metadata:
  name: student-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /tmp/student-data
---
# pvc.yaml — the demand
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: student-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi
---
# pod.yaml — the consumer
apiVersion: v1
kind: Pod
metadata:
  name: storage-demo
spec:
  containers:
    - name: app
      image: nginx:1.27
      volumeMounts:
        - name: persistent-storage
          mountPath: /data
  volumes:
    - name: persistent-storage
      persistentVolumeClaim:
        claimName: student-pvc        # ⭐ the Pod references the CLAIM, never the PV
```

```bash
kubectl apply -f pv.yaml && kubectl get pv
```
```text
NAME         CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS
student-pv   1Gi        RWO            Retain           Available
```
```bash
kubectl apply -f pvc.yaml && kubectl get pvc
```
```text
NAME          STATUS   VOLUME
student-pvc   Bound    student-pv        ⭐ Bound = matched to a suitable PV
```

> ⭐ **A PVC stuck in `Pending` is the classic storage bug** — no PV matches its size/accessMode, or
> there's no default StorageClass. `kubectl describe pvc` says which.
>
> ⭐ **Note the PVC asked for 500Mi and got a 1Gi PV.** Binding matches *at least* the request — you
> get the whole PV, not a slice of it.

### Reclaim policy
| Policy | What happens when the PVC is deleted |
|---|---|
| ⭐ **`Retain`** | PV and data **kept**; admin must clean up manually — safest |
| `Delete` | PV **and the underlying storage** are deleted — the cloud default |
| `Recycle` | Deprecated |

---

## ✅ Proving Persistence

```bash
kubectl apply -f pod.yaml
kubectl exec -it storage-demo -- bash
  echo "Kubernetes Storage" > /data/message.txt
  exit

kubectl delete pod storage-demo          # ⭐ destroy the Pod
kubectl apply -f pod.yaml                # recreate it

kubectl exec storage-demo -- cat /data/message.txt
```
```text
Kubernetes Storage        ⭐ the Pod was deleted, but the data survived
```

**Why?**
```text
Pod  →  PVC  →  PV  →  Storage
⭐ The storage has a lifecycle INDEPENDENT of the individual Pod.
```

---

## 🔐 Access Modes

| Access Mode | Code | Description |
|---|---|---|
| ⭐ **ReadWriteOnce** | **RWO** | Mounted read/write by **one node** |
| **ReadOnlyMany** | **ROX** | Mounted read-only by **many nodes** |
| **ReadWriteMany** | **RWX** | Mounted read/write by **many nodes** |
| **ReadWriteOncePod** | **RWOP** | Mounted read/write by **a single Pod** |

> ⭐⭐ **RWO is per-NODE, not per-Pod.** Two Pods on the *same* node can share an RWO volume; two Pods
> on *different* nodes cannot.
>
> ⭐ **This is the Session-10 Recreate-strategy constraint, explained.** AWS EBS and GCP Persistent
> Disk are RWO — a rolling update **deadlocks** because the old Pod still holds the volume on its
> node while the new Pod waits to attach. That's why RWO workloads use `strategy: Recreate`.
>
> **RWX** needs a networked filesystem (NFS, AWS EFS, Azure Files) — normal block storage can't do it.

---

## ⚙️ StorageClass & Dynamic Provisioning

### The problem with manual PVs
> Suppose **100 developers** need storage:
```text
Developer → creates PVC → ⭐ Admin manually creates a PV
```
> **This becomes difficult to manage.**

### The solution
```text
PVC
 ▼
StorageClass
 ▼
Provisioner
 ▼
PV          ⭐ created AUTOMATICALLY when the PVC needs it
```

```bash
kubectl get storageclass
```
```text
NAME                 PROVISIONER
standard (default)   k8s.io/minikube-hostpath
```
```bash
kubectl describe storageclass standard   # provisioner, reclaim policy, volume binding mode
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard      # ⭐ name a StorageClass instead of a PV
  resources:
    requests:
      storage: 500Mi
```

```bash
kubectl apply -f pvc.yaml
kubectl get pvc
```
```text
NAME          STATUS   VOLUME
dynamic-pvc   Bound    pvc-xxxxxxxx      ⭐ a PV we never created
```
```bash
kubectl get pv      # ⭐ a PV was dynamically created for us
```

> ⭐⭐ **We did not manually create a PV. That's dynamic provisioning.**

### Default StorageClass
> A cluster can have a **default** StorageClass (shown as `standard (default)`).
> ⭐ **When a PVC does not specify `storageClassName`, Kubernetes can use the default** — which is
> exactly why the `student-pvc` earlier bound without naming one.

### Storage cheat sheet
| Object | Role |
|---|---|
| ⭐ **PV** | Storage **available** |
| ⭐ **PVC** | Storage **request** |
| ⭐ **StorageClass** | Helps create storage **dynamically** |

---

## 📈 HPA — Horizontal Pod Autoscaler

### Why
> Your app has **1 Pod**. Normal traffic → CPU 20%. Traffic spike → **CPU 90%**. You need more Pods.
>
> Instead of manually running `kubectl scale deployment hpa-demo --replicas=5`,
> ⭐ **HPA changes the replica count automatically.**

### Horizontal, not vertical ⭐
```text
Before:            After scaling:
  Pod 1              Pod 1   Pod 2   Pod 3   Pod 4
```
> ⭐ **HPA does NOT make the existing Pod bigger** — that would be *vertical* scaling (VPA).
> *(Session 1's vertical-vs-horizontal distinction, now automated.)*

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hpa-demo
spec:
  scaleTargetRef:               # ⭐ which workload to scale
    apiVersion: apps/v1
    kind: Deployment
    name: hpa-demo
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
```

| Field | Meaning |
|---|---|
| ⭐ **`scaleTargetRef`** | Which workload should HPA scale? |
| **`minReplicas`** | Minimum number of Pods |
| **`maxReplicas`** | Maximum number of Pods |
| **`metrics`** | What should HPA monitor? |

### ⭐⭐ CPU requests are mandatory
```yaml
resources:
  requests:
    cpu: 100m
```
> ⭐ **CPU requests are what utilization is calculated *against*:**
> ```
> CPU request = 100m
> CPU usage   =  50m
> Utilization = 50%       ⭐ percentage OF THE REQUEST, not of the node
> ```
> **Without a CPU request, HPA has no denominator and cannot scale at all** — it reports
> `<unknown>/50%`.

```bash
kubectl apply -f hpa.yaml
kubectl get hpa
```
```text
NAME       TARGETS   MINPODS   MAXPODS   REPLICAS
hpa-demo   0%/50%    1         5         1
```

### The HPA flow
```text
Application
     ▼
 CPU usage
     ▼
⭐ Metrics Server
     ▼
    HPA
     ▼
 Deployment
     ▼
More / fewer Pods
```

### The three autoscalers — don't confuse them ⭐
> ⚠️ *Only HPA is in the syllabus, but these three get mixed up constantly in interviews.*

| | Scales | Direction | Note |
|---|---|---|---|
| ⭐ **HPA** (Horizontal Pod Autoscaler) | **Number of Pods** | out / in | What this session covers |
| **VPA** (Vertical Pod Autoscaler) | ⭐ **CPU/memory *requests* of each Pod** | up / down | ⭐ **Must restart the Pod to apply** — and **conflicts with HPA on the same metric** |
| **Cluster Autoscaler** | ⭐ **Number of NODES** | out / in | Adds machines when Pods are **unschedulable (Pending)**; cloud-only |

```
   Traffic spike
        ▼
   ⭐ HPA adds Pods  ──▶  no room on any node?  ──▶  Pods go Pending
                                                         ▼
                                            ⭐ Cluster Autoscaler adds a NODE
                                                         ▼
                                                 Pods get scheduled
```
> ⭐ **HPA and Cluster Autoscaler are partners, not alternatives** — HPA creates the Pending Pods
> that make the Cluster Autoscaler add capacity. ⭐ **Never run HPA and VPA on the same CPU metric**;
> they fight each other.

### Scaling on more than CPU
`autoscaling/v2` also supports **memory**, **custom** metrics (from Prometheus via an adapter) and
**external** metrics (e.g. SQS queue depth) — and a `behavior:` block to tune scale-up/down speed:
```yaml
  metrics:
    - type: Resource
      resource:
        name: memory
        target: { type: Utilization, averageUtilization: 70 }
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300    # ⭐ the default 5-min anti-thrash window
```
> ⭐ **Queue depth is often the better signal than CPU** for worker pools — CPU lags, the backlog
> doesn't.

---

## 📊 Metrics Server

> ⭐ **HPA needs metrics. No Metrics Server, no autoscaling.**

```bash
kubectl top nodes
kubectl top pods
```
If you get:
```text
Metrics API not available
```
then it isn't installed:
```bash
minikube addons enable metrics-server
kubectl get pods -n kube-system | grep metrics-server
kubectl top pods                       # ⭐ try again
```

> ⭐ **`kubectl top` is the test.** If it fails, HPA will sit at `<unknown>/50%` forever.

---

## 🔥 Generating Load

```bash
kubectl run load-generator \
  --image=busybox:1.36 \
  --restart=Never \
  -- /bin/sh -c \
  "while true; do wget -q -O- http://hpa-demo-service; done"

kubectl get hpa -w       # ⭐ watch TARGETS climb and REPLICAS increase
kubectl get pods -w
```

Stop it:
```bash
kubectl delete pod load-generator
kubectl get hpa -w       # ⭐ replicas decrease after a cool-down
```

> ⭐ **Scale-up is fast; scale-down is deliberately slow** (a ~5-minute stabilisation window by
> default) to avoid *thrashing* — flapping replica counts on brief traffic dips.

---

## 🩺 Probes

> **A Pod can be `Running` but the application inside it may not actually be working.**
> ```
> Pod = Running
> Application = Broken
> ```
> ⭐ **Kubernetes needs a way to check the application.** That's what probes are for.

---

## 🔍 The Three Probes

### Liveness — *"Are you still alive?"*
> If the liveness check keeps failing, ⭐ **Kubernetes restarts the container.**
```yaml
livenessProbe:
  httpGet:
    path: /
    port: 80
```

### Readiness — *"Are you ready to receive traffic?"*
```text
Readiness fails
      ▼
Pod stays running
      ▼
Pod becomes NotReady
      ▼
⭐ Service should not send normal traffic to it
```
> ⭐⭐ **A readiness failure does NOT restart the container.**
> *(This is the Session-11 Endpoints mechanism: a NotReady Pod is removed from the Service's
> endpoint list.)*

### Startup — *"Has the application finished starting?"*
> Useful for applications that take a long time to start:
```text
Java application
      ├── starting...
      ├── starting...
      ├── starting...
      ▼
Application ready
```
> ⭐⭐ **Without a startup probe, an aggressive liveness probe could restart the application before it
> has finished starting** — an infinite restart loop where the app never gets the chance to boot.

### ⭐ The easy way to remember
```text
STARTUP    └── "Have you started?"
READINESS  └── "Can I send users to you?"
LIVENESS   └── "Are you still alive?"
```

### The comparison table
| Probe | Main question | What happens when it fails |
|---|---|---|
| **Startup** | Has the app started? | Container can be **restarted** |
| ⭐ **Readiness** | Can it receive traffic? | ⭐ **Pod becomes `NotReady`** (no restart) |
| **Liveness** | Is it still healthy? | Container can be **restarted** |

> ⭐⭐ **The single most important thing: `Readiness failure ≠ Container restart`.**

### All three together (`05-probes/startup.yaml`)
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: startup-demo
spec:
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
      startupProbe:              # ⭐ runs FIRST; the others are suspended until it passes
        httpGet: { path: /, port: 80 }
        failureThreshold: 30
        periodSeconds: 2         # ⭐ 30 × 2s = 60 seconds of grace to boot
      livenessProbe:
        httpGet: { path: /, port: 80 }
        periodSeconds: 5
      readinessProbe:
        httpGet: { path: /, port: 80 }
        periodSeconds: 5
```
> ⭐ **`failureThreshold × periodSeconds` is your startup budget.** Once the startup probe succeeds
> once, it never runs again and liveness/readiness take over.

### Probe types
> Kubernetes supports **HTTP**, **TCP**, **Exec**, and **gRPC**.
> *(The examples use HTTP because it's easiest to understand; Session 10's lifecycle lab used `exec`
> with `test -f /tmp/healthy`.)*

---

## ⚙️ Probe Configuration

```yaml
livenessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3
```

| Field | Meaning |
|---|---|
| **`initialDelaySeconds`** | How long Kubernetes waits before starting the checks |
| **`periodSeconds`** | How often it performs the check |
| **`timeoutSeconds`** | How long it waits for a response |
| **`failureThreshold`** | How many **consecutive** failures before the probe is considered failed |

> ⭐ **Time to restart = `initialDelaySeconds` + (`failureThreshold` × `periodSeconds`)**
> — above: 5 + (3 × 5) = **20 seconds** before a restart.
>
> ⭐ **Tune liveness conservatively.** Too aggressive and you restart a healthy-but-slow app,
> turning a latency blip into an outage.

---

## 💣 Breaking Probes Deliberately

### Break readiness
Change `path: /` to `path: /wrong-path`, reapply, then:
```bash
kubectl get pod readiness-demo
```
```text
NAME             READY   STATUS
readiness-demo   0/1     Running      ⭐ Running, but NOT ready
```
> ⭐ **The app is running but failing the readiness check** — so the Service won't route to it.
> This is Session 10's `Running != Ready` made concrete.

### Break liveness
Change the liveness path to `/wrong-path`, reapply, then:
```bash
kubectl get pod liveness-demo -w
kubectl describe pod liveness-demo
```
> ⭐ You'll see liveness probe **failures in Events** and the **RESTARTS counter climbing**.

### Debugging probes
```bash
kubectl describe pod <pod>                       # ⭐ probe failures appear in Events
kubectl logs <pod>
kubectl get events --sort-by=.lastTimestamp
kubectl exec -it <pod> -- sh
  wget -qO- http://localhost:80/                 # ⭐ test the endpoint from INSIDE the container
```
> ⭐ **That last step separates two very different failures:** if it works inside but the probe
> fails, the problem is the **probe config** (wrong path/port). If it fails inside too, the problem
> is the **app**.

---

## 🏗️ Mini Project — Production-Ready Web App

> The capstone combines **all three pillars** of this session:
> 1. ⭐ **State Persistence** — a PVC so `/data` outlives Pod deletions
> 2. ⭐ **Elastic Scaling** — an HPA scaling on CPU between **2 and 5** replicas
> 3. ⭐ **Health Diagnostics** — **Startup, Readiness and Liveness** probes together

```text
                       [ Service: web-service ]
                                  │ (Port 80)
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
      [ Pod: web-app-1 ]    [ Pod: web-app-2 ]    [ Pod: web-app-N ]
      ├─ Startup Probe      ├─ Startup Probe      ├─ Startup Probe
      ├─ Readiness Probe    ├─ Readiness Probe    ├─ Readiness Probe
      ├─ Liveness Probe     ├─ Liveness Probe     ├─ Liveness Probe
      ├─ CPU Requests       ├─ CPU Requests       ├─ CPU Requests
      └──────────┬──────────┴──────────┬──────────┘
                 │                     │
                 ▼                     │
   [ HPA: web-app-hpa (50% CPU) ] ◀────┘
                 ▲
                 │ pulls metrics
         [ Metrics Server ]

Pod
 └── VolumeMount: /data
       └── PVC: web-data (500Mi, ReadWriteOnce)
             └── StorageClass: standard (k8s.io/minikube-hostpath)
                   └── Physical/Host Persistent Storage
```

### Structure
```text
mini-project/
├── namespace.yaml       # production-webapp
├── pvc.yaml             # 500Mi ReadWriteOnce
├── deployment.yaml      # 2 replicas, probes, volume mounts, resource limits
├── service.yaml         # ClusterIP on port 80
└── hpa.yaml             # min 2, max 5, target 50% CPU
```

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: production-webapp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2          # ⭐ min 2, not 1 — survive a single pod failure
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
```

### Deploy
```bash
kubectl apply -f namespace.yaml
kubectl apply -f pvc.yaml     && kubectl get pvc  -n production-webapp
kubectl apply -f deployment.yaml -f service.yaml
kubectl get pods -n production-webapp
kubectl apply -f hpa.yaml     && kubectl get hpa  -n production-webapp
```
```text
NAME       STATUS   VOLUME                     CAPACITY   ACCESS MODES   STORAGECLASS
web-data   Bound    pvc-4b123456-789a-...      500Mi      RWO            standard

NAME          REFERENCE            TARGETS   MINPODS   MAXPODS   REPLICAS
web-app-hpa   Deployment/web-app   0%/50%    2         5         2
```

### ⭐ Task 1 — prove storage persistence
```bash
POD_NAME=$(kubectl get pods -n production-webapp -l app=web-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n production-webapp "$POD_NAME" -- sh -c 'echo "Student: Jane Doe" > /data/student.txt'
kubectl exec -n production-webapp "$POD_NAME" -- cat /data/student.txt     # → Student: Jane Doe

kubectl delete pod -n production-webapp "$POD_NAME"                        # ⭐ kill it

NEW_POD=$(kubectl get pods -n production-webapp -l app=web-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n production-webapp "$NEW_POD" -- cat /data/student.txt
```
```text
Student: Jane Doe
```
> ⭐ **The Pod was terminated and rescheduled, but the data remained completely intact on the
> PersistentVolume.**

### Task 2 — service verification
```bash
kubectl port-forward -n production-webapp svc/web-service 8080:80
curl http://localhost:8080
```
> ⭐ **`kubectl port-forward` is the fourth way to reach a Service** (after NodePort, LoadBalancer
> and Ingress) — local-only, perfect for debugging, no cluster changes required.

### Prerequisites
- Minikube or Docker Desktop Kubernetes running
- `kubectl` configured
- ⭐ **Metrics Server enabled** (`minikube addons enable metrics-server`)

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Volume** | Gives a container storage outside its own filesystem |
| ⭐ **emptyDir** | Temporary; **lifetime tied to the Pod** (survives container restarts, not Pod deletion) |
| **hostPath** | Mounts a **node** directory; learning/testing only, node-bound |
| ⭐ **PersistentVolume (PV)** | Storage **available** in the cluster |
| ⭐ **PersistentVolumeClaim (PVC)** | A **request** for storage; the Pod references the **claim** |
| **Bound** | The PVC has been matched to a suitable PV |
| **Reclaim policy** | `Retain` (keep data) · `Delete` (destroy it) |
| ⭐ **RWO / ROX / RWX / RWOP** | One **node** RW · many read-only · many RW · single **Pod** RW |
| ⭐ **RWO is per-node** | Why EBS/PD workloads need `strategy: Recreate` (Session 10) |
| ⭐ **StorageClass** | Enables **dynamic provisioning** — the PV is created automatically |
| **Default StorageClass** | Used when a PVC omits `storageClassName` |
| ⭐ **HPA** | Automatically changes the **replica count** (horizontal, never bigger pods) |
| ⭐ **CPU requests** | ⭐⭐ **Mandatory for HPA** — utilization is a % of the *request* |
| **`scaleTargetRef`** | Which Deployment the HPA scales |
| ⭐ **Metrics Server** | Supplies the metrics; `kubectl top` is the test that it works |
| **Thrashing** | Flapping replica counts; prevented by a slow scale-down window |
| ⭐ **HPA vs VPA vs Cluster Autoscaler** | More **Pods** / bigger **Pods** / more **Nodes** |
| ⭐ **HPA + Cluster Autoscaler** | Partners — HPA creates Pending Pods, CA adds nodes for them |
| ⭐ **Never HPA + VPA on the same metric** | They fight each other |
| ⭐ **Liveness** | *"Are you alive?"* → failure **restarts** the container |
| ⭐ **Readiness** | *"Can you receive traffic?"* → failure makes the Pod **NotReady** (no restart) |
| ⭐ **Startup** | *"Have you started?"* → protects slow-booting apps from liveness |
| **Probe types** | HTTP · TCP · Exec · gRPC |
| **`failureThreshold × periodSeconds`** | ⭐ Your startup budget / time-to-restart |
| **`kubectl port-forward`** | Local-only access to a Service for debugging |

---

## 🎯 Session Takeaways

1. ⭐ **Container filesystems are disposable — and in Kubernetes so are Pods.** Volumes are how data
   survives.
2. ⭐ **`emptyDir` lives and dies with the Pod** (though it survives container restarts) — good for
   scratch space and sharing files between containers in one Pod.
3. **`hostPath` ties data to one node** — fine for learning, wrong for production.
4. ⭐⭐ **PV = supply, PVC = demand, and the Pod always references the claim.** Their lifecycle is
   **independent of the Pod**, which is what makes the data survive.
5. ⭐ **A `Pending` PVC means nothing matched** — wrong size, wrong access mode, or no default
   StorageClass. `describe pvc` tells you.
6. ⭐⭐ **RWO is per-NODE, not per-Pod** — which is precisely why RWO workloads must use the
   **Recreate** strategy from Session 10. RWX requires a networked filesystem.
7. ⭐ **StorageClass turns manual PV creation into dynamic provisioning** — the PV appears when the
   PVC asks for it.
8. ⭐ **HPA scales replicas out, never up.** It's Session 1's horizontal scaling, automated.
9. ⭐⭐ **No CPU `requests` ⇒ no HPA.** Utilization is a percentage **of the request**, so without one
   there's no denominator and the target shows `<unknown>`.
10. ⭐ **No Metrics Server ⇒ no HPA.** `kubectl top pods` is the one-command check.
11. ⭐⭐ **Readiness failure ≠ container restart.** Liveness restarts; readiness only removes the Pod
    from Service endpoints. This is the most-tested probe fact there is.
12. ⭐ **Startup probes exist to stop liveness from killing a slow-booting app** before it ever
    finishes starting.
13. ⭐ **Debug a failing probe from inside the container** (`kubectl exec … wget localhost`) — it
    separates a bad probe config from a broken app.
14. ⭐ **The mini-project is the whole session in one Deployment:** PVC for state, HPA for elasticity,
    and all three probes for health.

---

## 🔗 References
- Volumes — https://kubernetes.io/docs/concepts/storage/volumes/
- Persistent Volumes — https://kubernetes.io/docs/concepts/storage/persistent-volumes/
- Storage Classes — https://kubernetes.io/docs/concepts/storage/storage-classes/
- Horizontal Pod Autoscaling — https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
- HPA Walkthrough — https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/
- Resource Metrics Pipeline — https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/
- Probes — https://kubernetes.io/docs/concepts/workloads/pods/probes/
- Configure Probes — https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Course repo — https://github.com/Nency-Ravaliya/devops-heros

---

## ➡️ Next
**Session 14 — Kubernetes Troubleshooting** *(not yet published in the course repo)*
