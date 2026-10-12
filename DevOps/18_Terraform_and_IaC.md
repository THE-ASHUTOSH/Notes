# Session 18 — Terraform & Infrastructure as Code 🏗️

> **Topics:** What is IaC? · Terraform Architecture · Providers · Resources · Variables ·
> Outputs · `init` · `plan` · `apply` · `destroy` · Terraform State
>
> 📁 Repo: `session18-terraform-iac/` — nine numbered folders, each a runnable AWS S3 example,
> plus `terraform-s3-demo/` showing the conventional multi-file layout.

Sessions 16–17 automated *deploying to* infrastructure. This session is about **creating the
infrastructure itself in code** — so that "the staging environment" is a reviewable file in
Git, not a sequence of clicks nobody wrote down.

---

## 📑 Table of Contents

1. [What is Infrastructure as Code?](#-what-is-infrastructure-as-code)
2. [Terraform Architecture](#-terraform-architecture)
3. [HCL Basics & File Layout](#-hcl-basics--file-layout)
4. [Providers](#-providers)
5. [Resources](#-resources)
6. [Variables](#-variables)
7. [Outputs](#-outputs)
8. [The Core Workflow: init → fmt → validate → plan → apply](#-the-core-workflow-init--fmt--validate--plan--apply)
9. [Destroy](#-destroy)
10. [Terraform State](#-terraform-state)
11. [Remote State & Locking](#-remote-state--locking)
12. [The multi-file demo project](#-the-multi-file-demo-project)
13. [Beyond the lab: modules, meta-arguments, data sources, CI](#-beyond-the-lab-modules-meta-arguments-data-sources-ci)
14. [Command Cheat Sheet](#-command-cheat-sheet)
15. [Key Terms Recap](#-key-terms-recap)
16. [Session Takeaways](#-session-takeaways)

---

## 🎯 What is Infrastructure as Code?

```
Traditional (ClickOps)            IaC
──────────────────────            ───
Open AWS Console                  Write Terraform code
   ↓                                 ↓
Click S3                          terraform plan
   ↓                                 ↓
Create bucket                     terraform apply
   ↓                                 ↓
Add configuration                 AWS infrastructure
   ↓
Repeat manually… for every env
```

| Benefit | What it actually buys you |
|---|---|
| **Repeatability** | dev / staging / prod from one definition — no drift |
| **Version control** | `git log` on your infrastructure; `git blame` on an outage |
| **Review** | infrastructure changes go through PRs like code ([Session 5](./05_Git_and_GitHub.md)) |
| **Consistency** | no "someone ticked a box in the console once" |
| **Disaster recovery** | rebuild a region from a repo |
| **CI/CD integration** | `terraform plan` as a pipeline gate |
| **Documentation** | ⭐ the code *is* the current, accurate diagram |

Three questions the lab asks, worth answering properly:

1. *What if 10 engineers manually create the same infrastructure?* You get 10 subtly different
   environments, and the bug only reproduces on one of them.
2. *How does Git help?* History, review, rollback, blame, and a single source of truth.
3. *What if you need the same infrastructure elsewhere?* Change one variable instead of
   repeating a 40-click runbook.

⭐ **Terraform is declarative.** You describe **what you want to exist**, not the API calls to
get there — the same mental model as a Kubernetes manifest
([Session 9](./09_Kubernetes_Fundamentals.md)). Terraform diffs desired state against reality
and works out the calls itself.

---

## 🧭 Terraform Architecture

```
          Terraform Configuration (.tf, HCL)
                         │
                         ▼
                ┌──────────────────┐
                │  Terraform CLI   │  ← builds a dependency graph, plans, applies
                └────────┬─────────┘
                         │
                 Provider Plugin
                         ▼
                ┌──────────────────┐
                │   AWS Provider   │  ← translates to AWS API calls
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │       AWS        │
                │  S3 / EC2 / VPC  │
                └──────────────────┘

          Terraform State  ──▶  terraform.tfstate
```

Five components:

| Component | Role |
|---|---|
| **Configuration** | `.tf` files written in **HCL** — the desired state |
| **CLI** | `init` / `plan` / `apply` / `destroy` |
| **Provider** | Plugin that speaks to an external API (AWS, Azure, GCP, Kubernetes, GitHub, Helm, Cloudflare…) |
| **Resource** | One piece of infrastructure Terraform manages |
| **State** | ⭐ Terraform's record of what it created and what it maps to |

```
Configuration  +  State  +  Real World
                   │
                   ▼
             Terraform Plan
```

⭐ **Memorise that triangle.** Every `plan` compares three things: what you *wrote*, what
Terraform *remembers*, and what *actually exists*. Nearly every confusing Terraform moment is
one of those three being out of sync with the others.

---

## 📄 HCL Basics & File Layout

Terraform reads **every `.tf` file in the directory** and concatenates them — file names are
convention, not syntax. The conventional split:

```text
terraform.tf     # terraform {} block: required_version, required_providers, backend
providers.tf     # provider {} configuration
variables.tf     # variable {} declarations
terraform.tfvars # variable VALUES  ← ⚠️ gitignored
main.tf          # the resources
outputs.tf       # output {} blocks
.gitignore
```

The `terraform` block itself:

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

| Operator | Means |
|---|---|
| `>= 1.6.0` | this version or newer |
| `~> 6.0` | ⭐ `>= 6.0, < 7.0` — allow minor/patch, block breaking majors |
| `= 6.2.1` | exactly this |

⭐ **Always constrain the provider version.** Without it, a provider major release lands on
your next `init` and your plan suddenly wants to replace production.

---

## 🔌 Providers

A provider is a plugin that lets Terraform talk to an external API.

```hcl
provider "aws" {
  region = "ap-south-1"
}
```

```text
aws
├── namespace:          hashicorp
├── type:               aws
└── version constraint: ~> 6.0
```

The full address is `registry.terraform.io/hashicorp/aws`. There are thousands — AWS, Azure,
Google Cloud, **Kubernetes**, **Helm**, GitHub, Datadog, Cloudflare.

### Authentication — never in the config

```bash
aws configure                    # writes ~/.aws/credentials
aws sts get-caller-identity      # ⭐ verify WHO you are before you apply
```

```hcl
provider "aws" {
  access_key = "..."     # ❌ NEVER — this ends up in Git
  secret_key = "..."
}
```

Credential sources Terraform picks up automatically, in order: environment variables
(`AWS_ACCESS_KEY_ID`…), shared credentials file, IAM instance/role profile, **OIDC in CI**
([Session 16](./16_CICD_and_GitHub_Actions.md)).

⭐ `aws sts get-caller-identity` before every real apply. "I thought I was on the dev account"
is a genuinely expensive mistake.

### Expected `init` output

```text
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 6.0"...
- Installing hashicorp/aws v6.x.x...

Terraform has been successfully initialized!
```

---

## 🧱 Resources

```hcl
resource "RESOURCE_TYPE" "LOCAL_NAME" {
  argument = value
}
```

```hcl
resource "aws_s3_bucket" "demo" {
  bucket_prefix = "session18-resource-"

  tags = {
    Name        = "Session 18 Resource Demo"
    Environment = "dev"
  }
}
```

| Part | Meaning |
|---|---|
| `resource` | the block type |
| `aws_s3_bucket` | **resource type** — the provider prefix (`aws_`) picks the provider |
| `demo` | **local name** — Terraform-internal only, never appears in AWS |
| `bucket_prefix` | an argument |

The **resource address** is `aws_s3_bucket.demo`, and that's what you see in
`terraform state list` and reference elsewhere:

```hcl
value = aws_s3_bucket.demo.arn        # referencing creates an implicit dependency ⭐
```

⭐ **References build the dependency graph.** Write `aws_s3_bucket.demo.id` inside another
resource and Terraform *knows* to create the bucket first — no ordering to declare. Use
`depends_on` only for dependencies Terraform can't see.

> 💡 `bucket_prefix` instead of `bucket` lets AWS append a random suffix. S3 bucket names are
> **globally unique across all AWS accounts**, so a fixed name in a classroom guarantees a
> collision.

### Tag everything

```hcl
tags = {
  Project     = "terraform-training"
  Environment = "dev"
  Owner       = "student"
  ManagedBy   = "Terraform"       # ⭐ tells the next person not to click it
}
```

---

## 🎚️ Variables

```hcl
bucket_prefix = "student-project-dev-"                        # ❌ hardcoded

bucket_prefix = "${var.project_name}-${var.environment}-"     # ✅ reusable
```

```hcl
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
```

Referenced as `var.environment`. Types: `string`, `number`, `bool`, `list(...)`, `map(...)`,
`set(...)`, `object({...})`, `any`.

A variable **with no `default` is required** — Terraform will prompt, or fail in CI. That's
how you force a value to be supplied for production.

### Where values come from — ⭐ precedence, lowest to highest

```
default in the variable block
  → terraform.tfvars  /  *.auto.tfvars
    → TF_VAR_<name> environment variable
      → -var-file=<file>
        → -var 'name=value'          ← highest
```

```bash
cp terraform.tfvars.example terraform.tfvars
terraform plan -var-file=prod.tfvars
terraform plan -var 'environment=test'
export TF_VAR_environment=test        # handy in CI
```

```hcl
# terraform.tfvars
aws_region   = "ap-south-1"
environment  = "dev"
project_name = "student-project"
```

### Validation & sensitivity

```hcl
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod."
  }
}

variable "db_password" {
  type      = string
  sensitive = true       # ⭐ redacted from plan/apply output (NOT from state)
}
```

### ⚠️ Never commit `terraform.tfvars`

```gitignore
.terraform/
*.tfstate
*.tfstate.*
terraform.tfvars
*.tfplan
.terraform.lock.hcl    # ← actually, DO commit this one (see below)
```

Commit `terraform.tfvars.example` with placeholder values instead — the same pattern as
`.env.example`.

> ⭐ Correction to the common `.gitignore`: **`.terraform.lock.hcl` should be committed.**
> It pins exact provider versions and checksums, so everyone and every CI run installs
> identical providers. It's the `package-lock.json` of Terraform.

---

## 📤 Outputs

```hcl
output "bucket_id" {
  description = "The S3 bucket ID"
  value       = aws_s3_bucket.demo.id
}

output "bucket_arn" {
  value = aws_s3_bucket.demo.arn
}
```

```bash
terraform output                 # all outputs
terraform output bucket_id       # one
terraform output -json           # ⭐ machine-readable, for pipelines
terraform output -raw bucket_id  # no quotes — for shell substitution
```

```text
Outputs:

bucket_arn    = "arn:aws:s3:::session18-output-xxxxxxxx"
bucket_id     = "session18-output-xxxxxxxx"
bucket_region = "ap-south-1"
```

Outputs matter for: passing values **between modules**, surfacing IDs, and feeding CI/CD
(`terraform output -raw cluster_name` → `aws eks update-kubeconfig`).

> 🐛 **Bug in the repo's `terraform-s3-demo/outputs.tf`:** every output block declares
> `type = string`. **`output` blocks do not accept a `type` argument** — only `value`,
> `description`, `sensitive`, `depends_on` and `precondition`. `terraform validate` fails with
> *"An argument named `type` is not expected here."* Delete those three lines.
> (`type` belongs in `variable` blocks — easy confusion, and `terraform validate` catches it,
> which is a neat demonstration of why validate exists.)

> 🐛 Second issue in the same demo: `output "bucket_region"` reads
> `aws_s3_bucket.devops553.region`, and `variables.tf` hard-codes `bucket_name = "yatri1107"`.
> A fixed S3 bucket name is globally unique — expect `BucketAlreadyExists`. Use
> `bucket_prefix`, as the numbered folders correctly do.

---

## 🔄 The Core Workflow: init → fmt → validate → plan → apply

```
     .tf files
         │
   terraform init        install providers, set up backend, write lock file
         │
   terraform fmt         canonical formatting
         │
   terraform validate    syntax + internal consistency (no cloud calls)
         │
   terraform plan        ⭐ compare config + state + reality → preview
         │
   terraform apply       make it so
         │
     real infrastructure
```

### 1. `init`

```bash
terraform init
```

Prepares the working directory: downloads providers into `.terraform/`, configures the backend,
writes `.terraform.lock.hcl`. **Safe to run repeatedly.** Run it again whenever you change
providers, modules or the backend.

### 2. `fmt`

```bash
terraform fmt           # rewrites files, prints names it changed
terraform fmt -check    # ⭐ CI-friendly: fails instead of rewriting
terraform fmt -recursive
```

### 3. `validate`

```bash
terraform validate
# Success! The configuration is valid.
```

Checks syntax and internal consistency **without contacting AWS** — fast, free, and perfect as
the first CI step.

### 4. `plan` ⭐

```bash
terraform plan
terraform plan -out=tfplan      # save it
```

```text
Plan: 1 to add, 0 to change, 0 to destroy.
```

| Symbol | Action |
|---|---|
| `+` | create |
| `~` | update in place |
| `-` | destroy |
| `-/+` | ⭐ **replace** — destroy then create. Read this line carefully. |
| `<=` | read (data source) |

⭐ **`-/+` on a database or a volume means data loss.** The `plan` output is not a formality;
it's the last moment you can stop it. The "`N to add, N to change, N to destroy`" summary line
is the single most important line Terraform prints.

### 5. `apply`

```bash
terraform apply
```

```text
Do you want to perform these actions?
  Only 'yes' will be accepted to approve.

Enter a value: yes
```

```text
aws_s3_bucket.lifecycle_demo: Creating...
aws_s3_bucket.lifecycle_demo: Creation complete after 2s

Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:
bucket_name = "session18-lifecycle-xxxxxxxx"
```

### ⭐ Saved plans — the CI/CD pattern

```bash
terraform plan -out=tfplan      # on the PR: review this
terraform apply tfplan          # on merge: apply EXACTLY what was reviewed
```

Plain `terraform apply` generates a *fresh* plan at apply time — which may differ from the one
a human approved. A saved plan closes that gap. (`-auto-approve` is for applying a saved plan
in CI, never for an interactive production apply.)

---

## 💣 Destroy

```bash
terraform state list       # what will go?
terraform plan -destroy    # ⭐ ALWAYS preview first
terraform destroy
```

```text
Plan: 0 to add, 0 to change, 1 to destroy.

Do you really want to destroy all resources?
  Only 'yes' will be accepted to confirm.

Enter a value: yes

Destroy complete! Resources: 1 destroyed.
```

> ⚠️ **`destroy` deletes real infrastructure.** It removes *everything in the state file*, not
> just what you were thinking about. Protections worth knowing:

```hcl
resource "aws_s3_bucket" "important" {
  lifecycle {
    prevent_destroy = true      # ⭐ terraform errors instead of deleting
  }
}
```

```bash
terraform destroy -target=aws_s3_bucket.demo    # scope it down (use sparingly)
```

Answers to the lab's questions:
1. *`plan` vs `apply`?* `plan` previews and changes nothing; `apply` executes.
2. *What does `destroy` do?* Deletes every resource in the state.
3. *Why `plan -destroy` first?* Because `destroy` is irreversible, and state can contain more
   than you remember putting there.

---

## 🗄️ Terraform State

```
main.tf  ──desired──▶  Terraform  ──┬──▶  terraform.tfstate   (what I created)
                                    └──▶  AWS infrastructure  (what exists)
```

State maps **Terraform resource addresses → real infrastructure IDs**. Without it, Terraform
has no idea that `aws_s3_bucket.demo` is the bucket `session18-state-7a3f`, and would try to
create a second one.

```bash
terraform state list                            # addresses under management
terraform state show aws_s3_bucket.state_demo   # one resource's attributes
terraform show                                  # everything
terraform state pull                            # raw JSON
```

```text
resource "aws_s3_bucket" "state_demo" {
    arn    = "arn:aws:s3:::session18-state-xxxxxxxx"
    bucket = "session18-state-xxxxxxxx"
    id     = "session18-state-xxxxxxxx"
}
```

### ⚠️ Two rules about state

**1. Never commit it.**

```gitignore
.terraform/
terraform.tfstate
terraform.tfstate.*
*.tfplan
```

⭐ **State is plaintext and contains secrets** — RDS passwords, private keys, anything marked
`sensitive`. `sensitive = true` hides it from *console output*, not from the state file.

**2. Never hand-edit it.** Opening `terraform.tfstate` and changing values is how you get a
state that disagrees with reality in a way no command can fix. Use the real commands:

```bash
terraform state mv <old> <new>    # rename/move without destroying
terraform state rm <address>      # stop managing (resource survives in AWS)
terraform import <address> <id>   # ⭐ adopt existing infrastructure into state
terraform refresh                 # (legacy; plan/apply refresh automatically now)
```

`terraform import` is the migration path out of ClickOps: point Terraform at resources that
already exist and bring them under management without recreating them.

### Drift

If someone changes a resource in the console, the next `plan` shows the difference and
proposes to change it back. ⭐ **That's the feature, not a bug** — Terraform converges reality
onto the code. It's also why "quick manual fix in the console" always costs more later.

---

## ☁️ Remote State & Locking

Local `terraform.tfstate` is fine for one person on a laptop. It breaks the instant there's a
team:

- it's on **one machine** — nobody else can plan
- **no locking** — two simultaneous applies corrupt it
- lose the laptop, lose the state (and the ability to manage the infrastructure)

```hcl
terraform {
  backend "s3" {
    bucket       = "my-tfstate-bucket"
    key          = "prod/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true          # S3-native locking (modern Terraform)
    # dynamodb_table = "tf-locks"   # the older DynamoDB locking approach
  }
}
```

| Backend | Used with |
|---|---|
| `s3` | AWS (+ DynamoDB or S3-native locking) |
| `azurerm` | Azure Blob Storage |
| `gcs` | Google Cloud Storage |
| `remote` / `cloud` | HCP Terraform (Terraform Cloud) |

⭐ **Locking is the point.** With a lock, a second `apply` waits instead of racing. Without
one, two engineers applying at once produce a state file that matches neither of them.

Separate state per environment — a separate `key` per env, or **workspaces**:

```bash
terraform workspace new staging
terraform workspace select prod
terraform workspace list
```

> ⚠️ Workspaces share one configuration and backend. For genuinely different environments,
> most teams prefer **separate directories + separate state keys**, because prod usually needs
> different settings, not just different values.

---

## 🗂️ The multi-file demo project

`terraform-s3-demo/` shows the idiomatic split:

```text
terraform-s3-demo/
├── terraform.tf     → terraform {} block (version + providers)
├── providers.tf     → provider "aws" { region = var.aws_region }
├── variables.tf     → variable declarations
├── terraform.tfvars → values  (gitignored)
├── main.tf          → resources
├── outputs.tf       → outputs
└── .gitignore
```

```hcl
# terraform.tf
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

# providers.tf
provider "aws" { region = var.aws_region }

# variables.tf
variable "aws_region" {
  type        = string
  description = "AWS region where the S3 bucket will be created."
  default     = "ap-south-1"
}
variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket."
}

# main.tf
resource "aws_s3_bucket" "devops553" {
  bucket        = var.bucket_name
  force_destroy = true          # ⚠️ allows destroy even with objects inside
  tags = {
    Name        = var.bucket_name
    Environment = "dev"
    ManagedBy   = "Terraform"
    Project     = "Session18"
  }
}

# outputs.tf  (with the invalid `type =` lines removed)
output "bucket_name" {
  description = "Name of the S3 bucket."
  value       = aws_s3_bucket.devops553.bucket
}
output "bucket_arn" {
  description = "ARN of the S3 bucket."
  value       = aws_s3_bucket.devops553.arn
}
```

### Full run

```bash
aws sts get-caller-identity     # ⭐ which account am I about to change?
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply                 # yes
terraform output
terraform state list
terraform state show aws_s3_bucket.devops553
aws s3 ls                       # verify out-of-band
terraform plan -destroy
terraform destroy               # yes
```

> ⚠️ `force_destroy = true` lets Terraform delete a bucket **with objects still in it**.
> Convenient in a lab, dangerous in production.

---

## 🔭 Beyond the lab: modules, meta-arguments, data sources, CI

### Modules — the reusable unit

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"

  name = "prod-vpc"
  cidr = "10.0.0.0/16"
  azs             = ["ap-south-1a", "ap-south-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
}
```

⭐ A module is to Terraform what a **chart is to Helm** ([Session 15](./15_Helm.md)) and a
function is to a program: inputs (variables), a body (resources), outputs. Every directory of
`.tf` files is already a module — the one you run is the *root module*.

### Meta-arguments

```hcl
count      = 3                        # create N copies → aws_instance.web[0..2]
for_each   = toset(["dev","prod"])    # ⭐ create one per key → ...["dev"]
depends_on = [aws_iam_role.app]       # explicit ordering
provider   = aws.us_east              # a non-default provider alias
lifecycle {
  create_before_destroy = true
  prevent_destroy       = true
  ignore_changes        = [tags["LastModified"]]
}
```

⭐ **Prefer `for_each` over `count`.** With `count`, removing the middle item renumbers
everything after it and Terraform destroys and recreates resources that didn't change.
`for_each` keys by a stable string, so removing one touches only that one.

### Data sources — read what you didn't create

```hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "web" {
  ami = data.aws_ami.ubuntu.id
}
```

### Useful HCL

```hcl
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = { Project = var.project_name, ManagedBy = "Terraform" }
}

name  = local.name_prefix
tags  = merge(local.common_tags, { Name = "web" })
count = var.environment == "prod" ? 3 : 1          # ternary
cidr  = cidrsubnet("10.0.0.0/16", 8, 1)            # → 10.0.1.0/24  (Session 4!)
```

### Terraform in CI/CD

```yaml
- uses: hashicorp/setup-terraform@v3
- run: terraform fmt -check
- run: terraform init
- run: terraform validate
- run: terraform plan -out=tfplan -no-color
# on PR: post the plan as a comment, require review
# on merge to main:
- run: terraform apply -auto-approve tfplan
```

Add **`tfsec` / `checkov` / `trivy config`** to catch a public S3 bucket or an open security
group *before* it exists — IaC scanning from
[Session 17](./17_Complete_CICD_and_DevSecOps.md). Also: `terraform-docs` for auto-generated
module docs, and **OIDC** rather than stored AWS keys.

### Terraform vs the alternatives

| Tool | Scope |
|---|---|
| **Terraform** | Multi-cloud, declarative, provider ecosystem. The default. |
| **OpenTofu** | Open-source fork after the BSL licence change; drop-in compatible |
| **CloudFormation** | AWS only, no state file to manage (AWS keeps it) |
| **Pulumi** | Real programming languages instead of HCL |
| **Ansible** | ⭐ *Configuration* management (mutable), not provisioning (immutable) |

---

## 📋 Command Cheat Sheet

```bash
# lifecycle
terraform init [-upgrade] [-backend-config=...]
terraform fmt [-check] [-recursive]
terraform validate
terraform plan [-out=tfplan] [-var-file=prod.tfvars] [-destroy]
terraform apply [tfplan] [-auto-approve]
terraform destroy [-target=ADDR]

# state
terraform state list
terraform state show <addr>
terraform state mv <src> <dst>
terraform state rm <addr>
terraform import <addr> <real-id>
terraform show [-json]

# outputs & workspaces
terraform output [-json] [-raw] [NAME]
terraform workspace list|new|select <name>

# misc
terraform providers
terraform graph | dot -Tpng > graph.png
terraform console          # interactive expression evaluation
terraform force-unlock <LOCK_ID>   # only when a lock is genuinely orphaned
```

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **IaC** | Defining infrastructure in version-controlled code |
| **HCL** | HashiCorp Configuration Language — Terraform's declarative syntax |
| **Provider** | Plugin that translates Terraform into an external API's calls |
| **Resource** | One managed piece of infrastructure; address `type.local_name` |
| **Data source** | Read-only lookup of something Terraform doesn't manage |
| **Variable** | Input; `var.name`. No default ⇒ required |
| **Output** | Exported value; ⚠️ **no `type` argument** |
| **Local** | A named expression inside the configuration (`local.x`) |
| **Module** | A reusable directory of `.tf` files with inputs and outputs |
| **State** | Terraform's map of addresses → real resources. Plaintext, secret-bearing |
| **Backend** | Where state lives — `local`, `s3`, `azurerm`, `gcs`, `cloud` |
| **Locking** | Prevents concurrent applies corrupting shared state |
| **Drift** | Reality diverging from state (someone clicked in the console) |
| **`plan`** | Preview; compares config + state + reality. Changes nothing |
| **`-/+`** | ⭐ Replace — destroy then create. Potential data loss |
| **`terraform import`** | Bring existing infrastructure under management |
| **`.terraform.lock.hcl`** | Provider version/checksum lock — **commit this** |
| **Workspace** | Multiple states from one configuration |

---

## 🎯 Session Takeaways

1. ⭐ **Terraform is declarative:** describe the desired state, let it compute the API calls — same model as Kubernetes manifests.
2. ⭐ **Every plan compares three things: configuration, state, and reality.** Almost every confusing moment is one of them being out of sync.
3. **The workflow is `init → fmt → validate → plan → apply`,** and `init` is safe to re-run any time.
4. ⭐ **Read the plan summary line.** `-/+` means destroy-and-recreate; on a database that's data loss.
5. **`plan -out=tfplan` then `apply tfplan`** so you apply exactly what was reviewed — plain `apply` re-plans.
6. ⭐ **State is the heart of Terraform, it is plaintext, and it holds secrets.** Never commit it, never hand-edit it.
7. **`sensitive = true` hides a value from output, not from state.**
8. **Local state doesn't survive a team.** Move to a remote backend with **locking** on day one.
9. **Commit `.terraform.lock.hcl`; gitignore `.terraform/`, `*.tfstate*`, `*.tfvars`, `*.tfplan`.**
10. ⭐ **Never put credentials in `.tf` files.** Use `aws configure`, env vars, instance roles or OIDC — and run `aws sts get-caller-identity` before you apply.
11. **Pin provider versions with `~> 6.0`**, or a major release will rewrite your plan for you.
12. **Always `terraform plan -destroy` first.** `destroy` removes everything in the state, not just what you had in mind.
13. **Prefer `for_each` over `count`** so removing one item doesn't renumber and recreate the rest.
14. **Manual console changes become drift**, and the next `plan` will propose to undo them. That's the feature.

---

## 🔗 References

- Terraform docs — https://developer.hashicorp.com/terraform/docs
- Install Terraform — https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli
- AWS get started — https://developer.hashicorp.com/terraform/tutorials/aws-get-started/aws-create
- AWS provider registry — https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- State — https://developer.hashicorp.com/terraform/language/state
- Backends — https://developer.hashicorp.com/terraform/language/backend
- Modules — https://developer.hashicorp.com/terraform/language/modules
- Style guide — https://developer.hashicorp.com/terraform/language/style
- CLI reference — https://developer.hashicorp.com/terraform/cli/commands
- AWS CLI install — https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- OpenTofu — https://opentofu.org/

---

## ➡️ Next

[Session 19 — Cloud & Terraform in Action](./19_Cloud_and_Terraform_in_Action.md) — stop
creating S3 buckets and start building a real VPC: subnets, route tables, internet gateway and
security groups.
