# ⚡ S01 · DevOps & Microservices

> *Revision card* — 5-minute recall.
> Full notes → [Session 1](../01_Introduction_to_DevOps_and_Microservices.md)

---

## 🔑 One-line core

**Microservices buy independent deployability at the cost of operational complexity —
*DevOps automation is what pays that cost.***

---

## 🏛️ Monolith vs Microservices

| | Monolith | Microservices |
|---|---|---|
| Deploy | all of it, together | *per service* |
| Scale | whole app | only the hot service |
| Failure | one bug → whole app | *blast radius contained* |
| Data | one DB | DB per service |
| Team | one codebase | own-your-service |
| Cost | simple | **network + ops + observability** |

> ⭐ **Small team / unclear domain → monolith.** Microservices are an *organisational*
> answer as much as a technical one.

---

## 🔄 DevOps lifecycle — memorise the loop

```
Plan → Code → Build → Test → Release → Deploy → Operate → Monitor
  ↑                                                           │
  └───────────────────────────────────────────────────────────┘
```

---

## ⚙️ CI vs CD

| | Means |
|---|---|
| **CI** | every push → auto **build + test** |
| **CD** = Delivery | always *deployable*; human approves prod |
| **CD** = Deployment | passing tests → **auto to prod** |

*Most companies run Continuous Delivery.*

---

## 🧰 Tool → lifecycle stage

| Stage | Tool |
|---|---|
| Code | Git, GitHub |
| Build | Docker, Maven |
| Test | pytest, JUnit, Selenium |
| Release | GitHub Actions, Jenkins |
| Deploy | Kubernetes, Helm, Argo CD |
| Operate | Terraform, Ansible |
| Monitor | Prometheus, Grafana, ELK |

---

## 🔐 DevSecOps — *shift left*

| Scan | Looks at |
|---|---|
| **SAST** | your source code |
| **SCA** | your dependencies |
| Secret scanning | credentials in git |
| **Image scan** (Trivy) | the container image |

> ⭐ A finding at commit time costs **10–100× less** than one found in production.

---

## 🔁 GitOps in one line

***If it isn't in Git, it doesn't exist.*** Git = desired state; an in-cluster agent
reconciles.

---

## 📊 DORA — how you know it's working

1. Deployment **frequency**
2. **Lead time** for changes
3. **Change failure rate**
4. **MTTR**

---

## ⚠️ Traps

- Microservices ≠ "better". They trade one hard problem for a different one.
- "DevOps team" is an anti-pattern — it's a *practice*, not a department.
- CI without tests is just a build server.

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Monolith → microservices, first thing you need? | **Automated deployment + observability** |
| Delivery vs Deployment? | manual prod approval vs none |
| Why DevSecOps? | security as a pipeline *stage*, not a final audit |
| 4 DORA metrics? | freq · lead time · failure rate · MTTR |

---

➡️ Next card: [S02 · Linux](./02_Linux_Fundamentals.md)
