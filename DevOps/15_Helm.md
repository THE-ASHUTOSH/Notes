# Session 15 — Helm ⎈

> **Topics:** What is Helm? · Helm Charts · Chart Structure · `Chart.yaml` · `values.yaml` ·
> Templates · Install & Upgrade · Rollback · Deploying an Application with Helm
>
> 📁 Repo: `session-15-helm/` — nine numbered folders (`01-what-is-helm` → `09-deploying-application`),
> several real charts (`demo-chart`, `myapp`, `simple-chart`, `my-app`, `template-demo`) and a
> **Notes App** mini-project.

Sessions 9–14 all ended the same way: `kubectl apply -f <some>.yaml`. That breaks down the moment
you need the *same* app in dev, staging and prod with different replica counts, images and
hostnames. Helm is the fix.

---

## 📑 Table of Contents

1. [The Problem Helm Solves](#-the-problem-helm-solves)
2. [Chart · Release · Values](#-chart--release--values)
3. [Installing Helm & First Commands](#-installing-helm--first-commands)
4. [Helm 2 vs Helm 3](#-helm-2-vs-helm-3)
5. [Creating a Chart](#-creating-a-chart)
6. [Chart Structure](#-chart-structure)
7. [`Chart.yaml`](#-chartyaml)
8. [`values.yaml` & Value Precedence](#-valuesyaml--value-precedence)
9. [Templates — Go Templating](#-templates--go-templating)
10. [Named Templates, `_helpers.tpl` & `NOTES.txt`](#-named-templates-_helperstpl--notestxt)
11. [Install & Upgrade](#-install--upgrade)
12. [Rollback](#-rollback)
13. [Full Walkthrough: the Guestbook / Notes chart](#-full-walkthrough-the-guestbook--notes-chart)
14. [Beyond the lab: dependencies, repos, hooks & tests](#-beyond-the-lab-dependencies-repos-hooks--tests)
15. [Debugging Helm](#-debugging-helm)
16. [Command Cheat Sheet](#-command-cheat-sheet)
17. [Key Terms Recap](#-key-terms-recap)
18. [Session Takeaways](#-session-takeaways)

---

## 🎯 The Problem Helm Solves

Without Helm, three environments means three copies of every manifest:

```
            Dev            Staging        Production
replicas     1                2               10
CPU         small           medium          large
image tag   :dev            :rc             :v2.1.0
host        dev.app.io      stg.app.io      app.io
```

Change one field and you edit it in three places — this is **configuration drift**, and it is
how "it works in staging" happens.

> **Helm is the package manager for Kubernetes.**
> Write **one chart**, pass **different values**.

The analogy the course uses, and it's a good one:

| Helm thing | Analogy |
|---|---|
| **Chart** | the **recipe** |
| **Values** | the **ingredients** you choose |
| **Release** | the **cooked meal** running in the cluster |

Compare it to what you already know: `apt`/`npm` install a package with defaults you can
configure. Helm does that for a whole Kubernetes application — Deployment + Service + Ingress
+ ConfigMap + HPA, installed, upgraded and removed as **one unit**.

---

## 🧩 Chart · Release · Values

```
   Chart (templates + defaults)
            │
            │  +  Values  (values.yaml, -f file, --set)
            ▼
     Rendered Kubernetes YAML
            │
            ▼
        RELEASE  ──▶  revision 1, 2, 3 … (history, rollback)
```

⭐ Three facts that make the rest make sense:

1. **One chart can produce many releases** in the same cluster (`helm install app-a ./chart`,
   `helm install app-b ./chart`) — which is exactly why templates are named
   `{{ .Release.Name }}-app` and not hard-coded.
2. **Helm renders locally, then applies.** The cluster only ever sees plain Kubernetes YAML.
   Nothing "Helm" runs inside your Pods.
3. **Every install/upgrade/rollback creates a new revision**, stored as a Secret in the release's
   namespace. That's what makes rollback possible.

---

## ⚙️ Installing Helm & First Commands

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
# version.BuildInfo{Version:"v3.15.0", ...}
```

```bash
helm list                                             # releases in current namespace
helm list -A                                          # all namespaces

helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo nginx

helm install my-nginx bitnami/nginx
# NAME: my-nginx / STATUS: deployed / REVISION: 1

kubectl get pods,svc
helm uninstall my-nginx       # removes every resource the release created
```

⭐ `helm uninstall` is the quiet superpower: it deletes **everything the release created** —
Deployment, Service, ConfigMap, ServiceAccount — because Helm tracks exactly what it rendered.
Hand-written `kubectl apply` leaves you to remember.

> Helm uses your **kubeconfig** — the same current-context and RBAC permissions as `kubectl`.
> Add `-n <namespace>` (and `--create-namespace` on install) just like kubectl.

---

## 🕰️ Helm 2 vs Helm 3

| | Helm 2 | Helm 3 ✅ |
|---|---|---|
| Server component | **Tiller** pod in the cluster | None — client only |
| Permissions | Tiller ran as `cluster-admin` ⚠️ | Your own kubeconfig / RBAC |
| Release state | ConfigMaps owned by Tiller | **Secrets** in the release namespace |
| Namespaces | Releases global | Releases scoped to a namespace |
| CRDs | Awkward | `crds/` directory |
| Chart apiVersion | `v1` | **`v2`** |

Tiller was the security problem: anyone who could talk to it could do anything in the cluster.
Helm 3 removed it. **This is a standard interview question.**

---

## 🏗️ Creating a Chart

```bash
helm create demo-chart
ls demo-chart/
# Chart.yaml  charts  templates  values.yaml
ls demo-chart/templates/
# NOTES.txt  _helpers.tpl  deployment.yaml  hpa.yaml  httproute.yaml
# ingress.yaml  service.yaml  serviceaccount.yaml  tests/
```

That scaffold is a **complete, working, production-shaped chart** — Deployment, Service,
Ingress, HPA, ServiceAccount, a Helm test, and helper templates. It's the fastest way to learn
chart conventions: read it rather than writing from a blank page.

```bash
helm template my-release demo-chart     # ⭐ render locally, no cluster needed
helm install demo-release demo-chart
helm list
helm uninstall demo-release
```

| Command | Does |
|---|---|
| `helm create` | generate a working chart skeleton |
| `helm template` | render to stdout — **no cluster, no release** |
| `helm lint` | static checks on the chart |
| `helm install` | render **and** apply, creating a release |
| `helm uninstall` | delete every resource in the release |

⭐ **`helm template` is your main debugging tool.** Before you blame Kubernetes, look at what
Helm actually produced.

---

## 📂 Chart Structure

```text
my-chart/
├── Chart.yaml          # who is this chart?  (metadata — REQUIRED)
├── values.yaml         # what are the defaults?
├── charts/             # subcharts / dependencies
├── crds/               # CustomResourceDefinitions (installed first, never templated)
├── .helmignore         # like .gitignore / .dockerignore — excluded from the package
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── _helpers.tpl    # reusable named templates (leading _ ⇒ never rendered as an object)
    ├── NOTES.txt       # message printed after install
    └── tests/
        └── test-connection.yaml
```

Rules worth knowing:

- Files in `templates/` are rendered as Kubernetes objects — **except** those starting with `_`
  (partials) and `NOTES.txt`.
- `charts/` holds dependencies; `crds/` are applied **before** everything else and are *not*
  templated or upgraded.
- `.helmignore` keeps junk out of the packaged `.tgz` — same idea as `.gitignore`
  ([Session 5](./05_Git_and_GitHub.md)) and `.dockerignore` ([Session 7](./07_Docker_Images_and_Dockerfile.md)).

---

## 📇 `Chart.yaml`

```yaml
apiVersion: v2              # REQUIRED — v2 means Helm 3
name: my-app                # REQUIRED
version: 0.1.0              # REQUIRED — SemVer, the CHART's own version
appVersion: "1.0"           # the APPLICATION's version (usually the image tag)
description: A learning chart
type: application           # or: library
keywords: [nginx, web]
home: https://example.com
maintainers:
  - name: Nency
    email: nency@example.com
```

### ⭐ `version` vs `appVersion` — the classic confusion

| Field | Versions | Changes when | SemVer enforced |
|---|---|---|---|
| `version` | the **chart** | you edit templates/values | **Yes** |
| `appVersion` | the **application** | you ship a new image | No (quote it — `"1.0"` is a string) |

```yaml
version: 0.2.0        # you added a template
appVersion: "1.5.0"   # the Docker image tag you deploy
```

### `type`

| Type | Meaning |
|---|---|
| `application` | deploys resources — use this for ~everything |
| `library` | only shared templates; can't be installed on its own |

### Validate it

```bash
helm lint my-app/
# ==> Linting my-app/
# 1 chart(s) linted, 0 chart(s) failed
```

### Use the metadata in templates

```yaml
metadata:
  labels:
    chart: "{{ .Chart.Name }}-{{ .Chart.Version }}"
    app.kubernetes.io/version: "{{ .Chart.AppVersion }}"
```

---

## 🎛️ `values.yaml` & Value Precedence

Hard-coding kills reuse:

```yaml
replicas: 1                   # hardcoded ❌
image: nginx:latest           # hardcoded ❌
```

```yaml
replicas: {{ .Values.replicaCount }}                            # ✅
image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}" # ✅
```

`values.yaml` — the defaults, committed to Git:

```yaml
replicaCount: 1

image:
  repository: nginx
  tag: latest

service:
  port: 80

app:
  name: demo-app
```

### Overriding

```bash
# A — a whole file per environment  ⭐ preferred
helm install my-app ./chart -f values-prod.yaml

# B — individual values
helm install my-app ./chart --set replicaCount=3
helm install my-app ./chart --set image.tag=v2,service.port=8080
helm install my-app ./chart --set-string version=1.0     # force string
helm install my-app ./chart --set-file cert=./tls.crt    # value from a file
```

### ⭐ Precedence (last one wins)

```
chart's values.yaml  →  parent chart values  →  -f file  (left to right)  →  --set  →  --set-string/--set-file
  lowest                                                                                         highest
```

Multiple `-f` flags are allowed and merge **left to right**, so
`-f base.yaml -f prod.yaml` lets prod override base.

### Verify before you deploy

```bash
helm template my-app ./chart | grep "replicas:"                      #   replicas: 1
helm template my-app ./chart --set replicaCount=3 | grep "replicas:" #   replicas: 3
helm get values my-app                                               # what a live release used
helm get values my-app --all                                         # including chart defaults
```

> ⚠️ **In production, prefer `-f values-prod.yaml` over `--set`.** A values file is in Git,
> reviewable and auditable; a `--set` lives only in somebody's shell history. `--set` is also
> genuinely awkward for lists and for values containing `.` or `,` (you must escape them:
> `--set nodeSelector."kubernetes\.io/role"=worker`).

---

## 🧬 Templates — Go Templating

A template is ordinary Kubernetes YAML with `{{ }}` holes in it.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-app
  labels:
    app: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.service.port }}
```

### Built-in objects

| Object | Gives you | Example |
|---|---|---|
| `.Values` | everything from values.yaml + overrides | `{{ .Values.replicaCount }}` |
| `.Release` | `.Name` `.Namespace` `.Revision` `.IsInstall` `.IsUpgrade` | `{{ .Release.Name }}` |
| `.Chart` | the `Chart.yaml` fields | `{{ .Chart.Version }}` |
| `.Capabilities` | cluster version & available APIs | `{{ .Capabilities.KubeVersion.Minor }}` |
| `.Files` | non-template files in the chart | `{{ .Files.Get "config.ini" }}` |
| `.Template` | current template's name/path | — |

### Conditionals

```yaml
{{- if .Values.service.enabled }}
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}-svc
spec:
  ports:
    - port: {{ .Values.service.port }}
{{- end }}
```

If `service.enabled` is false, **the whole object disappears** from the output.

```yaml
{{- if eq .Values.env "production" }} ... {{- else }} ... {{- end }}
{{- range .Values.hosts }}
  - host: {{ . }}
{{- end }}
{{- with .Values.resources }}
  resources:
    {{- toYaml . | nindent 4 }}
{{- end }}
```

### ⭐ Whitespace control: `{{-` and `-}}`

YAML is indentation-sensitive, and template tags leave blank lines behind. A leading `{{-`
eats the preceding whitespace **including the newline**; a trailing `-}}` eats what follows.
This is the #1 source of "why is my YAML invalid" in Helm.

### Functions & pipelines you'll actually use

```yaml
{{ .Values.name | quote }}                 # wrap in "quotes"
{{ .Values.name | upper | trunc 63 }}      # pipelines, like shell (Session 3)
{{ .Values.tag | default .Chart.AppVersion }}
{{ required "image.repository is required!" .Values.image.repository }}
{{ toYaml .Values.resources | nindent 12 }}  # embed a whole map with indentation
{{ include "my-app.labels" . | nindent 4 }}
{{ now | date "2006-01-02" }}
{{ .Values.secret | b64enc }}              # ← Secrets want base64 (Session 12)
```

⭐ `required` turns a silent misconfiguration into a loud build failure — use it for anything
that must not have a default (image repo, hostname, DB endpoint).
⭐ `nindent N` = newline + indent N spaces. Use it whenever you splice a block into YAML.

---

## 🧰 Named Templates, `_helpers.tpl` & `NOTES.txt`

`_helpers.tpl` holds reusable snippets. The leading underscore means Helm never treats it as a
Kubernetes object.

```yaml
{{/* Chart name + release name, truncated to the 63-char label limit */}}
{{- define "my-app.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "my-app.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
```

Use them:

```yaml
metadata:
  name: {{ include "my-app.fullname" . }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
```

> ⭐ **`include` over `template`.** `template` is a plain statement and cannot be piped;
> `include` returns a string, so `| nindent 4` works. Always use `include`.
> Note the trailing `.` — it passes the current context into the named template; forget it and
> `.Values` is empty inside.

**Why `trunc 63`?** Kubernetes label values max out at 63 characters. The generated charts do
this everywhere for a reason.

**`NOTES.txt`** is rendered and printed after `helm install` — the "here's your URL" message:

```text
Get the application URL:
  export NODE_PORT=$(kubectl get svc {{ include "my-app.fullname" . }} -o jsonpath="{.spec.ports[0].nodePort}")
  echo http://$NODE_IP:$NODE_PORT
```

---

## 🚀 Install & Upgrade

```bash
helm install web-app ./app-chart
# NAME: web-app / STATUS: deployed / REVISION: 1

helm list
# NAME      NAMESPACE   REVISION   STATUS     CHART
# web-app   default     1          deployed   app-chart-0.1.0

helm upgrade web-app ./app-chart --set replicaCount=3
# Release "web-app" has been upgraded. Happy Helming!
# REVISION: 2
```

### ⭐ `install` vs `upgrade` vs `upgrade --install`

| Command | Release exists | Release doesn't exist |
|---|---|---|
| `helm install` | ❌ fails | ✅ installs |
| `helm upgrade` | ✅ upgrades | ❌ fails |
| **`helm upgrade --install`** | ✅ upgrades | ✅ installs |

```bash
helm upgrade --install web-app ./app-chart     # ⭐ the idempotent form — use in CI/CD
```

This is the single most important Helm line in a pipeline: it works on the first deploy and on
the five-hundredth. You'll see it again in [Session 16](./16_CICD_and_GitHub_Actions.md).

### Flags that matter

```bash
helm upgrade --install app ./chart \
  -n production --create-namespace \
  -f values-prod.yaml \
  --set image.tag=$GIT_SHA \
  --atomic \            # ⭐ roll back automatically if it fails
  --wait \              # block until resources are Ready
  --timeout 5m \
  --history-max 10      # cap stored revisions
```

Every install/upgrade bumps the revision — `1`, `2`, `3`… — and that history is what rollback
walks back through.

---

## ⏪ Rollback

```text
Revision 1: working   (nginx:1.24)
Revision 2: broken    (nginx:doesnotexist)  →  ImagePullBackOff
```

```bash
helm upgrade rollback-demo ./app-chart --set image.tag=doesnotexist
kubectl get pods
# rollback-demo-app-xxxx   0/1   ImagePullBackOff
```

> 🔍 Note that **Helm still reports `STATUS: deployed`** for revision 2. Helm's job finished
> when the API server accepted the manifests — it didn't wait for the Pods to be healthy.
> That is exactly what `--wait` and `--atomic` change.

```bash
helm history rollback-demo
# REVISION   STATUS      DESCRIPTION
# 1          superseded  Install complete
# 2          deployed    Upgrade complete

helm rollback rollback-demo 1
# Rollback was a success! Happy Helming!

helm history rollback-demo
# 1  superseded  Install complete
# 2  superseded  Upgrade complete
# 3  deployed    Rollback to 1       ← ⭐ rollback is a NEW revision
```

⭐ **Rollback never deletes history — it appends.** Revision 3 *is* revision 1's content.
Forward-only history is what makes it auditable.

```bash
helm rollback <release>        # bare = go back one revision
```

### `--atomic`: don't ship broken in the first place

```bash
helm upgrade rollback-demo ./app-chart \
  --set image.tag=doesnotexist \
  --atomic --timeout 60s
```

If Pods aren't Ready inside the timeout, Helm **automatically rolls back** and the command
exits non-zero — so your pipeline fails loudly instead of leaving a broken release behind.
`--atomic` implies `--wait`.

> ⭐ This is only as good as your **readiness probes**
> ([Session 13](./13_Kubernetes_Storage_HPA_and_Probes.md)). With no probe, "Ready" means
> "the process started", and `--atomic` will happily bless a broken app.

---

## 🧪 Full Walkthrough: the Guestbook / Notes chart

The `09-deploying-application` and `mini-project` folders build the same thing — a chart with a
**Deployment + Service + ConfigMap**, deployed to dev then upgraded to prod values.

**`Chart.yaml`**

```yaml
apiVersion: v2
name: notes-chart
description: A simple Notes application Helm chart
type: application
version: 0.1.0
appVersion: "1.0"
```

**`values.yaml`** (dev defaults)

```yaml
replicaCount: 1
image:
  repository: nginx
  tag: "1.24"
service:
  port: 80
  nodePort: 30090
app:
  name: notes-app
  environment: development
```

**`values-prod.yaml`** (the only file that differs per environment)

```yaml
replicaCount: 3
image:
  tag: "1.25"
app:
  environment: production
```

**`templates/configmap.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-config
data:
  APP_NAME: {{ .Values.app.name | quote }}
  ENVIRONMENT: {{ .Values.app.environment | quote }}
```

**`templates/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-deploy
  labels:
    app: {{ .Release.Name }}
    environment: {{ .Values.app.environment }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
        - name: notes
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.service.port }}
          envFrom:
            - configMapRef:
                name: {{ .Release.Name }}-config
```

**`templates/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}-svc
spec:
  type: NodePort
  selector:
    app: {{ .Release.Name }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.port }}
      nodePort: {{ .Values.service.nodePort }}
```

### The 9-step loop

```bash
helm lint notes-chart                                  # 1. syntax
helm template notes-dev notes-chart                    # 2. preview — no {{ }} should remain
helm install notes-dev notes-chart                     # 3. deploy (REVISION 1)
kubectl get pods,svc,configmaps                        # 4. verify
helm upgrade notes-dev notes-chart -f notes-chart/values-prod.yaml   # 5. prod (REVISION 2) → 3 pods
helm history notes-dev                                 # 6. history
helm upgrade notes-dev notes-chart --set image.tag=broken-tag        # 7. break it → ImagePullBackOff
helm rollback notes-dev 2                              # 8. recover (REVISION 3)
helm uninstall notes-dev                               # 9. clean up — everything goes
```

> ⚠️ One gotcha in this chart: the Service hard-codes `nodePort: 30090`. Two releases of the
> same chart in one cluster will collide on that port. In a reusable chart you'd make the
> nodePort optional (`{{- if .Values.service.nodePort }}`) or just use `ClusterIP` + Ingress.

---

## 🔭 Beyond the lab: dependencies, repos, hooks & tests

Not in the repo folders, but you meet all of it immediately on a real team.

### Dependencies (subcharts)

```yaml
# Chart.yaml
dependencies:
  - name: postgresql
    version: "15.5.x"
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled      # toggle from values.yaml
```

```bash
helm dependency update ./my-chart     # downloads into charts/ and writes Chart.lock
helm dependency build ./my-chart      # install exactly what Chart.lock pins
```

Override a subchart's values by nesting under its name:

```yaml
postgresql:
  enabled: true
  auth:
    database: notes
```

### Packaging & sharing

```bash
helm package ./my-chart               # → my-chart-0.1.0.tgz
helm repo index .                     # generate index.yaml for a chart repo

# OCI registries (the modern way — any container registry works)
helm push my-chart-0.1.0.tgz oci://ghcr.io/<user>/charts
helm install app oci://ghcr.io/<user>/charts/my-chart --version 0.1.0
```

⭐ An OCI registry means your charts live right next to your images — same auth, same place.
GHCR, ECR, ACR and Docker Hub all support it.

### Hooks — run things around the lifecycle

```yaml
metadata:
  annotations:
    "helm.sh/hook": pre-upgrade          # pre/post-install, pre/post-upgrade, pre/post-delete
    "helm.sh/hook-weight": "-5"          # lower runs first
    "helm.sh/hook-delete-policy": hook-succeeded
```

The classic use is a **database migration Job** that must finish before the new Pods start.

### Chart tests

```bash
helm test my-release     # runs templates/tests/* (Pods annotated helm.sh/hook: test)
```

The `helm create` scaffold ships `tests/test-connection.yaml`, which curls the Service — a free
smoke test after every deploy.

---

## 🐞 Debugging Helm

```bash
helm lint ./chart                           # static checks
helm template my-rel ./chart                # ⭐ render locally
helm template my-rel ./chart --debug        # + error detail
helm install my-rel ./chart --dry-run --debug   # render WITH cluster validation
helm get manifest my-rel                    # exactly what is applied for a live release
helm get values my-rel --all                # values actually in effect
helm get notes my-rel
helm history my-rel
helm diff upgrade my-rel ./chart            # plugin: helm-diff — preview an upgrade ⭐
```

| Symptom | Cause | Fix |
|---|---|---|
| `error converting YAML to JSON` | broken indentation from a template | `helm template`, check `{{-` / `nindent` |
| `nil pointer evaluating interface {}` | a value referenced in a template isn't in values.yaml | add it, or use `default` / `required` |
| `cannot re-use a name that is still in use` | release already exists | `helm upgrade --install` |
| Release stuck `pending-upgrade` | a previous run was interrupted | see below |
| Upgrade "succeeded" but Pods are broken | Helm didn't wait | use `--wait --atomic` |
| `UPGRADE FAILED: ... field is immutable` | changed a Deployment's `selector` | delete and reinstall; selectors are immutable |

**Stuck in `pending-upgrade`** (a real interview scenario):

```bash
kubectl get secrets -l owner=helm,name=<release>    # one Secret per revision
kubectl delete secret sh.helm.release.v1.<release>.v<N>   # remove the stuck revision
helm rollback <release> <last-good-revision>
```

---

## 📋 Command Cheat Sheet

```bash
# repos
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update && helm repo list
helm search repo <keyword>  |  helm search hub <keyword>

# authoring
helm create <chart>
helm lint ./chart
helm template <release> ./chart [-f vals.yaml] [--set k=v]
helm package ./chart

# lifecycle
helm install  <release> ./chart [-n ns --create-namespace]
helm upgrade --install <release> ./chart -f values-prod.yaml --atomic --wait
helm list [-A]
helm status   <release>
helm history  <release>
helm rollback <release> [REVISION]
helm uninstall <release> [--keep-history]

# introspection
helm get manifest <release>
helm get values   <release> --all
helm show values  <chart>        # what knobs does this chart expose?
helm show chart   <chart>

# dependencies & tests
helm dependency update ./chart
helm test <release>
```

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Chart** | A packaged directory of templated Kubernetes manifests + defaults |
| **Release** | One installed instance of a chart; many per cluster from one chart |
| **Revision** | A numbered snapshot of a release; created by install, upgrade **and** rollback |
| **Values** | The configuration fed into templates — `values.yaml`, `-f`, `--set` |
| **`version`** | The chart's own SemVer |
| **`appVersion`** | The application's version (usually the image tag) |
| **Tiller** | Helm 2's in-cluster server; **removed in Helm 3** |
| **`_helpers.tpl`** | Partial file of `define`d named templates; not rendered as an object |
| **`include`** | Calls a named template **and returns a string** so it can be piped |
| **`nindent N`** | Newline + indent by N — for splicing blocks into YAML |
| **`required`** | Fails the render if a value is missing |
| **`--atomic`** | Auto-rollback (and `--wait`) if an upgrade doesn't become healthy |
| **Hook** | Annotation that runs a resource at a lifecycle point (e.g. pre-upgrade migration) |
| **Subchart** | A dependency chart under `charts/`, configured by nesting under its name |

---

## 🎯 Session Takeaways

1. ⭐ **Chart = recipe, Values = ingredients, Release = the meal.** One chart, many environments.
2. **Helm renders locally and applies plain YAML.** Nothing Helm-specific runs in your cluster.
3. ⭐ **`helm template` before `helm install`.** Most "Kubernetes" errors are template errors.
4. **`version` is the chart, `appVersion` is the app.** Only `version` must be SemVer.
5. ⭐ **Precedence: `values.yaml` → `-f` (left to right) → `--set`.** Prefer `-f` files in CI — they're in Git and auditable.
6. ⭐ **`helm upgrade --install` is the pipeline command** — idempotent on first and every deploy.
7. **Every change is a revision, and rollback appends a new one.** History is forward-only and auditable.
8. ⭐ **`--atomic --wait` or you ship broken releases quietly** — plain `helm upgrade` reports success as soon as the API server accepts the YAML.
9. **`--atomic` is only as trustworthy as your readiness probes.**
10. **Helm 3 dropped Tiller**, scoped releases to namespaces and stores state as Secrets. Know why: Tiller's `cluster-admin` was a security hole.
11. **Use `include … | nindent N`, never bare `template`,** and mind `{{-` whitespace control — YAML is indentation-sensitive.
12. **`helm uninstall` removes exactly what the release created** — the cleanup story hand-rolled YAML never gets right.

---

## 🔗 References

- Helm docs — https://helm.sh/docs/
- Charts — https://helm.sh/docs/topics/charts/
- Chart Template Guide — https://helm.sh/docs/chart_template_guide/
- Values files — https://helm.sh/docs/chart_template_guide/values_files/
- Named templates — https://helm.sh/docs/chart_template_guide/named_templates/
- Chart best practices — https://helm.sh/docs/chart_best_practices/
- Hooks — https://helm.sh/docs/topics/charts_hooks/
- CLI reference — https://helm.sh/docs/helm/
- Artifact Hub (find charts) — https://artifacthub.io/

---

## ➡️ Next

[Session 16 — CI/CD & GitHub Actions](./16_CICD_and_GitHub_Actions.md) — automate the
`build → test → push → helm upgrade --install` chain so a `git push` does all of it.
