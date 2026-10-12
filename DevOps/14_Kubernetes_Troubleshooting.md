# Session 14 — Kubernetes Troubleshooting 🩺

> **Topics:** `kubectl get` · `kubectl describe` · `kubectl logs` · `kubectl exec` · Events ·
> CrashLoopBackOff · ImagePullBackOff · Pending Pods · Service & DNS Troubleshooting
>
> 📁 Repo: `session-14-kubernetes-troubleshooting/` — nine numbered folders, each with a
> **broken-pod / fixed-pod** pair, plus a `mini-project` challenge.

This session answers one question: *"My app isn't working. How do I find out why?"*
Everything in sessions 9–13 was about **making things run**. This one is about **what to do
when they don't** — and the answer is a fixed, repeatable process, not guesswork.

---

## 📑 Table of Contents

1. [The Troubleshooting Mindset](#-the-troubleshooting-mindset)
2. [The Five Commands](#-the-five-commands)
3. [`kubectl get` — What is happening?](#-kubectl-get--what-is-happening)
4. [`kubectl describe` — Why is it happening?](#-kubectl-describe--why-is-it-happening)
5. [`kubectl logs` — What is the app saying?](#-kubectl-logs--what-is-the-app-saying)
6. [`kubectl exec` — What does it look like from inside?](#-kubectl-exec--what-does-it-look-like-from-inside)
7. [Events — What did Kubernetes try?](#-events--what-did-kubernetes-try)
8. [CrashLoopBackOff](#-crashloopbackoff)
9. [ImagePullBackOff](#-imagepullbackoff)
10. [Pending Pods](#-pending-pods)
11. [Service & DNS Troubleshooting](#-service--dns-troubleshooting)
12. [Beyond the lab: OOMKilled, Evicted & friends](#-beyond-the-lab-oomkilled-evicted--friends)
13. [`kubectl debug` & ephemeral containers](#-kubectl-debug--ephemeral-containers)
14. [Symptom → First Command (cheat table)](#-symptom--first-command-cheat-table)
15. [Key Terms Recap](#-key-terms-recap)
16. [Session Takeaways](#-session-takeaways)

---

## 🧠 The Troubleshooting Mindset

The single biggest mistake is **deleting the Pod and hoping**. A restart hides the evidence
and the problem comes back at 3am. Follow the loop instead:

```
   PROBLEM
      │
      ▼
 1. Observe         kubectl get pods
      │
      ▼
 2. Check status    STATUS? READY? RESTARTS?
      │
      ▼
 3. Check details   kubectl describe pod <name>
      │
      ▼
 4. Check events    (bottom of describe, or kubectl get events)
      │
      ▼
 5. Check logs      kubectl logs <name> [--previous]
      │
      ▼
 6. Go inside       kubectl exec -it <name> -- sh
      │
      ▼
 7. Test network    nslookup / wget / curl
      │
      ▼
 8. ROOT CAUSE  ──▶  FIX  ──▶  VERIFY
```

⭐ **The direction of travel is always outside-in:** cluster → object → container → application.
Each step narrows the search space. You stop as soon as a step tells you the answer.

---

## 🖐️ The Five Commands

| Command | Question it answers | Scope |
|---|---|---|
| `kubectl get` | **What** is happening? | Quick status, many objects |
| `kubectl describe` | **Why** is it happening? | One object, full detail + events |
| `kubectl logs` | What is the **application** saying? | Inside the container, stdout/stderr |
| `kubectl exec` | What does it look like **from inside**? | Live shell in a running container |
| `kubectl events` | What did **Kubernetes** try to do? | Control-plane activity log |

⭐ `get` and `describe` are about **Kubernetes' view**. `logs` and `exec` are about the
**application's view**. Most real incidents need one of each.

---

## 🔍 `kubectl get` — What is happening?

```bash
kubectl apply -f 01-kubectl-get/pod.yaml     # pod/get-demo created
kubectl get pods
```

```text
NAME       READY   STATUS    RESTARTS   AGE
get-demo   1/1     Running   0          10s
```

| Column | Meaning | What it tells you when it's wrong |
|---|---|---|
| **NAME** | Pod name | — |
| **READY** | `ready / total` containers | `0/1` while `Running` ⇒ **readiness probe failing** |
| **STATUS** | Phase, or a container-level reason | The headline symptom |
| **RESTARTS** | Container restart count | Climbing ⇒ crash loop |
| **AGE** | Time since creation | A very young Pod that keeps resetting age ⇒ recreated, not restarted |

### Variants worth memorising

```bash
kubectl get pods -o wide            # + Pod IP and NODE  ← is it even scheduled?
kubectl get pods -w                 # watch changes live
kubectl get all                     # pods, services, deployments, replicasets
kubectl get pods --show-labels      # labels — critical for Service debugging
kubectl get pods -A                 # every namespace
kubectl get nodes                   # is the cluster itself healthy?
```

> ⚠️ `kubectl get all` is a lie by omission — it does **not** include ConfigMaps, Secrets,
> Ingresses, PVCs or CRDs. Don't use it to prove something doesn't exist.

**`get` tells you *what*. It never tells you *why*.** That is the next command's job.

---

## 📋 `kubectl describe` — Why is it happening?

```bash
kubectl describe pod describe-demo
```

Sections, in the order you should read them when debugging:

| Section | Look for |
|---|---|
| **Events** (bottom) | ⭐ Read this **first**. `Warning` lines explain almost everything. |
| **Containers → State / Last State** | `Running`, `Waiting (reason)`, `Terminated (exit code)` |
| **Containers → Restart Count** | Crash loop confirmation |
| **Conditions** | `PodScheduled`, `Initialized`, `ContainersReady`, `Ready` — the first `False` is your lead |
| **Node** | Blank ⇒ never scheduled ⇒ a scheduler problem, not an app problem |
| **Volumes / Mounts** | Missing ConfigMap/Secret/PVC shows up here and in Events |

```text
Containers:
  nginx:
    Image:  nginx:1.27
    State:  Running
    Ready:  True
```

Works on every object, not just Pods:

```bash
kubectl describe deployment <name>   # rollout status, conditions, replica math
kubectl describe service <name>      # ⭐ selector + endpoints
kubectl describe node <name>         # capacity, allocated resources, taints, pressure
kubectl describe pvc <name>          # why storage is still Pending
```

⭐ **Habit to build:** the instant you see `Pending`, `CrashLoopBackOff` or `ImagePullBackOff`,
your next keystrokes are `kubectl describe pod <name>` — *not* `kubectl delete pod`.

---

## 📜 `kubectl logs` — What is the app saying?

Kubernetes exposes whatever the container writes to **stdout/stderr**.

```bash
kubectl logs logs-demo                  # current container
kubectl logs -f logs-demo               # follow (Ctrl+C to stop)
kubectl logs logs-demo --previous       # ⭐ the container that just died
kubectl logs logs-demo -c app           # pick a container in a multi-container Pod
kubectl logs --tail=50 logs-demo        # last 50 lines
kubectl logs --since=10m logs-demo      # time-bounded
kubectl logs -l app=web --all-containers # ⭐ all Pods matching a label at once
```

The repo's `03-kubectl-logs/pod.yaml` is a busybox Pod that prints a startup sequence then
loops a heartbeat — exactly the shape of a real app log:

```text
Application started
Connecting to database...
Database connection successful
Application is running
Application is healthy        ← repeats every 5s
```

⭐ **`--previous` is the single most under-used debugging flag.** In a `CrashLoopBackOff` the
container you're looking at is the *new* one, which may not have produced output yet. The
error you need was printed by the one that already died.

> 💡 **Why stdout?** This is the [12-factor](https://12factor.net/logs) rule: a container
> should treat logs as an event stream and write to stdout, never to a file inside the
> container. If your app logs to `/var/log/app.log`, `kubectl logs` shows nothing and the logs
> vanish with the container.

---

## 🚪 `kubectl exec` — What does it look like from inside?

```bash
kubectl exec -it exec-demo -- bash          # interactive shell
kubectl exec exec-demo -- hostname          # one-shot command, no shell
kubectl exec exec-demo -- cat /etc/hosts
kubectl exec exec-demo -- ls /usr/share/nginx/html
kubectl exec -it exec-demo -c app -- sh     # choose the container
```

The classic use: **split "is the app broken?" from "is the networking broken?"**

```bash
kubectl exec -it web-pod -- curl localhost
```

| Result | Conclusion |
|---|---|
| HTML comes back | App is fine ⇒ look at Service, selector, `targetPort`, DNS, NetworkPolicy |
| Connection refused | App isn't listening ⇒ wrong port, or bound to `127.0.0.1` instead of `0.0.0.0` |

> ⚠️ **`exec` needs a running container.** In a crash loop there may be no stable container to
> enter — the command will fail or the shell will die under you. Use `logs --previous`,
> `describe`, or `kubectl debug` instead.

> ⚠️ Many hardened/distroless images have **no shell at all** (`sh: not found`). That's a
> security feature, not a bug — use `kubectl debug` (below).

---

## 📣 Events — What did Kubernetes try?

Events are the control plane's activity log: *"I tried to do X, and here's what happened."*

```bash
kubectl get events
kubectl get events --sort-by=.lastTimestamp         # ⭐ chronological
kubectl get events --field-selector type=Warning    # ⭐ cut the noise during an incident
kubectl events --watch                              # newer, nicer subcommand
kubectl events --for pod/events-demo                # scoped to one object
kubectl get events -A --sort-by=.lastTimestamp      # cluster-wide
```

A healthy Pod's event trail:

```text
TYPE     REASON      MESSAGE
Normal   Scheduled   Successfully assigned default/events-demo to minikube
Normal   Pulling     Pulling image "nginx:1.27"
Normal   Pulled      Successfully pulled image
Normal   Created     Created container nginx
Normal   Started     Started container nginx
```

Reasons that are really diagnoses:

| Reason | Means |
|---|---|
| `FailedScheduling` | No node will take this Pod — the message says exactly why |
| `Failed` / `ErrImagePull` | Image could not be pulled |
| `BackOff` | Restarting too fast; Kubernetes is throttling |
| `Unhealthy` | A liveness or readiness probe failed |
| `FailedMount` | ConfigMap / Secret / PVC missing or not bound |
| `Evicted` | Node ran out of a resource and reclaimed the Pod |
| `OOMKilled` *(container state)* | Container exceeded its memory limit |

> ⚠️ **Events expire.** Default TTL is **1 hour**. If an incident happened overnight, the
> events are gone — which is one reason production clusters ship events to a logging backend.
> This is also why "it was fine when I checked" is not evidence.

---

## 💥 CrashLoopBackOff

```bash
kubectl apply -f 06-crashloopbackoff/broken-pod.yaml
kubectl get pod crash-demo
```

```text
NAME         READY   STATUS             RESTARTS
crash-demo   0/1     CrashLoopBackOff   3
```

### What it actually is

```
start ──▶ crash ──▶ restart ──▶ crash ──▶ Kubernetes waits ──▶ try again
                                               │
                                     backoff: 10s, 20s, 40s … capped at 5 min
```

⭐ **`CrashLoopBackOff` is a *symptom*, never a root cause.** It only says "this container keeps
dying". It also isn't a Pod *phase* — the phase is still `Running`; this is a container
**waiting reason** (see [Session 10](./10_Kubernetes_Pods_ReplicaSets_and_Deployments.md)).

### The broken Pod

```yaml
command:
  - sh
  - -c
  - |
    echo "Application starting..."
    echo "Something went wrong!"
    exit 1          # ← exit code 1: the container's main process failed
```

### Investigation

```bash
kubectl describe pod crash-demo      # State / Last State / Restart Count / Events
kubectl logs crash-demo              # "Application starting... / Something went wrong!"
kubectl logs crash-demo --previous   # ⭐ when the current container has no output yet
```

### The fix

```yaml
command:
  - sh
  - -c
  - |
    echo "Application starting..."
    echo "Application is healthy"
    sleep 3600      # ← PID 1 stays alive
```

```bash
kubectl delete pod crash-demo
kubectl apply -f 06-crashloopbackoff/fixed-pod.yaml   # 1/1 Running
```

### Real-world causes, ranked

| Cause | Tell-tale sign |
|---|---|
| Application exception on startup | Stack trace in `logs --previous` |
| Missing env var / config | App logs "undefined"/"nil"; `FailedMount` in events |
| Wrong `command` / `args` | `exec: "xyz": not found`, exit code **127** |
| **Container finished its work** | Exit code **0** but `restartPolicy: Always` ⇒ use a **Job** |
| Failed dependency (DB not up) | "connection refused" to another service |
| **Liveness probe too aggressive** | Restarts at a *regular interval*; `Unhealthy` events |
| OOM | `Last State: Terminated, Reason: OOMKilled`, exit **137** |
| Permission denied on a mounted volume | `EACCES`; fix with `securityContext.fsGroup` |

> ⭐ Exit codes carry over straight from [Session 6](./06_Docker_Fundamentals.md):
> **0** = clean exit, **1** = app error, **127** = command not found,
> **137** = SIGKILL/OOM, **143** = SIGTERM.

---

## 🖼️ ImagePullBackOff

```bash
kubectl apply -f 07-imagepullbackoff/broken-pod.yaml
```

```text
NAME         READY   STATUS           RESTARTS
image-demo   0/1     ErrImagePull     0      ← first attempt failed
image-demo   0/1     ImagePullBackOff 0      ← now retrying with backoff
```

`ErrImagePull` is the **first failure**; `ImagePullBackOff` is the **throttled retry state**.
Same root problem.

The broken manifest:

```yaml
image: nginx:this-image-does-not-exist      # tag doesn't exist
```

```bash
kubectl describe pod image-demo    # Events → "Failed to pull image ..."
```

The events message distinguishes the causes — read it rather than guessing:

| Cause | Message contains |
|---|---|
| Typo in image name | `repository does not exist` |
| Non-existent tag | `manifest unknown` / `not found` |
| Private registry, no credentials | `unauthorized` / `authentication required` |
| Registry unreachable / DNS | `dial tcp … i/o timeout` |
| Rate-limited (Docker Hub anonymous pulls) | `toomanyrequests` |
| Wrong architecture | `no matching manifest for linux/amd64` |

**Fix for private registries** — create a pull secret and reference it:

```bash
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io --docker-username=<u> --docker-password=<token>
```

```yaml
spec:
  imagePullSecrets:
    - name: regcred
```

> ⚠️ `imagePullPolicy: Always` + a local-only image (e.g. one you just built into minikube)
> gives `ImagePullBackOff` too. Use `IfNotPresent` for locally-built images.
> Note that `:latest` **defaults** to `Always` — another reason never to use `:latest`.

---

## ⏳ Pending Pods

```text
NAME           READY   STATUS    RESTARTS   AGE
pending-demo   0/1     Pending   0          10s
```

⭐ `Pending` means **the Pod has not been scheduled onto a node yet** (or its images haven't
started downloading). Nothing is wrong with your *application* — the problem is upstream.
Confirm with `kubectl get pod -o wide`: **`NODE` is `<none>`**.

The broken manifest asks for a node that doesn't exist:

```yaml
spec:
  nodeSelector:
    kubernetes.io/hostname: node-that-does-not-exist
```

```bash
kubectl describe pod pending-demo   # Conditions: PodScheduled=False
                                    # Events: Warning FailedScheduling …
kubectl get nodes                   # only "minikube" exists
```

Remove the selector and it schedules immediately.

### Every reason a Pod stays Pending

| Cause | How to confirm |
|---|---|
| **Insufficient CPU / memory** ⭐ most common | `kubectl describe node` → *Allocated resources*; event says `Insufficient cpu` |
| Node selector doesn't match any node | `kubectl get nodes --show-labels` |
| Affinity / anti-affinity unsatisfiable | Event text names the predicate |
| **Taints with no matching toleration** | `kubectl describe node \| grep Taints` |
| **PVC unbound** | `kubectl get pvc` shows `Pending`; no StorageClass or no matching PV |
| Not enough node ports / IP exhaustion | Event text |
| Cluster is simply full | Scale the node pool, or the **Cluster Autoscaler** adds a node |

> 💡 The autoscaler trio from [Session 13](./13_Kubernetes_Storage_HPA_and_Probes.md) matters
> here: **HPA** adds Pods, but if no node can hold them they go `Pending` — and only the
> **Cluster Autoscaler** can fix that by adding nodes.

---

## 🌐 Service & DNS Troubleshooting

This is the richest lab in the session, and the most common real-world failure: **everything
looks healthy, but traffic doesn't flow.**

### The chain that has to hold

```
Pod labels  ──match──▶  Service selector  ──produces──▶  Endpoints
                                                              │
                                                              ▼
                                                    ClusterIP  ──▶  DNS name
                                                                    service.ns.svc.cluster.local
```

Break **any** link and you get a Service that exists, Pods that are `Running`, and zero traffic.

### Walkthrough

```bash
kubectl apply -f 09-service-dns-troubleshooting/deployment.yaml   # 2 nginx pods, label app=web
kubectl apply -f 09-service-dns-troubleshooting/service.yaml
kubectl get service
kubectl describe service web-service     # Selector / Port / TargetPort / Endpoints
kubectl get endpoints web-service        # ⭐ THE command
```

Healthy:

```text
NAME          ENDPOINTS
web-service   10.244.0.5:80,10.244.0.6:80
```

Broken:

```text
NAME             ENDPOINTS
broken-service   <none>              ← selector matched nothing
```

> 🐛 **Bug in the repo's own `service.yaml`:** its selector is `app: web-ahsgdf`, while the
> Deployment labels Pods `app: web`. So `web-service` also comes up with `<none>` endpoints —
> the README's "you should see Pod IPs" step fails as written. Change the selector to
> `app: web` (or treat it as a free extra debugging exercise, which is how it reads).
> `09-service-dns-troubleshooting/pod.yaml` is also a stray copy of the logs demo and is unused.

### Testing DNS from inside the cluster

```bash
kubectl apply -f 09-service-dns-troubleshooting/dns-test-pod.yaml   # dnsutils image

kubectl exec -it dns-test -- nslookup web-service
kubectl exec -it dns-test -- nslookup web-service.default.svc.cluster.local
kubectl exec dns-test -- wget -qO- http://web-service
kubectl exec -it dns-test -- cat /etc/resolv.conf
```

DNS naming (recap from [Session 11](./11_Kubernetes_Networking_and_Services.md)):

```
<service>.<namespace>.svc.cluster.local
```

### ⭐ The decisive diagnostic

| `nslookup` | `wget`/`curl` | Diagnosis |
|---|---|---|
| ✅ works | ✅ works | Not a cluster-networking problem — look at the app or the client |
| ✅ works | ❌ fails | **DNS is fine.** Selector / endpoints / `targetPort` / NetworkPolicy / app not listening |
| ❌ fails | ❌ fails | Real DNS problem — check CoreDNS |

> ⚠️ **Do not blame DNS first.** A resolvable name with no endpoints behind it fails at the
> *connection* step, not the *lookup* step, and the two look identical from the app's logs.

### Checking CoreDNS

```bash
kubectl get pods -n kube-system                      # coredns-xxxxx should be Running
kubectl logs -n kube-system -l k8s-app=kube-dns      # CoreDNS logs
kubectl get svc -n kube-system kube-dns              # the cluster DNS ClusterIP
```

### The 7-step Service checklist

```bash
1. kubectl get pods                       # are they Running AND Ready?
2. kubectl get pods --show-labels         # what labels do they actually have?
3. kubectl describe service <name>        # what selector does the Service want?
4. kubectl get endpoints <name>           # ⭐ empty = the smoking gun
5. kubectl exec <pod> -- nslookup <name>  # DNS
6. kubectl exec <pod> -- wget -qO- <name> # connectivity
7. kubectl get pods -n kube-system        # CoreDNS healthy?
```

> ⭐ **Empty endpoints has exactly two causes:** the selector doesn't match any Pod's labels,
> **or** the matching Pods aren't `Ready`. A Pod that fails its readiness probe is silently
> removed from the endpoint list — `Running` is not `Ready`.

---

## 🧯 Beyond the lab: OOMKilled, Evicted & friends

Not in the repo, but you will hit all of these in a real cluster.

### `OOMKilled` — exit code 137

```bash
kubectl describe pod <name> | grep -A4 "Last State"
```

```text
Last State:  Terminated
  Reason:    OOMKilled
  Exit Code: 137
```

The container exceeded its **memory `limit`** and the kernel's OOM killer took it. Memory is
**incompressible** — unlike CPU, which is merely throttled, exceeding memory is fatal.
Fix: raise the limit, or fix the leak. (Also check the app's own heap settings — a JVM that
doesn't know its cgroup limit will happily grow past it.)

### `Evicted`

The **node** ran out of memory/disk and the kubelet reclaimed Pods to save itself.

```bash
kubectl get pods -A --field-selector status.phase=Failed
kubectl describe node <node> | grep -i pressure   # MemoryPressure / DiskPressure
```

Pods with **no resource `requests`** are evicted first (QoS class `BestEffort`). Setting
`requests` == `limits` gives `Guaranteed` — the last to be evicted.

### Node `NotReady`

```bash
kubectl get nodes
kubectl describe node <node>      # Conditions + Taints
```

Usually the kubelet, the container runtime or the CNI plugin is down on that box. Every Pod
on the node goes `Terminating`/unknown after the eviction timeout (~5 min).

### `Terminating` forever

A finalizer or a stuck volume detach. Find the finalizer first:

```bash
kubectl get pod <name> -o jsonpath='{.metadata.finalizers}'
kubectl delete pod <name> --grace-period=0 --force     # last resort, leaks resources
```

### Other quick wins

```bash
kubectl top pods                     # actual CPU/memory (needs Metrics Server)
kubectl top nodes
kubectl rollout status deploy/<name> # is the rollout stuck?
kubectl rollout undo deploy/<name>   # ⭐ fastest incident mitigation
kubectl get pod <name> -o yaml       # the full truth, including status
kubectl api-resources                # what kinds exist in this cluster
```

---

## 🐞 `kubectl debug` & ephemeral containers

When the container has **no shell**, or is **crash-looping** so `exec` can't attach:

```bash
# Attach a debug container (with tools) to a RUNNING pod, sharing its namespaces
kubectl debug -it <pod> --image=busybox:1.36 --target=<container>

# Copy a crashing pod, swap in a shell as the entrypoint, and poke around
kubectl debug <pod> -it --copy-to=<pod>-dbg --container=app -- sh

# Get a root shell on the NODE itself
kubectl debug node/<node> -it --image=busybox:1.36
```

`--target` shares the **process namespace** so you can see the real app's processes and
`/proc`. The `--copy-to` form is the one that beats a crash loop: the copy doesn't run the
broken command, so it stays up long enough to inspect config, env and mounts.

Also useful:

```bash
kubectl port-forward pod/<name> 8080:80     # bypass Service + Ingress entirely
kubectl cp <pod>:/path/to/file ./file       # pull a file out for inspection
```

> ⭐ `port-forward` is the fastest way to answer "is this the app or the networking?" —
> it goes straight to the Pod and skips Service, Ingress and DNS completely.

---

## 🗺️ Symptom → First Command (cheat table)

| You see | Almost certainly | Run this first |
|---|---|---|
| `Pending`, `NODE: <none>` | Scheduling: resources, selector, taint, PVC | `kubectl describe pod` → Events |
| `ContainerCreating` (stuck) | Volume mount / Secret / ConfigMap / CNI | `kubectl describe pod` → Events |
| `ErrImagePull` / `ImagePullBackOff` | Image name, tag, or registry auth | `kubectl describe pod` → Events |
| `CrashLoopBackOff` | App exits on startup | `kubectl logs --previous` |
| `Running` but `0/1` READY | Readiness probe failing | `kubectl describe pod` → Events (`Unhealthy`) |
| `OOMKilled` / exit 137 | Memory limit too low or a leak | `kubectl top pod`, raise limit |
| `Evicted` | Node under memory/disk pressure | `kubectl describe node` → Conditions |
| `Completed` + restarts | Job-shaped workload under a Deployment | Use a **Job** instead |
| Service returns nothing | Selector/label mismatch, or Pods not Ready | ⭐ `kubectl get endpoints <svc>` |
| DNS name won't resolve | CoreDNS | `kubectl logs -n kube-system -l k8s-app=kube-dns` |
| Ingress 404 / 503 | Wrong host/path, or Service has no endpoints | `kubectl describe ingress`, then endpoints |
| Node `NotReady` | kubelet / runtime / CNI down on that node | `kubectl describe node` |

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Event** | Control-plane record of an attempted action; TTL **1 hour** by default |
| **`CrashLoopBackOff`** | Container waiting-reason: repeatedly starting and failing, with exponential backoff (capped at 5 min) |
| **`ErrImagePull` / `ImagePullBackOff`** | First pull failure / throttled retry state for the same problem |
| **`Pending`** | Pod accepted by the API server but not yet scheduled or not yet pulling |
| **Endpoints** | The list of Pod IP:port behind a Service. Built from selector ∩ *Ready* Pods |
| **`FailedScheduling`** | Scheduler event; its message states the exact unsatisfied constraint |
| **`OOMKilled`** | Container exceeded its memory limit; exit code 137 |
| **Evicted** | kubelet killed the Pod to relieve node resource pressure |
| **Ephemeral container** | Temporary container injected into a running Pod by `kubectl debug` |
| **`--previous`** | Flag to read logs from the container instance that just died |
| **QoS class** | `Guaranteed` / `Burstable` / `BestEffort` — determines eviction order |

---

## 🎯 Session Takeaways

1. ⭐ **Follow the loop, don't guess:** `get` → `describe` → Events → `logs` → `exec` → test → fix → verify.
2. ⭐ **`CrashLoopBackOff` and `ImagePullBackOff` are symptoms**, not causes. The cause is in Events or in `logs --previous`.
3. **Read Events first.** The bottom of `kubectl describe pod` solves more incidents than any other output — and they expire after an hour, so capture them.
4. ⭐ **`kubectl get endpoints <svc>` is the Service debugging command.** Empty = selector mismatch **or** Pods not Ready.
5. **`Running` ≠ `Ready`.** A `0/1 Running` Pod is a readiness-probe problem and is already out of the Service's endpoint list.
6. **`Pending` is a scheduler problem, not an app problem.** Check `-o wide` for `NODE: <none>`, then node resources, selectors, taints and PVCs.
7. **DNS is rarely the culprit.** If `nslookup` works but `wget` doesn't, the problem is downstream of DNS.
8. **Never `kubectl delete pod` to "fix" something** until you've captured the evidence — the restart destroys it and the bug returns.
9. **Exit codes are the same as Docker's:** 0 clean, 1 app error, 127 command not found, 137 OOM/SIGKILL, 143 SIGTERM.
10. **`kubectl debug` and `port-forward`** handle the two cases plain `exec` can't: no shell in the image, and nothing stays running.

---

## 🔗 References

- Debug Running Pods — https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/
- Debug Pods (troubleshooting guide) — https://kubernetes.io/docs/tasks/debug/debug-application/
- Debug Services — https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/
- DNS troubleshooting — https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/
- Pod Lifecycle & phases — https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- kube-scheduler — https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/
- Node-pressure eviction — https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/
- Ephemeral containers — https://kubernetes.io/docs/concepts/workloads/pods/ephemeral-containers/
- kubectl reference — https://kubernetes.io/docs/reference/kubectl/

---

## ➡️ Next

[Session 15 — Helm](./15_Helm.md) — stop hand-editing YAML for every environment and start
packaging it.
