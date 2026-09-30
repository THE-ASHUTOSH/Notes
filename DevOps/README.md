# DevOps Notes 🚀

Detailed, section-wise study notes for the DevOps course.
Each session is a **separate markdown file** — read them in order, or jump to a topic.

**Source material:** [Nency-Ravaliya/devops-heros](https://github.com/Nency-Ravaliya/devops-heros)
(session handwritten notes, PDF cheat sheets, interview Q&A, and all the example code —
Dockerfiles, shell scripts, Compose files and the 3-tier demo app).

---

## 📚 Sessions

| # | Session | Topics covered |
|---|---|---|
| **01** | [Introduction to DevOps & Microservices](./01_Introduction_to_DevOps_and_Microservices.md) | Monolith vs Microservices · What is DevOps · DevOps Lifecycle · CI/CD Overview · DevOps Tools (13 pillars) · DevSecOps (SAST/DAST/OWASP/Trivy) · GitOps · Job Roles · AI vs ML vs DL |
| **02** | [Linux Fundamentals](./02_Linux_Fundamentals.md) | Linux File System (FHS) · Essential Commands · Users & Permissions · Processes & Signals · Services (systemd) · Package Management · Disk & Storage · Networking commands · Logs & Basic Troubleshooting · SSH |
| **03** | [Shell Scripting](./03_Shell_Scripting.md) | Variables · Input · Command Substitution · Arguments · Conditions · Loops · Functions · Pipes & Redirection · Arrays · Exit Codes & Error Handling · Debugging · Automation scripts |
| **04** | [Networking Fundamentals](./04_Networking_Fundamentals.md) | OSI & TCP/IP models · IP Address & Classes · Subnet Mask · CIDR · Public vs Private IP · MAC/ARP · Ports · TCP vs UDP · DNS · HTTP/HTTPS · DHCP · Load Balancers & Firewalls · Troubleshooting ladder |
| **05** | [Git & GitHub](./05_Git_and_GitHub.md) | Git vs GitHub · The three areas · Repository & Commits · Branching · Merge vs Rebase · Merge Conflicts · Remotes · Pull Requests · Branching strategies · Tags & SemVer · Git in CI/CD |
| **06** | [Docker Fundamentals](./06_Docker_Fundamentals.md) | Containers vs VMs · namespaces & cgroups · Docker Architecture · Images · Containers · Container Lifecycle · Docker Hub & Registries · Commands · Debugging · Cleanup · Exit codes · Swarm intro |
| **07** | [Docker Images & Dockerfile](./07_Docker_Images_and_Dockerfile.md) | Dockerfile instructions · FROM/RUN/COPY/WORKDIR/ENV/EXPOSE · **CMD vs ENTRYPOINT** · `.dockerignore` · Layers & Build Cache · **Multi-stage Builds** · Image Optimization · Security best practices |
| **08** | [Docker Networking, Volumes & Compose](./08_Docker_Networking_Volumes_and_Compose.md) | Network drivers · Container-to-container communication · Port Mapping · Volumes · Bind Mounts · tmpfs · Docker Compose · Multi-container 3-tier app walkthrough |
| **09** | [Kubernetes Fundamentals](./09_Kubernetes_Fundamentals.md) | Why Kubernetes · Cluster architecture · Control Plane & Worker Nodes · API Server · Scheduler · Controller Manager · etcd · kubelet · kubectl · Declarative model · Namespaces |
| **10** | [Pods, ReplicaSets & Deployments](./10_Kubernetes_Pods_ReplicaSets_and_Deployments.md) | Pods · Pod lifecycle (12-scenario lab) · Labels & Selectors · ReplicaSets · Deployments · Scaling · Rolling Updates · Rollbacks · Blue-Green · Canary · Recreate · StatefulSets & DaemonSets |
| **11** | [Kubernetes Networking & Services](./11_Kubernetes_Networking_and_Services.md) | Pod networking · CoreDNS & FQDN · Service discovery · ClusterIP · NodePort · LoadBalancer · ExternalName · Headless · Selectors · `port` vs `targetPort` · `ndots:5` |
| **12** | [Ingress, ConfigMaps & Secrets](./12_Kubernetes_Ingress_ConfigMaps_and_Secrets.md) | ConfigMaps · Secrets & the base64 newline bug · Env injection · Ingress Controller vs resource · Host & path-based routing · `rewrite-target` · TLS termination |
| **13** | [Storage, HPA & Probes](./13_Kubernetes_Storage_HPA_and_Probes.md) | Volumes · emptyDir · hostPath · PV / PVC · Access modes · StorageClass & dynamic provisioning · HPA · Metrics Server · Liveness / Readiness / Startup probes · Mini-project |

---

## 🗺️ How the sessions connect

```
  01 DevOps & Microservices        ← the "why": architecture + culture + lifecycle
        │
        ├── 02 Linux               ← the ground everything runs on
        │      └── 03 Shell        ← automating that ground
        │
        ├── 04 Networking          ← how anything reaches anything
        │
        ├── 05 Git & GitHub        ← the source of truth that triggers everything
        │
        └── 06 Docker Fundamentals ← package the app
               └── 07 Dockerfile   ← build the image well
                      └── 08 Networking/Volumes/Compose  ← run a real multi-container app
                             │
                             ▼
        09 Kubernetes Fundamentals ← orchestrate them across many machines
               ├── 10 Pods / ReplicaSets / Deployments  ← run & release workloads
               ├── 11 Networking & Services             ← let them find each other
               ├── 12 Ingress / ConfigMaps / Secrets    ← expose & configure them
               └── 13 Storage / HPA / Probes            ← persist, scale & keep them healthy
                             │
                             ▼
                       (next) Troubleshooting → Helm → CI/CD → Terraform → Monitoring → GitOps
```

**The thread that runs through all thirteen:**
> Linux gives you processes, permissions, ports and logs. Shell automates them. Networking connects
> them. Git versions them. Docker packages them. Compose runs them together.
> Everything after this (Kubernetes, Helm, Terraform, CI/CD) is the same ideas at larger scale.

---

## 🔁 Concepts that reappear across sessions

| Concept | First seen | Comes back as |
|---|---|---|
| **Signals** (SIGTERM/SIGKILL) | 02 Linux processes | `docker stop` → exit codes **143** / **137** (06) |
| **Exit codes** (`$?`, 127, 137) | 03 Shell | Container exit codes (06); pipeline failures (CI/CD) |
| **`chmod +x`** | 02 Permissions | Running scripts (03); `RUN chmod +x entrypoint.sh` (07) |
| **Ports & `0.0.0.0`** | 04 Networking | `-p 8080:80`, `app.run(host="0.0.0.0")` (06–08) |
| **DNS** | 04 Networking | Docker service names (08); Kubernetes Service DNS |
| **Private IP ranges** | 04 Networking | `docker0` = `172.17.0.0/16` (08); VPC CIDRs (Terraform) |
| **`/var/lib`**, `/etc`, `/var/log` | 02 File system | `/var/lib/docker`, `/var/lib/mysql` volume mounts (08) |
| **`.gitignore`** | 05 Git | `.dockerignore` (07) |
| **Command substitution `$(...)`** | 03 Shell | `docker rm -f $(docker ps -aq)` (06) |
| **Redirection `>` vs `>>`** | 03 Shell | Log handling, cron output capture |
| **Health checks** | 06 Docker `HEALTHCHECK` | K8s liveness/readiness/startup probes |
| **Secrets hygiene** | 05 Git (`.env`) | 07 (never in `ENV`/`ARG`) → K8s Secrets, Vault |
| **Trivy image scanning** | 01 DevSecOps | 07 Security → CI/CD security gates |

---

## ⭐ Highest-value takeaways per session

| Session | If you only remember one thing |
|---|---|
| **01** | Microservices buy independent deployability at the cost of operational complexity — **DevOps automation is what pays that cost**. Lifecycle: Plan→Code→Build→Test→Release→Deploy→Operate→Monitor→(loop). |
| **02** | `/etc` (config), `/var/log` (logs), `/var/lib` (state). Permissions are `r=4 w=2 x=1`. `systemctl status` → `journalctl -u <svc>` is the start of every investigation. |
| **03** | `set -euo pipefail`, **always quote `"$var"`**, `>` overwrites while `>>` appends, and call a function **without** parentheses. |
| **04** | Network bits + host bits = 32; usable hosts = `2^host − 2`. Ports: 22/80/443/3306/5432/6379/6443. **TCP = reliable, UDP = fast.** When it breaks, it's usually DNS. |
| **05** | `merge` preserves history (safe on shared branches); `rebase` rewrites it (own branches only). `revert` for pushed commits, `reset` only for local ones. `reflog` saves you. |
| **06** | Image = class, container = object. Containers share the host **kernel** → MBs and seconds. A container lives only as long as **PID 1**. |
| **07** | **Copy dependency manifests before source code** for cache efficiency. `CMD` is overridable, `ENTRYPOINT` is appended to. Multi-stage builds shrink images dramatically. |
| **08** | Use a **user-defined network** and talk by **service name on the container's own port**. Anything you want to keep goes in a **named volume**. |
| **09** | Everything goes through the **API server**, and only it touches **etcd**. You declare **desired state**; controllers reconcile reality to match — self-healing is a free side effect. |
| **10** | Only five Pod **phases** exist (`CrashLoopBackOff` is a container *state*). **`Running != Ready`**. Rolling updates only advance when a new Pod passes **readiness**, and `maxUnavailable: 0` turns a bad deploy into a stalled one instead of an outage. |
| **11** | `nodePort` → `port` → `targetPort` is the packet's path (`containerPort` is just documentation). **`kubectl get endpoints` is the Service debugging command** — empty means a selector or readiness problem. |
| **12** | A Secret is **base64-encoded, not encrypted** — RBAC is the real protection, and always use `echo -n`. Editing a ConfigMap does nothing to running pods: **`kubectl rollout restart`**. |
| **13** | **PV = supply, PVC = demand**, and their lifecycle is independent of the Pod. **No CPU `requests` and no Metrics Server ⇒ no HPA.** **Readiness failure ≠ container restart.** |

---

## 🧭 Course roadmap (remaining sessions)

- Kubernetes Troubleshooting — `CrashLoopBackOff`, `ImagePullBackOff`, pending pods, DNS
- Helm — charts, `Chart.yaml`, `values.yaml`, templates, install/upgrade/rollback
- CI/CD & GitHub Actions — workflows, jobs, steps, runners, secrets, artifacts
- Complete CI/CD & DevSecOps — registry, K8s deploy, SAST, SCA, secret & image scanning, security gates
- Terraform & IaC — providers, resources, variables, outputs, `init/plan/apply/destroy`, state
- Cloud & Terraform in Action — IaaS/PaaS/SaaS, regions & AZs, VPC, subnets, route tables, security groups
- Monitoring, Observability & GitOps — metrics/logs/traces, Prometheus, Grafana, Argo CD
- Final DevOps Project — dockerize → CI/CD → scan → deploy → Helm → Ingress → HPA → monitoring

---

## 🔗 Key references

- Course repo — https://github.com/Nency-Ravaliya/devops-heros
- Docker docs — https://docs.docker.com
- Git cheat sheet — https://git-scm.com/cheat-sheet
- Pro Git (free book) — https://git-scm.com/book/en/v2
- Kubernetes docs — https://kubernetes.io/docs/
- Trivy — https://trivy.dev/
- OWASP Top 10 — https://owasp.org/www-project-top-ten/
