# ⚡ S07 · Docker Images & Dockerfile

> *Revision card.* Full notes → [Session 7](../07_Docker_Images_and_Dockerfile.md)

---

## 🔑 One-line core

***Copy dependency manifests before source code.*** That one ordering decision is most of
your build speed.

---

## 📚 Instructions

| | Does | Note |
|---|---|---|
| `FROM` | base image | `AS name` starts a stage |
| `WORKDIR` | set + create cwd | better than `RUN cd` |
| `COPY` | copy files | ⭐ prefer over `ADD` |
| `ADD` | copy + untar + URLs | rarely what you want |
| `RUN` | runs at **build** time | each one = a layer |
| `ENV` | runtime env var | ⚠️ visible in `docker history` |
| `ARG` | **build-time only** | ⚠️ also visible |
| `EXPOSE` | ⚠️ **documentation only** | `-p` publishes |
| `USER` | ⭐ drop from root | biggest security win |
| `VOLUME` | declare a mount point | |
| `HEALTHCHECK` | liveness | |
| `CMD` | default command | **replaced** by run args |
| `ENTRYPOINT` | fixed executable | run args **appended** |

---

## 🎬 CMD vs ENTRYPOINT — the classic

```dockerfile
CMD ["echo", "hello"]
$ docker run img world        →  world          # REPLACED

ENTRYPOINT ["echo"]
$ docker run img world        →  world          # APPENDED

ENTRYPOINT ["ping"]
CMD ["localhost"]
$ docker run img              →  ping localhost
$ docker run img google.com   →  ping google.com
```

> ⚠️ **Use exec form `["cmd","arg"]`, never shell form.** Shell form wraps you in
> `/bin/sh -c`, which **swallows SIGTERM** — your app never gets a graceful shutdown.

---

## 🧱 Layer cache — the rule

```dockerfile
COPY requirements.txt .          # ← changes rarely
RUN pip install -r requirements.txt   # ← expensive, stays cached
COPY . .                         # ← changes every commit
```

> ⭐ **A changed layer invalidates every layer after it.** Put the volatile stuff last.
> Deleting a file in a *later* layer does **not** shrink the image — clean up in the
> **same** `RUN`.

---

## 🎭 Multi-stage — the biggest win

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./ && RUN npm ci
COPY . . && RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

**~1.1 GB toolchain → ~50 MB runtime.** Smaller *and* far fewer CVEs.

---

## 📉 Size ladder

| Base | ~Size |
|---|---|
| `ubuntu` | 78 MB |
| `python:3.12` | 1 GB |
| `python:3.12-slim` | 130 MB |
| `alpine` | 7 MB |
| `distroless` / `scratch` | ~2 MB · 0 |

---

## 🚫 `.dockerignore` — write it first

```
.git
node_modules
__pycache__
.env
*.log
Dockerfile
```

Speeds the build, protects the cache, and keeps `.env` out of the image.

---

## 🔒 Security checklist

- [ ] `USER` non-root
- [ ] pinned base tag (or digest)
- [ ] `--no-cache-dir` / clean apt lists **in the same RUN**
- [ ] **no secrets in `ENV` / `ARG`** — use BuildKit secrets
- [ ] `trivy image myapp:tag --severity HIGH,CRITICAL`
- [ ] bind `0.0.0.0`, not `127.0.0.1`

---

## ⚠️ Traps

| Trap | Reality |
|---|---|
| `EXPOSE 80` publishes the port | ⚠️ **No.** `-p` does. |
| Secrets in `ARG` are safe | ⚠️ `docker history` shows them |
| Shell form is fine | ⚠️ swallows signals |
| Deleting files later shrinks the image | ⚠️ layers are append-only |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| `CMD` vs `ENTRYPOINT`? | replaced vs appended |
| Why copy `requirements.txt` first? | keep the install layer cached |
| Shrink a 1 GB image? | **multi-stage** + slim/alpine base |
| `COPY` vs `ADD`? | plain copy vs copy+untar+URL — prefer COPY |

---

⬅️ [S06](./06_Docker_Fundamentals.md) · ➡️ [S08 · Compose](./08_Docker_Networking_Volumes_and_Compose.md)
