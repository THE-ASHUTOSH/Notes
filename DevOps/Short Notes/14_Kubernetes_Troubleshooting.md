# ⚡ S14 · Kubernetes Troubleshooting

> *Revision card.* Full notes → [Session 14](../14_Kubernetes_Troubleshooting.md)

---

## 🔑 One-line core

***`CrashLoopBackOff` is a symptom, never a cause.*** Follow the loop; never
`kubectl delete pod` to "fix" it — the restart destroys the evidence.

---

## 🔁 The loop

```
get  →  describe  →  EVENTS  →  logs --previous  →  exec  →  test  →  FIX  →  VERIFY
```

| Command | Answers |
|---|---|
| `kubectl get` | **what** is happening |
| `kubectl describe` | **why** — ⭐ read **Events** first |
| `kubectl logs` | what the **app** says |
| `kubectl exec` | what it looks like **from inside** |
| `kubectl events` | what **Kubernetes tried** |

---

## 🗺️ Symptom → first command

| You see | Almost certainly | Run |
|---|---|---|
| `Pending`, `NODE <none>` | scheduling: resources / selector / taint / PVC | `describe pod` → Events |
| `ContainerCreating` stuck | volume / Secret / ConfigMap / CNI | `describe pod` → Events |
| `ImagePullBackOff` | name, tag, or registry auth | `describe pod` → Events |
| **`CrashLoopBackOff`** | app exits on startup | ⭐ `logs --previous` |
| `Running` but **`0/1`** | **readiness** failing | `describe` → `Unhealthy` |
| exit **137** | **OOMKilled** | `top pod`, raise limit |
| `Evicted` | node memory/disk pressure | `describe node` |
| Service returns nothing | selector / not Ready | ⭐ `get endpoints` |
| DNS won't resolve | CoreDNS | `logs -n kube-system -l k8s-app=kube-dns` |

---

## 💥 CrashLoopBackOff

```
start → crash → restart → crash → wait (10s, 20s, 40s … capped 5 min)
```

```bash
kubectl describe pod <p>          # State / Last State / Restart Count / Events
kubectl logs <p> --previous       # ⭐ the container that just DIED
```

| Cause | Tell |
|---|---|
| app exception | stack trace in `--previous` |
| missing env / config | `FailedMount` in Events |
| wrong `command` | exit **127**, `not found` |
| **finished its work** | exit **0** → you wanted a **Job** |
| liveness too aggressive | restarts at a *regular* interval |
| OOM | `Reason: OOMKilled`, exit **137** |

---

## 🖼️ ImagePullBackOff

`ErrImagePull` = first failure · `ImagePullBackOff` = throttled retry. **Same cause.**

| Message contains | Means |
|---|---|
| `repository does not exist` | typo |
| `manifest unknown` | bad tag |
| `unauthorized` | need `imagePullSecrets` |
| `toomanyrequests` | Docker Hub rate limit |
| `no matching manifest` | wrong architecture |

```bash
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io --docker-username=u --docker-password=tok
```

---

## ⏳ Pending

⭐ **A scheduler problem, not an app problem.** Confirm: `get pod -o wide` → `NODE <none>`.

| Cause | Check |
|---|---|
| **insufficient CPU/memory** ⭐ | `describe node` → Allocated resources |
| nodeSelector mismatch | `get nodes --show-labels` |
| taints, no toleration | `describe node \| grep Taints` |
| **PVC unbound** | `get pvc` |
| cluster full | needs the **Cluster Autoscaler** |

---

## 🌐 Service / DNS

```bash
kubectl get endpoints <svc>          # ⭐ <none> = the smoking gun
kubectl get pods --show-labels
kubectl exec -it dns-test -- nslookup <svc>
kubectl exec -it dns-test -- wget -qO- http://<svc>
```

| `nslookup` | `wget` | Diagnosis |
|---|---|---|
| ✅ | ❌ | ⭐ **not DNS** — selector / endpoints / targetPort / NetworkPolicy |
| ❌ | ❌ | CoreDNS |

> ⭐ **Empty endpoints has exactly two causes:** labels don't match, **or** the Pods
> aren't **Ready**.

---

## 🧰 When `exec` can't help

```bash
kubectl debug -it <pod> --image=busybox:1.36 --target=<container>
kubectl debug <pod> -it --copy-to=<pod>-dbg --container=app -- sh   # ⭐ beats a crash loop
kubectl port-forward pod/<p> 8080:80      # ⭐ skips Service + Ingress entirely
kubectl top pods / top nodes
kubectl get pod <p> -o yaml
```

Use these when the image has **no shell** (distroless) or nothing stays running.

---

## ⚠️ Traps

- Events **expire after 1 hour** — capture them
- `kubectl get all` hides ConfigMaps, Secrets, Ingresses, PVCs
- `delete pod` "fixes" it and the bug returns tonight
- `CLOSE_WAIT`-style hangs are **your app**, not the network

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| First command, always? | `kubectl describe pod` → **Events** |
| CrashLoop, logs empty? | `--previous` |
| Service dead, Pods healthy? | `get endpoints` |
| Pod Pending? | **scheduler** — resources / selector / taint / PVC |
| No shell in the image? | `kubectl debug` |

---

⬅️ [S13](./13_Storage_HPA_Probes.md) · ➡️ [S15 · Helm](./15_Helm.md)
