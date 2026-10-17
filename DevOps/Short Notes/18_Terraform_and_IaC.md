# ⚡ S18 · Terraform & Infrastructure as Code

> *Revision card.* Full notes → [Session 18](../18_Terraform_and_IaC.md)

---

## 🔑 One-line core

***Every plan compares three things: configuration + state + reality.***
Nearly every confusing Terraform moment is one of them out of sync.

---

## 🔄 The workflow

```
.tf files → init → fmt → validate → plan → apply → [state] → destroy
```

| Command | Does |
|---|---|
| `terraform init` | download providers, set up backend, write lock file — **safe to re-run** |
| `terraform fmt` | canonical formatting (`-check` in CI) |
| `terraform validate` | syntax + consistency, **no cloud calls** |
| `terraform plan` | ⭐ preview — changes nothing |
| `terraform apply` | make it so |
| `terraform destroy` | ⚠️ deletes **everything in state** |

---

## 🔣 Plan symbols — read this line

| | |
|---|---|
| `+` | create |
| `~` | update in place |
| `-` | destroy |
| **`-/+`** | ⭐ **REPLACE — destroy then create. On a DB that is data loss.** |
| `<=` | read (data source) |

```
Plan: 1 to add, 0 to change, 0 to destroy.    ← the most important line Terraform prints
```

---

## 🧱 Blocks

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }   # ⭐ ~> 6.0 = >=6.0, <7.0
  }
  backend "s3" { … }
}

provider "aws" { region = var.aws_region }

resource "aws_s3_bucket" "demo" {        # type . local_name
  bucket_prefix = "demo-"
  tags = { ManagedBy = "Terraform" }
}

variable "env"  { type = string, default = "dev" }   # no default = REQUIRED
output   "id"   { value = aws_s3_bucket.demo.id }    # ⚠️ NO `type` argument!
locals   { name = "${var.project}-${var.env}" }
data "aws_ami" "ubuntu" { most_recent = true }
module "vpc" { source = "terraform-aws-modules/vpc/aws", version = "5.8.1" }
```

> ⚠️ **`output` blocks take `value`, `description`, `sensitive` — never `type`.**
> `terraform validate` catches it: *"An argument named `type` is not expected here."*

---

## 🎚️ Variable precedence — lowest → highest

```
default → terraform.tfvars / *.auto.tfvars → TF_VAR_x → -var-file → -var
```

```hcl
variable "env" {
  type = string
  validation {
    condition     = contains(["dev","staging","prod"], var.env)
    error_message = "must be dev, staging or prod."
  }
}
variable "db_password" { type = string, sensitive = true }
```

> ⚠️ **`sensitive = true` hides it from *output*, NOT from state.**

---

## 🗄️ State — the heart of it

**State maps resource addresses → real infrastructure IDs.** Without it, Terraform has no
idea `aws_s3_bucket.demo` is the bucket it made.

```bash
terraform state list
terraform state show <addr>
terraform state mv  <src> <dst>      # rename without destroying
terraform state rm  <addr>           # stop managing (resource survives)
terraform import <addr> <real-id>    # ⭐ adopt existing infra
```

> ⚠️⚠️ **State is plaintext and contains secrets.** Never commit it, **never hand-edit it**.

---

## ☁️ Remote backend + locking

```hcl
backend "s3" {
  bucket = "my-tfstate"
  key    = "prod/terraform.tfstate"
  region = "ap-south-1"
  encrypt      = true
  use_lockfile = true        # or dynamodb_table = "tf-locks"
}
```

> ⭐ **Locking is the point.** Without it, two simultaneous applies produce a state that
> matches neither.

---

## 🚫 .gitignore

```gitignore
.terraform/
*.tfstate
*.tfstate.*
terraform.tfvars
*.tfplan
```

> ⭐ **But DO commit `.terraform.lock.hcl`** — it pins provider versions + checksums.
> It's the `package-lock.json` of Terraform.

---

## 🧩 Meta-arguments

```hcl
count      = 3                         # → addr[0..2]
for_each   = toset(["dev","prod"])     # ⭐ → addr["dev"]
depends_on = [aws_iam_role.app]
lifecycle {
  prevent_destroy       = true         # ⭐ protect prod
  create_before_destroy = true
  ignore_changes        = [tags["LastModified"]]
}
```

> ⭐ **Prefer `for_each` over `count`.** With `count`, deleting the middle item renumbers
> everything after it — Terraform destroys and recreates resources that didn't change.

---

## 🔐 Credentials

```bash
aws configure
aws sts get-caller-identity      # ⭐ WHICH ACCOUNT am I about to change?
```

```hcl
provider "aws" { access_key = "…" }   # ❌ NEVER — this ends up in Git
```

Use env vars, instance roles, or **OIDC** in CI.

---

## 🏭 CI/CD pattern

```bash
terraform fmt -check
terraform init
terraform validate
terraform plan -out=tfplan      # ⭐ review THIS
terraform apply tfplan          # ⭐ apply exactly what was reviewed
```

> ⚠️ Plain `terraform apply` **re-plans** at apply time — it may differ from what a human
> approved.

---

## ⚠️ Traps

| Trap | Reality |
|---|---|
| `destroy` only removes what I'm thinking of | ⚠️ **everything in state** — `plan -destroy` first |
| `sensitive` protects the value | ⚠️ not in state |
| Unpinned provider | ⚠️ a major release rewrites your plan |
| Manual console change | ⚠️ becomes **drift**; next plan undoes it |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| What does a plan compare? | config + **state** + reality |
| `-/+` means? | destroy **and** recreate |
| Lost the state file? | you've lost management of the infra — use remote state |
| Adopt an existing resource? | `terraform import` |
| `count` vs `for_each`? | ⭐ `for_each`, keyed and stable |
| Commit the lock file? | **yes** |

---

⬅️ [S17](./17_Complete_CICD_and_DevSecOps.md) · ➡️ [S19 · Cloud & VPC](./19_Cloud_and_Terraform_in_Action.md)
