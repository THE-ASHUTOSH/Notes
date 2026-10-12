# Session 19 — Cloud & Terraform in Action ☁️

> **Topics:** Cloud Fundamentals · IaaS, PaaS, SaaS · Regions & Availability Zones · VPC/VNet ·
> Subnets · Route Tables · Security Groups · Provisioning Infrastructure using Terraform
>
> 📁 Repo: `session19-cloud-terraform/` — concept folders `01`–`05`, a runnable
> `06-terraform-vpc` lab, a `07-terraform-workflow` recap and an `08-mini-project` capstone.

[Session 18](./18_Terraform_and_IaC.md) taught Terraform with one S3 bucket. This session uses
it to build a **real network**: a VPC with a public subnet, an internet gateway, a route table
and a security group — the foundation every cloud workload sits on.

⭐ Everything in the networking half is [Session 4](./04_Networking_Fundamentals.md) with AWS
names attached. CIDR, private IP ranges, ports, firewalls — same concepts, cloud vocabulary.

---

## 📑 Table of Contents

1. [Cloud Service Models: IaaS, PaaS, SaaS](#-cloud-service-models-iaas-paas-saas)
2. [Regions & Availability Zones](#-regions--availability-zones)
3. [VPC & Subnets](#-vpc--subnets)
4. [Route Tables & Internet Gateway](#-route-tables--internet-gateway)
5. [Security Groups](#-security-groups)
6. [NACLs vs Security Groups](#-nacls-vs-security-groups)
7. [The Terraform VPC Lab](#-the-terraform-vpc-lab)
8. [Workflow Recap](#-workflow-recap)
9. [Mini Project](#-mini-project)
10. [Beyond the lab: NAT, private subnets, HA, cost](#-beyond-the-lab-nat-private-subnets-ha-cost)
11. [AWS ⇄ Azure ⇄ GCP vocabulary](#-aws--azure--gcp-vocabulary)
12. [Key Terms Recap](#-key-terms-recap)
13. [Session Takeaways](#-session-takeaways)

---

## 🏢 Cloud Service Models: IaaS, PaaS, SaaS

> Cloud computing = renting computing resources instead of buying and maintaining the machines.

Providers: **AWS**, **Microsoft Azure**, **Google Cloud**.

The difference between the three models is simply **where the line of responsibility sits**:

```
            IaaS                PaaS                SaaS
          ────────            ────────            ────────
YOU  ──▶  Application         Application              ·
          Runtime                  ·                   ·
          OS                       ·                   ·
          Configuration            ·                   ·
          ───────────         ───────────         ───────────
CLOUD ─▶  Virtual Machine     Runtime             Everything
          Storage             OS
          Network             Servers
                              Infrastructure
```

| Model | You mainly manage | AWS example | In one sentence |
|---|---|---|---|
| **IaaS** | VM, OS, application | EC2, EBS, VPC | *"Give me a server. I'll install Java and Nginx."* |
| **PaaS** | Your application code | Elastic Beanstalk, App Service, App Engine | *"Here's my app. You handle the server."* |
| **SaaS** | Just your data and usage | Gmail, Google Docs, M365, Slack | *"I just want email."* |

```
IaaS → more control, more responsibility
PaaS → less infrastructure work
SaaS → just use the software
```

### The rental analogy

| | |
|---|---|
| **IaaS** | Rent an **empty house** — you furnish it |
| **PaaS** | Rent a **furnished apartment** — move in and live |
| **SaaS** | Stay in a **hotel** — you just use the room |

### Classify these

| Service | Model |
|---|---|
| EC2 | IaaS |
| Gmail | SaaS |
| Elastic Beanstalk | PaaS |
| Google Docs | SaaS |
| A virtual machine | IaaS |

> 💡 Where do **containers** fit? Kubernetes on EC2 is IaaS you operate yourself; EKS/GKE/AKS
> are managed control planes (closer to PaaS); Fargate/Cloud Run are "give me a container, I
> don't want to see a node" — often called **CaaS**, and **Lambda** is **FaaS** (serverless):
> you supply a function, the platform supplies literally everything else.

⭐ **The trade-off is always the same:** the more the cloud manages, the less control and the
less operational burden you have. There's no "best" model — only the right line for your team.

---

## 🌍 Regions & Availability Zones

```
AWS
 └── Region (ap-south-1 = Mumbai)
      ├── Availability Zone  ap-south-1a
      ├── Availability Zone  ap-south-1b
      └── Availability Zone  ap-south-1c
```

| Concept | Meaning | Analogy |
|---|---|---|
| **Region** | A geographic area where the provider runs infrastructure (`ap-south-1`, `us-east-1`, `eu-west-1`) | A **city** |
| **Availability Zone (AZ)** | An isolated location (one or more datacentres) inside a region — separate power, cooling and networking | **Separate campuses** in that city |

### Why multiple AZs

```
Application
   ├── Server A → AZ-a
   └── Server B → AZ-b        ← AZ-a fails, the app survives
```

⭐ AZs are close enough for **low-latency synchronous replication**, far enough apart that one
flood, fire or power failure doesn't take both. That is the entire basis of cloud high
availability, and it's why a single-AZ deployment isn't "highly available" no matter how many
instances it has.

### Regional vs zonal resources

| Resource | Scope |
|---|---|
| **VPC** | ⭐ Regional — spans every AZ in the region |
| **Subnet** | ⭐ **Exactly one AZ** |
| Internet Gateway, Route Table, Security Group | Regional (VPC-wide) |
| EC2 instance, EBS volume | Zonal |

**This is why multi-AZ means multiple subnets.** You can't stretch a subnet across AZs, so
high availability starts with one subnet per AZ.

```hcl
provider "aws" {
  region = "ap-south-1"
}
```

```bash
aws configure get region        # ap-south-1
aws sts get-caller-identity     # ⭐ which account?
```

How to choose a region: **latency to users**, **data residency/compliance**, **price** (it
varies measurably), and **service availability** (new services launch in `us-east-1` first).

Answers to the lab's questions: a Region is bigger than an AZ · one Region has multiple AZs ·
multiple AZs give fault isolation · a subnet belongs to **one AZ**.

---

## 🏘️ VPC & Subnets

### VPC — Virtual Private Cloud

Your own **private, isolated network** inside the provider.

```
Cloud
 └── Your VPC  (10.0.0.0/16)
      ├── your subnets
      ├── your routes
      └── your security rules
```

### Subnet — a smaller network inside the VPC

```
VPC  10.0.0.0/16
 ├── Public Subnet   10.0.1.0/24     (AZ-a)
 └── Private Subnet  10.0.2.0/24     (AZ-b)
```

### CIDR, briefly

```
10.0.0.0/16   ← big network  (65,536 addresses)
 ├── 10.0.1.0/24   (256)
 ├── 10.0.2.0/24
 └── 10.0.3.0/24
```

⭐ **VPC = bigger network, subnet = smaller network inside it.** The `/16` and `/24` are
straight from [Session 4](./04_Networking_Fundamentals.md): the number is how many bits are
the **network** part, so a bigger number means a smaller network.

> 💡 AWS reserves **5 addresses per subnet** (network address, VPC router, DNS, future use,
> broadcast). So a `/24` gives you **251** usable IPs, not 254. Also: a VPC's CIDR **cannot be
> changed** after creation (you can only add secondary blocks) — plan it with room to grow.
> Use the RFC 1918 private ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.

### ⭐ Public vs private subnet

There is **no "public" checkbox.** A subnet is public purely because:

> **its route table has a route to an Internet Gateway.**

```
Public:                     Private:
  Internet                    Internet
     │                            ✗
  Internet Gateway            Private Subnet
     │                            │
  Public Subnet                Database
     │
  Web Server
```

```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true          # instances get a public IP automatically
}
```

```bash
aws ec2 describe-vpcs    --query 'Vpcs[].{VpcId:VpcId,Cidr:CidrBlock,State:State}'
aws ec2 describe-subnets --query 'Subnets[].{SubnetId:SubnetId,Cidr:CidrBlock,AZ:AvailabilityZone}'
```

A subnet can **not** be larger than its VPC — its CIDR must fit inside the VPC's.

---

## 🛣️ Route Tables & Internet Gateway

You have a VPC and a subnet. How does traffic know where to go?

### Route table — the road map

```
Destination       Target
10.0.0.0/16       local            ← always present: traffic inside the VPC
0.0.0.0/0         igw-xxxxxxxx     ← "everything else goes to the internet"
```

Routing is **longest-prefix match**: the most specific route wins, so the `local` route always
beats the `0.0.0.0/0` catch-all for in-VPC traffic.

### Internet Gateway (IGW)

```
Internet
   │
Internet Gateway       ← horizontally scaled, redundant, VPC-wide
   │
  VPC
   │
Public Subnet
```

> ⚠️ **Creating an IGW does not make any subnet public.** The subnet's route table must also
> route `0.0.0.0/0` at it, *and* the instance needs a public IP. Three things, not one.

### The three pieces, in Terraform

```hcl
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {    # ⭐ the easily-forgotten one
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
```

⭐ **The association is what actually makes the subnet public.** Without it the subnet falls
back to the VPC's *main* route table, which has no internet route — a classic "I created
everything and it still doesn't work".

### `0.0.0.0/0`

```
0.0.0.0/0 = any IPv4 destination        (the "default route")
0.0.0.0/0 → Internet Gateway = "send internet-bound traffic to the IGW"
```

### ⭐ Route table vs security group — don't confuse them

```
Route Table     =  WHERE should traffic go?       (reachability)
Security Group  =  IS this traffic allowed?       (permission)
```

Both must say yes. A route with no allow rule is blocked; an allow rule with no route goes
nowhere.

```
Laptop → Internet → IGW → Route Table → Public Subnet → Security Group → EC2
```

---

## 🔥 Security Groups

A **virtual firewall** attached to resources (EC2 ENIs, RDS, load balancers).

> "Who is allowed to talk to my server?"

```
Inbound
  Port 22  SSH    → restrict to your IP
  Port 80  HTTP   → allow
  Port 443 HTTPS  → allow
```

```hcl
resource "aws_security_group" "web" {
  name        = "session19-web"
  description = "Allow web traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound IPv4"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"          # -1 = all protocols
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### ⭐ Security groups are **stateful**

```
Allowed inbound request ──▶ Server ──▶ response returns automatically
```

You allow inbound 443; the reply goes out without any egress rule, because the connection is
tracked. (This is where NACLs differ — see below.)

### Other properties worth knowing

- **Allow-only.** There are no deny rules. Anything not explicitly allowed is denied.
- **Default inbound is deny-all, default outbound is allow-all.**
- ⭐ **A source can be another security group**, not just a CIDR:

```hcl
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]   # ⭐ "only the app tier"
  }
```

  This is the idiomatic pattern — it keeps working as instances come and go and IPs change,
  the same way a Kubernetes Service selects by **label** rather than IP
  ([Session 11](./11_Kubernetes_Networking_and_Services.md)).

### ⚠️ The SSH warning

```hcl
cidr_blocks = ["0.0.0.0/0"]      # for port 22 — ❌
```

Valid HCL, terrible idea: SSH open to the entire internet gets credential-stuffed within
minutes. Restrict to a trusted CIDR, or skip SSH entirely with **AWS Systems Manager Session
Manager** / a bastion host.

```bash
aws ec2 describe-security-groups --query 'SecurityGroups[].{GroupId:GroupId,Name:GroupName,VpcId:VpcId}'
```

**Memory trick:** `Route Table = WHERE? · Security Group = ALLOWED?`

---

## 🧱 NACLs vs Security Groups

Not in the lab, but the comparison is a standard interview question:

| | **Security Group** | **Network ACL** |
|---|---|---|
| Attaches to | the resource (ENI) | the **subnet** |
| Rules | allow only | allow **and deny** |
| State | ⭐ **stateful** | ⭐ **stateless** — you must allow the return traffic too |
| Evaluation | all rules together | numbered, **first match wins** |
| Default | deny in, allow out | allow all both ways |

⭐ Stateless is the gotcha: with a NACL you must also permit the **ephemeral port range**
(1024–65535) inbound, or responses to your own outbound requests get dropped. Most teams use
security groups for everything and leave NACLs at their defaults.

---

## 🧪 The Terraform VPC Lab

`06-terraform-vpc` creates six resources — and deliberately **no EC2**, to avoid charges.

```
                    Internet
                        │
              ┌─────────▼────────┐
              │ Internet Gateway │
              └─────────┬────────┘
                ┌───────▼────────┐
                │      VPC       │
                │  10.0.0.0/16   │
                │  ┌──────────┐  │
                │  │  Public  │  │
                │  │  Subnet  │  │
                │  │10.0.1.0/24  │
                │  └──────────┘  │
                │   Route Table  │
                │  Security Group│
                └────────────────┘
```

```text
06-terraform-vpc/
├── versions.tf      terraform{} + provider
├── variables.tf     aws_region
├── main.tf          the six resources
├── outputs.tf       vpc_id, vpc_cidr, subnet_id, security_group_id
├── terraform.tfvars.example
└── .gitignore
```

**`main.tf`** (abridged — the shape is what matters)

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true      # ⭐ needed for private DNS names
  enable_dns_hostnames = true      # ⭐ needed for public DNS names
  tags = { Name = "session19-vpc", Session = "19", ManagedBy = "Terraform" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "main" { vpc_id = aws_vpc.main.id }

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "web" {
  name   = "session19-web-sg"
  vpc_id = aws_vpc.main.id
  ingress { description = "HTTP",  from_port = 80,  to_port = 80,  protocol = "tcp", cidr_blocks = ["0.0.0.0/0"] }
  ingress { description = "HTTPS", from_port = 443, to_port = 443, protocol = "tcp", cidr_blocks = ["0.0.0.0/0"] }
  egress  { description = "All outbound", from_port = 0, to_port = 0, protocol = "-1", cidr_blocks = ["0.0.0.0/0"] }
}
```

> 💡 **`enable_dns_hostnames` matters more than it looks.** Without it, instances get no public
> DNS name and VPC endpoints/RDS private names don't resolve. It's off by default on a
> hand-made VPC and is a frequent "why can't anything resolve?" cause.

> ⚠️ `availability_zone = "${var.aws_region}a"` works for `ap-south-1a` but assumes a suffix
> that doesn't always exist (and your account may not be able to use `a`). The robust form:
> ```hcl
> data "aws_availability_zones" "available" { state = "available" }
> # ...
> availability_zone = data.aws_availability_zones.available.names[0]
> ```

### Run it

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt
terraform validate          # Success! The configuration is valid.
terraform plan              # Plan: 6 to add, 0 to change, 0 to destroy.
terraform apply             # yes
```

```text
Apply complete! Resources: 6 added, 0 changed, 0 destroyed.

Outputs:
security_group_id = "sg-..."
subnet_id         = "subnet-..."
vpc_cidr          = "10.0.0.0/16"
vpc_id            = "vpc-..."
```

> 🐛 The README's sample output says `5 added` while the configuration defines **six**
> resources (the README itself notes "there are six resources"). Expect **6** — the
> `aws_route_table_association` is easy to miss when counting.

```bash
terraform state list
# aws_internet_gateway.main
# aws_route_table.public
# aws_route_table_association.public
# aws_security_group.web
# aws_subnet.public
# aws_vpc.main

terraform output
```

Verify out-of-band:

```bash
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=session19-vpc" \
  --query 'Vpcs[].{VpcId:VpcId,Cidr:CidrBlock,State:State}'
aws ec2 describe-subnets --filters "Name=tag:Name,Values=session19-public-subnet" \
  --query 'Subnets[].{SubnetId:SubnetId,Cidr:CidrBlock,AZ:AvailabilityZone}'
```

### ⭐ Always destroy

```bash
terraform plan -destroy
terraform destroy          # yes  →  Destroy complete! Resources: 6 destroyed.
```

A VPC, subnet, IGW, route table and security group are all **free**. An EC2 instance, NAT
Gateway or Elastic IP is not. Destroy anyway — it's the habit that saves you a surprise bill.

### Exercise

Change the VPC to `10.10.0.0/16` and the subnet to `10.10.1.0/24`, then
`terraform fmt && terraform validate && terraform plan`. You'll see `-/+` **replace** on the
VPC: ⭐ a VPC's CIDR is immutable, so changing it destroys and recreates the whole network and
everything in it. Read the plan before applying.

---

## 🔄 Workflow Recap

```
.tf files → init → fmt → validate → plan → apply → cloud → state → destroy
```

| Command | Think |
|---|---|
| `terraform init` | "Prepare this folder." |
| `terraform fmt` | "Make my code tidy." |
| `terraform validate` | "Is the configuration valid?" |
| `terraform plan` | "Show me what you're going to do." |
| `terraform apply` | "Actually do it." |
| `terraform output` | "Give me the values I exported." |
| `terraform state list` | "What are you tracking?" |
| `terraform destroy` | "Remove it all." |

---

## 🎓 Mini Project

Same architecture, different addresses — which is exactly the point: the code is identical,
only the variables change.

```
Internet → Internet Gateway
              │
         VPC 10.20.0.0/16
              ├── Public Route Table
              ├── Public Subnet 10.20.1.0/24
              ├── Route Table Association
              └── Web Security Group
```

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform fmt && terraform validate
terraform plan
terraform apply            # yes
terraform output
terraform destroy          # ⭐ don't skip
```

It combines **cloud fundamentals + networking + Terraform** into one deliverable.

### Natural extensions

- A **second AZ**: another subnet + association → real high availability
- A **private subnet** for a database, with no IGW route
- An **EC2** instance in the public subnet with user-data installing nginx
- Refactor the whole thing into a **module** with `vpc_cidr` and `az_count` inputs

---

## 🔭 Beyond the lab: NAT, private subnets, HA, cost

### The standard production VPC

```
                         Internet
                             │
                    Internet Gateway
                             │
   ┌─────────────────────────┴──────────────────────────┐
   │ VPC 10.0.0.0/16                                     │
   │                                                     │
   │   AZ-a                        AZ-b                  │
   │   ┌──────────────────┐        ┌──────────────────┐  │
   │   │ Public  10.0.1/24│        │ Public  10.0.2/24│  │  ← ALB, NAT GW
   │   │     [NAT GW]     │        │     [NAT GW]     │  │
   │   └────────┬─────────┘        └────────┬─────────┘  │
   │   ┌────────▼─────────┐        ┌────────▼─────────┐  │
   │   │ Private 10.0.11/24        │ Private 10.0.12/24  │  ← app servers, EKS nodes
   │   └──────────────────┘        └──────────────────┘  │
   │   ┌──────────────────┐        ┌──────────────────┐  │
   │   │ DB     10.0.21/24│        │ DB     10.0.22/24│  │  ← RDS, no internet at all
   │   └──────────────────┘        └──────────────────┘  │
   └─────────────────────────────────────────────────────┘
```

### NAT Gateway

Private instances still need **outbound** internet (OS updates, pulling images, calling APIs)
without being **inbound**-reachable.

```
Private subnet route table:
  0.0.0.0/0 → nat-xxxxx   (the NAT GW lives in a PUBLIC subnet)
```

⭐ **IGW is two-way; NAT is outbound-only.** That asymmetry is the whole design: your database
can reach the internet, the internet cannot reach your database.

> 💰 **NAT Gateways are one of the top surprise costs in AWS** — hourly charge *plus* per-GB
> data processing, per AZ. For HA you want one per AZ, which multiplies it. A **VPC Gateway
> Endpoint for S3** is free and removes a large share of that traffic.

### Other pieces you'll meet

| Thing | For |
|---|---|
| **Elastic IP** | A static public IPv4 (⚠️ charged when unattached) |
| **VPC Endpoint** | Private access to S3/DynamoDB/etc. without traversing the internet |
| **VPC Peering / Transit Gateway** | Connecting VPCs |
| **Bastion / SSM Session Manager** | Reaching private instances without opening SSH |
| **ALB / NLB** | Managed load balancers ([Session 4](./04_Networking_Fundamentals.md)) |
| **Flow Logs** | Packet-level record — the first thing to enable when "the network is weird" |

### Cost discipline

```bash
terraform destroy                      # ⭐ every single lab
aws ec2 describe-instances --query 'Reservations[].Instances[].{Id:InstanceId,State:State.Name}'
aws ec2 describe-addresses             # unattached Elastic IPs cost money
```

Set a **billing alarm / AWS Budget** before your first paid resource, use the free tier
deliberately, and tag everything with `Project` + `Owner` so costs can be attributed.

---

## 🗺️ AWS ⇄ Azure ⇄ GCP vocabulary

| Concept | AWS | Azure | GCP |
|---|---|---|---|
| Private network | **VPC** | **VNet** | **VPC** (global!) |
| Subnet | Subnet (per-AZ) | Subnet | Subnetwork (per-region) |
| Internet egress | Internet Gateway | (implicit) | Default internet gateway |
| Instance firewall | **Security Group** | **NSG** | Firewall rules (tag-based) |
| Subnet firewall | NACL | NSG on subnet | — |
| VM | EC2 | Virtual Machine | Compute Engine |
| Object storage | S3 | Blob Storage | Cloud Storage |
| Managed K8s | EKS | AKS | GKE |
| Serverless function | Lambda | Functions | Cloud Functions |
| Zone concept | Availability Zone | Availability Zone | Zone |

⭐ Note the real difference, not just the naming: a **GCP VPC is global** and subnets are
regional, while an **AWS VPC is regional** and subnets are zonal. Terraform's model is the
same everywhere, but the topology isn't.

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **IaaS / PaaS / SaaS** | Rent infrastructure / platform / finished software |
| **Region** | Geographic area containing multiple AZs |
| **Availability Zone** | Isolated datacentre location inside a region |
| **VPC** | Your private, isolated network — **regional** |
| **Subnet** | A CIDR slice of the VPC in **exactly one AZ** |
| **Public subnet** | ⭐ One whose route table routes `0.0.0.0/0` to an Internet Gateway |
| **Internet Gateway** | Two-way VPC↔internet connection |
| **NAT Gateway** | **Outbound-only** internet for private subnets; ⚠️ costs money |
| **Route table** | Destination → target map; **WHERE** traffic goes |
| **Route table association** | ⭐ Links a subnet to a route table — the step people forget |
| **`0.0.0.0/0`** | Any IPv4 destination — the default route |
| **Security group** | Stateful, allow-only, resource-level firewall; **IS it allowed?** |
| **NACL** | **Stateless**, allow+deny, subnet-level, first-match-wins |
| **`map_public_ip_on_launch`** | Auto-assign public IPs in this subnet |
| **`enable_dns_hostnames`** | Required for public DNS names inside the VPC |
| **Elastic IP** | Static public IPv4; charged when idle |
| **VPC Endpoint** | Private path to an AWS service, bypassing the internet |

---

## 🎯 Session Takeaways

1. ⭐ **IaaS / PaaS / SaaS is one question: where does your responsibility stop?** More managed = less control, less toil.
2. **Region = city, AZ = separate campus.** Multi-AZ is the foundation of cloud high availability.
3. ⭐ **VPC is regional, a subnet lives in exactly one AZ.** That's why HA means multiple subnets.
4. ⭐ **A subnet is "public" only because its route table points `0.0.0.0/0` at an Internet Gateway** — there is no public checkbox.
5. **Creating an IGW changes nothing by itself.** You need IGW **+** route **+** association **+** a public IP.
6. ⭐ **Route table = WHERE, Security group = ALLOWED.** Both must agree or the packet dies.
7. **Security groups are stateful and allow-only;** NACLs are stateless and need explicit return rules.
8. ⭐ **Reference another security group as a source** instead of a CIDR — it survives IP churn.
9. **Never open port 22 to `0.0.0.0/0`.**
10. **VPC CIDRs are immutable** — changing one is a `-/+` replace that destroys the whole network. Size it generously up front, and remember AWS reserves 5 IPs per subnet.
11. **NAT is outbound-only and expensive.** IGW is free and two-way.
12. ⭐ **`terraform destroy` after every lab**, and set a billing alarm before your first paid resource.
13. **The network concepts are [Session 4](./04_Networking_Fundamentals.md) with AWS names.** CIDR, private ranges, ports and firewalls didn't change.

---

## 🔗 References

- AWS VPC — https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html
- Subnets & routing — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html
- Internet Gateways — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- NAT Gateways — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- Security groups — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
- Network ACLs — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- Regions & AZs — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html
- Terraform AWS provider — https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- `terraform-aws-modules/vpc` — https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest
- AWS Well-Architected Framework — https://aws.amazon.com/architecture/well-architected/

---

## ➡️ Next

[Session 20 — Monitoring, Observability & GitOps](./20_Monitoring_Observability_and_GitOps.md)
— the infrastructure exists and the app is deployed. Now: how do you know it's healthy, and
how do you make Git the single source of truth for what's running?
