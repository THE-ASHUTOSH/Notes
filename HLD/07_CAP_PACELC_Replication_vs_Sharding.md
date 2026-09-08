# Session 7 — Storage Layer: CAP Dilemma & Replication 🎭

> **Topics:** CAP & PACELC theorems · Replication vs Sharding
>
> 📄 Class doc: [\[SST-2028\] CAP-PACELC](https://docs.google.com/document/d/1hrZ9_18wXISAUqoztCwEF1z9q4hAuXpL5hpNvl00LlA/edit?tab=t.0)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [What CAP & PACELC Are For](#-what-cap--pacelc-are-for)
2. [Consistency — When Does It Even Apply?](#-consistency--when-does-it-even-apply)
3. [The Three Consistency Levels](#-the-three-consistency-levels)
4. [Other Consistency Forms](#-other-forms-of-consistency)
5. [Availability](#-availability)
6. [Partition Tolerance](#-partition-tolerance)
7. [The Bank/ATM Dilemma](#-the-bankatm-dilemma)
8. [CAP Theorem](#-cap-theorem)
9. [A+P, C+P, A+C Systems](#-the-three-combinations)
10. [CAP — the Better Definition](#-cap-theorem-the-better-definition)
11. [PACELC Theorem](#-pacelc-theorem)
12. [Proof by Story — Aditi's Reminder Service](#-proof-by-story--aditis-reminder-service)
13. [Replication](#-replication)
14. [Isn't Redundancy Bad? (Normalization)](#-isnt-redundancy-bad-normalization)
15. [Why We Need Replication](#-why-we-need-replication)
16. [Replication vs Sharding](#-replication-vs-sharding)
17. [What About Caching?](#-what-about-caching)
18. [Key Terms Recap](#-key-terms-recap)

---

## 🎯 What CAP & PACELC Are For

> **CAP theorem & PACELC theorem tell us what is possible and what is not possible when we talk
> about distributed systems.**
>
> **distributed = more than 1 server, connected via some network.**

> ⭐ **Note: CAP/PACELC will apply only when you have replication** (multiple copies of the same
> data, distributed across multiple servers, which are connected with a network).

---

## 🔍 Consistency — When Does It Even Apply?

Before arguing about consistency, check that the question is even **meaningful**.

> **When can we talk about consistency?**

### 1. Consistency is always about **data**
> - ⭐ **Stateless app servers cannot be consistent or inconsistent** — because they're stateless,
>   they don't have any data
> - Asking otherwise is a category error, like:
>   - *"At how many km/hr is your door cooking the colour 9?"* → **undefined**
>   - *(Ragging question in IITs)* *"What's the colour of an electron?"* → **undefined**
> - **Consistency is typically in the context of a database or caches**

### 2. There have to be **multiple copies** of the same data (replication/caching)
> - ⭐ **If there's only 1 copy of data — then it is guaranteed to be up to date** (because you're
>   reading & writing to the same place)
> - **The only possible way for things to be out-of-date is when we have multiple copies of the same
>   data**, for example:
>   - **database + cache**
>   - **database replicas**

### 3. There should be a **read after a write/update**
> - ⭐ **If the data is static/immutable, then there's no way of having stale reads** — because the
>   data is never updated
> - For example, after the contest is over, the leaderboard is **always** up-to-date (because no new
>   submissions). ⭐ So after the contest, we won't say the leaderboard is *consistent* — we'll say
>   **consistency is no longer relevant**

*(This is exactly the Code Judge insight from Session 5: **immutable data needs no invalidation**.)*

### Definitions
| Term | Definition |
|---|---|
| **State** | ⭐ **Some data that we wish to preserve across multiple requests.** So **state == data** |
| **Stale read** | ⭐ **When an old value of data is read after an update.** Stale reads **can** (not always) lead to bad user experience. **If a stale read is possible, it means we don't have immediate consistency** |

---

## 🎚️ The Three Consistency Levels

### Immediate Consistency (a.k.a. "Consistent")
> - ⭐ **It is impossible for stale reads to happen** — every read is guaranteed to read the latest
>   data
> - **Only possible when all the "copies" are always kept in sync, all the time (or use Quorum)**
> - ⭐ **Immediate consistency is always good to have, but it is very hard to achieve** (typically
>   requires **2 phase commit** → **high latency, low availability**)
> - **Because it is hard to achieve, we do NOT always go with immediate consistency**

### Eventual Consistency (a.k.a. "Not Consistent")
> **Is it possible for some reads to be stale for some time. But if we wait long enough, then
> eventually we will be able to read the updated data.**

⭐ **The precise definition matters — this is a classic exam trap:**

| Statement | Verdict |
|---|---|
| *"**Eventually the data will be consistent**"* | ❌ **WRONG** — this would mean there is a future point in time after which the data will **always remain** consistent |
| *"**Eventually every write will reflect in all copies**"* | ✅ ⭐ **CORRECT** — if we wait long enough, then what we had written earlier will be reflected. **However, the data can still be stale because new writes are coming in continuously** |

```
   ❌  "the system becomes consistent at some point and stays consistent"
   ✅  "each individual write eventually lands everywhere"
       …but the system as a whole may NEVER be fully in sync,
          because new writes keep arriving. ⭐
```

> **In 99% of the cases, eventual consistency is good enough.**

### Data Loss — No Consistency whatsoever
> - **If it is possible for some data to be permanently lost**, then it means there are some updates
>   that **will never reflect** in the data
> - ⭐ **No matter how long we wait, the data will never become consistent. Data has been permanently
>   lost**
> - **It is very rare for systems to have no consistency** (only relevant in case of **analytics** —
>   when the **trend is more important than individual data points**)

*(= the Write-Back cache from Session 4.)*

---

## 🧩 Other Forms of Consistency

> **Q: Are there still more forms of consistency?**
> **Yes… but all of the other forms fall inside the umbrella of eventual consistency.**

| Form | Meaning |
|---|---|
| ⭐ **Read-your-Write Consistency** | **If Ashish has edited his post, then he will immediately see the update, but his friends might not see the update immediately** (friends will get it eventually) |

> *There are still more forms…* (monotonic reads, causal consistency, session consistency, …)

> 🧠 **Read-your-write is the practical sweet spot** for social apps: the *author* is the one who
> notices staleness, so give **them** a fresh read and let everyone else be eventual. You'll see
> this again in the Newsfeed and Messaging case studies.

---

## 🟢 Availability

> **Availability refers to whether a server can deny a request or not.**
> - **If a server *can* deny a request** → the system is **"not available"** / has **"low
>   availability"**
> - **If a server *always* satisfies the request** → the system is **"available"** / has **"high
>   availability"**

### What is NOT low availability ⭐

| Scenario | Low availability? | Why |
|---|---|---|
| **A bad request comes and the server denies it** (**4xx** bad request, **3xx** auth error) | ❌ **No** | ⭐ **In cases when the user is at fault, the server is allowed to deny the request** — it must still respond, but with the appropriate error message. **We will still call the system highly available** |
| **A request comes, but the server crashes** (and doesn't respond) | ❌ **No** | ⭐ **The request will timeout, the client can just retry, and the LB will send the next request to a healthy server** |

### What IS low availability
> ⭐ **If a healthy request comes to a healthy server — but the server still refuses to provide the
> service** (for some internal reason — **mostly because it is unable to sync-up with other
> replicas**) — then the service is said to have **low availability**.
>
> **Examples:**
> - **internal server error** (bad code / unable to access certain critical resources)
> - **some specific reason why the server wants to deny service**
> - **request times out** — ⭐ **because the server is busy, not because the server is down**

```
   healthy request  +  healthy server  +  REFUSED   =  ⭐ LOW AVAILABILITY
   bad request      →  4xx                          =  fine
   dead server      →  timeout → retry elsewhere    =  fine
```

> 🧠 **This is a much sharper definition than the usual "uptime percentage".** Availability in CAP
> is about **a working server choosing to say no**, which is exactly what happens when it can't
> reach its replicas.

### Availability arithmetic
> **99.999% availability** → in 1 year, you can have a service downtime of **maximum 5.26 minutes**.

---

## 🔌 Partition Tolerance

> **A system is partition tolerant if it can continue functioning seamlessly in the face of network
> partitions.**
>
> - ⭐ **When a partition happens, if the system continues working at least partially** (some
>   availability might be lost, some consistency might be lost, **but the entire system doesn't go
>   down entirely**) → the system **is** partition tolerant
> - ⭐ **If any loss of communication between nodes brings down the entire system as a whole** → the
>   system is **not** partition tolerant
>
> **Partition tolerance is very highly desired.**

### Network Partition
> **In a network of servers (distributed system), if some subset of the servers is not able to
> communicate with the other subset of servers, then we have a network partition.**

```
   ┌───────────────┐        ✂  partition  ✂        ┌───────────────┐
   │  Server A  ●──┼───────────  ✗  ─────────────┼──●  Server B    │
   │  Server C  ●──┤                             ├──●  Server D    │
   └───────────────┘                             └───────────────┘
       subset 1                                       subset 2
```

> ⭐ **It is not necessary for the network connection to break for the partition to happen.**
> **A slow/congested network can behave like a broken network because the requests will time out.**

### How likely is a network partition?
> - **In large scale distributed systems (Google has 10 million+ servers), network partitions are
>   not just likely — they ALWAYS exist**
> - **Some subset is always disconnected** — some node / network will always be down, leading to a
>   small partition somewhere
> - ⭐⭐ **100% probability! There's ALWAYS a partition somewhere.**

> 🧠 **This single fact is what collapses CAP from "pick 2 of 3" into "pick A or C".** You don't get
> to *choose* P — reality assigns it to you.

---

## 🏧 The Bank/ATM Dilemma

**Situation:**
> - **Tarun wants to withdraw money from his bank account via the ATM**
> - In the backend, the bank will **replicate** the account information — because **we don't want to
>   lose the account data if some server/hard-disk crashes**
> - When Tarun withdraws money from the ATM, **the bank must update both copies of the data** to
>   reflect the new balance

**Now imagine that a network partition happens** — the two bank database servers cannot communicate.
Two cases arise:

### Case 1 — **A+P**: Highly Available, low consistency
> - **The bank returns success without updating both the servers** — it updated the balance in just
>   one server and **gives the money to Tarun**
> - This gives us **eventual consistency** (stale reads are possible, but **once the network is back
>   up, the db servers can sync up**) and it will be **highly available**
> - ⭐ **The data was inconsistent, but the system remained available in the face of n/w partition**

### Case 2 — **C+P**: Consistent, without Availability
> - **The bank database can detect that it is not able to communicate with its replica, and it
>   denies the service**
> - ⭐ **Low availability** — because the request was healthy, the server was healthy, **still the
>   request got denied!**
> - **But we got immediate consistency** — a stale read was not possible
> - **However availability suffered** — we had to deny the request
>
> ⭐ **Note: the "redeem money" functionality is down, but the "check balance" functionality is still
> up. So the entire system is not down as a whole — the system IS partition tolerant.**

```
   ⭐ Partition tolerance ≠ everything keeps working.
      It means the system DEGRADES instead of DYING.
      (withdrawals blocked, balance checks fine  →  still partition tolerant)
```

### When is a system NOT partition tolerant?
> ⭐ **When any n/w partition brings down the entire system!**
> **This is very very rare — most backend systems (99.99%) are designed to be partition tolerant.**
>
> **This happens in the case of stock exchanges (NSE/BSE/SSE/NYSE). Stock Exchanges are A+C
> systems. They don't have Partition Tolerance.**
> - **If two servers within the stock exchange are unable to communicate with each other, the entire
>   exchange will be shut down until the issue is resolved**
> - **Stock Exchanges therefore do a lot of engineering to minimize the chances of a n/w partition.
>   Each pair of servers will be connected by multiple redundant fibre connections**

### What do real banks actually do? ⭐
> **In reality, the ATM system, and most banks follow A+P (eventual consistency).**
>
> **Reason: because the banks have found a way to "earn" from their own mistakes.**
>
> - If we redeem more money than what you have due to a n/w partition, **eventually the n/w
>   partition will resolve** and both bank DBs will be able to communicate. Then they will do
>   automatic **"auditing"** and realize that you redeemed twice
> - ⭐ **Tarun's bank balance is now negative. The bank will charge Tarun an overdraft fee + interest
>   on the ₹100 he borrowed**
>
> ⭐ **This is also why "refunds" take 5–7 business days, even though payment happens immediately.**
> *(Note: typically the refund actually happens immediately — but in the worst case it can take a
> long time, because of eventual consistency.)*

> 🧠 **The deepest lesson in this session:** the consistency choice is a **business decision**, not a
> technical one. The bank chose availability because **the cost of the inconsistency is recoverable
> — and even profitable.** Always ask *"what does it cost the business when this is wrong?"*

---

## 📐 CAP Theorem

> **CAP theorem gives you a fundamental limit of what you can achieve with distributed systems.**

```
                        CONSISTENCY
                             /\
                            /  \
                           /    \
                          /  C+A \        pick any 2 (1st definition)
                         /   0.1% \
                        /----------\
                       /  A+P    C+P\
                      /   99%    0.9%\
       AVAILABILITY  /------------------\  PARTITION TOLERANCE
```

> ℹ️ **Google Spanner "seems" to violate the CAP theorem** — they claim to provide all 3.
> - **They don't actually violate CAP** (they don't claim to violate CAP either)
> - ⭐ **They do some black magic with timestamps** (TrueTime — atomic clocks + GPS) to
>   **practically** achieve all 3

---

## 🎲 The Three Combinations

### A+P Systems — high availability + eventual consistency ⭐ **99% of all systems**
> - **Even if there's a partial failure (network partition), the system will still continue
>   functioning** (the users' requests will continue being served)
> - **AP systems give up on consistency** — they're **eventually consistent**
>
> ⭐ **99% of all systems are AP. Because mostly, we do not care about immediate consistency.**
>
> **Example — Social Media (Twitter / Facebook / Instagram / …):**
> **If the user continues to see the old post, or if a new post doesn't appear in your friend's
> newsfeed immediately, it's not the end of the world — as long as the post gets updated eventually.**

### C+P Systems — immediate consistency + low availability ⭐ **0.9%**
> - **If there's no network partition, only then is the system able to serve the users**
> - **The moment a network partition happens, the system may deny the users' requests** (lose
>   availability)
>
> **Rare. Only 0.9% of systems are C+P. When data is critical.**
>
> **Examples:**
> | Example | Note |
> |---|---|
> | **financial transactions & banks** | ⭐ *these are often eventually consistent* (see above!) |
> | **Stock brokers (Zerodha)** | |
> | **Ticket Booking (BookMyShow) / Product Purchase** | ensure that customers are not ordering more than the inventory amount |
> | **IRCTC** | ⭐ **makes ticket booking eventually consistent** — they offer you **RAC tickets** which are resolved later — *"eventually"* |
>
> **CP is rare, because in most cases we're okay with eventual consistency. Immediate consistency is
> always good to have, but not strictly needed in most systems.**

*(That IRCTC/RAC remark is a direct preview of **Session 16**.)*

### A+C Systems — consistent + available, but **no partition tolerance** ⭐ **0.1%**
> - **Never denies the user's request, and always remains consistent — as long as there's no network
>   partition**
> - ⭐ **The moment a network partition happens, the entire system crashes as a whole!**
>
> **Extremely rare. Only 0.1% of cases.**
>
> **Example: stock exchange (NSE, NYSE, SSE, BSE, …)**
> - ⭐ **A+C systems are typically NOT geographically distributed** — because we cannot afford
>   network partitions
> - In stock exchanges:
>   - **very powerful servers**
>   - **all the servers are located in the same building**
>   - **servers are connected with high speed fibre**
>   - **and multiple redundant connections**
> - **The chances of having a network partition in such a system are close to 0** (**by design** —
>   extremely expensive to maintain)
> - **Still, if a n/w partition happens, then the entire system has to shut down**

> ⭐ Notice the strategy: A+C systems don't *solve* partitions — they **spend enormous money making
> them nearly impossible**, and accept total shutdown as the fallback.

---

## 🔑 CAP Theorem: the Better Definition

> **1st definition: pick any 2.**
>
> ⭐⭐ **2nd definition: when there's a network partition, you must choose between Availability or
> Consistency. You cannot have both.**
>
> **As long as there's no n/w partition, you don't have to worry about anything. The moment a n/w
> partition happens, you can either choose Consistency, or you can choose Availability. You cannot
> get both.**

### Why the 2nd definition is the useful one
> **Because in large systems there's ALWAYS a n/w partition somewhere. Therefore you definitely want
> partition tolerance. So effectively, your choice is typically between A+P or C+P.**

```
   ⭐ P is not a choice — it's the weather.
      Your real question is only ever:  "when it rains, do I stay open (A) or stay correct (C)?"
```

---

## 🌦️ PACELC Theorem

> **PACELC theorem is an extension to the CAP theorem.**

```
   P A C   ⭐ if there's a network PARTITION, choose between
             • AVAILABILITY  (serve potentially stale data)          OR
             • CONSISTENCY   (service down, but data remains consistent)

   E L C   ⭐ ELSE (even when there's NO partition), there's a trade-off between
             • LATENCY       (low latency because sync-up is later)   OR
             • CONSISTENCY   (sync up right away, but latency is higher)
```

> **Just like in DSA we have a trade-off between Time Complexity and Space Complexity, we also have
> a trade-off in HLD between Consistency and Availability, and Consistency and Latency.**

### The punchline ⭐⭐
> **Basically:**
> - **If you choose immediate consistency, then you have to give up on Availability AND Latency
>   both!**
> - **If you want your system to always be consistent, then**
>   - **it will be slow (high latency), and**
>   - **it might deny requests (low availability)**
>
> ⭐ **So immediate consistency comes at a huge cost!**

| | Partition happening | No partition |
|---|---|---|
| **Choose Consistency** | ⭐ Deny requests (**low availability**) | ⭐ Sync synchronously (**high latency**) |
| **Choose the other thing** | Serve stale data (**high availability**) | Sync later (**low latency**) |

> 🧠 **Why PACELC is a genuine improvement on CAP:** CAP only describes the rare partition case,
> which sounds like an edge case you can ignore. **PACELC points out that you're paying for
> consistency 100% of the time, in latency** — which is what you actually feel in production.

---

## 📖 Proof by Story — Aditi's Reminder Service

A brilliant, fully worked intuition pump.

### The setup
**Aditi's Reminder Service** — customers call her, she writes reminders in a diary, and calls them
back at the right time.

| Scaling | What happened |
|---|---|
| **Vertical Scaling (Scaling Up)** | In the start, Aditi was handling this service **along with her day job**… but as the number of requests increased, **she quit her job and started doing this service full time** |
| **Horizontal Scaling (Scaling Out)** | Because Aditi was not able to handle all the calls herself, **she hired Sanjana** to help her out |

### One shared diary, or two independent diaries?
> **If we go with a single diary, then:**
> - ⭐ **Aditi & Sanjana will have to be in the same room** (colocated geographically — can't be
>   distributed far apart) — **it's not a distributed system**
> - ⭐ **Both of them will fight for the diary** — the diary will become a **bottleneck**
>
> **It is better to have separate diaries:**
> - **they can be located far apart** (Sanjana can work from home)
> - **the diary is not the bottleneck**
>
> ⭐ **So we go with the 2-diary approach (because a single diary would render our scaling useless).**

> 🧠 **This is the whole reason consistency problems exist.** The moment you scale out for real, you
> must duplicate state — and duplicated state can disagree.

### The Angry Customer
> **Customer:** *"Yesterday I called you to remember my flight at 11 am in the morning. But then I
> called you at 8 am to ask for my flight timing, and you said that you don't remember. You lost my
> data, and I missed my flight."*
>
> **Q: Why did this happen?**
> ⭐ **When the write request came, it went to Sanjana, but the read request came to Aditi, and
> Aditi's data was not in sync with Sanjana's data.** → **Consistency Issue**

### Protocol 1 — Sync eventually (at night)
> They decide to **copy each other's data each night before they close the shop**, so that in the
> morning both have the same copy of data.
>
> **Q: Can there be stale reads still — can there be angry customer calls?**
> ⭐ **Yes**, until the sync happens (at night) any reads before the sync can potentially be stale.
> **But if we wait long enough, eventually the data will be in sync.**
>
> - So **the data can be stale (low consistency)**
> - but when a write request comes, **we only have to write at 1 place (low latency)**
>
> ⭐ **Low Consistency + Low Latency**

### Protocol 2 — Sync immediately
> Whenever one of them gets a call:
> 1. **write the data in their own diary**
> 2. **put the customer on hold**
> 3. **call the other person**
> 4. **get the other person to write the data as well in their diary**
> 5. **only when the other person responds with success, we can return success**
> 6. **if the other person returns error, then we should delete from our diary (rollback) and return
>    error**
>
> - ⭐ **This protocol gives immediate consistency** — the data will always be in sync (because I'm
>   always writing to both diaries)
> - ⭐ **Note that this leads to higher latency** — when Aditi is calling Sanjana to write, **the
>   client is waiting on the phone**
> - ⭐ **Also, the throughput will suffer** — because now **every call is being handled twice** (it
>   goes to both Aditi and Sanjana). **This means that the horizontal scaling that we did is now
>   suffering**

> **Q: Will this protocol also be applied to the reads?**
> ⭐ **No. This is only for the writes.** When a read comes, **both Aditi and Sanjana can respond
> independently** using the data in their own diaries (because both of them have all the data).
> **So no waiting time for read queries (low latency).**
>
> ⭐ **High Consistency + High Latency**

> 💡 **Note the asymmetry:** replication makes **writes** expensive and **reads** cheap. That single
> asymmetry is why replication is a **read-scaling** technique (see the table below).

### How does Google Docs handle this?
> - ⭐ **Gives you eventual consistency** — you're allowed to make changes **even when your network
>   is down**; the changes will sync up eventually once your network is restored
> - **How? By performing conflict resolution later.**
>
> **Conflict-Free Replicated Data Types (CRDTs)**
> ⭐ **CRDTs are very powerful, but also very complex. Google Docs doesn't actually use CRDTs, but it
> uses a custom protocol that is a little weaker (but similar) to CRDTs.**

### Vacation Time — a server being down is **not** a partition ⭐
> **Sanjana decides to go on a vacation.**
> - **No availability issue** — Sanjana is just on a vacation
> - ⭐ **No n/w partition** — Sanjana is just on leave. **The calls can be routed to Aditi**
> - **When Sanjana comes back, before she starts taking any calls, she can just sync up with Aditi's
>   diary — no consistency issue here**
>
> **In BOTH protocols:** because Sanjana is simply **not present**, Aditi can just keep writing in
> her own diary (**even in Protocol 2**). When Sanjana comes back she can sync up before serving any
> calls.
>
> ⭐ **So no availability issue, no consistency issue. Why? Because there's no n/w partition — it's
> just that some server (Sanjana) is down.**

> ⭐⭐ **Critical distinction: a DOWN node is not a PARTITION.** A down node can be removed from the
> pool and resynced later. A **partition** is when both sides are **alive and serving** but can't
> see each other — that's when you're forced to choose.

### The Big Fight — an actual partition
> **Sanjana & Aditi have a big fight, and they refuse to talk to each other (n/w partition).**

| Protocol | What happens | Outcome |
|---|---|---|
| **Protocol 1 — Sync eventually** | **No worries — both of them can continue taking calls & continue writing in their own diaries. Eventually the fight will resolve (n/w will be fixed) — they can just sync up their diaries when they're friends again.** **Data will remain stale until the fight resolves. But the service will continue to be available** | ⭐ **Partition ⇒ High Availability + Eventual Consistency** |
| **Protocol 2 — Sync immediately** | **The protocol mandates that Aditi must write to both places, but she's not talking to Sanjana. So when she gets a "write" call, she must deny.** ⭐ **Note that she can still continue serving "read" requests from her own diary! But any write requests must be denied until the fight resolves** | ⭐ **Partition ⇒ Immediate Consistency + Low Availability** |

> **Note that only the write requests are unavailable — the read requests continue. But overall, we
> will say that the system has low availability.**

> 🧠 **The story proves CAP without a single equation.** Same two people, same partition — the only
> variable is **the sync protocol**, and it forces exactly the A-vs-C choice.

---

## 📄 Replication

> ⭐ **Explicitly (by choice) having multiple copies of the same data. These copies will be stored in
> different servers.**

---

## 🤔 Isn't Redundancy Bad? (Normalization)

> **RDBMS — we study normalization.** While studying normalization, we say that **redundancy
> (duplicate data) is bad**, because it leads to various **anomalies** (read / write / delete / …).

### The anomalies, demonstrated

**Un-normalized table:**
| Course | Student |
|---|---|
| HLD | Tarun |
| HLD | Sanjana |
| LLD | Harini |
| DBMS | Sanjana |

**Update anomaly** — rename `HLD` ⇒ `High Level Design`, but **fail to update all places**:
| Course | Student |
|---|---|
| **High Level Design** | Tarun |
| **HLD** | Sanjana |
| LLD | Harini |
| DBMS | Sanjana |
> ⭐ **Effectively, we've an additional course now!** (inconsistency)

**Delete anomaly** — if we **delete Sanjana**:
> ⭐ **We have mistakenly deleted the course DBMS** (because Sanjana was the only entry with DBMS)

### Normalized design (which gets rid of these anomalies)
| Course ID | Course Name |
|---|---|
| 1 | HLD |
| 2 | LLD |
| 3 | DBMS |

| Student ID | Student Name |
|---|---|
| 1 | Sanjana |
| 2 | Tarun |
| 3 | Harini |

| Student ID | Course ID |
|---|---|
| 1 | 1 |
| 1 | 3 |
| 2 | 1 |
| 3 | 2 |

> 🧠 **So how do we reconcile "redundancy is bad" with "replicate everything"?**
> **Normalization removes *accidental, uncontrolled* redundancy inside one dataset. Replication adds
> *deliberate, managed* redundancy across machines.** The first prevents anomalies; the second
> prevents **data loss**. Different problems, opposite answers.

---

## 🛡️ Why We Need Replication

> ⭐⭐ **Replication is the ONLY way that we can protect ourselves from data loss.**

### ACID Durability is not enough
> - **"D" in ACID stands for durability** — any committed transaction will be **persisted on the
>   disk**. So if there's a **power failure**, once the system restarts we will find that transaction
>   in the database; it will not be lost
> - ⭐ **ACID Durability is about persistent vs volatile memory. It does NOT protect you from HDD
>   failures.**
>
> ⭐⭐ **"The only way to prevent data loss in case of HDD failures is replication (have multiple
> copies of the same data across multiple disks)."**

### Replicate across **servers**, not within one
> **There's no point in replicating the data within the same server (useless redundancy)** — we're
> just wasting disk space, and **if the server crashes, we still lose data**.
>
> ⭐ **You always replicate across multiple servers (useful redundancy).**

---

## ⚖️ Replication vs Sharding

| | **Replication** | **Sharding** |
|---|---|---|
| **Definition** | **Having multiple copies of the same data across multiple servers** | **Partition data horizontally across servers** |
| **In one word** | ⭐ **Copying** | ⭐ **Splitting** |
| **Data on different servers** | ⭐ **The SAME data** | ⭐ **DIFFERENT data** |

### Pros
| **Replication** | **Sharding** |
|---|---|
| ⭐ **Minimizes the chances of data loss** (gives you **resilience**) | ⭐ **Allows us to store more data than a single server's capacity** (scaling out) |
| ⭐ **(only) READ throughput is improved**, because you can read from any copy (the read load is distributed equally across all the replicas) | ⭐ **BOTH read & write throughput increase** (the read & write load is distributed equally across all the shards) |

### Cons
| **Replication** | **Sharding** |
|---|---|
| ⭐ **It leads to an increase in data size** — so **capacity is decreased**. If you have **3× replication** (each piece of data copied in 3 places), then your overall data storage capacity has **decreased by 3×** | **Complex** |
| ⭐ **It worsens WRITE throughput** — because you now have to copy the data to multiple places, which means extra writes. *(Note: you can write to the replicas in the background, but you still have to write)* | ⭐ **Requires consistent hashing for routing** |
| ⭐ **You have to worry about keeping the replicas in sync** (consistency troubles) | ⭐ **Risk of fan-out queries** (joins/transactions across shards) |

```
   REPLICATION (copying)                 SHARDING (splitting)
   ─────────────────────                 ────────────────────
   [A B C]  [A B C]  [A B C]             [A]      [B]      [C]
   ✅ survive disk failure               ✅ store more than 1 server holds
   ✅ read throughput ↑                  ✅ read AND write throughput ↑
   ❌ write throughput ↓                 ❌ no cross-shard joins/transactions
   ❌ capacity ÷ 3                       ❌ needs consistent hashing
   ❌ consistency problems               ❌ complex
```

### Which one should we use?
> ⭐ **Both! Together.**
>
> **You have more data than a single server can handle, and you also don't want to lose the data.**
>
> ⭐ **Large systems have both sharding & replication at the same time.**

```
        Shard 1              Shard 2              Shard 3
   ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
   │ A  (primary)  │    │ B  (primary)  │    │ C  (primary)  │
   │ A  (replica)  │    │ B  (replica)  │    │ C  (replica)  │
   │ A  (replica)  │    │ B  (replica)  │    │ C  (replica)  │
   └───────────────┘    └───────────────┘    └───────────────┘
   ⭐ shard for CAPACITY & WRITE throughput; replicate for DURABILITY & READ throughput
```

---

## 🗄️ What About Caching?

> **Caching is kind-of like replication.** In caching, your data is in **2 places**:
> - **database**, and
> - **cache**
>
> ⭐ **It's not pure replication — caching will not save you from data loss, because caches are
> volatile** (they store data in RAM typically).

| Cache | Effect |
|---|---|
| **Doesn't save you from data loss** | because cache is **volatile** |
| **Improves read throughput** | ✅ good |
| ⭐ **Worsens write latency & throughput** | ❌ bad |

> 🧠 **Cache = replication without durability.** You get the read-throughput benefit and the
> consistency headache, but none of the data-loss protection. That's exactly why the CAP reasoning
> from Session 4 (write-through, 2PC) applied to caches too.

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Distributed** | ⭐ **More than 1 server, connected via some network** |
| **State** | ⭐ Data we wish to preserve across requests — **state == data** |
| **Stale read** | Reading an old value after an update |
| **Consistency preconditions** | ⭐ (1) it's about **data**, (2) **multiple copies** exist, (3) a **read follows a write** |
| **Immediate consistency** | Stale reads impossible; needs all copies in sync (or **quorum**); typically 2PC |
| **Eventual consistency** | ⭐ *"every write eventually reflects in all copies"* — **not** "the data becomes consistent" |
| **Read-your-write consistency** | The author sees their own update immediately; others eventually |
| **Data loss** | No consistency ever; only acceptable for analytics/trends |
| **Availability** | ⭐ Whether a **healthy server** can **deny** a **healthy request** |
| **Not low availability** | 4xx/3xx (user's fault) · a crashed server (timeout → retry elsewhere) |
| **Low availability** | ⭐ Healthy server refuses a healthy request (usually: can't sync with replicas) |
| **Network partition** | Some subset of servers can't talk to another subset; ⭐ **a slow network counts** |
| **Partition tolerance** | System **degrades** rather than dying when partitioned |
| **CAP (def 1)** | Pick any 2 of Consistency / Availability / Partition tolerance |
| **CAP (def 2)** ⭐ | **When partitioned, choose A or C — you cannot have both** |
| **A+P** | ⭐ **99%** of systems — social media, most web apps |
| **C+P** | ⭐ **0.9%** — brokers, ticket booking, inventory |
| **A+C** | ⭐ **0.1%** — stock exchanges; not geo-distributed; total shutdown on partition |
| **PACELC** | ⭐ **P**artition → **A** or **C**; **E**lse → **L**atency or **C**onsistency |
| **CRDT** | Conflict-Free Replicated Data Type — powerful, complex; Google Docs uses something similar |
| **Replication** | ⭐ **Copying** — same data on many servers; the **only** protection against disk failure |
| **Sharding** | ⭐ **Splitting** — different data on different servers |
| **Fan-out query** | A query that must hit many shards (joins/transactions across shards) |
| **ACID Durability** | Survives power failure (persistent vs volatile); ⭐ **does NOT survive disk failure** |

---

## 🎯 Session Takeaways

1. **Consistency is only a meaningful question when** it's about data, there are **multiple copies**,
   and a **read follows a write**. Otherwise it's undefined — like the colour of an electron.
2. ⭐ **Eventual consistency means "every write eventually lands everywhere"** — *not* "the system
   becomes consistent and stays that way".
3. ⭐ **Availability in CAP = a healthy server refusing a healthy request.** 4xx errors and crashed
   servers are **not** availability problems.
4. ⭐ **Partitions always exist** at scale — 100% probability. So **P is not optional**, and your real
   choice is **A+P or C+P**.
5. ⭐ **A node being down is not a partition.** Down ⇒ remove and resync. Partition ⇒ both sides alive
   and blind to each other ⇒ **you must choose**.
6. **Partition tolerance means degrading, not surviving intact** — withdrawals blocked while balance
   checks work is still partition tolerant.
7. **99% A+P, 0.9% C+P, 0.1% A+C.** Stock exchanges buy their way out of partitions and shut down
   entirely if one happens.
8. ⭐ **Banks choose A+P and monetise the inconsistency** (overdraft fees) — the consistency decision
   is a **business** decision.
9. ⭐ **PACELC: consistency costs you availability during partitions AND latency all the rest of the
   time.** *"Immediate consistency comes at a huge cost."*
10. ⭐ **Replication = copying** (durability + read throughput, worse writes, ÷N capacity);
    **Sharding = splitting** (capacity + read *and* write throughput, but no cross-shard joins).
11. ⭐ **Replication is the only defence against disk failure** — ACID durability does not protect you.
12. **Real systems use both**, and **a cache is replication without durability**.

---

## ➡️ Next
**[Session 8 — Master-Slave Replication & Tunable Consistency](./08_Master_Slave_and_Tunable_Consistency.md)**
