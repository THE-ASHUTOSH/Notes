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
                       (next) Kubernetes → Helm → CI/CD → Terraform → Monitoring → GitOps
```

**The thread that runs through all eight:**
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

---

## 🧭 Course roadmap (remaining sessions)

- Kubernetes Fundamentals — architecture, control plane, API server, scheduler, etcd, kubelet, kubectl
- Kubernetes Pods, ReplicaSets & Deployments — scaling, rolling updates, rollbacks
- Kubernetes Networking & Services — ClusterIP, NodePort, LoadBalancer, DNS, `port` vs `targetPort`
- Kubernetes Ingress, ConfigMaps & Secrets — host/path routing, TLS, env vars
- Kubernetes Storage, HPA & Probes — PV/PVC, StorageClass, metrics-server, liveness/readiness/startup
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
