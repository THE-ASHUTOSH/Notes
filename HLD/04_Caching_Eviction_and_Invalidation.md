# Session 4 — Caching – 2: Invalidation, Consistency & Eviction 🔄

> **Topics:** Eviction mechanisms · Introduction to Immediate & Eventual Consistency ·
> Invalidation Mechanisms · Case Study — Scaler Code Judge
>
> 📄 Class doc: [\[SST-2028\] Caching 2](https://docs.google.com/document/d/12tdw0PoZAOhgCH8A9HgWu9zYYjUDS4lzaq3gqcrLZq8/edit?tab=t.0)

---

## 📑 Table of Contents
1. [Consistency Models](#-consistency-models)
2. [How Cache Reads/Writes Happen](#-how-cache-readswrites-happen)
3. [Why the Cache Must Stay "Dumb"](#-why-the-cache-must-stay-dumb)
4. [Invalidation 1 — TTL](#1️⃣-ttl--time-to-live)
5. [Eager vs Lazy Invalidation](#-eager-vs-lazy-invalidation)
6. [TTL Tuning](#-ttl-tuning)
7. [Invalidation 2 — Write Around](#2️⃣-write-around)
8. [Invalidation 3 — Write Through](#3️⃣-write-through)
9. [Why Write Through is Hard — 2PC](#-why-write-through-is-hard--two-phase-commit)
10. [Invalidation 4 — Write Back](#4️⃣-write-back)
11. [Comparison of All Four](#-comparison-of-all-four-policies)
12. [Cache Eviction](#-cache-eviction)
13. [Eviction Policies](#-eviction-policies)
14. [Key Terms Recap](#-key-terms-recap)

---

## 🎚️ Consistency Models

First, the vocabulary. This is the foundation for **Session 7 (CAP)**.

| Term | Definition |
|---|---|
| **Consistent** | ⭐ **It is not possible to read a stale value.** Every read is guaranteed to read the latest data |
| **Inconsistent** | **It is possible for the reads to be stale** (possible for us to read an old value) |

And the three levels you must be able to name:

| Model | Definition |
|---|---|
| **Immediate Consistency** | ⭐ **Data will immediately be consistent. No waiting required. All copies sync up immediately. Impossible to read a stale/old value.** *(a.k.a. strong consistency)* |
| **Eventual Consistency** | ⭐ **Data will be consistent *eventually*. For some time the data might be inconsistent, but if you wait long enough, it will become consistent** (everything syncs up eventually) |
| **No Consistency** | ⭐ **Data loss can happen!** No matter how long you wait, your data will **never** become consistent |

```
   IMMEDIATE          write ──▶ [all copies updated] ──▶ read ✅ always fresh
   EVENTUAL           write ──▶ [copy A updated] … lag … [copy B updated]
                                        ↑ read here → ⚠️ STALE
   NONE               write ──▶ [copy A updated] ──✗ crash ──▶ ❌ data GONE
```

> *More about consistency in future classes* → **Session 7 (CAP/PACELC)** and **Session 8 (tunable
> consistency)**.

> 🧠 Keep these three straight — each of the four invalidation policies below lands in exactly one
> of these buckets, and that's the single most important thing to remember about each.

---

## 🔁 How Cache Reads/Writes Happen

### The typical read/write cycle
```
WRITE requests  ──▶ go DIRECTLY to the DATABASE (typically), NOT to the cache

READ request:
  1. App server first checks if the value is in the cache
  2. ├── if PRESENT  (Cache HIT)  → return the cached value
     └── if ABSENT   (Cache MISS) → app server fetches value from DB
                                    → returns to the user
                                    → (async) updates the value in the cache
```

```
            ┌──────────┐   write   ┌──────────┐
            │   App    │──────────▶│    DB    │  ⭐ writes bypass the cache
            │  Server  │           └────┬─────┘
            └────┬─────┘                │ miss: fetch
                 │ 1. read              │
                 ▼                      │
            ┌──────────┐                │
            │  CACHE   │◀───────────────┘
            └──────────┘   3. (async) populate
```

### ⭐ The critical consequence
> **Note: since any writes only go to the DB, the data inside the cache can get stale.**
>
> If a read now comes to the cache, **the cache will tell you happily that the value is 10 — which
> is incorrect!**
>
> ⭐ **Note that because this will be a cache *hit*, the app server will just return this incorrect
> value to the client — it won't even check the database.**

```
   t=0   DB: a=10      Cache: a=10        ✅ consistent
   t=1   write a=20 → DB
         DB: a=20      Cache: a=10        ⚠️ STALE
   t=2   read a → cache HIT → returns 10  💥 WRONG, and the DB is never consulted
```

**This is the entire problem that invalidation policies exist to solve.**

> **Q: Why can't we update the cache & the database together for each write?**
> **Because it's hard & slow — more on this later.** When we do something like this, it is called a
> **Write Through** cache.

---

## 🤖 Why the Cache Must Stay "Dumb"

> **Q: Can the cache itself fetch the data from the database?** Why does a cache miss have to happen
> in the above manner? If the cache doesn't have some data, can't it itself fetch it from the
> database, store it, and then return it to the app server?
>
> *Disclaimer: some people do it, but it is typically considered **bad design (anti-pattern)**.*

### Reason: **Separation of concerns**

> - **Business logic** — *what data to fetch, what tables to join, how to filter the data, how to
>   validate it, how to sort it* — **all of this lives inside the app server**.
> - ⭐ **Cache server is supposed to be "dumb".**
> - If we try to make the cache server intelligent, then our business logic will be **split across
>   two entities** — app server & cache server:
>   - **What if the two codebases are not in sync?**
>   - **Codebase logic can be stale in some place**
> - **Cache server would have to have a powerful CPU** — to do all this slicing & dicing of data

> ⭐ **Therefore, any fetching/updating responsibility lies with the app server. The cache server
> just acts as dumb storage.**

| | App server | Cache server |
|---|---|---|
| Business logic | ✅ **all of it** | ❌ none |
| Auth / filtering / sorting / joins | ✅ | ❌ |
| Job | Decide *what* the data is | Store & return bytes for a key |
| CPU needs | High | ⭐ Low (it's a hash table) |

---

## 1️⃣ TTL — Time To Live

> ⚠️ *Note: you might also see TTL called a cache **eviction** strategy — it is **both** an
> invalidation policy and an eviction policy (because it is so simple), **but with a little
> modification**. **Pure TTL is NOT an eviction policy.***

### How it works
> - Whenever you store data inside the cache, **apart from storing the value, you also store the
>   expiry time**.
> - **Every cache entry has a fixed amount of time for which it is valid (TTL).**
> - **TTL can be configured globally** (for all keys), **or per key**.
> - ⭐ **After the TTL expires, we *assume* that the value is stale, and we invalidate it.**
> - ⭐ **In reality, we have no idea whether the value is actually stale or not** (whether the value
>   has been updated in the database or not).

**Example:** write `a=10` to the cache at **8 am** with **TTL = 1 hour** → expiry = **9 am**.

| Key | Value | Expiry |
|---|---|---|
| `a` | 10 | 9:00 am |
| `b` | 20 | 9:05 am |

> ⭐ TTL is **guesswork, formalised.** You are betting that "an hour old" is good enough. It is
> wildly effective precisely because it requires **zero coordination** with the database.

### What consistency does TTL provide?
> **Q: Can the data served from the cache be stale?** What if we read stale data from the cache,
> before the value has a chance to expire?
>
> ⭐ **Yes** — if an update happens in the database **before** the cache entry expires, then the
> subsequent reads (before expiry) **will return the stale data** from the cache.
>
> ⭐ **So, TTL provides "eventual consistency".**

> *Note: when the read request (after the update) came, we first checked the cache (as we always
> do). Since we found the data in the cache, and the data had not expired (**even though it was
> stale**), we returned it to the user. **We ended up serving stale data.***

The staleness window is bounded by the TTL: **worst case, you serve data that is `TTL` seconds old.**

---

## ⏰ Eager vs Lazy Invalidation

> **Q: When do we actually delete this entry from the cache?**

### Eager Invalidation — immediately when the expiry happens
> - This would mean that our cache server has to run some sort of an **event loop / timer for each
>   expiry** (**Timer + Priority Queue**)
> - **Additional overhead in the cache server**
> - ⭐ Imagine if for some reason **a lot of entries have the same expiry time** (say 9 am). Then at
>   9 am, **any request that comes will have to wait** because the cache server will be busy
>   clearing up all the expired entries
> - ⭐ **Performance will be "jittery" — it will not be smooth.** Because of this cleanup process,
>   there can be **temporary latency increases** in cache performance

### Lazy Invalidation — when the next read request comes
> - If we do this, then we're potentially **storing stale data in the cache — wastage of space**
> - ⭐ **But that isn't an issue, because the eviction algo is taking care of that**
> - ⭐ **Always better to invalidate in a lazy manner — this will give you a smooth latency over all
>   requests**

| | **Eager** | **Lazy** ⭐ |
|---|---|---|
| When | The instant TTL expires | On the next read of that key |
| Machinery | Timer + priority queue per entry | ⭐ Just compare `now > expiry` on read |
| Cache server overhead | High | ⭐ ~Zero |
| Latency profile | ⭐ **Jittery** (spikes when many keys expire together) | ⭐ **Smooth** |
| Wasted space | None | Stale entries linger… |
| …but | | ⭐ …**eviction cleans them up anyway** |
| **Verdict** | ❌ | ✅ **Always prefer lazy** |

> ⭐ **This is a lovely example of two subsystems covering for each other:** lazy invalidation
> leaves garbage behind, and eviction was *already* going to remove garbage. So the "downside" of
> lazy invalidation costs nothing. **This is why "both are always running together" (Session 3).**

### On refreshing expiry on read
> **Q: Can we update the expiry of an entry every time we access it from the cache?**
> ⭐ **No, we should not do that when the read requests come.**
>
> - Initial set in cache at **8:55** with expiry **9:00**
> - An **update** was made in DB at **8:58**, so the cache is now **stale**. The cache will be
>   invalidated at 9:00
> - If a read request comes at **8:59**, and you move the expiry forward to **9:05** — in this case
>   your TTL is now higher, and ⭐ **your data will remain stale until 9:05**
>
> **We *can* push the expiry forward when we *write* to the cache** — but then it is not really TTL,
> it becomes something else entirely.

> 🧠 The rule: **TTL measures age since *the data was cached*, not since it was last read.**
> Refreshing on read converts a freshness guarantee into an unbounded staleness bug.

### 🍎 Analogy for TTL — fruit in the fridge
> - Whenever you purchase fruits from the market, **before you put them in the fridge, you label
>   each individual fruit with an expiry date**
> - When you're hungry, you just check the fridge for the fruit you want
> - You **check the tag**:
>   - If the expiry date **has passed** → you **throw that fruit in the garbage** — ⭐ *even though
>     the fruit actually doesn't look spoilt* — and you go to the market to purchase it
>   - If the expiry date **has not passed** → you **eat the fruit** — ⭐ *even if the fruit is rotten*

> ⭐⭐ **That last line is the whole point.** TTL doesn't know if data is stale. It only knows how old
> it is. It **throws away good data** and **serves bad data** — but it does so cheaply and predictably.

---

## ⏱️ TTL Tuning

> **Q: What's the ideal value for TTL?**
> ⭐ **Completely dependent on the application.** It might be as low as **5 seconds**, or as large
> as **a week**.

| TTL | Cache misses | Freshness |
|---|---|---|
| **Lower TTL** | ⭐ **More** cache misses (data invalidated very quickly) | ⭐ Data is **more fresh** |
| **Higher TTL** | ⭐ **Better** cache hit rate | ⭐ Data is **more stale** |

```
        hit rate ▲                                    ▲ staleness
                 │                                    │
                 │        ╱────────                   │        ╱
                 │      ╱                             │      ╱
                 │    ╱                               │    ╱
                 │  ╱                                 │  ╱
                 └────────────────▶ TTL               └────────────────▶ TTL

        ⭐ TTL is a DIAL between freshness and performance. There is no correct setting —
           only a correct setting FOR YOUR APPLICATION.
```

Examples of the judgement call:
| Data | Sensible TTL | Why |
|---|---|---|
| Stock price | ~1 s | Staleness is money |
| User preferences | minutes–hours | Rarely changes, low harm |
| Product catalogue | hours | Changes on a deploy cadence |
| Country/currency list | a week | Effectively static |

---

## 2️⃣ Write Around

> **Very similar to TTL — as in it also provides "eventual consistency".**

### The key difference vs TTL — *how expensive is the read?*

| Policy | Works best when… |
|---|---|
| **TTL** | ⭐ **Fetching an entry from the DB is easy**, or requires **no additional postprocessing/computation** |
| **Write Around** | ⭐ **Fetching data from the DB is extremely expensive**, or requires **additional postprocessing/computation** |

### Example — TTL is right
```sql
user_preferences
    user_id (bigint)   name (text)   preferences (json)

select * from user_preferences
where user_id = 1234
```
> **Very simple & fast query.** Assume we need to cache the user preferences and we're okay with
> eventual consistency → ⭐ **the ideal invalidation policy will be TTL.**

*(Because on a miss, recomputing is trivial — just re-run a primary-key lookup.)*

### Example — Write Around is right
```sql
user_preferences
    user_id (bigint)   name (text)   preferences (json)

-- Find out all the users that are using dark theme on some mobile device.
select * from user_preferences up
join user_devices ud on ud.user_id = up.user_id
where ud.device_type = 'mobile' and up.theme = 'dark'
group by up.user_id
```
> **Complex & slow query.** In this case it might be better to use a **Write Around** policy.

*(Because on a miss you cannot afford to recompute on the request path — it would be a disaster
under load.)*

### How Write Around works
> ⭐ In case of write around, there's a **separate background process** (running in a **separate app
> server**) that **periodically**:
> 1. **fetches all recently updated data from DB**
> 2. **does the computation**
> 3. **updates the cache in one go**

```sql
select * from ...
where updated_at > (now() - '1 hour')
```

```
   ┌──────────────┐  writes   ┌──────────┐
   │  App Server  │──────────▶│    DB    │
   └──────┬───────┘           └────┬─────┘
          │ reads                  │ ⭐ periodic pull of
          ▼                        │    recently-updated rows
   ┌──────────────┐                ▼
   │    CACHE     │◀────── ┌────────────────────┐
   └──────────────┘  bulk  │  BACKGROUND WORKER │  (separate app server / cron)
                     write │  compute + update  │
                           └────────────────────┘
```

> **Q: Can Write Around serve stale data from the cache?**
> ⭐ **Yes.** Until the background **"cron job"** runs again, any updates to the DB mean that **the
> cache has stale data.**

### 🍎 Analogy for Write Around — fruit again
> - Whenever you purchase fruits from the market, **you just put them in the fridge**
> - ⭐ **You only go to the market at random times**
> - Whenever you want to eat the fruit, you check your fridge:
>   - if the fruit is there → **you eat it, irrespective of whether it is fresh or rotten**
>   - ⭐ **if the fruit is not there → you sleep hungry. You don't go to the market**
> - **Every weekend you simply throw out all the fruits from your fridge** — irrespective of whether
>   they're fresh or rotten — **and you restock your fridge**

### ⭐ The surprising rule: a miss returns an error, not a DB read
> **Q: If the data is not found in the cache (the cron job has not even run once so far), then what
> happens during a read?**
>
> ⭐ **Reads always check the cache. If the data is not in the cache, we simply return a 404 error to
> the client. We do NOT go to the database.**
>
> **Why?** Because we use write-around **when the data fetching/computation is expensive**. So if
> the computed data is not found in the cache, ⭐ **we want to wait for the computation to complete
> once, instead of doing the computation on the fly for each incoming request.**

> 🧠 This is the deepest idea in the session. In write-around, **the cache is not an optimisation —
> it is the *only* read path.** The database is write-only from the API's perspective. Falling back
> to the DB would defeat the entire purpose and could take the database down.

### Sizing
> **Q: What if the data is too large to fit in the cache?**
> - **Write-around is typically done when the "computed" data is small enough to fit in the cache.**
> - ⭐ **Eviction algorithm is usually not needed** for the data that will be cached. You will evict
>   it only **when the data is no longer required**.
> - For example, **when the contest is over, you can evict the leaderboard data.**

*(That leaderboard hint is a direct pointer at the Session 5 case studies.)*

---

## 3️⃣ Write Through

> **In certain cases, we require "immediate consistency" (aka strong consistency) — no stale reads,
> ever.**
>
> ⭐ **The only way to achieve that is to ensure that whatever writes happen, happen at both the
> cache and the DB *together*!**

```
                     ┌──────────┐
   write ──────────▶ │   App    │
                     │  Server  │
                     └──┬────┬──┘
              ┌─────────┘    └─────────┐
              ▼    BOTH, ATOMICALLY    ▼
        ┌──────────┐            ┌──────────┐
        │  CACHE   │            │    DB    │
        └──────────┘            └──────────┘
```

> ⭐ **Write through cache is difficult — because ensuring atomicity across multiple servers is
> difficult!**

---

## 🔀 Why Write Through is Hard — Two Phase Commit

### On a single server, atomicity is easy
> - **OS thread synchronization** (locks, semaphores, mutexes, …)
> - **Shared RAM**
> - ⭐ **It is easy to ensure that two tasks happen atomically (either both, or neither)**

### Across multiple servers (cache & DB), it isn't
> - ⭐ **No shared RAM**
> - **What if the write to DB succeeds but the write to the cache fails?**
>   - either **retry** the write to cache (**user will have to wait — high latency**)
>   - or, **rollback** the DB write (transactions)
> - **What if the write to DB succeeds, the write to cache succeeds, but the *response* from the
>   cache fails?**
>   - ⭐ **App server thinks that the write failed somewhere, so it will try to rollback/retry**
>   - **What if the rollback fails?**
>   - **What if the ACK for the rollback fails?**

```
   App ──write──▶ DB    ✅
   App ──write──▶ Cache ✅
   App ◀──ACK───  Cache ✗ LOST
        │
        └─▶ App believes it failed → rolls back the DB
            → now DB=old, Cache=new  💥 INCONSISTENT, and worse than before
            → rollback fails? → ACK for rollback fails? → … turtles all the way down
```

> ⭐ **This infinite regress is not a bug you can code around** — it's a fundamental property of
> distributed systems (you cannot distinguish "the message was lost" from "the machine died").

### Two Phase Commit (2PC)
> ⭐ **2 Phase Commit — protocol used to perform atomic transactions in a distributed setting**
> - **slow** (high latency & low throughput)
> - **hard to implement** (needs state management)
> - **needs additional infrastructure**

```
   PHASE 1 — PREPARE                 PHASE 2 — COMMIT
   Coordinator ──"can you commit?"──▶ Cache   ──"COMMIT"──▶ Cache  ✅
   Coordinator ──"can you commit?"──▶ DB      ──"COMMIT"──▶ DB     ✅
               ◀──── "yes" ────────           (if ANY said no → ABORT everywhere)
```

> ⭐ **We will formalize this trade-off in the CAP theorem class.**
> ⭐⭐ **"If you want consistency, you have to pay for it in blood (it will cause high latency and
> low throughput)."**

### ⭐ The important exception: a LOCAL cache
> **Note: 2 phase commit is needed only in the case of a *global* cache** — the app server has to
> make writes in **2 places** — DB & cache.
>
> ⭐ **If the cache is *local*, you will ALWAYS use immediate consistency (write through)** if the
> writes come to the app servers:
> - **no latency issues, no 2PC required**
> - Because the cache is **"local" (RAM/HDD)** and it is **guaranteed that writes always succeed**
> - ⭐ **Effectively you only have to coordinate with the database write (no need of managing 2
>   states)**

```
   GLOBAL cache:  App ──▶ DB  +  App ──▶ Redis (network!)   → 2 failure points → 2PC
   LOCAL cache:   App ──▶ DB  +  App ──▶ own RAM (cannot fail) → 1 failure point → free ⭐
```

> 🧠 **A genuinely useful design lever:** if you need strong consistency in a cache, making the
> cache **local** removes the distributed-transaction problem entirely. The price is the
> statefulness/consistent-hashing requirement from Session 3.

---

## 4️⃣ Write Back

> ⭐ **It provides NO consistency guarantees. In fact, write back cache can lead to DATA LOSS!**

### How it works
> - ⭐ **Writes do NOT go to the database — instead, writes go to the cache**
> - **Periodically, you write the data back from the cache to the database**

```
   write ──▶ ┌──────────┐  ⭐ periodically flushed  ┌──────────┐
             │  CACHE   │ ───────────────────────▶ │    DB    │
   read  ──▶ └──────────┘                          └──────────┘
             (both reads AND writes hit the cache)
```

### How can there be data loss?
> ⭐ **Yes, this can lead to data loss!**
> - **If the cache server crashes with unsynced changes, then the data is permanently lost**
> - **Cache is volatile, it doesn't store data on disk**
> - **DB is persistent, but the cache server crashed with new data that had not been synced to the
>   DB yet**

### Then why would we ever use it?
> **Pros:**
> - **Any read/write is happening at the cache**
> - ⭐ **Any read/write will be insanely fast! (100,000+ reads/writes per second)** — compared to a
>   database which can only handle **100 to 1000 writes/second per server**

```
   Cache: 100,000+ writes/sec
   DB:        100–1,000 writes/sec       ⭐ a 100×–1000× difference
```

> **Use it in scenarios where:**
> - ⭐ **the individual data points are not important**
> - ⭐ **when it is okay to lose some data**
> - ⭐ **when trends matter more than individual data points** — **analytics**
> - **extremely high write throughput is required**
>
> **Examples:** tracking the **number of views / likes / clicks** on a video/post/…

> 🧠 **The judgement:** if a viral video's view count is 1,000,482 and a crash loses 300 of them,
> **nobody cares** — the *trend* is intact. But if a bank balance loses ₹300, you're finished.
> **Write-back is chosen based on the business value of a single data point.**

---

## 📊 Comparison of All Four Policies

| Policy | Writes go to | Reads served from | Consistency | Stale reads? | Data loss? | Use when |
|---|---|---|---|---|---|---|
| **TTL** | DB | Cache (fallback DB) | ⭐ **Eventual** | ✅ up to TTL | ❌ | Cheap re-fetch, tolerable staleness |
| **Write Around** | DB | ⭐ **Cache only (404 on miss)** | ⭐ **Eventual** | ✅ until cron runs | ❌ | ⭐ **Expensive computation** |
| **Write Through** | ⭐ **DB + Cache together** | Cache | ⭐ **Immediate (strong)** | ❌ **never** | ❌ | Strong consistency required |
| **Write Back** | ⭐ **Cache only** | Cache | ⭐ **None** | ✅ | ⭐ **YES** | Analytics, counters, huge write throughput |

### Decision flow
```
Do you need immediate consistency?
├── YES → WRITE THROUGH
│          └── is the cache LOCAL? → ⭐ free (no 2PC)
│              is the cache GLOBAL? → ⭐ needs 2PC → high latency, low throughput
└── NO
     ├── Is losing individual writes acceptable, and do you need 100k+ writes/sec?
     │      └── YES → WRITE BACK (analytics, view counts)
     └── NO
          ├── Is recomputing the value on a miss CHEAP?  → TTL
          └── Is recomputing the value on a miss EXPENSIVE? → WRITE AROUND
```

---

## 🗑️ Cache Eviction

### Why the cache is always full
> - If you've just started the cache server, it is initially **empty**
> - **Do you want your cache server to be empty?** ⭐ **No!** You want the cache to be **full**,
>   because otherwise **you're wasting much-needed cache**. You want to cache as much data as
>   possible!
> - As the operations continue, the cache server will get full — ⭐ **it will always remain full from
>   this point onwards** (unless it crashes & restarts)
> - But you still want to cache **more** data into it (even though it is full) — this means **you
>   first have to get rid of something that is already cached** to make space for new data

> ⭐ **Cache Eviction algorithm decides which data to "kick-out" to make space for new data.**

> 🧠 **Key mental correction:** a full cache is not a problem to be fixed — it's the **healthy steady
> state**. Eviction is therefore not an error path; it runs constantly, forever.

### How do you decide which eviction policy to use?
> ⭐ **Just use LRU.**
> - ⭐ **No need to think at all — LRU works well for all use cases**
> - **It might not be the perfect choice, but it will work well enough**
> - **Only if you've a lot of extra time**, and you've already optimized everything else:
>   - you can implement and run all the various eviction strategies
>   - **measure which one is performing the best in practice**
>   - ⭐ **(never guess)**

---

## 🔢 Eviction Policies

| Policy | Evicts | Verdict |
|---|---|---|
| **FIFO** — First In First Out | The **oldest inserted** entry | Simple; ignores usage |
| **LIFO** — Last In First Out | The **most recently inserted** entry | Rarely sensible |
| ⭐ **LRU** — Least Recently Used | The entry **not accessed for the longest time** | ⭐ **99% of cases** |
| **LFU** — Least Frequently Used | The entry with the **fewest accesses** | Good for stable popularity; slow to adapt |
| **MRU** — Most Recently Used | The **most recently used** entry | ⭐ **Complete opposite of LRU. Bad for 99% of cases!** |

### Why LRU works — locality of reference 📚

*(Homework from the class: read about these.)*

| Principle | Definition |
|---|---|
| ⭐ **Temporal locality of data** | **If some data has been accessed right now, then it is highly likely that it will be accessed again in the near future** |
| ⭐ **Spatial locality of data** | **If some data has been accessed right now, then it is highly likely that "nearby" data will be accessed in the near future** |

```
   [a, b, c, d, f, e, g, r, …]
     ↑ accessed 'd' now
       → temporal: 'd' likely again soon        → keep 'd'  (LRU does this)
       → spatial : 'f', 'e' likely soon too     → prefetch neighbours
```

> ⭐ **LRU is a direct implementation of temporal locality.** That is *why* it works so broadly —
> it's not a heuristic someone guessed, it's a bet on a real and near-universal property of access
> patterns.

**Implementation note:** LRU is classically a **hashmap + doubly linked list** — O(1) get and O(1)
move-to-front. (This is the well-known LLD interview problem, and where LLD meets HLD.)

### 🧠 Homework: find a valid use-case for MRU
> *H/W: find a valid use-case of the MRU eviction policy*

*Hint to think about: when is "just accessed" evidence that data **won't** be needed again? Consider
a **one-pass sequential scan** of a huge table — the row you just read is the row you're **least**
likely to revisit, while older cached rows may still be wanted. MRU protects the cache from being
wiped by a scan.*

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Consistent** | Impossible to read a stale value |
| **Immediate / strong consistency** | All copies sync immediately; never stale |
| **Eventual consistency** | Temporarily stale, converges if you wait |
| **No consistency** | Data loss possible; never converges |
| **Cache hit / miss** | Value found / not found in the cache |
| **Separation of concerns** | ⭐ Business logic in the app server; **cache is dumb storage** |
| **TTL** | Store an expiry with each entry; assume stale after it → **eventual consistency** |
| **Eager invalidation** | Delete exactly at expiry — needs timers, causes **jittery latency** |
| **Lazy invalidation** ⭐ | Check expiry on the next read — smooth latency; eviction cleans the rest |
| **Write Around** | Background cron computes & fills the cache; ⭐ **miss ⇒ 404, never hit the DB** |
| **Write Through** | Write to DB **and** cache atomically → **immediate consistency** |
| **2 Phase Commit (2PC)** | Distributed atomic-commit protocol: prepare → commit. Slow, hard, needs infra |
| **Write Back** | Write only to cache, flush to DB later → ⭐ **fast but can lose data** |
| **Cache eviction** | Choosing what to kick out of a (permanently) full cache |
| **FIFO / LIFO / LRU / LFU / MRU** | Eviction policies; ⭐ **LRU for ~99% of cases** |
| **Temporal locality** | Recently accessed data will likely be accessed again soon |
| **Spatial locality** | Data *near* recently accessed data will likely be accessed soon |

---

## 🎯 Session Takeaways

1. **Three consistency levels:** immediate (never stale), eventual (stale for a while), none (data loss).
2. **Writes go to the DB, reads check the cache** — which is exactly *why* caches go stale, and why
   a cache **hit** can confidently return a **wrong** answer.
3. ⭐ **The cache must stay dumb.** Business logic belongs in one place — the app server.
4. **TTL = guessing by age.** It throws away fresh data and serves rotten data, but costs nothing
   and gives **eventual consistency** with a bounded staleness window.
5. ⭐ **Always invalidate lazily** — eager invalidation makes latency jittery, and eviction already
   cleans up the leftovers.
6. **Never refresh TTL on a read** — it converts bounded staleness into unbounded staleness.
7. ⭐ **TTL when re-fetching is cheap; Write Around when computing is expensive** — and in
   write-around, **a miss returns 404**, because the cache *is* the read path.
8. ⭐ **Write Through buys immediate consistency and pays "in blood"** (2PC → high latency, low
   throughput) — **unless the cache is local**, where it's free.
9. ⭐ **Write Back is 100×–1000× faster and can lose your data** — use it only when individual data
   points don't matter (analytics, view counts).
10. ⭐ **A cache is always full; eviction always runs. Just use LRU** — it's temporal locality made
    concrete. Never guess; measure.

---

## ➡️ Next
**[Session 5 — Caching: Case Studies](./05_Caching_Case_Studies.md)** — Scaler Code Judge,
Scaler Leaderboard, and the Social Media Newsfeed.
