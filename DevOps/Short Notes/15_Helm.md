# ⚡ S15 · Helm

> *Revision card.* Full notes → [Session 15](../15_Helm.md)

---

## 🔑 One-line core

***Chart = recipe, Values = ingredients, Release = the cooked meal.***
`helm template` **before** `helm install`.

---

## 📦 The three nouns

| | |
|---|---|
| **Chart** | packaged, templated Kubernetes manifests + defaults |
| **Release** | one *installed instance* — many per cluster from one chart |
| **Revision** | a numbered snapshot; created by install, upgrade **and rollback** |

Helm **renders locally, then applies plain YAML**. Nothing Helm-specific runs in your cluster.

---

## 📂 Chart layout

```
my-chart/
├── Chart.yaml          metadata (REQUIRED)
├── values.yaml         defaults
├── charts/             subcharts
├── crds/               applied first, never templated
├── .helmignore
└── templates/
    ├── deployment.yaml  service.yaml
    ├── _helpers.tpl     ← leading _ = partial, not an object
    ├── NOTES.txt        ← printed after install
    └── tests/
```

---

## 📇 `Chart.yaml` — the classic confusion

```yaml
apiVersion: v2        # v2 = Helm 3
name: my-app
version: 0.1.0        # ⭐ the CHART's version — SemVer enforced
appVersion: "1.5.0"   # ⭐ the APP's version (image tag) — quote it
type: application     # or library
```

| | Changes when |
|---|---|
| `version` | you edit templates/values |
| `appVersion` | you ship a new image |

---

## 🎚️ Values precedence — last wins

```
chart values.yaml → parent chart → -f file (left→right) → --set → --set-string/--set-file
     lowest                                                            highest
```

```bash
helm install app ./chart -f values-prod.yaml --set image.tag=v2
helm get values app --all        # what a live release actually used
```

> ⭐ **Prefer `-f values-prod.yaml` in CI** — it's in Git, reviewable, auditable.
> `--set` lives only in somebody's shell history.

---

## 🧬 Templating

| | |
|---|---|
| `{{ .Values.x }}` | from values |
| `{{ .Release.Name }}` `.Namespace` `.Revision` | release info |
| `{{ .Chart.Name }}` `.Version` `.AppVersion` | chart info |
| `{{ .Capabilities.KubeVersion }}` | cluster |
| `{{- if }} {{- end }}` | ⭐ `{{-` eats preceding whitespace **incl. the newline** |
| `{{ x \| default y }}` `\| quote` `\| b64enc` | pipelines |
| `{{ required "msg" .Values.x }}` | ⭐ fail loudly on a missing value |
| `{{ toYaml .Values.r \| nindent 12 }}` | splice a block |
| `{{ include "name" . }}` | ⭐ use **include**, never bare `template` |

> ⚠️ `template` can't be piped; `include` returns a string so `| nindent` works.
> And **don't forget the trailing `.`** — it passes the context.

---

## 🚀 Lifecycle

```bash
helm create my-chart
helm lint ./chart
helm template rel ./chart               # ⭐ render locally, no cluster
helm install rel ./chart                # REVISION 1
helm upgrade rel ./chart --set replicaCount=3    # REVISION 2
helm history rel
helm rollback rel 1                     # REVISION 3 ⭐ rollback APPENDS
helm uninstall rel                      # removes EVERYTHING it created
```

| Command | Exists | Doesn't |
|---|---|---|
| `helm install` | ❌ fails | ✅ |
| `helm upgrade` | ✅ | ❌ fails |
| **`helm upgrade --install`** | ✅ | ✅ ⭐ **use this in CI** |

---

## ⚛️ `--atomic` — don't ship broken

```bash
helm upgrade --install app ./chart -f values-prod.yaml \
  --set image.tag=$GIT_SHA --atomic --wait --timeout 5m
```

> ⚠️ **Plain `helm upgrade` reports success as soon as the API server accepts the YAML** —
> your Pods can be in `ImagePullBackOff` and Helm says `STATUS: deployed`.
> `--atomic` waits and **auto-rolls-back** — but it is **only as good as your readiness
> probes**.

---

## 🕰️ Helm 2 vs 3 — interview favourite

| | Helm 2 | **Helm 3** |
|---|---|---|
| Server | **Tiller** pod | none, client-only |
| Permissions | ⚠️ Tiller ran as `cluster-admin` | your kubeconfig / RBAC |
| State | ConfigMaps | **Secrets** in the namespace |
| apiVersion | v1 | **v2** |

---

## 🐞 Debug

```bash
helm template rel ./chart --debug
helm install rel ./chart --dry-run --debug
helm get manifest rel
helm diff upgrade rel ./chart      # plugin
```

| Error | Cause |
|---|---|
| `error converting YAML to JSON` | indentation — check `{{-` / `nindent` |
| `nil pointer evaluating interface` | value missing from values.yaml |
| `cannot re-use a name` | use `upgrade --install` |
| stuck `pending-upgrade` | delete the stuck `sh.helm.release.v1.*` Secret, then rollback |
| `field is immutable` | changed a Deployment **selector** → delete + reinstall |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| `version` vs `appVersion`? | the chart vs the app |
| CI deploy command? | `helm upgrade --install … --atomic --wait` |
| Rollback deletes history? | **no** — it appends a revision |
| Why Helm 3 dropped Tiller? | it ran as cluster-admin |
| YAML broken after templating? | `helm template` + whitespace control |

---

⬅️ [S14](./14_Kubernetes_Troubleshooting.md) · ➡️ [S16 · GitHub Actions](./16_CICD_and_GitHub_Actions.md)
