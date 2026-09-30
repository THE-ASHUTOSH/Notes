# Session 9 — Kubernetes Fundamentals ☸️

> **Topics:** Why Kubernetes? · Kubernetes Architecture · Control Plane & Worker Nodes ·
> API Server · Scheduler · Controller Manager · etcd · kubelet · kubectl
>
> 📁 Repo: `session9-k8s/` — contains **reference links only** (no lab files), so this session is
> built from the syllabus topics plus those linked resources.

---

## 📑 Table of Contents
1. [Why Kubernetes?](#-why-kubernetes)
2. [What Kubernetes Is (and Isn't)](#-what-kubernetes-is-and-isnt)
3. [Cluster Architecture](#-cluster-architecture)
4. [Control Plane Components](#-control-plane-components)
5. [Worker Node Components](#-worker-node-components)
6. [kubectl](#-kubectl)
7. [The Declarative Model](#-the-declarative-model--desired-vs-actual-state)
8. [What Happens When You Run `kubectl apply`](#-what-happens-when-you-run-kubectl-apply)
9. [Core Objects Preview](#-core-objects-preview)
10. [Namespaces](#-namespaces)
11. [RBAC — Who Can Do What](#-rbac--who-can-do-what)
12. [Local Clusters](#-local-clusters-for-learning)
13. [Key Terms Recap](#-key-terms-recap)

---

## 🎯 Why Kubernetes?

Session 8 ended with Docker Compose running a 3-tier app on **one machine**. That's where Compose
stops. Kubernetes starts where these questions begin:

| Question Compose can't answer | Kubernetes answer |
|---|---|
| A container crashed at 3 AM — who restarts it? | ⭐ **Self-healing** — the controller restarts it automatically |
| Traffic tripled — who adds more containers? | ⭐ **Autoscaling** (HPA — Session 13) |
| One machine isn't enough — how do I use 50? | ⭐ **Scheduling across a cluster of nodes** |
| A whole node died — what happens to its containers? | ⭐ **Rescheduled onto healthy nodes** |
| How do I deploy a new version with **zero downtime**? | ⭐ **Rolling updates + rollbacks** (Session 10) |
| How do containers find each other across machines? | ⭐ **Services + cluster DNS** (Session 11) |
| Where do passwords and config live? | ⭐ **ConfigMaps & Secrets** (Session 12) |
| How does data survive a pod moving to another node? | ⭐ **PV / PVC / StorageClass** (Session 13) |

> ⭐ **The one-line definition:** Kubernetes is a **container orchestrator** — it decides *where*
> containers run, keeps the right *number* of them alive, and gives them stable *networking* and
> *storage*.

**Why it's called K8s:** `K` + 8 letters + `s`. Originally from Google's internal **Borg**, donated
to the **CNCF** in 2014.

---

## 🧭 What Kubernetes Is (and Isn't)

| Kubernetes **does** | Kubernetes does **NOT** |
|---|---|
| Schedule containers onto machines | Build container images (that's Docker/BuildKit — Session 7) |
| Restart / reschedule failed containers | Provide a CI/CD pipeline (that's GitHub Actions) |
| Scale replicas up and down | Provide application-level services (databases, queues) |
| Service discovery + load balancing | Dictate your application architecture |
| Roll out and roll back releases | Do logging/monitoring itself (you add Prometheus/Loki) |
| Manage config and secrets | Replace your cloud provider |

> ⭐ **K8s runs containers — it doesn't make them.** The Docker image you built in Session 7 is
> exactly what a Pod runs here.

---

## 🏗️ Cluster Architecture

A **cluster** = **one control plane** (the brain) + **many worker nodes** (the muscle).

```
                    ┌──────────────────────────────────────────────────┐
                    │              CONTROL PLANE (master)              │
   kubectl ────────▶│  ┌────────────┐                                  │
   (you)            │  │ API SERVER │◀── the ONLY thing that talks     │
                    │  └─────┬──────┘    to etcd; everything goes      │
                    │        │           through here ⭐                │
                    │  ┌─────┴──────┬──────────────┬────────────────┐  │
                    │  │            │              │                │  │
                    │  ▼            ▼              ▼                ▼  │
                    │ etcd     SCHEDULER   CONTROLLER MGR    CLOUD CTRL │
                    │ (state)  (where?)    (reconcile)       (cloud API)│
                    └──────────────────────┬───────────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              ▼                            ▼                            ▼
    ┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
    │   WORKER NODE 1   │       │   WORKER NODE 2   │       │   WORKER NODE 3   │
    │  ┌─────────────┐  │       │  ┌─────────────┐  │       │  ┌─────────────┐  │
    │  │   kubelet   │  │       │  │   kubelet   │  │       │  │   kubelet   │  │
    │  ├─────────────┤  │       │  ├─────────────┤  │       │  ├─────────────┤  │
    │  │ kube-proxy  │  │       │  │ kube-proxy  │  │       │  │ kube-proxy  │  │
    │  ├─────────────┤  │       │  ├─────────────┤  │       │  ├─────────────┤  │
    │  │  container  │  │       │  │  container  │  │       │  │  container  │  │
    │  │   runtime   │  │       │  │   runtime   │  │       │  │   runtime   │  │
    │  ├─────────────┤  │       │  ├─────────────┤  │       │  ├─────────────┤  │
    │  │ [Pod] [Pod] │  │       │  │ [Pod] [Pod] │  │       │  │ [Pod] [Pod] │  │
    │  └─────────────┘  │       │  └─────────────┘  │       │  └─────────────┘  │
    └───────────────────┘       └───────────────────┘       └───────────────────┘
```

---

## 🧠 Control Plane Components

### 1. `kube-apiserver` — the front door ⭐
> **The only component that reads and writes `etcd`. Every other component — including `kubectl`,
> the scheduler, and every kubelet — talks to the cluster *through* the API server.**

| Responsibility | Detail |
|---|---|
| **REST API** | Exposes the Kubernetes API over HTTPS (port **6443**) |
| **Authentication** | Who are you? (certs, tokens, OIDC) |
| **Authorization** | Are you allowed? (**RBAC**) |
| **Admission control** | Should this be modified/rejected? (quotas, policies, defaulting) |
| **Validation** | Is this YAML actually valid? |
| **Persistence** | Writes the accepted object to **etcd** |

> ⭐ **It's a hub, not a controller.** The API server never *decides* anything about workloads — it
> just validates, stores, and notifies. All the deciding happens in controllers watching it.

### 2. `etcd` — the cluster's only database ⭐
> **A distributed, consistent key-value store holding the entire cluster state.**

- ⭐ **If etcd is lost, the cluster is lost.** It is *the* single source of truth.
- Uses the **Raft** consensus algorithm → runs in **odd numbers** (3 or 5) for a clear majority.
- Stores **every** object: Pods, Deployments, Services, Secrets, ConfigMaps, RBAC rules.
- ⭐ **Back it up.** `etcdctl snapshot save` is the single most important cluster backup you own.
- Components **watch** etcd (via the API server) — this watch mechanism is what makes Kubernetes
  event-driven rather than polling.

### 3. `kube-scheduler` — *where* should this Pod run? ⭐
> Watches for Pods with **no `nodeName` assigned** and picks a node for each one.

It runs a two-phase algorithm:
```
1. FILTERING  (predicates) — which nodes COULD run this Pod?
     • enough CPU/memory for the Pod's requests?
     • node selector / affinity rules satisfied?
     • taints tolerated?
     • required ports free? volumes attachable?

2. SCORING    (priorities) — which of those is BEST?
     • least-utilised node
     • spread across zones / avoid co-locating replicas
     • image already cached on the node

  → highest score wins → writes nodeName onto the Pod object
```
> ⭐ **The scheduler doesn't start anything.** It only *writes a decision* (`spec.nodeName`) back to
> the API server. The kubelet on that node notices and does the actual work.
>
> ⭐ This is why **CPU/memory `requests` matter so much** — they are the scheduler's only input for
> capacity. A Pod requesting more than any node has stays **Pending** forever (Session 10's
> `02-pending.yaml` demonstrates exactly this).

### 4. `kube-controller-manager` — the reconciliation engine ⭐
> A single binary running **many controllers**, each an infinite loop:

```
        ┌─────────────────────────────────────────┐
        │  observe ACTUAL state (via API server)  │
        │              ↓                          │
        │  compare with DESIRED state (etcd)      │
        │              ↓                          │
        │  act to close the gap                   │
        └──────────────┬──────────────────────────┘
                       └────── repeat forever ⭐
```

| Controller | Job |
|---|---|
| **Deployment controller** | Creates/updates ReplicaSets for rollouts |
| **ReplicaSet controller** | Keeps *N* pod replicas alive |
| **Node controller** | Notices unreachable nodes, evicts their pods |
| **Endpoints / EndpointSlice controller** | ⭐ Keeps the list of healthy Pod IPs behind each Service |
| **Job / CronJob controller** | Runs batch and scheduled work |
| **ServiceAccount & Token controllers** | Identity for pods |

### 5. `cloud-controller-manager` — cloud integration
Talks to AWS/GCP/Azure APIs: provisions **LoadBalancers** (Session 11), attaches **volumes**
(Session 13), and manages node lifecycle. Absent on bare-metal/Minikube.

---

## ⚙️ Worker Node Components

### 1. `kubelet` — the node's agent ⭐
> The **only** component that actually starts and stops containers on a machine.

- Watches the API server for Pods assigned to **its** node.
- Tells the **container runtime** to pull images and run containers.
- ⭐ **Runs the probes** (liveness / readiness / startup — Session 13) and restarts containers that
  fail liveness.
- Reports node and Pod status back to the API server (this is how `kubectl get pods` knows anything).
- ⭐ **It manages Pods, not arbitrary containers** — a container you start with `docker run` on a node
  is invisible to Kubernetes.

### 2. `kube-proxy` — the networking plumber ⭐
> Implements **Service** networking on every node by programming the Linux kernel.

| Mode | How |
|---|---|
| **iptables** (default) | Injects netfilter DNAT rules; random pod selection |
| ⭐ **IPVS** (large clusters) | Kernel hash tables → **O(1)** with 10,000+ services, plus real LB algorithms |

> ⭐ **Traffic never flows *through* kube-proxy.** It writes the rules; the **kernel** rewrites the
> packets. Detailed in Session 11.

### 3. Container runtime
Runs the containers, via the **CRI** (Container Runtime Interface):
**containerd** (most common) · **CRI-O** · *(dockershim was removed in v1.24)*

> ⭐ **Session 6 callback:** Docker-built images still run perfectly — they follow the **OCI**
> standard. "Kubernetes dropped Docker" only means it dropped the *shim*, not your images.

---

## 💻 kubectl

> The CLI that turns your commands into **HTTP calls to the API server**. Config lives in
> `~/.kube/config`.

```bash
# --- cluster info ---
kubectl version --short
kubectl cluster-info
kubectl get nodes -o wide
kubectl get componentstatuses          # control plane health (deprecated but still handy)

# --- the universal verbs ---
kubectl get <type> [name]              # list / show
kubectl describe <type> <name>         # ⭐ details + EVENTS (first debugging stop)
kubectl logs <pod>                     # container logs
kubectl exec -it <pod> -- sh           # shell inside a container
kubectl apply -f file.yaml             # ⭐ declarative create-or-update
kubectl delete -f file.yaml
kubectl edit <type> <name>             # open live object in $EDITOR

# --- useful flags ---
kubectl get pods -A                    # ⭐ all namespaces
kubectl get pods -o wide               # + node and pod IP
kubectl get pods -w                    # ⭐ watch live changes
kubectl get pods --show-labels
kubectl get pods -l app=nginx          # ⭐ filter by label
kubectl get pod <p> -o yaml            # full object as stored
kubectl get pod <p> -o jsonpath='{.status.phase}'
kubectl api-resources                  # every object type + short name
kubectl explain pod.spec.containers    # ⭐ built-in schema docs
```

### Imperative vs declarative
| | Imperative | ⭐ Declarative |
|---|---|---|
| Command | `kubectl create deployment nginx --image=nginx` | `kubectl apply -f deployment.yaml` |
| Source of truth | Your shell history | ⭐ **A file in Git** |
| Repeatable | No | ⭐ Yes |
| Use for | Quick experiments, generating YAML | ⭐ **Everything real** |

> ⭐ **The generator trick** — get a YAML skeleton without memorising it:
> ```bash
> kubectl create deployment web --image=nginx --dry-run=client -o yaml > deploy.yaml
> ```

---

## 🔄 The Declarative Model — Desired vs Actual State

> ⭐⭐ **This is the single most important idea in Kubernetes.**
>
> **You never tell Kubernetes what to *do*. You tell it what you *want*, and controllers
> continuously work to make reality match.**

```
   You:  "I want 3 replicas of nginx:1.25"     ← DESIRED STATE (in etcd)
   K8s:  ...counts 3 running. Nothing to do.   ← ACTUAL STATE matches

   [a node dies, 1 pod lost]

   K8s:  ...counts 2. Desired is 3. Create 1.  ⭐ self-healing, no human involved
```

**Consequences worth internalising:**
- **Self-healing is free** — it's just the reconciliation loop doing its job.
- ⭐ **Deleting a Pod managed by a Deployment does nothing useful** — the controller recreates it.
  To actually remove it, delete the *Deployment*.
- ⭐ **`kubectl apply` is idempotent** — running it ten times equals running it once.
- This is exactly why **GitOps** (Session 1) works: point a controller at a Git repo and the same
  loop reconciles your whole cluster.

---

## 🔁 What Happens When You Run `kubectl apply`

Worth tracing once — it explains almost every error message you'll ever see.

```
 1. kubectl reads the YAML, converts to JSON, POSTs to the API server (:6443)
 2. API SERVER:  authenticate → authorize (RBAC) → admission control → validate
 3. API SERVER:  writes the Deployment object to ⭐ etcd, replies "201 created"
                 (kubectl returns here — your prompt comes back ⭐ before anything runs)
 4. DEPLOYMENT CONTROLLER (watching):   sees new Deployment → creates a ReplicaSet
 5. REPLICASET CONTROLLER (watching):   sees RS wants 3, has 0 → creates 3 Pod objects
                                        (⭐ Pods exist in etcd but have no node → Pending)
 6. SCHEDULER (watching):               filters + scores nodes → writes spec.nodeName on each Pod
 7. KUBELET on that node (watching):    sees a Pod assigned to it
                                        → tells containerd to pull the image
                                        → starts the container
                                        → runs probes, reports status back
 8. ENDPOINTS CONTROLLER:               once Pods pass readiness, adds their IPs to the Service
 9. KUBE-PROXY on every node:           programs iptables/IPVS so the Service IP reaches them
```

> ⭐ **Every component communicates only with the API server** — never directly with each other.
> That single rule is what makes the architecture extensible: add a new controller, and it just
> watches the same API.

---

## 📦 Core Objects Preview

| Object | Purpose | Session |
|---|---|---|
| ⭐ **Pod** | Smallest deployable unit — one or more containers sharing network + storage | 10 |
| **ReplicaSet** | Keeps N identical Pods running | 10 |
| ⭐ **Deployment** | Manages ReplicaSets → rolling updates & rollbacks | 10 |
| **StatefulSet** | Stable identity + per-pod storage (databases, Kafka) | 10 |
| **DaemonSet** | One Pod on **every** node (log/metric agents) | 10 |
| **Job / CronJob** | Run-to-completion and scheduled tasks | — |
| ⭐ **Service** | Stable IP + DNS + load balancing over Pods | 11 |
| **Ingress** | Layer-7 HTTP routing into the cluster | 12 |
| **ConfigMap / Secret** | Non-secret / secret configuration | 12 |
| **PV / PVC / StorageClass** | Persistent storage | 13 |
| **HPA** | Autoscale replica count | 13 |
| **Namespace** | Virtual cluster for isolation | this session |

### Every object has the same four top-level fields ⭐
```yaml
apiVersion: apps/v1     # which API group + version
kind: Deployment        # what type of object
metadata:               # name, namespace, labels, annotations
  name: myapp
spec:                   # ⭐ DESIRED state — you write this
  ...
status:                 # ⭐ ACTUAL state — Kubernetes writes this, never you
```

---

## 🗂️ Namespaces

> **Virtual clusters inside one physical cluster** — for isolating teams, environments, or apps.

```bash
kubectl get namespaces
kubectl create namespace dev
kubectl get pods -n dev
kubectl config set-context --current --namespace=dev   # ⭐ stop typing -n
```

**Built-in namespaces:**
| Namespace | Contents |
|---|---|
| `default` | Where your objects go if you don't say otherwise |
| ⭐ `kube-system` | **CoreDNS, kube-proxy, metrics-server** — the cluster's own components |
| `kube-public` | World-readable cluster info |
| `kube-node-lease` | Node heartbeats |

> ⭐ **Namespaces affect DNS.** A Service in another namespace needs
> `service.namespace` — the #1 cause of "it worked in dev" bugs (Session 11).
>
> ⭐ **Not everything is namespaced:** Nodes, PersistentVolumes, StorageClasses and Namespaces
> themselves are **cluster-scoped**. Check with `kubectl api-resources --namespaced=false`.

---

## 🔐 RBAC — Who Can Do What

> ⚠️ *Not in the repo, but **Session 12 depends on it**: "Base64 is encoding, not encryption — use
> RBAC to restrict who can run `kubectl get secret`." Here's what that actually means.*

Recall the API server's request pipeline: **authenticate → authorize → admission → validate**.
**RBAC (Role-Based Access Control) is the authorize step.**

### Four objects, two pairs ⭐
| Object | Scope | Answers |
|---|---|---|
| **Role** | ⭐ One namespace | *What actions are allowed?* |
| **ClusterRole** | ⭐ Whole cluster | Same, but cluster-wide (or for cluster-scoped resources like Nodes, PVs) |
| **RoleBinding** | One namespace | *Who gets that Role?* |
| **ClusterRoleBinding** | Whole cluster | *Who gets that ClusterRole, everywhere?* |

```
   Subject  ──(RoleBinding)──▶  Role  ──▶  [verbs] on [resources]
   (user / group / ServiceAccount)
```

### The Session-12 example, made concrete
```yaml
# A Role that can read pods but NOT secrets
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
  - apiGroups: [""]                 # "" = the core API group
    resources: ["pods"]             # ⭐ note: "secrets" is deliberately absent
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
  - kind: ServiceAccount
    name: my-app
    namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**Common verbs:** `get` · `list` · `watch` · `create` · `update` · `patch` · `delete`

> ⭐ **RBAC is additive and deny-by-default.** There is no "deny" rule — you simply never grant the
> permission. If no binding allows an action, it's forbidden.

### Check permissions before you get paged ⭐
```bash
kubectl auth can-i get secrets                              # ⭐ as yourself
kubectl auth can-i get secrets --as=system:serviceaccount:default:my-app
kubectl auth can-i --list                                   # everything you can do
kubectl get rolebindings,clusterrolebindings -A
```

> ⭐⭐ **`kubectl auth can-i` is the command that turns "I think it's locked down" into "I verified
> it's locked down."**

### ServiceAccounts — identity for Pods
> Every Pod runs as a **ServiceAccount** (the namespace's `default` one if you don't say otherwise),
> and its token is mounted into the container.

```yaml
spec:
  serviceAccountName: my-app
  automountServiceAccountToken: false    # ⭐ turn it off if the Pod never calls the API
```

> ⭐ **The practical rule:** the `default` ServiceAccount should have **no permissions**. Give each
> workload its own ServiceAccount with only the verbs it needs — otherwise a compromised Pod can
> read every Secret in the namespace, which is exactly the attack Session 12 warned about.

---

## 🖥️ Local Clusters (for learning)

| Tool | Note |
|---|---|
| ⭐ **Minikube** | Single-node VM/container cluster; used throughout Sessions 10–13 |
| **kind** | Kubernetes *in* Docker — fast, great for CI |
| **k3s / k3d** | Lightweight, production-capable |
| **Docker Desktop** | Built-in single-node cluster, one checkbox |

```bash
minikube start
minikube status
kubectl get nodes

minikube addons list
minikube addons enable ingress            # ⭐ needed in Session 12
minikube addons enable metrics-server     # ⭐ needed in Session 13 (HPA)

minikube ip                               # ⭐ the IP for NodePort/Ingress testing
minikube service <svc> --url
minikube dashboard
minikube delete
```

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Kubernetes / K8s** | Container orchestrator: schedules, heals, scales, networks containers |
| **Cluster** | One control plane + many worker nodes |
| **Node** | A machine (VM or physical) that runs Pods |
| ⭐ **kube-apiserver** | The front door — **the only component that touches etcd** |
| ⭐ **etcd** | Distributed key-value store holding **all** cluster state; back it up |
| ⭐ **kube-scheduler** | Picks a node per Pod (**filter → score**); only writes `nodeName` |
| ⭐ **controller-manager** | Runs the reconciliation loops (Deployment, ReplicaSet, Node, Endpoints…) |
| **cloud-controller-manager** | Provisions cloud LBs and volumes |
| ⭐ **kubelet** | Node agent — actually starts containers and **runs the probes** |
| ⭐ **kube-proxy** | Programs iptables/IPVS for Service routing (traffic doesn't flow through it) |
| **Container runtime** | containerd / CRI-O, via the **CRI**; runs **OCI** images |
| **kubectl** | CLI that makes HTTP calls to the API server |
| ⭐ **Desired vs actual state** | You declare desired; controllers reconcile reality to match |
| **Reconciliation loop** | observe → compare → act → repeat forever |
| **Namespace** | Virtual cluster for isolation; affects DNS names |
| **spec vs status** | ⭐ You write `spec`; Kubernetes writes `status` |
| ⭐ **RBAC** | The API server's **authorize** step — Role/ClusterRole (what) + Binding (who) |
| **Role vs ClusterRole** | Namespaced vs cluster-wide permissions |
| ⭐ **Additive, deny-by-default** | No "deny" rules exist — anything not granted is forbidden |
| ⭐ **`kubectl auth can-i`** | Verify permissions instead of assuming them |
| **ServiceAccount** | A Pod's identity; ⭐ give each workload its own, keep `default` powerless |

---

## 🎯 Session Takeaways

1. **Kubernetes starts where Compose stops** — multiple machines, self-healing, zero-downtime
   releases, autoscaling.
2. ⭐ **It orchestrates containers; it doesn't build them.** Your Session-7 Docker image is the input.
3. **Control plane = brain** (API server, etcd, scheduler, controller-manager);
   **worker nodes = muscle** (kubelet, kube-proxy, runtime).
4. ⭐ **Everything goes through the API server, and only it touches etcd.** No component talks
   directly to another — that's what makes K8s extensible.
5. ⭐ **etcd is the single source of truth. Losing it loses the cluster** — snapshot it.
6. ⭐ **The scheduler only decides and writes `nodeName`;** the **kubelet** does the actual starting.
   Resource **requests** are the scheduler's only capacity input.
7. ⭐⭐ **Declarative, not imperative: you declare desired state and controllers reconcile.**
   Self-healing is a free side effect — and deleting a managed Pod just gets it recreated.
8. **Every object has `apiVersion`, `kind`, `metadata`, `spec` (yours), `status` (Kubernetes').**
9. ⭐ **`kubectl describe` first, `kubectl logs` second** — the Events section answers most questions.
10. **Namespaces isolate, and they change DNS names** — a fact that bites in Session 11.

---

## 🔗 References
*(from `session9-k8s/Readme.md`)*
- Kubernetes Basics tutorial — https://kubernetes.io/docs/tutorials/kubernetes-basics/
- Minikube start — https://minikube.sigs.k8s.io/docs/start/
- Cluster architecture — https://kubernetes.io/docs/concepts/architecture/
- Instructor's Kubernetes repo — https://github.com/Nency-Ravaliya/Kubernetes
- Course repo — https://github.com/Nency-Ravaliya/devops-heros

---

## ➡️ Next
**[Session 10 — Pods, ReplicaSets & Deployments](./10_Kubernetes_Pods_ReplicaSets_and_Deployments.md)**
