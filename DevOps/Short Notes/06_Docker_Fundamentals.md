# ⚡ S06 · Docker Fundamentals

> *Revision card.* Full notes → [Session 6](../06_Docker_Fundamentals.md)

---

## 🔑 One-line core

***Image = class, container = object.*** Containers share the host **kernel** → MBs and
seconds. A container lives exactly as long as **PID 1**.

---

## ⚖️ Container vs VM

| Container | VM |
|---|---|
| shares host **kernel** | own **guest OS** |
| MBs | GBs |
| starts in **seconds** | minutes |
| process isolation | hardware isolation |
| density: hundreds | tens |

---

## 🔬 How it actually works

| | |
|---|---|
| **namespaces** | what a container **sees** — PID, net, mnt, UTS, IPC, user |
| **cgroups** | what a container **gets** — CPU, memory limits |
| **union FS** | read-only layers + one thin writable layer |

> ⭐ Docker is a friendly front-end to **Linux kernel features**.

---

## 🏗️ Architecture

```
docker CLI ──REST──▶ dockerd (daemon) ──▶ containerd ──▶ runc ──▶ container
                          │
                          └──▶ registry (Docker Hub / GHCR)
```

---

## 🔄 Lifecycle

```
          docker run
image ──────────────▶ created ──▶ running ⇄ paused
                                     │
                            stop ────┼──── kill
                                     ▼
                                   exited ──rm──▶ gone
```

---

## 🧾 Commands

```bash
docker run -d --name web -p 8080:80 nginx:1.27
docker ps            / docker ps -a
docker logs -f web
docker exec -it web sh
docker stop web      / docker rm web
docker images        / docker rmi nginx:1.27
docker inspect web
docker stats
docker system prune -a --volumes      # ⚠️ deletes data
```

---

## 🔢 Exit codes — carry into Kubernetes

| | |
|---|---|
| **0** | clean exit |
| 1 | application error |
| 125 | daemon error |
| 126 | not executable |
| **127** | command not found |
| **137** | SIGKILL / **OOM** |
| **143** | SIGTERM |

---

## 📏 Limits & health

```bash
docker run --memory=512m --cpus=1.5 myapp
```

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost/health || exit 1
```

---

## 🏷️ Tags

> ⚠️ **`:latest` is not "newest" — it's just a default name.** Pin a tag (or a digest)
> or you cannot say what is running.

---

## ⚠️ Traps

- *"My container exits immediately"* → **PID 1 finished or crashed**. `docker logs` it.
- Forgetting `--rm` on throwaway runs → disk fills with stopped containers
- No memory limit in prod → one container takes down the host
- `prune -a --volumes` deletes **data**

---

## 🩺 Debug order

```
docker ps -a   →  docker logs   →  docker inspect   →  docker exec -it
```

*Same outside-in order you'll use with `kubectl`.*

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Image vs container? | class vs object |
| Why so much faster than a VM? | shares the host **kernel** |
| Exit 137? | OOM-killed / SIGKILL |
| Container stops instantly? | PID 1 exited |
| Swarm vs Kubernetes? | simpler vs won |

---

⬅️ [S05](./05_Git_and_GitHub.md) · ➡️ [S07 · Dockerfile](./07_Docker_Images_and_Dockerfile.md)
