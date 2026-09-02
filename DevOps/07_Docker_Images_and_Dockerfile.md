# Session 7 — Docker Images & Dockerfile 📝

> A **Dockerfile** is Infrastructure as Code for your application's runtime environment.
> It turns "install these things, copy that, run this" into a **reproducible, version-controlled
> recipe** that anyone (and any CI runner) can build identically.

---

## 📑 Table of Contents
1. [What is a Dockerfile](#-what-is-a-dockerfile)
2. [Instruction Reference](#-instruction-reference)
3. [FROM](#from--the-base-image)
4. [WORKDIR](#workdir--the-working-directory)
5. [COPY vs ADD](#copy-vs-add)
6. [RUN](#run--execute-at-build-time)
7. [ENV vs ARG](#env-vs-arg)
8. [EXPOSE](#expose--document-the-port)
9. [CMD vs ENTRYPOINT](#-cmd-vs-entrypoint)
10. [USER, VOLUME, LABEL, HEALTHCHECK](#-user-volume-label--healthcheck)
11. [Build Context & .dockerignore](#-build-context--dockerignore)
12. [Layers & Build Cache](#-layers--the-build-cache)
13. [Building Images](#-building-images)
14. [Multi-Stage Builds](#-multi-stage-builds)
15. [Image Optimization](#-image-optimization)
16. [Security Best Practices](#-security-best-practices)
17. [Worked Examples from Class](#-worked-examples-from-class)
18. [Complete Reference Dockerfiles](#-complete-reference-dockerfiles)
19. [Cheat Sheet](#-quick-cheat-sheet)

---

## 📄 What is a Dockerfile?

> A **Dockerfile** is a **text file containing instructions to build a Docker image
> automatically.**

```
Dockerfile  ──docker build──▶  Image  ──docker run──▶  Container
 (recipe)                    (template)              (running instance)
```

**Rules**
- Named exactly `Dockerfile` by convention (use `-f` for anything else).
- Instructions are conventionally **UPPERCASE** (case-insensitive, but always follow the convention).
- Executed **top to bottom**, and **each instruction creates a layer**.
- Lines starting with `#` are comments.
- `\` continues a line.
- The **first instruction must be `FROM`** (except `ARG` / parser directives).

```dockerfile
# syntax=docker/dockerfile:1        ← optional parser directive (enables newer features)
FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

---

## 📚 Instruction Reference

| Instruction | Purpose | Example |
|---|---|---|
| **`FROM`** | Base image to start from | `FROM ubuntu:20.04` |
| **`WORKDIR`** | Set the working directory | `WORKDIR /app` |
| **`COPY`** | Copy files from host to image | `COPY . /app` |
| **`ADD`** | Like `COPY`, but can extract tars & download URLs | `ADD app.tar.gz /app` |
| **`RUN`** | Execute commands **during build** | `RUN apt-get update` |
| **`CMD`** | **Default** command when the container starts | `CMD ["python", "app.py"]` |
| **`ENTRYPOINT`** | Configure the container as an executable | `ENTRYPOINT ["nginx"]` |
| **`EXPOSE`** | **Document** which ports the app listens on | `EXPOSE 8080` |
| **`ENV`** | Set environment variables (build **and** runtime) | `ENV APP_ENV=production` |
| **`ARG`** | **Build-time** variables | `ARG VERSION=1.0` |
| **`VOLUME`** | Create a mount point for persistent data | `VOLUME /data` |
| **`LABEL`** | Add metadata to the image | `LABEL version="1.0"` |
| **`USER`** | Switch the user for subsequent instructions & runtime | `USER nodejs` |
| **`HEALTHCHECK`** | How to test that the app is working | `HEALTHCHECK CMD curl -f localhost/health` |
| **`SHELL`** | Change the default shell for `RUN` | `SHELL ["/bin/bash", "-c"]` |
| **`ONBUILD`** | Trigger an instruction when this image is used as a base | `ONBUILD COPY . /app` |
| **`STOPSIGNAL`** | Signal sent to stop the container | `STOPSIGNAL SIGQUIT` |

---

### `FROM` — the base image

```dockerfile
FROM node:24-alpine
FROM python:3.11-slim
FROM nginx:latest
FROM scratch                 # completely empty (for static Go/Rust binaries)
FROM node:24-alpine AS builder   # ⭐ named stage, for multi-stage builds
```

- **Every image starts here.** It provides the OS userland, package manager and runtime.
- ⭐ **Always pin a specific tag.** `FROM python:latest` means your build changes under you.
- Prefer official images from Docker Hub, and prefer `-alpine`/`-slim` variants.

| Base | Size | Notes |
|---|---|---|
| `ubuntu:22.04` | ~78 MB | Familiar, `apt`, big |
| `debian:bookworm-slim` | ~75 MB | Good general default |
| `python:3.11-slim` | ~130 MB | ⭐ Safe balance |
| `node:24-alpine` | ~50 MB | ⭐ Small, musl libc |
| `alpine:3.20` | ~7 MB | Tiny, `apk`, musl |
| `gcr.io/distroless/...` | ~20 MB | No shell → most secure, hard to debug |
| `scratch` | 0 B | Static binaries only |

---

### `WORKDIR` — the working directory

```dockerfile
WORKDIR /app
```
- Sets the directory for all subsequent `RUN`, `CMD`, `ENTRYPOINT`, `COPY`, `ADD`.
- **Creates the directory if it doesn't exist.**
- ⭐ Use it instead of `RUN cd /app` — `cd` in a `RUN` doesn't persist to the next instruction,
  because **each `RUN` is a separate shell**:

```dockerfile
RUN cd /app        # ❌ has no effect on the next line
RUN npm install    #    still runs in /

WORKDIR /app       # ✅ persists
RUN npm install    #    runs in /app
```

---

### `COPY` vs `ADD`

```dockerfile
COPY package*.json ./          # ⭐ wildcards work
COPY . .                       # copy the whole build context
COPY src/ /app/src/
COPY --chown=node:node . .     # ⭐ set ownership while copying
COPY --from=builder /app/dist ./dist    # ⭐ from another build stage

ADD app.tar.gz /app/           # auto-EXTRACTS the archive
ADD https://example.com/f.zip /tmp/     # downloads (but doesn't extract)
```

| | `COPY` | `ADD` |
|---|---|---|
| Copy local files | ✅ | ✅ |
| Auto-extract local tar/gz | ❌ | ✅ |
| Download from a URL | ❌ | ✅ |
| Transparent / predictable | ✅ | ❌ |
| **Recommendation** | ⭐ **Use `COPY` by default** | Only for auto-extracting a local tar |

> ⚠️ Don't use `ADD <url>`: it can't verify checksums, can't retry sensibly, and bakes the
> download into a layer. Use `RUN curl -fsSL <url> -o file && echo "<sha> file" | sha256sum -c`.

> 📌 **Paths are relative to the build context**, and you **cannot copy from outside it**
> (`COPY ../file .` fails).

---

### `RUN` — execute at build time

```dockerfile
RUN npm install                              # shell form → /bin/sh -c "npm install"
RUN ["npm", "install"]                       # exec form (no shell — no pipes/globs/vars)

# ⭐ Combine + clean up in ONE layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

**Why combining matters:**
```dockerfile
# ❌ Bad: 3 layers, and the apt cache is baked into layer 1 forever
RUN apt-get update
RUN apt-get install -y package1
RUN apt-get install -y package2

# ✅ Good: 1 layer, cache removed inside the same layer
RUN apt-get update && \
    apt-get install -y package1 package2 && \
    rm -rf /var/lib/apt/lists/*
```
> ⚠️ Layers are **additive**. `RUN rm -rf /cache` in a *later* layer does **not** shrink the image —
> the data still exists in the earlier layer. Cleanup must happen in the **same `RUN`**.

> ⚠️ **Also:** `RUN apt-get update` alone in one layer + `install` in another causes the
> infamous **stale-cache bug** — the cached `update` layer is reused while `install` fetches
> versions that no longer exist. Always chain them.

**Package-manager cleanup idioms**
```dockerfile
# Debian/Ubuntu
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
# Alpine
RUN apk add --no-cache curl
# Python
RUN pip install --no-cache-dir -r requirements.txt
# Node
RUN npm ci --omit=dev && npm cache clean --force
```

---

### `ENV` vs `ARG`

```dockerfile
ARG NODE_VERSION=24            # ⭐ BUILD-time only
FROM node:${NODE_VERSION}-alpine

ARG BUILD_DATE                 # no default → must be passed
ENV APP_ENV=production \        # ⭐ persists at RUNTIME
    PORT=3000 \
    PATH="/root/.local/bin:$PATH"
```
```bash
docker build --build-arg NODE_VERSION=22 --build-arg BUILD_DATE=$(date -u +%F) -t myapp .
docker run -e APP_ENV=staging myapp        # ⭐ ENV can be overridden at run time
```

| | `ARG` | `ENV` |
|---|---|---|
| Available during **build** | ✅ | ✅ |
| Available at **runtime** | ❌ | ✅ |
| Set from CLI | `--build-arg` | `-e` / `--env-file` |
| Visible in `docker inspect` | Only in build history | ✅ Yes |

> 🚨 **Never put secrets in `ARG` or `ENV`.** Both are recoverable from image history
> (`docker history`, `docker inspect`) even if you "unset" them later. Use
> **BuildKit secret mounts** at build time and **runtime env vars / secret managers** at run time:
> ```dockerfile
> RUN --mount=type=secret,id=npmrc npm ci
> ```
> ```bash
> DOCKER_BUILDKIT=1 docker build --secret id=npmrc,src=$HOME/.npmrc -t myapp .
> ```

---

### `EXPOSE` — document the port

```dockerfile
EXPOSE 80
EXPOSE 80 443
EXPOSE 53/udp
```

> ⚠️⭐ **`EXPOSE` is documentation only. It does NOT publish the port.**
> ```dockerfile
> FROM nginx
> EXPOSE 80 443
> # EXPOSE is documentation only
> # Doesn't actually publish ports
> # Must use -p or -P at runtime
> ```
> ```bash
> docker run -d -p 8080:80 nginx      # ⭐ THIS publishes it
> docker run -d -P nginx              # publish all EXPOSEd ports to random host ports
> ```

What `EXPOSE` *is* good for: it tells humans and tools (like `-P`, and Compose) which ports the
app uses.

---

## 🎬 CMD vs ENTRYPOINT

This is **the** classic Docker interview question.

### `CMD`
- Provides **default arguments** to `ENTRYPOINT`, or a standalone default command.
- ⭐ **Can be overridden** by command-line arguments to `docker run`.
- **Only the last `CMD` in a Dockerfile is used.**
- Executed when the container starts.

### `ENTRYPOINT`
- Configures the container to **run as an executable**.
- ⭐ **Cannot be overridden easily** (needs the `--entrypoint` flag).
- **Command-line arguments are appended to `ENTRYPOINT`.**
- Makes the container behave like a binary.

### Comparison
| Feature | **CMD** | **ENTRYPOINT** |
|---|---|---|
| Purpose | Default command/args | Main executable |
| Override at `docker run` | ⭐ **Easy** (just pass args) | **Difficult** (`--entrypoint`) |
| Multiple in a Dockerfile | Only the last one is used | Only the last one is used |
| Use case | Flexible commands | Fixed executable |

### 1. CMD only
```dockerfile
FROM ubuntu
CMD ["echo", "Hello World"]
```
```bash
docker run myimage              # Output: Hello World
docker run myimage echo Hi      # Output: Hi          (⭐ CMD overridden)
```

### 2. ENTRYPOINT only
```dockerfile
FROM ubuntu
ENTRYPOINT ["echo"]
```
```bash
docker run myimage              # Output: (nothing)
docker run myimage Hello        # Output: Hello       (⭐ appended to ENTRYPOINT)
```

### 3. ENTRYPOINT + CMD (best practice ⭐)
```dockerfile
FROM ubuntu
ENTRYPOINT ["echo"]
CMD ["Hello World"]
```
```bash
docker run myimage              # Output: Hello World
docker run myimage Goodbye      # Output: Goodbye     (⭐ CMD replaced, ENTRYPOINT kept)
```

### Real-world example (Python app)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .

# ENTRYPOINT sets the main executable
ENTRYPOINT ["python"]

# CMD provides the default script
CMD ["app.py"]
```
```bash
docker run myapp                # Runs: python app.py
docker run myapp test.py        # Runs: python test.py
```

### Shell form vs exec form ⭐ (a subtle but important difference)
```dockerfile
CMD npm start                   # SHELL form → runs: /bin/sh -c "npm start"
CMD ["npm", "start"]            # ⭐ EXEC form → runs npm directly as PID 1
```

| | Shell form | Exec form `["..."]` |
|---|---|---|
| Runs via `/bin/sh -c` | ✅ | ❌ (direct exec) |
| PID 1 is | `sh` | ⭐ **your process** |
| Receives SIGTERM from `docker stop` | ❌ **No** (sh swallows it → 10 s wait then SIGKILL) | ✅ **Yes** → graceful shutdown |
| Variable/pipe/glob expansion | ✅ | ❌ |
| **Recommendation** | Only when you need shell features | ⭐ **Prefer exec form** |

If you need shell features *and* proper signal handling:
```dockerfile
CMD ["sh", "-c", "exec node server.js --port $PORT"]     # `exec` replaces sh with node
```

**The `exec "$@"` entrypoint pattern** (used with a wrapper script):
```bash
#!/bin/sh
set -e
# ... wait for DB, run migrations, render config ...
exec "$@"          # ⭐ hand off to CMD, becoming PID 1
```
```dockerfile
ENTRYPOINT ["/entrypoint.sh"]
CMD ["node", "server.js"]
```

---

## 👤 USER, VOLUME, LABEL & HEALTHCHECK

### `USER` — don't run as root ⭐
```dockerfile
FROM node:24-alpine

# Create a non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

WORKDIR /app
COPY --chown=nodejs:nodejs . .

USER nodejs                    # ⭐ everything after this runs as nodejs
CMD ["node", "server.js"]
```
> By default containers run as **root**, and container-root maps to host-root in many setups —
> a container escape then owns your host. Official images often ship a ready-made user
> (`node`, `nginx`, `postgres`), so `USER node` is often enough.
>
> ⚠️ A non-root user **cannot bind ports < 1024** — listen on 8080 and map with `-p 80:8080`.

### `VOLUME`
```dockerfile
VOLUME /var/lib/mysql
VOLUME ["/data", "/logs"]
```
Declares a mount point whose data should live outside the container's writable layer. If the user
doesn't mount anything there, Docker creates an **anonymous volume** automatically.
> 💡 Prefer declaring volumes at **run time** (`-v`) or in **Compose** — `VOLUME` in a Dockerfile
> can surprise users with orphaned anonymous volumes.

### `LABEL` — metadata
```dockerfile
LABEL maintainer="ashutosh.kumar@scalerailabs.com"
LABEL version="1.0"
LABEL org.opencontainers.image.source="https://github.com/user/repo"
LABEL org.opencontainers.image.revision="$GIT_SHA"
```
```bash
docker inspect --format='{{json .Config.Labels}}' myapp | jq
docker images --filter "label=version=1.0"
```
Use the **OCI standard label keys** so registries and scanners can read them.

### `HEALTHCHECK`
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1
```
*(Full details in Session 6.)*

### `STOPSIGNAL` & `SHELL`
```dockerfile
STOPSIGNAL SIGQUIT                     # nginx prefers SIGQUIT for graceful shutdown
SHELL ["/bin/bash", "-o", "pipefail", "-c"]   # ⭐ make RUN pipelines fail properly
```

---

## 📁 Build Context & `.dockerignore`

### The build context
```bash
docker build -t myapp .
#                     ↑ THE BUILD CONTEXT — this directory is sent to the daemon
```
- The **entire directory** is packaged and uploaded to the Docker daemon **before** the build starts.
- `COPY`/`ADD` can only read files **inside** the context.
- ⭐ A huge context (`.git`, `node_modules`) makes every build slow, even if you never `COPY` it.

```bash
docker build -t myapp .                       # context = current dir, Dockerfile = ./Dockerfile
docker build -t myapp -f Dockerfile.dev .     # ⭐ different Dockerfile, same context
docker build -t myapp ./backend               # context = ./backend
docker build -t myapp https://github.com/u/r.git#main    # context from Git
```

### `.dockerignore`
Works exactly like `.gitignore`, but for the build context.

```dockerignore
# Version control
.git
.gitignore

# Dependencies (will be installed inside the image)
node_modules
venv
__pycache__

# Secrets ⭐
.env
.env.*
*.pem
*.key

# Build output
dist
build
target

# Docker files themselves
Dockerfile
Dockerfile.*
docker-compose.yml
.dockerignore

# Docs & noise
*.md
README.md
.DS_Store
.vscode
.idea

# Logs & tests
*.log
logs
tests
coverage
```

**Three reasons it matters**
1. ⚡ **Faster builds** — less data uploaded to the daemon
2. 📦 **Smaller images** — `COPY . .` won't drag in junk
3. 🔒 **Security** — ⭐ prevents `.env`, `.git` and private keys from ending up in the image

> 🚨 Without a `.dockerignore`, `COPY . .` will happily bake your `.git` history and `.env`
> secrets into a layer that you then push to a registry.

---

## 🧱 Layers & the Build Cache

Every instruction creates a layer, and Docker **caches** each one. On rebuild, Docker reuses a
cached layer **only if the instruction and its inputs are unchanged** — and **once one layer is
invalidated, every layer after it is rebuilt.**

### The single most valuable optimization ⭐
```dockerfile
# ❌ BAD — any source change re-runs npm install (slow, every time)
FROM node:24-alpine
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "start"]

# ✅ GOOD — dependencies are cached until package.json changes
FROM node:24-alpine
WORKDIR /app
COPY package*.json ./          # ⭐ copy ONLY the dependency manifest first
RUN npm install                # ⭐ this layer is cached across source edits
COPY . .                       # source changes only invalidate from here down
CMD ["npm", "start"]
```

**The ordering principle:** put instructions from **least likely to change** →
**most likely to change**.
```
1. FROM                    (rarely changes)
2. system packages (RUN apt-get ...)
3. dependency manifests (COPY package*.json / requirements.txt)
4. RUN install dependencies
5. COPY application source (changes constantly)
6. CMD / ENTRYPOINT
```

**Cache control**
```bash
docker build --no-cache -t myapp .            # ⭐ ignore the cache entirely
docker build --pull -t myapp .                # re-pull the base image
docker build --progress=plain -t myapp .      # verbose output (see cache hits)
docker history myapp                          # ⭐ layer sizes — find the fat layer
docker builder prune                          # clean the build cache
```

**BuildKit cache mounts** (keep the package cache *outside* the image):
```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=cache,target=/root/.npm npm ci
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
```

---

## 🔨 Building Images

```bash
docker build -t myapp:1.0 .                  # ⭐ build and tag
docker build -t myapp:1.0 -t myapp:latest .  # multiple tags in one build
docker build -f Dockerfile.prod -t myapp .   # a specific Dockerfile
docker build --build-arg VERSION=2.0 -t myapp .
docker build --target builder -t myapp:build .    # ⭐ stop at a specific stage
docker build --platform linux/amd64 -t myapp .    # ⭐ cross-platform (Apple Silicon → x86 servers)
docker build --no-cache -t myapp .

# Then:
docker run -d -p 5000:5000 myapp:1.0
docker images
docker history myapp:1.0
```

**Multi-architecture builds** (needed when your laptop is ARM but production is x86):
```bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t user/myapp:1.0 --push .
```

---

## 🎭 Multi-Stage Builds

> **Multi-stage builds allow you to use multiple `FROM` statements in a Dockerfile to create
> smaller, more secure final images.**

### Benefits
- **Smaller images** — only production dependencies land in the final image
- **Faster deployments** — smaller = faster push/pull
- **More secure** — no compilers, build tools or source code in the production image
- **Organized** — separate build and runtime environments
- **No cleanup needed** — build artifacts are automatically excluded

### How it works
```
Stage 1 "builder"          Stage 2 "production"
┌──────────────────┐       ┌──────────────────┐
│ node:24 (full)   │       │ node:24-alpine   │
│ + dev deps       │       │ + prod deps only │
│ + source code    │ ────▶ │ + build output   │  ← COPY --from=builder
│ + compilers      │       │                  │
│ (700 MB)         │       │ (200 MB) ✅ SHIPPED│
│ 🗑️ DISCARDED     │       └──────────────────┘
└──────────────────┘
```
Only the **last stage** becomes the final image. Everything else is thrown away.

### Example: Java application

**Without multi-stage (bad):**
```dockerfile
FROM maven:3.8-jdk-11
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package
CMD ["java", "-jar", "target/app.jar"]

# Problem: image includes Maven, source code, build cache
# Size: ~700 MB
```

**With multi-stage (good):**
```dockerfile
# Stage 1: Build
FROM maven:3.8-jdk-11 AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

# Stage 2: Runtime
FROM openjdk:11-jre-slim
WORKDIR /app
COPY --from=builder /app/target/app.jar .
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]

# Result: only JRE + JAR in the final image
# Size: ~200 MB (65% smaller!)
```

### Example: Node.js application
```dockerfile
# Build stage
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
RUN npm prune --production

# Production stage
FROM node:16-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./
EXPOSE 3000
USER node
CMD ["node", "dist/server.js"]
```

### Example: Python application
```dockerfile
# Build stage
FROM python:3.9 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

### Building a specific stage
```bash
docker build --target builder -t myapp:build .    # ⭐ build only 'builder' (for testing)
docker build -t myapp:latest .                    # build the final stage (default)
```

### Extra multi-stage tricks
```dockerfile
FROM node:24-alpine AS deps            # 1. dependencies
FROM deps AS build                     # 2. build (⭐ stages can extend other stages)
FROM build AS test                     # 3. run tests
RUN npm test
FROM node:24-alpine AS production      # 4. minimal runtime
COPY --from=build /app/dist ./dist

# Copy from an EXTERNAL image without adding a stage:
COPY --from=nginx:alpine /etc/nginx/nginx.conf /etc/nginx/nginx.conf
```
```bash
docker build --target test .           # ⭐ run the test stage in CI; fails the build if tests fail
```

---

## 📉 Image Optimization

### 1. Use Alpine or slim base images
```dockerfile
FROM ubuntu:20.04         # Huge: 1 GB+
FROM python:3.9           # Better: 200 MB
FROM python:3.9-alpine    # Best: 50 MB
```

### 2. Multi-stage builds
```dockerfile
FROM node:16 AS build
COPY . .
RUN npm run build

FROM node:16-alpine
COPY --from=build /app/dist ./dist
```

### 3. Combine RUN commands
```dockerfile
# Bad: creates 3 layers
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# Good: creates 1 layer
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
```

### 4. Use `.dockerignore`
```
.git
*.md
tests/
.env
node_modules
```

### 5. Don't install unnecessary packages
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    package1 \
    package2 && \
    rm -rf /var/lib/apt/lists/*
```

### 6. Clean up in the same layer
```dockerfile
RUN apt-get update && \
    apt-get install -y build-essential && \
    # ... compile something ... && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
```

### 7. Leverage the build cache
```dockerfile
# Copy dependency files first
COPY package.json package-lock.json ./
RUN npm install

# Then copy source (changes more often)
COPY . .
```

### 8. Use specific COPY (not blanket ADD/COPY)
```dockerfile
# Good: only copy what's needed
COPY package.json ./
COPY src/ ./src/

# Bad: copies everything
COPY . .
```

### Size comparison
| Approach | Image size |
|---|---|
| Ubuntu + full dependencies | **1.2 GB** |
| Debian slim + selective install | **450 MB** |
| Alpine + minimal packages | **85 MB** |
| **Multi-stage Alpine** | **45 MB** ⭐ |

### Why size matters
| Impact | Effect |
|---|---|
| **Pull/push time** | 1 GB × 50 nodes = slow rollouts and big egress bills |
| **Cold-start latency** | Kubernetes must pull before a pod starts |
| **Attack surface** | ⭐ Fewer packages = fewer CVEs for Trivy to find |
| **Storage cost** | Registry + node disk |
| **CI duration** | Every pipeline run pays the price |

**Diagnose bloat**
```bash
docker images                        # compare sizes
docker history myapp:1.0             # ⭐ which layer is fat?
docker history --no-trunc myapp:1.0  # see the full command
docker system df -v
```

---

## 🔒 Security Best Practices

### 1. Use official and verified images
```dockerfile
FROM nginx:1.21-alpine       # ✅ Good: official image
FROM randomuser/nginx        # ❌ Bad: unknown source
```

### 2. Use specific image tags (not `latest`)
```dockerfile
FROM python:3.9.7-alpine     # ✅ Good: specific version
FROM python:latest           # ❌ Bad: unpredictable
```

### 3. Run as a non-root user
```dockerfile
FROM node:14-alpine

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

WORKDIR /app
COPY --chown=nodejs:nodejs . .

USER nodejs
CMD ["node", "server.js"]
```

### 4. Minimize image layers and size
See [Image Optimization](#-image-optimization).

### 5. Use multi-stage builds
Keeps compilers, source code and dev dependencies out of production.

### 6. Scan images for vulnerabilities ⭐
```bash
docker scout cve nginx:latest        # Docker Scout
trivy image nginx:latest             # ⭐ Trivy (from Session 1)
snyk container test nginx:latest     # Snyk

# As a CI security gate:
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:1.0
```

### 7. Use Docker secrets (not environment variables)
```bash
echo "my_password" | docker secret create db_password -

docker service create \
  --name mysql \
  --secret db_password \
  mysql:8.0
```

### 8. Limit container resources
```bash
docker run -d --name web --memory="512m" --cpus="1.0" nginx
```

### 9. Use a read-only filesystem
```bash
docker run -d --name web --read-only --tmpfs /tmp nginx
```

### 10. Enable Docker Content Trust
```bash
export DOCKER_CONTENT_TRUST=1     # only signed images can be pulled/run
docker pull nginx:latest
```

### 11. Use a `.dockerignore` file
```dockerignore
.git
.env
node_modules
*.log
*.md
.dockerignore
Dockerfile
docker-compose.yml
```

### 12. Regular updates
```bash
docker pull nginx:alpine
docker build --pull -t myapp .
```

### Security checklist
- [ ] Use minimal base images (Alpine/slim/distroless)
- [ ] Run as a **non-root** user
- [ ] **Don't store secrets in images** (not in `ENV`, `ARG` or files)
- [ ] Scan images for vulnerabilities (Trivy in CI)
- [ ] Limit container capabilities (`--cap-drop ALL --cap-add NET_BIND_SERVICE`)
- [ ] Use read-only filesystems where possible
- [ ] Keep the Docker engine updated
- [ ] Implement network policies
- [ ] Log and monitor container activity
- [ ] Use trusted registries only
- [ ] `--security-opt no-new-privileges` to block privilege escalation
- [ ] ⚠️ Never use `--privileged` or mount `/var/run/docker.sock` without a very good reason

---

## 🧪 Worked Examples from Class

### 1. `nginx-web/` — static site on nginx

**`index.html`**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Hello Docker</title>
</head>
<body>
    <h1>Hello World from Nginx + Docker!</h1>
</body>
</html>
```

**`Dockerfile`**
```dockerfile
FROM nginx:latest

COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

```bash
docker build -t nginx-web .
docker run -d --name web -p 8080:80 nginx-web
# → open http://localhost:8080
```

**What to learn from it**
- `/usr/share/nginx/html/` is nginx's default document root (Session 2: `/usr/share` = static data).
- ⭐ **`daemon off;` is essential.** By default nginx daemonizes (goes to background), the
  foreground process exits, and **the container dies immediately**. `daemon off;` keeps it in the
  foreground as PID 1. This is the "container lives as long as PID 1" rule in action.
- The official `nginx` image already sets this `CMD`, so it's technically redundant here — but
  writing it explicitly makes the lesson visible.
- 🔧 Improvement: pin the tag (`nginx:1.27-alpine`) instead of `latest`.

---

### 2. `node-app/` — Express app (single stage)

**`package.json`**
```json
{
  "name": "docker-hello-world",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^5.1.0"
  }
}
```

**`server.js`**
```javascript
const express = require("express");

const app = express();
const PORT = 3000;

app.get("/", (req, res) => {
  res.send("<h1>Hello World from Docker!</h1>");
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

**`Dockerfile`**
```dockerfile
FROM node:24-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

```bash
docker build -t node-app .
docker run -d --name node-app -p 3000:3000 node-app
curl http://localhost:3000
docker logs -f node-app
```

**What to learn from it** — this is the **canonical, correctly-ordered Dockerfile**:
| Line | Why it's there |
|---|---|
| `FROM node:24-alpine` | Small base with Node pre-installed |
| `WORKDIR /app` | All later paths are relative to `/app` |
| `COPY package*.json ./` | ⭐ **Dependency manifest first** — the whole point of cache layering. `package*.json` matches both `package.json` and `package-lock.json` |
| `RUN npm install` | ⭐ Cached until the manifest changes |
| `COPY . .` | Source last, because it changes most often |
| `EXPOSE 3000` | Documents the port |
| `CMD ["npm", "start"]` | Exec form; runs `node server.js` from `package.json` |

🔧 **Production hardening of this exact file:**
```dockerfile
FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force   # ⭐ ci = reproducible, no dev deps
COPY --chown=node:node . .
EXPOSE 3000
USER node                                          # ⭐ non-root
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://localhost:3000/ || exit 1
CMD ["node", "server.js"]                          # ⭐ direct exec → receives SIGTERM
```
> Note `CMD ["npm", "start"]` puts **npm** at PID 1, which doesn't forward SIGTERM well.
> Calling `node` directly gives graceful shutdown.

---

### 3. `multi-stage-dockerfile/` — the same app, multi-stage

**`server.js`**
```javascript
const express = require("express");

const app = express();
const PORT = 3000;

app.get("/", (req, res) => {
  res.send("<h1>Hello World from Docker Multi-Stage Build!</h1>");
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

**`Dockerfile`**
```dockerfile
# -------------------------
# Stage 1: Build
# -------------------------
FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# -------------------------
# Stage 2: Production
# -------------------------
FROM node:24-alpine AS production
WORKDIR /app
COPY --from=builder /app/package*.json ./
RUN npm install --omit=dev
COPY --from=builder /app/server.js ./
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t node-multistage .
docker build --target builder -t node-multistage:build .   # just the builder stage
docker images | grep node                                   # ⭐ compare the sizes
```

**What to learn from it**
- Two `FROM` statements, each **named** with `AS builder` / `AS production`.
- ⭐ `RUN npm install --omit=dev` in stage 2 installs **production dependencies only** —
  dev tools (test frameworks, linters, TypeScript) never reach the shipped image.
- ⭐ `COPY --from=builder` pulls **only the artifacts you name** — `package*.json` and `server.js`.
  Everything else from stage 1 (dev `node_modules`, caches, source) is discarded.
- The final image contains: Alpine + Node + prod deps + one JS file. Nothing more.

> 💡 For a plain Node app with no build step, the gain here is modest. The pattern pays off
> enormously when there **is** a build step (TypeScript, React/Vite, Java/Maven, Go) — as in the
> Java example above, where it cut 700 MB → 200 MB.

---

### 4. `python-app/` — Python container (and how to fix it)

**`app.py`**
```python
print("Hello World from Docker!")
```

**`Dockerfile` (as written in class)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt update && apt install -y pip3 python3

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
```

```bash
docker build -t python-app .
docker run --rm python-app        # → Hello World from Docker!
```

> ℹ️ This container **exits immediately with code 0** — and that's correct! `app.py` just prints
> and finishes. Its job is done, so PID 1 exits and the container stops. Use `--rm` so it
> cleans itself up. A *service* would need a long-running process (a web server, a loop).

**🔧 Three problems worth learning from:**

| Problem | Why it's wrong | Fix |
|---|---|---|
| `RUN apt install -y pip3 python3` | ⭐ **Redundant and harmful** — the `python:3.11-slim` base **already contains** Python and pip. This reinstalls a *second*, different Python (and `pip3` isn't even a valid Debian package name — it's `python3-pip`), adding ~100 MB and version confusion. | **Delete the line entirely.** |
| `apt update` without cleanup, in its own layer | Leaves the apt cache baked into the image; risks the stale-cache bug | Chain `apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*` |
| `pip install -r requirements.txt` | No `--no-cache-dir` → pip's wheel cache is stored in the image; and there's no `requirements.txt` in the folder, so the build fails | Add `--no-cache-dir`; create the file (even if empty) |

**Corrected version:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Base image already has python + pip — no apt needed at all.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
```

**If you genuinely need extra OS packages:**
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*
```

---

## 📦 Complete Reference Dockerfiles

### Python Flask web app (from the interview-prep material)
```dockerfile
# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["flask", "run", "--host=0.0.0.0"]
```
```bash
docker build -t myapp:1.0 .
docker run -d -p 5000:5000 myapp:1.0
```
> ⭐ Note `--host=0.0.0.0`: without it Flask binds `127.0.0.1` **inside** the container and the
> port mapping appears to do nothing.

### Production-grade Node.js (everything applied)
```dockerfile
# syntax=docker/dockerfile:1

# ---------- Stage 1: dependencies ----------
FROM node:24-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# ---------- Stage 2: build ----------
FROM deps AS build
COPY . .
RUN npm run build

# ---------- Stage 3: test (optional gate) ----------
FROM build AS test
RUN npm test

# ---------- Stage 4: production ----------
FROM node:24-alpine AS production

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=build --chown=node:node /app/dist ./dist

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- "http://localhost:${PORT}/health" || exit 1

LABEL org.opencontainers.image.source="https://github.com/user/repo"

CMD ["node", "dist/server.js"]
```

### Go — the smallest possible image
```dockerfile
FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app ./cmd/server

FROM scratch                                   # ⭐ nothing but your binary
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /app /app
EXPOSE 8080
ENTRYPOINT ["/app"]
# Final size: ~10 MB
```

---

## 📋 Quick Cheat Sheet

```dockerfile
# ---------- STRUCTURE (ordered for cache efficiency) ----------
FROM node:24-alpine AS builder    # base (pin the tag!)
ARG VERSION=1.0                   # build-time variable
ENV NODE_ENV=production           # runtime variable
WORKDIR /app                      # working directory (creates it)
RUN apk add --no-cache curl       # build-time command (combine + clean!)
COPY package*.json ./             # ⭐ deps manifest FIRST
RUN npm ci --omit=dev             # ⭐ cached layer
COPY . .                          # source LAST
USER node                         # ⭐ drop root
EXPOSE 3000                       # documentation only!
HEALTHCHECK CMD wget -qO- localhost:3000 || exit 1
ENTRYPOINT ["node"]               # fixed executable
CMD ["server.js"]                 # default args (overridable)
```

```bash
# ---------- BUILD ----------
docker build -t myapp:1.0 .
docker build -f Dockerfile.dev -t myapp:dev .
docker build --target builder -t myapp:build .
docker build --build-arg VERSION=2.0 -t myapp .
docker build --no-cache -t myapp .
docker build --platform linux/amd64 -t myapp .
docker buildx build --platform linux/amd64,linux/arm64 -t user/app --push .

# ---------- INSPECT / OPTIMIZE ----------
docker images
docker history myapp:1.0          # ⭐ find fat layers
docker image inspect myapp:1.0
trivy image myapp:1.0             # ⭐ scan for CVEs

# ---------- CMD vs ENTRYPOINT ----------
CMD ["echo","hi"]                 # docker run img          → hi
                                  # docker run img echo yo  → yo   (OVERRIDDEN)
ENTRYPOINT ["echo"]               # docker run img yo       → yo   (APPENDED)
ENTRYPOINT ["echo"] + CMD ["hi"]  # docker run img          → hi
                                  # docker run img bye      → bye
docker run --entrypoint /bin/sh -it myapp   # override ENTRYPOINT

# ---------- COPY vs ADD ----------
COPY src dst                      # ⭐ default choice
ADD  app.tar.gz /app/             # only for auto-extracting a local tar
COPY --from=builder /app/dist .   # from another stage
COPY --chown=node:node . .        # set ownership
```

**Golden rules**
1. ⭐ Pin base image tags — never `latest`
2. ⭐ Copy dependency manifests before source code
3. ⭐ Combine `RUN` commands and clean up **in the same layer**
4. ⭐ Always add a `.dockerignore`
5. ⭐ Use multi-stage builds when there's a build step
6. ⭐ Run as a non-root `USER`
7. ⭐ Prefer exec form (`["..."]`) for CMD/ENTRYPOINT
8. ⭐ Never bake secrets into `ENV`/`ARG`/layers
9. ⭐ `EXPOSE` documents; `-p` publishes
10. ⭐ Bind to `0.0.0.0`, not `127.0.0.1`

---

## 🔗 References
- Dockerfile reference — https://docs.docker.com/reference/dockerfile/
- Dockerfile best practices — https://docs.docker.com/build/building/best-practices/
- Multi-stage builds — https://docs.docker.com/build/building/multi-stage/
- BuildKit — https://docs.docker.com/build/buildkit/
- Trivy — https://trivy.dev/
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
