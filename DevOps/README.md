# DevOps Notes 🚀

Complete, section-wise study notes for the **21-session DevOps & Cloud** course.
One markdown file per session — read them in order, or jump to a topic.

**Source material:** [Nency-Ravaliya/devops-heros](https://github.com/Nency-Ravaliya/devops-heros)
— every session folder, README, PDF, shell script, Dockerfile, Compose file, Kubernetes
manifest, Helm chart, Terraform configuration and demo application in the repo, plus the
official course syllabus. Where the source material is thin, wrong or inconsistent, the notes
say so explicitly and give the correct version.

> 🖥️ There's also a **browsable website** for these notes — see [Reading as a website](#-reading-as-a-website).

---

## 📚 Sessions

| # | Session | Topics covered |
|---|---|---|
| **01** | [Introduction to DevOps & Microservices](./01_Introduction_to_DevOps_and_Microservices.md) | Monolith vs Microservices · What is DevOps · DevOps Lifecycle · CI/CD Overview · DevOps Tools (13 pillars) · DevSecOps · GitOps · Job Roles |
| **02** | [Linux Fundamentals](./02_Linux_Fundamentals.md) | File System (FHS) · Essential Commands · Users & Permissions · Processes & Signals · systemd · Package Management · Disk · Logs & Troubleshooting · SSH |
| **03** | [Shell Scripting](./03_Shell_Scripting.md) | Variables · Input · Command Substitution · Arguments · Conditions · Loops · Functions · Pipes & Redirection · Arrays · Exit Codes · Debugging · Automation |
| **04** | [Networking Fundamentals](./04_Networking_Fundamentals.md) | OSI & TCP/IP · IP Classes · Subnet Mask · CIDR · Public vs Private · MAC/ARP · Ports · TCP vs UDP · DNS · HTTP/HTTPS · DHCP · Load Balancers · Troubleshooting ladder |
| **05** | [Git & GitHub](./05_Git_and_GitHub.md) | Git vs GitHub · The three areas · Commits · Branching · Merge vs Rebase · Conflicts · Remotes · Pull Requests · Branching strategies · Tags & SemVer |
| **06** | [Docker Fundamentals](./06_Docker_Fundamentals.md) | Containers vs VMs · namespaces & cgroups · Architecture · Images · Containers · Lifecycle · Registries · Debugging · Cleanup · Exit codes · Swarm |
| **07** | [Docker Images & Dockerfile](./07_Docker_Images_and_Dockerfile.md) | Dockerfile instructions · **CMD vs ENTRYPOINT** · `.dockerignore` · Layers & Build Cache · **Multi-stage Builds** · Image Optimization · Security |
| **08** | [Docker Networking, Volumes & Compose](./08_Docker_Networking_Volumes_and_Compose.md) | Network drivers · Container-to-container comms · Port Mapping · Volumes · Bind Mounts · tmpfs · Compose · 3-tier app walkthrough |
| **09** | [Kubernetes Fundamentals](./09_Kubernetes_Fundamentals.md) | Why Kubernetes · Cluster architecture · Control Plane & Nodes · API Server · Scheduler · Controller Manager · etcd · kubelet · kubectl · Namespaces · RBAC |
| **10** | [Pods, ReplicaSets & Deployments](./10_Kubernetes_Pods_ReplicaSets_and_Deployments.md) | Pods & lifecycle · Labels & Selectors · ReplicaSets · Deployments · Scaling · Rolling Updates · Rollbacks · Blue-Green · Canary · StatefulSets · DaemonSets · Jobs |
| **11** | [Kubernetes Networking & Services](./11_Kubernetes_Networking_and_Services.md) | Pod networking · CNI · CoreDNS & FQDN · Service discovery · ClusterIP · NodePort · LoadBalancer · ExternalName · Headless · `port` vs `targetPort` |
| **12** | [Ingress, ConfigMaps & Secrets](./12_Kubernetes_Ingress_ConfigMaps_and_Secrets.md) | ConfigMaps · Secrets & the base64 trap · Env injection · Ingress Controller vs resource · Host & path routing · `rewrite-target` · TLS termination |
| **13** | [Storage, HPA & Probes](./13_Kubernetes_Storage_HPA_and_Probes.md) | Volumes · emptyDir · hostPath · PV / PVC · Access modes · StorageClass · HPA · Metrics Server · Liveness / Readiness / Startup probes · Autoscaler trio |
| **14** | [Kubernetes Troubleshooting](./14_Kubernetes_Troubleshooting.md) | `get` / `describe` / `logs` / `exec` · Events · **CrashLoopBackOff** · **ImagePullBackOff** · Pending Pods · Service & DNS debugging · OOMKilled · `kubectl debug` |
| **15** | [Helm](./15_Helm.md) | Chart · Release · Values · Chart structure · `Chart.yaml` · `values.yaml` · Go templates · `_helpers.tpl` · Install & Upgrade · **Rollback** · `--atomic` · Dependencies |
| **16** | [CI/CD & GitHub Actions](./16_CICD_and_GitHub_Actions.md) | CI vs CD · Pipeline concepts · Workflows & Triggers · Jobs & Steps · `needs:` · Runners · Matrix builds · Secrets · Artifacts · Caching · Contexts · OIDC |
| **17** | [Complete CI/CD & DevSecOps](./17_Complete_CICD_and_DevSecOps.md) | Docker build in pipeline · GHCR · **SAST** · **SCA** · Secret scanning · **Image scanning (Trivy)** · **Security gates** · Kubernetes deployment from CI |
| **18** | [Terraform & Infrastructure as Code](./18_Terraform_and_IaC.md) | What is IaC · Terraform architecture · Providers · Resources · Variables · Outputs · `init`/`plan`/`apply`/`destroy` · **State** · Remote backends · Modules |
| **19** | [Cloud & Terraform in Action](./19_Cloud_and_Terraform_in_Action.md) | IaaS/PaaS/SaaS · Regions & AZs · **VPC** · Subnets · Route Tables · Internet Gateway · **Security Groups** · NACLs · NAT · Provisioning a VPC with Terraform |
| **20** | [Monitoring, Observability & GitOps](./20_Monitoring_Observability_and_GitOps.md) | Monitoring vs Observability · Metrics/Logs/Traces · **Prometheus** · PromQL · **Grafana** · Golden Signals · SLOs · **GitOps** · **Argo CD** · Self-healing |
| **21** | [Final DevOps Project](./21_Final_DevOps_Project.md) | TaskBoard capstone: app → Git → CI → Docker → Trivy → GHCR → Terraform (VPC+EKS) → Helm → Ingress → HPA → Prometheus/Grafana → Troubleshooting |

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
                      └── 08 Networking / Volumes / Compose   ← a real multi-container app
                             │
                             ▼
        09 Kubernetes Fundamentals ← orchestrate across many machines
               ├── 10 Pods / ReplicaSets / Deployments  ← run & release workloads
               ├── 11 Networking & Services             ← let them find each other
               ├── 12 Ingress / ConfigMaps / Secrets    ← expose & configure them
               ├── 13 Storage / HPA / Probes            ← persist, scale, keep healthy
               └── 14 Troubleshooting                   ← what to do when it breaks
                             │
                             ▼
        15 Helm                    ← package all that YAML
               │
               ▼
        16 CI/CD & GitHub Actions  ← automate build → test → deploy
               └── 17 DevSecOps    ← add the security gates
                      │
                      ▼
        18 Terraform & IaC         ← create the infrastructure in code
               └── 19 Cloud & VPC  ← a real network to run on
                      │
                      ▼
        20 Monitoring & GitOps     ← see it, and let Git drive it
                      │
                      ▼
        21 Final Project           ← all of it, at once
```

**The thread that runs through all twenty-one:**

> Linux gives you processes, permissions, ports and logs. Shell automates them. Networking
> connects them. Git versions them. Docker packages them. Kubernetes runs them at scale.
> Helm packages the packaging. Actions automates the whole chain. Terraform creates what it
> runs on. Prometheus watches it. Argo CD keeps it honest.
> **Every session after 08 is the same ideas at a larger scale.**

---

## 🔁 Concepts that reappear across sessions

| Concept | First seen | Comes back as |
|---|---|---|
| **Signals** (SIGTERM/SIGKILL) | 02 Linux processes | `docker stop` exit **143** / **137** (06) → Pod termination grace period (10) |
| **Exit codes** (`$?`, 127, 137) | 03 Shell | Container exit codes (06) → `CrashLoopBackOff` diagnosis (14) → pipeline gates (16) |
| **`chmod +x`** | 02 Permissions | Running scripts (03) → `RUN chmod +x entrypoint.sh` (07) → `build.sh` in CI (16) |
| **Ports & `0.0.0.0`** | 04 Networking | `-p 8080:80` (06) → `containerPort` (10) → `--host 0.0.0.0` in the capstone (21) |
| **DNS** | 04 Networking | Compose service names (08) → CoreDNS & Service FQDN (11) → `http://prometheus:9090` (20) |
| **CIDR & private IP ranges** | 04 Networking | `docker0` = `172.17.0.0/16` (08) → Pod CIDR (11) → VPC & subnets (19) |
| **`/etc`, `/var/log`, `/var/lib`** | 02 File system | `/var/lib/docker`, `/var/lib/postgresql/data` volume mounts (08, 21) |
| **`.gitignore`** | 05 Git | `.dockerignore` (07) → `.helmignore` (15) → Terraform `.gitignore` (18) |
| **Command substitution `$(...)`** | 03 Shell | `docker rm -f $(docker ps -aq)` (06) → `${GITHUB_SHA::7}` image tags (16) |
| **Declarative desired state** | 09 Kubernetes | Terraform plan/apply (18) → Argo CD reconciliation (20) |
| **Health checks** | 06 `HEALTHCHECK` | Liveness/readiness/startup probes (13) → `--atomic` relies on them (15) → `/health` vs `/ready` (21) |
| **Labels & selectors** | 10 Kubernetes | Service endpoints (11) → ServiceMonitor (20) → security group references (19) |
| **Secrets hygiene** | 05 Git (`.env`) | Never in `ENV`/`ARG` (07) → K8s Secrets (12) → Actions secrets (16) → secret scanning (17) → Sealed Secrets (20) |
| **Trivy / image scanning** | 01 DevSecOps | Image security (07) → the CI security gate (17) → the capstone pipeline (21) |
| **Rollback** | 05 `git revert` | `kubectl rollout undo` (10) → `helm rollback` (15) → `terraform` state (18) → `git revert` in GitOps (20) |
| **Templating** | 15 Helm `{{ }}` | Terraform variables (18) → Actions `${{ }}` contexts (16) |

---

## ⭐ Highest-value takeaway per session

| # | If you only remember one thing |
|---|---|
| **01** | Microservices buy independent deployability at the cost of operational complexity — **DevOps automation is what pays that cost**. |
| **02** | `/etc` config, `/var/log` logs, `/var/lib` state. Permissions are `r=4 w=2 x=1`. `systemctl status` → `journalctl -u` starts every investigation. |
| **03** | `set -euo pipefail`, **always quote `"$var"`**, `>` overwrites while `>>` appends, and call a function **without** parentheses. |
| **04** | Network bits + host bits = 32; usable hosts = `2^host − 2`. Ports 22/80/443/3306/5432/6379/6443. **TCP reliable, UDP fast.** When it breaks, it's DNS. |
| **05** | `merge` preserves history (shared branches); `rebase` rewrites it (own branches only). `revert` for pushed commits, `reset` only for local. `reflog` saves you. |
| **06** | Image = class, container = object. Containers share the host **kernel** → MBs and seconds. A container lives only as long as **PID 1**. |
| **07** | **Copy dependency manifests before source code** for cache efficiency. `CMD` is overridable, `ENTRYPOINT` is appended to. Multi-stage builds shrink images dramatically. |
| **08** | Use a **user-defined network** and talk by **service name on the container's own port**. Anything you want to keep goes in a **named volume**. |
| **09** | Everything goes through the **API server**, and only it touches **etcd**. You declare desired state; controllers reconcile. Self-healing is a free side effect. |
| **10** | Only five Pod **phases** exist (`CrashLoopBackOff` is a container *state*). **`Running != Ready`.** Rolling updates advance only when a new Pod passes **readiness**. |
| **11** | `nodePort` → `port` → `targetPort` is the packet's path. **`kubectl get endpoints` is the Service debugging command** — empty means selector or readiness. |
| **12** | A Secret is **base64-encoded, not encrypted** — RBAC is the real protection. Editing a ConfigMap does nothing to running pods: **`kubectl rollout restart`**. |
| **13** | **PV = supply, PVC = demand.** **No CPU `requests` and no Metrics Server ⇒ no HPA.** **Readiness failure ≠ container restart.** |
| **14** | `get` → `describe` → **Events** → `logs --previous` → `exec`. `CrashLoopBackOff` is a *symptom*; the cause is in Events or the previous container's logs. |
| **15** | Chart = recipe, Values = ingredients, Release = the meal. **`helm template` before `helm install`**, and **`helm upgrade --install … --atomic`** in CI. |
| **16** | A workflow is `WHEN` + `WHAT`. **Jobs are parallel and each gets a fresh VM; steps are sequential.** `needs:` is the gate. `actions/checkout` first, always. |
| **17** | **SAST = your code, SCA = your dependencies, secret scanning = your credentials, image scanning = your container.** A scan without **`--exit-code 1`** is not a gate. |
| **18** | Every plan compares **configuration + state + reality**. `-/+` means destroy-and-recreate. **State is plaintext and holds secrets** — never commit it, never edit it. |
| **19** | A subnet is "public" only because its **route table points `0.0.0.0/0` at an Internet Gateway**. **Route table = WHERE, security group = ALLOWED.** |
| **20** | Monitoring says *when*, observability says *why*. Prometheus **pulls** (`up` is free health). GitOps = Git is desired state + **`selfHeal`** makes it authoritative. |
| **21** | The chain is the deliverable. **Tag every image with the commit SHA**, and `helm template` before every deploy — it catches the bugs `helm install` reports as success. |

---

## 🖥️ Reading as a website

These notes also build into a plain static HTML site — one `.html` page per session, no
server needed, same markdown as the source.

```bash
pip install -r site/requirements.txt    # once
python site/build.py
```

Then open `site/dist/index.html` directly in a browser.

It is published automatically to **GitHub Pages** on every push to `main`
(`.github/workflows/pages.yml`); set *Settings → Pages → Source* to **GitHub Actions** once to
enable it. See [`site/README.md`](../site/README.md) for details.

Features: sidebar across every notes folder, per-page table of contents, prev/next navigation,
build-time syntax highlighting, dark/light theme, and GitHub-compatible heading anchors so the
in-note TOC links work in both places.

---

## 📌 Conventions used in these notes

| Marker | Meaning |
|---|---|
| ⭐ | The thing most worth remembering / the most common exam or interview point |
| ⚠️ | A trap, a gotcha, or something that will cost you money or data |
| 🐛 | A genuine bug or inconsistency **in the source repo**, with the fix |
| 💡 | Useful context that goes slightly beyond the syllabus |
| 💰 | Something billable — destroy it when you're done |

Each session file follows the same shape: **Topics + repo folder → Table of Contents →
content → Key Terms Recap → Session Takeaways → References → Next**.

---

## 🔗 Key references

- Course repo — https://github.com/Nency-Ravaliya/devops-heros
- Linux `man` pages & https://tldr.sh
- Pro Git (free book) — https://git-scm.com/book/en/v2
- Docker docs — https://docs.docker.com
- Kubernetes docs — https://kubernetes.io/docs/
- Helm docs — https://helm.sh/docs/
- GitHub Actions docs — https://docs.github.com/en/actions
- Trivy — https://trivy.dev/ · OWASP Top 10 — https://owasp.org/www-project-top-ten/
- Terraform docs — https://developer.hashicorp.com/terraform/docs
- AWS VPC — https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html
- Prometheus — https://prometheus.io/docs/ · Grafana — https://grafana.com/docs/
- Argo CD — https://argo-cd.readthedocs.io/ · OpenGitOps — https://opengitops.dev/
- Google SRE Book — https://sre.google/sre-book/table-of-contents/
