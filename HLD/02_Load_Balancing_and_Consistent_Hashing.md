# Session 2 — Load Balancing & Consistent Hashing ⚖️

> **Topics:** Load Balancing Algorithms — Round Robin & Consistent Hashing
>
> 📄 Class doc: [\[SST-2028\] Load Balancing & Consistent Hashing](https://docs.google.com/document/d/1ywh8AHebgelMwIWJ1zPQEIbeEavR1F1Y_RBfKizTWKc/edit?usp=sharing)

---

## 📑 Table of Contents
1. [Recap — Load Balancing](#-recap--load-balancing)
2. [IPv4 vs IPv6](#-ipv4-vs-ipv6)
3. [The Real Question](#-the-real-question-which-server)
4. [How to Store the Data?](#-how-to-store-the-data)
5. [Data Sharding & Partitioning](#-data-sharding--partitioning)
6. [Sharding ⟺ Routing](#-sharding--routing-the-key-insight)
7. [What Makes a Routing Algorithm "Good"](#-what-makes-a-routing-algorithm-good)
8. [Algorithm 1 — Round Robin](#1-algorithm-1--round-robin)
9. [Algorithm 2 — Bucketing](#2-algorithm-2--bucketing)
10. [Algorithm 3 — Mapping Table](#3-algorithm-3--mapping-table)
11. [Algorithm 4 — Consistent Hashing](#4-algorithm-4--consistent-hashing)
12. [Hash Functions](#-hash-functions)
13. [The Hash Ring](#-the-hash-ring)
14. [The Consistent Hashing Algorithm](#-the-consistent-hashing-algorithm)
15. [Implementation](#-implementation)
16. [Verifying the Four Properties](#-verifying-the-four-properties)
17. [Comparison Table](#-the-full-comparison)
18. [Key Terms Recap](#-key-terms-recap)

---

## 🔄 Recap — Load Balancing

### Purpose
1. **Provide a unified view of the entire backend system to the end user** — because the end user
   doesn't care which exact server handles their request.
2. **Distribute the load (requests / data) equally** across the other app/db servers.

### Resources
- How to configure: [LB configuration doc](https://docs.google.com/document/d/1DxQzLpu1XPe_mRWsewNWtKL6E4uwKHQhBp7GX6Sg7qI/edit#heading=h.fzwcs020kou5)
- Tutorial: https://avinetworks.com/what-is-load-balancing/
- AWS Elastic Load Balancer: https://aws.amazon.com/elasticloadbalancing/getting-started/

---

## 🔢 IPv4 vs IPv6

Example address: `142.250.192.4`

### IPv4
```
IPv4:  0-255  .  0-255  .  0-255  .  0-255

total number of possibilities = 2^8 × 2^8 × 2^8 × 2^8 = 2^32 ≈ 4 billion
number of devices on the internet = 100 billion – 1 trillion
```
> ⭐ **The problem is immediate:** ~4 billion addresses for 100 billion – 1 trillion devices.

### How we cope today
| Mechanism | Effect |
|---|---|
| **Static IPs** | Permanently assigned — needed for servers, so clients can always find them |
| **Dynamic IPs** | Assigned temporarily from a pool (DHCP) — fine for your laptop/phone, which only *initiates* connections |
| *(also: NAT / private ranges)* | Many devices share one public IP |

### IPv6
```
IPv6: 128 bits
Number of possibilities = 2^128 ≈ 256 billion billion billion billion
```

> 💡 **Why this belongs in a load-balancing lecture:** the LB routes on the address in the request.
> Understanding that a client's IP may be **dynamic** (and shared via NAT) tells you why routing on
> *client IP* is fragile, and why we route on something stable like **`user_id`** instead.

---

## ❓ The Real Question: Which Server?

> **Q: Which server should a particular request be sent to?**

> ⭐ **To understand this, we first must understand how the data is distributed across the various
> servers.** Because otherwise, we will end up sending the requests to servers which **don't
> contain the appropriate data** (Sanjana's request gets sent to a server which contains Ashok's
> data).

```
   ❌  Sanjana's request ──▶ LB ──▶ Server B
                                     └── contains ASHOK's data
                                         → cannot answer!
```

This is the central realisation of the session: **routing and data placement are the same problem.**

---

## 💾 How to Store the Data?

> **Q: Can we store all the data on 1 server?**
> **No.** We got multiple laptops **because we were running out of resources** (disk space / CPU / …).

> **Q: Should we split the data randomly?**
> - **How will we retrieve it?**
> - ⭐ **The data storage has to follow some logic — that can be repeated.**
> - ⭐ **We should be able to find out at any time, which data is stored in which server.**

So the placement rule must be **deterministic** and **recomputable** — not random, and ideally not
stored in a lookup table that has to be kept in sync (we'll see why in Algorithm 3).

---

## ✂️ Data Sharding & Partitioning

Partitioning comes in four flavours — two axes (**vertical / horizontal**) × two scopes
(**within one DB / across servers**):

### Within a single database

| Type | Why? |
|---|---|
| **Vertical Partitioning (Normalization)** | Because you want to **normalize** it — split a wide table into related tables |
| **Horizontal Partitioning** | • **improve indexing performance**<br>• **support multi-tenancy** (prevent data cross-communication between clients) |

```
   VERTICAL PARTITIONING (split by COLUMNS)
   ┌──────────────────────────────┐      ┌────────────┐  ┌──────────────┐
   │ id │ name │ password │ bio   │  →   │ id │ name  │  │ id │password │
   │    │      │          │       │      │    │ bio   │  │    │         │
   └──────────────────────────────┘      └────────────┘  └──────────────┘

   HORIZONTAL PARTITIONING (split by ROWS)
   ┌──────────────────┐      ┌──────────────┐  ┌──────────────┐
   │ users 1 … 1000   │  →   │ users 1..500 │  │ users 501..  │
   └──────────────────┘      └──────────────┘  └──────────────┘
```

### Across servers

| Type | Why? |
|---|---|
| **Vertical Partitioning (across servers)** | **Migrate to microservices / separation of concerns** — the users table on one service, bookmarks on another |
| **Horizontal Partitioning (across servers)** | ⭐ **All the data cannot fit on a single server** |

### Sharding

> ⭐ **Sharding is simply "Horizontal Partitioning across servers".**
>
> **Sharding Key** — sharding is always based on some value: the **sharding key**.

> *How to choose a good sharding key — we will see this in a later lecture* → **Session 9**.

---

## 🔗 Sharding ⟺ Routing (the key insight)

> ⭐ It should **not** be the case that sharding follows logic A, but routing follows logic B.
>
> **Why?** Because if that is the case — then the requests will end up on servers that **don't
> contain the necessary data!**
>
> **The logic / algorithm must be the same for both sharding & routing.**

Therefore:

> ⭐⭐ **All we have to do is use a Routing Algorithm. Sharding happens via Routing.**
> **Routing is the thing that happens — sharding is just a side effect of routing!**

If we're routing based on `user_id`, then **automatically the sharding will happen based on
`user_id`**. Because if Sanjana's requests are being routed to server A, then **only server A will
be able to store Sanjana's data** — server B / C never received requests with Sanjana's data in the
first place!

```
   We only decide:            (which request  →  which server)
                                       ⇓
   And by doing that we have
   automatically decided:     (which data     →  which server)
```

> 🧠 **This is the mental model to carry forward.** You don't design "sharding" and "routing" as two
> systems. You design **one routing function**, and data placement falls out of it for free.

---

## ✅ What Makes a Routing Algorithm "Good"

The five requirements. Every algorithm below is judged against exactly these.

| # | Property | Why it matters |
|---|---|---|
| **1** | **Fast** | Computationally easy to decide which request goes to which server — it runs on **every single request** |
| **2** | **Equal distribution** | Should divide the load (**data & requests**) equally across all servers |
| **3** | **Freely add/remove servers** | Servers are unreliable → they **crash**, so server count can **decrease**. We might need to scale out → server count can **increase** |
| **4** | ⭐ **Minimal data movement** | When the number of servers changes, the data movement must be **minimal** |
| **5** | ⭐ **Deterministic without exchanging information** | We have **multiple LBs**. All LBs must always be **"in-sync"** — they must forward the same type of requests (say Sanjana's) to the **same** server, otherwise Sanjana's data will be all over the place. **But they must not have to constantly communicate** with each other to stay in sync — constant communication for every request is too much overhead |

> ⭐ **Property 5 is the one people forget**, and it's the one that kills the "obvious" solution
> (Algorithm 3).

Routing algorithms **run inside the Load Balancers**.

---

## 1️⃣ Algorithm 1 — Round Robin

> **Send the next request to the next server.** Simple `%`-based technique.

```python
server_list = ["10.11.6.12", "10.11.5.17", ...]

fn handle_request(request):
    key = request.user_id
    N = len(server_list)
    server_id = key % N
    server = server_list[server_id]
    forward_request(request, server)
```

### Initial distribution
```
server_list = [A, B, C, D]      n = 4
user_id     = 0 … 100

A   0   4   8    …
B   1   5   9    …
C   2   6   10   …
D   3   7   11   …
```
Beautifully even. Now watch what happens on failure.

### Adding / removing servers — the disaster

**Server B crashes** → `N` becomes 3:
```
A   0   3   6   9    …
B   ✗
C   1   4   7   10   …
D   2   5   8   11   …
```

Analysis:
- Users **(1, 5, 9, …)** were previously on server B, so **of course their data has to be
  migrated** — that's unavoidable and expected.
- ⭐ **However, other users' data should not have to be migrated needlessly** — their servers are
  still working, there's no need to move their data!

> **Is that the case?**
> ⭐ **No! Pretty much all the data gets shuffled around.**

Trace a few users to see it:

| user_id | before (`% 4`) | after (`% 3`) | moved? |
|---|---|---|---|
| 0 | A | A | no |
| 1 | **B** | C | yes *(unavoidable)* |
| 2 | C | D | ⚠️ **needless** |
| 3 | D | A | ⚠️ **needless** |
| 4 | A | C | ⚠️ **needless** |
| 5 | **B** | D | yes *(unavoidable)* |
| 6 | C | A | ⚠️ **needless** |
| 7 | D | C | ⚠️ **needless** |

> Similarly, **when we add servers**, once again the value of `N` will change, and the value of
> `(user_id % N)` will also change for **pretty much everyone**.

### Verdict
| ✅ Pros | ❌ Cons |
|---|---|
| **Fast** | ⭐ **Lots of unnecessary data movement!** |
| **Equal distribution** | |
| **No need for syncing information** | |

> ⭐ **The root cause:** `key % N` makes the result depend on **N**. Change N and you change the
> answer for **almost every key**. Fixing this is the entire motivation for consistent hashing.
>
> 💡 **In practice**, "Round Robin" as used by a *stateless* LB (just cycle through servers, ignore
> the key) is perfectly fine — because there's no data to move. It only becomes a catastrophe when
> the routing decision also determines **data placement**, which is exactly our case.

---

## 2️⃣ Algorithm 2 — Bucketing

> **Assign the server → `user_id` in ranges.**

```
A  will get user_ids    0 …  99
B  will get user_ids  100 … 199
C  will get user_ids  200 … 299
D  will get user_ids  300 … 399

total users = 400
```

### Adding / removing servers

**If server B crashes** — the ranges must be recomputed across 3 servers:
```
A  will get user_ids    0 … 132
C  will get user_ids  133 … 265
D  will get user_ids  266 … 399
```
Users 100–132 move to A, 200–265 move to C, 300–399 move to D… **enormous re-shuffling** again.

### More users sign up
> ⭐ **We cannot accommodate new users in existing servers** — because we have **already decided the
> buckets**. So it is **impossible to add new users without first buying more servers.**

This is the fatal flaw: the scheme is defined over a **fixed, known key space** (0–399). Real
systems have an **unbounded, growing** key space.

### Verdict
| ✅ Pros | ❌ Cons |
|---|---|
| **Equal data distribution** | **Too much data re-shuffling** |
| **Fast** | ⭐ **Cannot even add users** |

---

## 3️⃣ Algorithm 3 — Mapping Table

> **What if the LB maintains a Hashmap from `user_id` → `server_id`?**

```python
server_list = ["10.11.6.12", "10.11.5.17", ...]

mapping = {
    sanjana: A,
    prem:    B,
    bathula: A,
    pallavi: C,
    venkat:  B,
    ...
}

fn handle_request(request):
    key = request.user_name
    server = mapping[key]
    forward_request(request, server)
```

### Adding / removing servers / users

```python
fn handle_server_crash(crashed_server):
    for user, server in mapping:
        if server == crashed_server:
            # assign a new server to this user
            new_server = get_random_server()
            mapping[user] = new_server
            migrate(user, crashed_server, new_server)

fn handle_new_user(user):
    server = get_random_server()
    mapping[user] = server
```

Now check the migration behaviour:

| Question | Answer |
|---|---|
| Will the data of people that were earlier on the crashed server get moved? | **Yes** — *and that is desired* |
| For users whose servers are still running, will their data get moved? | ⭐ **No!** |

So it **nails property 4** (minimal data movement) — the thing Round Robin and Bucketing both failed.

### But… ⭐

| ✅ Pros | ❌ Cons |
|---|---|
| **Equal data distribution** | ⭐ **We will have to keep this mapping table in sync for ALL the LBs** |
| **Fast** (O(1) hashmap lookup) | If different LBs have a different mapping table, **the requests will end up in random servers!** |
| **Minimizes data movement** | |

> ⭐⭐ **"Keeping data in sync, always, with very low latency ⇒ extremely hard problem.
> IMPOSSIBLE!"**

This is **property 5** failing. And note the irony: keeping a small table consistent across N
load balancers is *the very same distributed-consistency problem* we're trying to solve for user
data. We'd have to solve distributed consensus just to route a request. (You'll meet exactly this
problem again in **Session 7 — CAP**.)

```
   LB-1: {sanjana: A}          LB-2: {sanjana: C}
             │                          │
             ▼                          ▼
        Server A                    Server C
     (has her data)             (has nothing!)  ← 💥
```

---

## 4️⃣ Algorithm 4 — Consistent Hashing

> **Pros: All of the above!**
> - **Fast**
> - **Equal load distribution**
> - **Freely add/remove servers**
> - **Minimal data movement**
> - **No need for any sync between LBs**
>
> **Cons: None!**

That's the claim. The rest of the session earns it.

---

## 🔢 Hash Functions

### First: what is a *function*?
> A function is a **deterministic** mapping from inputs to outputs.

```python
fn add(a, b):
    return a + b

add(2, 3)  => 5
add(2, 3)  => 5
add(2, 3)  => 5
```
> **No matter how many times I call a function, it will always give me the same result for the same
> input.**

**Counter-example — a procedure with side effects:**
```python
state = 0
fn proc add(a, b):
    state = b
    return a + b + state
```
> In this case the **procedure** (impure function) **doesn't always return the same value** —
> because it has **side effects**.

> ⭐ Determinism is the property we're about to depend on completely.

### Now: a hash function
> A hash function is a **"digest" function** — a function that takes as input **anything**, but
> returns values within a **fixed range**.

```python
fn hash_1(data):
    return (sum of ascii values of chars of data) % 100

fn hash_2(data):
    return (sum of squares of ascii values of chars of data) % 799

fn hash_3(data):
    return (multiply even and odd numbers in the data) % 1337
```
> In `hash_1`'s case, **no matter what the data, the output will always be from 0 … 99.**

### Resources
- Definitions and properties: https://en.wikipedia.org/wiki/Hash_function
- Cryptographically secure (extra guarantees): https://en.wikipedia.org/wiki/Cryptographic_hash_function
- Family of hashes: https://en.wikipedia.org/wiki/Universal_hashing
- K-independent hashing: https://en.wikipedia.org/wiki/K-independent_hashing

---

## 💠 The Hash Ring

> ⭐ **Hash Ring = the output space of a given hash function.**

If `hash()` outputs `0 … 2^64 - 1`, imagine that range **bent into a circle**, so that the value
after `2^64 - 1` wraps back around to `0`.

```
                        0 / 2^64-1
                        ╭───────╮
                    ╭───╯       ╰───╮
                  ╭─╯               ╰─╮
                 │                     │
       2^64·¾    │                     │   2^64·¼
                 │                     │
                  ╰─╮               ╭─╯
                    ╰───╮       ╭───╯
                        ╰───────╯
                        2^64 · ½
```

### Placing users & servers on the ring

| Entity | Hash functions used |
|---|---|
| **Users** | **1** hash function — `hash_0` |
| **Servers** | ⭐ **k** hash functions — `hash_1 … hash_k`. **Typical value of k is 32 or 64** |

Critical setup details:
- These hash functions are **set up while the LB is being coded/configured**.
- ⭐ **All the LBs for a system will have the same set of hash functions in their code.**
- All these **(k+1)** hash functions have the **same output space** (say `0 … 2^64 - 1`).

### Why k copies of each server?
Each server appears at **k random points** on the ring instead of one. This is what produces
**even distribution** — with a single point per server, random placement leaves some servers owning
huge arcs and others owning slivers. With k = 32 or 64 points each, the arcs average out.

*(Terminology note: these k points are what other systems call **virtual nodes / vnodes**. The
Cassandra paper calls the alternative approach "nodes get assigned to multiple positions in the
circle (like in Dynamo)".)*

### Collisions?
> Suppose our hash function outputs values in the range `0 … (2^64 - 1)`.
> **Given 1 billion users, and 1 million servers, what is the probability that two hashes collide?**
> ⭐ **This probability will be very close to 0.**

The space is ~1.8 × 10^19 slots; ~10^9 users and ~10^6 × 64 server points barely occupy it.

---

## ⚙️ The Consistent Hashing Algorithm

> 1. For **each server** we have, hash it using **all the hash functions `hash_1 … hash_k`** and
>    **put the server on the ring**.
> 2. Whenever a **request arrives**, hash the **`user_id`** using **`hash_0`** and place the user
>    on the ring.
> 3. ⭐ **The request will be forwarded to the first server on the ring which is in the clockwise
>    direction.**

```
                       0
                    ╭──────╮
              [A]╭──╯      ╰──╮[C]        Sanjana hashes here ──┐
               ╭─╯              ╰─╮                             │
              │      ← clockwise   │                            ▼
        [B]   │                    │  ● Sanjana  ──clockwise──▶ [C]
              │                    │
               ╰─╮              ╭─╯[A]
              [C]╰──╮      ╭──╯[B]
                    ╰──────╯
                    (each server appears k times)
```

### Why does removing a server only move *its* keys?

```
   BEFORE (B crashes)                    AFTER
   … ──[A]── u1 u2 ──[B]── u3 u4 ──[C]…  … ──[A]── u1 u2 ──✗── u3 u4 ──[C]…
              ↑              ↑                        ↑         ↑
        u1,u2 → B      u3,u4 → C            u1,u2 now walk clockwise → C
                                            u3,u4 → C  (UNCHANGED)
```
⭐ Only the users **in the arcs that B owned** move — and they move to **the next server
clockwise**. Every other user's answer is **completely unaffected**, because their nearest
clockwise server never changed. **This is property 4, achieved by construction.**

Adding a server is the mirror image: the new server steals a slice of the arcs it lands in, and
**nothing else moves**.

---

## 💻 Implementation

The class implementation, using binary search over a sorted ring:

```python
import bisect

def custom_hash(data, i):
    h = sum(ord(c) ** i | 0xaff for c in data)
    h *= 3
    h >>= 1
    return h % 10

def build_ring(servers, k):
    ring = []
    for server in servers:
        for i in range(1, k+1):  # 1..k
            h = custom_hash(server, i)
            print(f'adding {server} to spot {h}')
            ring.append((h, server))

    ring = sorted(ring)
    print('final ring:', ring)
    return ring

def route(user):
    user_hash = custom_hash(user, 0)

    # I now need to find the 1st server in the ring
    # that is to the right of the user
    index = bisect.bisect_right(ring, (user_hash, user))
    index = index % len(ring)  # wrap it around the ring
    server_hash, server = ring[index]
    print(f'{user} hashed to {user_hash}. Routing them to {server} at location {server_hash}')
    return server

servers = [
    '10.11.1.13',
    '10.11.2.17',
    '10.11.13.167',
    '10.11.12.255',
    '10.11.1.0',
]
ring = build_ring(servers, 3)

route('Vishal')
route('Vishal')
route('Sanjana')
route('Vishal')
route('Sanjana')
route('Sanjana')
```

**Reading the code:**
| Line | What it does |
|---|---|
| `custom_hash(data, i)` | A **family** of hash functions — the parameter `i` selects which one. `i=0` is used for users, `i=1..k` for servers |
| `build_ring(servers, k)` | Places each server at **k** points, then **sorts** → the ring is just a sorted array of `(hash, server)` |
| `bisect_right` | ⭐ Binary search for the **first ring entry to the right** of the user's hash |
| `index % len(ring)` | ⭐ **Wraps around** — if the user hashed past the last server, the answer is the *first* server (the ring closes) |

> ⚠️ Note `% 10` in `custom_hash` — that tiny output space is deliberate for a classroom demo (so
> you can see collisions and wrap-around). Production uses a 64-bit or 128-bit space
> (MD5/SHA-1/MurmurHash), where collisions are effectively impossible.

---

## ✅ Verifying the Four Properties

### Is the algorithm deterministic?
> *Will Sanjana always go to server C (as long as Sanjana is alive, and server C is running, and no
> servers are added/removed)?*
> ⭐ **Yes!**

Because hashing is deterministic and the ring is derived purely from the server list.

### Is the algorithm fast?
> ⭐ **Yes!** The ring is a **sorted array**, and to find the nearest server in the clockwise
> direction, you have to do a **binary search (upperbound)** for the user's hash.
>
> **O(log(N·k))** — where **N** is the number of servers and **k** is the number of server hashes.

For N = 1,000,000 servers and k = 64: `log₂(64,000,000)` ≈ **26 comparisons**. Trivial per request.

📖 Further reading: https://arpitbhayani.me/blogs/consistent-hashing/

### Do the LBs have to share any data to be in sync?
> ⭐ **No!**
> - Each LB knows **which servers are running** (via health-check / heartbeat — Session 1)
> - **The code in each LB is the exact same**
> - So **each LB will calculate the same hashes and the same ring**
> - So **each LB will calculate the same server for any user**

```
   LB-1  ──┐   same hash functions (in code)
   LB-2  ──┼──▶ same server list (from healthchecks) ──▶ SAME RING ──▶ same answer
   LB-3  ──┘
              ⭐ zero coordination messages
```
> ⭐ **This is the property that made the Mapping Table impossible and makes consistent hashing
> work.** The "shared state" is replaced by **shared *code* + shared *observation***, both of which
> are free.

### Is the data distribution even?
This is where the class doc ends — it's the natural next question, and the answer is **"yes, because
of k"**:

| k (points per server) | Distribution quality |
|---|---|
| **1** | Poor — random arcs, some servers get 5× the load of others |
| **32 – 64** ⭐ | Good — the law of large numbers averages the arcs out |
| Very large | Marginally better, but the ring gets big and lookups slower |

Two refinements worth knowing:
- **Weighted nodes** — give a beefier server **more** points on the ring, so it takes
  proportionally more load. (Handles the *heterogeneous hardware* problem from Session 1.)
- **Load-based token movement** — instead of more points, actively move lightly-loaded nodes on the
  ring to relieve heavily-loaded ones. *(This is the approach Cassandra chose, "as it makes the
  design and implementation very tractable".)*

---

## 📊 The Full Comparison

| Property | **Round Robin** | **Bucketing** | **Mapping Table** | **Consistent Hashing** |
|---|:---:|:---:|:---:|:---:|
| **1. Fast** | ✅ | ✅ | ✅ | ✅ `O(log Nk)` |
| **2. Equal distribution** | ✅ | ✅ | ✅ | ✅ *(needs k = 32–64)* |
| **3. Freely add/remove servers** | ✅ | ⚠️ | ✅ | ✅ |
| **4. Minimal data movement** | ❌ **everything moves** | ❌ **massive reshuffle** | ✅ | ✅ **only ~1/N moves** |
| **5. No sync between LBs** | ✅ | ✅ | ❌ **IMPOSSIBLE** | ✅ |
| **Can add new users** | ✅ | ❌ **no** | ✅ | ✅ |
| **Verdict** | Fails #4 | Fails #4 and can't grow | Fails #5 | ⭐ **All five** |

### The one-line story of the session
```
key % N          →  breaks because the answer depends on N
fixed ranges     →  breaks because the key space is fixed
a lookup table   →  breaks because tables must be kept in sync
a hash RING      →  the answer depends only on (this key, the servers that are alive)
                    …and every LB can compute that independently. ✅
```

---

## 🌍 Where You'll Meet Consistent Hashing Again

| System | Use |
|---|---|
| **Cassandra / DynamoDB / Riak** | Partitioning rows across nodes on a ring |
| **Memcached / Redis clients** | Choosing which cache node holds a key → **Session 3** |
| **CDNs** | Mapping content to edge servers (the original 1997 Karger et al. paper was about exactly this — *"Consistent hashing and random trees: Distributed caching protocols for relieving hot spots on the World Wide Web"*) |
| **Load balancers** | Sticky routing without a state table |
| **Kubernetes / service meshes** | Session affinity for upstream selection |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **IPv4 / IPv6** | 32-bit (~4 billion) vs 128-bit (~2^128) address spaces |
| **Static vs Dynamic IP** | Permanently assigned (servers) vs assigned from a pool (clients) |
| **Vertical Partitioning** | Split by **columns** — normalization, or separation of concerns across services |
| **Horizontal Partitioning** | Split by **rows** — indexing performance, multi-tenancy |
| **Sharding** | ⭐ **Horizontal partitioning across servers** |
| **Sharding key** | The value sharding is based on (e.g. `user_id`) |
| **Sharding ⟺ Routing** | ⭐ Same algorithm must drive both; **sharding is a side effect of routing** |
| **Round Robin** | `key % N` — fast and even, but **N changes ⇒ everything moves** |
| **Bucketing** | Fixed key ranges per server — can't grow, huge reshuffles |
| **Mapping Table** | Explicit key→server hashmap — perfect except **it can't be kept in sync** |
| **Hash function** | Deterministic "digest": any input → fixed output range |
| **Deterministic** | Same input always gives the same output (no side effects) |
| **Hash Ring** | ⭐ The output space of a hash function, bent into a circle |
| **k** | Number of hash functions used per server; **typically 32 or 64** |
| **Virtual node (vnode)** | One of a server's k points on the ring |
| **Clockwise rule** | A key belongs to the **first server clockwise** from its hash |
| **Consistent Hashing** | Ring-based routing: `O(log Nk)`, even, minimal movement, **zero LB coordination** |

---

## 🎯 Session Takeaways

1. **Routing and data placement are one problem.** Decide which server serves a request, and you
   have decided which server stores its data.
2. **Sharding = horizontal partitioning across servers**, always based on a **sharding key**.
3. ⭐ **Sharding is a side effect of routing** — so design the routing algorithm, not two systems.
4. A good routing algorithm needs **five** properties; the fifth (**no coordination between LBs**)
   is the one that eliminates the obvious solutions.
5. `key % N` fails because **the answer depends on N** — change N and nearly every key remaps.
6. **Bucketing** additionally can't accept new users without buying hardware.
7. **Mapping tables** are perfect except that keeping them in sync across LBs is *the* hard problem
   of distributed systems — *"IMPOSSIBLE"*.
8. ⭐ **Consistent hashing** puts servers at **k (≈32–64) points** on a **ring** and sends each key
   to the **first server clockwise**.
9. Removing a server moves **only its own arcs' keys** (~1/N of data); everything else is untouched.
10. ⭐ LBs stay in sync with **zero messages** — same code + same healthcheck view ⇒ same ring ⇒ same
    answer. Lookup is `O(log(N·k))`.

---

## ➡️ Next
**[Session 3 — Caching – 1](./03_Caching_Hierarchy_and_Types.md)** — the caching hierarchy
(browser → CDN → backend), local vs global caches, and the two hard problems: eviction and
invalidation.
