# ⚡ S12 · Ingress, ConfigMaps & Secrets

> *Revision card.* Full notes → [Session 12](../12_Kubernetes_Ingress_ConfigMaps_and_Secrets.md)

---

## 🔑 One-line core

***A Secret is base64-encoded, NOT encrypted.*** And an Ingress **resource** does nothing
without an Ingress **controller**.

---

## 🗂️ ConfigMap

```bash
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=debug \
  --from-file=app.properties
```

**Two ways to consume:**

```yaml
# 1 — as env vars
envFrom:
  - configMapRef: { name: app-config }

# 2 — as files (⭐ these DO auto-update, ~60 s)
volumeMounts:
  - { name: cfg, mountPath: /etc/config }
volumes:
  - name: cfg
    configMap: { name: app-config }
```

> ⚠️ **Editing a ConfigMap does nothing to running Pods** when it's injected as **env
> vars**. → ⭐ **`kubectl rollout restart deploy/<name>`**
> Mounted as a **volume**, the file updates itself — but your app has to re-read it.

---

## 🔐 Secret

```bash
kubectl create secret generic db-secret \
  --from-literal=password='s3cr3t'
```

```bash
echo -n 's3cr3t' | base64      # ⭐ -n  or you encode a NEWLINE
echo 'czNjcjN0' | base64 -d
```

> ⚠️ **The classic bug:** `echo 'pw' | base64` includes a trailing `\n`. Your app
> authenticates with `"pw\n"` and fails with a useless error. **Always `echo -n`.**

| Type | For |
|---|---|
| `Opaque` | generic |
| `kubernetes.io/dockerconfigjson` | registry pull secret |
| `kubernetes.io/tls` | cert + key |

**What actually protects a Secret:**

- ⭐ **RBAC** — who can `get secrets`
- encryption at rest in etcd (`EncryptionConfiguration`)
- External Secrets / Sealed Secrets / Vault
- ⚠️ **Not** base64

---

## 🚦 Ingress — resource vs controller

```
Internet → [Ingress CONTROLLER]  ← nginx/traefik Pod; a real LoadBalancer Service
                   │  reads
            [Ingress RESOURCE]   ← just YAML rules
                   │
              Services → Pods
```

> ⚠️ **No controller installed ⇒ your Ingress does absolutely nothing**, silently.

---

## 🛣️ Routing

```yaml
spec:
  ingressClassName: nginx
  rules:
    - host: api.example.com                 # host-based
      http:
        paths:
          - path: /v1
            pathType: Prefix                # ⭐ Prefix | Exact | ImplementationSpecific
            backend:
              service: { name: api-v1, port: { number: 80 } }
  tls:
    - hosts: [api.example.com]
      secretName: api-tls                   # kubernetes.io/tls
```

---

## ✂️ `rewrite-target` — the one that confuses everyone

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
    - http:
        paths:
          - path: /api(/|$)(.*)
            pathType: Prefix
```

`/api/users` → backend sees **`/users`**. Without it the backend gets `/api/users` and
404s.

---

## 🔒 TLS

- Ingress **terminates** TLS — traffic inside the cluster is usually plaintext
- **cert-manager** + Let's Encrypt automates issue **and renewal**
- ⚠️ *"The cert expired at 3am"* is the classic outage

---

## ⚠️ Traps

| Trap | Reality |
|---|---|
| Secrets are encrypted | ⚠️ **base64 only** |
| `echo 'x' \| base64` | ⚠️ encodes a **newline** |
| Ingress works out of the box | ⚠️ needs a controller |
| ConfigMap edit reaches running pods | ⚠️ not via env vars |
| Ingress does TCP | ⚠️ it's **HTTP/HTTPS (L7)** only |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Is a Secret secure? | **No** — RBAC + encryption at rest is |
| Changed a ConfigMap, nothing happened? | `kubectl rollout restart` |
| Ingress created, 404 everywhere? | **no controller**, or wrong `ingressClassName` |
| Password fails but looks right? | missing `echo -n` |
| Non-HTTP traffic? | Service `LoadBalancer` / NodePort, not Ingress |

---

⬅️ [S11](./11_Kubernetes_Networking_and_Services.md) · ➡️ [S13 · Storage & HPA](./13_Storage_HPA_Probes.md)
