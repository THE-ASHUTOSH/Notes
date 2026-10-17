# ⚡ S19 · Cloud & Terraform in Action

> *Revision card.* Full notes → [Session 19](../19_Cloud_and_Terraform_in_Action.md)

---

## 🔑 One-line core

***A subnet is "public" only because its route table sends `0.0.0.0/0` to an Internet
Gateway.*** There is no public checkbox.
**Route table = WHERE · Security group = ALLOWED.**

---

## ☁️ IaaS / PaaS / SaaS

| | You manage | AWS | One line |
|---|---|---|---|
| **IaaS** | VM, OS, app | EC2, EBS, VPC | *"give me a server"* |
| **PaaS** | your code | Elastic Beanstalk | *"here's my app"* |
| **SaaS** | your data | Gmail, Slack | *"I just want email"* |

🏠 **Rental analogy:** empty house · furnished flat · hotel room.
💡 Also: **CaaS** (Fargate, Cloud Run) and **FaaS** (Lambda).

---

## 🌍 Region vs AZ

```
Region (ap-south-1 = Mumbai)   ← a CITY
 ├── AZ ap-south-1a            ← separate CAMPUSES
 ├── AZ ap-south-1b              own power, cooling, networking
 └── AZ ap-south-1c
```

| Resource | Scope |
|---|---|
| **VPC** | ⭐ **regional** — spans every AZ |
| **Subnet** | ⭐ **exactly one AZ** |
| IGW, route table, security group | regional (VPC-wide) |
| EC2, EBS | zonal |

> ⭐ **That's why multi-AZ means multiple subnets** — you cannot stretch one across AZs.

---

## 🏘️ VPC & subnets

```
VPC  10.0.0.0/16
 ├── Public  10.0.1.0/24   (AZ-a)   ← route 0.0.0.0/0 → IGW
 └── Private 10.0.2.0/24   (AZ-b)   ← no IGW route
```

> ⚠️ **AWS reserves 5 IPs per subnet** → a `/24` gives **251** usable, not 254.
> ⚠️ **A VPC's CIDR is immutable** — changing it is a `-/+` replace of the whole network.
> Use RFC 1918 ranges and size generously.

---

## 🛣️ Route table

| Destination | Target |
|---|---|
| `10.0.0.0/16` | **local** (always there) |
| `0.0.0.0/0` | `igw-xxxx` ← **this is what makes it public** |

Routing is **longest-prefix match** — `local` always beats the catch-all.

```hcl
resource "aws_internet_gateway" "main" { vpc_id = aws_vpc.main.id }

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route { cidr_block = "0.0.0.0/0", gateway_id = aws_internet_gateway.main.id }
}

resource "aws_route_table_association" "public" {   # ⭐ THE FORGOTTEN ONE
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
```

> ⚠️ **Creating an IGW makes nothing public.** You need **IGW + route + association +
> a public IP.** Four things.
> Without the association the subnet falls back to the VPC's *main* route table — which has
> no internet route.

---

## 🔥 Security groups

```hcl
ingress { from_port = 80, to_port = 80, protocol = "tcp", cidr_blocks = ["0.0.0.0/0"] }
egress  { from_port = 0,  to_port = 0,  protocol = "-1",  cidr_blocks = ["0.0.0.0/0"] }
```

| | |
|---|---|
| **Stateful** ⭐ | allow inbound → **the reply goes out automatically** |
| **Allow-only** | no deny rules; anything not allowed is denied |
| Defaults | inbound **deny all**, outbound **allow all** |
| ⭐ **Source can be another SG** | `security_groups = [aws_security_group.app.id]` — survives IP churn |

> ⚠️ **Never `cidr_blocks = ["0.0.0.0/0"]` on port 22.** Use a trusted CIDR, a bastion, or
> SSM Session Manager.

---

## ⚖️ Security group vs NACL

| | **Security Group** | **NACL** |
|---|---|---|
| Attaches to | the resource (ENI) | the **subnet** |
| Rules | allow only | allow **and deny** |
| State | ⭐ **stateful** | ⭐ **stateless** — must allow return traffic too |
| Order | all rules together | numbered, **first match wins** |

> ⚠️ Stateless is the gotcha: with a NACL you must also allow **ephemeral ports
> 1024–65535** inbound, or replies to your own requests get dropped.

---

## 🚪 IGW vs NAT

| **Internet Gateway** | **NAT Gateway** |
|---|---|
| **two-way** | ⭐ **outbound only** |
| free | 💰 **hourly + per-GB, per AZ** |
| public subnets | lives in a public subnet, serves private ones |

> ⭐ That asymmetry is the design: your database can reach the internet; the internet
> cannot reach your database.
> 💰 **NAT Gateways are a top surprise AWS cost.** A free **S3 VPC Gateway Endpoint**
> removes a big share of that traffic.

---

## 🧪 The lab (6 resources, no EC2 = no charges)

```bash
terraform init && terraform fmt && terraform validate
terraform plan        # Plan: 6 to add
terraform apply       # vpc · subnet · igw · route table · association · sg
terraform plan -destroy && terraform destroy     # ⭐ always
```

💡 `enable_dns_hostnames = true` — off by default on a hand-made VPC, and the cause of
many *"why won't anything resolve?"* hours.

💡 `availability_zone = "${var.aws_region}a"` is fragile — prefer:
```hcl
data "aws_availability_zones" "available" { state = "available" }
# availability_zone = data.aws_availability_zones.available.names[0]
```

---

## 🗺️ AWS ⇄ Azure ⇄ GCP

| | AWS | Azure | GCP |
|---|---|---|---|
| Network | **VPC** (regional) | VNet | **VPC** (⭐ global!) |
| Firewall | Security Group | NSG | Firewall rules |
| VM | EC2 | VM | Compute Engine |
| Objects | S3 | Blob | Cloud Storage |
| K8s | EKS | AKS | GKE |

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| What makes a subnet public? | a route `0.0.0.0/0 → IGW` **+ the association** |
| Usable IPs in a `/24`? | **251** (AWS reserves 5) |
| SG vs route table? | **allowed?** vs **where?** |
| SG stateful? | **yes** — NACLs are not |
| Private subnet needs updates? | **NAT Gateway** (💰) |
| Change a VPC CIDR? | ⚠️ you can't — it's a replace |

---

⬅️ [S18](./18_Terraform_and_IaC.md) · ➡️ [S20 · Monitoring & GitOps](./20_Monitoring_Observability_GitOps.md)
