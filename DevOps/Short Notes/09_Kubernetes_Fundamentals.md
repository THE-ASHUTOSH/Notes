# ⚡ S09 · Kubernetes Fundamentals

> *Revision card.* Full notes → [Session 9](../09_Kubernetes_Fundamentals.md)

---

## 🔑 One-line core

***Everything goes through the API server, and only it touches etcd.*** You declare
**desired state**; controllers reconcile reality to match — self-healing is a free
side-effect.

---

## 🏗️ Cluster architecture

```
┌──────────────── CONTROL PLANE ────────────────┐
│  kube-apiserver  ←── the ONLY door            │
│       │                                       │
│   ┌───┴────┬──────────────┬───────────┐       │
│  etcd   scheduler   controller-mgr   cloud-cm │
└───────────────────────────────────────────────┘
            │
┌───────────┴──── WORKER NODE ──────────────────┐
│  kubelet · kube-proxy · container runtime     │
│        └── Pods ── containers                 │
└───────────────────────────────────────────────┘
```

---

## 🧠 Control plane components

| | Does |
|---|---|
| **kube-apiserver** | ⭐ the **only** component that talks to etcd; REST + auth + validation |
| **etcd** | key-value store = **the cluster's entire state**. ⚠️ back it up |
| **scheduler** | picks a **node** for a new Pod — ⚠️ does *not* start it |
| **controller-manager** | the reconcile loops (node, replicaset, endpoints, …) |
| cloud-controller-manager | load balancers, volumes, routes |

## ⚙️ Worker node

| | Does |
|---|---|
| **kubelet** | talks to the runtime, **actually starts containers**, reports status |
| **kube-proxy** | Service → Pod networking rules (iptables / IPVS) |
| **runtime** | containerd / CRI-O |

---

## 🔁 What `kubectl apply` really does

```
kubectl apply ──▶ API server ──▶ validate ──▶ write to etcd
                                                  │
                            scheduler watches ────┤ assigns node
                                                  │
                            kubelet watches ──────┘ starts container
                                                  │
                                      status ─────▶ back to etcd
```

> ⭐ **Nobody is "told" anything — everyone watches.** That's the control loop.

---

## 📦 Core objects

| | |
|---|---|
| **Pod** | smallest unit — 1+ containers, shared net + storage |
| **ReplicaSet** | keeps N Pods alive |
| **Deployment** | manages ReplicaSets → rolling updates, rollbacks |
| **Service** | stable address + load balancing |
| **ConfigMap / Secret** | config / sensitive config |
| **Namespace** | logical partition |
| Job / CronJob | run-to-completion / scheduled |
| DaemonSet | one Pod per node |
| StatefulSet | stable identity + storage |

---

## 🗂️ Namespaces

```bash
kubectl get ns
kubectl get pods -n kube-system
kubectl config set-context --current --namespace=dev
```

Built-in: `default` · `kube-system` · `kube-public` · `kube-node-lease`

> ⚠️ Namespaces are **not** a security boundary by themselves — add RBAC + NetworkPolicy.

---

## 🔐 RBAC in four nouns

```
Subject (user / group / ServiceAccount)
   │   bound by
RoleBinding ───────▶ Role            (namespaced)
ClusterRoleBinding ─▶ ClusterRole    (cluster-wide)
```

```bash
kubectl auth can-i delete pods --as system:serviceaccount:dev:myapp
```

---

## 🧾 kubectl

```bash
kubectl get pods -o wide -A
kubectl describe pod <p>
kubectl logs -f <p> [-c container] [--previous]
kubectl exec -it <p> -- sh
kubectl apply -f . / delete -f .
kubectl get all
kubectl explain pod.spec.containers      # ⭐ built-in docs
```

---

## ⚠️ Traps

- The **scheduler** doesn't start Pods — the **kubelet** does.
- `kubectl get all` omits ConfigMaps, Secrets, Ingresses, PVCs, CRDs.
- Imperative `kubectl edit` in prod = drift. Keep YAML in Git.

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Who talks to etcd? | **only** the API server |
| Scheduler's job? | choose a node, nothing else |
| What starts the container? | **kubelet** |
| Why self-healing? | controllers reconcile desired vs actual, forever |
| Local cluster? | minikube · kind · k3s |

---

⬅️ [S08](./08_Docker_Networking_Volumes_and_Compose.md) · ➡️ [S10 · Pods & Deployments](./10_Pods_ReplicaSets_Deployments.md)
