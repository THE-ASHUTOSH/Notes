# Session 8 — Docker Networking, Volumes & Compose 🔗

> Single containers are easy. Real applications are **several containers that must find each
> other, keep their data, and start together**. This session covers the three mechanisms that
> make that possible: **networks** (communication), **volumes** (persistence) and
> **Compose** (orchestration of a single-host stack).

---

## 📑 Table of Contents
1. [Docker Networking](#-docker-networking)
2. [Network Drivers](#-network-drivers-networking-modes)
3. [Container-to-Container Communication](#-container-to-container-communication)
4. [Port Mapping](#-port-mapping)
5. [Network Commands](#-network-commands)
6. [Data Persistence: The Problem](#-data-persistence-the-problem)
7. [Docker Volumes](#-docker-volumes)
8. [Bind Mounts](#-bind-mounts)
9. [tmpfs Mounts](#-tmpfs-mounts)
10. [Volume vs Bind Mount](#-volume-vs-bind-mount)
11. [Volume Commands](#-volume-commands)
12. [Docker Compose](#-docker-compose)
13. [Compose File Reference](#-compose-file-reference)
14. [Compose Commands](#-compose-commands)
15. [Worked Examples from Class](#-worked-examples-from-class)
16. [The 3-Tier Demo Application](#-the-3-tier-demo-application-full-walkthrough)
17. [Troubleshooting](#-troubleshooting)
18. [Cheat Sheet](#-quick-cheat-sheet)

---

## 🌐 Docker Networking

Every container gets its **own network namespace** — its own interfaces, IP address, routing table
and port space. Docker then wires those namespaces together according to a **network driver**.

```
                        HOST
   ┌──────────────────────────────────────────────────┐
   │   eth0: 192.168.1.50  (the host's real NIC)      │
   │              │                                    │
   │        ┌─────▼──────┐  iptables NAT / DNAT        │
   │        │  docker0   │  bridge  172.17.0.1         │
   │        └──┬──────┬──┘                             │
   │           │      │        veth pairs              │
   │      ┌────▼──┐ ┌─▼─────┐                          │
   │      │ web   │ │  db   │  ← each has its own      │
   │      │.0.2   │ │ .0.3  │    netns + IP            │
   │      └───────┘ └───────┘                          │
   └──────────────────────────────────────────────────┘
```

**Key facts**
- The default bridge is **`docker0`**, subnet **`172.17.0.0/16`** (a private range — Session 4).
- Containers get IPs like `172.17.0.2`, `172.17.0.3`.
- Container→internet works out of the box via **SNAT/masquerade**.
- Internet→container requires **published ports** (**DNAT**) — `-p`.
- ⭐ Container IPs are **ephemeral** — they change on restart. **Never hard-code them; use names.**

---

## 🚗 Network Drivers (networking modes)

Docker provides several networking modes for container communication.

### 1. Bridge Network (default)
- **Default network for containers**
- **Isolated network on the host**
- **Containers can communicate via IP**
- Uses a **software bridge on the host** (`docker0`)
- **Good for single-host deployments**

```bash
# Create a bridge network
docker network create my-bridge

# Run a container on the bridge network
docker run -d --name web --network my-bridge nginx

# Containers can ping each other by name
docker exec web1 ping web2
```

> ⭐ **Critical distinction — the default bridge vs a user-defined bridge:**
>
> | | Default `bridge` | **User-defined** bridge (`docker network create`) |
> |---|---|---|
> | **DNS / name resolution** | ❌ **None** — you must use IPs | ✅ **Yes** — resolve by container name |
> | Isolation | All containers share it | Only attached containers can talk |
> | Attach/detach a running container | ❌ | ✅ |
> | Recommendation | Legacy | ⭐ **Always use this** |
>
> This is *the* reason `docker-compose` works so smoothly: it **automatically creates a
> user-defined bridge** for your project, so services can reach each other by service name.

### 2. Host Network
- **Container shares the host's network namespace**
- **No network isolation**
- **Container uses the host's IP directly**
- **Better performance** (no NAT overhead)
- **Port conflicts possible**

```bash
docker run -d --name web --network host nginx

# Container accessible on the host's IP
curl http://localhost:80
```
> `-p` is **ignored** with `--network host` — the container binds host ports directly.
> Use it for high-throughput/low-latency needs (packet processing, monitoring agents).
> ⚠️ Linux only — behaves differently on Docker Desktop for Mac/Windows.

### 3. None Network
- **No networking**
- **Complete network isolation**
- **Container has only a loopback interface**
- **Used for security/testing**

```bash
docker run -d --name isolated --network none nginx
```
Good for batch jobs that only process mounted files and must never reach the network.

### 4. Overlay Network
- **Multi-host networking**
- **Used with Docker Swarm or Kubernetes**
- **Containers on different hosts can communicate**
- **Encrypted communication possible**

```bash
# Create overlay network (Swarm mode)
docker network create --driver overlay my-overlay

# Deploy a service using the overlay
docker service create --name web --network my-overlay nginx
```

### 5. Macvlan Network
- **Assigns a MAC address to the container**
- **Container appears as a physical device on the network**
- **Direct Layer 2 connectivity**
- **Used for legacy apps requiring direct network access**

```bash
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 my-macvlan
```

### Driver selection guide
| Driver | Scope | Use when |
|---|---|---|
| **bridge** (user-defined) | Single host | ⭐ Default choice for app stacks |
| **host** | Single host | Maximum performance, no isolation needed |
| **none** | Single host | Total isolation |
| **overlay** | Multi-host | Swarm/cluster services |
| **macvlan** | Single host, L2 | Container needs to look like a physical device |
| **ipvlan** | Single host, L2/L3 | Like macvlan but shares the host MAC |

---

## 🔗 Container-to-Container Communication

### The rule ⭐
> **On a user-defined network, containers reach each other by CONTAINER NAME (or service name in
> Compose), on the container's OWN port. No port publishing is needed for internal traffic.**

Docker runs an **embedded DNS server at `127.0.0.11`** inside each container on a user-defined
network, which resolves container/service names to their current IP.

```bash
# 1. Create a user-defined network
docker network create app-net

# 2. Run containers on it
docker run -d --name db    --network app-net -e MYSQL_ROOT_PASSWORD=root mysql:8.0
docker run -d --name api   --network app-net -p 5000:5000 my-api
docker run -d --name web   --network app-net -p 8080:80 nginx

# 3. They talk by NAME
docker exec api ping db                 # ⭐ resolves via Docker DNS
docker exec api curl http://web:80      # container port 80, NOT the published 8080
docker exec web nslookup db
```

**Application configuration follows the same rule** — this is exactly what the class demo does:
```python
# Flask backend connecting to the MySQL container
mysql.connector.connect(
    host="database",     # ⭐ the SERVICE NAME, not an IP, not localhost
    user="root",
    password="root",
    database="demo"
)
```
```nginx
# nginx proxying to the backend container
location /api {
    proxy_pass http://backend:5000/api;   # ⭐ service name + container port
}
```

### The four mistakes everyone makes
| Mistake | Why it fails | Fix |
|---|---|---|
| `host="localhost"` | ⭐ Inside a container, `localhost` is **that container itself**, not the host or another container | Use the **service name** |
| `host="127.0.0.1"` | Same problem | Use the service name |
| Using the **published** host port (`backend:8080`) | Publishing maps *host→container*; internal traffic uses the **container's own** port | Use the container port (`backend:5000`) |
| Containers on the **default** bridge | ⭐ No DNS there — names don't resolve | Create a user-defined network / use Compose |

### Reaching the host from inside a container
```bash
host.docker.internal          # ⭐ Docker Desktop (Mac/Windows), and Linux with the flag below
docker run --add-host=host.docker.internal:host-gateway ...   # Linux
```

### Network segmentation ⭐ (a security pattern)
A container can join **multiple networks** — which lets you build tiers:
```bash
docker network create frontend_net
docker network create backend_net

docker run -d --name frontend --network frontend_net -p 8080:80 nginx
docker run -d --name backend  --network frontend_net my-api      # in the frontend tier
docker network connect backend_net backend                        # ⭐ ALSO in the backend tier
docker run -d --name database --network backend_net mysql:8.0
```
Result:
```
   Internet ──▶ frontend  ─┐
                           ├─ frontend_net ─▶ backend ─┐
                           ┘                            ├─ backend_net ─▶ database
                                                        ┘
   ⭐ frontend CANNOT reach database at all — no shared network.
```
This is the **defence-in-depth** layout used in the demo app below.

---

## 🔌 Port Mapping

### Syntax
```bash
docker run -p [host_port]:[container_port] image_name
```

### Examples

**1. Basic port mapping**
```bash
docker run -d -p 8080:80 nginx
# Access: http://localhost:8080
```

**2. Multiple port mappings**
```bash
docker run -d \
  -p 8080:80 \
  -p 8443:443 \
  nginx
```

**3. Bind to a specific IP**
```bash
docker run -d -p 127.0.0.1:8080:80 nginx
# ⭐ Only accessible from localhost — not exposed on the network
```

**4. Random host port**
```bash
docker run -d -p 80 nginx
docker port <container_name>       # check the assigned port
```

**5. Expose all ports**
```bash
docker run -d -P nginx
# -P maps all EXPOSEd ports to random host ports
```

**6. UDP port mapping**
```bash
docker run -d -p 53:53/udp dns-server
```

### `EXPOSE` in the Dockerfile
```dockerfile
FROM nginx
EXPOSE 80 443

# EXPOSE is documentation only
# Doesn't actually publish ports
# Must use -p or -P at runtime
```

### Checking port mappings
```bash
docker port <container_name>
# Example output:
# 80/tcp -> 0.0.0.0:8080
# 443/tcp -> 0.0.0.0:8443

docker inspect <container_name> | grep -A 10 Ports
docker ps                          # the PORTS column
ss -tulnp | grep 8080              # ⭐ verify from the host side (Session 4)
```

### The mental model ⭐
```
  -p 8080:80
     │    └── CONTAINER port — where the app inside actually listens
     └─────── HOST port — what you type in the browser

  Browser :8080 ──▶ Host ──iptables DNAT──▶ Container :80
```

**Rules to remember**
- **Left = host, right = container.** (Compose uses the same order.)
- ⭐ The app inside must bind **`0.0.0.0`**, not `127.0.0.1`, or the mapping delivers nothing.
- Two containers **cannot** publish the same host port → `port is already allocated`.
- Publishing is only needed for **external** access; internal container↔container traffic
  doesn't need it.
- Default bind address is `0.0.0.0` (all interfaces) — use `127.0.0.1:PORT:PORT` to keep a
  service local-only (great for databases in dev).

---

## 🧰 Network Commands

| Command | Description | Example |
|---|---|---|
| `docker network ls` | List networks | `docker network ls` |
| `docker network create <name>` | Create a network | `docker network create mynetwork` |
| `docker network inspect <name>` | Show network details | `docker network inspect mynetwork` |
| `docker run --network <name> <image>` | Attach a container to a network | `docker run --network mynetwork nginx` |
| `docker network connect` | Connect a **running** container to a network | `docker network connect my-network web` |
| `docker network disconnect` | Disconnect a container from a network | `docker network disconnect my-network web` |
| `docker network rm <name>` | Remove a custom network | `docker network rm mynetwork` |
| `docker network prune` | Remove unused networks | `docker network prune` |

```bash
docker network ls
# NETWORK ID     NAME      DRIVER    SCOPE
# abc123...      bridge    bridge    local     ← the default
# def456...      host      host      local
# ghi789...      none      null      local

docker network create app-net                          # bridge by default
docker network create --driver bridge app-net
docker network create --subnet=172.20.0.0/16 \
                      --gateway=172.20.0.1 custom-net  # ⭐ custom subnet
docker network create --internal secure-net            # ⭐ NO external/internet access

docker network inspect app-net                         # ⭐ see attached containers + their IPs
docker network inspect bridge | jq '.[0].Containers'

docker network connect app-net web                     # attach a running container
docker network disconnect app-net web

docker network rm app-net
docker network prune -f
```

---

## 💾 Data Persistence: The Problem

### What happens to data when a container is deleted?

**Without volumes:**
- **Data is lost when the container is deleted**
- The container has a **writable layer on top of the image**
- That **writable layer is deleted with the container**

**Example (data loss):**
```bash
docker run -it --name test ubuntu bash
# Inside container: echo "important data" > /data.txt
# Exit container

docker rm test
# Data is GONE forever
```

**With volumes:**
- **Data persists after container deletion**
- The **volume exists independently**
- It **can be reused by new containers**

**Example (data persistence):**
```bash
docker volume create app-data

docker run -it --name test -v app-data:/data ubuntu bash
# Inside container: echo "important data" > /data/file.txt
# Exit container

docker rm test

docker run -it --name test2 -v app-data:/data ubuntu bash
# Inside container: cat /data/file.txt
# Output: important data (STILL THERE!)
```

> 🧠 **Why this design?** Containers are meant to be **stateless and disposable** — you should be
> able to kill and recreate one at any moment. State therefore has to live *outside* the container.
> Volumes are that outside.

---

## 📂 Docker Volumes

> **Docker Volumes provide persistent data storage that exists independently of the container
> lifecycle.**

### Why use volumes
| Reason | Detail |
|---|---|
| **Data persistence** | Data survives container deletion |
| **Data sharing** | Multiple containers can share the same volume |
| **Performance** | Better I/O than bind mounts (especially on Mac/Windows) |
| **Backup/restore** | Easier to back up and migrate |
| **Docker-managed** | Docker handles the storage drivers |

### Types of mounts

```
       ┌─────────────── CONTAINER ───────────────┐
       │                                         │
       │   /var/lib/mysql  ◀── VOLUME ───────────┼──▶ /var/lib/docker/volumes/db_data
       │                       (Docker-managed)  │        ⭐ production
       │                                         │
       │   /app            ◀── BIND MOUNT ───────┼──▶ /home/me/project
       │                       (any host path)   │        ⭐ development
       │                                         │
       │   /tmp/cache      ◀── TMPFS ────────────┼──▶ RAM only (never on disk)
       │                                         │        ⭐ secrets/scratch
       └─────────────────────────────────────────┘
```

### 1. Volumes (recommended ⭐)
- **Managed by Docker**
- **Stored in `/var/lib/docker/volumes/`**
- **Best for production**
- **Can be named or anonymous**

```bash
# Create a named volume
docker volume create my-data

# Run a container with the volume
docker run -d \
  --name web \
  -v my-data:/app/data \
  nginx

docker volume ls
docker volume inspect my-data
docker volume rm my-data
docker volume prune               # remove unused volumes
```

**Named vs anonymous**
```bash
-v my-data:/app/data     # ⭐ NAMED — you can find it, reuse it, back it up
-v /app/data             # ANONYMOUS — random hash name, easily orphaned
```

**Sharing a volume between containers**
```bash
docker volume create shared-data
docker run -d -v shared-data:/data --name c1 alpine sleep 3600
docker run -d -v shared-data:/data --name c2 alpine sleep 3600
docker exec c1 sh -c 'echo hello > /data/msg'
docker exec c2 cat /data/msg          # → hello
docker run -v shared-data:/data:ro alpine cat /data/msg   # ⭐ :ro = read-only
```

---

## 📎 Bind Mounts

- **Mount any host directory into the container**
- **Full path required**
- **Good for development** (code changes reflect immediately)
- **Host-dependent** (less portable)

```bash
# Bind mount syntax
docker run -d \
  --name web \
  -v /host/path:/container/path \
  nginx

# Or using --mount (more explicit)
docker run -d \
  --name web \
  --mount type=bind,source=/host/path,target=/container/path \
  nginx
```

**Practical forms**
```bash
docker run -v "$(pwd)":/app -w /app node:24-alpine npm run dev   # ⭐ live-reload dev loop
docker run -v "$(pwd)/nginx.conf":/etc/nginx/conf.d/default.conf:ro nginx  # ⭐ mount ONE config file
docker run -v /var/run/docker.sock:/var/run/docker.sock ...       # ⚠️ full host control — careful!
```

> ⭐ **The killer development use case:** bind-mount your source into the container. Edit a file
> in your editor → the change is instantly visible inside the container → nodemon/flask-reload
> restarts. **No rebuild required.**

> ⚠️ **Bind-mount gotchas**
> - The mount **shadows** whatever was in the container at that path. Bind-mounting `/app` over
>   an image that installed `node_modules` there **hides** them → "module not found". Fix with an
>   anonymous volume on top: `-v "$(pwd)":/app -v /app/node_modules`.
> - Relative paths need `$(pwd)`; Docker requires **absolute** paths.
> - **File permissions/UID mismatches** between host and container are a common source of
>   "permission denied".
> - Slower on Docker Desktop for Mac/Windows (crosses the VM boundary).

---

## 🌪️ tmpfs Mounts

- **Stored in host memory only**
- **No disk I/O**
- **Temporary data** (passwords, session data)
- **Data lost when the container stops**

```bash
docker run -d \
  --name web \
  --tmpfs /app/temp \
  nginx

docker run -d --mount type=tmpfs,destination=/app/cache,tmpfs-size=64m nginx
```
Pairs beautifully with `--read-only`:
```bash
docker run -d --read-only --tmpfs /tmp --tmpfs /var/run nginx   # ⭐ hardened container
```

---

## ⚖️ Volume vs Bind Mount

| Feature | **Volume** | **Bind Mount** |
|---|---|---|
| **Managed by** | **Docker** | **User** |
| **Location** | `/var/lib/docker/volumes/` | **Any host path** |
| **Portability** | **High** | **Low** |
| **Performance** | **Better** | Good |
| **Use case** | ⭐ **Production** | ⭐ **Development** |
| Exists before the container? | Docker creates it | Must exist on the host (or Docker creates an empty dir) |
| Backup | `docker volume` commands / tar via a helper container | Normal filesystem tools |
| Works in Swarm/K8s | ✅ (with drivers) | ❌ Node-specific |
| CLI | `-v name:/path` | `-v /host/path:/path` |

**How Docker decides which one you meant:** if the part before `:` **starts with `/` or `.`**
it's a **bind mount**; otherwise it's a **named volume**. One stray slash changes the meaning.

### Real-world example (database)
```bash
# Run MySQL with a persistent volume
docker run -d \
  --name mysql \
  -e MYSQL_ROOT_PASSWORD=secret \
  -v mysql-data:/var/lib/mysql \
  mysql:8.0

# Data persists even after container removal
docker rm -f mysql
docker run -d \
  --name mysql-new \
  -e MYSQL_ROOT_PASSWORD=secret \
  -v mysql-data:/var/lib/mysql \
  mysql:8.0
# Data still there!
```

### Best practices
- **Always use volumes for important data**
- **Use bind mounts for development only**
- **Regular volume backups**
- **Monitor volume disk usage**

**Backup & restore a volume**
```bash
# Backup
docker run --rm -v mysql-data:/data -v "$(pwd)":/backup alpine \
  tar czf /backup/mysql-backup.tar.gz -C /data .

# Restore
docker run --rm -v mysql-data:/data -v "$(pwd)":/backup alpine \
  sh -c "cd /data && tar xzf /backup/mysql-backup.tar.gz"
```

**Where the data actually lives**
```bash
docker volume inspect mysql-data --format '{{.Mountpoint}}'
# /var/lib/docker/volumes/mysql-data/_data
sudo ls /var/lib/docker/volumes/mysql-data/_data
```
> ⚠️ `docker system prune -a --volumes` **deletes your database volumes**. Read the prompt.

---

## 🗄️ Volume Commands

| Command | Description | Example |
|---|---|---|
| `docker volume create <name>` | Create a new volume | `docker volume create mydata` |
| `docker volume ls` | List volumes | `docker volume ls` |
| `docker volume inspect <volume>` | Volume details | `docker volume inspect mydata` |
| `docker run -v <volume>:/path <image>` | Attach a volume to a container | `docker run -v mydata:/app/data nginx` |
| `docker volume rm <volume>` | Delete a volume | `docker volume rm mydata` |
| `docker volume prune` | Delete all unused volumes | `docker volume prune` |

```bash
docker volume create mydata
docker volume ls
docker volume ls -q
docker volume ls --filter dangling=true       # ⭐ orphaned volumes
docker volume inspect mydata
docker volume rm mydata
docker volume rm $(docker volume ls -q)       # ⚠️ remove ALL volumes
docker volume prune
docker system df -v                            # ⭐ which volumes are eating disk
```

---

## 🎼 Docker Compose

> **Docker Compose is a tool for defining and running multi-container Docker applications using
> a YAML file.**

### Key benefits
- **Single file defines the entire application stack**
- **Easy orchestration of multiple containers**
- **Simplified commands** (one command to start/stop all)
- **Networking automatically configured** ⭐
- **Environment-specific configurations**
- **Development and testing made easy**

### Without Compose vs with Compose
```bash
# ❌ Without Compose — every time, in the right order, with the right flags
docker network create app-net
docker volume create db-data
docker run -d --name db --network app-net -v db-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=root mysql:8.0
docker run -d --name api --network app-net -e DB_HOST=db -p 5000:5000 my-api
docker run -d --name web --network app-net -p 8080:80 nginx

# ✅ With Compose
docker compose up -d
```

### What Compose does for you automatically ⭐
1. Creates a **user-defined bridge network** named `<project>_default` → **service names resolve
   via DNS out of the box**
2. Creates declared **volumes**
3. Starts services in **dependency order** (`depends_on`)
4. Names containers predictably: `<project>_<service>_<index>`
5. `docker compose down` tears the whole thing down cleanly

### `docker-compose` vs `docker compose`
| | Notes |
|---|---|
| `docker-compose` (v1, Python) | Legacy, standalone binary, hyphenated |
| **`docker compose`** (v2, Go plugin) ⭐ | Current, bundled with Docker; same YAML |
> Both are shown in this session's material. Prefer `docker compose` on new setups.
> Also: the top-level **`version:` key is deprecated** in Compose v2 — the class files correctly
> omit it and start directly with `services:`.

---

## 📜 Compose File Reference

Full-featured example:
```yaml
version: '3.8'        # (optional/deprecated in Compose v2)

services:
  # Web application
  web:
    build: .                          # build from a local Dockerfile
    ports:
      - "8080:80"                     # HOST:CONTAINER
    environment:
      - DATABASE_URL=mysql://db:3306/myapp
    depends_on:
      - db
      - redis
    volumes:
      - ./app:/app
    networks:
      - app-network
    restart: always

  # Database
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: secret
      MYSQL_DATABASE: myapp
    volumes:
      - db-data:/var/lib/mysql
    networks:
      - app-network
    restart: always

  # Cache
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    networks:
      - app-network
    restart: always

volumes:
  db-data:

networks:
  app-network:
    driver: bridge
```

### Top-level keys
| Key | Purpose |
|---|---|
| `services` | ⭐ The containers that make up the app |
| `volumes` | Named volumes to create |
| `networks` | Networks to create |
| `secrets` / `configs` | Swarm-mode secrets and config files |

### Service keys you'll use constantly
| Key | Meaning |
|---|---|
| `image:` | Use a pre-built image |
| `build:` | ⭐ Build from a Dockerfile (`build: ./dir` or `build: {context:, dockerfile:, args:}`) |
| `ports:` | Publish `"HOST:CONTAINER"` (⭐ **always quote** — `8080:80` unquoted can be parsed as a sexagesimal number) |
| `expose:` | Internal-only ports (documentation) |
| `environment:` | Env vars (list `- K=V` or map `K: V`) |
| `env_file:` | Load vars from a file (⭐ keep secrets out of the YAML) |
| `volumes:` | Named volumes and/or bind mounts |
| `networks:` | Which networks to join |
| `depends_on:` | ⭐ Start order — **not** readiness (see below) |
| `restart:` | `no` \| `always` \| `on-failure` \| `unless-stopped` |
| `command:` | Override the image's `CMD` |
| `entrypoint:` | Override the `ENTRYPOINT` |
| `healthcheck:` | Define a health test |
| `container_name:` | Fixed name (⚠️ blocks scaling) |
| `deploy.replicas` | Number of instances (Swarm) |

### ⚠️ `depends_on` does NOT wait for readiness
```yaml
backend:
  depends_on:
    - database          # ⭐ waits only for the container to START, not for MySQL to accept connections
```
MySQL takes 10–30 seconds to initialise, so your app will crash on first connect. Three fixes:

**A. Health-condition dependency (best)**
```yaml
services:
  database:
    image: mysql:8.0
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-proot"]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 30s

  backend:
    build: ./backend
    depends_on:
      database:
        condition: service_healthy     # ⭐ actually waits
```

**B. Retry in the application** (the robust, cloud-native answer — the DB *will* restart someday)

**C. A wait loop in the entrypoint** (Session 3):
```bash
until nc -z database 3306; do sleep 2; done
exec "$@"
```

### Environment variables & `.env`
```yaml
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}     # ⭐ from the .env file / shell
      MYSQL_DATABASE: ${DB_NAME:-demo}        # with a default
```
```bash
# .env  (⭐ add to .gitignore!)
DB_PASSWORD=supersecret
DB_NAME=demo
```
```bash
docker compose config       # ⭐ see the fully-resolved YAML with variables substituted
```

### Multiple compose files (per-environment overrides)
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
`docker-compose.override.yml` is merged automatically when present.

---

## ⌨️ Compose Commands

```bash
# ---- Start / stop ----
docker compose up                    # start all, attached (shows logs)
docker compose up -d                 # ⭐ start all in the background
docker compose up web                # start only 'web' and its dependencies
docker compose up -d --build         # ⭐ rebuild images before starting
docker compose up -d --force-recreate

docker compose stop                  # stop containers (keep them)
docker compose start                 # start existing stopped containers
docker compose restart
docker compose down                  # ⭐ stop AND remove containers + networks
docker compose down -v               # ⚠️ also remove VOLUMES (deletes data!)
docker compose down --rmi all        # also remove images

# ---- Inspect ----
docker compose ps                    # running services
docker compose logs                  # all logs
docker compose logs -f               # ⭐ follow all
docker compose logs -f web           # ⭐ follow one service
docker compose logs --tail=100 web
docker compose top                   # processes per service
docker compose config                # ⭐ validate + view the expanded YAML
docker compose images
docker compose port web 80

# ---- Interact ----
docker compose exec web bash         # ⭐ shell into a RUNNING service
docker compose exec db mysql -uroot -proot
docker compose run web python manage.py migrate    # ⭐ one-off task in a NEW container
docker compose run --rm web pytest
docker compose run --no-deps web python test.py

# ---- Build & scale ----
docker compose build
docker compose build --no-cache
docker compose pull                  # pull all images
docker compose up -d --scale web=3   # ⭐ run 3 replicas of 'web'
```

### `up` vs `run` vs `start` ⭐

**1. `docker compose up`**
- Creates **and** starts all services
- Builds images if needed
- Creates networks and volumes
- Attaches to containers (shows logs)
- Use `-d` for detached mode

**2. `docker compose run`**
- Runs **one-off commands** in a **new** container
- The service must be defined in `docker-compose.yml`
- Does **NOT** start other services (unless `depends_on`)
- Useful for running tests, migrations, etc.

**3. `docker compose start`**
- Starts **existing stopped** containers
- Does **NOT** create new containers
- Does **NOT** build images
- Quick restart of stopped services

| Command | Creates containers | Starts services | Builds images | One-off commands |
|---|---|---|---|---|
| **`up`** | Yes | Yes | If needed | No |
| **`run`** | Yes (one) | No | No | ✅ **Yes** |
| **`start`** | No | Yes | No | No |

**Workflow example**
```bash
docker compose up -d                                  # create and start all
docker compose stop                                   # stop all services
docker compose start                                  # restart stopped services
docker compose run web python manage.py migrate        # run a DB migration
docker compose down                                    # stop and remove all
```

### Use cases for Compose
- **Development environments** ⭐
- **Testing environments**
- **Microservices applications**
- **CI/CD pipelines**
- **Demo/training setups**

> 🧭 **Compose is single-host.** For multi-host production you move to **Kubernetes** (the next
> sessions) or Swarm. Compose remains the best local-dev tool.

---

## 🧪 Worked Examples from Class

### 1. Two services + `depends_on` (`session6-7-docker/docker-compose-app/`)
```yaml
services:

  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    depends_on:
      - redis

  redis:
    image: redis:alpine
```
```bash
docker compose up -d
docker compose ps
curl http://localhost:8080
docker compose exec web sh -c "ping -c2 redis"    # ⭐ resolves by service name
docker compose down
```
**Teaches:** the minimal Compose file; `image:`, `ports:`, `depends_on:`; automatic network +
DNS between `web` and `redis`. Note `redis` publishes **no** ports — it's reachable internally
on `redis:6379` but not from the host. ⭐ That's the correct default for a backing service.

---

### 2. Three tiers, no volume (`session8/docker-compose-app/`)
```yaml
services:

  frontend:
    image: nginx
    ports:
      - "8080:80"

  backend:
    image: nginx

  database:
    image: mysql
    environment:
      MYSQL_ROOT_PASSWORD: root
```
**Teaches:** the classic 3-tier shape and the `environment:` key (MySQL images *require*
`MYSQL_ROOT_PASSWORD` or they refuse to start).

⚠️ **The lesson here is the bug:** `database` has **no volume**, so
`docker compose down` destroys the entire database. Also `image: mysql` is unpinned.

---

### 3. Three tiers **with a named volume** (`session8/docker-compose.yml`)
```yaml
services:

  frontend:
    image: nginx
    ports:
      - "8080:80"

  backend:
    image: nginx

  database:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
    volumes:
      - db_data:/var/lib/mysql        # ⭐ the fix

volumes:
  db_data:                            # ⭐ declared at the top level
```
**Teaches:** the two-part volume pattern — declare it under top-level `volumes:`, then mount it in
the service. `/var/lib/mysql` is MySQL's data directory (Session 2: `/var/lib` = app state).
Now `docker compose down` (without `-v`) **keeps the data**, and `up` again finds the same database.

```bash
docker compose up -d
docker compose exec database mysql -uroot -proot -e "CREATE DATABASE demo;"
docker compose down                 # containers gone
docker compose up -d
docker compose exec database mysql -uroot -proot -e "SHOW DATABASES;"   # ⭐ demo is still there
docker volume ls                    # session8_db_data
```

---

## 🏗️ The 3-Tier Demo Application (full walkthrough)

`session8-docker-networking-volume/demo/` — this ties **everything** together:
multi-stage-free custom build, service DNS, a reverse proxy, network segmentation,
bind mounts for config, and a named volume for data.

### Architecture
```
                    :8080
  Browser ─────────────────┐
                           ▼
              ┌──────────────────────────┐
              │  frontend (nginx:latest) │  serves index.html
              │  /      → static files   │  proxies /api → backend:5000
              │  /api   → proxy_pass     │
              └────────────┬─────────────┘
                    frontend_net
                           │
              ┌────────────▼─────────────┐
              │  backend (build ./backend)│  Flask on :5000
              │  Python + mysql-connector │  connects to host="database"
              └────────────┬─────────────┘
                     backend_net
                           │
              ┌────────────▼─────────────┐
              │  database (mysql:8.0)     │  volume db_data → /var/lib/mysql
              └──────────────────────────┘

  ⭐ frontend is NOT on backend_net → it cannot reach the database directly.
  ⭐ Only the frontend publishes a port. backend and database are internal-only.
```

### `docker-compose.yml`
```yaml
services:

  frontend:
    image: nginx:latest
    ports:
      - "8080:80"
    volumes:
      - ./frontend/index.html:/usr/share/nginx/html/index.html
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf
    networks:
      - frontend_net

  backend:
    build: ./backend
    networks:
      - frontend_net
      - backend_net          # ⭐ the bridge between the two tiers
    depends_on:
      - database

  database:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: demo
    volumes:
      - db_data:/var/lib/mysql
    networks:
      - backend_net

networks:
  frontend_net:
  backend_net:

volumes:
  db_data:
```

### `frontend/nginx.conf` — the reverse proxy
```nginx
server {

    listen 80;

    root /usr/share/nginx/html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /api {

        proxy_pass http://backend:5000/api;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
⭐ `proxy_pass http://backend:5000/api` — **service name + container port**, resolved by Docker DNS
over `frontend_net`. This also means the browser only ever talks to `localhost:8080`, so
**there are no CORS problems**.

### `frontend/index.html`
```html
<!DOCTYPE html>

<html>

<head>
    <title>Docker Network Demo</title>
</head>

<body>

    <h1>Docker 3-Tier Application</h1>

    <button onclick="getData()">
        Get Data From Backend
    </button>

    <h2>Response:</h2>

    <pre id="result"></pre>

    <script>

        async function getData() {

            const response = await fetch('/api');

            const data = await response.json();

            document.getElementById("result").textContent =
                JSON.stringify(data, null, 2);
        }

    </script>

</body>

</html>
```
⭐ `fetch('/api')` is a **relative** URL — it goes to `localhost:8080/api`, which nginx proxies
internally. The browser never needs to know the backend exists.

### `backend/Dockerfile`
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```
⭐ Textbook layer ordering: `requirements.txt` before `app.py`, and `--no-cache-dir` to keep the
image small (Session 7).

### `backend/requirements.txt`
```
Flask
mysql-connector-python
```

### `backend/app.py`
```python
from flask import Flask
import mysql.connector
import time

app = Flask(__name__)


def get_db_connection():

    return mysql.connector.connect(
        host="database",          # ⭐ the SERVICE NAME — Docker DNS resolves it
        user="root",
        password="root",
        database="demo"
    )


@app.route("/")
def hello():
    return "Hello from Backend!"


@app.route("/api")
def api():

    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message VARCHAR(255)
            )
        """)

        cursor.execute(
            "INSERT INTO messages (message) VALUES ('Hello from MySQL!')"
        )

        db.commit()

        cursor.execute("SELECT message FROM messages ORDER BY id DESC LIMIT 1")

        result = cursor.fetchone()

        cursor.close()
        db.close()

        return {
            "backend": "Backend is working!",
            "database": result[0]
        }

    except Exception as e:
        return {
            "error": str(e)
        }, 500


app.run(host="0.0.0.0", port=5000)
```

**Three things to notice**
1. ⭐ `host="database"` — the Compose **service name**, not an IP and not `localhost`.
2. ⭐ `app.run(host="0.0.0.0", port=5000)` — binding `0.0.0.0` is what makes the container
   reachable from nginx. `127.0.0.1` would make it invisible.
3. The `try/except` returning **HTTP 500** with the error message is what lets you see
   *"Can't connect to MySQL server"* in the browser while the DB is still initialising.

### Running it
```bash
cd session8-docker-networking-volume/demo

docker compose up -d --build
docker compose ps
docker compose logs -f backend

# open http://localhost:8080 and click the button
curl http://localhost:8080/api

# ---- prove the networking claims ----
docker compose exec backend  ping -c2 database    # ✅ works  (shares backend_net)
docker compose exec frontend ping -c2 database    # ❌ fails  (⭐ no shared network!)
docker compose exec backend  curl -s http://frontend:80   # ✅ works (shares frontend_net)
docker network ls | grep demo
docker network inspect demo_backend_net

# ---- prove persistence ----
docker compose exec database mysql -uroot -proot demo -e "SELECT COUNT(*) FROM messages;"
docker compose down            # containers destroyed, volume kept
docker compose up -d
docker compose exec database mysql -uroot -proot demo -e "SELECT COUNT(*) FROM messages;"
# ⭐ same count → the volume did its job

docker compose down -v         # ⚠️ NOW the data is gone
```

### Known rough edges (and the production fixes)
| Issue | Fix |
|---|---|
| ⚠️ `depends_on` doesn't wait for MySQL to be ready → first `/api` call may 500 | Add a `healthcheck` + `condition: service_healthy`, or retry in `get_db_connection()` |
| ⚠️ Credentials hard-coded in `app.py` and the YAML | `env_file: .env` + `os.environ["DB_PASSWORD"]`; `.env` in `.gitignore` |
| ⚠️ `app.run()` is the Flask **dev** server | Use `gunicorn -b 0.0.0.0:5000 app:app` in production |
| ⚠️ `import time` is unused | Remove (it was presumably for a retry loop) |
| ⚠️ `/api` inserts a row on **every** GET | A GET shouldn't mutate state; also creates the table on every call |
| ⚠️ `image: nginx:latest` unpinned | `nginx:1.27-alpine` |
| ⚠️ Bind-mounted config files are writable | Add `:ro` — `./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro` |
| ⚠️ Containers run as root | Add a non-root `USER` in the backend Dockerfile |

---

## 🩺 Troubleshooting

### Networking issues
```bash
# Check the container's IP
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' web

# Test connectivity
docker exec web ping db

# Check DNS
docker exec web nslookup db

# View network details
docker network inspect bridge
```

### The diagnostic ladder
| Symptom | Check | Likely fix |
|---|---|---|
| Can't resolve another container's name | `docker network inspect <net>` — are both attached? | Put both on the **same user-defined** network (not the default bridge) |
| `Connection refused` between containers | `docker exec a nc -zv b 5000` | Wrong port; use the **container** port, not the published one |
| Works between containers, not from the browser | `docker port web`, `docker ps` PORTS column | Missing/incorrect `-p` mapping |
| Published port but nothing responds | `docker exec web ss -tulnp` | ⭐ App bound to `127.0.0.1` — must be `0.0.0.0` |
| `port is already allocated` | `ss -tulnp \| grep :8080` | Pick another host port or stop the other container |
| `502 Bad Gateway` from nginx | `docker compose logs backend` | Upstream container crashed or isn't ready yet |
| Container can't reach the internet | `docker exec web ping 8.8.8.8`; `docker exec web cat /etc/resolv.conf` | Host DNS/NAT issue; check `--internal` networks |
| Need to reach the host from a container | — | `host.docker.internal` (+ `--add-host=...:host-gateway` on Linux) |

### Volume issues
| Symptom | Cause | Fix |
|---|---|---|
| Data gone after `down` | No volume, or `down -v` was used | Declare a named volume; never `-v` in production |
| Bind mount appears empty | Wrong host path, or relative path | Use `$(pwd)/...`; check with `docker inspect` |
| `node_modules` not found | ⭐ Bind mount shadowed the image's install | Add `-v /app/node_modules` (anonymous volume on top) |
| Permission denied writing to a mount | UID mismatch host↔container | `--user $(id -u):$(id -g)`, or `chown` in the entrypoint |
| MySQL "database exists" but is empty | The volume already had a different initialised dataset | `docker compose down -v` to reinitialise (dev only!) |
| Disk filling up | Orphaned volumes | `docker volume ls -f dangling=true`, `docker system df -v`, `docker volume prune` |
| Changes to a mounted config not applied | The service caches config at start | `docker compose restart <service>` |

### Compose issues
```bash
docker compose config           # ⭐ FIRST: validate the YAML and see resolved variables
docker compose logs -f          # ⭐ SECOND: read the logs
docker compose ps               # what's actually up / exited
docker compose up -d --build --force-recreate   # rebuild from scratch
docker compose down -v && docker compose up -d  # ⚠️ nuclear reset (deletes data)
```
| Symptom | Fix |
|---|---|
| `yaml: mapping values are not allowed` | Indentation — YAML needs **spaces, never tabs** |
| Port parsed strangely | ⭐ **Quote** ports: `"8080:80"` |
| Changes to the Dockerfile ignored | `docker compose up -d --build` |
| Variables not substituted | `.env` in the wrong directory; verify with `docker compose config` |
| Service crashes on start, depends on DB | `depends_on` doesn't wait → add a healthcheck condition |
| Can't scale a service | Remove `container_name:` and any fixed host port |

---

## 📋 Quick Cheat Sheet

```bash
# ================= NETWORKING =================
docker network ls
docker network create app-net                    # ⭐ user-defined bridge (gives DNS)
docker network create --subnet=172.20.0.0/16 custom-net
docker network create --internal secure-net      # no internet
docker network inspect app-net
docker network connect app-net web               # attach a running container
docker network disconnect app-net web
docker network rm app-net ; docker network prune

docker run -d --name web --network app-net -p 8080:80 nginx
docker run -d --network host nginx               # share the host stack
docker run -d --network none alpine              # fully isolated

# Port mapping
-p 8080:80            # HOST:CONTAINER
-p 127.0.0.1:8080:80  # ⭐ localhost only
-p 80                 # random host port
-P                    # publish all EXPOSEd ports
-p 53:53/udp          # UDP
docker port web

# ⭐ Talk between containers: SERVICE NAME + CONTAINER PORT
#    http://backend:5000     NOT localhost, NOT the published port

# ================= VOLUMES =================
docker volume create mydata
docker volume ls ; docker volume ls -f dangling=true
docker volume inspect mydata
docker volume rm mydata ; docker volume prune

-v mydata:/app/data              # ⭐ named VOLUME     → production
-v /host/path:/app               # ⭐ BIND MOUNT       → development
-v "$(pwd)":/app                 # bind the current dir
-v mydata:/app/data:ro           # read-only
--tmpfs /app/tmp                 # RAM only
--mount type=bind,source=/h,target=/c
--mount type=volume,source=mydata,target=/data

# Backup / restore a volume
docker run --rm -v mydata:/data -v "$(pwd)":/b alpine tar czf /b/bk.tar.gz -C /data .
docker run --rm -v mydata:/data -v "$(pwd)":/b alpine sh -c "cd /data && tar xzf /b/bk.tar.gz"

# ================= COMPOSE =================
docker compose up -d                 # ⭐ start everything
docker compose up -d --build         # ⭐ rebuild first
docker compose down                  # stop + remove containers/networks
docker compose down -v               # ⚠️ also delete volumes (DATA LOSS)
docker compose ps
docker compose logs -f [service]     # ⭐
docker compose exec web sh           # ⭐ shell into a running service
docker compose run --rm web pytest   # one-off container
docker compose restart [service]
docker compose config                # ⭐ validate + expand
docker compose up -d --scale web=3
docker compose stop / start
docker compose pull / build --no-cache
docker compose -f a.yml -f b.yml up -d
```

**The ten rules of this session**
1. ⭐ Use a **user-defined network** — the default bridge has no DNS
2. ⭐ Containers talk by **service/container name**, never by IP or `localhost`
3. ⭐ Use the **container's own port** internally; publish only what the outside world needs
4. ⭐ Bind to **`0.0.0.0`** inside containers
5. ⭐ `EXPOSE` documents; **`-p` publishes**
6. ⭐ Anything you want to keep goes in a **named volume**
7. ⭐ **Volumes for production, bind mounts for development**
8. ⭐ Segment networks by tier so the frontend can't touch the database
9. ⭐ `depends_on` waits for **start**, not **readiness** — add a healthcheck
10. ⭐ `docker compose down -v` deletes data — know before you type it

---

## 🔗 References
- Docker network drivers — https://docs.docker.com/engine/network/drivers/
- Docker volumes — https://docs.docker.com/engine/storage/volumes/
- Docker Compose file reference — https://docs.docker.com/reference/compose-file/
- Compose networking — https://docs.docker.com/compose/how-tos/networking/
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
