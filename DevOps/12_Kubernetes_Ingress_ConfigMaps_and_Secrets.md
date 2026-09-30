# Session 12 — Ingress, ConfigMaps & Secrets 🔐

> **Topics:** Ingress · Ingress Controller · Host & Path-based Routing · TLS · ConfigMaps ·
> Secrets · Environment Variables
>
> 📁 Repo: `session-12-ingress-configmaps-secrets/` — `lab.md` (end-to-end 9-part lab),
> `01-configmap` … `04-full-demo`, and `troubleshooting/secret-base64-gotcha.md`.

---

## 📑 Table of Contents
1. [ConfigMaps](#-configmaps)
2. [Secrets](#-secrets)
3. [The Base64 Newline Bug](#-the-base64-newline-bug)
4. [Injecting Config into Pods](#-injecting-config-into-pods)
5. [ConfigMap Updates Don't Reach Running Pods](#-configmap-updates-dont-reach-running-pods)
6. [Why Ingress Exists](#-why-ingress-exists)
7. [Ingress Controller vs Ingress Resource](#-ingress-controller-vs-ingress-resource)
8. [Path-Based Routing](#-path-based-routing)
9. [Host-Based Routing & TLS](#-host-based-routing--tls)
10. [The Full Demo Walkthrough](#-the-full-demo-walkthrough)
11. [Troubleshooting](#-troubleshooting)
12. [Key Terms Recap](#-key-terms-recap)

---

## 📋 ConfigMaps

> **Store non-sensitive configuration separately from your container image**, so the same image runs
> in dev, staging and production with different settings.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: yatri-app-config
  namespace: default
  labels:
    app: yatri-app
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  APP_PORT: "5000"
  DEFAULT_CURRENCY: "INR"
  MAX_BOOKING_DAYS: "30"
```

> ⭐ **No passwords. No sensitive data. Just configuration values.**
> *(Session 7's rule — "never bake config or secrets into the image" — is what this object exists for.)*

```bash
kubectl apply -f configmap.yaml
kubectl get configmap yatri-app-config
```
```text
NAME               DATA   AGE
yatri-app-config   5      8s
```
```bash
kubectl describe configmap yatri-app-config          # ⭐ values shown in PLAIN TEXT
kubectl get configmap yatri-app-config -o jsonpath='{.data.ENVIRONMENT}'   # → production
```

**Ways to create one:**
```bash
kubectl create configmap app-config --from-literal=ENVIRONMENT=production
kubectl create configmap app-config --from-file=./app.properties
kubectl create configmap app-config --from-env-file=./.env
kubectl apply -f configmap.yaml                      # ⭐ declarative — use this
```

---

## 🔑 Secrets

> **Same idea as a ConfigMap, but for sensitive values** — passwords, tokens, keys, certificates.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: yatri-db-secret
  namespace: default
  labels:
    app: yatri-app
type: Opaque
data:
  # echo -n "yatri_admin" | base64
  POSTGRES_USER: eWF0cmlfYWRtaW4=
  # echo -n "secretpassword" | base64
  POSTGRES_PASSWORD: c2VjcmV0cGFzc3dvcmQ=
  # echo -n "yatri_production_db" | base64
  POSTGRES_DB: eWF0cmlfcHJvZHVjdGlvbl9kYg==
```

```bash
kubectl apply -f secret.yaml
kubectl get secret yatri-db-secret
```
```text
NAME              TYPE     DATA   AGE
yatri-db-secret   Opaque   3      5s
```

**`describe` masks the values** — nobody behind you can read them:
```bash
kubectl describe secret yatri-db-secret
```
```text
Data
====
POSTGRES_DB:        19 bytes
POSTGRES_PASSWORD:  14 bytes
POSTGRES_USER:      11 bytes
```

### ⭐⭐ But Base64 is NOT encryption — prove it yourself
```bash
kubectl get secret yatri-db-secret -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 --decode
```
```text
secretpassword
```

> ⭐⭐ **"Base64 is encoding, not encryption."**
> Anyone who can run `kubectl get secret` can read every password in that namespace.
>
> **Therefore:**
> | Protection | How |
> |---|---|
> | ⭐ **RBAC** | **Restrict who can run `kubectl get secret`** — this is the primary control |
> | **Encryption at rest** | Enable `EncryptionConfiguration` so etcd stores them encrypted |
> | **External secret stores** | HashiCorp Vault, AWS Secrets Manager, Sealed Secrets, External Secrets Operator |
> | **Never commit to Git** | A Secret YAML with real values is a plaintext password in your repo |

### Secret types
| Type | Use |
|---|---|
| `Opaque` | ⭐ Default — arbitrary key/value |
| `kubernetes.io/tls` | ⭐ TLS cert + key (used for Ingress below) |
| `kubernetes.io/dockerconfigjson` | Private registry credentials (`imagePullSecrets`) |
| `kubernetes.io/service-account-token` | Service account tokens |

### ConfigMap vs Secret
| | **ConfigMap** | **Secret** |
|---|---|---|
| For | Non-sensitive config | Sensitive values |
| Stored as | Plain text | ⭐ **Base64 (encoding, not encryption)** |
| `describe` shows values | ✅ Yes | ⭐ ❌ Masked as byte counts |
| Size limit | ~1 MiB | ~1 MiB |
| Can be mounted as env vars or files | ✅ | ✅ |

---

## 💥 The Base64 Newline Bug

> ⭐⭐ **The single most common Secret bug in Kubernetes, and a great debugging drill.**

### The incident
> **Symptom:** PostgreSQL rejects connections with
> `FATAL: password authentication failed for user "yatri_admin"`.
> **The developer's claim:** *"I verified the password is correct! I typed
> `echo "mypassword" | base64`."*

### The investigation
```bash
echo "mypassword" | xxd
```
```text
00000000: 6d79 7061 7373 776f 7264 0a              mypassword.
                                  ^^
                    ⭐ the last byte is 0a — ASCII for \n (newline)
```

```bash
# Wrong way — standard echo appends a hidden newline
echo "mypassword" | base64
# → bXlwYXNzd29yZAo=              ⭐ ends in Ao=  (the "o=" encodes the \n)

# Correct way — -n suppresses the trailing newline
echo -n "mypassword" | base64
# → bXlwYXNzd29yZA==              ⭐ ends in ==
```

> ⭐ **The application receives `mypassword\n` (11 chars) instead of `mypassword` (10 chars).
> The database is correctly rejecting it.**

### The fix
> ⭐⭐ **Always use `echo -n` when encoding secrets.**
>
> **The tell:** Base64 ending in **`Ao=`** means you encoded a trailing newline. Correct output
> ends in **`=`** or **`==`**.

**Or sidestep the whole problem** — let kubectl do the encoding:
```bash
kubectl create secret generic db \
  --from-literal=POSTGRES_PASSWORD='secretpassword'   # ⭐ no manual base64 at all
```

> 💡 **This is the same class of bug as the CRLF line-ending trap in Session 3** — an invisible
> character that makes a string subtly wrong. Both are found the same way: with `xxd`.

---

## 💉 Injecting Config into Pods

Two mechanisms, and you'll use both together:

```yaml
envFrom:
  - configMapRef:
      name: yatri-app-config    # ⭐ injects ALL 5 keys from the ConfigMap at once

env:
  - name: POSTGRES_USER
    valueFrom:
      secretKeyRef:             # ⭐ picks INDIVIDUAL keys from the Secret
        name: yatri-db-secret
        key: POSTGRES_USER
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        name: yatri-db-secret
        key: POSTGRES_PASSWORD
  - name: POSTGRES_DB
    valueFrom:
      secretKeyRef:
        name: yatri-db-secret
        key: POSTGRES_DB
```

| | Meaning |
|---|---|
| ⭐ **`envFrom` + `configMapRef`** | Pull **all keys** from the ConfigMap in one go |
| ⭐ **`env` + `secretKeyRef`** | Pick **individual keys** from the Secret, one by one |

**Verify the injection actually happened:**
```bash
kubectl exec -it deployment/yatri-backend -- env | grep -E "ENVIRONMENT|LOG_LEVEL|POSTGRES"
```
```text
ENVIRONMENT=production
LOG_LEVEL=INFO
DEFAULT_CURRENCY=INR
POSTGRES_USER=yatri_admin
POSTGRES_PASSWORD=secretpassword
POSTGRES_DB=yatri_production_db
```
> ⭐ **The pod reads both ConfigMap and Secret values as ordinary Linux environment variables** —
> the application code doesn't know or care where they came from.

### The other option: mount as files
```yaml
volumes:
  - name: config
    configMap:
      name: yatri-app-config
containers:
  - volumeMounts:
      - name: config
        mountPath: /etc/config
```
| | **Env vars** | **Volume mount** |
|---|---|---|
| Updates reach running pods | ⭐ **Never** (see below) | ⭐ **Yes**, eventually (~60 s) |
| Good for | Simple key/values | Whole config files, TLS certs |
| Visible in `kubectl describe pod` | ✅ (secrets leak here!) | ❌ |

---

## 🔄 ConfigMap Updates Don't Reach Running Pods

⭐ **A live demonstration worth doing once:**

```bash
kubectl patch configmap yatri-app-config --type merge -p '{"data":{"ENVIRONMENT":"staging"}}'
kubectl exec -it deployment/yatri-backend -- env | grep ENVIRONMENT
```
```text
ENVIRONMENT=production        ⭐ IT DID NOT CHANGE
```

> ⭐⭐ **Environment variables are set once, when the container starts.** Patching the ConfigMap
> changes the object in etcd but does nothing to a running process.

```bash
kubectl rollout restart deployment/yatri-backend    # ⭐ the fix
kubectl rollout status deployment/yatri-backend
kubectl exec -it deployment/yatri-backend -- env | grep ENVIRONMENT
```
```text
ENVIRONMENT=staging           ✅ now it's picked up
```

> ⭐ **`kubectl rollout restart` is the command to remember** — it triggers a normal rolling update
> (Session 10), so the config change ships with **zero downtime**.
>
> 💡 **Volume-mounted** ConfigMaps *do* update in place (~60 s), but your app must watch the file.
> Env vars never do. A common production pattern is to hash the ConfigMap into a pod annotation so
> any config change automatically triggers a rollout.

---

## 🚪 Why Ingress Exists

### The problem: one LoadBalancer per service = expensive chaos
```text
Without Ingress:
  Frontend     -> AWS Load Balancer 1 ($25/month)
  Backend API  -> AWS Load Balancer 2 ($25/month)
  Auth         -> AWS Load Balancer 3 ($25/month)
  Payment      -> AWS Load Balancer 4 ($25/month)
  Admin        -> AWS Load Balancer 5 ($25/month)
  ⭐ Total: $125/month just for load balancers
```
> Users also get ugly non-standard URLs like `http://3.15.22.100:30080`, **no SSL/TLS termination,
> no centralised routing**, and no host-based routing (`api.myapp.com` vs `myapp.com`).

### The solution
```text
With Ingress:
  1 AWS Load Balancer ($25/month)
       │
  NGINX Ingress Controller
       │
       ├── yatri.local/         -> Frontend ClusterIP Service
       └── yatri.local/api/*    -> Backend API ClusterIP Service
```

```text
Public Internet
      │ https://yatri.local (Port 80/443)
      ▼
+------------------------------------------+
|   NGINX Ingress Controller Pod           |
|   ⭐ Layer 7 HTTP Reverse Proxy           |
+------------------------------------------+
      │                        │
      │ Path: /                │ Path: /api/*
      ▼                        ▼
+----------------+     +---------------------+
| Frontend Svc   |     | Backend API Svc     |
| (ClusterIP)    |     | (ClusterIP)         |
+----------------+     +---------------------+
```

> ⭐ **This is the direct answer to Session 11's cost problem.** Services stay **ClusterIP**; only the
> Ingress Controller gets a LoadBalancer.

---

## 🎛️ Ingress Controller vs Ingress Resource

> ⭐⭐ **An `Ingress` resource is just a routing rule definition. It does NOTHING on its own.
> You MUST have an Ingress Controller installed** (e.g. `ingress-nginx`).

| | **Ingress resource** | **Ingress Controller** |
|---|---|---|
| What it is | A YAML object — rules | ⭐ A **running pod** (reverse proxy) that reads those rules |
| Analogy | The routing table | The router |
| Without the other | ⭐ Nothing happens | Nothing to route |

```bash
minikube addons enable ingress            # ⭐ on Minikube
kubectl get pods -n ingress-nginx
```
```text
NAME                                        READY   STATUS      RESTARTS   AGE
ingress-nginx-controller-7799c6795f-9k2lw   1/1     Running     0          35s
```
> On **AWS EKS**: install `ingress-nginx` via Helm — one AWS NLB is provisioned for it automatically.

**Key properties:**
- ⭐ Ingress operates at **Layer 7 (HTTP/HTTPS)** — routes on **hostnames** and **URL paths**.
- ⭐ Supports **TLS termination**: configure the certificate once in Ingress; backends speak plain
  HTTP internally. **This is the standard pattern.**
- Other controllers: Traefik, HAProxy, Kong, AWS ALB Controller, Istio Gateway.

---

## 🛣️ Path-Based Routing

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: yatri-ingress
  namespace: default
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  rules:
    - host: yatri.local
      http:
        paths:
          - path: /api(/|$)(.*)                  # ⭐ regex capture groups
            pathType: ImplementationSpecific
            backend:
              service:
                name: yatri-backend-service
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: yatri-frontend-service
                port:
                  number: 80
```

> One rule, one host (`yatri.local`), two paths: **`/api/*` → backend**, **`/` → frontend**.

### The three `pathType` values ⭐
| `pathType` | Meaning |
|---|---|
| **`Prefix`** | Matches by URL path prefix, split on `/` — the common choice |
| **`Exact`** | Must match exactly, case-sensitive |
| ⭐ **`ImplementationSpecific`** | Delegates matching to the controller — **required for NGINX regex + rewrite** |

### The rewrite-target mechanism ⭐
```
path:            /api(/|$)(.*)
                      │      └── capture group $2  ← everything after /api/
rewrite-target:  /$2

Request:   yatri.local/api/health
Backend receives:      /health        ⭐ the /api prefix is STRIPPED
```
> ⭐ **Without `rewrite-target`, the backend would receive `/api/health`** and 404 — because the
> backend doesn't know it's mounted under `/api`. This is the classic Ingress gotcha.

**Simple prefix version, no regex** (`path-based.yml`):
```yaml
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: frontend-service, port: { number: 80 } }
          - path: /api
            pathType: Prefix
            backend:
              service: { name: backend-service, port: { number: 80 } }
```

---

## 🔒 Host-Based Routing & TLS

### Step 1 — Generate a self-signed certificate
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key \
  -out tls.crt \
  -subj "/CN=campus.local/O=CampusDevOps"
```

### Step 2 — Store it as a `kubernetes.io/tls` Secret ⭐
```bash
kubectl create secret tls campus-tls-cert --cert=tls.crt --key=tls.key
kubectl get secret campus-tls-cert
```
```text
NAME              TYPE                DATA   AGE
campus-tls-cert   kubernetes.io/tls   2      5s
```
> ⭐ **This is where Secrets and Ingress meet** — the certificate is just another Secret, of a
> specific type.

### Step 3 — Ingress with TLS + multiple hosts
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: campus-ingress-tls
  namespace: default
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"     # ⭐ force HTTP → HTTPS
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - portal.campus.local
        - api.campus.local
      secretName: campus-tls-cert        # ⭐ the TLS Secret
  rules:
    - host: portal.campus.local          # Host 1: frontend
      http:
        paths:
          - path: /()(.*)
            pathType: ImplementationSpecific
            backend:
              service: { name: yatri-frontend-service, port: { number: 80 } }

    - host: api.campus.local             # Host 2: backend (host + path routing)
      http:
        paths:
          - path: /api(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service: { name: yatri-backend-service, port: { number: 80 } }
```

```bash
kubectl apply -f 03-ingress/ingress-tls.yaml
kubectl get ingress campus-ingress-tls
```
```text
NAME                 CLASS   HOSTS                                  ADDRESS        PORTS     AGE
campus-ingress-tls   nginx   portal.campus.local,api.campus.local   192.168.49.2   80, 443   10s
```
> ⭐ **`PORTS` showing `80, 443` confirms both HTTP and HTTPS are active.**

### Step 4 — Test without editing `/etc/hosts`
```bash
INGRESS_IP=$(kubectl get ingress campus-ingress-tls -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl -k --resolve portal.campus.local:443:$INGRESS_IP https://portal.campus.local/
curl -k --resolve api.campus.local:443:$INGRESS_IP    https://api.campus.local/api/health
```
| Flag | Why |
|---|---|
| ⭐ `-k` | Ignore the self-signed certificate warning |
| ⭐ `--resolve host:port:IP` | Fake the DNS entry **for this request only** — no `/etc/hosts` edit |

> ⭐ **Why host-based routing needs the `Host` header:** one IP serves many hostnames, so the
> controller decides which backend to use by reading the `Host` header (or **SNI** for HTTPS).
> That's why every test below passes `-H "Host: yatri.local"`.

---

## 🧪 The Full Demo Walkthrough

`04-full-demo/` assembles everything: ConfigMap + Secret + backend + frontend + Ingress.

```bash
cd 04-full-demo
# configmap.yaml  secret.yaml  backend.yaml  frontend.yaml  ingress.yaml  run-demo.sh  cleanup.sh
```

### The flow
```bash
kubectl apply -f configmap.yaml     # 5 plain-text keys
kubectl apply -f secret.yaml        # 3 base64 keys
kubectl apply -f backend.yaml       # deployment + ClusterIP service, consumes both
kubectl apply -f frontend.yaml      # deployment + ClusterIP service
minikube addons enable ingress
kubectl apply -f ingress.yaml
```

Both services are **ClusterIP** — ⭐ **only reachable from inside the cluster. That's exactly why
we need Ingress:**
```text
NAME                     TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
yatri-frontend-service   ClusterIP   10.96.45.12    <none>        80/TCP    22s
yatri-backend-service    ClusterIP   10.96.112.88   <none>        80/TCP    3m
```

Wait for the Ingress to get an address:
```bash
kubectl get ingress yatri-ingress
```
```text
NAME            CLASS   HOSTS        ADDRESS        PORTS   AGE
yatri-ingress   nginx   yatri.local  192.168.49.2   80      15s
```
> ⭐ **An empty `ADDRESS` column means the controller hasn't picked it up yet** — wait, or check
> that the controller pod is running and `ingressClassName` matches.

```bash
kubectl describe ingress yatri-ingress
```
```text
Rules:
  Host         Path                  Backends
  ----         ----                  --------
  yatri.local  /api(/|$)(.*)         yatri-backend-service:80
               /                     yatri-frontend-service:80
```

### Test both routes through one IP ⭐
```bash
INGRESS_IP=$(minikube ip)

curl -s -H "Host: yatri.local" http://${INGRESS_IP}/ | grep -i "<title>"
# → <title>Welcome to nginx!</title>              ⭐ frontend

curl -s -H "Host: yatri.local" http://${INGRESS_IP}/api/
```
```text
Yatri Backend API
=================
ENVIRONMENT     : production
LOG_LEVEL       : INFO
DEFAULT_CURRENCY: INR
POSTGRES_USER   : yatri_admin
POSTGRES_DB     : yatri_production_db
```
> ⭐⭐ **Both paths work through ONE IP address and ONE Ingress Controller pod** — and the backend
> response proves the ConfigMap and Secret were injected correctly. The whole session in one curl.

### See everything at once
```bash
kubectl get configmap yatri-app-config
kubectl get secret    yatri-db-secret
kubectl get pods      -l app=yatri-frontend
kubectl get pods      -l app=yatri-backend
kubectl get svc       yatri-frontend-service yatri-backend-service
kubectl get ingress   yatri-ingress
```

### Cleanup
```bash
bash cleanup.sh          # deletes ingress → deployments/services → secret → configmap
```

---

## 🔧 Troubleshooting

| Symptom | Likely cause |
|---|---|
| ⭐ **DB rejects a correct-looking password** | ⭐⭐ **Trailing newline** — you used `echo` instead of `echo -n`. Tell: base64 ends in `Ao=` |
| ⭐ **ConfigMap changed but pod still shows old value** | Env vars are set at container start — ⭐ **`kubectl rollout restart`** |
| **Ingress `ADDRESS` stays empty** | Controller not installed/running, or `ingressClassName` mismatch |
| **404 from the backend through Ingress** | ⭐ Missing `rewrite-target` — backend received `/api/health` instead of `/health` |
| **404 / default backend** | Wrong `Host` header — Ingress routes by host; use `-H "Host: ..."` |
| **503 from Ingress** | Backend Service has ⭐ **no ready endpoints** (`kubectl get endpoints`) |
| **TLS not active (`PORTS` shows only 80)** | `tls:` block missing, or `secretName` doesn't exist |
| **`ImagePullBackOff` on the controller** | Addon not fully enabled — `kubectl get pods -n ingress-nginx` |

```bash
kubectl describe ingress <name>                    # rules + events
kubectl get endpoints <service>                    # ⭐ empty = the real problem
kubectl logs -n ingress-nginx <controller-pod>     # ⭐ the actual nginx errors
kubectl exec -it deployment/<app> -- env           # did config actually inject?
```

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **ConfigMap** | Non-sensitive key/value config, stored in plain text |
| **Secret** | Sensitive key/value config, ⭐ **base64-encoded, NOT encrypted** |
| ⭐ **Base64 ≠ encryption** | Anyone with `kubectl get secret` can decode it ⇒ **protect with RBAC** |
| ⭐ **`echo -n`** | Suppresses the trailing newline; ⭐ base64 ending in **`Ao=`** means you forgot it |
| **`type: Opaque`** | Default Secret type |
| ⭐ **`kubernetes.io/tls`** | Secret type holding a cert + key, used by Ingress |
| ⭐ **`envFrom` + `configMapRef`** | Inject **all** ConfigMap keys at once |
| ⭐ **`env` + `secretKeyRef`** | Inject **individual** Secret keys |
| ⭐ **Env vars are set once** | ConfigMap edits need **`kubectl rollout restart`** |
| **Volume-mounted config** | Updates in place (~60 s), unlike env vars |
| ⭐ **Ingress resource** | Routing **rules** — does nothing alone |
| ⭐ **Ingress Controller** | The **running reverse proxy** that implements the rules (ingress-nginx, Traefik…) |
| **Layer 7 routing** | Routes on **host** and **path**, unlike a Layer-4 LoadBalancer |
| **`pathType`** | `Prefix` · `Exact` · ⭐ `ImplementationSpecific` (needed for NGINX regex) |
| ⭐ **`rewrite-target`** | Strips the matched prefix before forwarding — without it you get 404s |
| **`ssl-redirect`** | Annotation forcing HTTP → HTTPS |
| **TLS termination** | Ingress decrypts; backends speak plain HTTP internally |
| ⭐ **`curl --resolve`** | Fake DNS for one request instead of editing `/etc/hosts` |
| **`ingressClassName`** | Which controller should pick up this Ingress |

---

## 🎯 Session Takeaways

1. **ConfigMaps and Secrets keep configuration out of the image** — the same image runs everywhere
   with different settings.
2. ⭐⭐ **A Secret is base64-encoded, not encrypted.** `kubectl get secret … | base64 --decode` prints
   the password. **RBAC is the actual protection**, plus encryption-at-rest and external secret stores.
3. ⭐⭐ **Always `echo -n` when hand-encoding.** A trailing `\n` makes a 14-character password
   15 characters, and the database is right to reject it. **Base64 ending in `Ao=` is the tell.**
   Better still: let `kubectl create secret --from-literal` encode for you.
4. ⭐ **`envFrom` pulls a whole ConfigMap; `secretKeyRef` picks individual Secret keys.** The app just
   sees ordinary environment variables.
5. ⭐⭐ **Editing a ConfigMap does nothing to running pods** — env vars are fixed at container start.
   **`kubectl rollout restart`** ships the change with zero downtime.
6. ⭐ **One LoadBalancer per service is the problem Ingress solves** — 5 services = $125/month vs $25.
   Keep app Services as **ClusterIP** and expose only the controller.
7. ⭐⭐ **The Ingress resource is inert without an Ingress Controller.** Rules vs router.
8. ⭐ **Ingress is Layer 7** — it routes on host and path, which a Layer-4 LoadBalancer simply cannot do.
9. ⭐ **`rewrite-target` is the classic gotcha** — without it the backend receives the `/api` prefix
   it doesn't expect and returns 404.
10. ⭐ **TLS lives in a `kubernetes.io/tls` Secret**, terminates at the Ingress, and backends keep
    talking plain HTTP — the standard production pattern.
11. ⭐ **Host-based routing depends on the `Host` header**, so test with `-H "Host: ..."` or
    `curl --resolve`.
12. ⭐ **Empty Ingress `ADDRESS` → controller problem; 503 through Ingress → empty Service
    endpoints.** Different layers, different fixes.

---

## 🔗 References
- Ingress — https://kubernetes.io/docs/concepts/services-networking/ingress/
- Ingress Controllers — https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/
- ConfigMaps — https://kubernetes.io/docs/concepts/configuration/configmap/
- Secrets — https://kubernetes.io/docs/concepts/configuration/secret/
- Course repo — https://github.com/Nency-Ravaliya/devops-heros

---

## ➡️ Next
**[Session 13 — Storage, HPA & Probes](./13_Kubernetes_Storage_HPA_and_Probes.md)**
