# ⚡ S11 · Kubernetes Networking & Services

> *Revision card.* Full notes → [Session 11](../11_Kubernetes_Networking_and_Services.md)

---

## 🔑 One-line core

***`kubectl get endpoints <svc>` is the Service debugging command.***
Empty = selector mismatch **or** Pods not Ready.

---

## 🌐 The four networking rules

1. Every **Pod gets its own IP**
2. Pods can reach each other **without NAT**
3. Nodes can reach Pods without NAT
4. The IP a Pod sees for itself is the IP others see

> ⚠️ **Pod IPs are ephemeral** — they change on every restart. That is *why* Services exist.

---

## 🔗 The chain that must hold

```
Pod labels ──match──▶ Service selector ──produces──▶ Endpoints
                                                        │
                                              ClusterIP ──▶ DNS name
```

Break **any** link → Service exists, Pods `Running`, **zero traffic**.

---

## 🚪 Service types

| Type | Reachable from | Use |
|---|---|---|
| **ClusterIP** (default) | inside the cluster only | internal services |
| **NodePort** | `<nodeIP>:30000–32767` | dev / bare metal |
| **LoadBalancer** | external IP from the cloud | prod on a cloud |
| **ExternalName** | CNAME to an outside host | external DB |
| **Headless** (`clusterIP: None`) | returns **Pod IPs** | StatefulSets |

---

## 🔢 The ports — know the direction

```
client → nodePort (30080) → port (80) → targetPort (8080) → container
            ↑                  ↑              ↑
       on the node        on the Service   on the Pod
```

```yaml
ports:
  - nodePort:   30080     # outside world
    port:       80        # the Service's own port
    targetPort: 8080      # the container's port
```

> ⚠️ **`containerPort` in a Pod spec is documentation only.** `targetPort` is what routes.

---

## 🧭 DNS

```
<service>.<namespace>.svc.cluster.local
```

| From | Use |
|---|---|
| same namespace | `backend` |
| other namespace | `backend.prod` |
| fully qualified | `backend.prod.svc.cluster.local` |

**CoreDNS** runs in `kube-system`.

> 💡 **`ndots:5`** in `/etc/resolv.conf` means short names try **five search suffixes
> first** — which is why an external lookup can be unexpectedly slow. End with a `.` to skip it.

---

## 🩺 The 7-step Service debug

```bash
1. kubectl get pods                        # Running AND Ready?
2. kubectl get pods --show-labels          # actual labels
3. kubectl describe svc <name>             # wanted selector
4. kubectl get endpoints <name>            # ⭐ empty = the smoking gun
5. kubectl exec <pod> -- nslookup <svc>    # DNS
6. kubectl exec <pod> -- wget -qO- <svc>   # connectivity
7. kubectl get pods -n kube-system         # CoreDNS alive?
```

### The decisive test

| `nslookup` | `curl` | Diagnosis |
|---|---|---|
| ✅ | ✅ | not a cluster-networking problem |
| ✅ | ❌ | ⭐ **DNS is fine** — selector / endpoints / targetPort / NetworkPolicy |
| ❌ | ❌ | real DNS problem → CoreDNS |

> ⚠️ **Do not blame DNS first.**

---

## 🛡️ NetworkPolicy (needs a CNI that supports it)

> ⭐ **Default is allow-all.** The moment *one* policy selects a Pod, everything not
> explicitly allowed is **denied** for that Pod.

```yaml
spec:
  podSelector: { matchLabels: { app: db } }
  policyTypes: [Ingress]
  ingress:
    - from: [{ podSelector: { matchLabels: { app: api } } }]
      ports: [{ port: 5432 }]
```

---

## ⚠️ Traps

| Trap | Reality |
|---|---|
| Service down because Pods are broken | ⚠️ often just a **label typo** |
| `containerPort` routes traffic | ⚠️ it's documentation |
| NodePort works like a load balancer | ⚠️ you still need something in front |
| Pod IP is stable | ⚠️ never |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Service returns nothing, Pods healthy? | `kubectl get endpoints` → selector/readiness |
| NodePort range? | **30000–32767** |
| FQDN form? | `svc.ns.svc.cluster.local` |
| Headless Service for? | **StatefulSets** — returns Pod IPs |
| `port` vs `targetPort`? | Service's port vs the container's |

---

⬅️ [S10](./10_Pods_ReplicaSets_Deployments.md) · ➡️ [S12 · Ingress & Config](./12_Ingress_ConfigMaps_Secrets.md)
