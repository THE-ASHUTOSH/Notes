# ⚡ S10 · Pods, ReplicaSets & Deployments

> *Revision card.* Full notes → [Session 10](../10_Kubernetes_Pods_ReplicaSets_and_Deployments.md)

---

## 🔑 One-line core

***`Running` ≠ `Ready`.*** Only five Pod **phases** exist — `CrashLoopBackOff` is a
container *state*, not a phase.

---

## 📦 Pod phases — there are only five

| Phase | Means |
|---|---|
| **Pending** | accepted, **not scheduled yet** (or pulling) |
| **Running** | bound to a node, ≥1 container running |
| **Succeeded** | all containers exited **0** |
| **Failed** | a container exited **non-zero** |
| **Unknown** | node unreachable |

> ⚠️ `CrashLoopBackOff`, `ImagePullBackOff`, `ContainerCreating`, `Terminating` are
> **container states / reasons** — *not* phases.

---

## 🧩 Multi-container patterns

| | |
|---|---|
| **Sidecar** | log shipper, proxy next to the app |
| **Init container** | runs **to completion first** — wait for DB, migrate |
| **Adapter / Ambassador** | reshape output / proxy outbound |

Containers in a Pod share **network (localhost!)** and can share volumes.

---

## 🏷️ Labels & selectors — the glue

```yaml
metadata:
  labels: { app: web, tier: frontend }
---
selector:
  matchLabels: { app: web }
```

```bash
kubectl get pods -l app=web --show-labels
```

> ⭐ **Everything finds everything else by label** — Services, ReplicaSets, NetworkPolicies.

---

## 🔁 Deployment → ReplicaSet → Pod

```
Deployment  (rollout strategy, history)
     └── ReplicaSet  (keeps N pods)   ← a NEW one per image change
             └── Pods
```

```bash
kubectl create deploy web --image=nginx:1.27 --replicas=3
kubectl scale deploy web --replicas=5
kubectl set image deploy/web nginx=nginx:1.28
kubectl rollout status deploy/web
kubectl rollout history deploy/web
kubectl rollout undo deploy/web            # ⭐ fastest mitigation
kubectl rollout restart deploy/web         # ⭐ re-read ConfigMaps
```

---

## 🎚️ Rolling update knobs

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1          # extra pods allowed above replicas
    maxUnavailable: 0    # ⭐ zero-downtime
```

> ⭐ **A rolling update only advances when a new Pod passes its *readiness* probe.**
> With `maxUnavailable: 0`, a bad deploy **stalls** instead of causing an outage.

---

## 🚀 The four strategies

| | How | Cost |
|---|---|---|
| **RollingUpdate** (default) | replace gradually | two versions live at once |
| **Recreate** | kill all, then start | **downtime** — needed for incompatible schemas |
| **Blue-Green** | two full envs, flip the Service | 2× resources, instant rollback |
| **Canary** | 5% → 25% → 100% | needs metrics + traffic splitting |

---

## 🗃️ Other workload kinds

| | For |
|---|---|
| **StatefulSet** | stable name (`web-0`), stable storage, ordered start — databases |
| **DaemonSet** | exactly one Pod **per node** — log agents, CNI, node-exporter |
| **Job** | run **to completion**; `completions`, `parallelism`, `backoffLimit` |
| **CronJob** | a Job on a schedule (⚠️ **UTC**) |

> ⚠️ A container that finishes its work under a **Deployment** gets restarted forever.
> Exit 0 + `restartPolicy: Always` ⇒ you wanted a **Job**.

---

## ⚠️ Traps

- `Running 0/1` = **readiness failing**, and it's already out of the Service's endpoints
- Deployment `selector` is **immutable** — changing it means delete + recreate
- No readiness probe ⇒ rolling update "succeeds" the moment the process starts
- CronJob schedules are UTC

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| How many Pod phases? | **five** |
| Is `CrashLoopBackOff` a phase? | **no** — a container waiting reason |
| Zero-downtime deploy? | `maxUnavailable: 0` **+ readiness probe** |
| Roll back fast? | `kubectl rollout undo` |
| Config changed, pods didn't? | `kubectl rollout restart` |
| Batch work? | **Job**, not Deployment |

---

⬅️ [S09](./09_Kubernetes_Fundamentals.md) · ➡️ [S11 · Services](./11_Kubernetes_Networking_and_Services.md)
