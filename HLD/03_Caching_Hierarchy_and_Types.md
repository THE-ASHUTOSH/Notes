# Session 3 — Caching – 1: Hierarchy & Types 🗄️

> **Topics:** The Caching Hierarchy: Browser, CDN, Backend · Types of backend caches: Local vs
> Global, Single vs Distributed · Challenges with Caching — Eviction & Invalidation
>
> 📄 Class doc: [\[SST-2028\] Intro to Caching](https://docs.google.com/document/d/1wCMktm6Yh_XHoN5o0YvDsRLMYPGBIYpAs3B6jn4oYes/edit?tab=t.0)
> 📝 Assignment: [HLD101 Assignment: Search Typeahead](https://docs.google.com/document/d/1GyQX3dNrcq5YlBiAxq9MNzS9wPwu_ZmRslAEjvhw8Bo/edit?tab=t.0)

---

## 📑 Table of Contents
1. [Need for Caching](#-need-for-caching)
2. [The Human Brain is Hierarchical](#-the-human-brain-is-hierarchical)
3. [Computer Memory Hierarchy](#-computer-memory-hierarchy)
4. [Why Memory Must Be Hierarchical](#-why-memory-must-be-hierarchical)
5. [Web Memory Hierarchy](#-web-memory-hierarchy)
6. [Browser Cache](#1-browser-cache-client-side)
7. [CDN](#2-cdn--content-delivery-network)
8. [The Latency Physics](#-the-latency-physics-why-distance-costs)
9. [Finding the Nearest Edge](#-finding-the-nearest-edge-server)
10. [Are CDNs Databases?](#-are-cdns-databases)
11. [How the CDN Gets the Data](#-how-does-the-cdn-get-the-data-in-the-first-place)
12. [When Does the CDN Actually Cache?](#-when-does-the-cdn-actually-cache)
13. [Backend Cache: Local vs Global](#3-backend-cache)
14. [Single vs Distributed](#-single-vs-distributed-global-caches-only)
15. [Routing Algorithm for a Distributed Cache](#-routing-algorithm-for-a-distributed-cache-)
16. [Challenges with Caching](#-challenges-with-caching)
17. [Key Terms Recap](#-key-terms-recap)

---

## ☕ Need for Caching

### Making Tea

Think about how you make tea. You don't walk to the shop for sugar, then walk back for tea leaves,
then walk back for milk. You keep a **small set of frequently-used things within arm's reach** on
the kitchen counter, and the bulk supply in a cupboard or the shop.

That's a cache:
- **Small** — the counter can't hold a warehouse
- **Fast** — arm's reach vs a trip to the shop
- **Holds what you use often** — not everything
- **Not the source of truth** — the shop is

> ⭐ Every caching decision in this course is a variation on: *what do I keep on the counter?*

---

## 🧠 The Human Brain is Hierarchical

| Memory type | Speed | Capacity | Durability | Access |
|---|---|---|---|---|
| **Working memory** | **extremely fast** | only **4–7 items** | volatile | **random access** |
| **Short term memory** | **very fast** | thousands of items | volatile (slightly longer — **up to weeks**) | **random access** |
| **Long term memory** | **extremely slow** | practically **unlimited** | **permanent** | **sequential access** |

- When you go to sleep (**REM**), your brain **consolidates your short-term memory into long-term
  memory**.

> ⭐ **Even biological memory is hierarchical!**

Notice the pattern already: as capacity goes **up**, speed goes **down**, and access shifts from
**random** to **sequential**. That exact trade-off repeats in silicon.

---

## 💻 Computer Memory Hierarchy

| Level | Detail |
|---|---|
| **CPU Registers** | ⭐ **This is what the CPU actually interacts with.** Very small (**few bytes**). Registers work at **clock-tick speed** — **0.2 ns** per access (**5 billion ops/sec**) |
| **Cache (inside the CPU) — L1, L2, L3** | **L1, L2** exist **per core**. **L3** is **shared across all CPU cores** |
| **Main memory (RAM)** | Almost **500× – 1000× slower** than CPU registers. **100 ns** traditionally; modern **DDR4** RAMs have a random read latency of **~10 ns** |
| **HDD (magnetic disk drive)** | ⭐ **100,000× slower than RAM** |

```
        SPEED                                              CAPACITY
          ▲                                                    │
          │   ┌──────────────────┐  0.2 ns   few bytes          │
   fastest│   │  CPU REGISTERS   │                              │
          │   ├──────────────────┤                              │
          │   │  L1 / L2 (per    │  ~1-10 ns  KBs               │
          │   │  core), L3       │                              │
          │   │  (shared)        │                              │
          │   ├──────────────────┤                              │
          │   │  RAM             │  10-100 ns  GBs              │
          │   ├──────────────────┤                              │
          │   │  SSD             │  ~100 µs    TBs              │
          │   ├──────────────────┤                              ▼
   slowest│   │  HDD             │  ~10 ms     TBs-PBs      largest
          ▼   └──────────────────┘
```

**Reference:** *Latency Numbers Every Programmer Should Know*

> 💡 **Session 1 connection:** these numbers are why `sorted(data)` on 50 PB is hard. The data
> physically cannot sit in the fast layers.

---

## 📐 Why Memory Must Be Hierarchical

The reasoning from the class doc:

1. **Memory is always hierarchical.**
2. **Larger memory storages will be slower compared to smaller ones.**
3. ⭐ **If you have to produce a lot of something, you will use cheaper technology** — because
   *registers of the size of RAM would be way too expensive*.
4. **Larger storages are typically slow in sequential access and *ultra* slow in random access.**
5. **Smaller storages are generally faster and have better random access.**

> ⭐ **Therefore, you have a need for caching.**

Caching is not an optimisation bolted on afterwards — it is the **inevitable consequence** of the
fact that fast memory is expensive and therefore small.

📖 Further: *Optimizing code for efficient cache usage* (cache lines, locality of reference)

---

## 🌐 Web Memory Hierarchy

The same hierarchy exists across the internet:

```
   ┌──────────────┐   ┌──────────────┐   ┌───────────────────────────┐   ┌──────────┐
   │   BROWSER    │──▶│     CDN      │──▶│   BACKEND (app + cache)   │──▶│    DB    │
   │ (client side)│   │ (3rd party)  │   │                           │   │ (truth)  │
   └──────────────┘   └──────────────┘   └───────────────────────────┘   └──────────┘
     fastest,           close to           Redis / local RAM              slowest,
     tiny, per-user     the user                                          complete
```

Each layer answers what it can, and only the misses fall through.

---

## 1️⃣ Browser Cache (client side)

### Not accessible to the frontend dev
| Cache | Notes |
|---|---|
| **DNS cache** | Inspect it at `chrome://net-internals/#dns` |
| **File / Media Cache** | Images, JS, CSS, fonts cached by the browser itself |

### Accessible to the frontend dev
| Store | Capacity |
|---|---|
| **Cookies** | **4 KB** |
| **Session Storage** | **5 MB** |
| **Local Storage** | up to **10 MB** |
| **IndexedDB** | up to **10 GB** |

> 💡 Note the hierarchy *within* the browser too — Cookies are tiny but sent with every request;
> IndexedDB is huge but requires an async API. Same trade-off shape again.

---

## 2️⃣ CDN — Content Delivery Network

**Providers:** Akamai, Fastly, Cloudflare, CloudFront, Cloudinary, …

> ⭐ **CDNs are the backbone of the internet.**
>
> **CDNs are neither client side, nor backend side. They're a 3rd party service (like DNS).**

### What type of data does a CDN cache?
> **Large (> 10 KB), mostly static (changes rarely) data**
> - **multimedia:** images, audio, videos, pdfs, zip, …
> - **code:** js, html, css

> ⭐ **Any user-content (images / videos / reels / avatars uploaded by the users) will be served via
> CDNs.**

### What problem do CDNs solve?
> **They act as a cache + they reduce latency.**

---

## 🌍 The Latency Physics (why distance costs)

The class worked this out from first principles. Scaler's servers are in **Mumbai** (AWS South East
Asia); imagine you're in the **US** watching a lecture recording.

```
circumference of earth        = 40,000 km
speed of light (vacuum)   c   = 299,792,458 m/s  ≈ 3 × 10^8 m/s
speed of light in FIBRE        ≈ 2 × 10^8 m/s     ← slower inside the cable!

round trip time (India → US → India):

    40,000 km / (2 × 10^8 m/s)
  = 4 × 10^4 × 10^3 m / (2 × 10^8 m/s)
  = 4 / 20  seconds
  = 200 ms
```

> ⭐ **It takes at least 200 ms for a packet to make the US–India–US trip** — and *in reality it
> will be closer to **500–600 ms***.

> ⭐ **This is a hard physical floor.** No amount of faster servers, better code, or bigger machines
> fixes it. The only fix is **to be closer**.

### It isn't just latency — bandwidth suffers too
> Also, if you're fetching data from far away, **the bandwidth will also be slower**:
> - **multiple hops** — your bandwidth is limited by the **slowest server in the route** the data takes
> - **intercontinental fibre optic cables** handle trans-Atlantic / trans-Pacific data — they connect
>   continents & countries, and **all** network traffic across continents travels over these cables
> - ⭐ **these cables are a bottleneck**

### Definitions
| Term | Definition |
|---|---|
| **Bandwidth** | **Bytes / second** — how *much* data per unit time |
| **Latency** | **Delay between sending the request and receiving a response** |

> 🧠 Analogy: bandwidth is the **width of the pipe**; latency is the **length of the pipe**.

### The solution
> *What if instead of streaming the video from the Indian servers, you could get that video from a
> server near your home!*
> - **very low latency** (a few ms)
> - **bandwidth will be much higher**

| Term | Meaning |
|---|---|
| **Edge** | **Close to the user** |
| **Edge-node / edge-server** | ⭐ A server which is **(physically / geographically) close to the user** |

> If we could purchase **1,000,000 servers** and place them all across the globe to act as caches,
> we could serve the data from a server closer to the user.
>
> ⭐ **This is what CDNs do!** CDNs provide a **global infrastructure of edge-nodes**. They
> **rent out** these servers to whoever wants to use them.

> ⭐ **CDNs handle almost 70% of all the traffic on the internet!**

---

## 📍 Finding the Nearest Edge Server

> **Q: How can you find the IP address of the nearest CDN server (edge server)?**

| Mechanism | How it works | Catch |
|---|---|---|
| **GeoDNS** | A special type of DNS that can **resolve the closest IP address based on the user's geographical location** | ⚠️ **Low penetration** — the *majority of DNS servers do not support the GeoDNS protocols* |
| **AnyCast** | A **custom redirect that the CDNs provide** to send you to the nearest server | The practical mainstream answer |

*(AnyCast works by advertising the **same IP address** from many locations; internet routing
naturally delivers your packets to the topologically nearest one.)*

📖 https://www.cloudflare.com/learning/cdn/glossary/anycast-network/

---

## 🗃️ Are CDNs Databases?

> **No — they're a cache.** They don't **"store"** the data, they just **temporarily hold** it to
> **"serve"** it to the clients.
>
> ⭐ **Any data that you add to a CDN must be backed by a file storage service like S3.**

### Can our backend servers access the CDN?
> **No.** The backend server will access it **directly from the file storage (like S3)**.
> ⭐ **CDNs are client-facing. CDNs are accessed only by the clients.**
>
> *Note: there's nothing stopping our backend server from making a file request to the CDN. It's
> just a useless thing to do.*

```
   Client ──────▶ CDN ──▶ S3        ✅ the intended path
   Backend ─────────────▶ S3        ✅ direct
   Backend ─────▶ CDN               ❌ pointless (extra hop, no benefit)
```

---

## 📤 How Does the CDN Get the Data in the First Place?

### Step 1 — Abdul uploads a video
```
1. Abdul makes a request to Facebook's backend servers
2. Starts uploading the video to their servers
3. Facebook stores this video in a FILE STORAGE (like S3)
4. Facebook stores the METADATA in some database (like MongoDB, like SQL)
5. Facebook hits the CDN servers and CONFIGURES A URL:

     Facebook ──▶ Akamai
     "Please give me the CDN url for this database URL
      s3.aws.com/1234/video.mp4"

6. CDN stores this URL and gives back a unique CDN URL:
     "cdn.akamai.com/a3b2fd5.mp4"

7. CDN stores the mapping from its URL → the database URL internally
```

> ⭐ Note: at this point the CDN holds **only a mapping**, not the video.

### Step 2 — Upinta wants to watch this video
```
1. She makes a request to the Facebook backend servers
2. Backend servers return an HTML + JS + CSS page
```
```html
<html>
<body>
    <video src="s3.aws.com/1234/video.mp4" />     <!-- ❌ database URL -->
    <video src="cdn.akamai.com/a3b2fd5.mp4" />    <!-- ✅ CDN URL -->
</body>
</html>
```
> **Upinta's browser will download the video from the URL embedded in the HTML file:**
> - If the embedded URL is the **database URL**, Upinta might be located **far away** from the
>   database servers — her **download speed will be slow and her latency will be high**.
> - If the embedded URL is the **CDN URL**, Upinta gets the video from the **edge-server closest to
>   her**.
>
> ⭐ **This means the backend server must embed the CDN URL instead of the database URL in the
> response page.**

Then, at the edge:
```
3. CDN's edge node receives the request for "cdn.akamai.com/a3b2fd5.mp4"
4. Edge node checks whether it has the file cached locally
     ├── if YES  → just serve the file                       ⭐ CACHE HIT
     └── if NO   → find the database URL                     ⭐ CACHE MISS
                   fetch the video from the database
                   cache it locally in the CDN's edge server
                   serve it
```

### Step 3 — Pankaj (Upinta's neighbour) also wants to watch
```
1. Pankaj makes a request to the Facebook backend
2. Gets the HTML file with the CDN url
3. Pankaj's browser tries to download from the CDN edge server
4. ⭐ This time around, the edge server HAS the file cached!
     because Upinta just watched it
5. CDN server just serves the file
```

> 🧠 **This is why CDNs work so well for popular content:** the *first* viewer in a region pays the
> long-distance cost once, and **everyone after them gets it locally**.

---

## 🎯 When Does the CDN Actually Cache?

> **Q: When does the CDN actually cache the file from the DB?**
> - ❌ When the CDN is informed about the file by the backend server
> - ❌ When the **first** user makes the first request to fetch the file
> - ✅ ⭐ **When the 2nd request for the file comes, then the CDNs actually store it in their cache!**

### Why?
> ⭐ **CDNs have found out that 70% of all URLs are "1-hit wonders"** — they are accessed **once**,
> and then **never again forever!**

Caching a 1-hit wonder is pure waste: you consume edge storage for a file nobody will ask for
again. Waiting for a **second** request is a cheap, brilliant filter for "is this actually popular?"

> Note: the CDN **will** fetch the file from the DB for both the first and the second request
> (because how else will it get the file?) — **but it will only *cache* it on the 2nd request.**

### The industry workaround 🕹️
> **Media.net is an ad-tech platform** — we serve ads to you.
> - **Ads must load very quickly**
> - Ads are **static content** (images/videos) — served via CDN
> - ⭐ **When we told the CDN about any URL, we would make 2 fake requests to the CDN so that it
>   would be forced to cache it**
> - ⭐ **We would make these requests from multiple countries, so that it caches it everywhere**

This is called **cache warming / pre-warming** — and it's a genuinely common production technique.

### Can the CDN be a bottleneck?
> **No!** Because **CDNs have 100s of millions of servers distributed all across the globe.**

### Some crazy CDN stats (as of 2025)
| Stat | Value |
|---|---|
| **Total CDN bandwidth** (all CDNs combined) | exceeds **10 Petabits per second** (that's **10 million GBps**) |
| **Total CDN storage** | exceeds **1 Zettabyte** (Giga < Tera < Peta < Exa < **Zetta**) |
| **Akamai alone** | handles **> 3 Exabytes per day!** |
| **Share of internet traffic** | **70%** handled by CDNs |

### References
- Basics: https://aws.amazon.com/what-is/cdn/ · https://www.akamai.com/glossary/what-is-a-cdn · https://www.cloudflare.com/learning/cdn/what-is-a-cdn/
- AnyCast: https://www.cloudflare.com/learning/cdn/glossary/anycast-network/
- Quick setup: https://www.sumologic.com/blog/cdn-aws-cloudfront/
- CDN cache invalidation: CloudFront `CacheBehavior` · *Invalidate files to remove content* (CloudFront docs)

---

## 3️⃣ Backend Cache

Now the cache **inside** our own system. Two orthogonal questions:
**(a) Local or Global?** **(b) if Global — Single or Distributed?**

### Global cache
> - **Exists as a separate layer between the app server and the DB**
> - ⭐ **All app servers can access this cache**
> - For example, a **Redis cache** (or a Redis cache cluster)

```
   ┌───────┐  ┌───────┐  ┌───────┐
   │ App 1 │  │ App 2 │  │ App 3 │
   └───┬───┘  └───┬───┘  └───┬───┘
       └──────────┼──────────┘
                  ▼
          ┌───────────────┐     ⭐ shared by all app servers
          │     REDIS     │
          └───────┬───────┘
                  ▼
          ┌───────────────┐
          │      DB       │
          └───────────────┘
```

```python
def get_user_preferences(request):
    user_id = request.user_id
    preferences = redisClient.getKey('pref:user_id')
    if preferences is None:
         preferences = sqlClient \
                          .getPreferencesForUser(user_id)
         redisClient.setKey('pref:user_id', preferences)
    return preferences
```
*(This read-through pattern — check cache, on miss read DB and populate cache — is called
**cache-aside**. Session 4 covers the alternatives.)*

### Local cache
> - **Each app server can locally cache data inside its RAM/HDD**
> - ⭐ **App servers are NOT allowed to access the cache of other app servers** (the cache is
>   **local & private** to each app server)
> - ⭐ **Since the app servers are now storing data, it might make the app servers *stateful***
>   (depending on how we use the cache)
> - ⭐ **which means that the application LB might have to use consistent hashing**

```
   ┌───────────┐  ┌───────────┐  ┌───────────┐
   │  App 1    │  │  App 2    │  │  App 3    │
   │ [cache A] │  │ [cache B] │  │ [cache C] │   ⭐ private, no cross-access
   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
         └──────────────┼──────────────┘
                        ▼
                ┌───────────────┐
                │      DB       │
                └───────────────┘
```

```python
user_preferences_cache = {}   # stored in the RAM

def get_user_preferences(request):
    user_id = request.user_id
    preferences = user_preferences_cache.getKey('pref:user_id')
    if preferences is None:
         preferences = sqlClient \
                          .getPreferencesForUser(user_id)
         user_preferences_cache.setKey('pref:user_id', preferences)
    return preferences
```

> ⭐⭐ **The Session-2 payoff:** a local cache makes app servers **stateful**, and stateful servers
> must receive the *same user's* requests every time — otherwise the cache is useless (every server
> would cache every user). **That requires consistent hashing at the application load balancer.**
> This is the first place the two sessions lock together.

### Local vs Global

| | **Local** | **Global** |
|---|---|---|
| Location | Inside each app server's RAM/HDD | Separate layer between app and DB |
| Shared? | ❌ Private per server | ✅ All app servers |
| Latency | ⭐ **Fastest** — no network hop | One network hop (~0.5 ms) |
| Duplication | Same key cached on many servers | Stored once |
| App statefulness | ⭐ Makes app servers **stateful** | App servers stay **stateless** |
| LB requirement | ⭐ Needs **consistent hashing** | Any algorithm works |
| Consistency | Harder — N copies to invalidate | Easier — one copy |
| Example | In-process dict / Guava / Caffeine | Redis, Memcached |

---

## 🔢 Single vs Distributed (global caches only)

> **Distributed cache:** if a **single cache server is not enough** — we want to **store more data**
> in cache, or we want to **improve the read throughput** — then we will use a **distributed cache**.

> ⭐ **Note: Single vs Distributed is only about *global* cache** — because a **local cache is
> inherently distributed** (each app server acts as a cache, and there are multiple app servers).

### So you can have 3 types of caches
```
1. Local cache                (automatically distributed)
2. Global Single cache        (like a single Redis server)
3. Global Distributed cache   (like a cluster of Redis servers)
```

---

## 🎯 Routing Algorithm for a Distributed Cache ⭐

> **Q: What Routing Algorithm should the LB of a distributed cache use?**
>
> ⭐ **The answer depends on *why* we decided to use a "distributed" cache.**

| Reason we went distributed | What we actually did | Do servers hold the same data? | Routing algorithm |
|---|---|---|---|
| **The data was too large to fit on 1 server** | We **sharded** the data across the cache servers | ❌ **Different cache servers have different data** | ⭐ **Consistent Hashing** |
| **The number of requests was too large for 1 server** | We **replicated** the data across the cache servers | ✅ **Different cache servers have the same data** | ⭐ **Round Robin** |

```
   SHARDED (capacity problem)              REPLICATED (throughput problem)
   ──────────────────────────              ───────────────────────────────
   keys A-H → [cache 1]                    ALL keys → [cache 1]  ┐
   keys I-P → [cache 2]                    ALL keys → [cache 2]  ├ any will do
   keys Q-Z → [cache 3]                    ALL keys → [cache 3]  ┘
   ⭐ MUST hit the right one               ⭐ ANY one can answer
   → Consistent Hashing                    → Round Robin
```

> 🧠 **This is a beautiful, examinable insight:** the routing algorithm is not a matter of taste —
> it is **determined by whether the nodes hold different data or the same data**. Sharding demands
> a deterministic key→node function; replication demands only fair spreading.
>
> *(Recall Session 2: "sharding is a side effect of routing". Same principle, applied to the cache
> tier.)*

---

## ⚠️ Challenges with Caching

Two problems, two solutions — and they are **not** alternatives.

### Problem 1 — Limited space → **Cache Eviction**
> - **Caches are much smaller** (compared to the DB)
> - **Since it is small, it can get full**
> - If the cache is full and you still want to insert a new entry, **you must first "evict"
>   something** from the cache
> - **Solution: Cache Eviction**
> - ⭐ **Note: cache eviction happens during *writes*.**

### Problem 2 — Stale data → **Cache Invalidation**
> - ⭐ **The cache is not the source of truth — the database is the source of truth**
> - It is possible for the data to get **updated in the database, but not in the cache**
> - Then the data inside the cache will be **"stale" (old)**
> - You must **detect when data is old**, and you must **"invalidate" the data** (& remove it from
>   the cache)
> - **Solution: Cache Invalidation**
> - ⭐ **Note: cache invalidation happens during *reads* (lazily).**

```
   ┌─────────────────────────────────────────────────────────────┐
   │  EVICTION            (space problem)   → runs on WRITES     │
   │    "the cache is FULL, something must go"                   │
   │                                                             │
   │  INVALIDATION        (freshness problem) → runs on READS    │
   │    "this entry is OLD, it must not be served"               │
   └─────────────────────────────────────────────────────────────┘
```

### Should we do eviction, or should we do invalidation?
> ⭐ **Both!**
> **Both the cache invalidation algorithm and the cache eviction algorithm are always running
> together — each solves one problem.**

| | **Eviction** | **Invalidation** |
|---|---|---|
| Problem solved | **Limited space** | **Stale data** |
| Triggered on | ⭐ **Writes** (insert into a full cache) | ⭐ **Reads** (lazily, on access) |
| Question asked | *"Who should I throw out?"* | *"Is this still correct?"* |
| Entry removed is | Usually **still valid**, just unlucky | **Definitely wrong** |
| Algorithms | LRU, LFU, FIFO, Random… (**Session 4**) | TTL, write-through, write-around… (**Session 4**) |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Cache** | Small, fast store of frequently-used data; **not the source of truth** |
| **Memory hierarchy** | Larger ⇒ slower & cheaper; smaller ⇒ faster & pricier. Applies to brains, CPUs and the web |
| **CPU register** | What the CPU actually interacts with — few bytes, **0.2 ns** |
| **L1/L2/L3** | CPU caches; **L1/L2 per core**, **L3 shared** |
| **RAM** | 500–1000× slower than registers; **~10–100 ns** |
| **HDD** | ⭐ **100,000× slower than RAM** |
| **Cookies / Session / Local Storage / IndexedDB** | Browser stores: **4 KB / 5 MB / 10 MB / 10 GB** |
| **CDN** | 3rd-party network of edge servers caching large static content; **~70% of internet traffic** |
| **Edge server** | A server physically/geographically **close to the user** |
| **Latency** | Delay between request and response |
| **Bandwidth** | Bytes per second |
| **GeoDNS** | DNS that resolves the nearest IP by user location (low adoption) |
| **AnyCast** | CDN redirect mechanism to reach the nearest edge |
| **1-hit wonder** | ⭐ A URL accessed once and never again — **70% of all URLs**; why CDNs cache on the **2nd** request |
| **Cache warming** | Deliberately making requests so the CDN caches content in advance |
| **Local cache** | Private, in-process cache per app server → makes servers **stateful** → needs **consistent hashing** |
| **Global cache** | Shared cache layer (Redis) between app servers and DB |
| **Distributed cache** | Multiple global cache servers — **sharded** (→ consistent hashing) or **replicated** (→ round robin) |
| **Cache hit / miss** | Data was / wasn't found in the cache |
| **Cache Eviction** | Making room in a full cache — happens on **writes** |
| **Cache Invalidation** | Removing stale data — happens on **reads**, lazily |

---

## 🎯 Session Takeaways

1. **Caching is inevitable, not optional** — fast memory is expensive, therefore small, therefore
   you must choose what to keep close.
2. **Every memory system is hierarchical** — brain, CPU, and the web all trade capacity for speed.
3. **HDD is ~100,000× slower than RAM.** That single ratio justifies the entire caching industry.
4. ⭐ **Distance is physics:** India↔US round trip is **≥200 ms** (really 500–600 ms). Only moving
   *closer* fixes it — hence CDNs.
5. **CDNs are caches, not databases** — they must be backed by S3, and they are **client-facing only**.
6. The backend must **embed the CDN URL**, not the storage URL, or the CDN never gets used.
7. ⭐ **CDNs cache on the 2nd request**, because **70% of URLs are 1-hit wonders**.
8. **Local cache = fastest but makes servers stateful** (⇒ consistent hashing at the app LB);
   **global cache = shared and keeps servers stateless**.
9. ⭐ **Distributed-cache routing depends on *why* it's distributed:** sharded (capacity) ⇒
   **consistent hashing**; replicated (throughput) ⇒ **round robin**.
10. ⭐ **Eviction (space, on writes) and Invalidation (staleness, on reads) are both always running.**

---

## ➡️ Next
**[Session 4 — Caching – 2](./04_Caching_Eviction_and_Invalidation.md)** — eviction mechanisms
(LRU/LFU/…), immediate vs eventual consistency, invalidation mechanisms, and the Scaler Code Judge
case study.
