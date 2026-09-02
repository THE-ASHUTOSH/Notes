# Session 6 — Docker Fundamentals 🐳

> Docker solves the single most expensive problem in software delivery: **"it works on my machine."**
> It packages an application *together with* its dependencies into a portable image that runs
> identically on your laptop, in CI, and in production.

---

## 📑 Table of Contents
1. [What is Docker & Why](#-what-is-docker--why-it-matters)
2. [Containers vs Virtual Machines](#-containers-vs-virtual-machines)
3. [How Containers Actually Work](#-how-containers-actually-work-namespaces--cgroups)
4. [Docker Architecture](#-docker-architecture)
5. [Docker Images](#-docker-images)
6. [Docker Containers](#-docker-containers)
7. [Image vs Container](#-image-vs-container)
8. [Container Lifecycle](#-container-lifecycle)
9. [Docker Hub & Registries](#-docker-hub--registries)
10. [Essential Commands](#-essential-commands)
11. [Inspection & Debugging](#-inspection--debugging)
12. [Cleanup Commands](#-cleanup-commands)
13. [Resource Limits & Health Checks](#-resource-limits--health-checks)
14. [Exit Codes](#-container-exit-codes)
15. [Troubleshooting](#-troubleshooting-a-failing-container)
16. [Docker Swarm (intro)](#-docker-swarm-a-brief-intro)
17. [Cheat Sheet](#-quick-cheat-sheet)

---

## 🎯 What is Docker & Why It Matters

**Docker is an open-source containerization platform** that packages applications and their
dependencies into **lightweight, portable containers** that run consistently across
different environments.

### Key benefits
| Benefit | Explanation |
|---|---|
| **Consistency** | ⭐ The *"works on my machine"* problem solved — the same environment from dev to production. The image contains the OS libraries, runtime, dependencies and your code. |
| **Efficiency** | Containers **share the host OS kernel**, unlike VMs which require full OS instances. |
| **Portability** | Run anywhere — local machine, data centre, or cloud (AWS, Azure, GCP). |
| **Scalability** | Quickly spin containers up/down based on demand. |
| **Isolation** | Each container runs in its own isolated environment (own filesystem, network, processes). |
| **Speed** | Containers start in **seconds** vs **minutes** for VMs. |

### Industry adoption
- **~87% market share** in containerization
- Used by **Uber, Airbnb, Google, Netflix, Amazon, Spotify, PayPal**
- **Essential for modern DevOps and CI/CD pipelines** — the build artifact of choice

### The problem it solves, concretely
```
BEFORE Docker                          WITH Docker
─────────────────                      ────────────────────────
Dev:     Node 18, macOS                Everyone runs the SAME IMAGE:
CI:      Node 20, Ubuntu 20               node:24-alpine + your code +
Staging: Node 16, CentOS                  exact dependency versions
Prod:    Node 18, Debian
                                       → identical behaviour everywhere
→ subtle, expensive, late bugs
```

---

## ⚖️ Containers vs Virtual Machines

```
   VIRTUAL MACHINES                       CONTAINERS
┌──────┬──────┬──────┐              ┌──────┬──────┬──────┐
│ App A│ App B│ App C│              │ App A│ App B│ App C│
├──────┼──────┼──────┤              ├──────┼──────┼──────┤
│ Libs │ Libs │ Libs │              │ Libs │ Libs │ Libs │
├──────┼──────┼──────┤              └──────┴──────┴──────┘
│Guest │Guest │Guest │  ← FULL OS   ┌─────────────────────┐
│  OS  │  OS  │  OS  │    per VM    │   Docker Engine     │
├──────┴──────┴──────┤    (GBs!)    ├─────────────────────┤
│    Hypervisor      │              │   Host OS (kernel)  │  ← SHARED kernel
├────────────────────┤              ├─────────────────────┤
│   Host OS          │              │     Hardware        │
├────────────────────┤              └─────────────────────┘
│   Hardware         │
└────────────────────┘
```

| Aspect | **Docker Container** | **Virtual Machine** |
|---|---|---|
| **Size** | Lightweight (**MBs**) | Heavy (**GBs**) |
| **Startup** | **Seconds** | **Minutes** |
| **OS** | **Shares the host kernel** | **Full OS per VM** (guest OS) |
| **Resources** | Minimal overhead | Significant overhead |
| **Isolation** | **Process-level** | **Hardware-level** (stronger) |
| **Use case** | **Microservices, apps** | **Full OS instances** |
| **Density per host** | Hundreds | A handful to dozens |
| **Portability** | Very high (one image everywhere) | Lower (large images, hypervisor-specific) |
| **Boot process** | No kernel boot — just a process | Full BIOS → kernel → init |

### The essential trade-off
- **Containers share the kernel** → tiny and instant, but **weaker isolation** and you
  **cannot run a different kernel** (no Windows containers on a Linux host, and vice-versa).
- **VMs virtualize hardware** → each has its own kernel → **stronger security boundary**, at the
  cost of gigabytes and minutes.

> 💡 **They're complementary, not rivals.** In the real world you run **containers inside VMs**:
> a cloud Kubernetes node is a VM, and it runs dozens of containers.

> 🪟 **On Windows/macOS** there is no Linux kernel, so Docker Desktop quietly runs a small Linux
> VM (WSL2 on Windows) and your containers live inside it. That's why bind mounts can be slower
> on those platforms.

---

## 🔬 How Containers Actually Work (namespaces & cgroups)

A container is **just a normal Linux process** with restricted visibility. Two kernel features
do all the work:

| Kernel feature | Provides | Namespaces involved |
|---|---|---|
| **Namespaces** | **Isolation** — "what the process can *see*" | `pid` (own process tree, app is PID 1), `net` (own interfaces/ports), `mnt` (own filesystem), `uts` (own hostname), `ipc`, `user` |
| **cgroups** (control groups) | **Limits** — "how much the process can *use*" | CPU, memory, disk I/O, network bandwidth, PID count |
| **Union filesystem** (OverlayFS) | **Layered images** + a thin writable layer per container | — |
| **Capabilities / seccomp / AppArmor** | Restricts which syscalls and root powers are available | — |

```bash
ps aux | grep nginx          # ⭐ on the HOST you can see the containerized process!
ls /proc/<pid>/ns/           # its namespaces
cat /sys/fs/cgroup/...       # its resource limits
```

> 🧠 This is why **`docker stop` sends SIGTERM to PID 1** in the container, and why your app should
> handle SIGTERM to shut down gracefully.

---

## 🏗️ Docker Architecture

Docker follows a **client–server architecture** with three main components.

```
┌──────────────────┐        REST API         ┌────────────────────────────────────┐
│  DOCKER CLIENT   │  ───────────────────▶   │       DOCKER HOST (daemon)         │
│                  │   /var/run/docker.sock  │                                    │
│ docker build     │                         │  dockerd                           │
│ docker pull      │                         │   ├── Images    (read-only)        │
│ docker run       │                         │   ├── Containers                   │
│ docker ps        │                         │   ├── Networks                     │
└──────────────────┘                         │   └── Volumes                      │
                                             │                                    │
                                             │  containerd → runc → [container]   │
                                             └───────────────┬────────────────────┘
                                                             │ push / pull
                                                             ▼
                                             ┌────────────────────────────────────┐
                                             │        DOCKER REGISTRY             │
                                             │  Docker Hub (default public)       │
                                             │  ECR · GCR · ACR · GHCR · Harbor   │
                                             └────────────────────────────────────┘
```

### 1. Docker Client
- The **command-line interface (CLI)** tool — the `docker` command you type.
- Sends commands to the Docker daemon via a **REST API**.
- Examples: `docker run`, `docker build`, `docker pull`.
- **Can communicate with remote Docker hosts** (`docker -H tcp://host:2375 ps`, or `DOCKER_HOST`).

### 2. Docker Host (Docker Daemon — `dockerd`)
- The **core engine** running on the host machine.
- **Manages containers, images, networks and volumes.**
- **Listens for Docker API requests.**
- **Handles container lifecycle operations.**
- Listens on the Unix socket `/var/run/docker.sock` by default.

### 3. Docker Registry
- **Stores and distributes Docker images.**
- **Docker Hub** — the public, default registry.
- **Private registries:** AWS ECR, Google Container Registry (GCR), Azure Container Registry (ACR).
- Push/pull images using `docker push` and `docker pull`.

### Docker Engine components
| Component | Role |
|---|---|
| **Docker CLI** | User interface for Docker |
| **dockerd** | The daemon: API, orchestration of builds, networks, volumes |
| **containerd** | **High-level container runtime** — manages the container lifecycle & image pulls |
| **runc** | **Low-level container runtime** — actually *creates* the container (namespaces/cgroups) via OCI spec |

> 💡 **Why this matters:** Kubernetes dropped the Docker *shim* and talks to **containerd**
> directly. Docker-built images still run perfectly — because they follow the **OCI**
> (Open Container Initiative) standard. "Docker image" and "OCI image" are effectively the same thing.

> 🔐 **Security note:** `/var/run/docker.sock` grants full root-equivalent control of the host.
> Adding a user to the `docker` group is effectively granting root. Never expose the socket
> or port 2375 to an untrusted network.

---

## 🖼️ Docker Images

> A **Docker image** is a **read-only template** used to create containers.

### Characteristics
- Contains **application code, libraries, dependencies and configuration**
- **Built from Dockerfile instructions**
- **Stored in a Docker registry**
- **Immutable** — never changes once created
- **Composed of layers** — each Dockerfile instruction creates one layer

### The layer model ⭐
```
┌──────────────────────────────────────┐
│  Container writable layer  (R/W)     │ ← per container, deleted with it
├──────────────────────────────────────┤
│  CMD ["npm","start"]                 │ ┐
│  COPY . .                            │ │
│  RUN npm install                     │ │  IMAGE LAYERS
│  COPY package*.json ./               │ │  (read-only, CACHED, SHARED)
│  WORKDIR /app                        │ │
│  FROM node:24-alpine                 │ ┘
└──────────────────────────────────────┘
```

Consequences of layering:
- **Shared storage** — ten images built `FROM node:24-alpine` store that base **once**.
- **Fast rebuilds** — unchanged layers come from the **build cache**.
- **Efficient transfer** — `docker push/pull` only moves layers the other side lacks.
- ⚠️ **Layers are additive** — deleting a file in a later layer does **not** shrink the image, and
  a secret added in one layer stays in history forever.

### Image naming
```
        registry.example.com:5000 / myteam / myapp : 1.4.2
        └──────── registry ──────┘ └─ repo ─┘ └───┘  └tag┘
                                              name

docker.io/library/nginx:latest      ← the full form of plain `nginx`
```
- **No registry given** → defaults to **Docker Hub** (`docker.io`)
- **No tag given** → defaults to **`:latest`** (⚠️ *not* a stable pointer — it's just a tag name)
- **Digest pinning** for absolute reproducibility: `nginx@sha256:abc123...`

### Image commands
| Command | Description | Example |
|---|---|---|
| `docker pull <image>` | Download an image from Docker Hub | `docker pull nginx` |
| `docker images` | List all downloaded images | `docker images` |
| `docker image inspect <image>` | View image details | `docker image inspect nginx` |
| `docker tag <image> <new-name>` | Tag an image with a new name | `docker tag nginx mynginx:v1` |
| `docker rmi <image>` | Delete an image | `docker rmi nginx` |
| `docker image prune` | Remove unused images | `docker image prune` |
| `docker history <image>` | Show image layer history | `docker history nginx` |
| `docker save` / `docker load` | Export/import an image as a tar | `docker save -o app.tar myapp` |
| `docker search <term>` | Search Docker Hub | `docker search nginx` |

```bash
docker pull nginx                    # :latest
docker pull nginx:1.27-alpine        # ⭐ pin a specific version
docker images
docker images -q                     # only IDs (for scripting)
docker images --filter "dangling=true"   # untagged leftovers
docker history nginx                 # ⭐ see every layer and its size
docker image inspect nginx | jq '.[0].Config.Env'

docker tag myapp:1.0 myapp:latest
docker tag myapp:1.0 username/myapp:1.0     # ⭐ tag for pushing to a registry

docker save -o myimage.tar myapp:1.0        # export to a tar file
docker load -i myimage.tar                  # import from a tar file
docker rmi myapp:1.0
docker rmi -f $(docker images -q)           # ⚠️ force remove ALL images
```

---

## 📦 Docker Containers

> A **Docker container** is a **running instance** of a Docker image.

### Characteristics
- **Writable layer on top of the image**
- Can be **started, stopped, deleted, moved**
- An **isolated process** with its own filesystem, network and process space
- **Multiple containers can run from the same image**
- **Ephemeral by default** — anything written inside is lost when it's removed (→ use volumes)

### Container commands
| Command | Description | Example |
|---|---|---|
| `docker run <image>` | Run a container from an image | `docker run nginx` |
| `docker run -d -p 8080:80 <image>` | Detached mode + map ports | `docker run -d -p 8080:80 nginx` |
| `docker run --name <name> <image>` | Name your container | `docker run --name webserver nginx` |
| `docker exec -it <container> bash` | Access a shell inside the container | `docker exec -it webserver bash` |
| `docker ps` | List **running** containers | `docker ps` |
| `docker ps -a` | List **all** containers (incl. stopped) | `docker ps -a` |
| `docker logs <container>` | Show container logs | `docker logs webserver` |
| `docker logs -f <container>` | Follow live logs | `docker logs -f webserver` |
| `docker stop <container>` | Stop a running container (SIGTERM) | `docker stop abc123` |
| `docker start <container>` | Start a stopped container | `docker start abc123` |
| `docker restart <container>` | Restart a container | `docker restart webserver` |
| `docker rm <container>` | Delete a container | `docker rm abc123` |

### `docker run` — the flags that matter
```bash
docker run -d --name web -p 8080:80 nginx

  -d, --detach          # ⭐ run in the background
  -it                   # ⭐ interactive + TTY (for shells: docker run -it ubuntu bash)
  --name web            # ⭐ a stable, human name (otherwise Docker invents e.g. "wizardly_hopper")
  -p 8080:80            # ⭐ publish HOST:CONTAINER port
  -P                    # publish ALL EXPOSEd ports to random host ports
  -e KEY=value          # ⭐ set an environment variable
  --env-file .env       # load env vars from a file
  -v myvol:/data        # ⭐ mount a volume (Session 8)
  --network mynet       # ⭐ attach to a network (Session 8)
  --rm                  # ⭐ auto-delete the container when it exits (great for one-offs)
  --restart unless-stopped   # ⭐ restart policy
  -w /app               # working directory
  -u 1000:1000          # run as a specific UID:GID
  --memory="512m" --cpus="1.0"   # resource limits
  --entrypoint /bin/sh  # override the image's ENTRYPOINT
```

**Restart policies**
| Policy | Behaviour |
|---|---|
| `no` (default) | Never restart |
| `on-failure[:N]` | Restart only on a non-zero exit, up to N times |
| `always` | Always restart, including after a daemon restart |
| `unless-stopped` ⭐ | Like `always`, but respects a manual `docker stop` |

**Naming things**
```bash
docker ps                       # NAMES and CONTAINER ID columns
docker stop web                 # ⭐ names work anywhere an ID does
docker stop abc123              # a unique ID prefix is enough
docker rename old new
```

---

## 🆚 Image vs Container

| | **Docker Image** | **Docker Container** |
|---|---|---|
| **Nature** | Read-only **template** | **Running instance** of an image |
| **Mutability** | **Immutable** | Has a **writable layer** |
| **Built from** | A `Dockerfile` | An image |
| **Stored in** | A registry (Docker Hub, ECR…) | The Docker host |
| **Count** | 1 image → many containers | Many per image |
| **Lifecycle** | Build → tag → push | Create → start → stop → remove |
| **List with** | `docker images` | `docker ps -a` |
| **Delete with** | `docker rmi` | `docker rm` |

### The analogy ⭐
```
Image     = a CLASS in programming     (the blueprint)
Container = an OBJECT / INSTANCE       (the running application)
```
Also valid: image = a *recipe*, container = the *cooked dish*; image = an OS *.iso*,
container = the *booted machine*.

```bash
# Pull an image (blueprint)
docker pull nginx:latest

# Run containers from that image (instances)
docker run -d --name web1 nginx:latest
docker run -d --name web2 nginx:latest
docker run -d --name web3 nginx:latest

# Now you have 1 image and 3 running containers
docker images     # 1 row
docker ps         # 3 rows
```

---

## 🔄 Container Lifecycle

```
                    docker create
      ┌──────────┐ ─────────────▶ ┌──────────┐
      │  IMAGE   │                │ CREATED  │
      └──────────┘                └────┬─────┘
            │                          │ docker start
            │  docker run              ▼
            │  (= create + start) ┌──────────┐  docker pause   ┌──────────┐
            └────────────────────▶│ RUNNING  │ ───────────────▶│  PAUSED  │
                                  │          │ ◀───────────────│          │
                                  └────┬─────┘  docker unpause └──────────┘
                            docker stop│  ▲
                            (SIGTERM,  │  │ docker start / restart
                             then      ▼  │
                             SIGKILL) ┌──────────┐  docker rm   ┌──────────┐
                                      │ EXITED   │ ────────────▶│ REMOVED  │
                                      │(stopped) │              │(deleted) │
                                      └──────────┘              └──────────┘
                                            ▲
                              app crashes / │ docker kill (SIGKILL, immediate)
                              exits ────────┘
```

| State | Meaning | How you got there |
|---|---|---|
| **Created** | Container exists, never started | `docker create` |
| **Running** | Process is executing | `docker run` / `docker start` |
| **Paused** | Processes frozen (SIGSTOP), memory retained | `docker pause` |
| **Exited** | Process finished or was stopped; filesystem still on disk | `docker stop`, app exit, crash |
| **Restarting** | Restart policy is bringing it back | `--restart` |
| **Dead** | Daemon couldn't remove it cleanly | rare, storage issues |
| **Removed** | Gone; writable layer deleted | `docker rm` |

### Lifecycle commands
```bash
docker create --name web nginx     # create but don't start
docker start web                   # start it
docker run -d --name web nginx     # ⭐ create + start in one step

docker stop web                    # ⭐ SIGTERM, wait 10s, then SIGKILL (graceful)
docker stop -t 30 web              # give it 30 seconds
docker kill web                    # ⚠️ immediate SIGKILL (no cleanup)
docker restart web                 # stop + start

docker pause web                   # freeze all processes
docker unpause web                 # resume

docker rm web                      # remove a STOPPED container
docker rm -f web                   # ⭐ force-remove a running one
docker run --rm ...                # ⭐ auto-remove on exit

docker rename web webserver
docker update --memory 1g web      # change resource limits on a live container
docker cp web:/app/file.txt ./     # copy OUT of a container
docker cp ./file.txt web:/app/     # copy INTO a container
docker commit web myimage:snapshot # ⚠️ create an image from a container (avoid — use a Dockerfile)
```

> ⚠️ **Key insight:** a container **lives only as long as its main process (PID 1)**.
> `docker run ubuntu` exits immediately because `bash` with no input has nothing to do.
> `docker run -it ubuntu bash` stays alive because you gave it a terminal.
> This is why a Dockerfile's `CMD` must run a **foreground** process — hence
> `CMD ["nginx", "-g", "daemon off;"]`.

---

## 🌐 Docker Hub & Registries

> **Docker Hub is a cloud-based public registry service for storing and sharing Docker images.**

### Key features
| Feature | Detail |
|---|---|
| **Public repositories** | Free hosting for open-source images |
| **Private repositories** | Secure storage for proprietary images (paid plans) |
| **Official images** | ⭐ Verified images from software vendors (`nginx`, `mysql`, `redis`, `node`, `python`) |
| **Automated builds** | Link GitHub/Bitbucket for automatic image builds |
| **Webhooks** | Trigger actions after a successful push |
| **Organizations & teams** | Collaborate with team members |
| **Image scanning** | Security vulnerability scanning |

### Common Docker Hub commands
```bash
# Login to Docker Hub
docker login
docker login registry.example.com          # a private registry
docker logout

# Tag image for Docker Hub  (must be username/repo:tag!)
docker tag myapp:1.0 username/myapp:1.0

# Push image to Docker Hub
docker push username/myapp:1.0

# Pull image from Docker Hub
docker pull username/myapp:1.0

# Search for images
docker search nginx
```

> ⚠️ **You cannot push `myapp:1.0`** — a push needs a namespace: `username/myapp:1.0` or
> `registry.host/project/myapp:1.0`. Forgetting this is the #1 first-push error.

### Alternative registries
| Registry | Notes |
|---|---|
| **AWS ECR** (Elastic Container Registry) | Native to AWS/EKS; login via `aws ecr get-login-password` |
| **Google Container Registry / Artifact Registry** | GCP |
| **Azure Container Registry (ACR)** | Azure |
| **GitHub Container Registry (GHCR)** | `ghcr.io/user/image` — pairs perfectly with GitHub Actions |
| **Harbor** | Self-hosted, open-source, with scanning + RBAC |
| **GitLab Container Registry** | Bundled with GitLab CI |
| **Nexus / Artifactory** | Enterprise multi-format artifact repositories |

### Image tag strategy ⭐
| Tag | Verdict |
|---|---|
| `myapp:latest` | ❌ Ambiguous — you never know what's deployed |
| `myapp:1.4.2` | ✅ Semantic version |
| `myapp:9088568` | ✅ Git commit SHA — perfectly traceable |
| `myapp:1.4.2-alpine` | ✅ Version + base variant |
| `myapp@sha256:...` | ✅✅ Immutable digest — maximum reproducibility |

**Official base image variants**
| Suffix | Meaning | Size |
|---|---|---|
| *(none)* e.g. `python:3.12` | Full Debian-based | ~1 GB |
| `-slim` | Debian, stripped of extras | ~150 MB |
| `-alpine` | ⭐ Alpine Linux (musl libc) | ~50 MB |
| `-bookworm` / `-bullseye` | Pinned Debian release | varies |
| `distroless` (Google) | No shell, no package manager — most secure | tiny |

> ⚠️ **Alpine caveat:** it uses **musl** instead of **glibc**. Python packages with C extensions
> may need compiling, and rare glibc-dependent binaries break. `-slim` is a safe middle ground.

---

## 🛠️ Essential Commands

### Container lifecycle
```bash
docker run -d --name web -p 8080:80 nginx     # run
docker ps                                     # running containers
docker ps -a                                  # all containers
docker ps -q                                  # IDs only
docker ps --filter "status=exited"            # filter
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"   # ⭐ custom output
docker stop web                               # stop
docker start web                               # start
docker restart web                             # restart
docker pause web / docker unpause web          # pause / unpause
docker kill web                                # force stop
docker rm web                                  # remove
docker rm -f web                               # force remove
```

### Image management
```bash
docker build -t myapp:1.0 .                    # build from a Dockerfile
docker images                                  # list images
docker pull nginx:latest                       # pull
docker push username/myapp:1.0                 # push
docker rmi myapp:1.0                           # remove
docker image prune                             # remove dangling images
docker tag myapp:1.0 myapp:latest              # tag
```

### Dockerfile & image building
| Command | Description | Example |
|---|---|---|
| `docker build -t <name> .` | Build an image from a Dockerfile | `docker build -t myapp .` |
| `docker build -f <path/to/Dockerfile> .` | Use a specific Dockerfile | `docker build -f Dockerfile.dev .` |
| `docker history <image>` | Show image layer history | `docker history nginx` |
| `docker build --no-cache -t <image> .` | Build **without** using the cache | |
| `docker build --target <stage> -t <image> .` | Build a specific stage of a multi-stage build | |

*(Covered in depth in Session 7.)*

### System management
```bash
docker info                     # ⭐ system-wide Docker info (driver, root dir, counts)
docker version                  # client + server versions
docker system df                # ⭐ disk usage by images/containers/volumes/cache
docker events                   # real-time daemon event stream
docker login / logout
```

---

## 🔍 Inspection & Debugging

| Command | Description |
|---|---|
| `docker logs <container>` | View logs from a running/stopped container |
| `docker inspect <container>` | Show detailed low-level config of a container or image |
| `docker events` | Real-time events from the Docker daemon (useful for monitoring) |
| `docker top <container>` | Show running processes inside a container |
| `docker stats` | Live CPU, memory, I/O stats for running containers |
| `docker exec -it <container> /bin/bash` | Open a terminal inside a running container |
| `docker attach <container>` | Attach your terminal to a running container's output |
| `docker diff <container>` | Show what has changed inside a container's filesystem |
| `docker port <container>` | Show port mappings |
| `docker exec <container> env` | Show environment variables |

```bash
# ---- Logs ----
docker logs web
docker logs -f web                    # ⭐ follow live
docker logs --tail 100 web            # last 100 lines
docker logs --since 30m web           # last 30 minutes
docker logs -t web                    # with timestamps
docker logs web --tail 100 > container_logs.txt    # save to a file

# ---- Exec into a container ----
docker exec -it web /bin/bash         # ⭐ interactive shell
docker exec -it web sh                # ⭐ if bash isn't available (Alpine!)
docker exec web ps aux                # run a single command
docker exec web df -h
docker exec web netstat -tuln
docker exec web env                   # environment variables
docker exec -u root -it web sh        # ⭐ get in as root when the app runs as a user

# ---- Inspect ----
docker inspect web                                    # everything (big JSON)
docker inspect --format='{{.State.Status}}' web       # ⭐ one field
docker inspect --format='{{.State.ExitCode}}' web     # ⭐ why did it die?
docker inspect --format='{{.State.OOMKilled}}' web    # ⭐ killed for memory?
docker inspect --format='{{.NetworkSettings.IPAddress}}' web
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' web
docker inspect --format='{{json .State.Health}}' web | jq

# ---- Live resources ----
docker stats                          # ⭐ all containers, live
docker stats web --no-stream          # one snapshot (scriptable)
docker top web                        # processes inside

# ---- Events ----
docker events                                     # everything, live
docker events --filter container=web              # ⭐ one container
docker events --filter type=container
docker events --since 1h

# ---- Filesystem changes ----
docker diff web         # A=added, C=changed, D=deleted vs the image
docker port web         # 80/tcp -> 0.0.0.0:8080
```

> 💡 **`attach` vs `exec`:** `attach` connects to the **existing PID 1** (Ctrl+C may kill the
> container!). `exec` starts a **new process** — almost always what you want.

---

## 🧹 Cleanup Commands

Docker silently eats disk. These are the commands that get it back.

| Command | Description |
|---|---|
| `docker system prune` | Remove unused containers, networks, dangling images and build cache |
| `docker system prune -a` | Remove **all** unused images (not just dangling ones) |
| `docker container prune` | Remove only stopped containers |
| `docker image prune` | Remove dangling (untagged) images |
| `docker image prune -a` | Remove all unused images |
| `docker volume prune` | Remove all unused volumes |
| `docker network prune` | Remove all unused networks |
| `docker builder prune` | Clean the build cache |
| `docker system df` | Show disk usage |

> ⚠️ **Note:** these are powerful cleanup tools — use them carefully.
> `prune -a --volumes` on a dev machine can delete database volumes you wanted.

### Bulk deletion of all containers, images, volumes

| Task | Command |
|---|---|
| Remove all containers (stopped & running) | `docker rm -f $(docker ps -aq)` |
| Remove all images | `docker rmi -f $(docker images -q)` |
| Remove all volumes | `docker volume rm $(docker volume ls -q)` |
| Remove all networks | `docker network rm $(docker network ls -q)` |

**How these one-liners work** (from the session's `docker.md`):
```bash
docker stop $(docker ps -q)
#   docker ps -q  → gets IDs of RUNNING containers
#   docker stop   → stops them

docker rm $(docker ps -aq)
#   docker ps -aq → gets IDs of ALL containers, including stopped ones
#   docker rm     → removes them

# Force remove all containers — stop + remove in one command
docker rm -f $(docker ps -aq)

# Remove all Docker images
docker rmi $(docker images -q)
docker rmi -f $(docker images -q)       # force

# Complete Docker cleanup
docker system prune -a
docker system prune -a --volumes        # ⚠️ also wipes volumes (DATA LOSS)
```

> 💡 The pattern is always **`$(command that lists IDs)`** fed into a command that takes IDs —
> exactly the command substitution from Session 3. If the list is empty the command errors
> harmlessly; add `2>/dev/null || true` in scripts.

**Disk-space triage**
```bash
docker system df            # ⭐ start here
docker system df -v         # per-image/volume breakdown
du -sh /var/lib/docker      # the real footprint on disk
```

---

## 📏 Resource Limits & Health Checks

### Limiting resources (cgroups in practice)
```bash
docker run -d \
  --name web \
  --memory="512m" \          # ⭐ hard memory cap — exceeding it = OOM kill (exit 137)
  --memory-swap="1g" \       # memory + swap total
  --cpus="1.5" \             # ⭐ 1.5 CPU cores' worth of time
  --cpu-shares=512 \         # relative weight under contention (default 1024)
  --pids-limit=200 \         # max processes (fork-bomb protection)
  nginx

docker update --memory 1g --cpus 2 web    # change limits on a running container
docker stats                              # verify actual usage vs limits
```

> ⚠️ **Always set memory limits in production.** Without them, one leaking container can OOM the
> entire host and take every other container down with it.

### Health checks
A **HEALTHCHECK** teaches Docker how to tell "the process is running" from "the app actually works".

**In a Dockerfile**
```dockerfile
FROM nginx:alpine

HEALTHCHECK --interval=30s \
            --timeout=3s \
            --start-period=5s \
            --retries=3 \
  CMD curl -f http://localhost/health || exit 1

# or with wget (Alpine has wget built in, not curl)
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1
```

**Parameters**
| Flag | Meaning | Default |
|---|---|---|
| `--interval` | How often to run the check | 30s |
| `--timeout` | Max time for the check to complete | 30s |
| `--start-period` | ⭐ Grace period before failures count (slow-starting apps) | 0s |
| `--retries` | Consecutive failures before marking **unhealthy** | 3 |

**In Docker Compose**
```yaml
services:
  web:
    image: myapp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    image: postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Health states**
| State | Meaning |
|---|---|
| `starting` | Health check not yet run (within `start_period`) |
| `healthy` | ✅ Check passing |
| `unhealthy` | ❌ Check failing after `retries` |

```bash
docker ps                                                  # STATUS shows (healthy)/(unhealthy)
docker inspect --format='{{json .State.Health}}' web | jq  # ⭐ detailed history
docker inspect web | grep -A 10 Health
```

> 🧠 **This concept scales up:** Kubernetes takes it further with **liveness** (restart if broken),
> **readiness** (remove from load balancing) and **startup** probes — covered later in the course.

---

## 🔢 Container Exit Codes

Read these from `docker ps -a` or `docker inspect --format='{{.State.ExitCode}}'`.

| Exit code | Meaning | Common cause |
|---|---|---|
| **0** | Success | Normal exit |
| **1** | Application error | Bug in the application |
| **125** | Docker daemon error | Bad `docker run` flag |
| **126** | Command not executable | Permission issue (missing `chmod +x`) |
| **127** | ⭐ Command not found | Wrong command/path in `CMD`/`ENTRYPOINT`, or missing binary |
| **137** | ⭐ SIGKILL (**OOM**) | **Out of memory** — or `docker kill` |
| **139** | SIGSEGV | Segmentation fault |
| **143** | SIGTERM | Graceful shutdown (`docker stop`) |

> 🧠 These are the Linux **128 + signal number** codes from Session 3 — the shell and Docker
> speak the same language. `137 = 128 + 9 (SIGKILL)`, `143 = 128 + 15 (SIGTERM)`.

---

## 🩺 Troubleshooting a Failing Container

### Step-by-step debugging process

**1. Check container status**
```bash
docker ps -a
# Check status (running, exited, restarting) and note the EXIT CODE
# 0 = success, non-zero = error
```

**2. View container logs**
```bash
docker logs <container_name>
docker logs -f <container_name>            # follow in real time
docker logs --tail 50 <container_name>     # last 50 lines
docker logs --since 30m <container_name>   # from a specific time
docker logs -t <container_name>            # include timestamps
```

**3. Inspect container details**
```bash
docker inspect <container_name>                                  # full config
docker inspect --format='{{.State.Status}}' <container_name>
docker inspect --format='{{.NetworkSettings.IPAddress}}' <container_name>
```

**4. Check container events**
```bash
docker events --filter container=<container_name>
```

**5. Execute commands inside the container**
```bash
docker exec -it <container_name> /bin/bash
docker exec -it <container_name> sh          # if bash isn't available
docker exec <container_name> ps aux
docker exec <container_name> df -h
docker exec <container_name> netstat -tuln
```

**6. Check resource usage**
```bash
docker stats <container_name>
docker inspect --format='{{.State.OOMKilled}}' <container_name>   # ⭐ ran out of memory?
```

**7. Review Dockerfile and build**
```bash
docker history <image_name>
docker build --no-cache -t <image_name> .
```

**8. Container exits instantly, so you can't `exec` into it?**
```bash
docker run -it --entrypoint /bin/sh <image>    # ⭐ bypass the broken CMD and look around
docker logs <container>                        # logs survive even after the container exits
docker cp <container>:/app/config.yml ./       # pull files out of a dead container
```

### Troubleshooting checklist
- [ ] Container logs show errors?
- [ ] Container has enough memory/CPU?
- [ ] Ports are available and not conflicting?
- [ ] Environment variables set correctly?
- [ ] Volumes mounted correctly?
- [ ] Network connectivity working?
- [ ] Base image compatible?
- [ ] Dependencies installed correctly?

### Symptom → cause table
| Symptom | Likely cause & fix |
|---|---|
| Exits immediately, code **0** | `CMD` isn't a **foreground** process (e.g. `nginx` without `daemon off;`) |
| Exit **127** | Command/binary not found — wrong path, or not installed in the image |
| Exit **126** | Script not executable → `RUN chmod +x entrypoint.sh` |
| Exit **137** | ⭐ OOM-killed → raise `--memory` or fix the leak; verify with `.State.OOMKilled` |
| `CrashLoopBackOff`-style restart loop | App fails on startup — read the logs; check env vars/config/DB availability |
| `port is already allocated` | Another process/container holds the host port → `ss -tulnp \| grep :8080` |
| Reachable inside, not from host | App bound to `127.0.0.1` instead of **`0.0.0.0`** ⭐ |
| `ImagePull`/`manifest unknown` | Wrong image name/tag, or you need `docker login` |
| Data lost after `docker rm` | No volume was used — see Session 8 |
| Can't resolve another container's name | Not on a **user-defined** network — see Session 8 |
| Build is slow every time | Layer cache invalidated too early — copy dependency files first (Session 7) |

---

## 🐝 Docker Swarm (a brief intro)

**Docker Swarm** is Docker's **native clustering and orchestration tool** for managing a cluster
of Docker engines.

### Key features
- **Cluster management** — multiple Docker hosts act as a single virtual host
- **Declarative service model** — define the desired state
- **Scaling** — scale services up/down easily
- **Load balancing** — built-in
- **Rolling updates** — zero-downtime deployments
- **Service discovery** — automatic DNS-based discovery

```bash
# Initialize a manager node
docker swarm init --advertise-addr 192.168.1.100

# Join worker nodes (run on the worker machines)
docker swarm join --token <worker-token> 192.168.1.100:2377

docker node ls                                     # view nodes

# Deploy a service
docker service create --name web --replicas 3 --publish 8080:80 nginx
docker service ls                                  # list services
docker service ps web                              # tasks/replicas of a service
docker service scale web=5                         # scale
docker service update --image nginx:1.21 web       # ⭐ rolling update
docker service rm web                              # remove
```

### Docker Swarm vs Kubernetes
| Feature | **Docker Swarm** | **Kubernetes** |
|---|---|---|
| Complexity | Simple | Complex |
| Setup | Easy | Difficult |
| Learning curve | Low | High |
| Scalability | Good | Excellent |
| Ecosystem | Limited | Extensive |
| Use case | Small–medium | **Enterprise** |

> 🧭 **Reality check:** **Kubernetes won.** Swarm is worth understanding conceptually (it
> introduces services, replicas, rolling updates and overlay networks with almost no ceremony),
> but the course — and the industry — moves on to Kubernetes.

---

## 📋 Quick Cheat Sheet

```bash
# ---------- IMAGES ----------
docker pull nginx:1.27-alpine
docker images                    # docker images -q     (IDs)
docker build -t myapp:1.0 .
docker tag myapp:1.0 user/myapp:1.0
docker push user/myapp:1.0
docker history myapp:1.0
docker rmi myapp:1.0
docker save -o app.tar myapp:1.0 ; docker load -i app.tar

# ---------- CONTAINERS ----------
docker run -d --name web -p 8080:80 nginx
docker run -it --rm ubuntu bash
docker ps ; docker ps -a ; docker ps -q
docker stop web ; docker start web ; docker restart web
docker rm -f web
docker rename web webserver

# ---------- DEBUG ----------
docker logs -f --tail 100 web
docker exec -it web sh
docker inspect web
docker inspect --format='{{.State.ExitCode}}' web
docker stats ; docker top web ; docker diff web ; docker port web
docker events --filter container=web
docker run -it --entrypoint /bin/sh myapp     # broken CMD? look inside

# ---------- LIMITS ----------
docker run -d --memory=512m --cpus=1.0 --restart unless-stopped nginx

# ---------- CLEANUP ----------
docker system df
docker rm -f $(docker ps -aq)
docker rmi -f $(docker images -q)
docker system prune -a
docker system prune -a --volumes     # ⚠️ deletes data

# ---------- SYSTEM ----------
docker info ; docker version ; docker login
```

---

## 🔑 Key Takeaways

1. Understand **Docker architecture** deeply (client, daemon, registry; containerd + runc)
2. Know the difference between **images and containers** (class vs object)
3. Master the **essential Docker commands**
4. Containers **share the host kernel**; VMs bring their own → MBs/seconds vs GBs/minutes
5. Images are **immutable, layered and cached**; containers add a thin **writable layer**
6. A container **lives only as long as its PID 1** → `CMD` must run in the foreground
7. Data written inside a container is **lost on `docker rm`** → use volumes (Session 8)
8. Read **exit codes** (`137` = OOM, `127` = command not found, `143` = SIGTERM)
9. Always **pin image tags** and **set resource limits** in production
10. Know when **Docker Swarm** vs **Kubernetes** applies

---

## 🔗 References
- Docker overview — https://docs.docker.com/get-started/docker-overview/
- Docker architecture (GeeksforGeeks) — https://www.geeksforgeeks.org/devops/architecture-of-docker/
- Official docs — https://docs.docker.com
- Docker Hub — https://hub.docker.com
- Play with Docker — https://labs.play-with-docker.com
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
