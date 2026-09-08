# Session 13 — Case Study: Search Typeahead (Part 2) 🌳

> **Topics:** Approach 1 — Tries · Approach 2 — Hashmap/Key-Value · Sharding · Optimizing the
> system (Batching & Sampling) · Future scope (recency, geolocation, personalisation, typos)
>
> 📄 Class doc: [\[SST-2028\] Case Study: Typeahead-2](https://docs.google.com/document/d/1AjOS8itQOsg6VSjrUbKuiVg_6hsgeSStQKc_39DjTcw/edit?tab=t.0)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [Approach 1 — Tries](#-approach-1--tries)
2. [Trie Sharding](#-trie-sharding)
3. [Approach 2 — Hashmap / Key-Value](#-approach-2--hashmap--key-value)
4. [The Two Databases](#-the-two-databases)
5. [Queries on the Hashmap Design](#-queries-on-the-hashmap-design)
6. [The Write Explosion](#-the-write-explosion)
7. [Optimizing the System — the Decision Table](#-optimizing-the-system)
8. [Batching](#-batching)
9. [Sampling](#-sampling)
10. [Future Scope — Recency](#-future-scope--recency-factor)
11. [Geolocation Personalisation](#-geolocation-based-personalization)
12. [User Personalisation](#-user-based-personalization)
13. [Handling Typos](#-handling-typos)
14. [Key Terms Recap](#-key-terms-recap)

---

## 🌲 Approach 1 — Tries

> **If the user types the partial query `"What"`, then we must show the top 5 search queries that are
> a strict prefix match.**

### The node
> **Each trie node will store:**
> - **children** (all the subsequent letters)
> - **isTerminal**
> - ⭐ **count** (only if `isTerminal` — the number of times this search query has been searched)

```java
class TrieNode {
    TrieNode children[63]    // a-z + A-Z + 0-9 + space
    long count;              // how many times has this
                             // query been searched
}
```

### Queries

**`typeahead(partialQuery)`**
> 1. **Go to the node that matches the `partialQuery`** — start from root, and **for each letter of
>    the `partialQuery` go to the appropriate child**
> 2. **Once we've reached the matching node, all the possible suggestions are within the SUBTREE of
>    this node**
> 3. **We will have to go through the entire subtree** (all possible suggestions that match the
>    prefix) **and find the top 5**

> ⭐⭐ **Going through the entire subtree of a node will be highly time consuming — there are
> potentially BILLIONS of entries in that subtree!**

```
              root
               │
               w
               │
               h
               │
               a
               │
               t ◀── partialQuery ends here
             / | \
            …  …  …   ⭐ must scan the ENTIRE subtree to find the top 5
                         (billions of nodes)
```

### The fix — data augmentation ⭐
> ⭐ **Can improve this by "data-augmentation": at every node, pre-compute & store the top 5
> results.**
> **In this case, the updates will become (slightly) slow.**

**`log_search(searchQuery)`** *(update the count for this query)*
> 1. **traverse to the node that matches this `searchQuery`**
> 2. **increment the count**
> 3. ⭐ **(if augmented, then also update the data for all nodes till root)**

---

## 🔀 Trie Sharding

> **Q: What will be the sharding key?**

### Option A — First letter
> **Every query that starts with the letter `a` will go to the same shard.**
>
> ⭐ *This doesn't mean that the starting letter `a` must get a dedicated shard — a single shard
> might contain multiple starting letters. We're just saying that all queries that start with the
> letter `a` must definitely go in the same shard.*

| Property | Verdict |
|---|---|
| **Cardinality** | ⭐ **Low cardinality (only 26 possible children)** |
| **Distribution** | ⭐ **Uneven data distribution** — *number of queries starting with `a` will be much higher than the number starting with `z`* |

### Option B — First 3 letters
> **Every query that starts with the letters `abc` will go to the same shard.**

| Property | Verdict |
|---|---|
| **Cardinality** | ⭐ **High cardinality: 26³ ≈ 17,000** ✅ |
| **Distribution** | ⭐ **Still uneven** — *number of queries starting with `why` will be much higher than the number starting with `zxz`* |

**The manual fix:**
> ⭐ **To fix the load distribution, we will have to MANUALLY create groups of starting-3-letters in
> order to club the less frequent queries together:**
> - **number of queries starting with `why` will be much higher ⇒ dedicated shard**
> - **number of queries starting with `zxz` will be lower in count, so we group them with other rare
>   starting letters: `zyx` + `zxy` + `zxz` + …**

```
   Shard 1: "why"                    ⭐ one hot prefix gets a whole shard
   Shard 2: "wha"
   Shard 3: "how"
   ...
   Shard N: "zxz" + "zyx" + "zxy" + "qqz" + …   ⭐ many cold prefixes share one shard
```

### The killer problem ⭐
> **Q: Which existing Databases support this?**
>
> ⭐⭐ **There's no popular database that was built for storing tries!**
>
> **Tries exist as a 3rd-party extension in some popular databases. However, no database was built
> specifically to store tries.**
>
> ⭐⭐ **So you must build your own DB.**

> 🧠 **This is the real reason the trie loses.** It's not that the trie is algorithmically wrong — it's
> arguably ideal. It's that **you'd have to write, shard, replicate and operate a bespoke database**,
> and manually rebalance shards by prefix frequency. That is an enormous engineering cost for a
> problem that has a much cheaper answer.

---

## 🗺️ Approach 2 — Hashmap / Key-Value

> ⭐⭐ **The reframing that solves the problem:**
>
> - **As a DSA person**, we would create a Trie, and **augment** the TrieNode with data. This data
>   will store the **top 5 suggestions** for each TrieNode.
> - ⭐⭐ **As an HLD person, we will realize that effectively, we're just CACHING the top-5 results for
>   each possible "prefix".**
>
> ```
>   prefix            ==  TrieNode
>   data-augmentation ==  cache
> ```
>
> ⭐ **So we can store this as a separate cache!**

> 🧠 **This is the single most valuable idea in the case study.** The trie's *structure* was never the
> point — the **augmented top-5 at each node** was doing all the work. And a "value stored at each
> prefix" is just… **a key-value pair**. The tree collapses into a hashmap.

---

## 🗄️ The Two Databases

| | **Search Frequency DB** | **Top Suggestions DB** (cache) |
|---|---|---|
| **Stores** | ⭐ **for each actual `searchQuery`, its count** | ⭐ **for each possible PREFIX (for which our system will show suggestions), the top k suggestions** |

### Search Frequency DB
| Search Query | Count |
|---|---|
| what is the color of the sky | 5000 |
| what is the day today | 1000 |
| what is 2 + 2 | 10000 |
| what does the fox say | 2000 |
| what does a fox eat? | 1900 |
| how to kill someone | 2000 |
| how to cook eggs | 1500 |
| how to sing | 500 |

### Top Suggestions DB (k = 3)
| Prefix (partial query) | Top k suggestions |
|---|---|
| `wha` | `what is 2+2 ⇒ 10000` · `what is the color of the sky ⇒ 5000` · `what does the fox say ⇒ 2000` |
| `what` | `what is 2+2 ⇒ 10000` · `what is the color of the sky ⇒ 5000` · `what does the fox say ⇒ 2000` |
| … | … |
| `what i` | `what is 2+2 ⇒ 10000` · `what is the color of the sky ⇒ 5000` · `what is the day today ⇒ 1000` |
| `what d` | `what does the fox say ⇒ 2000` · `what does a fox eat? ⇒ 1900` |
| `how` | `how to kill someone ⇒ 2000` · `how to cook eggs ⇒ 1500` · `how to sing ⇒ 500` |
| … | … |
| `how to k` | `how to kill someone ⇒ 2000` |

---

## 🔍 Queries on the Hashmap Design

### `typeahead(partial_query)` — beautifully simple
> **If someone types `"what i"` then we can just go to the suggestions db, and look up that
> `partialQuery`.**
>
> ⭐ **This will be very fast:**
> - **hashmaps have O(1) lookup**
> - ⭐ *in reality, the complexity is O(l) where l is the length of the key. But the assumption is
>   that **your keys in a hashmap should NEVER be long**. If your hashmap keys are long, then you're
>   using hashmaps incorrectly.* **In our case, the average key length was assumed to be 10 chars,
>   and the max length was assumed to be 50 chars**
> - ⭐ **we don't need any computation / processing — we just have to get the value for the given key
>   from the key-value DB**

**Does it meet the NFRs?**
> **We needed ultra low latency (< 10 ms), and high read throughput (10 million reads/second at
> peak):**
> - ⭐ **Redis lookup has latency of ≤ 1 ms** ✅
> - ⭐ **A single Redis server can easily handle 100,000+ reads/writes per second!**
> - ⭐ **⇒ just need ~100 Redis servers**
> - 😄 *(Google has over 10 million servers — as of 2020)*

```
   10,000,000 reads/sec  ÷  100,000 reads/sec/server  =  ⭐ 100 servers
```

### Sharding — free ⭐
> ⭐ **Sharding is automatic — based on `hash(key)`.**
>
> **Q: Are there databases that have 1st class support for hashmaps?**
> ⭐ **Yes. Not just 1 — there's an entire category!**
>
> **Q: Which existing Databases support this?**
> ⭐ **Key-Value databases are basically just hashmaps that are distributed across servers:
> Redis / Memcached / DynamoDB / …**

> ⭐⭐ **Compare with the trie:** *"you must build your own DB"* vs *"there's an entire category of
> databases for this, and they shard themselves."* **This is why Approach 2 wins.**

---

## 💥 The Write Explosion

### `log_search(search_query)`
> **Whenever someone searches for `"what does the fox say"`:**
>
> **1. I need to update the count in the search frequency database**
> - ⭐ **super simple — just call `redis.inc(searchQuery)`**
>
> **2. I need to update the cache (top suggestions database)** — **what all entries do I need to
> update?**
> - **If I'm updating the count for `what does the fox say`, then is it possible for the suggestions
>   of the prefix `"how"` to get changed?** ⭐ **No.**
> - ⭐ **What prefixes will get affected? Only the PREFIXES OF THE SEARCH QUERY:**
>   ```
>   wha
>   what
>   what d
>   ...
>   what does the fox
>   what does the fox s
>   what does the fox sa
>   what does the fox say
>   ```
> - ⭐ **How many such prefixes (on average) need to be updated?** **The average query is 10 letters.
>   So ~10 prefixes on average need to be updated**

### The arithmetic ⭐
> ⭐ **But this now means that for each update, I must do 1 + 10 writes.**
```
total number of writes in redis
= (1 million log_search / sec) × 11 writes / log_search
= ⭐⭐ 11 million writes / second
```
> ⭐⭐ **This makes my system BOTH read & write heavy!**
> ⭐⭐ **There is no DB in the world that is optimized for both reads & writes.**

### Worked example of an update
When `what does a fox eat?` goes from **1900 → 2100**, it overtakes `what does the fox say` (2000),
so the ordering flips in every affected prefix:

| Prefix | Top suggestions **after** the update |
|---|---|
| `wha` | `what is 2+2 ⇒ 10000` · `what is the color of the sky ⇒ 5000` · **`what does a fox eat ⇒ 2100`** · `what does the fox say ⇒ 2000` |
| `what d` | **`what does a fox eat? ⇒ 2100`** · `what does the fox say ⇒ 2000` |
| `what do` | **`what does a fox eat? ⇒ 2100`** · `what does the fox say ⇒ 2000` |
| `what i` | *(unchanged)* |
| `how` | ⭐ *(unchanged — not a prefix of the updated query)* |

---

## ⚙️ Optimizing the System

⭐⭐ **A genuinely reusable decision table. Memorise this.**

### If the system is **Read Heavy** (not write heavy)
| Consistency | Strategy |
|---|---|
| **Eventual consistency is okay** | ⭐ **Absorb the reads in the cache, and optimize the DB for writes** |
| **Immediate consistency is needed** | Either ⭐ **incur extra write latency by using a write-through cache** (and your DB will be optimized for writes), **or** ⭐ **optimize the DB for reads** — in this case the writes will be slower, but that's okay because the writes are fewer. Both reads & writes now go to the DB. **This will be slower than the cached approach** |

### If the system is **Write Heavy** (not read heavy)
> ⭐ **Irrespective of eventual vs immediate consistency ⇒ optimize the DB for writes.**
> - **If your reads are significant, you can absorb the reads in the cache.** If not significant,
>   then let them go to the DB, and let the reads be slow
> - ⭐⭐ **Your cache CANNOT handle the writes — because that would lead to data loss if the cache
>   server crashes with unsynced changes (write-back cache)**

### If the system is **both read & write heavy**
> ⭐⭐ **very VERY difficult!**
>
> **Either you can somehow "REDUCE" the writes:**
> - ⭐ **Batching** — **forces eventual consistency.** *Wait for a bunch of requests to collect, and
>   then process them in 1 go*
> - ⭐ **Sampling** — **forces data loss.** *Don't process all the requests… process only some of them*
>
> **If you cannot reduce the writes, then you need to SHARD MORE:**
> - ⭐ **sharding improves both reads & writes!**
> - **but then you can't join across shards efficiently** — if some query needs data from multiple
>   shards, that will be slow

```
   ┌────────────────────────────────────────────────────────────────────┐
   │  BOTH read & write heavy?                                          │
   │     1. ⭐ REDUCE the writes:  Batching (⇒eventual) / Sampling (⇒loss)│
   │     2. ⭐ Else SHARD MORE      (helps reads AND writes)              │
   └────────────────────────────────────────────────────────────────────┘
```

> ⭐ **Notice how the NFRs from Session 12 pay off:** we established that typeahead tolerates **both**
> stale reads **and** data loss. That means **both** levers — batching *and* sampling — are legal
> here. Most systems can only use one, or neither.

---

## 📦 Batching

> ⭐ **We can reduce the number of writes significantly, because we can afford eventual consistency &
> data loss (non-functional requirements).**

### What batching is
> ⭐ **Instead of doing each task 1 by 1, you wait for a lot of tasks to pile up. And then you do all
> of them in 1 go as a batch.**
>
> **Example: if you have 10 guests at your house, and you need to serve tea:**
> - **make a cup of tea, serve it. Make the next cup of tea, serve it…** → individual request
>   processing
> - ⭐ **make a batch of tea in 1 go… and then serve it together → Batching!**

### Applied
> ⭐ **Whenever we get a `log_search(search_query)` request, instead of updating the suggestions db
> immediately, we wait for the count to increase by a fixed amount (say 1000).**

**Earlier:**
```python
fn log_search(search_query):       # 1 million qps
    frequency_db.inc(search_query) # 1 million writes/s
    update_prefixes(search_query)

fn update_prefixes(search_query):
    for i = 3 ... len(search_query) - 1   # 10 iterations
        prefix = search_query[:i]
        ... logic to update the suggestions list
            in the suggestions db
        # 10 million writes/s
```

**With batching:** ⭐
```python
fn log_search(search_query):       # 1 million qps
    updated_count = frequency_db.inc(search_query)
    # 1 million writes/s

    if updated_count % 1000 == 0:
          # ⭐ update the prefixes only if the count
          # has changed by the batch size
    update_prefixes(search_query)

fn update_prefixes(search_query):
    ...   # (1 million / 1000 qps) × 10 updates
          # ⭐ 10,000 writes/sec
```

### The savings
| | Frequency DB | Suggestions DB | **Total** |
|---|---|---|---|
| **Earlier** | 1 million writes/sec | **10 million** writes/sec | ⭐ **11 million writes/sec** |
| **After batching** | 1 million writes/sec | **10,000** writes/sec | ⭐ **1.01 million writes/sec** |

> ⭐ **Effectively, we will only update the suggestions when the count increases by 1000.**
>
> ⭐⭐ **Note: we cannot make the number of writes less than 1 million per second, because that's the
> number of times we have to update at least the counts in the frequency database.**
>
> ⭐⭐ **Note: batching doesn't cause DATA LOSS (freq data is always up-to-date) — it just causes
> DELAYS (stale reads) in the suggestions updates.**

> 💡 **The `% 1000 == 0` trick is elegant** — it needs no timers, no queues, no buffers. The counter
> *itself* is the batch boundary.

---

## 🎲 Sampling

### The intuition — exit polls
> **Exit polls during elections:**
> - **country-wide election: 1 crore voters**
> - **the actual counting will take several days**
> - **News channels want to predict the winner with high accuracy before the actual results are
>   announced**
> - **The news channels will ask various people "who did you vote for" and they will create their own
>   voting list & winners**
>
> **Can the news channels talk to all the 1 crore voters?** ⭐ **No.**
> - **They stand in front of a small fraction of the polling booths**
> - **As the people exit the booths, they will ask a few random people "who did you vote for"**
> - ⭐ **They will only use this small subset/sample of data to "estimate" the winner**
> - ⭐ **If the news channel is unbiased, their exit poll results will almost perfectly match the
>   actual election results**

> ⭐⭐ **The principle: If you draw an UNBIASED sample from a population, then any TRENDS that hold
> within the population will also hold within the sample.**
>
> ⭐ **Typically a good way of getting unbiased samples is to just sample UNIFORMLY AT RANDOM.**
>
> ⭐ **Note: Sampling CAN cause data loss of individual data points. But it won't lose the overall
> trends. (use it only when data loss is okay)**

### Applied — and note *where* the change goes ⭐

**Earlier:**
```python
# search service
fn search(query):
    ...
    make an API call to typeahead service's log_search endpoint

# typeahead service
    fn log_search(search_query):
        frequency_db.inc(search_query)
        update_prefixes(search_query)

    fn update_prefixes(search_query):
        for i = 3 ... len(search_query) - 1
            prefix = search_query[:i]
            ... logic to update the suggestions list in the suggestions db
```

**With sampling:** ⭐
```python
# search service
fn search(query):
    ...
    if rand() < 0.001:
        # ⭐ with a probability of 0.1% make the following call
        make an API call to typeahead service's log_search endpoint

# typeahead service
     ...   # UNCHANGED
```

> ⭐⭐ **Note the sampling happens in the SEARCH service, not the typeahead service** — so the network
> call itself is avoided 99.9% of the time. You save the API call, not just the DB write.

> - **For 99.9% of the searches, we're not even updating the counts (just ignore them)**
> - **For a random 0.1% of the searches, we call `log_search` and update both the counts & the
>   suggestions**
>
> ⭐⭐ **Thanks to sampling, instead of having 1 million + 10 million writes/second, we now come back
> to just (1 million + 10 million) / 1000 = 10,000 writes / second.**

### The three objections, answered
| Objection | Answer |
|---|---|
| **Won't the counts be inaccurate?** | ⭐ **Yes.** Effectively, each count is being **divided by approx. 1000** (but not exactly — it's random) |
| **Won't the suggestions be not exactly in order?** | ⭐ **Yes.** **But none of that matters. Because still, the suggestions shown to the users will continue to be highly relevant!** |
| **If we use sampling, won't infrequent queries have very low counts / be completely missed?** | ⭐⭐ **Yes, that can happen! That's a FEATURE, not a bug!** **A rare query will never be a part of typeahead suggestions anyway (because it is not popular).** ⭐ **Effectively, sampling has automatically reduced your data massively by removing the majority (99.9%) of the bad queries** 🙂 |

### Batching vs Sampling
| | **Batching** | **Sampling** |
|---|---|---|
| Mechanism | Update the suggestions only every Nth increment | Only process a random fraction of requests |
| Forces | ⭐ **Eventual consistency** (delays) | ⭐ **Data loss** |
| Frequency DB accuracy | ⭐ **Exact** | ⭐ **Approximate (÷1000)** |
| Writes after | **1.01 million/sec** | ⭐ **10,000/sec** |
| Floor | Can't go below the 1M count-increments | ⭐ **No floor — scales all the way down** |
| Side benefit | — | ⭐ **Automatically discards 99.9% of junk queries** |

> 🧠 **They compose.** In production you would likely do **both**: sample at the search service to cut
> the request volume, then batch the prefix updates on what survives.

---

## 🔮 Future Scope — Recency Factor

### Problem statement
> **Suppose there's a big event that happens:** COVID lockdown gets declared · Election results are
> out · Some high-profile person got arrested · Federer won the Wimbledon · …
> **This is a trending event.**
>
> ⭐ **Even though `"why is the sky blue?"` might have a higher overall count, since the query
> `"what happened in Nepal?"` is trending (recent + popular), we should rank that higher when someone
> types `"wh"`.**

### Approach 1 — Separate counts per window
> **For each query, we maintain three counts:** **Total Count**, **Last Week Count**, **Last Day
> Count**
```
total:why is the sky blue?     ⇒ 5000
 week:why is the sky blue?     ⇒  200
  day:why is the sky blue?     ⇒   50
total:what happened in Nepal?  ⇒  500
 week:what happened in Nepal?  ⇒  300
  day:what happened in Nepal?  ⇒  100
```
> **To find the top-k suggestions:**
> 1. **Find top-k from total**
> 2. **Find top-k from weekly**
> 3. **Find top-k from daily**
> 4. **Merge the results based on some scoring function**

### Approach 2 — Exponential decay ⭐ (the elegant one)
> **Goal: give more weightage to the recent counts.**
>
> ⭐ **Solution: simply DECAY the historical counts after every fixed period of time. After each day,
> decrease the total count for each query by 10%.**

**A steadily popular query — `"who has control over nukes?"`** with 1000 searches/day:
```
raw counts: [1000, 1000, 1000, …, 1000]  ⇒ true total is 100,000

day 1: 1000
day 2: 90% of 1000 + 1000  ⇒ 1900
day 3: 90% of 1900 + 1000  ⇒ 2710
day 4: 90% of 2710 + 1000  ⇒ 3439
...
day 100: 1000 × (1 + 0.9 + 0.9² + 0.9³ + …)
       = 1000 × 1/(1 - 0.9)
       = ⭐ 10,000     (a geometric series — it CONVERGES)
```

**A trending query — `"who won the wimbledon"`** with nothing for 97 days then 5000/day:
```
raw counts: [0, 0, 0, …, 5000, 5000, 5000]  ⇒ true total is just 15,000

day 97 : 0
day 98 : 5000
day 99 : 5000 × 0.9 + 5000  ⇒  9,500
day 100: 9500 × 0.9 + 5000  ⇒ ⭐ 13,550
```

> ⭐⭐ **The magic:** the steady query has a **true count of 100,000** but a decayed score of
> **10,000**; the trending query has a true count of only **15,000** but a decayed score of
> **13,550**. **Recency has been baked directly into a single number** — no separate windows, no
> merge function, no scoring heuristic.
>
> **And it self-cleans:** ⭐ **if the count after decay reduces below a threshold (say 0) then we can
> remove that entry.**

---

## 🌍 Geolocation-based Personalization

> - **Given the user's request, find out their location based on IP address**
> - ⭐ **Build a separate database for each location ⇒ shard the DB by `country_id`**
> - **Now an Indian user's request will only go to the Indian shard**

```
"global:what does the fox say"  ⇒ 1000
"India:what does the fox say"   ⇒   10
"USA:what does the fox say"     ⇒   10
```

> ⭐ **When an Indian user types `"wha"`:** find the suggestions for the `"wha"` prefix, **and** the
> suggestions for the `"India:wha"` prefix, **merge the results**, and then return the final set.

> 💡 Note the key-prefix trick: **the same key-value store handles global and per-country data** just
> by namespacing the key. No new infrastructure.

---

## 👤 User-based Personalization

> ⭐ **Do this purely on the CLIENT side:**
> - **The browser stores the user's search/browsing history**
> - **browser will create typeahead suggestions from the user's local data**
> - **browser will initiate a backend request to get the global typeahead suggestions**
> - ⭐ **browser will merge these two lists**
>
> ⭐ *Google actually pulls this from the backend too — because it does maintain your search &
> browsing history in the backend DB.*

> 🧠 **Why client-side is the right first answer:** per-user suggestions would multiply your key space
> by the number of users (billions of extra keys), for data only one person will ever read. Pushing
> it to the client costs the backend **nothing**.

---

## ✏️ Handling Typos

> - ⭐ **Whenever a search is made, apart from updating the count of the `search_query`, you also
>   update the count of the `spell_corrected(search_query)`**
> - ⭐ **Whenever a user types something, you find the suggestions for `partial_query`, but you also
>   include the suggestions for `spell_corrected(partial_query)`**

```python
def spell_corrected(input: str) -> str:
    """Corrects the spellings of the words within
       the input string, and returns the corrected
       string.
       Note:
           - each word in the input is spell corrected
           - gracefully handles partial words
    """
```

> ⭐ **You can simply have a dictionary and you can calculate the "EDIT-DISTANCE" between the user's
> words and the words in the dictionary.**
>
> 📖 **Peter Norvig — *How to Write a Spelling Corrector*:** https://norvig.com/spell-correct.html

---

## 🖼️ The Final Design

```
                                         ┌──────────────────────────────┐
   User types "what i"  ───────────────▶ │  /typeahead service          │
       (2M req/s avg, 10M peak)          │  O(1) key-value lookup        │
                                         └──────────────┬───────────────┘
                                                        │  < 1 ms
                                                        ▼
                                    ┌───────────────────────────────────────┐
                                    │  TOP SUGGESTIONS DB (cache)           │
                                    │  key: prefix → value: top-5 list      │
                                    │  ⭐ ~100 key-value servers, auto-sharded│
                                    └───────────────────────────────────────┘
                                                        ▲
                                                        │ batched prefix updates
                                                        │ (only every 1000th count)
   User searches ───▶ ┌──────────────────┐              │
                      │ /search service  │              │
                      │ ⭐ if rand()<0.001│              │
                      └────────┬─────────┘              │
                               │ async log_search        │
                               ▼                         │
                    ┌────────────────────────┐           │
                    │ SEARCH FREQUENCY DB    │───────────┘
                    │ key: query → count     │
                    │ ⭐ write-optimised (LSM)│
                    └────────────────────────┘
```

| Decision | Choice | Why |
|---|---|---|
| Data structure | ⭐ **Key-value (hashmap), not a trie** | No DB exists for tries; KV DBs auto-shard |
| Two stores | **Frequency DB** + **Top-Suggestions DB (cache)** | Separate the write path from the read path |
| Read path | O(1) lookup, **< 1 ms**, ~**100 servers** | Meets the < 10 ms NFR |
| Sharding | ⭐ **automatic via `hash(key)`** | Free with any KV database |
| Write reduction | ⭐ **Sampling (0.1%) + Batching (every 1000)** | 11M writes/s → **10,000 writes/s** |
| Recency | ⭐ **Exponential decay (×0.9 daily)** | One number captures both popularity and recency |
| Geo | Namespaced keys (`India:wha`) + merge | No new infrastructure |
| Personalisation | ⭐ **Client side** | Avoids billions of per-user keys |
| Typos | Also index & query `spell_corrected(...)` | Edit distance against a dictionary |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Trie** | Prefix tree; node stores children + `isTerminal` + **count** |
| **Data augmentation** | ⭐ Precompute & store the **top 5** at each node — makes reads fast, writes slower |
| **Trie sharding** | By **first letter** (low cardinality, uneven) or **first 3 letters** (26³≈17,000, still uneven → **manual grouping** of rare prefixes) |
| ⭐ **Why tries lose** | ⭐⭐ **No popular database was built to store tries — you'd have to build your own DB** |
| ⭐ **The reframe** | ⭐⭐ **prefix == TrieNode, data-augmentation == cache** ⇒ it's just a **key-value store** |
| **Search Frequency DB** | `searchQuery → count` |
| **Top Suggestions DB** | `prefix → top-k suggestions` (the cache) |
| **Hashmap key length rule** | ⭐ Keys should **never be long** — if they are, you're using hashmaps wrong |
| **Redis capacity** | **≤ 1 ms** latency; **100,000+ ops/sec/server** ⇒ **~100 servers** for 10M req/s |
| **KV databases** | Redis / Memcached / DynamoDB — ⭐ **hashmaps distributed across servers, auto-sharded** |
| ⭐ **The write explosion** | 1 count write + ~10 prefix writes = **11 million writes/sec** |
| **Read-heavy strategy** | ⭐ Cache the reads, **write-optimise the DB** |
| **Write-heavy strategy** | ⭐ Always write-optimise the DB; **the cache can never absorb writes** (write-back ⇒ data loss) |
| **Both heavy** | ⭐⭐ Reduce writes (**batching** / **sampling**) or **shard more** |
| ⭐ **Batching** | Update only every Nth increment ⇒ **forces eventual consistency**, no data loss; 11M → **1.01M** writes/s |
| ⭐ **Sampling** | Process a random 0.1% ⇒ **forces data loss**, keeps **trends**; 11M → **10,000** writes/s |
| **Unbiased sample principle** | ⭐ Trends in the population hold in a uniformly random sample |
| ⭐ **Exponential decay** | Multiply all counts by 0.9 daily — ⭐ **bakes recency into a single number**; geometric series converges; drop entries below a threshold |
| **Geo personalisation** | Namespace keys (`India:wha`) and merge with global |
| **User personalisation** | ⭐ Do it **client side** — avoids billions of per-user keys |
| **Typo handling** | Index and query `spell_corrected(...)`; **edit distance** vs a dictionary |

---

## 🎯 Session Takeaways

1. **A trie is the natural DSA answer** — but reading the top-5 means scanning a subtree of billions,
   so you must **augment each node** with its precomputed top-5.
2. **Trie sharding is painful:** first letter has cardinality 26; first-3-letters gives 17,000 but is
   still skewed, forcing **manual grouping** of rare prefixes.
3. ⭐⭐ **Tries lose for an engineering reason, not an algorithmic one: no database exists for them —
   you'd have to build and operate your own.**
4. ⭐⭐ **The winning reframe: `prefix == TrieNode` and `augmentation == cache`.** The trie collapses
   into a **key-value store**, which an entire category of databases already implements and shards
   automatically.
5. ⭐ **Two stores:** a **frequency DB** (`query → count`) and a **top-suggestions cache**
   (`prefix → top-k`). Reads hit only the cache — **O(1), < 1 ms, ~100 servers**.
6. ⭐ **Hashmap keys must be short** — that's why a 10-char average query is fine as a key.
7. ⭐⭐ **The write explosion:** one search updates 1 count **+ ~10 prefixes** = **11 million
   writes/sec**, making the system **both read- and write-heavy** — which no database can serve.
8. ⭐ **Memorise the optimisation table:** read-heavy ⇒ cache reads + write-optimise the DB;
   write-heavy ⇒ write-optimise (**never let the cache take writes**); both ⇒ **reduce writes or shard
   more**.
9. ⭐ **Batching forces eventual consistency but loses no data** (11M → 1.01M writes/s), and the
   `count % 1000 == 0` check needs no extra machinery.
10. ⭐⭐ **Sampling forces data loss but preserves trends** (11M → 10,000 writes/s), belongs in the
    **search** service so the API call is skipped too, and **discarding rare queries is a feature**.
11. ⭐⭐ **Exponential decay (×0.9/day) captures recency in one number** — a steady 100,000-count query
    scores 10,000 while a 15,000-count trending query scores 13,550.
12. ⭐ **Push personalisation to the client** and handle **geo by namespacing keys**; both avoid adding
    backend scale.

---

## ➡️ Next
**[Session 14 — Case Study: Messaging Applications](./14_Case_Study_Messaging_Applications.md)** —
FB Messenger, WhatsApp and Slack.
