# ⚡ S08 · Docker Networking, Volumes & Compose

> *Revision card.* Full notes → [Session 8](../08_Docker_Networking_Volumes_and_Compose.md)

---

## 🔑 One-line core

***Use a user-defined network and talk by service name on the container's own port.***
Anything you want to keep goes in a **named volume**.

---

## 🌐 Network drivers

| Driver | Use |
|---|---|
| `bridge` (default) | `docker0` = `172.17.0.0/16` — ⚠️ **no DNS by name** |
| **user-defined bridge** | ⭐ what you should use — **automatic DNS by container name** |
| `host` | no isolation, shares host stack (Linux only) |
| `none` | no networking |
| `overlay` | multi-host (Swarm / K8s) |

```bash
docker network create appnet
docker run -d --name db  --network appnet postgres:16
docker run -d --name api --network appnet myapi
# inside api:  postgresql://db:5432/...      ← by NAME
```

---

## 🧠 The #1 mistake

```
❌ http://localhost:5000      ← localhost inside a container IS that container
✅ http://backend:5000        ← service name, container's OWN port
```

> ⭐ **Not the published host port.** `-p 8080:5000` is for traffic from **outside**.

---

## 🔌 Port mapping

```
-p 8080:80      host 8080 → container 80
-p 127.0.0.1:8080:80    bind to loopback only
-P              publish all EXPOSEd ports randomly
```

---

## 💾 Storage — pick one

| | Use for | Lives |
|---|---|---|
| **Named volume** ⭐ | **data you keep** (databases) | `/var/lib/docker/volumes` |
| **Bind mount** | **dev source** (live reload) | a host path you choose |
| `tmpfs` | secrets, scratch | RAM only, gone on stop |

```bash
docker run -v pgdata:/var/lib/postgresql/data postgres:16   # volume
docker run -v "$PWD/src:/app/src" myapp                     # bind mount
```

> ⚠️ A container's writable layer **dies with the container**.

---

## 🎼 Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    environment: { POSTGRES_PASSWORD: secret }
    volumes: [ "pgdata:/var/lib/postgresql/data" ]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 5

  api:
    build: ./api
    environment: { DATABASE_URL: "postgresql://db:5432/app" }
    depends_on:
      db: { condition: service_healthy }     # ⭐ the real fix
    ports: [ "8000:8000" ]

volumes:
  pgdata:
```

```bash
docker compose up --build -d
docker compose ps / logs -f / exec api sh
docker compose down        # keeps volumes
docker compose down -v     # ⚠️ DELETES volumes
```

---

## ⚠️ Traps

| Trap | Reality |
|---|---|
| `depends_on` waits for readiness | ⚠️ **No — only for *start*.** Use a healthcheck. |
| `localhost` reaches another container | ⚠️ it reaches *itself* |
| Default bridge gives you DNS | ⚠️ only **user-defined** networks do |
| `down -v` is harmless | ⚠️ **deletes your database** |

---

## 🏗️ 3-tier shape

```
frontend ──frontnet──▶ backend ──backnet──▶ database
                                              │
                                        named volume
```

> ⭐ **Segment networks by tier** so the frontend literally cannot reach the DB.

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Containers can't talk? | not on the same **user-defined** network |
| Backend URL from frontend? | `http://backend:5000` |
| DB data gone after restart? | no **named volume** |
| `depends_on` fixed the race? | no — add a **healthcheck** |
| When do you outgrow Compose? | multiple machines, self-healing, rolling updates → **K8s** |

---

⬅️ [S07](./07_Docker_Images_and_Dockerfile.md) · ➡️ [S09 · Kubernetes](./09_Kubernetes_Fundamentals.md)
