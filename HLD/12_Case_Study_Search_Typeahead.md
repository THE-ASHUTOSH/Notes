# Session 12 — Case Study: Google Search Typeahead (Part 1) 🔎

> **Topics:** How to approach a design problem · Problem statement · Functional & Non-functional
> requirements · Scale estimation
>
> 📄 Class doc: [\[SST-2028\] Case Study: Google Search Typeahead](https://docs.google.com/document/d/11YhxJwEiwWLVUoSAfFEacY0e49hb7zg_enOLpsIvNIc/edit?tab=t.0)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [DSA vs Design Interviews](#-dsa-vs-design-interviews)
2. [The 5-Step Design Approach](#-the-5-step-design-approach)
3. [Problem Statement — Reason by Analogy](#1️⃣-problem-statement--reason-by-analogy)
4. [Typeahead vs Autocomplete](#-typeahead-vs-autocomplete)
5. [Functional Requirements](#2️⃣-functional-requirements-fr)
6. [What to Avoid](#-what-to-avoid)
7. [Hidden Features](#-hidden-features)
8. [Data Source & Flow](#-data-source--flow)
9. [Non-Functional Requirements](#3️⃣-non-functional-requirements-nfr)
10. [Scale Estimation](#4️⃣-scale-estimation)
11. [Read Heavy or Write Heavy?](#-read-heavy--write-heavy)
12. [Key Terms Recap](#-key-terms-recap)

---

## 🎯 DSA vs Design Interviews

| | **DSA Interviews** | **Design Interviews** |
|---|---|---|
| Problem statement | ⭐ **Concrete — well defined** | ⭐ **Extremely vague** — *"Design Typeahead"*, and **you might not even know what typeahead is** |
| Examples | **Example input-output pairs** given | — |
| Solution shape | **Idea about the kind of solution that will work** | ⭐ **Very open ended** — the discussion can go in **any direction**; depends on **your expertise** *and* **the interviewer's expertise** |
| Constraints | **Input constraints** given — e.g. *array of integers of size 10⁶ ⇒ can you use O(n²)? No. Max O(n log n)* | You must **derive** the constraints yourself |
| Time | Time constrained | ⭐ **Still time constrained — 45 mins** |

### What you must do in a design interview
> - **Figure out what you're supposed to build**
> - ⭐ **Figure out what the interviewer wants**
> - **Build that solution**
> - ⭐ **Take on sufficiently complex things so that you can showcase your skills & impress the
>   interviewer**

### The DSA approach (for contrast)
```
Problem Statement → Examples (solve it by hand) → Brute Force → Draw observations → Optimized
```

---

## 🪜 The 5-Step Design Approach

```
┌──────────────────────────── 20–25 mins ────────────────────────────┐
│  1. Problem Statement                                              │
│  2. Functional Requirements          (FR)                          │
│  3. Non-functional Requirements      (NFR)                         │
│  4. Scale Estimation                                               │
└────────────────────────────────────────────────────────────────────┘
┌──────────────────────────── 25–20 mins ────────────────────────────┐
│  5. API Design                                                     │
│  6. System Design                                                  │
└────────────────────────────────────────────────────────────────────┘
```

> ⭐ **Note the time split: nearly HALF the interview goes on understanding the problem before you
> draw a single box.** That is deliberate — a beautiful design for the wrong problem scores zero.

---

## 1️⃣ Problem Statement — Reason by Analogy

> ⭐ **Reason by analogy:** **find existing companies / systems that offer a similar product /
> feature.** It **gives you an overview of the umbrella of different scopes that you can consider.**

> **Typeahead is a specific form of autocomplete** — *try to type ahead of the user.*
> - **Typeahead in Google**
> - **Typeahead in Amazon**
>
> ⭐ **Typeahead & Search are different products — but typeahead is always followed by some form of
> search.**

### What NOT to build
> **Autocomplete is available in many different settings:**
> - **Smartphone Keyboards:** word completion / contacts / …
> - **Text editors / Code editors:** **IntelliSense** (complete next token), **GitHub Copilot** (can
>   show entire functions)
> - **Grammarly:** sentence completion while prose writing
> - **Gmail / Outlook:** sentence completion for writing mail; **to/cc/bcc** email completion from
>   contacts

---

## 🆚 Typeahead vs Autocomplete

> ⭐⭐ **The key difference:**
>
> | | **Autocomplete** | **Typeahead** |
> |---|---|---|
> | Scope | ⭐ **Typically LOCAL to your machine** | ⭐ **Always associated with SEARCH** |
> | Suggestions are | ⭐ **Specific to YOU** | ⭐ **The most popular queries searched GLOBALLY in the past, that match the given prefix** |
> | Standalone? | ⭐ **Yes, standalone** | No — feeds into search |

> 🧠 **This single distinction defines the entire system.** "Globally popular past queries" tells you
> immediately that you need (a) a **global count** of every search query ever made, and (b) a way to
> find the **top-k by count among all strings sharing a prefix**. Everything in Session 13 follows
> from that sentence.

---

## 2️⃣ Functional Requirements (FR)

### MVP — Minimal Viable Product
> - **Minimal:** minimal set of features to achieve viability
> - **Viable:** should demonstrate the core features & usability
> - **Product:** solve a genuine problem

### Actors
> - **End User:** the person doing the Google search

### MVP Features
> ⭐⭐ **Always keep the "minimal" in your mind. MVP features is NOT a feature-suggestion
> competition.**

Three buckets:

| Bucket | Meaning |
|---|---|
| ⭐ **MVP features** | **perfect for discussion** — **(v0)** |
| **Future Scope** | **good to have, but not absolutely necessary** — **(v1+)** |
| ⭐ **Bad** | **get yourself rejected in an interview** — **(v-never)** |

### ✅ MVP (v0)
| Feature | Notes |
|---|---|
| **As the user is typing in the search-box, we should auto-complete their search query. We should show "typeahead" suggestions** | ⭐ `typeahead(partial_query) => suggestions_list` — **user-facing** |
| **The suggestions shown in typeahead are popular searches that other people have made in the past** | ⭐ `log_search(search_query) => void` — **internal** |
| ⭐ **We will limit to showing only top 5, relevant suggestions** | **relevant:** any suggestion should be a **prefix match** with the `partial_query`. **top 5:** we keep track of the **number of times a search_query has been searched for (globally)**; given a `partial_query`, show the search_queries that are a prefix match **and have the highest count** |
| **With every letter that the user types, the typeahead suggestions should change** | ⭐ **we will update the typeahead with every letter — send a new API request with every letter typed** |
| ⭐ **We will start showing typeahead suggestions only after the user has typed at least 3 letters** | **otherwise, we will probably show irrelevant results** |
| ⭐ **…and if the user's query is at most 50 letters** | 😄 *most likely, they've slept on the keyboard* |

### 🔜 Future Scope (v1+)
| Feature |
|---|
| **Typeahead results should be personalized** — **geolocation**, **user's browsing/search history** |
| **Results should take recency/news factor into consideration** (**trending topics**) |
| **Fix typos / Spell-correct the user's `partialQuery`** before showing the typeahead results |
| **Even when the user has typed < 3 characters, we should suggest the "trending" global searches / previous recent searches by the user** |
| **User-age based personalization** — e.g. query `"why is s"`: **5 years ⇒ "why is sky blue"**, **30 years ⇒ "why is scotch smooth"** 😄 |
| **Grammar-correct the user's `partialQuery`** |
| **Provide suggestions as per the law of the land** *(what??)* |

### ❌ Bad (v-never) — frontend-only features
| Feature | Why it's bad |
|---|---|
| **Display a textbox in which the user can type something** | **(frontend)** |
| **Clicking a typeahead suggestion should lead to a search** | **(frontend)** |
| **While showing the suggestions, the part that has already been typed should be highlighted** | **(frontend)** |
| **After giving suggestions, if the user presses tab it should copy the query into the text box** | **(frontend)** |

---

## 🚫 What to Avoid

> ⭐ **Avoid anything that doesn't affect our backend infra / system design:**
>
> - ⭐ **frontend features** — they don't affect our backend infra / system design; **purely cosmetic**
> - ⭐ **common features that are not the core of the system that we're trying to build:**
>   - *design Uber* → **we require authentication** — ⭐ *is authentication what the interviewer is
>     asking you to design? **No — it's just a dependency***
>   - *we require payments* → ⭐ **when the interviewer asks us to design Uber, they're not asking us
>     to design payments**
>   - ⭐ **We will assume that auth & payments already exist**
>
> ⭐ **Any suggested feature should come in the form of a complete sentence (from the user's
> perspective).**

> 💡 **Why the "complete sentence from the user's perspective" rule is good:** it forces you to state
> a *capability* rather than a *component*. "We need a cache" is not a requirement; "the user sees
> suggestions within 10 ms of typing" is.

---

## 🔍 Hidden Features

> **How to find hidden features?** ⭐ **For every feature that you discuss, think of the following:**

### 1. API (internal / user-facing)
```
typeahead(partial_query) => suggestions_list      ⭐ user-facing
log_search(search_query) => void                  ⭐ internal
```
```
GET /typeahead?partialQuery={}
```
Questions worth raising:
- ⭐ **why REST, why not SOAP / RPC / …**
- ⭐ **why GET, why not POST**
- ⭐ **naming convention**

> **API vs Protocol:**
> - ⭐ **API: input & output (the interface)**
> - ⭐ **Protocol: how the communication happens (REST / …)**

### 2. Data Source & Flow
> ⭐ **Where does the list of suggestions come from?**

```
   Users are constantly searching on Google.

   Every time a user makes a search (search_query):
     1. this search_query goes to the /search microservice
     2. search microservice returns the relevant web-results
     3. ⭐ (ASYNC) the search microservice informs the /typeahead microservice
        that this search has been made (passing the search_query)
     4. the /typeahead service stores this search_query to populate its suggestions list
```

```
                     ┌──────────────────┐
   User ───search───▶│ /search service  │───▶ web results ───▶ User
                     └────────┬─────────┘
                              │ ⭐ ASYNC: log_search(search_query)
                              ▼
                     ┌──────────────────┐
                     │/typeahead service│
                     └──────────────────┘
```

> ⭐ **The `async` matters enormously:** the search response must never wait for typeahead
> bookkeeping. This is fire-and-forget, which is *also* what makes the data loss in the NFRs
> acceptable.

---

## 3️⃣ Non-Functional Requirements (NFR)

> *(design goals)* — driven by **PACELC**.

### Consistency vs Availability
> ⭐⭐ **Do NOT jump to an answer.** Work through these four questions:

#### Q: What is the data?
> **Past search queries and their corresponding counts.**

| Search Query | Count |
|---|---|
| why is the sky blue? | 49,999 |
| why is water wet? | 50,000 |
| what is the color of the ocean | 5,000 |

#### Q: What does eventual consistency mean in this context?
> **When is the data changing?**
> - ⭐ **Every time someone makes a search, the count of some entry changes.**
> - ⭐ **Every time someone makes a search, the top-5 relevant results for some typeahead
>   `partial_query` changes.**
>
> **It is possible for the search-count to reflect in a delayed manner in the top-5 results.**
> **For some time, it is possible that the true count of Query1 > Query2, but we still show Query2
> before Query1 in the typeahead suggestions.**

#### Q: Can we afford stale reads in this situation?
> ⭐ **Yes, that's okay:**
> - **because the user doesn't really know (or care about) the true search counts**
> - **we don't necessarily need to maintain a strict order in the typeahead suggestions**
> - ⭐ **it is okay for a few good suggestions to not be shown, as long as the ones shown are also
>   good enough**

#### Q: What does data loss mean in this context?
> **Data loss would happen if someone has searched for a query, but for whatever reason, we were not
> able to increment the count for that query (the query didn't get logged). The counts will be off by
> a small amount.**

| Search Query | **True** Count | **DB** Count |
|---|---|---|
| why is suryakumar dropped? | 49,999 | 49,999 |
| why is water wet? | 50,000 | **49,998** ⭐ *(no issues)* |
| what is the color of the ocean | 5,000 | 5,000 |

#### Q: Can we afford data loss in this situation?
> ⭐ **Yes, that's okay.** *(same reasons as above)*

> ⭐⭐ **This is a rare and important conclusion: the system can tolerate not just eventual
> consistency but actual DATA LOSS.** Almost nothing else in this course can. That single fact
> unlocks **sampling** in Session 13 — a 1000× reduction in writes.

### Consistency vs Latency
> **What are our latency requirements?**
> - ⭐⭐ **Ultra-low latency — literally competing with the user's typing speed!**
> - ⭐ **each typeahead query to take < 10 ms**
> - *(this doesn't include the round trip — that depends on the user's distance from the servers.
>   We don't have much control over that; the only solution is to have **geolocated servers**)*

### Others
| NFR | Note |
|---|---|
| **Security** | ⭐ **Do NOT do this unless you're a security expert.** *99% of all security issues happen because non-security-expert devs try to do security* |
| **Observability** | |
| **Rate Limits** | |
| **Idempotency** | |
| **Delivery Guarantees** | |

---

## 4️⃣ Scale Estimation

> ⭐ **The scale will dictate our design choices.**

### Goals
| Goal | Question |
|---|---|
| **Amount of Data** | ⭐ **Is sharding needed?** |
| **Amount of Load** | **Requests per second (for each API)**; **Peak Load (vs avg load)** |
| **Read-heavy / Write-heavy** | |

> ⭐ **All these things will help guide our choice of database, cache, & sharding.**

### Does accuracy matter?
> ⭐ **No. Back-of-the-envelope estimates. Being off by a factor of 2 or 3 is okay.**
> ```
> Actual value: 100
> You suggest: 50    ✅ okay
> You suggest: 200   ✅ okay
> You suggest: 10    ❌ not okay (off by a factor of 10)
> ```
> ⭐⭐ **However, any estimates that you make should be JUSTIFIED. Don't pull numbers out of thin air.
> You will have to make some assumptions — each assumption should be clearly stated as such.**

### How to start
> ⭐ **Start by estimating the number of daily active users.**

**Population numbers to memorise:**
| Population | Value |
|---|---|
| **World Population** | **~8 billion** |
| **Number of Internet Users** | **~5 billion** |
| **India's Population** | **~1.4 billion** |
| **USA's Population** | **~350 million** |

### Pareto Principle (the 80/20 rule) ⭐
> **Only 20% of your users will be active.**
>
> **Can be extended to the 80-20-1 principle for social media:**
> - ⭐ **80% are just passively browsing**
> - ⭐ **20% are interacting** (comments, likes, shares)
> - ⭐ **1% are content creators** (posts)

### The estimates
```
assumption: Google has 5 billion users.

Daily Active Users (DAU) = 20% of 5 billion  =  1 billion users

assumption: Number of searches per active-user per day = 20

Total number of searches / day
= (20 searches / user / day) × (1 billion users)
= ⭐ 20 billion searches / day

Avg. searches / second
= 20 × 10^9 searches / (10^5 seconds)      (1 day = 86,400 s ≈ 10^5 s)
= ⭐ 200,000 searches / second
```
> ⭐ **Note: searches are going to the `search` API, not the `typeahead` API.**

### Typeahead requests — the multiplier ⭐
```
assumption: Number of typeahead queries per search query = 10
   • avg size of a search query is 10 letters
   • we start showing suggestions after the first 3 letters
   • number of typeaheads per search = (10 - 3) = 7 ≈ 10
```
Every keystroke is an API call:
```
search_query: "why is the sky blue"
   typeahead("why")
   typeahead("why i")
   typeahead("why is")
   typeahead("why is t")
   typeahead("why is th")
   typeahead("why is the")
   typeahead("why is the s")
   ...
   typeahead("why is the sky blue")
```
```
typeahead(...) API: requests/second
= (200,000 searches / second) × (10 typeaheads / search)
= ⭐⭐ 2 million typeaheads / second

log_search(...) API: requests/second
= ⭐ 200,000 requests / second

Peak Load = 5× the average load
= 5 × 2 million
= ⭐⭐ 10 million typeaheads / second
```

> 🧠 **The 10× amplification is the crux of the whole problem.** Typeahead is **10× more
> request-heavy than Google Search itself** — and each of those requests must return in **under
> 10 ms**.

### Amount of Data
> **What's the data? Past search queries & their counts.**

```
Avg. size of search query: 10 letters   (assumed earlier)
```

**How many entries in this table?** ⭐ **Should we say that for each search that happens, we will
have an entry in this table?**
> ⭐ **No.** Because:
> - **for NEW searches, we're adding entries**
> - **for queries that have already been searched earlier, we're just UPDATING the counts**
>
> ⭐ **The number of entries in the table will depend on the number of "UNIQUE" (never seen before in
> the history of Google) search queries that happen.**

```
assumption: % of search queries that are new (never seen before) = 10%

number of new entries / day
= 10% of (20 billion searches / day)
= ⭐ 2 billion entries per day

amount of data / day
= (10 bytes / entry) × (2 billion entries / day)
= ⭐ 20 GB / day

total amount of data (over 20 years)
= (20 GB / day) × (20 × 400 days)         (365 ≈ 400)
= 16 × 10^4 GB
= ⭐⭐ 160 TB
```

### The two conclusions ⭐
> **Can this amount of data fit on a single server?**
> ⭐ **Probably yes, with modern storage.**
>
> **But, will a single server be able to handle 10 million requests / second?**
> ⭐⭐ **Absolutely no! We need sharding!**

> 💡 **Note *why* we shard here.** It is **not** a capacity problem (160 TB fits) — it is a
> **throughput** problem. Recall Session 3/5's mental model: *"why do we have more than 1 server?"*
> Here the answer is **requests**, not **data**.

---

## ⚖️ Read Heavy / Write Heavy?

```
typeahead   => READ  query  =>  ⭐ 2 million requests / second
log_search  => WRITE query  =>  ⭐ 200,000 requests / second

⭐ reads are 10× more than writes
```
> ⭐ **We will call this READ HEAVY** — because even though the system has to handle lots of writes
> too, **it is dominated by reads.**

### The strategy this implies ⭐⭐
> **Whenever you've read-heavy systems & the writes are ALSO significant:**
> - ⭐ **you can absorb your reads in a CACHE**
> - ⭐ **optimize your DB for WRITES**
>
> ⭐⭐ **No database system is optimized for both reads & writes (that's impossible).**

```
   ┌───────────────────────────────────────────────────────────────┐
   │  reads   →  absorb in the CACHE                               │
   │  writes  →  let them hit a WRITE-OPTIMISED DB (⭐ LSM tree!)   │
   └───────────────────────────────────────────────────────────────┘
```

> 🧠 **Sessions 10–11 just became relevant:** a **write-optimised database** *is* an LSM-tree store —
> sequential appends, high write throughput. And the cache absorbing 2M reads/sec is the Session 3–5
> material. **This case study is where the whole course converges.**

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Typeahead** | ⭐ Suggestions = **globally most popular past search queries** matching a prefix; always tied to **search** |
| **Autocomplete** | ⭐ **Local** to your machine, **personal**, standalone |
| **Reason by analogy** | Find comparable existing products to map out the possible scope |
| **The 5-step approach** | Problem → FR → NFR → Scale → API → System Design (**~half the time on the first four**) |
| **MVP buckets** | ⭐ **v0 (MVP)** · **v1+ (future scope)** · **v-never (rejection)** |
| **v-never features** | ⭐ Frontend/cosmetic features, and dependencies like auth & payments |
| **Feature statement rule** | ⭐ A complete sentence **from the user's perspective** |
| **API vs Protocol** | ⭐ **API = interface (in/out)**; **Protocol = how it travels (REST/RPC)** |
| **Async logging** | ⭐ `/search` informs `/typeahead` **asynchronously** — never blocks the search response |
| **Pareto (80/20)** | ⭐ **20% of users are active**; social media: **80% browse / 20% interact / 1% create** |
| **1 day ≈ 10⁵ seconds** | The single most useful estimation shortcut |
| **Estimation tolerance** | ⭐ Off by 2–3× is fine; off by 10× is not. **Every assumption must be stated** |
| **Scale (typeahead)** | ⭐ **2M reads/sec avg, 10M at peak**; **200K writes/sec**; **160 TB over 20 years** |
| **Why shard here** | ⭐ **Throughput**, not capacity — 160 TB fits, 10M req/s does not |
| **Read heavy** | ⭐ Reads dominate ⇒ **absorb reads in cache, optimise the DB for writes** |
| **The impossibility** | ⭐⭐ **No DB is optimised for both reads and writes** |

---

## 🎯 Session Takeaways

1. **Design interviews are deliberately vague** — your first job is to discover *what the interviewer
   wants*, not to start drawing boxes.
2. ⭐ **Spend ~half the interview on Problem → FR → NFR → Scale.** Design comes after.
3. ⭐ **Reason by analogy** to map the scope, then explicitly say **what you are not building**.
4. ⭐⭐ **Typeahead ≠ autocomplete.** Typeahead = **globally popular past queries** by prefix. That
   definition dictates the entire data model.
5. ⭐ **Sort features into v0 / v1+ / v-never.** Frontend polish and dependencies (auth, payments) are
   **v-never** — proposing them can get you rejected.
6. ⭐ **Find hidden requirements by asking, for every feature: what's the API? where does the data
   come from?** That's how `log_search` was discovered.
7. ⭐ **Work the consistency question in four steps:** what is the data → what does eventual mean here
   → can we tolerate stale reads → **can we tolerate data loss?**
8. ⭐⭐ **Typeahead tolerates both stale reads AND data loss** — nobody knows the true counts. This is
   the licence for sampling later.
9. ⭐ **Latency budget: < 10 ms**, competing with human typing speed. Distance is unfixable except by
   **geolocated servers**.
10. ⭐ **Estimation discipline:** start from DAU, apply **Pareto (20%)**, use **1 day ≈ 10⁵ s**, and
    **justify every assumption**. Being 2–3× off is fine.
11. ⭐⭐ **The 10× keystroke amplification** makes typeahead a bigger system than search: **2M req/s
    average, 10M at peak.**
12. ⭐⭐ **We shard for throughput, not storage** — and because it's read-heavy with heavy writes,
    the answer is **cache the reads, write-optimise the DB.**

---

## ➡️ Next
**[Session 13 — Case Study: Search Typeahead (Part 2)](./13_Case_Study_Search_Typeahead_2.md)** —
Tries vs Hashmaps, sharding, batching, sampling, and the recency/personalisation extensions.
