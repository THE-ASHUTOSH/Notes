# Session 5 — Caching: Case Studies 📊

> **Topics:** Case studies — 1. Scaler Code Judge (continued) · 2. Scaler Leaderboard ·
> 3. Social Media Newsfeed
>
> 📄 Class doc: [\[SST-2028\] Caching Case Studies](https://docs.google.com/document/d/13GogwThXSMBB5lXPKAuoMm3lNKx4Yn0NZcOEVaQ2IpQ/edit?tab=t.0)
>
> ℹ️ The class doc covers **Code Judge** and **Contest Leaderboard** in full. The **Social Media
> Newsfeed** is taken up in [Session 6](./06_APIs_Microservices_and_Newsfeed.md).

---

## 📑 Table of Contents
1. [Do We Always Want to Cache?](#-do-we-always-want-to-cache)
2. [The 5-Step Cache Design Process](#-the-5-step-cache-design-process)
3. [Case Study 1 — Scaler Code Judge](#-case-study-1--scaler-code-judge)
4. [Code Judge: Capacity Estimation](#-capacity-estimation)
5. [Code Judge: Local vs Global](#-step-2-local-vs-global)
6. [Code Judge: Invalidation — the TTL Trap](#-invalidation--the-ttl-trap)
7. [Code Judge: The Versioning Solution](#-the-solution--versioning-immutability)
8. [Code Judge: Eviction](#-eviction-algorithm)
9. [Code Judge: Load Balancer & Multi-threading](#-load-balancer---why-not-multi-threading)
10. [Case Study 2 — Contest Leaderboard](#-case-study-2--contest-leaderboard)
11. [Leaderboard: Capacity Estimation](#-capacity-estimation-1)
12. [Leaderboard: Cache Type](#-step-2-cache-type)
13. [⚠️ Interview Advice — Never Name a Technology](#-interview-advice--never-name-a-technology)
14. [Redis](#-redis)
15. [Leaderboard: Invalidation](#-invalidation)
16. [Leaderboard: Redis Schema](#-redis-schema)
17. [Leaderboard: Eviction & LB](#-eviction--load-balancer)
18. [Key Terms Recap](#-key-terms-recap)

---

## 💰 Do We Always Want to Cache?

> *Do we always want **cash**?* **Yes.** 😄
> *Do we always want to **cache**?* ⭐ **It is not always so.**

### Pros
| Pro | Detail |
|---|---|
| **Improves read throughput** | *assuming a high hit rate* |
| **Improves best/average case read latency** | ⭐ **but it ALWAYS worsens the worst case read latency** |

> **Throughput:** the **average number of tasks completed per unit time**. High throughput is good.

### Cons
| Con | Detail |
|---|---|
| **Adds complexity** | It **has to be designed** |
| **Additional infrastructure to maintain** | Another cluster to run, monitor, patch |
| **Caching logic gets mixed into business logic** in the app server code | ⭐ One way to mitigate this is to **move the caching to the middleware** |
| ⭐ **Increases latency in the worst case** | If there's a cache **miss**, you now have to check **2 places** — first cache, then DB |
| ⭐ **Worsens write throughput (sometimes)** | Because now you have to write to **2 places** (DB + Cache) |

```
   HIT  :  App → Cache            ✅ ~0.5 ms      (best case: much better)
   MISS :  App → Cache → DB       ❌ 0.5 + 10 ms  (worst case: WORSE than no cache)
```

> ⭐ **The honest framing:** a cache is a **bet**. If your hit rate is high, you win big. If it's
> low, you've added latency, complexity and infrastructure for nothing. **Establish the need first.**

---

## 🪜 The 5-Step Cache Design Process

> Use this checklist for **every** caching question — in this course and in interviews.

```
1. Establish the NEED for caching
2. Determine the TYPE of cache
     • Local vs Global
     • Single vs Distributed   (only if global cache)
3. Identify the EVICTION algorithm
     • just use LRU
4. Identify the INVALIDATION algorithm, based on:
     • consistency requirements
     • data / query complexity
5. Think about the LOAD BALANCER  (consistent hashing vs round robin)
```

> 🧠 Note the ordering logic: **need → shape → eviction → invalidation → routing.** Steps 4 and 5
> depend on the answers to 2 and 3, which is why this order and not any other.

---

## ⚖️ Case Study 1 — Scaler Code Judge

> **Code Judge** — a service that "judges" your code submission. When you submit a solution for a
> DSA problem in Scaler, we have to take your code and **run it through hundreds of testcases** to
> evaluate whether it is correct or not.

### What does the app server need to evaluate a code submission?
| Input | Examples |
|---|---|
| **User info** | auth, already solved this problem or not, part of course or not, … |
| **Problem info** | topic, total score, memory limit, time limit, number of testcases, … |
| **Code Submission** | made by the user |
| ⭐ **Testcase data** | **input file, expected output file** |

---

## 🧮 Capacity Estimation

### How large can this data be (avg/worst case)?
| Data | Size | Where it lives |
|---|---|---|
| **User info / Problem info** | a few **KB** | **SQL database** (Amazon RDS) |
| ⭐ **Testcase data** | **1 – 2 GB** | **File storage** (Amazon S3) |

### Why is testcase data gigabytes?
> For a problem we run your code through **100 testcases**. Imagine the problem is about **sorting
> an array**. Each testcase comprises a large array (**N = 10⁶**), and each expected output is also
> a large array (N = 10⁶).

```
  100 testcases × (10^6 integers / testcase) × (8 bytes / integer)
= 100 × 10^6 × 8 bytes
= 800 MB
≈ 1 GB          ← for the INPUT file. Similar size for the OUTPUT file.
```

### Total testcase data in S3
```
Scaler has around 3,000 problems
  3,000 problems × (1 GB testcase data / problem)
= 3 TB of testcase data
```

> **Is this data too large?**
> ⭐ **Not really — storage is cheap.** 3 TB is too large to fit **completely in RAM**, but can
> **easily fit on HDD**.

### How many problems are solved on a given day?
> **Around 100 – 200 different problems** are being solved by Scaler students on any given day.
> We're running **multiple batches in parallel** — each batch might be solving the problems of the
> current (or last) class, and the batches **overlap in timelines**.

> ⭐ **This is the key number for cache sizing:** the *working set* is ~100–200 problems
> (~100–200 GB), **not** the full 3 TB.

### Should we store these testcases in a CDN?
> ⭐ **No!**
> - **Backend services will never access data from the CDN**
> - **CDNs are client-facing**
> - CDNs reduce latency for the **client**, by serving data from an **edge** server close to the user

*(Straight from Session 3 — and a trap worth recognising: "it's a big static file" tempts you toward
a CDN, but the consumer here is a **backend** service.)*

---

## 🎯 Step 1: Need for Caching

> **Q: Do we want to transfer 1 GB of data over the network for each request?**
> ⭐ **Absolutely No. Therefore, we need a cache!**

---

## 🏠 Step 2: Local vs Global

### ❌ Global Cache — **doesn't solve our problem**
> - Yes, it will be available to all app servers (so our app servers can be stateless)
> - Yes, the data is large, so global makes more sense?
> - ⭐ **NO — it doesn't solve our problem at all.** We still have to transfer **1 GB** of testcase
>   data for each request — **from the cache server to the app server**
>   - earlier we were transferring **from S3 → app server** — expensive!
>   - now we're transferring **from cache → app server** — expensive!

```
   ❌  S3 ──1GB──▶ App        (the original problem)
   ❌  Redis ──1GB──▶ App     (same problem, different hostname!)
```

> ⭐ **The insight:** a global cache removes *database* load but **not network transfer**. When the
> payload itself is the problem, moving it closer isn't enough — it must **not move at all**.

### ✅ Local Cache — each server caches some testcases in its local HDD
```
1. The request comes to the app server
2. The app server hits the SQL db to fetch the user/problem info (small data)
3. If the problem's testcases are already cached in the app server's HDD
      → it will just use those testcase files   ⭐ (NO network overhead)
4. If not cached
      → download the files from S3, cache them locally (on its HDD), then use them
5. Any subsequent requests for the same problem now use the testcases from the HDD
```

```python
# POST /evaluate-submission

fn check_solution(request):
    pid = request.solution.problem_id
    uid = request.auth_token.uid
    user_info, problem_info = fetch_from_SQL(user_id, pid)

    if not file_exists(`{pid}_in.txt`):  # caching logic
        download_from_s3(url='s3.hld-bucket-com/testcases/{pid}_in.txt',
                         save_to='/users/scaler/testcases/{pid}_in.txt')
        download_from_s3(url='s3.hld-bucket-com/testcases/{pid}_out.txt',
                         save_to='/users/scaler/testcases/{pid}_out.txt')
        # this function will save it on the local HDD

    # these reads are from the local HDD
    inputs = read_file(`/users/scaler/testcases/{pid}_in.txt`)
    expected_outputs = read_file(`/users/scaler/testcases/{pid}_out.txt`)

    return evaluate(solution.code, inputs, expected_outputs)
```

> 💡 Note this is a **local cache on the HDD**, not in RAM — 100–200 GB of testcases won't fit in
> RAM but comfortably fits on disk. **A local disk read still beats a network transfer by a mile.**

### Single vs Distributed
> **N/A** — single vs distributed only applies for **global** caches. A **local cache is
> distributed automatically**, because there are multiple app servers.

---

## ⏳ Invalidation — the TTL Trap

### When is invalidation even applicable?
> ⭐ **Invalidation is only applicable when the data changes.** If the data never changes, do we need
> to invalidate? No.

### Can the testcases change?
> - **New problems can be added** — but that is **not a data updation**
> - **Can the testcase data for an existing problem be updated?** ⭐ **Yes.**
>   **Because our problem setters are not Gods… they can make mistakes.** It is possible that:
>   - our **editorial solution was incorrect** → we have to fix the solution and the
>     `expected_output.txt` file
>   - our solution was correct, but our **testcases were not "tight enough"** — our problem required
>     an **O(n log n)** solution, but the testcases let the **O(n²)** solutions pass as well → we
>     have to fix **both** the `input.txt` and the `expected_output.txt` file

### How frequently?
> **Extremely rarely.** We have good problem setters and a lot of QA. But it happens from time to
> time. Let's say **~1 update / problem / year** on average.

### Can we ignore this rare edge case?
> ⭐ **Absolutely NOT! We must have the infrastructure & logic in place!**
>
> *Imagine that we realize our testcases are bad **during a live contest** — we can't say stuff like
> "oh but I thought that this will be so rare, my cat also thinks the same, so I didn't implement
> this…"*

> ⭐ **A genuinely important engineering lesson:** rarity is not an excuse. What matters is the
> **cost when it happens**, not the probability.

### What consistency do we require?
> Imagine that during a contest we realise some testcases are wrong. Our problem setters create new
> testcases and upload them to S3. And we **announce** to all participants that the testcases have
> been updated — *please resubmit problem 3*.

| Model | What it means here | Verdict |
|---|---|---|
| **Eventual Consistency** | After updation & announcement, for some time (next 10 mins) when people resubmit P3, **still the old testcases are used** | ⭐ **NOT good enough!** |
| **Immediate Consistency** | After updation & announcement, **any submissions to P3 use the new testcases** (new testcases effective **immediately**) | ✅ **Required** |

> So now that we know we require immediate consistency, it is obvious that we should use
> **Write Through**. *But let's explore — just for learning.*

### ❌ TTL
> Every time we download the file from S3, we maintain an expiry time. If the request comes before
> expiry we use the cached testcases; otherwise we assume the file has expired, delete the cached
> testcase and fetch again from S3.

```python
fn check_solution(solution):
    pid = solution['problem_id']
    user_info, problem_info = fetch_from_rds(pid)

    if file_exists(`{pid}_in.txt`):
         if read_last_updated_at(`{pid}_in.txt`) < now() - (1 hour):
              # file was downloaded more than 1 hour ago — stale!
              delete_file(`{pid}_in.txt`)    # TTL invalidation

    if not file_exists(`{pid}_in.txt`):         # caching logic
        download_from_s3([`{pid}_in.txt`, `{pid}_out.txt`])
        # this function will save it on the local HDD

    inputs = read_file(`{pid}_in.txt`)    # these reads are from the local HDD
    expected_outputs = read_file(`{pid}_out.txt`)

    return evaluate(solution.code, inputs, expected_outputs)
```

**What is the ideal TTL?** Walk down the options:

| TTL | Problem |
|---|---|
| **1 week / 1 day / 10 hours** | ⭐ **By the time the TTL expires, the contest is over. The updated testcases never took effect** |
| **1 hour / 10 min** | ⭐ **For the next few minutes after your announcement, the old testcases are still being used. Bad user experience** |
| **1 min / 10 s / 1 s** | ⭐ Every 1 min the TTL expires → each app server has to **re-download 5–10 GB** from S3. With **1000 app servers**, we'd transfer **5 TB of data per minute** → **defeats the purpose of caching**; the **miss rate is too high** |

> *There should be some sweet spot for TTL…*
> ⭐⭐ **No! There's absolutely no sweet spot — none of the values are going to work. All of them
> are a bad experience in some way or another.**

### ❌ Write Around
> **Same as TTL** — we will have to decide how frequently the CRON job will run. **Once again,
> there's no ideal value.**

### ❌ Write Back
> **This is stupid** — this will lead to **data loss**. Additionally, we've a **local** cache — we
> will have to write to **1000 app servers** whenever a write comes.

### ❌ Write Through
> **Q: Is it feasible to update 1 GB files in hundreds of app servers + S3 in an atomic manner?**
> ⭐ **Absolutely not!**
> - Maintaining atomicity across **2** servers is already insanely hard & slow
> - Maintaining atomicity across **100s of servers is impossible**
>   - **at least 1 server will fail** — you now have to **rollback the other 99** servers
>   - **you will be limited by the slowest server** (incredibly slow writes)
>
> ⭐ **This will NOT work!**

**So all four textbook policies fail.** 🤔

---

## ⭐ The Solution — Versioning (Immutability)

> Instead, we can do the following: **version the testcase files using a timestamp in the file name**
```
p1_input.txt   ⇒   p1_input_2025-03-16 08:00.txt
```

### The read path
> The normal cache works as earlier (with a slight modification):
> 1. When a request comes to the app server, we first check the **SQL db** to fetch the user info
>    and problem info
> 2. ⭐ **During this call itself, the SQL db will also give us the input/output *file names* for
>    this problem's testcases**
> 3. If these files are already available in the HDD (local cache) → just use them
> 4. If not → fetch from S3 and then use them

### The invalidation path
> - Problem setter **uploads the new files (with new timestamp in name) to S3**
> - Problem setter **updates the file name in the SQL db**
> - ⭐ **Note that these two writes (S3, SQL) don't have to be atomic.** We can first upload to S3,
>   and **only if that succeeds**, update the filename in SQL — **because if the new file is uploaded
>   in S3 but the filename is not updated in SQL, the new file is not causing any harm — it's just
>   not being used**
> - For any requests that arrive **after the SQL entry has been updated**:
>   - the SQL db provides the **new file name**
>   - the app server detects it **does not have these new files** in the HDD (local cache)
>   - so the app server **fetches these files from S3** and then uses them

```python
fn check_solution(request):
    pid = request.solution.problem_id
    uid = request.uid
    user_info, problem_info = fetch_from_rds(uid, pid)

    input_file_name  = problem_info.input_file_name    # get the version from the SQL DB
    output_file_name = problem_info.output_file_name

    if not file_exists(input_file_name):               # caching logic
        download_from_s3([input_file_name, output_file_name])
        # this function will save it on the local HDD

    inputs           = read_file(input_file_name)      # these reads are from the local HDD
    expected_outputs = read_file(output_file_name)

    return evaluate(solution.code, inputs, expected_outputs)
```

### Why this is brilliant ⭐⭐
> - **Basically, we're caching the testcases.** We're **not** caching the **version id** — ⭐ **the
>   version id is fetched every time from the DB, so the version id cannot be stale**
> - Now that we're **not updating the testcases at all** (we're not modifying existing files, we're
>   **uploading a new version**), ⭐ **the testcases are immutable — since they never change, there's
>   no need for invalidation**

```
   THE TRICK:
   ┌────────────────────────────────────────────────────────────────────┐
   │  Cache the BIG, EXPENSIVE thing that is now IMMUTABLE  (files)     │
   │  Fetch the TINY, MUTABLE pointer to it EVERY TIME     (filename)   │
   └────────────────────────────────────────────────────────────────────┘
   → Immediate consistency, with ZERO distributed transactions.
```

> ⭐ **Note:** basically, the app server is only doing **eviction, not invalidation**. **The problem
> setter does invalidation** by "invalidating" the old testcase filenames and replacing them with
> the new testcase filenames in the SQL database.

> 🧠 **Generalise this pattern — it's one of the most useful in all of system design:**
> **make your cached data immutable and version it; keep the mutable pointer small and uncached.**
> This is exactly how **cache-busting asset URLs** (`app.9f2c1a.js`), **Docker image digests**, and
> **content-addressed storage** all work.

---

## 🗑️ Eviction Algorithm

> **LRU eviction (in the app server).**
> - ⭐ **The operating system will automatically maintain the read/write timestamps for all files.
>   We can just use that for LRU eviction.**
> - We can find all the files in the folder — **whichever file was least recently used, just delete
>   that** to make space.

```python
fn check_solution(solution):
    pid = solution['problem_id']
    user_info, problem_info = fetch_from_rds(pid)

    file_name = problem_info['file_name']    # get the version from the SQL DB

    if not file_exists(`{file_name}_in.txt`):      # caching logic
        if get_folder_size('.') > 100GB:
             delete(get_oldest_accessed_at_file('.'))    # LRU eviction
        download_from_s3([`{file_name}_in.txt`, `{file_name}_out.txt`])
        # this function will save it on the local HDD

    inputs           = read_file(`{file_name}_in.txt`)   # these reads are from the local HDD
    expected_outputs = read_file(`{file_name}_out.txt`)

    return evaluate(solution.code, inputs, expected_outputs)
```

> 💡 **Elegant re-use:** you don't need to build an LRU data structure at all — the **filesystem
> already tracks access times** (`atime`). The cheapest LRU is the one you don't implement.

---

## 🔀 Load Balancer — & Why Not Multi-threading

### The mental model (memorise this)
> **Ask yourself, "why do we have more than 1 server?"**
> - **Because the data was too large to fit on a single server** → this means the data was
>   **sharded** across the servers → ⭐ **you MUST use Consistent Hashing**
> - **Because the number of requests (compute) was too much for a single server** → this means
>   different servers have the **same data (replication)** → ⭐ **you can just use Round Robin**

### Evaluating the options for Code Judge

| Routing choice | What happens |
|---|---|
| **Round Robin** | Any request can go to any app server. **All app servers will have to cache all 100 problems** that are being solved on any given day. *This seems like a waste (**but is not**)* |
| **Consistent Hashing on `user_id`** | ⭐ **Same thing** — because any user can be solving any problem, and multiple users will be assigned to any server, **every server will have to cache all problems being solved today** |
| **Consistent Hashing on `problem_id`** | Requests for Problem 1 → server 1, Problem 2 → server 2, … ⭐ **Now only server 1 has to cache the testcases for problem 1** |

### Why routing on `problem_id` is a **bad design** ⭐
> - **During a contest, 100k people are solving 5 problems** → out of the **100 app servers, only 5
>   are getting all the load** → ⭐ **uneven load distribution**
> - In our case, **a single server can't even handle multiple requests at the same time**
> - Typically, to handle multiple requests at the same time, we use **multi-threading**…

*(This is the **hot key / celebrity problem** in its purest form: the perfect cache-locality key is
also the worst load-distribution key.)*

### Q: Is multi-threading a good idea here? ⭐ **NO!**
> **We cannot multi-thread the code-judge. Code evaluation is a CPU bound task.**

**What does multi-threading actually do?**
> - **Most programs are I/O bound.** They're waiting for some I/O to happen (user keystroke / mouse
>   click, network download, file read, printer access, …)
> - ⭐ **CPUs are millions of times faster than disks / networks. 99.99% of the time, your CPU is
>   idle.**
> - So you can do multiple things at the same time by **"context switching"** the CPU:
>   ```
>   Do task 1 → task 1 waits for I/O → instead of waiting, CONTEXT SWITCH
>   Start task 2 → task 2 also goes for I/O → context switch back to task 1
>   Do task 1 → …
>   ```

**But for CPU bound tasks** (video processing, heavy computation, analytics, machine learning, SHA
calculation, …):
> ⭐ **Context switching will WORSEN the performance** — because **the CPU is already busy**. If you
> try to break its loop and get it to multi-task, it will slow everything down → **thrashing**.

> ⭐⭐ **Moral: only multi-thread / async-IO *I/O bound* processes. NEVER multi-thread *CPU bound*
> processes.**

### The conclusion
> In code judge, **evaluating a single request requires ~5 seconds**. During those 5 seconds **the
> app server is completely occupied — it cannot handle any other requests.**
>
> ⭐ **Therefore, we want requests to go to the next available server → Round Robin routing.**

```
   ⭐ FINAL ANSWER for Code Judge:
      Local cache (HDD)  +  versioned immutable files  +  LRU eviction  +  ROUND ROBIN
```

---

## 🏆 Case Study 2 — Contest Leaderboard

### What is a leaderboard?
> - **paginated**
> - **ranklist**
> - for each rank, it shows:
>   - **user details**
>   - for each contest problem: **problem details**, and the **user's score & submission details**
>     for that problem

---

## 🧮 Capacity Estimation

### The situation
```
3 hour contest
100,000 participants
5 problems

Assumption: Avg. submissions / participant / problem = 1
```

### Submissions
```
Total submissions during contest
= 1 submission / (participant × problem) × 5 problems × 100,000 participants
= 500,000 submissions during the entire contest

Average submissions per second
= 500,000 / (3 × 3600 seconds)
= 500,000 / 10,000 seconds
= 50 submissions / second

⭐ Peak Load = 2× the average = 100 submissions / second
```
> *(Number of submissions/second during the **start and end** of the contest will be higher than
> average.)*

> These submissions are evaluated by the **code judge** (previous case study). For each request, the
> code judge updates the **final verdict/score in the SQL db**. Based on this collective data, we
> need to compute and show the leaderboard.

### How can we compute the ranklist?
| Data needed | Source |
|---|---|
| What contest is running | `contests` table |
| What users are participating | join `users` × `contests` × `contest_participants` |
| What problems are in this contest | join `problems` × `contests` × `contest_problems` |
| What submissions users have made | join `users` × `user_submissions` × `problems` × `contest_problems` |

> 📝 **H/W:** *do the LLD for this and try to figure out the basic DB schema for these tables
> (columns, indexes, f-key constraints, the not-null constraints, …)*

Then:
```
1. Take all this data
2. AGGREGATE (group by) by user_id
3. Calculate the final score for each user
     (individual submission scores, number of incorrect attempts, time taken to solve, …)
4. SORT the users by the final score
   → The final sorted list is our ranklist
```

### How much data is there?
```
500,000 submissions total during the contest
Each submission detail ≈ 100 bytes (problem id, score, time taken, verdict, user id, contest id, …)

total size = 100 bytes × 500,000 = 50 MB
```

> **The data is not large, but:**
> - ⭐ When we typically make DB queries, **we don't fetch such large amounts of data in a single
>   query** for most use cases. So fetching **50 MB from the DB in a single query is kinda large**
> - ⭐ This data is fetched by **joining 10s of tables**. **Even if we have indexes, the database
>   will take a few seconds (1 to 2 seconds)** to fetch this data

### How long to compute the ranklist?
> Because this is heavy compute, let's say it takes us ⭐ **~5 seconds** to fetch data & compute the
> ranklist.

---

## 🎯 Step 1: Need for Caching

### How frequently is the ranklist queried?
```
Assume each user views the ranklist 20 times (on average) during the contest (once every 10 mins)

Requests / second
= (20 views / user / 3 hours) × 100,000 users
= 2 million views / 3 hours
= 2 million views / 10,000 seconds
= 200 views / second
```

> **Q: Can we calculate the ranklist 200 times/second, when it takes 5 seconds to compute the
> ranklist once?**
> ⭐ **That's stupid.**
>
> **Because the request rate is very high, and the ranklist computation is heavy, we don't want to
> compute it again and again. Hence the need for caching.**

```
   Demand : 200 computations / second
   Supply :   0.2 computations / second  (1 per 5 s)
   ⭐ A 1000× gap. Caching isn't an optimisation here — it's the only way the feature exists.
```

---

## 🏠 Step 2: Cache Type

### Local vs Global — look at the query shape
> **What does a typical query look like?** Either/and of:
> - **show me page 23** (ranks 230 to 239 ⇒ **10 users / page**)
> - **show me my rank**

**What does the query result look like?** A simple JSON file:
```json
[
    {"rank": 1, "user_id": "...", "user_name": "...", "problems": [{"1": "..."}, {"...": "..."}]},
    {"rank": 2, "user_id": "...", "user_name": "...", "problems": [{"1": "..."}, {"...": "..."}]},
    {"rank": 3, "user_id": "...", "user_name": "...", "problems": [{"1": "..."}, {"...": "..."}]},
    {"rank": 4, "user_id": "...", "user_name": "...", "problems": [{"1": "..."}, {"...": "..."}]}
]
```

**How large is this JSON response?**
```
(100 bytes / user entry) × (10 entries / page) = 1 KB / page
```

> ⭐ **We can totally go with a Global cache, because for any request, we will only need to fetch
> 1 KB of data.**

> 🧠 **Contrast with Code Judge!** There, the payload was **1 GB** → global cache was useless.
> Here the payload is **1 KB** → global cache is perfect. ⭐ **The payload size per request decides
> local vs global.**

### Single vs Distributed
```
Total data in the entire ranklist
= (100 bytes / user entry) × (100,000 users)
= 10 MB          ⭐ this is a tiny amount of data!
```
> - **Data is tiny, so a single cache server can store it**
> - **200 queries/second can easily be handled by a single Redis server** — ⭐ **a single Redis
>   server can easily handle up to 100,000 read requests/sec!**
> - The amount of data transferred over the network for each leaderboard page request is only
>   **1 KB** — also very small. So **no extreme n/w overhead** (we only need **200 Kbps** bandwidth
>   for this)

> ⭐ **Since the cached data is tiny and the n/w overhead per request is small, the ideal cache here
> is a Single Global Cache server.**

### Scale vocabulary
| Term | Definition |
|---|---|
| **Low Scale (of data)** | ⭐ Data that **can fit on 1 server** (if in RAM: **≤ 10 GB**; if on disk: **≤ 1 TB**) |
| **High Scale (of data)** | ⭐ Data that **cannot fit on 1 server** |

---

## ⚠️ Interview Advice — Never Name a Technology

> **Note: even though I explicitly said that we can use Redis here, *you* should never do that
> during interviews (never name a specific technology).**
>
> For example, **don't say Kafka or Redis or Postgres**… Instead say **"Persistent Message Queue"**,
> or **"in-memory Key-Value Cache"**, or **"Relational Database"**.

### What happens if you name a technology?
> - ⭐ **This opens the scope for deep-diving into that particular technology**
>   - *why Kafka, why not RabbitMQ or why not SQS?*
> - **You will now have to justify why you've chosen this tech stack**
> - **Now you need to be familiar with multiple technologies** to answer this properly
> - ⭐ **Deep diving during interviews is good — but we, the candidate, want to decide where we deep
>   dive based on our strengths. We don't want the interviewer to decide where to deep dive.**

### So what should you say?
> *"We will use a **single global cache server** here. We need a **fast, in-memory key-value
> cache**… something like Redis or Memcache or something else."*

### If the interviewer says "how will you choose" / "choose one"
> - **I've worked with Redis in the past, so I might prefer that**
> - **But I will see what is being used by other teams, or by other projects in my team** — if my
>   team is already extensively using X, then I should also use X, because **I will benefit from the
>   team's expertise, and the infra is already set up**
> - **I will consider the cost** — maybe Memcached is 2× cheaper than Redis
> - **I will consider what kind of load these things will be able to handle**
> - **I will consider what features they offer**
> - ⭐ **I will research before choosing one.**

> 🧠 This is genuinely excellent interview craft: it shows engineering maturity (team, cost, load,
> features) **while keeping control of the conversation.**

---

## 🔴 Redis

> **The most popular solution for caches (and key-value db) by far.**
> A **very fast, in-memory, key-value database.**

### Why is it fast?
| Reason | Detail |
|---|---|
| **Written in C** | Close to the metal |
| ⭐ **Single threaded** (uses **async-io** instead of threads) | • threads require **locks** for synchronisation, and **locks are extremely slow**<br>• threads have a **high overhead**<br>• **context switching is slow** (because you need to store/restore the thread context) |
| **Lots of low-level optimizations** | |

> 💡 **Connect to the Code Judge lesson:** Redis is **I/O bound**, so it uses **async-IO** rather
> than threads — and it deliberately avoids the context-switching cost we just discussed. Same
> principle, opposite workload.

### In-memory
> - **Uses the RAM**
> - **By default it doesn't store any data on the disk**
> - ⭐ **RAM is almost 100,000× faster than the disk** (for random access)
> - *(optional — not enabled by default)* support for **disk-persistence** (note that this will
>   **reduce write speed**)

### Key-value
> - **no complex joins**
> - **no indexes**
> - **no complex queries**
> - **no search**
> - ⭐ **think of it as a hashmap in memory**

### Powerful primitives
> - support for **complex datatypes**: **sorted sets**, **bloom filters**, …
> - **custom datatypes**
> - **powerful atomic operations**: `inc`

*(**Sorted sets** are especially relevant here — they're the natural Redis structure for a
leaderboard. **Bloom filters** come back in Session 11.)*

### Database
> But **mostly used as a global cache** (single or distributed).

### 📖 Reading
**Mandatory (for everyone)**
- Try online: https://onecompiler.com/redis
- Quick start: https://redis.io/learn/howtos/quick-start
- Cheatsheet: https://redis.io/learn/howtos/quick-start/cheat-sheet

**Optional (mandatory for SDE2 or higher)**
- Tutorial: https://redis.io/university/
- Docs: https://redis.io/docs/latest/
- [Eviction policies & Cluster mode](https://docs.google.com/document/d/1k4nzubvtX_yLctUT4VWK8ZJt4KCcOEdRJdxQgWCaiU8/)

---

## 🔄 Invalidation

### Is immediate consistency good to have?
> **It's always good to have. If we can get immediate consistency without any issues, then why not!**

### What does eventual consistency mean in this context?
> When a user makes a code submission, **their score has changed — the "true" ranklist has changed.**
> **Eventual consistency** would mean the leaderboard **still shows the old (stale) ranks for some
> time** (say 10 mins) even though the true ranks have changed.

### Is immediate consistency critical here?
> ⭐ **No.** If the true ranking of the participants has changed, but the changes don't show up in
> the leaderboard for some time — **that's not the end of the world. That won't cause a bad user
> experience.**
>
> **Eventual consistency is good enough. Immediate consistency is not critical.**

### Is immediate consistency even *possible*? ⭐
> - **How frequently does the "true theoretical" ranking change?** **With every submission!**
> - Peak load = **100 submissions / second** → ⭐ **the true theoretical ranklist changes 100
>   times/second**
> - **It takes ~5 seconds to compute the ranklist once**
>
> ⭐⭐ **It is IMPOSSIBLE to get immediate consistency. Because by the time we calculate the
> ranklist, it has already changed 500 times!**

```
   ranklist changes:  100 / second
   ranklist computes:   1 / 5 seconds
   ⭐ You are 500 changes behind before you even finish. Strong consistency is not "expensive"
      here — it is mathematically unattainable.
```

> 🧠 **Two separate questions, both worth asking:** *is strong consistency **needed**?* and *is it
> even **possible**?* Here the answer is **no** to both — which makes the decision easy and
> defensible.

### How frequently should the ranklist be invalidated?
> How long is the "eventual" / how much delay can I afford — 10 hours? 1 hour? 10 mins? 1 min?
> 10 s? 1 s? 100 ms? 10 ms?
>
> ⭐ **In fact, Scaler invalidates the ranklist every 30 mins. And nobody has complained about it so
> far.**

### TTL vs Write Around
> **Both TTL & Write Around provide eventual consistency.**

| | **TTL** | **Write Around** ✅ |
|---|---|---|
| Ease | **Easy to implement & use** — we're already using Redis, and **Redis has support for TTL** | Needs a separate periodic job |
| The killer problem | ⭐ **The computation is heavy.** If data is not in the cache, **the user's request will have to wait for 5 seconds** to compute the ranklist. **Because computing the ranklist is heavy compute, we shouldn't do it for any individual request** | Computation never happens on the request path |
| Best when | ⭐ **fetching the result from the DB is very easy** | ⭐ **computation is expensive** |

**The chosen design — Write Around:**
> - **Separate app server which runs periodically (every 10 mins)**
> - It will **fetch all submission scores for this contest**
> - **Compute the ranklist**
> - **Store the ranklist in the Redis server**

### What about the initial requests, before the CRON job has run?
> In this case the cache doesn't have the ranklist yet, so **any request should return an error** —
> *"ranklist is not available yet… it will appear after 10 mins."*
>
> ⭐ **Alternatively, you could "warm up" the cache before the contest starts**, so that everyone has
> **rank 1** at the start of the contest (or random ranks).

*(Exactly the write-around "404 on miss" rule from Session 4 — and cache warming from Session 3.)*

---

## 🗂️ Redis Schema

> **What exactly does Redis store?**
> We've **two types of queries** that need to be answered:
> 1. given a page (23rd page), show me the ranks on that page (230 to 239)
> 2. given my `user_id`, show me my rank

⭐ **The design answer: store the data twice, once per access pattern.**

| Key (string) | Value |
|---|---|
| `contest:3:page:1` | `"[{rank: 1, user_id, user_name, problems: […]}, {rank: 2, …}, … 10 entries]"` |
| `contest:3:page:2` | `"[{rank: 11, …}, {rank: 12, …}, … 10 entries]"` |
| … | … |
| `contest:3:page:10000` | `"[{…}, {…}, … 10 entries]"` |
| `contest:3:user:377` | `{rank: 1, user_id: 377, user_name: …, problems: […]}` |
| `contest:3:user:123` | `{rank: 50, user_id: 123, …}` |
| `contest:3:user:2573` | `{rank: 1232, user_id: 2573, …}` |
| `contest:3:user:58` | `{rank: 2, user_id: 58, …}` |
| … | … **100,000 entries** (one for each participant) |

```
Total amount of data in Redis = 10 MB + 10 MB = 20 MB
⭐ (because each user's entry is being stored TWICE — once for page, once for the user)
```

> 🧠 **Denormalisation for access patterns.** In a cache (and in NoSQL — Sessions 9/15) you don't
> normalise; you **store one copy per query shape**. Doubling 10 MB to 20 MB is a trivial price for
> making both queries O(1).

### The read path
> Suppose the user (with `id=1234`) goes to page 23 in the leaderboard. Their request goes to an app
> server in the **Leaderboard Service**. This app server makes **2 reads** from Redis:

```python
pageEntries = redisClient.get("contest:3:page:1")
myRank      = redisClient.get("contest:3:user:1234")
return MakeLeaderboardTable(pageEntries, myRank)
```

### Extending it — filtering by Institution
> **Q: Suppose we want to support filtering by Institution, then how will we support it?**
```
contest:3:institution:IIT-B  ⇒  {institute_name: …, users: [{rank: 1, user_id, …}, {…}, …]}
```
⭐ Same principle: **a new access pattern gets a new key prefix.**

---

## 🗑️ Eviction & Load Balancer

### Eviction
> - **20 MB of data / contest. There's no need of eviction!**
> - Note that we will have to store this data for **every live contest**
> - ⭐ **Once the contest is over, the ranklist for that contest can't change** (no more new
>   submissions) — so the ranklist can just be **dumped in the SQL db itself** (no need to cache the
>   data, because after the contest the number of views for the leaderboard will go down, and since
>   the ranklist doesn't change, you don't need to compute anything)
> - **How many live contests might we run in parallel at any given moment?** **Max 10** (usually 1
>   or 2) → **200 MB of data in total ⇒ still doesn't require eviction**

> ⭐ **Eviction algorithm: once the contest ends (after 24 hours), dump the leaderboard data into the
> SQL db itself.**

*(This is the Session-4 point in action: "**Eviction algorithm is usually not needed** for
write-around data. You will evict it only when the data is no longer required — for example, when
the contest is over.")*

### Load Balancer (for the cache)
> - ⭐ **There's no LB for the cache — the cache is a single Redis server**
> - **If the cache server crashes → no data loss** (the cache doesn't store any "real" data)
> - **We will just restart the cache server, and the cron job will run automatically after 10 mins**
>   (or we can force it to run after the cache server has been restarted)

```
   ⭐ FINAL ANSWER for Leaderboard:
      Single GLOBAL cache  +  WRITE AROUND (10-min cron)  +  no eviction (dump to SQL at contest end)
      +  no cache LB  +  denormalised keys per access pattern
```

---

## 🆚 The Two Case Studies Side by Side

This contrast is the most examinable thing in the session.

| | **Code Judge** | **Leaderboard** |
|---|---|---|
| **Cached payload size** | ⭐ **~1 GB / request** | ⭐ **~1 KB / request** |
| **Total data** | 3 TB (working set 100–200 GB) | 10 MB (20 MB stored) |
| **Cache type** | ⭐ **Local (HDD)** | ⭐ **Single Global** |
| **Why** | Network transfer *is* the problem | Payload tiny; data tiny |
| **Consistency required** | ⭐ **Immediate** | ⭐ **Eventual (30 min in practice)** |
| **Consistency achieved via** | ⭐ **Versioned immutable files** (no invalidation needed!) | ⭐ **Write Around** cron |
| **Why not the textbook policy** | TTL/WA/WB/WT all fail | TTL fails (5 s compute on the request path) |
| **Eviction** | **LRU** using the OS's file access times | ⭐ **None** — dump to SQL when the contest ends |
| **Load balancer** | ⭐ **Round Robin** (CPU-bound, 5 s/request) | No cache LB (single server) |
| **Key lesson** | ⭐ Cache the immutable thing; fetch the mutable pointer | ⭐ Precompute off the request path; denormalise per query |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Throughput** | Average number of tasks completed per unit time |
| **The caching trade-off** | Better best/avg latency; ⭐ **always worse worst-case latency** |
| **5-step cache design** | Need → type (local/global, single/distributed) → eviction → invalidation → LB |
| **Working set** | The subset of data actually being accessed (100–200 problems, not 3 TB) |
| **Local cache on HDD** | Valid! A local disk read still beats a network transfer |
| **Versioning / immutability** | ⭐ Never mutate cached data — publish a new version and swap a small pointer |
| **Immutable data needs no invalidation** | ⭐ The central trick of the Code Judge design |
| **I/O bound** | Task spends its time waiting on disk/network → ⭐ **multi-thread / async-IO is good** |
| **CPU bound** | Task keeps the CPU busy → ⭐ **NEVER multi-thread** (thrashing) |
| **Thrashing** | Performance collapse from excessive context switching |
| **Low / High scale (data)** | Fits on one server (RAM ≤10 GB, disk ≤1 TB) / doesn't fit |
| **Cache warming** | Pre-populating the cache before traffic arrives |
| **Denormalisation for access patterns** | ⭐ Store the same data once per query shape (`page:*` **and** `user:*`) |
| **Redis** | Fast, in-memory, single-threaded, async-IO key-value store; ~100k reads/sec |
| **Interview rule** | ⭐ **Never name a specific technology** — say "in-memory key-value cache" |

---

## 🎯 Session Takeaways

1. **Caching is not free.** It always worsens the **worst-case** read latency and can worsen write
   throughput. **Establish the need first.**
2. ⭐ **Follow the 5 steps every time:** need → type → eviction → invalidation → load balancer.
3. ⭐ **Payload size per request decides local vs global.** 1 GB ⇒ local; 1 KB ⇒ global. A global
   cache does not fix a **network transfer** problem.
4. **Rarity is not a reason to skip a feature** — a once-a-year testcase fix still needs real
   infrastructure, because the cost *when* it happens is enormous.
5. ⭐ **Sometimes no invalidation policy works.** For Code Judge, TTL, Write Around, Write Back and
   Write Through all fail.
6. ⭐⭐ **The fix is immutability + versioning:** cache the big immutable file, always fetch the tiny
   mutable filename from the DB. You get **immediate consistency with zero distributed
   transactions**.
7. **Re-use what already exists** — the OS's file access timestamps *are* your LRU metadata.
8. ⭐ **Never multi-thread a CPU-bound task.** Code judging takes 5 s of pure CPU ⇒ one request per
   server ⇒ **Round Robin**, not consistent hashing.
9. ⭐ **The perfect cache-locality key can be the worst load-distribution key** (`problem_id` during
   a contest) — check for hot keys before sharding on something.
10. ⭐ **Ask both "is strong consistency needed?" and "is it even possible?"** For the leaderboard it
    is *impossible* — the truth changes 100×/s and computing takes 5 s.
11. **Precompute expensive results off the request path** (write-around cron) and **denormalise the
    cache per access pattern** (`page:*` and `user:*`).
12. ⭐ **In interviews, never name a technology.** Say "in-memory key-value cache" and keep control
    of where you deep-dive.

---

## ➡️ Next
**[Session 6 — Facebook Newsfeed, APIs & Microservices](./06_APIs_Microservices_and_Newsfeed.md)** —
HTTP API design practices, building microservices, HTTP vs RPC communication, and the social media
newsfeed.
