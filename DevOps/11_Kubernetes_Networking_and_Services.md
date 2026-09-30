# Session 11 — Kubernetes Networking & Services 🌐

> **Topics:** Pod Networking · Kubernetes DNS · Service Discovery · ClusterIP · NodePort ·
> LoadBalancer · Service Selectors · `port` vs `targetPort`
>
> 📁 Repo: `session-11-kubernetes-services/` — `service.md` (the 5-service guide), `fqdn.md`
> (CoreDNS deep dive), and five hands-on labs (`01-clusterip` … `05-headless`).

---

## 📑 Table of Contents
1. [Pod Networking — the Kubernetes Network Model](#-pod-networking--the-kubernetes-network-model)
2. [Why Services Exist](#-why-services-exist)
3. [The 4 Ports You Must Never Confuse](#-the-4-ports-you-must-never-confuse)
4. [Master Comparison Table](#-master-comparison-table-all-5-types)
5. [ClusterIP](#1-clusterip--the-internal-phone-system)
6. [NodePort](#2-nodeport--the-building-gate-port)
7. [LoadBalancer](#3-loadbalancer--the-cloud-vip-entrance)
8. [ExternalName](#4-externalname--the-internal-speed-dial-alias)
9. [Headless Service](#5-headless-service--the-direct-calling-line)
10. [How Traffic Flows Under the Hood](#-how-traffic-flows-under-the-hood)
11. [Services Without Selectors](#-services-without-selectors)
12. [FQDN & CoreDNS](#-fqdn--coredns)
13. [Short Name vs Long Name](#-short-name-vs-long-name)
14. [resolv.conf and ndots:5](#-inside-a-pod-etcresolvconf)
15. [Testing DNS](#-testing-dns-in-your-cluster)
16. [Decision Tree](#-decision-tree-which-service-do-i-pick)
17. [Interview Q&A](#-interview-qa)
18. [Key Terms Recap](#-key-terms-recap)

---

## 🕸️ Pod Networking — the Kubernetes Network Model

> ⚠️ *The syllabus lists "Pod Networking", but the repo's `service.md` starts at Services. This
> section fills that gap — and everything after it depends on these four rules.*

### The four rules every Kubernetes cluster must satisfy ⭐⭐
```
1. ⭐ Every Pod gets its OWN unique IP address (cluster-wide).
2. ⭐ Every Pod can reach every other Pod DIRECTLY — WITHOUT NAT.
3. ⭐ Every Node can reach every Pod without NAT.
4. ⭐ The IP a Pod sees for itself is the SAME IP others use to reach it.
```

> ⭐⭐ **This is called the "flat network" or "IP-per-Pod" model, and it is the single biggest
> difference from Docker.**
>
> **Session 8 recap:** in Docker you published ports (`-p 8080:80`) because containers sat behind a
> NAT bridge. **In Kubernetes there is no port publishing between Pods** — Pod A simply talks to
> Pod B's IP on Pod B's real port. `hostPort` exists but is almost never used.

### The three networks in a cluster
| Network | Example CIDR | Who lives there | Routable outside? |
|---|---|---|---|
| **Node network** | `192.168.49.0/24` | The machines themselves | ✅ Real network |
| ⭐ **Pod network** | `10.244.0.0/16` | Every Pod | ❌ Cluster-internal (set by the CNI plugin) |
| ⭐ **Service network** | `10.96.0.0/12` | ClusterIPs | ❌ ⭐ **Purely virtual — exists only as iptables/IPVS rules** |

```
   ┌─ NODE 1 (192.168.49.2) ──────────┐   ┌─ NODE 2 (192.168.49.3) ──────────┐
   │  Pod A  10.244.1.5               │   │  Pod C  10.244.2.9               │
   │  Pod B  10.244.1.6               │   │  Pod D  10.244.2.10              │
   └──────────────┬───────────────────┘   └──────────────┬───────────────────┘
                  └────────── CNI overlay/routing ───────┘
   ⭐ Pod A reaches Pod C at 10.244.2.9 directly — no NAT, no port mapping, different node.
```

> ⭐ **Note the Service network doesn't appear in that diagram** — because no packet ever *arrives*
> at a ClusterIP. The kernel rewrites the destination to a Pod IP before the packet leaves the
> sending node. That's why `ping <ClusterIP>` usually fails even when the Service works perfectly.

### Four levels of communication
| From → To | Mechanism |
|---|---|
| **Container → Container** (same Pod) | ⭐ **`localhost`** — they share a network namespace |
| **Pod → Pod** | ⭐ Direct Pod IP, no NAT — but **IPs change**, so use a Service |
| **Pod → Service** | ClusterIP, resolved by CoreDNS, routed by kube-proxy |
| **External → Pod** | NodePort / LoadBalancer / Ingress |

### CNI — who actually implements this? ⭐
> Kubernetes **does not implement Pod networking itself.** It defines the rules and delegates to a
> **CNI (Container Network Interface) plugin**, which the kubelet calls whenever a Pod is created.

| Plugin | Note |
|---|---|
| **Flannel** | Simplest; VXLAN overlay. Good for learning |
| ⭐ **Calico** | Most common; native routing (no overlay) + ⭐ **NetworkPolicy support** |
| **Cilium** | eBPF-based; high performance, deep observability |
| **Weave Net**, **AWS VPC CNI** | Cloud/overlay variants — AWS VPC CNI gives Pods **real VPC IPs** |

> ⭐ **No CNI plugin installed ⇒ every Pod stays `Pending` / `ContainerCreating`** and nodes report
> `NotReady`. This is the classic "I built a cluster from scratch and nothing starts" failure.

### The `pause` container ⭐
Every Pod secretly runs an extra tiny container called **`pause`**. It does nothing but hold the
**network namespace** open, so your app containers can crash and restart **without the Pod losing
its IP**. That's why `docker ps` on a node shows twice as many containers as you expected.

### NetworkPolicy — the flat network's downside ⭐
> ⭐ **By default, the flat model means EVERY Pod can talk to EVERY other Pod in the cluster** —
> including across namespaces. That's convenient and **insecure**.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend
spec:
  podSelector:                      # ⭐ applies TO these pods
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:              # ⭐ only FROM these pods
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 5000
```

> ⭐ **Two gotchas:**
> 1. **NetworkPolicy is deny-by-default *once a Pod is selected*.** A Pod with no policy accepts
>    everything; the moment one policy selects it, only what's explicitly allowed gets through.
> 2. ⭐ **Policies are enforced by the CNI plugin, not Kubernetes.** Apply one on a cluster running
>    Flannel and it is silently ignored — the YAML applies successfully and does nothing.
>
> 💡 This is the Kubernetes equivalent of Session 8's **network segmentation** (`frontend_net` /
> `backend_net`) — same goal, declarative instead of topological.

---

## 🎯 Why Services Exist

> ⭐⭐ **"Pods come and go, but Services stay forever."**

### The pizza delivery analogy
> - **Delivery drivers (Pods)** come and go. A driver's bike breaks down and a new driver replaces
>   them **with a different phone number (Pod IP)**.
> - If customers called individual drivers directly, they'd constantly get dead numbers.
> - Instead the business sets up **one permanent 1-800 helpline (the Service)**. An internal
>   switchboard operator (**`kube-proxy`**) routes each call to whichever driver is available.

### The four problems Services solve
| Problem | Solution |
|---|---|
| ⭐ **Dynamic ephemeral IPs** | Pods are disposable; every restart changes the IP. A Service gives a **static IP and DNS name that never changes** |
| **Automatic load balancing** | Distributes requests across all healthy replicas matching the `selector` |
| ⭐ **Built-in service discovery** | CoreDNS creates a DNS record for every Service |
| ⭐ **Health-check awareness** | A Pod failing its **readiness probe** is pulled out of rotation automatically |

> ⭐ **That last row is the Session-10 link:** readiness probes don't just gate rollouts — they gate
> *traffic*, by controlling Service endpoints.

---

## 🔌 The 4 Ports You Must Never Confuse

```text
 Client (Browser / External User)
             |
             | Hits Node IP on:
             v
      [ nodePort: 30080 ]     <- Port on every Worker Node host (30000-32767)
             |
             v
      [ port: 80 ]            <- Port exposed by the Service itself (cluster-internal)
             |
             v
      [ targetPort: 8080 ]    <- Port your application container listens on inside the Pod
             |
             v
      [ containerPort: 8080 ] <- Informational field in the Pod/Deployment spec
```

| Port | Lives on | Who talks to it | Example |
|---|---|---|---|
| ⭐ **`nodePort`** | The worker node machine | External world / browser | `30080` (range **30000–32767**) |
| ⭐ **`port`** | The Service object | Other pods / internal services | `80` |
| ⭐ **`targetPort`** | The backend Pod container | The Service routing traffic | `8080` (number **or port name**) |
| **`containerPort`** | Deployment/Pod spec | ⭐ **Purely documentation / metadata** | `8080` |

> ⭐ **Mnemonic:** `nodePort` → `port` → `targetPort` is the path a packet takes, outside-in.
> `containerPort` isn't on the path at all — it's a comment. *(Same as Docker's `EXPOSE` vs `-p`,
> Session 7.)*

---

## 📊 Master Comparison Table (all 5 types)

| Feature | **ClusterIP** | **NodePort** | **LoadBalancer** | **ExternalName** | **Headless** |
|---|---|---|---|---|---|
| **Default type?** | ⭐ ✅ if omitted | ❌ | ❌ | ❌ | ❌ (`clusterIP: None`) |
| **ClusterIP allocated?** | ✅ virtual IP | ✅ (creates ClusterIP under the hood) | ✅ (creates NodePort + ClusterIP) | ❌ | ⭐ ❌ explicitly disabled |
| **External access?** | ❌ internal only | ✅ `NodeIP:NodePort` | ✅ cloud LB public IP | ❌ N/A (redirects out) | ❌ direct pod-to-pod |
| **Port range** | any 1–65535 | ⭐ **30000–32767** | any standard (80/443) | none | any |
| **DNS record** | single `A` → ClusterIP | single `A` → ClusterIP | single `A` → ClusterIP | ⭐ **`CNAME`** → external FQDN | ⭐ **multiple `A`** (one per Pod IP) |
| **Cloud provider needed?** | ❌ | ❌ | ⭐ ✅ | ❌ | ❌ |
| **Load balancing by** | `kube-proxy` | `kube-proxy` | Cloud LB + `kube-proxy` | DNS client | ⭐ **the client application** |
| **Creates Endpoints?** | ✅ | ✅ | ✅ | ⭐ ❌ (DNS alias only) | ✅ (pod IPs directly) |
| **Primary use case** | Microservices talking internally | Dev/testing, bare-metal, Ingress entry point | Public internet on AWS/GCP/Azure | External DBs (RDS, Mongo Atlas) | ⭐ **StatefulSets** (Kafka, MongoDB, Cassandra) |

---

## 1. ClusterIP — the internal phone system

> **The default.** An **internal virtual IP reachable only from inside the cluster**.
>
> 🏢 *Like an office PBX intercom: dialing extension `102` reaches Finance from inside the office,
> but nobody on the street can dial `102` from their cell phone.*

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: production
spec:
  type: ClusterIP          # optional — default if omitted
  selector:
    app: backend-api
  ports:
    - protocol: TCP
      port: 80             # Service port other pods connect to
      targetPort: 3000     # port your app listens on inside the container
```

**Under the hood:**
- The API server assigns an IP from the **service CIDR** (e.g. `10.96.0.0/12`).
- ⭐ **This IP is *virtual* — it belongs to no network card anywhere.**
- `kube-proxy` programs `iptables`/`IPVS` on **every** node so packets to that virtual IP get
  rewritten (DNAT) to one of the Pod IPs in the Service's **Endpoints**.

**Used for:** inter-service communication (frontend → backend API) · internal databases and caches
(Redis, PostgreSQL) that must never be public · ⭐ **backends behind an Ingress Controller**.

---

## 2. NodePort — the building gate port

> **Opens the same high port (30000–32767) on EVERY worker node.** Any request to
> `<any-node-IP>:<nodePort>` reaches your pods.
>
> 🏢 *An apartment complex with 5 towers. Every tower has a back gate labelled "Gate #30080 leads to
> the laundry room". Whichever tower you enter, you end up in the same laundry room.*

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport-service
spec:
  type: NodePort
  selector:
    app: web-frontend
  ports:
    - port: 80          # internal cluster service port
      targetPort: 80    # container port
      nodePort: 30080   # ⭐ optional — K8s assigns a random one if omitted
```

**Under the hood:** K8s picks a port in range → `kube-proxy` listens on it on **every node** →
it also creates a ClusterIP underneath. ⭐ **Traffic hitting `Node-A:30080` is forwarded to a backend
pod even if that pod runs on `Node-B`.**

**Used for:** on-premise/bare-metal clusters (no cloud LB API) · ⭐ **exposing the Ingress
Controller** to a hardware LB (F5, HAProxy) · quick Minikube demos.

**Why not for everyday public production?**
> - ⭐ **Ugly port range** for users (`:30080` instead of `:80`/`:443`).
> - ⭐ **If a node goes down**, clients hitting that node IP fail unless external DNS/LB handles failover.
> - ⭐ **Security**: exposing high ports across all nodes increases the attack surface.

---

## 3. LoadBalancer — the cloud VIP entrance

> **A real, highly available public IP on standard ports, provisioned automatically by your cloud
> provider.**
>
> 🏨 *Valet parking at a 5-star hotel: guests drive to the front entrance, hand over the keys, and
> the valet takes the car in through the staff entrance.*

```yaml
apiVersion: v1
kind: Service
metadata:
  name: public-storefront
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  type: LoadBalancer
  selector:
    app: storefront
  ports:
    - protocol: TCP
      port: 80          # port clients reach on the public IP
      targetPort: 8080  # port inside your container
```

### ⭐ The "Russian doll" principle
```
[Internet Client]
       │ Port 80/443
       ▼
[Cloud Load Balancer (AWS NLB / GCP LB)]      ← 3. cloud controller calls the cloud API
       │ NodePort: 31234
       ▼
[Worker Node 1 / 2 / 3]                       ← 2. K8s opens a NodePort on every node
       │ ClusterIP: 10.96.x.x
       ▼
[Target Pod]                                  ← 1. K8s creates a ClusterIP
```
> ⭐ **A LoadBalancer Service *contains* a NodePort, which *contains* a ClusterIP.** Nested dolls.

### ⭐⭐ Cost alert
> **Every `LoadBalancer` Service creates a dedicated cloud resource costing real money
> (~$15–30/month per LB on AWS).** With 50 microservices that's 50 load balancers.
>
> ⭐ **Production best practice: deploy ONE Ingress Controller exposed via a single LoadBalancer,
> and route 100 microservices through it** via host/path rules (Session 12).

**Direct LoadBalancer is still right for:** non-HTTP protocols (gaming servers, raw TCP/UDP, VoIP)
that Ingress can't handle.

---

## 4. ExternalName — the internal speed-dial alias

> ⭐ **The odd one out.** No selector, no IP, no `kube-proxy`, no pods. It is simply a
> **CoreDNS CNAME redirect**.
>
> 📱 *Speed dial: you save your friend as "Doc". Your phone looks up the real 10-digit number and
> dials it. If his number changes, you update one contact card, not all your notes.*

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rds-database-service
  namespace: default
spec:
  type: ExternalName
  externalName: my-postgres-prod.c2345892.us-east-1.rds.amazonaws.com
```

**Under the hood:** a pod queries `rds-database-service.default.svc.cluster.local` → CoreDNS returns
a **CNAME** → the pod's resolver does a second lookup to get the real IP.
⭐ **No proxying or NAT happens — the pod talks directly to the external service.**

### ⭐ The killer use case — environment portability
```
dev :  db-service  →  a local PostgreSQL pod (ClusterIP)
prod:  db-service  →  ExternalName → AWS Aurora RDS

⭐ Your app config is IDENTICAL in both:  DB_HOST=db-service
```

---

## 5. Headless Service — the direct calling line

> **Created by setting `clusterIP: None`.** It tells Kubernetes: *"Do NOT give me a virtual VIP and
> do NOT load balance. Just give me the direct IPs of all healthy backend pods via DNS."*
>
> 📇 *Instead of a switchboard connecting you to an arbitrary employee, someone hands you a list of
> every engineer's direct cell number. You choose who to call.*

```yaml
apiVersion: v1
kind: Service
metadata:
  name: cassandra-headless
spec:
  clusterIP: None      # ⭐ THIS makes it headless
  selector:
    app: cassandra
  ports:
    - port: 9042
      name: cql
```

### The DNS difference ⭐
```bash
# Normal ClusterIP
nslookup backend-service
# → 10.96.14.22                    (one virtual IP)

# Headless
nslookup cassandra-headless
# → 10.244.1.45                    ⭐ multiple A records — the actual pod IPs
#   10.244.2.89
#   10.244.3.12
```

### ⭐ Paired with a StatefulSet, every pod gets a permanent DNS name
```
<pod-name>.<service-name>.<namespace>.svc.cluster.local

kafka-0.kafka-headless.production.svc.cluster.local
kafka-1.kafka-headless.production.svc.cluster.local
kafka-2.kafka-headless.production.svc.cluster.local
```

**Used for:**
1. ⭐ **Stateful distributed systems** — **Kafka, ZooKeeper, MongoDB replica sets, Cassandra,
   Elasticsearch, Redis clusters**. These need to know who is Leader vs Replica and manage their own
   clustering and replication.
2. **Client-side load balancing** — gRPC/Envoy clients that want to choose the backend themselves
   rather than accept random `kube-proxy` forwarding.

> ⭐ **This is the `serviceName` field of the StatefulSet in Session 10.** A StatefulSet without a
> headless Service has no per-pod DNS, which defeats the point.

---

## ⚙️ How Traffic Flows Under the Hood

> ⭐ **The master node does not route packets.** Here's the actual mechanism:

```
1. ENDPOINT CONTROLLER
   Watches the Service selector → finds all pods with matching labels
   that ⭐ PASS THEIR READINESS PROBES → writes an Endpoints / EndpointSlice
   object holding the live list of pod IPs.

2. KUBE-PROXY (on every worker node)
   Watches the API for new Services and Endpoints.

3. DATA PLANE
   • iptables mode (default): injects netfilter rules into the kernel.
     Packets matching the virtual Service IP get DNAT'd to a healthy Pod IP.
   • IPVS mode (high scale): IP Virtual Server in the kernel — hash tables
     instead of linear lists ⇒ ⭐ O(1) with 10,000+ services, plus real
     algorithms (least-connection, weighted round-robin).
```

> ⭐⭐ **Traffic never passes *through* kube-proxy.** kube-proxy writes rules; **the Linux kernel**
> rewrites the packets. That's why Service routing costs almost nothing.

---

## 🔗 Services Without Selectors

> **Can you create a Service without a `selector`?** ⭐ **YES** — and it's a staple senior interview
> question.

When there's no selector, Kubernetes **does not** create an Endpoints object. ⭐ **You create and
manage it yourself.**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: legacy-db
spec:
  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306
  # ⭐ NO selector
---
apiVersion: v1
kind: Endpoints
metadata:
  name: legacy-db        # ⭐ MUST match the Service name exactly
subsets:
  - addresses:
      - ip: 192.168.1.150   # external legacy server outside K8s
    ports:
      - port: 3306
```

> ⭐ Now any pod can connect to `legacy-db:3306` and traffic goes to `192.168.1.150` — an external
> machine treated exactly like an internal ClusterIP.

**vs ExternalName:**
| | **ExternalName** | **Service without selector** |
|---|---|---|
| Mechanism | ⭐ **DNS CNAME redirect** | ⭐ **kube-proxy NAT to specific IPs** |
| Points at | An external **domain name (FQDN)** | Specific **IP addresses** |
| Traffic path | ⭐ Bypasses the cluster network entirely | Routed through kube-proxy |

---

## 📛 FQDN & CoreDNS

> **How do Pods talk without knowing each other's IPs?** ⭐ **CoreDNS + FQDN.**

### The FQDN anatomy ⭐
```text
  payment-service .  production  .   svc   .  cluster.local
  └──────┬──────┘   └─────┬────┘    └──┬──┘  └──────┬──────┘
    Service Name      Namespace    Object Type   Cluster Domain
```

| Segment | Meaning |
|---|---|
| `payment-service` | The Service's `metadata.name` |
| `production` | The **namespace** it lives in |
| `svc` | Tells CoreDNS this is a **Service** (vs `pod`) |
| `cluster.local` | The cluster's base domain (default; set at cluster creation) |

### CoreDNS — the cluster phonebook
> 🏨 *CoreDNS is the hotel operator. Pod A asks "what's the IP of `payment-service`?", the operator
> checks the phonebook and replies "10.96.45.12".*

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
```
```text
NAME                       READY   STATUS    RESTARTS   AGE
coredns-768b85b76f-8j2k4   1/1     Running   0          5d
coredns-768b85b76f-vx4qp   1/1     Running   0          5d
```
> ⭐ **CoreDNS watches the Kubernetes API.** Create/update/delete a Service and its DNS record
> changes **in real time**.

### The full query flow
```
1. Frontend Pod runs: curl http://backend
2. Linux checks /etc/resolv.conf inside the Pod
     nameserver → 10.96.0.10 (CoreDNS Service IP)
     appends search domain → backend.production.svc.cluster.local
3. Query sent to the CoreDNS Pod in kube-system
4. CoreDNS returns the Service ClusterIP: 10.96.200.55
5. Pod sends the HTTP request to 10.96.200.55
   → ⭐ kube-proxy's kernel rules route it to one of the backend Pods
```

---

## 🏠 Short Name vs Long Name

### Same namespace ✅
```
[Frontend Pod]  ── curl http://backend ──▶  [Backend Service]     both in `production`
```
Works, because `/etc/resolv.conf` automatically appends `production.svc.cluster.local`.

### Different namespaces ⭐
```
Namespace: [dev]                                   Namespace: [production]
[Test Pod] ── curl http://backend ──▶ ❌ FAILS      (looks for backend.dev.svc...)
[Test Pod] ── curl http://backend.production ──▶ ✅ SUCCESS
```

> ⭐⭐ **The #1 cross-namespace bug.** The fix:
> ```bash
> curl http://backend.production                          # service + namespace (most common)
> curl http://backend.production.svc.cluster.local        # full FQDN (bulletproof)
> ```

### The three DNS name forms
| Form | Pattern | Returns |
|---|---|---|
| **Service** | `<service>.<namespace>.svc.cluster.local` | The single **ClusterIP** |
| ⭐ **StatefulSet pod** (headless) | `<pod>.<service>.<namespace>.svc.cluster.local` | That **specific pod's IP** |
| **Any pod, by IP** | `<pod-ip-with-dashes>.<namespace>.pod.cluster.local` | e.g. `10-244-2-85.default.pod.cluster.local` |

---

## 📄 Inside a Pod: `/etc/resolv.conf`

Kubernetes injects this into **every** Pod:
```ini
nameserver 10.96.0.10
search production.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

| Line | Meaning |
|---|---|
| `nameserver 10.96.0.10` | ⭐ The ClusterIP of the CoreDNS Service — every lookup goes here |
| `search …` | ⭐ **Autocomplete list.** `curl http://backend` tries `backend.production.svc.cluster.local` → `backend.svc.cluster.local` → `backend.cluster.local` |
| `options ndots:5` | ⭐ *"If a name has fewer than 5 dots, try the search suffixes first before treating it as an external domain"* |

### ⭐⭐ The `ndots:5` performance trap
Calling an external API like `api.stripe.com` (only 2 dots):
```
1. api.stripe.com.production.svc.cluster.local   → NXDOMAIN
2. api.stripe.com.svc.cluster.local              → NXDOMAIN
3. api.stripe.com.cluster.local                  → NXDOMAIN
4. api.stripe.com                                → ✅ finally
```
> ⭐ **Three useless DNS queries on every single call** — real latency on high-throughput
> microservices.
>
> **Fixes:** add a **trailing dot** in config (`api.stripe.com.`) to mark it already fully qualified,
> or set `dnsConfig.options` in the Pod spec to lower `ndots` (e.g. `ndots:2`).

---

## 🧪 Testing DNS in Your Cluster

```bash
# spin up a throwaway diagnostic pod
kubectl run dnsutils --rm -it --image=ghcr.io/nestybox/curl:latest -- sh
# (or busybox:1.28 / tutum/dnsutils)

# inside:
nslookup kubernetes                                  # short name
nslookup kubernetes.default.svc.cluster.local        # full FQDN
cat /etc/resolv.conf                                 # which DNS am I using?
```
```text
Server:         10.96.0.10
Address:        10.96.0.10#53

Name:   kubernetes.default.svc.cluster.local
Address: 10.96.0.1
```

**Service debugging ladder:**
```bash
kubectl get svc <svc>
kubectl describe svc <svc>              # ⭐ check the Selector line
kubectl get endpoints <svc>             # ⭐⭐ EMPTY endpoints = selector matches nothing,
                                        #    or no pod is passing readiness
kubectl get pods --show-labels          # do the labels actually match?
```
> ⭐ **`kubectl get endpoints` is *the* Service debugging command.** If it's empty, the problem is
> your selector or your readiness probe — never the Service type.
> *(The repo's `troubleshooting/empty-endpoints.yaml` drills exactly this.)*

---

## 🌳 Decision Tree: Which Service Do I Pick?

```text
Do you need to expose this outside the cluster?
│
├── NO ──► Need direct peer-to-peer pod communication / StatefulSet clustering?
│           ├── YES ──► ⭐ HEADLESS SERVICE (clusterIP: None)
│           └── NO  ──► ⭐ CLUSTERIP (default)
│
└── YES ─► Connecting to an outside third-party domain (e.g. AWS RDS FQDN)?
            ├── YES ──► ⭐ EXTERNALNAME
            └── NO  ──► On a public cloud?
                         ├── YES ──► Exposing HTTP/HTTPS web apps?
                         │            ├── YES ──► ⭐⭐ ONE INGRESS CONTROLLER via LOADBALANCER,
                         │            │            apps stay CLUSTERIP
                         │            └── NO  ──► LOADBALANCER (Layer 4 TCP/UDP)
                         └── NO (bare-metal / on-prem / local) ──► ⭐ NODEPORT
```

---

## ❓ Interview Q&A

**Q1: Default Service type if none is specified?**
> ⭐ **`ClusterIP`** — reachable only from within the cluster.

**Q2: NodePort vs LoadBalancer?**
> `NodePort` exposes a static port (30000–32767) on every node's IP; the user connects to
> `<Node-IP>:<NodePort>`. ⭐ `LoadBalancer` **supersedes NodePort** by calling the cloud API to
> provision an external LB with a public IP, taking traffic on 80/443 and distributing to nodes.

**Q3: Why a Headless Service instead of ClusterIP?**
> ⭐ (1) Stateful clustered systems (**Kafka, MongoDB replica sets, Cassandra**) where nodes must
> discover **specific peers** (Leader vs Follower), not a random load-balanced one.
> (2) You want CoreDNS to return **all pod IPs** so the client can do its own load balancing.

**Q4: If NodePort and LoadBalancer both expose services, why do we need Ingress?**
> ⭐⭐ **Cost and Layer-7 routing.**
> - Every LoadBalancer = a paid cloud LB. 50 microservices = 50 LBs = hundreds of dollars/month.
> - A LoadBalancer is **Layer 4** — it can't do path routing (`/api` vs `/login`), host routing
>   (`api.domain.com` vs `web.domain.com`), or multi-domain SSL termination.
> - ⭐ An **Ingress Controller** uses **one** LoadBalancer and routes all L7 traffic to internal
>   ClusterIP services.

**Q5: What happens when a backend pod fails its readiness probe?**
> ⭐ The endpoint controller **immediately removes its IP from the Endpoints/EndpointSlice**, so
> traffic stops reaching it. When the probe passes again, it's added back.
> ⭐⭐ **The pod is NOT killed — liveness kills, readiness controls traffic.**

**Q6: Default NodePort range, and can it change?**
> ⭐ **30000–32767**. Yes — via the `--service-node-port-range` flag on `kube-apiserver`.

**Q7: ExternalName vs a selectorless Service pointing at an external IP?**
> ⭐ ExternalName is **DNS CNAME only** — maps to a **domain name**, traffic never touches the
> cluster network. A selectorless Service + manual Endpoints points at **IP addresses** and routes
> via kube-proxy NAT.

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| ⭐ **IP-per-Pod / flat network** | Every Pod gets a unique IP and reaches every other Pod **without NAT** |
| **Three networks** | Node (`192.168.x`) · Pod (`10.244.x`) · ⭐ Service (`10.96.x`, **purely virtual**) |
| ⭐ **CNI** | The plugin that actually implements Pod networking (Calico, Flannel, Cilium) — ⭐ **missing CNI ⇒ everything stuck Pending** |
| **`pause` container** | Hidden per-Pod container holding the network namespace so the **IP survives crashes** |
| ⭐ **NetworkPolicy** | Firewall rules between Pods; ⭐ **deny-by-default once selected**, and ⭐ **enforced by the CNI — silently ignored on Flannel** |
| ⭐ **Service** | Stable IP + DNS name + load balancing over a changing set of Pods |
| ⭐ **`port` / `targetPort` / `nodePort`** | Service port / container port / node port (**30000–32767**) |
| **`containerPort`** | ⭐ Documentation only — not on the traffic path |
| ⭐ **ClusterIP** | Default; **virtual IP** internal to the cluster |
| **Service CIDR** | Pool the virtual IPs come from (e.g. `10.96.0.0/12`) |
| ⭐ **NodePort** | Same high port open on **every** node; forwards across nodes |
| ⭐ **LoadBalancer** | Cloud LB → NodePort → ClusterIP → Pod ("Russian dolls"); ⭐ **costs money per service** |
| **ExternalName** | ⭐ CoreDNS **CNAME** to an external FQDN; no IP, no proxy, no pods |
| ⭐ **Headless** | `clusterIP: None` → **multiple A records** (pod IPs); required for StatefulSets |
| ⭐ **Endpoints / EndpointSlice** | Live list of **ready** pod IPs behind a Service — ⭐ **empty = your bug** |
| **Endpoint controller** | Keeps that list in sync with the selector + readiness |
| ⭐ **kube-proxy** | Programs iptables/IPVS; ⭐ **traffic doesn't flow through it** |
| **iptables vs IPVS** | netfilter DNAT vs kernel hash tables (**O(1)** at 10,000+ services) |
| **Selectorless Service** | No selector ⇒ **you** write the Endpoints; points at external IPs |
| ⭐ **CoreDNS** | Cluster DNS in `kube-system`; watches the API, updates records in real time |
| ⭐ **FQDN** | `<service>.<namespace>.svc.cluster.local` |
| **StatefulSet pod DNS** | `<pod>.<service>.<namespace>.svc.cluster.local` |
| ⭐ **Cross-namespace** | Short names fail — use `service.namespace` |
| ⭐ **`ndots:5`** | Names with <5 dots try search suffixes first ⇒ **3 wasted lookups** on external domains |

---

## 🎯 Session Takeaways

1. ⭐⭐ **The flat network model is the foundation:** every Pod has its own IP and reaches every other
   Pod **without NAT**, across nodes. **There is no port publishing between Pods** — unlike Docker.
2. ⭐ **Three networks, and the Service network is virtual** — no packet ever arrives at a ClusterIP,
   which is why `ping <ClusterIP>` fails even when the Service works.
3. ⭐ **Kubernetes delegates Pod networking to a CNI plugin.** No CNI ⇒ every Pod stays `Pending`.
   **NetworkPolicy is also enforced by the CNI** — apply one on Flannel and it does nothing.
4. ⭐ **Pods come and go; Services stay.** Pod IPs change on every restart — a Service is the stable
   name, IP and load balancer in front of them.
5. ⭐ **Know the four ports:** `nodePort` → `port` → `targetPort` is the packet's path;
   **`containerPort` is just documentation.**
6. ⭐ **ClusterIP is the default and is a *virtual* IP** that exists on no network card — kube-proxy's
   kernel rules make it work.
7. ⭐ **NodePort opens the port on every node** and forwards across nodes, but the ugly port range,
   node-failure exposure and attack surface keep it out of public production.
8. ⭐⭐ **LoadBalancer contains a NodePort which contains a ClusterIP** — and **each one costs
   ~$15–30/month**, which is the entire economic argument for Ingress.
9. **ExternalName is a CNAME, not a proxy** — its best use is making `DB_HOST=db-service` work
   identically in dev and prod.
10. ⭐ **Headless (`clusterIP: None`) returns pod IPs instead of a VIP**, and gives StatefulSet pods
   stable per-pod DNS — mandatory for Kafka/Mongo/Cassandra.
11. ⭐⭐ **kube-proxy writes rules; the kernel moves packets.** IPVS beats iptables at 10,000+ services.
12. ⭐ **Readiness probes control Service membership** — a failing pod is silently removed from
   Endpoints, and **liveness kills while readiness only de-routes**.
13. ⭐⭐ **`kubectl get endpoints` is the Service debugging command.** Empty endpoints means a selector
    mismatch or a failing readiness probe — not a Service-type problem.
14. ⭐ **CoreDNS gives every Service an FQDN**, and **cross-namespace calls need
    `service.namespace`** — the most common "worked in dev" failure.
15. ⭐ **`ndots:5` silently costs you 3 failed DNS lookups per external API call**; fix with a
    trailing dot or a lower `ndots`.

---

## 🔗 References
- Kubernetes Services — https://kubernetes.io/docs/concepts/services-networking/service/
- DNS for Services and Pods — https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/
- Instructor's Kubernetes repo — https://github.com/Nency-Ravaliya/Kubernetes
- Course repo — https://github.com/Nency-Ravaliya/devops-heros

---

## ➡️ Next
**[Session 12 — Ingress, ConfigMaps & Secrets](./12_Kubernetes_Ingress_ConfigMaps_and_Secrets.md)**
