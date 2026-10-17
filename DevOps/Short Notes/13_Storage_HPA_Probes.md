# ⚡ S13 · Storage, HPA & Probes

> *Revision card.* Full notes → [Session 13](../13_Kubernetes_Storage_HPA_and_Probes.md)

---

## 🔑 One-line core

***PV = supply, PVC = demand.*** **No CPU `requests` + no Metrics Server ⇒ no HPA.**
**Readiness failure ≠ container restart.**

---

## 💾 Volume types

| | Lives | Use |
|---|---|---|
| `emptyDir` | **dies with the Pod** | scratch, sidecar sharing |
| `hostPath` | a path on **that node** | ⚠️ node-specific, avoid |
| **PVC** | independent of the Pod | ⭐ real data |
| `configMap` / `secret` | injected files | config |

---

## 🔌 PV / PVC

```
PVC (I want 10Gi, RWO)  ──binds──▶  PV (here is 10Gi)
         ↑                                ↑
    the Pod asks                   admin-made, or
                                   StorageClass makes it (dynamic)
```

| Access mode | Means |
|---|---|
| **RWO** `ReadWriteOnce` | one **node** can mount read-write ⭐ most block storage |
| **ROX** `ReadOnlyMany` | many nodes, read-only |
| **RWX** `ReadWriteMany` | many nodes read-write — needs NFS/CephFS/EFS |

| Reclaim policy | On PVC delete |
|---|---|
| `Retain` | keep the data ⭐ for prod |
| `Delete` | wipe it (default for dynamic) |

---

## 🏭 StorageClass = dynamic provisioning

```yaml
storageClassName: gp3        # no admin, no pre-made PV
```

Omit it → the cluster's **default** class. `storageClassName: ""` → no dynamic
provisioning at all.

---

## 📈 HPA

```bash
kubectl autoscale deploy web --cpu-percent=70 --min=2 --max=10
kubectl get hpa
```

```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target: { type: Utilization, averageUtilization: 70 }
```

> ⭐ **Two hard requirements:**
> 1. the Deployment **must set `resources.requests.cpu`** — utilisation is a *percentage
>    of the request*
> 2. **Metrics Server must be installed**
>
> ⚠️ Missing either → `TARGETS: <unknown>/70%` and **it never scales**.

### The autoscaler trio

| | Scales |
|---|---|
| **HPA** | **more Pods** |
| **VPA** | bigger Pods (⚠️ restarts them) |
| **Cluster Autoscaler** | **more nodes** |

> ⭐ HPA adds Pods; if no node can hold them they sit **`Pending`** — only the **Cluster
> Autoscaler** fixes that.

---

## 🩺 The three probes

| Probe | Question | On failure |
|---|---|---|
| **liveness** | *is it alive?* | ⭐ **restart the container** |
| **readiness** | *can it take traffic?* | ⭐ **remove from Service endpoints** (no restart) |
| **startup** | *has it finished booting?* | hold the other two off |

```yaml
livenessProbe:
  httpGet: { path: /health, port: 8080 }
  initialDelaySeconds: 20
  periodSeconds: 15
readinessProbe:
  httpGet: { path: /ready, port: 8080 }
  initialDelaySeconds: 10
  periodSeconds: 10
startupProbe:
  httpGet: { path: /health, port: 8080 }
  failureThreshold: 30
  periodSeconds: 10          # → 300 s to boot
```

> ⚠️ **Never check the database in a liveness probe.** A DB blip then restarts your whole
> fleet — a recoverable outage becomes a self-inflicted one. **That belongs in readiness.**

> ⚠️ Liveness `initialDelaySeconds` **too short** → Kubernetes kills the container while
> it is still legitimately starting. Use a **startupProbe** for slow starters.

---

## 🧮 Requests vs limits

```yaml
resources:
  requests: { cpu: 100m, memory: 128Mi }   # ⭐ scheduling + HPA basis
  limits:   { cpu: 500m, memory: 512Mi }   # enforcement
```

| | Over the limit |
|---|---|
| **CPU** | **throttled** (compressible) |
| **Memory** | ⚠️ **OOMKilled — exit 137** (incompressible) |

**QoS:** `requests == limits` → **Guaranteed** · some set → **Burstable** · none →
**BestEffort** (⚠️ evicted first).

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| HPA says `<unknown>`? | no CPU **requests**, or no **Metrics Server** |
| Pod restarts in a loop at a fixed interval? | **liveness probe** too aggressive |
| Readiness fails — restart? | **no**, just removed from endpoints |
| Exit 137? | **OOMKilled** — raise the memory limit or fix the leak |
| PVC stuck `Pending`? | no matching PV / no StorageClass |
| RWO on two nodes? | ⚠️ won't mount — you need RWX |

---

⬅️ [S12](./12_Ingress_ConfigMaps_Secrets.md) · ➡️ [S14 · Troubleshooting](./14_Kubernetes_Troubleshooting.md)
