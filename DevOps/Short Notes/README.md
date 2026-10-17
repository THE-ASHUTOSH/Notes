# ⚡ DevOps Short Notes

**Revision cards** — one per session. The kind of handwritten page you read the night
before, not the textbook you read the month before.

Each card is *one screen of recall*: the single core idea, the tables worth memorising,
the traps, and rapid-fire Q&A. When you need the *why*, the full note is one link away at
the top of every card.

> On the website these render on **ruled paper in a handwritten face** — the markdown is
> the same file you can read on GitHub.

---

## 🃏 The cards

| # | Card | The one line |
|---|---|---|
| **01** | [DevOps & Microservices](./01_DevOps_and_Microservices.md) | Microservices buy deployability; **automation pays the cost** |
| **02** | [Linux Fundamentals](./02_Linux_Fundamentals.md) | `/etc` config · `/var/log` logs · `/var/lib` state |
| **03** | [Shell Scripting](./03_Shell_Scripting.md) | `set -euo pipefail` + **always quote `"$var"`** |
| **04** | [Networking Fundamentals](./04_Networking_Fundamentals.md) | hosts = **2^host − 2**; and it's always DNS |
| **05** | [Git & GitHub](./05_Git_and_GitHub.md) | `revert` for pushed, `reset` for local, `reflog` saves you |
| **06** | [Docker Fundamentals](./06_Docker_Fundamentals.md) | Image = class, container = object, **PID 1 is life** |
| **07** | [Docker Images & Dockerfile](./07_Docker_Images_and_Dockerfile.md) | **Manifests before source code**; multi-stage wins |
| **08** | [Networking, Volumes & Compose](./08_Docker_Networking_Volumes_and_Compose.md) | Service name on the **container's own port** |
| **09** | [Kubernetes Fundamentals](./09_Kubernetes_Fundamentals.md) | Only the API server touches etcd; **controllers reconcile** |
| **10** | [Pods, ReplicaSets & Deployments](./10_Pods_ReplicaSets_Deployments.md) | **`Running` ≠ `Ready`**; five phases only |
| **11** | [Networking & Services](./11_Kubernetes_Networking_and_Services.md) | ⭐ **`kubectl get endpoints`** |
| **12** | [Ingress, ConfigMaps & Secrets](./12_Ingress_ConfigMaps_Secrets.md) | Secrets are **base64, not encrypted** |
| **13** | [Storage, HPA & Probes](./13_Storage_HPA_Probes.md) | **No requests + no Metrics Server ⇒ no HPA** |
| **14** | [Kubernetes Troubleshooting](./14_Kubernetes_Troubleshooting.md) | `CrashLoopBackOff` is a **symptom** |
| **15** | [Helm](./15_Helm.md) | `helm template` **before** `helm install` |
| **16** | [CI/CD & GitHub Actions](./16_CICD_and_GitHub_Actions.md) | A workflow is **WHEN + WHAT**; `needs:` is the gate |
| **17** | [Complete CI/CD & DevSecOps](./17_Complete_CICD_and_DevSecOps.md) | **A scan is not a gate** — `--exit-code 1` is |
| **18** | [Terraform & IaC](./18_Terraform_and_IaC.md) | Plan = **config + state + reality** |
| **19** | [Cloud & Terraform in Action](./19_Cloud_and_Terraform_in_Action.md) | Route table = **where**, SG = **allowed** |
| **20** | [Monitoring, Observability & GitOps](./20_Monitoring_Observability_GitOps.md) | Monitoring = **when**, observability = **why** |
| **21** | [Final DevOps Project](./21_Final_DevOps_Project.md) | **The chain is the deliverable** |

---

## 🧠 The ten things to walk in knowing

1. **Image = class, container = object.** Containers share the host **kernel**.
2. **Copy dependency manifests before source code** — the whole build-cache lesson.
3. **`CMD` is replaced, `ENTRYPOINT` is appended to.** Exec form, or signals die.
4. **Talk by service name on the container's own port** — never `localhost`, never the
   published port.
5. **`Running` ≠ `Ready`**, and a readiness failure **removes from endpoints without
   restarting**.
6. ⭐ **`kubectl get endpoints <svc>`** — empty means selector mismatch **or** Pods not Ready.
7. **Secrets are base64, not encrypted.** RBAC is the real protection. `echo -n`.
8. **No CPU `requests` + no Metrics Server ⇒ HPA never scales.**
9. **`helm upgrade --install … --atomic`** — and `--atomic` is only as good as your
   readiness probes.
10. **A scan without `--exit-code 1` is theatre.**

---

## 🔢 Numbers worth memorising

| | |
|---|---|
| Permissions | `r=4 w=2 x=1` → `755`, `644`, `600` |
| Usable hosts | `2^host_bits − 2` |
| Ports | 22 · 53 · 80 · 443 · 3306 · 5432 · 6379 · **6443** |
| NodePort range | **30000–32767** |
| Exit codes | 0 · 1 · **127** · **137** OOM · **143** SIGTERM |
| Privileged ports | **< 1024** = root only |
| AWS reserved IPs | **5 per subnet** → `/24` = 251 usable |
| Error budget | 99.9% ≈ **43 min/month** |

---

## ⚠️ The traps that catch everyone once

- `echo 'pw' | base64` encodes a **newline** → use **`echo -n`**
- `EXPOSE` **documents**; `-p` **publishes**
- `depends_on` waits for **start**, not readiness
- Editing a ConfigMap does nothing to running pods → **`kubectl rollout restart`**
- An Ingress **resource** without a **controller** does nothing, silently
- `terraform` `output` blocks take **no `type` argument**
- Creating an IGW makes nothing public — you need the **route table association** too
- Liveness probes that hit the database **restart your whole fleet** during a DB blip
- `docker compose down -v` and `terraform destroy` **delete data**

---

⬆️ Back to the [full DevOps notes](../README.md)
