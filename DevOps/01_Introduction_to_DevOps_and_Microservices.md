# Session 1 — Introduction to DevOps & Microservices 🚀

> Foundation session. Before touching a single tool, you need to know **what** we are deploying
> (architecture), **why** we automate it (DevOps culture), and **how** the work flows (lifecycle + CI/CD).

---

## 📑 Table of Contents
1. [Software Architecture: The Starting Point](#-software-architecture-the-starting-point)
2. [Monolithic Architecture](#1-monolithic-architecture)
3. [Microservice Architecture](#2-microservice-architecture)
4. [Monolith vs Microservices](#-monolith-vs-microservices)
5. [How Microservices Talk to Each Other](#-how-microservices-talk-to-each-other)
6. [Choosing an Architecture](#-choosing-an-architecture-the-classroom-question)
7. [What is DevOps?](#-what-is-devops)
8. [The DevOps Lifecycle](#-the-devops-lifecycle)
9. [CI/CD Overview](#-cicd-overview)
10. [DevOps Tools Landscape](#-devops-tools-landscape-the-13-pillars)
11. [DevSecOps & Security Tooling](#-devsecops--security-tooling)
12. [GitOps](#-gitops)
13. [Job Roles](#-job-roles-in-the-devopscloud-space)
14. [AI vs ML vs DL](#-ai-vs-ml-vs-dl)
15. [Key Terms Recap](#-key-terms-recap)

---

## 🏛️ Software Architecture: The Starting Point

Every application has to be *structured* somehow. Two dominant styles:

1. **Monolithic Architecture** — one single deployable unit.
2. **Microservice Architecture** — many small, independently deployable units.

DevOps practices exist largely *because* modern systems moved toward the second style. When you
have 40 services instead of 1 application, manual deployment stops being possible — automation
becomes mandatory.

---

## 1. Monolithic Architecture

### What it is
A **monolith** is an application where the **entire functionality lives in one single codebase**
and ships as **one single deployable artifact** (one `.jar`, one `.war`, one container, one
process). UI layer, business logic and data-access layer are compiled and released together.

```
┌──────────────────────────────────────────────┐
│              MONOLITH (1 process)            │
│                                              │
│   UI  │  Auth  │  Orders  │  Payments        │
│       │        │          │                  │
│   ────┴────────┴──────────┴────────          │
│           Shared Business Logic              │
│           Shared Data Access Layer           │
└───────────────────┬──────────────────────────┘
                    │
              ┌─────▼─────┐
              │  ONE DB   │
              └───────────┘
```

### Characteristics (from class notes)
| # | Characteristic | Explanation |
|---|---|---|
| 1 | **Simple to start** | One repo, one build, one deploy. Zero distributed-systems overhead. Perfect for a small team or a v1 product. |
| 2 | **Complex & delayed deployments** | Changing one line in the "Payments" module forces you to rebuild, retest and redeploy the *entire* application. Release cycles become weekly/monthly. |
| 3 | **One common codebase** | Everything shares the same repo, language, runtime and often the same database schema. |
| 4 | **Tightly coupled** | Modules call each other via in-process function calls. A change in one module frequently breaks others, and a failure in one can crash the whole process. |

### Advantages
- **Fast initial development** — no network boundaries, no service discovery, no API contracts.
- **Simple debugging** — a single stack trace covers the whole request path.
- **ACID transactions are easy** — one database, so one DB transaction spans the whole operation.
- **Lower infrastructure cost** — one server/container can host the whole app.
- **No network latency** between "modules" (they are just method calls).

### Disadvantages
- **Scaling is all-or-nothing** — if only *search* is hot, you still replicate the entire
  application, wasting CPU/RAM on the other 90%.
- **Single point of failure** — one memory leak in one module takes down everything.
- **Technology lock-in** — the whole app is stuck on one language/framework version.
- **Slow onboarding** — a new developer must understand a huge codebase.
- **Long build & test times** — CI pipeline duration grows with the codebase.
- **Risky releases** — the blast radius of every deployment is 100% of the product.

---

## 2. Microservice Architecture

### What it is
The application is decomposed into **small, independent services**, each owning **one business
capability**, each with its **own codebase, own database and own deployment lifecycle**, and each
communicating over the **network** (HTTP/REST, gRPC or message queues).

```
                        ┌──────────────┐
        Client ────────▶│  API Gateway │
                        └──┬───┬───┬───┘
             ┌─────────────┘   │   └─────────────┐
             ▼                 ▼                 ▼
      ┌────────────┐    ┌────────────┐    ┌────────────┐
      │   Auth     │    │  Orders    │    │  Payments  │
      │  Service   │    │  Service   │    │  Service   │
      └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
            ▼                 ▼                 ▼
        ┌───────┐         ┌───────┐         ┌───────┐
        │ DB_A  │         │ DB_B  │         │ DB_C  │
        └───────┘         └───────┘         └───────┘
       (each service owns its own data store)
```

### Characteristics (from class notes)
| # | Characteristic | Explanation |
|---|---|---|
| 1 | **More operational complexity** | You now run N services, N pipelines, N sets of logs, service discovery, distributed tracing, network policies. This is *exactly* the complexity DevOps tooling (Docker, K8s, CI/CD, Prometheus) exists to tame. |
| 2 | **Easily deployable** | Each service is small and independent, so you can deploy Payments 20× a day without touching Orders. |
| 3 | **Micro-components for each feature** | One service = one business feature = one team (bounded context). |
| 4 | **Loosely coupled** | Services interact through **well-defined APIs/contracts**, not shared code. Internal changes are invisible to callers as long as the contract holds. |

### Core principles
- **Single Responsibility / Bounded Context** — one service does one thing well.
- **Independent deployability** — deploying service A must never require deploying service B.
- **Database per service** — no service reaches into another's tables; data is exposed only via API.
- **Decentralized governance** — each team picks the language/DB that fits their problem
  (polyglot: Node for the API, Python for ML, Go for high throughput).
- **Design for failure** — the network *will* fail; use timeouts, retries, circuit breakers.
- **Observability first** — with distributed calls, logs alone are not enough (need traces + metrics).

### Advantages
- **Independent, granular scaling** — run 10 replicas of `search`, 2 of `billing`.
- **Fault isolation** — Payments crashing does not take down browsing/login.
- **Faster releases** — small blast radius → deploy many times per day.
- **Technology freedom** — right tool for each job.
- **Team autonomy & parallel development** — small teams ship without cross-team release trains.
- **Easier to understand a single service** — a new dev learns one small codebase.

### Disadvantages
- **Distributed system problems** — network latency, partial failure, retries, idempotency.
- **Data consistency is hard** — no cross-service ACID transaction. Needs the **Saga pattern**,
  eventual consistency, compensating transactions.
- **Operational overhead** — many pipelines, dashboards, service discovery, secrets per service.
- **Debugging is harder** — one request may cross 8 services → you need **distributed tracing**.
- **Higher infra cost** at small scale.
- **Versioning & contract management** — breaking an API breaks other teams.

---

## ⚖️ Monolith vs Microservices

| Aspect | Monolith | Microservices |
|---|---|---|
| **Codebase** | One common codebase | Many small codebases (one per service) |
| **Coupling** | Tightly coupled | Loosely coupled |
| **Deployment unit** | Whole app at once | Per service, independent |
| **Deployment speed** | Complex, delayed | Easy, frequent |
| **Getting started** | Simple | Needs upfront design + a platform |
| **Operational complexity** | Low | High (this is where DevOps earns its salary) |
| **Scaling** | Vertical / whole-app replicas | Horizontal, per service |
| **Failure blast radius** | Entire application | Single service (if designed well) |
| **Database** | One shared DB | DB per service |
| **Tech stack** | Single, uniform | Polyglot |
| **Transactions** | Simple (ACID) | Hard (Saga / eventual consistency) |
| **Team structure** | One large team, coordinated releases | Small autonomous teams |
| **Debugging** | Single stack trace | Distributed tracing needed |
| **Best fit** | MVPs, small teams, simple domains, internal tools | Large domains, many teams, high scale, uneven scaling needs |

> 🧠 **Mental model:** a monolith is a *studio apartment* (everything in one room — cheap and easy);
> microservices are an *apartment block* (each unit independent — but now you need a building
> manager, plumbing plans and security). **DevOps is the building manager.**

---

## 🔗 How Microservices Talk to Each Other

| Style | Mechanism | Use when |
|---|---|---|
| **Synchronous** | REST over HTTP, gRPC | Caller needs an immediate answer ("is this user valid?") |
| **Asynchronous** | Message queue / event bus (Kafka, RabbitMQ, SQS) | Fire-and-forget, decoupling, buffering spikes ("order placed" event) |
| **Service discovery** | DNS-based (Kubernetes Services) or a registry (Consul/Eureka) | Services must find each other without hard-coded IPs |
| **API Gateway** | Single entry point: routing, auth, rate limiting, TLS termination | Clients should not know the internal topology |

Supporting patterns you will meet later:
- **Load Balancer** — spreads traffic across replicas of a service.
- **Circuit Breaker** — stops hammering a service that is already failing.
- **Sidecar / Service Mesh** (Istio, Linkerd) — moves retries, mTLS and tracing out of app code.

> 💡 In Docker (Session 8) services find each other by **container name** on a user-defined network.
> In Kubernetes they find each other by **Service name** via cluster DNS. Same idea, different layer.

---

## 🎯 Choosing an Architecture (the classroom question)

> **Q: To build a "College Placement Application", which type of architecture will you use —
> (1) Monolith or (2) Microservice?**
>
> **Class answer: Microservice ✅**

**Why microservices fit this problem**
- The domain splits into **naturally separate features**: Student Profiles, Resume Management,
  Company/Recruiter Portal, Job Postings, Applications & Interview Scheduling, Notifications,
  Analytics/Reports, Authentication.
- **Very uneven load** — during placement season *Applications* and *Notifications* get hammered
  while *Analytics* is idle. You want to scale only the hot parts.
- **Independent teams/features** can ship without blocking each other.
- **Fault isolation matters** — if the Notification (email/SMS) service dies, students must still
  be able to apply.
- Different features want different tech (Python service for resume parsing/ranking, Node for the
  API, a search engine for job matching).

**Honest counterpoint (worth saying in an interview):** for a *single college, a few hundred users,
one developer*, a **monolith is the pragmatic first choice** — then extract services as load and
team size grow. This is the well-known **"Monolith First"** approach, and migrating
monolith → microservices incrementally is the **Strangler Fig pattern**. Choose microservices when
the *organizational and scaling* pain of a monolith is real, not hypothetical.

---

## 🤝 What is DevOps?

### The formula
```
DevOps  =  Dev  +  Ops
        =  Development  +  Operations
```

**DevOps is a culture and a set of practices** that unites software **Development** (writing
features) and IT **Operations** (running, scaling and keeping software alive) so an organization
can deliver software **faster, more frequently and more reliably**.

It is **not** a single tool, and **not** merely a job title — it is a way of working, supported by
automation.

### The problem it solves — the "wall of confusion"
Before DevOps, teams were siloed with **conflicting incentives**:

| | Dev team wants | Ops team wants |
|---|---|---|
| Goal | Ship features **fast** | Keep production **stable** |
| Attitude to change | More changes = progress | More changes = risk |
| Classic line | *"It works on my machine."* | *"Then we'll ship your machine."* |

Result: code thrown "over the wall", manual overnight deployments, environment drift
(dev ≠ staging ≠ prod), rare/big/terrifying releases, and blame wars after every failure.

### The DevOps answer
| Principle | What it means in practice |
|---|---|
| **Culture & shared ownership** | "You build it, you run it." Devs are on call; Ops write code. |
| **Automation** | Anything done twice manually gets scripted (build, test, deploy, provisioning). |
| **CI/CD** | Every commit is automatically built, tested and made deployable. |
| **Infrastructure as Code (IaC)** | Servers/networks defined in version-controlled files (Terraform), not clicked in a console. |
| **Small, frequent releases** | Small change = small blast radius = easy rollback. |
| **Monitoring & feedback loops** | Production tells you the truth; metrics/logs/traces feed back into planning. |
| **Fail fast, learn fast** | Blameless post-mortems; fix the system, not the person. |
| **Shift left** | Move testing and **security** as early in the pipeline as possible (→ DevSecOps). |

### Benefits
- 🚀 **Faster time to market** — deploy daily instead of quarterly
- 🛡️ **Higher reliability** — automated tests + repeatable deployments + fast rollback
- 📈 **Better scalability** — IaC + containers + orchestration
- 🤝 **Better collaboration** — one team, one goal
- 💰 **Lower cost** — less manual toil, less downtime, better resource utilisation
- 🔁 **Reproducibility** — the same artifact is promoted through dev → staging → prod

### DORA metrics (how DevOps performance is measured)
| Metric | Question it answers |
|---|---|
| **Deployment Frequency** | How often do we ship to production? |
| **Lead Time for Changes** | Commit → running in production: how long? |
| **Change Failure Rate** | What % of deployments cause a problem? |
| **MTTR** (Mean Time To Restore) | How fast do we recover from failure? |

---

## 🔄 The DevOps Lifecycle

The lifecycle is an **infinite loop** — the output of Monitor feeds back into Plan.

```
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   Plan ──▶ Code ──▶ Build ──▶ Test ──┐                       │
   │                                      │                       │
   │             Deploy ◀── Release ◀─────┘                       │
   │               │                                              │
   │               └──▶ Operate ──▶ Monitor ──────────────────────┘
   │                                   (feedback back into Plan)
   └──────────────────────────────────────────────────────────────┘
```

| Phase | What happens | Typical tools |
|---|---|---|
| **1. Plan** | Requirements, user stories, sprint planning, backlog, architecture decisions | Jira, Azure Boards, Confluence, GitHub Projects |
| **2. Code** | Write the application, review via Pull Requests, follow a branching strategy | Git, GitHub/GitLab, VS Code |
| **3. Build** | Compile, resolve dependencies, package the artifact / **build the Docker image** | Maven, Gradle, npm, **Docker**, GitHub Actions, Jenkins |
| **4. Test** | Unit, integration and e2e tests + **security scans** (SAST/SCA/image scanning). A failing test must break the build | JUnit, PyTest, Jest, Selenium, SonarQube, Trivy |
| **5. Release** | Version, tag and push the tested artifact to a registry; approval gates for production | Docker Hub / ECR / ACR / GHCR, Nexus, Artifactory |
| **6. Deploy** | Ship the release to an environment (dev → staging → prod) using rolling / blue-green / canary strategies | Kubernetes, Helm, Argo CD, Terraform |
| **7. Operate** | Keep it running: scaling, backups, incident response, on-call, capacity planning | Kubernetes, Ansible, cloud consoles |
| **8. Monitor** | Collect **metrics, logs, traces**; alert on SLO breaches; feed insight back to Plan | Prometheus, Grafana, Loki, ELK, Jaeger |

> 🧠 The loop shape is the whole point: **there is no "done"**. Every deployment produces
> production data that changes what you plan next.

---

## ⚙️ CI/CD Overview

### CI — Continuous Integration
> Developers **merge their code into a shared main branch frequently** (ideally many times a day),
> and every merge automatically triggers a **build + automated tests**.

- **Goal:** catch integration bugs within minutes of writing them, not weeks later.
- **Requires:** a single source of truth (Git), a fast automated test suite, and a rule that
  **a broken build gets fixed immediately**.
- **Typical CI job:** checkout → install deps → lint → unit tests → build artifact/image → scan → publish.

### CD — two meanings (know both!)

From class notes:
```
CD → Continuous Deployment  — fully automatic, straight to production
CD → Continuous Delivery    — automatic up to production, then MANUAL APPROVAL
```

| | Continuous **Delivery** | Continuous **Deployment** |
|---|---|---|
| **Definition** | Every change that passes the pipeline is *ready* to release; a human clicks "deploy" | Every change that passes the pipeline goes to production **automatically** |
| **Production release** | **Manual approval gate** ✋ | **No manual step** 🤖 |
| **Who decides when** | Business / release manager | The pipeline |
| **Needs** | Solid automated tests | *Excellent* automated tests, monitoring, feature flags, instant rollback |
| **Fits** | Regulated industries (banking, healthcare), coordinated launches | High-velocity web products |

### The pipeline
```
  Commit ──▶ [ CI: Build → Test → Scan → Package ] ──▶ Artifact/Image in Registry
                                                             │
                                     ┌───────────────────────┘
                                     ▼
                          [ CD: Deploy to Dev ] ──▶ [ Staging ]
                                                        │
                                    (auto)              │  (manual gate = Delivery)
                                                        ▼
                                                   [ Production ]
```

**Why it matters:** CI/CD is the *conveyor belt* of DevOps. Without it, "deploy 20× a day" is
impossible; with it, deployment becomes a boring non-event.

Deployment strategies covered later: **Rolling update**, **Blue-Green**, **Canary**, **Feature flags**.

---

## 🧰 DevOps Tools Landscape (the 13 pillars)

Exactly as listed in the session, with why each one exists:

| # | Tool / Area | Why it is in the stack |
|---|---|---|
| **1** | **Git & GitHub** | Version control — the **source of truth** for code, IaC, pipeline definitions and K8s manifests. Everything in DevOps starts from a Git commit. |
| **2** | **Docker** | **Containerization** — package app + dependencies into one portable image. Kills "works on my machine". |
| **3** | **Python** → (**Go**) | Scripting & automation glue: log parsing, API calls, cloud SDK scripts. **Go** is the language most cloud-native tooling is *written in* (Docker, Kubernetes, Terraform, Prometheus) — worth learning next. |
| **4** | **Linux** — *the heart of DevOps* ❤️ | Practically every server, container base image and CI runner is Linux. File system, permissions, processes, services, logs, networking — non-negotiable. |
| **5** | **Networking** — TCP/UDP, OSI layers | Everything is a network call: ports, DNS, HTTP/HTTPS, firewalls/security groups, load balancers, container networks. Half of all production incidents are network or DNS. |
| **6** | **CI/CD** | Automates Build → Test → Release → Deploy. Tools: GitHub Actions, Jenkins, GitLab CI, Azure DevOps. |
| **7** | **Cloud** — **AWS, Azure, GCP, Oracle** | Where the infrastructure actually lives: compute, storage, networking, managed Kubernetes, IAM. |
| **8** | **Kubernetes (K8s)** | **Container orchestration** at scale — scheduling, self-healing, scaling, rolling updates, service discovery. Core objects: **Pod, ReplicaSet, Deployment, StatefulSet, Service, Volume**. |
| **9** | **Terraform** | **IaC provisioner** — declaratively *create* cloud infrastructure (VPCs, VMs, clusters, DBs) from version-controlled code, with a state file tracking reality. |
| **10** | **Ansible** | **Configuration management** — agentless (SSH) provisioning/configuring of existing servers via YAML playbooks. *Terraform builds the house; Ansible furnishes it.* |
| **11** | **Monitoring** — **Prometheus + Grafana** | **Prometheus** = time-series **metrics** database + scraper + alerting rules. **Grafana** = **dashboards / visualization** on top. |
| **12** | **GitOps** | Git as the single source of truth for *deployments*; an agent (**Argo CD**/Flux) continuously reconciles the cluster to the repo. |
| **13** | **SecOps / DevSecOps** | Security shifted **left** into the pipeline: SAST, DAST, SCA, secret scanning, image scanning, security gates. |

### Tool categories at a glance
| Category | Tools |
|---|---|
| Version control | Git, GitHub, GitLab, Bitbucket |
| Build | Maven, Gradle, npm, Docker BuildKit |
| CI/CD | GitHub Actions, Jenkins, GitLab CI, CircleCI, Azure DevOps |
| Containers | Docker, containerd, Podman |
| Orchestration | Kubernetes, Docker Swarm, ECS |
| Packaging (K8s) | Helm, Kustomize |
| IaC | Terraform, CloudFormation, Pulumi, Bicep |
| Config management | Ansible, Chef, Puppet, SaltStack |
| Registries | Docker Hub, ECR, ACR, GCR, GHCR, Harbor, Nexus |
| Monitoring / metrics | Prometheus, Grafana, CloudWatch, Datadog |
| Logging | ELK / Elastic Stack, Loki, Fluentd, Splunk |
| Tracing | Jaeger, Zipkin, OpenTelemetry |
| Security | SonarQube, Trivy, Snyk, OWASP ZAP, Gitleaks, Vault |
| GitOps | Argo CD, Flux |

---

## 🔐 DevSecOps & Security Tooling

**DevSecOps = DevOps + security built into every stage** ("shift left" — find vulnerabilities in
the pipeline, not in a pen-test report six months after release).

From the session notes:

| Tool / Technique | Type | What it does |
|---|---|---|
| **SonarQube** | **SAST** | **Static Application Security Testing** — analyses **source code** (without running it) for bugs, code smells, vulnerabilities and coverage. Enforces a **Quality Gate** that can fail the build. |
| **SAST** | Static | Scans code/binaries at rest. Early and cheap, but can produce false positives. Tools: SonarQube, Semgrep, CodeQL. |
| **DAST** | Dynamic | **Dynamic Application Security Testing** — attacks the **running** application from the outside (like an attacker) to find runtime issues: injection, auth flaws, bad headers. Tool: **OWASP ZAP**. |
| **OWASP** | Standard / community | The **Open Worldwide Application Security Project** — publishes the **OWASP Top 10** (canonical list of the most critical web app risks) plus tools like ZAP and Dependency-Check. |
| **Trivy** ⭐ | Scanner | **Scans the Docker image** (also filesystems, IaC, Git repos, K8s) for **CVEs** in OS packages and app dependencies, plus misconfigurations and hard-coded secrets. Fast, free, pipeline-friendly. |
| **Snyk** | Scanner (SCA + container) | Commercial scanner for dependencies, containers and IaC, with fix suggestions/PRs. |

**Related terms for the CI/CD & DevSecOps session**
- **SCA (Software Composition Analysis)** — audits **third-party dependencies**
  (`package.json`, `requirements.txt`) for known CVEs and license issues.
- **Secret scanning** — detects committed API keys/passwords (Gitleaks, TruffleHog, GitHub secret scanning).
- **Container image scanning** — Trivy / Snyk / Docker Scout on the built image before it is pushed.
- **Security gate** — a pipeline step that **fails the build** when findings exceed a threshold
  (e.g. "no HIGH or CRITICAL CVEs allowed").

```bash
# The one command to remember from this session:
trivy image myapp:1.0                                          # scan a Docker image for CVEs
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:1.0    # use it as a security gate
```

---

## 🔁 GitOps

> **GitOps = Git is the single source of truth for infrastructure and deployments.**

- You **never** run `kubectl apply` by hand against production. Instead you **commit** the desired
  state (K8s manifests / Helm values) to a Git repo.
- An in-cluster agent (**Argo CD** or **Flux**) continuously **watches** that repo and
  **reconciles** the live cluster to match it.
- Consequences:
  - **Declarative** — the repo describes desired state, not steps.
  - **Auditable** — every production change is a Git commit with an author and a diff.
  - **Rollback = `git revert`.**
  - **Drift detection** — manual changes in the cluster get reverted automatically (self-healing).
- Covered in depth in the Monitoring/Observability & GitOps session.

---

## 💼 Job Roles in the DevOps/Cloud Space

The nine roles listed in the session, with what each actually does:

| # | Role | Focus | Notes from class |
|---|---|---|---|
| **1** | **DevOps Engineer** | Build & run CI/CD pipelines, containers, IaC, automation, environments | The core entry role |
| **2** | **DevSecOps Engineer** | DevOps + embedding security scanning/gates and compliance into pipelines | |
| **3** | **Platform Engineer** | Builds the **internal developer platform** — self-service infrastructure, golden paths, shared K8s/Helm/Terraform modules so product teams ship without deep infra knowledge | |
| **4** | **SRE — Site Reliability Engineer** | Reliability as an engineering problem: **SLI/SLO/SLA**, error budgets, capacity planning, incident response, reducing **toil** through automation | Typically **~4 years experience** |
| **5** | **Cloud Engineer** | Designs/operates cloud infrastructure on AWS/Azure/GCP — networking, IAM, compute, storage, cost | |
| **6** | **Solution Architect** | End-to-end system architecture, tech selection, non-functional requirements, stakeholder alignment | Typically **~5 years experience** |
| **7** | **AIOps Engineer** | Applies AI/ML to **operations**: anomaly detection in metrics, log clustering, alert-noise reduction, predictive scaling, automated root-cause analysis | |
| **8** | **MLOps Engineer** | DevOps **for machine learning**: data & feature pipelines, experiment tracking, model registry, model serving, drift monitoring, retraining pipelines | |
| **9** | **AI Cloud Engineer** ⭐ | The emerging role: building and operating **AI/LLM workloads on cloud** — GPU infrastructure, vector databases, RAG/inference pipelines, model gateways, token cost & latency optimisation | Highlighted as the growth area |

**Common skill spine across all of them:** Linux + Networking + Git + Containers + Cloud + IaC +
CI/CD + Observability.

---

## 🧠 AI vs ML vs DL

These are **nested subsets**, not alternatives:

```
┌───────────────────────────────────────────────┐
│  AI — Artificial Intelligence                 │
│  Any technique making machines act "smart"    │
│  (incl. rule-based systems, search, planning) │
│                                               │
│   ┌─────────────────────────────────────┐     │
│   │  ML — Machine Learning              │     │
│   │  Systems that LEARN patterns from   │     │
│   │  data instead of being hard-coded   │     │
│   │                                     │     │
│   │    ┌────────────────────────────┐   │     │
│   │    │  DL — Deep Learning        │   │     │
│   │    │  ML using multi-layer      │   │     │
│   │    │  neural networks           │   │     │
│   │    │  (CNNs, RNNs, Transformers │   │     │
│   │    │   → LLMs)                  │   │     │
│   │    └────────────────────────────┘   │     │
│   └─────────────────────────────────────┘     │
└───────────────────────────────────────────────┘
```

| | AI | ML | DL |
|---|---|---|---|
| **Scope** | Broadest | Subset of AI | Subset of ML |
| **How it works** | Any "intelligent" behaviour, including explicit rules | Learns a function from data | Learns hierarchical features via deep neural nets |
| **Data needed** | Varies | Moderate | Very large |
| **Compute** | Low–high | Moderate (CPU often fine) | High (**GPU/TPU**) |
| **Feature engineering** | Manual | Mostly manual | Learned automatically |
| **Examples** | Chess engine, expert system | Spam filter, churn prediction, recommendations | Image recognition, speech-to-text, **LLMs** |

**Relevance to DevOps:** MLOps/AIOps/AI-Cloud roles require you to *operate* these workloads —
GPU nodes, huge artifacts (model weights), data versioning, long-running training jobs, and
monitoring for **model drift** on top of normal infrastructure monitoring.

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Monolith** | One codebase, one deployable unit, tightly coupled |
| **Microservice** | Small independent service owning one business capability |
| **Loose coupling** | Components interact via stable contracts, not shared internals |
| **DevOps** | Dev + Ops: culture + automation for fast, reliable delivery |
| **DevOps Lifecycle** | Plan → Code → Build → Test → Release → Deploy → Operate → Monitor → (loop) |
| **CI** | Continuous Integration — auto build + test on every merge |
| **CD (Delivery)** | Always release-ready; production needs **manual approval** |
| **CD (Deployment)** | Every passing change auto-deploys to production |
| **IaC** | Infrastructure as Code — infra defined in version-controlled files (Terraform) |
| **Configuration management** | Bringing existing servers to a desired state (Ansible) |
| **Container** | Lightweight, isolated, portable app package sharing the host kernel (Docker) |
| **Orchestration** | Automated scheduling/scaling/healing of containers (Kubernetes) |
| **GitOps** | Git as source of truth; an agent reconciles the cluster to the repo (Argo CD) |
| **DevSecOps** | Security shifted left into the pipeline |
| **SAST** | Static code security analysis (SonarQube) |
| **DAST** | Attacking the running app (OWASP ZAP) |
| **SCA** | Scanning third-party dependencies for CVEs |
| **Trivy** | Scanner for **Docker images**, filesystems, IaC, secrets |
| **Security gate** | Pipeline step that fails the build on unacceptable findings |
| **Observability** | Understanding internal state from **metrics + logs + traces** |
| **SRE** | Reliability engineering with SLIs/SLOs and error budgets |
| **Toil** | Manual, repetitive, automatable operational work |
| **DORA metrics** | Deployment frequency, lead time, change failure rate, MTTR |

---

## 🔗 References
- Docker overview — https://docs.docker.com/get-started/docker-overview/
- Docker architecture — https://www.geeksforgeeks.org/devops/architecture-of-docker/
- OWASP Top 10 — https://owasp.org/www-project-top-ten/
- Trivy — https://trivy.dev/
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
