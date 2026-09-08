# Session 1 — System Design 101 🏗️

> **Topics:** Why & What of HLD · Overview of how the internet works · Challenges at Scale ·
> Vertical vs Horizontal Scaling · Introduction to Load Balancing
>
> 📄 Class doc: [\[SST-2028\] HLD 1 — System Design 101](https://docs.google.com/document/d/13GWDsE0rlfIKNVnBv3ThYPHoX3yEHDzArLMLG15Ifp4/edit?usp=sharing)

---

## 📑 Table of Contents
1. [What & Why of HLD](#-what--why-of-hld)
2. [The Google Interview Question](#-the-google-interview-question)
3. [Data Units](#-data-units-know-these-cold)
4. [What Can Go Wrong at Scale](#-what-can-go-wrong-at-scale)
5. [Case Study — del.icio.us](#-case-study--delicious)
6. [MVP](#-mvp--minimum-viable-product)
7. [How the Internet Works](#-how-the-internet-works)
8. [DNS](#-dns--domain-name-service)
9. [del.icio.us — Scaling Challenges](#-delicious--scaling-challenges)
10. [Personal Computer vs Server](#-personal-computer-vs-server)
11. [Database Design & Capacity Math](#-database-design--capacity-math)
12. [Types of Scaling](#-types-of-scaling)
13. [Which Scaling Technique?](#-which-scaling-technique-should-we-use)
14. [How Far Can Vertical Scaling Go?](#-how-far-can-vertical-scaling-go-jan-2025)
15. [Challenges with Horizontal Scaling](#-challenges-with-horizontal-scaling)
16. [Load Balancing](#-load-balancing)
17. [Heartbeat vs Healthcheck](#-heartbeat-vs-healthcheck)
18. [Is the LB a Bottleneck?](#-is-the-load-balancer-a-bottleneck)
19. [Is the LB a SPOF?](#-is-the-lb-a-single-point-of-failure)
20. [How to Succeed in HLD](#-how-to-succeed-in-hld)
21. [Key Terms Recap](#-key-terms-recap)

---

## 🎯 What & Why of HLD

### Low Level Design — **architecture of code**
- How to structure the **database schema**
- The **entities** & their **relationships**
- The **code design patterns**
- How you are laying out the various **components inside your code**

> **LLD helps us keep the code maintainable as the code complexity and team size scales up.**

### High Level Design — **architecture of the servers / machines that run the code**

| | **LLD** | **HLD** |
|---|---|---|
| Concerns | Code structure | Server/machine architecture |
| Scales with | Code complexity + **team size** | **Users + data + requests** |
| Output | Schema, entities, patterns, components | Servers, load balancers, caches, databases, shards |
| Goal | Maintainability | Scalability, availability, correctness at scale |

> ⭐ **The definition to remember:**
> **High Level Design is the study of problems that arise at scale, and the solutions for those
> problems.** As we go from **100 users to 1 billion users** (planet scale / web scale), what
> challenges arise, and how do we handle them?

### What is "scale"?
```
Scale = 1. Amount of data
        2. Number of requests per second
```

---

## 💼 The Google Interview Question

> **Interview Question — Staff Engineer @ Google**
> *Given a file containing strings, sort the strings in dictionary (lexicographic) order.*

```
input
cat, dog, apple, laptop, class, high, level, design

output
apple, cat, class, design, dog, high, laptop, level
```

**Very very easy!**

```python
with open('data.txt', 'r') as f:
    data = f.readlines()

print(sorted(data))
```

### Catch!

> **There is 50 Petabytes of data.**

Suddenly the trivial problem is a research project:

| Question | Answer |
|---|---|
| Will this amount of data fit in your **RAM**? | **No!** |
| Will it fit in your **HDD**? | **No!** |
| So? | ⭐ **This data must be stored in a distributed manner.** |

For reference: **Google has more than 10 million servers across the globe.**

The job becomes:
```
Collect data  =>  Sort  =>  Store the data back
```

> ⭐ **The whole point of the exercise:** *Simple problems become challenging at large scale.*
> `sorted(data)` is a one-liner on 50 MB and a distributed-systems problem on 50 PB.

---

## 📏 Data Units (know these cold)

| Unit | Size |
|---|---|
| **1 bit** | fundamental unit of information |
| **1 nibble** | 4 bits |
| **1 byte** | 8 bits |
| **1 Kilobyte (KB)** | 1,000 bytes |
| **1 Megabyte (MB)** | 1 million bytes |
| **1 Gigabyte (GB)** | 1 billion bytes |
| **1 Terabyte (TB)** | 1 trillion bytes |
| **1 Petabyte (PB)** | 1 quadrillion bytes |

**Decimal vs binary prefixes** — a classic source of confusion:
```
1 Kilobyte  (KB)  = 1,000 bytes        Kilo  = 1,000
1 Kibbibyte (KiB) = 1,024 bytes        Kibbi = 2^10 = 1,024
```

So the catch above is: **50 Petabytes = 50,000,000 Gigabytes!**

> 💡 For back-of-the-envelope work, always use the **decimal** powers (`10^3, 10^6, 10^9, 10^12`).
> They're close enough and the arithmetic stays in your head.

---

## 💥 What Can Go Wrong at Scale

> *Q: What can go wrong?* — with the 50 PB sort spread over thousands of machines:

| Category | Failure modes |
|---|---|
| **Network issues** | slow · down |
| **Server issues** | slow · down · **malicious** |
| **Heterogeneity issues** | different hardware models · different operating systems installed |
| **Human error** | software is buggy |
| **Data error** | hard disk is corrupt |

> ⭐ **And yet:** *"Despite all these challenges you must complete the task, both efficiently, and
> correctly!"*

This is the mindset shift of HLD: at small scale you assume things work and handle exceptions.
At large scale, **something is always broken** — the design must produce correct results anyway.

---

## 🔖 Case Study — del.icio.us

**A simple bookmarking service.** Launched **2003**, created by **Joshua**.

Timeline for context:
```
del.icio.us : 2003
YouTube     : 2004
Amazon AWS  : 2006
Google Chrome: 2008
```

### Motivation
- **Most people did not have internet at their home.**
- Any bookmarks you took on one system **are not available on the other systems** — because
  **bookmarks are local to the browser**.

> *"Let's create a bookmarking service — people can store their personal bookmarks on my website.
> My users will be able to access their bookmarks from any system, as long as they have an
> internet connection."*

📚 Reference: https://en.wikipedia.org/wiki/Delicious_(website)

---

## 🚀 MVP — Minimum Viable Product

Break the acronym apart — each word is a constraint:

| Word | Meaning |
|---|---|
| **Product** | solves a problem |
| **Viable** | usable — **demonstrates the solution** |
| **Minimal** | **minimal set of features** needed to be viable |

Also called a **proof of concept / prototype**.

### MVP for del.icio.us
| Feature | In MVP? |
|---|---|
| User should be able to **identify themselves**: registration + login | ✅ *(note: logout can be implemented later)* |
| User should be able to **add bookmarks** | ✅ |
| User should be able to **view their bookmarks** | ✅ |
| Deletion / updating / … | ❌ can be implemented later. **Not needed for MVP.** |

> 💡 The MVP discipline matters in HLD interviews too: **scope the functional requirements down**
> before you start designing, or you'll design for features nobody asked for.

---

## 🌐 How the Internet Works

### The players

| Term | Meaning |
|---|---|
| **Internet Service Provider (ISP)** | Your phone company that provides you internet — Airtel / Jio / Vi, ACT / Hayai / Starlink / Comcast |
| **IP address** | A (kinda) unique address assigned to each machine that is connected to a computer network |

> The *"(kinda) unique"* hedge matters — NAT, private ranges and dynamic allocation mean an IP is
> not a permanent, globally unique identity for a device.

### How does the browser find a website's IP?

> *Q: How does the browser know the IP address associated with a website like `google.com`,
> when Sanjana types the website URL in her browser?*

The naive version of the answer:

```
1. Joshua must PURCHASE A DOMAIN
2. Domain Registrar — intermediary that facilitates domain purchase & manipulation
      GoDaddy / Namecheap / Cloudflare
3. The registrar relays to ICANN that Joshua has purchased a domain
4. ICANN stores the IP address of Joshua's laptop against the domain name
5. Sanjana's browser asks ICANN  →  gets the IP  →  connects
```

### Issues with this design

```
5 Billion users on the internet
100 billion – 1 trillion devices on the internet
```

Therefore:
- ⭐ **ICANN servers will become a bottleneck**
- ⭐ **ICANN servers will become a single point of failure**

> 😄 As the class put it: **"I Can => I Can't!"**

---

## 📡 DNS — Domain Name Service

> **DNS maintains an IP address / a list of IP addresses for each domain name.**

The fix for the ICANN bottleneck is **decentralisation**:

| Question | Answer |
|---|---|
| **Who maintains the DNS?** | **ICANN is the central authority.** The **actual DNS servers are maintained by other entities.** |
| Who can run a DNS server? | ⭐ **Anyone!** Software companies (Google / Amazon / Meta), Governments, Militaries, Research Organizations, Educational Institutes, ISPs (Airtel / BSNL) |
| Can I choose? | **You can connect to any DNS server!** |
| What if I don't configure one? | **Your ISP also has a DNS server** — this is configured in your **router** |

```
            ┌──────────────────┐
            │      ICANN       │  central AUTHORITY (delegates, doesn't serve every query)
            └────────┬─────────┘
        ┌────────────┼────────────┬──────────────┐
        ▼            ▼            ▼              ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐   ┌──────────┐
   │ Google  │  │  ISP    │  │ Govt /  │   │ Research │   many independent DNS servers
   │8.8.8.8  │  │ (Airtel)│  │ Military│   │ / Edu    │
   └─────────┘  └─────────┘  └─────────┘   └──────────┘
        ▲
        └── your laptop can query ANY of them
```

> ⭐ **The HLD lesson hiding in DNS:** the answer to *"this central component is a bottleneck and a
> SPOF"* is **distribute the responsibility and cache aggressively**. You will apply this exact
> pattern to load balancers, caches, and databases for the rest of the course.

### Additional resources (from the class doc)
- Explanation: https://www.cloudflare.com/learning/dns/what-is-dns/
- Google Public DNS: https://developers.google.com/speed/public-dns
- Deep dive: https://network-insight.net/2015/04/21/dns-structure/
- Deep dive (IETF): https://datatracker.ietf.org/meeting/108/materials/slides-108-tdd-sessb-dns-deep-dive-part-1-pdf-00
- A-record configuration: https://www.namecheap.com/support/knowledgebase/article.aspx/319/2237/how-can-i-set-up-an-a-address-record-for-my-domain/
- CNAME vs ALIAS vs URL: https://support.dnsimple.com/articles/differences-between-a-cname-alias-url/
- Domain extensions: https://en.wikipedia.org/wiki/List_of_Internet_top-level_domains · https://www.godaddy.com/resources/skills/most-common-domain-extensions

---

## 📈 del.icio.us — Scaling Challenges

> Initially there were **100 users**. But after some time, **this website went viral**.
> Joshua was getting **millions of new bookmarks each day!**

Joshua was initially running this website **from his personal laptop**.

### System configuration (back in 2003)

*(the instructor's own first PC, from 2007 — 2003 hardware was even worse)*

| Resource | Spec |
|---|---|
| **Cost** | ₹35,000 |
| **RAM** | 128 MB |
| **HDD** | 40 GB |
| **CPU** | Intel Pentium Core 2 Dual (2 cores, 2.3 GHz) |
| **Network** | 8 Kbps dialup (BSNL) |

> *"In 2003, computers were even worse!"*

---

## 🖥️ Personal Computer vs Server

The problems with running a service off your own laptop:

- When Joshua goes to sleep, he **turns his laptop off** → **website goes down!**
- When Joshua **downloads a movie / plays a game** → **website becomes extremely slow!**

> **Joshua must stop using his laptop for his personal use!**

| | **Personal Computer** | **Server** |
|---|---|---|
| Purpose | Personal use | ⭐ **Dedicated computer whose sole purpose is to provide a (web) service over the internet** |
| Uptime | Off when you sleep | 24×7 |
| Resource contention | Competes with games, downloads, browsers | Dedicated to serving requests |

---

## 🗄️ Database Design & Capacity Math

### Schema
```sql
users (id, name, password)

user_bookmarks (user_id, URL)
    user_id : bigint        →    8 bytes
    URL     : varchar(1000) → 1000 bytes
```

**Why `varchar(1000)`?** Because real URLs are enormous. A single Amazon product URL:
```
https://www.amazon.in/Complete-Balanced-Sardine-Flavour-Pouches/dp/B0BLVJV7VT?pd_rd_w=FoAPt&content-id=amzn1.sym.c6f4280b-...&psc=1&ref_=pd_bap_d_grid_rp_0_1_ec_nped_pr_pd_hp_d_atf_rp_1_t
```

### Why `bigint` and not `int`? ⭐
```
4 byte integer
  unsigned:  0 … 2^32          (0 … 4 billion)
  signed:   -2^31 … (2^31 - 1) (-2 billion … 2 billion)
```
> **A 4-byte integer is not large enough to store all the users in the world!**
> Only **4 billion** possible values for **8+ billion** people.

So `user_id` must be an **8-byte bigint**. This is a real, famous bug class — running out of
auto-increment IDs takes production down.

### The capacity calculation

> **Q: How large is each row in the `user_bookmarks` table?**
> **≈ 1 KB** (8 bytes + up to 1000 bytes ≈ 1 KB)

> **Q: How much data are we adding to the DB each day if we receive 1 million new bookmarks/day?**
```
  1 KB/bookmark × 1 million bookmarks/day
= 10^3 bytes × 10^6 / day
= 10^9 bytes / day
= 1 GB / day
```

> **Q: In how many days will we run out of disk space?**
```
40 GB / (1 GB/day) = 40 days
```
> ⭐ **In 40 days, Joshua's server will run out of disk space!**

### It isn't only disk

> *Q: Is disk space the only resource that needs scaling?*
> Joshua's website is receiving a ton of requests each day.

| Resource | Why it's needed |
|---|---|
| **CPU** | handle the n/w requests, process the db queries |
| **Disk** | storing the data |
| **RAM** | to handle the **request contexts** |
| **Network** | to handle the requests |

> ⭐ **Every resource needs to be scaled.**

---

## 📊 Types of Scaling

### Vertical Scaling (scaling **up**)
> **Replace the existing server with a more powerful system.**

### Horizontal Scaling (scaling **out**)
> **Add more machines along with existing ones.**

```
        VERTICAL (up)                     HORIZONTAL (out)
        ─────────────                     ────────────────
      ┌────────────┐                 ┌───┐ ┌───┐ ┌───┐ ┌───┐
      │  ONE       │                 │ 1 │ │ 2 │ │ 3 │ │ 4 │  … 285 … 500
      │  POWERFUL  │                 └───┘ └───┘ └───┘ └───┘
      │  SERVER    │                 many cheap machines
      └────────────┘
```

### The economics 💰
Alternatively, Joshua could just purchase a lot of cheap laptops:
```
₹1,00,00,000 (1 crore) / ₹35,000 per laptop  =  285 laptops!
```
> **In fact he will get more! Because of *economy of scale* — he can purchase directly from the
> manufacturer. Maybe he gets 500 laptops.**

This is exactly the bet Google made: **lots of cheap commodity machines** beats **one exotic
supercomputer**, as long as your software tolerates failure.

---

## ⚖️ Which Scaling Technique Should We Use?

### Vertical scaling
| ✅ | ❌ |
|---|---|
| **Easy** — *"all you have to do is throw money at it"* | ⭐ **Has a limitation: you cannot scale infinitely.** After a certain point, you *have* to scale horizontally |
| No architectural change | **Limited by the current technology** |
| | **More costly** |

### Horizontal scaling
| ✅ | ❌ |
|---|---|
| **Not limited by current technology** — you can scale (pretty much) **infinitely** | ⭐ **A huge pain — it is extremely difficult!** |
| **Eventually you will *have* to** horizontally scale (because vertical scaling runs out) | Everything becomes a distributed-systems problem |

> ⭐⭐ **The thesis of this entire course:**
> **"The entirety of the HLD curriculum is about the challenges that arise when scaling
> horizontally and how to solve them."**

### In reality — you use both
> *"You vertically scale till it's financially feasible and simple. When it becomes too costly, or
> when you run out of hardware capability, you scale horizontally."*

Certain applications (**CPU-intensive tasks**) mandate **both**:

| Application | Scaling needed |
|---|---|
| **del.icio.us** | **Horizontal is all you need.** All systems can be cheap and less powerful |
| **Video Processing** | You **have to scale horizontally**, but **each server itself must have a powerful GPU, CPU, lots of RAM** → so you're also scaling **vertically** |
| **Large Language Model (ChatGPT)** | A **7 TB** neural network model → you need **7 TB of RAM + 7 TB of GPU memory + 7 TB disk** (vertical), and with **500 million users** you also need **horizontal** scaling |

---

## 🔝 How Far Can Vertical Scaling Go? (Jan 2025)

| Resource | **Typical server** | **Max server (Jan 2025)** |
|---|---|---|
| **CPU** | 1 – 16 cores | **370 cores** (×2 on a single motherboard) |
| **RAM** | 1 GB – 32 GB | **12 TB** |
| **HDD** | 500 GB – 8 TB | **2 PB** |
| **Network** | 10 Mbps – 1 Gbps | **10 TBps** |

> 💡 **Read this table twice.** The maximum machine is *enormous* — which means a surprising number
> of systems never need to scale out at all. But note the 50 PB sort from the interview question:
> even a 2 PB max-spec disk can't hold it. **The ceiling is real, it's just high.**

---

## 🚧 Challenges with Horizontal Scaling

Now that Joshua has 500 laptops:

> **Q: Which server's IP should the DNS register?**

DNS maps a domain to an IP. With 500 servers, which one? This single question forces the
introduction of the **load balancer**.

---

## ⚖️ Load Balancing

### Purpose
1. **Provide a unified view of the entire backend system to the end user** — because the end user
   doesn't care which exact server handles their request.
2. **Distribute the load (requests / data) equally** across the other app/db servers.

```
                    ┌──────────────────┐
   Users ─────────▶ │  LOAD BALANCER   │  one address, one "view" of the backend
                    └──┬───┬───┬───┬───┘
              ┌────────┘   │   │   └────────┐
              ▼            ▼   ▼            ▼
          ┌───────┐  ┌───────┐   ┌───────┐  ┌───────┐
          │ App 1 │  │ App 2 │ … │App 499│  │App 500│
          └───────┘  └───────┘   └───────┘  └───────┘
```

### Resources (from the class doc)
- How to configure: [LB configuration doc](https://docs.google.com/document/d/1DxQzLpu1XPe_mRWsewNWtKL6E4uwKHQhBp7GX6Sg7qI/edit#heading=h.fzwcs020kou5)
- Tutorial: https://avinetworks.com/what-is-load-balancing/
- AWS Elastic Load Balancer: https://aws.amazon.com/elasticloadbalancing/getting-started/

---

## 💓 Heartbeat vs Healthcheck

> **Q: How does the Load Balancer keep track of the running servers?**
> **Servers can crash at any time!** The LB **should not forward a user's request to a server
> which is down.**

Two mechanisms — know both, and which direction each one points:

| | **Heartbeat** | **Healthcheck** |
|---|---|---|
| **Who initiates** | ⭐ **The server** | ⭐ **The LB** |
| **Message** | Each server periodically pings the LB saying **"I'm alive!"** | LB pings each server asking **"Are you alive?"** |
| **Failure rule** | If the LB does **not receive heartbeats** from a server for a few **consecutive** times → assume the server is dead | If the server **fails to respond within time** (request timeout) → assume the server is dead |

```
   HEARTBEAT                          HEALTHCHECK
   ─────────                          ───────────
   Server ──"I'm alive!"──▶ LB        LB ──"Are you alive?"──▶ Server
   Server ──"I'm alive!"──▶ LB        LB ◀────── 200 OK ────── Server
   Server ─────  ✗  ─────▶ LB        LB ──"Are you alive?"──▶ Server
   (3 misses → presumed dead)         (timeout → presumed dead)
```

### How does the LB even know which servers exist?
- When the server first comes online in the network it must **ping the LB to register itself**, or
- You can **configure a "range" of IPs** in the LB:
  ```
  10.11.0.1 … 10.11.2.20
  ```

---

## 🚦 Is the Load Balancer a Bottleneck?

Compare the work each one does.

### An app server (e.g. a Django server handling bookmarking requests)
```
1. Request goes through the OSI layers (webserver resides at the Application Layer)
2. Deserialize the request to get the payload
3. Authorization — check the user permissions
4. Fetch the resource from DB
5. Process the data
6. Generate a response
7. Serialize the response
8. Send the response
```
> ⭐ **A typical app server can handle 100 – 1000 requests/sec.**

### A load balancer
> **The LB does NOT handle the request — it simply forwards it.**
```
1. Look at the IP address in the request
2. Decide which server to forward the request to
3. Re-route the request to that server
```
> ⭐ **A typical LB can easily handle 100,000+ requests/sec.**

### Conclusion
```
LB capacity / app capacity  ≈  100,000 / 1,000  =  100×
```
> **Therefore, LBs do not easily become bottlenecks.**
> **But at the scale of Google, a single LB will not be enough!** How to solve that? → next question.

---

## 💀 Is the LB a Single Point of Failure?

> **Q: What if the Load Balancer crashes? Isn't the LB a Single Point of Failure (SPoF)?**
>
> **Yes absolutely! If the LB goes down, the entire website goes down!**

### ❌ The tempting wrong answer
> *Q: Could we add multiple LBs and have another LB in front of the LBs?*
> **No, that will not work!**
> **We've just added another layer — the problem now happens at the first LB.**

```
   ❌  Client ──▶ [LB-0] ──┬──▶ [LB-1] ──▶ apps
                    ▲       └──▶ [LB-2] ──▶ apps
                    └─ still ONE SPOF, just moved up a level
```
This is an important general lesson: **you cannot solve a SPOF by putting another single component
in front of it.** You've only relocated the problem.

### ✅ The solution
> **We have multiple LBs, and the DNS acts as a LB in front of the LBs.**

```
   ✅  Client ──▶ DNS  (returns one of several IPs — a list of A records)
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
     [LB-1]     [LB-2]     [LB-3]      ← no single LB is critical
        │          │          │
        └──────────┼──────────┘
                   ▼
             App servers (500 of them)
```
DNS works here precisely because it is **already distributed and replicated** (see the DNS
section) — it has no single point of failure to inherit. Recall that *"DNS maintains an IP address
**/ a list of IP addresses** for each domain name"* — that list is what makes this possible.

---

## 🎲 Which Server Should the Request Go To?

> **Routing algorithm decides that!**
> - **Round Robin**
> - **Consistent Hashing**

Both are the entire subject of **Session 2**.

---

## 🎓 How to Succeed in HLD

Straight from the class doc — worth taking seriously:

| Principle | What it means |
|---|---|
| **Be curious** | Ask questions during the doubt session, devour all the reference material provided, explore interesting topics on your own |
| **Think about the internals** | For any app/software you use, think about the internal design, how they might handle the scale, what unique challenges they face, and how all that affects the features they support (**and don't support**) |
| ⭐ **Think of the business use-case of every feature** | e.g. *how does showing a "blue checkmark for read" help WhatsApp?* |
| **Interact with your peers** | HLD is best learned via discussion — bouncing ideas in a group, talking about what you've seen at work and why, and the unique tech challenges you and your company face |
| **Solve the assignments before the next class** | They're MCQs so they're quick, but they **require critical thinking** — which is exactly what the module develops |

### Recommended resources
| Type | Resource |
|---|---|
| 📕 **Reference book** | **"Designing Data-Intensive Applications: The Big Ideas Behind Reliable, Scalable, and Maintainable Systems"** — Martin Kleppmann |
| 📺 Alex Xu | https://www.youtube.com/@ByteByteGo |
| 📺 Arpit Bhayani | https://www.youtube.com/@AsliEngineering |
| 📺 Hussein Nasser | https://www.youtube.com/@hnasr |
| 📺 Martin Kleppmann | https://www.youtube.com/@kleppmann |
| 🔗 Microservices reference | https://microservices.io/ |
| 🔗 Engineering blogs | Amazon / Meta / Netflix |

### ⚠️ Resources to **avoid**
- **Medium articles by random authors** — *go to engineering blogs of **companies**, not engineering
  blogs of **people***
- **geeksforgeeks**

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **LLD** | Architecture of **code** — schema, entities, patterns, components |
| **HLD** | Architecture of the **servers/machines** that run the code |
| **HLD (real definition)** | The study of problems that arise **at scale**, and their solutions |
| **Scale** | (1) amount of data, (2) requests per second |
| **MVP** | **M**inimal set of features that is **V**iable (usable) and is a **P**roduct (solves a problem) |
| **ISP** | Company that provides your internet connection |
| **IP address** | (Kinda) unique address of a machine on a network |
| **Domain Registrar** | Intermediary facilitating domain purchase (GoDaddy/Namecheap/Cloudflare) |
| **ICANN** | The central **authority** for domains — a bottleneck/SPOF if it served every query |
| **DNS** | Maintains an IP / list of IPs per domain name; run by **many independent entities** |
| **Server** | Dedicated machine whose sole purpose is providing a service over the internet |
| **Vertical scaling** | Replace the server with a more powerful one; easy, costly, **capped** |
| **Horizontal scaling** | Add more machines; ~unlimited, but **extremely difficult** |
| **Economy of scale** | Buying in bulk direct from the manufacturer lowers per-unit cost |
| **Load Balancer** | Gives a unified view of the backend + distributes load equally |
| **Heartbeat** | ⭐ **Server → LB**: "I'm alive!" |
| **Healthcheck** | ⭐ **LB → Server**: "Are you alive?" |
| **SPoF** | Single Point of Failure — a component whose death kills the system |
| **Routing algorithm** | How the LB picks the server (Round Robin, Consistent Hashing) |

---

## 🎯 Session Takeaways

1. **LLD scales with team size & code complexity; HLD scales with users, data and requests.**
2. **Simple problems become challenging at large scale** — `sorted(data)` on 50 PB is a
   distributed-systems problem.
3. At scale, **failure is constant** (network, servers, heterogeneity, humans, data) — and you must
   still be **efficient and correct**.
4. **Do the capacity math early.** 1 KB/row × 1M rows/day = 1 GB/day → a 40 GB disk dies in **40 days**.
5. **Every resource** needs scaling — CPU, disk, RAM, network — not just storage.
6. **Vertical is easy but capped; horizontal is unlimited but hard.** Use vertical until it's
   uneconomic, then go horizontal. Some workloads need both.
7. ⭐ **The whole course is about the problems horizontal scaling creates, and how to solve them.**
8. **A load balancer is ~100× cheaper per request than an app server**, so it rarely bottlenecks —
   but it *is* a SPOF.
9. ⭐ **You can't fix a SPOF by adding another single component in front of it** — use multiple LBs
   with **DNS** distributing across them.
10. **Heartbeat = server pushes; Healthcheck = LB pulls.**

---

## ➡️ Next
**[Session 2 — Load Balancing & Consistent Hashing](./02_Load_Balancing_and_Consistent_Hashing.md)** —
sharding vs routing, why Round Robin/Bucketing/Mapping-tables all fail, and the hash ring.
