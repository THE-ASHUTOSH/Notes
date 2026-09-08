# Session 6 — Facebook Newsfeed, APIs & Microservices 📰

> **Topics (from the syllabus):** Building a simple Chat Application · Overview of HTTP APIs, API
> Design Practices · Building Microservices using Python (Message Service, Analytics Service) ·
> Communication between Microservices via HTTP and RPC · Allowing image uploads in Messages
>
> ⚠️ **No class doc is linked for this session** in the course sheet (the Notes cell is empty and the
> Topics cell duplicates the title text). These notes are therefore assembled from **the syllabus
> topics** plus **material the other class docs establish** — Session 5 lists *"Social Media
> Newsfeed"* as a case study, Session 12 defines API-vs-protocol and the async `/search → /typeahead`
> flow, and Session 14 covers the messaging APIs in depth. **Anything specific to your instructor's
> framing of the newsfeed will be missing** — send the doc if it surfaces and I'll fold it in.

---

## 📑 Table of Contents
1. [HTTP APIs — the Basics](#-http-apis--the-basics)
2. [API Design Practices](#-api-design-practices)
3. [Pagination](#-pagination)
4. [Microservices](#-microservices)
5. [HTTP vs RPC](#-communication-between-microservices--http-vs-rpc)
6. [Image Upload in Messages](#-image-upload-in-messages)
7. [The Newsfeed Problem](#-the-newsfeed-problem)
8. [Fan-out on Write vs Fan-out on Read](#-fan-out-on-write-vs-fan-out-on-read)
9. [The Celebrity Problem & Hybrid Fan-out](#-the-celebrity-problem--hybrid-fan-out)
10. [Newsfeed Architecture](#-newsfeed-architecture)
11. [Key Terms Recap](#-key-terms-recap)

---

## 🌐 HTTP APIs — the Basics

### API vs Protocol ⭐
*(the distinction the class doc for Session 12 makes explicitly)*
> - ⭐ **API: input & output (the interface)**
> - ⭐ **Protocol: how the communication happens (REST / RPC / …)**

So `typeahead(partial_query) => suggestions_list` is the **API**; `GET /typeahead?partialQuery={}`
over HTTP is one **protocol** choice for exposing it.

### HTTP verbs
| Verb | Purpose | Idempotent? | Safe? |
|---|---|---|---|
| **GET** | Retrieve a resource | ✅ | ✅ (no side effects) |
| **POST** | Create / submit | ❌ | ❌ |
| **PUT** | Replace a resource entirely | ✅ | ❌ |
| **PATCH** | Partially update | ❌ | ❌ |
| **DELETE** | Remove | ✅ | ❌ |

> ⭐ **Recall Session 14's rule:** *"Any WRITE (post/update/delete) API endpoint should be idempotent
> if your frontend can retry"* — and the frontend **will** retry, whether or not it does today.

### Status codes worth knowing
| Class | Meaning | Key codes |
|---|---|---|
| **2xx** | Success | **200** OK · **201** Created · **204** No Content |
| **3xx** | Redirect | 301 Moved Permanently · 304 Not Modified |
| **4xx** | ⭐ **Client** error | **400** Bad Request · **401** Unauthorized · **403** Forbidden · **404** Not Found · **409** Conflict · **429** Too Many Requests |
| **5xx** | ⭐ **Server** error | **500** Internal Server Error · **502** Bad Gateway · **503** Service Unavailable · **504** Gateway Timeout |

> ⭐ **Session 7's availability definition depends on this distinction:** *"In cases when the user is
> at fault, the server is allowed to deny the request… No, this is NOT low availability."* **4xx is
> not an availability problem; 5xx is.**

---

## ✅ API Design Practices

| Practice | Detail |
|---|---|
| ⭐ **Nouns for resources, verbs via HTTP methods** | `GET /messages` not `GET /getMessages`; `POST /messages` not `POST /createMessage` |
| **Plural, hierarchical paths** | `/conversations/{id}/messages` |
| ⭐ **Versioning** | `/v1/messages` or an `Accept` header — you can never break existing clients |
| ⭐ **Idempotency for writes** | Accept a **client-generated id** (Session 14: **UUID v7**) and return **success** on a duplicate so retries stop |
| ⭐ **Pagination on every list endpoint** | Never return an unbounded collection |
| **Consistent error shape** | `{error: {code, message, details}}` — same everywhere |
| **Rate limiting** | Return **429** with `Retry-After` |
| **Filtering / sorting via query params** | `?status=unread&sort=-created_at` |
| ⭐ **Return only what's needed** | Payload size is latency (Session 5: 1 KB per leaderboard page) |
| **Auth via headers, never URLs** | Bearer tokens; URLs land in logs |
| ⭐ **Document the contract** | OpenAPI/Swagger — the contract *is* the coupling point between services |

### Internal vs user-facing APIs ⭐
Session 12 marks each API as one or the other, and it matters:
```
typeahead(partial_query) => suggestions_list     ⭐ user-facing
log_search(search_query) => void                  ⭐ internal
```
> **User-facing** APIs need auth, rate limiting, versioning and backward compatibility.
> **Internal** APIs can be leaner, but need clear ownership and can use a faster protocol (RPC).

---

## 📄 Pagination

Session 14 makes pagination the **deciding factor** in choosing a database, so it's worth being
precise about the two styles:

| | **Offset pagination** | ⭐ **Cursor / keyset pagination** |
|---|---|---|
| Request | `?offset=200&limit=20` | `?after=<cursor>&limit=20` |
| How it works | Skip N rows | *"give me rows after this key"* |
| Cost | ⭐ **O(offset)** — page 10,000 is slow | ⭐ **O(1)** — index seek |
| Correctness under writes | ⭐ **Broken** — new rows shift everything, so you see duplicates or miss items | ⭐ **Stable** |
| Random page access | ✅ *"jump to page 23"* | ❌ only next/prev |
| Used by | Leaderboards (Session 5 uses `contest:3:page:23`) | ⭐ Feeds, message history |

> ⭐ **For a newsfeed or message history, always use cursor pagination** — the data is being appended
> to constantly, which is exactly when offset pagination misbehaves. Session 14's requirement was
> specifically **"paginated reads (by timestamp)"**, i.e. a keyset cursor.

---

## 🧩 Microservices

The syllabus names two concrete services — a **Message Service** and an **Analytics Service** — which
is a good minimal example of the split.

```
                        ┌──────────────────┐
   Client ──────────────▶│  API Gateway     │  auth, rate limit, routing, TLS
                        └────┬────────┬─────┘
                             ▼        ▼
              ┌──────────────────┐  ┌──────────────────┐
              │ MESSAGE SERVICE  │  │ ANALYTICS SERVICE│
              │ send/get messages│  │ counts, trends,  │
              │ own DB           │  │ dashboards       │
              └────────┬─────────┘  └────────▲─────────┘
                       │  ⭐ async event       │
                       └──▶ [Message Queue] ──┘
```

### Why split them ⭐
| Reason | Detail |
|---|---|
| ⭐ **Different scaling profiles** | Messages need **low latency, immediate consistency**; analytics needs **high write throughput** and tolerates **data loss** |
| ⭐ **Different databases** | Messages → **wide-column** (Session 14); analytics → aggregates, or a **write-back cache** (Session 4) |
| ⭐ **Different consistency requirements** | *"Communication needs strong consistency"* — a view count does not |
| **Independent deployment** | Ship analytics changes without touching the messaging path |
| **Fault isolation** | Analytics being down must never stop messages sending |

> ⭐⭐ **The rule this illustrates: split services along CONSISTENCY and SCALING boundaries, not along
> "things that sound different".** The Message and Analytics services are separated precisely because
> one cannot lose data and the other doesn't care.

### The cost — from Session 1
> *More operational complexity · distributed transactions · no cross-service joins · distributed
> tracing needed.* And Session 9: **ACID across services is effectively gone** — hence **Soft State**
> and the **Saga Pattern** (BASE, Session 9).

---

## 🔌 Communication between Microservices — HTTP vs RPC

### HTTP / REST
```python
# Message service calling the analytics service
requests.post("http://analytics-service/events",
              json={"type": "message_sent", "user_id": uid})
```

### RPC (Remote Procedure Call)
```python
# looks like a local function call
analytics_stub.LogEvent(EventRequest(type="message_sent", user_id=uid))
```

### Comparison ⭐
| | **HTTP / REST** | **RPC (e.g. gRPC)** |
|---|---|---|
| **Mental model** | Resources + verbs | ⭐ **Calling a function on another machine** |
| **Payload** | Usually **JSON** (text) | ⭐ **Binary** (Protocol Buffers) |
| **Contract** | OpenAPI (optional, often drifts) | ⭐ **`.proto` file — enforced, code-generated** |
| **Performance** | Slower — text parsing, verbose | ⭐ **Faster, smaller payloads** |
| **Transport** | HTTP/1.1 or 2 | ⭐ **HTTP/2 — multiplexing, streaming** |
| **Streaming** | Limited | ⭐ **Bidirectional streaming built in** |
| **Browser support** | ⭐ **Native** | Needs a proxy (grpc-web) |
| **Debuggability** | ⭐ **`curl` it, read it** | Needs tooling |
| **Coupling** | Looser | Tighter (shared schema) |
| **Best for** | ⭐ **Public / user-facing APIs** | ⭐ **Internal service-to-service, high volume** |

> ⭐ **The practical rule:** **REST at the edge, RPC inside.** User-facing APIs are REST/HTTP because
> browsers speak it and humans debug it; internal high-volume paths use RPC because the payload and
> parsing savings matter when one request fans out to a dozen services.

### The third option — asynchronous messaging ⭐⭐
Neither HTTP nor RPC, and often the right answer:
```
Message Service ──▶ [Queue / Event Bus] ──▶ Analytics Service
```
| Property | Sync (HTTP/RPC) | ⭐ Async (queue) |
|---|---|---|
| Caller waits | ✅ | ❌ ⭐ **fire and forget** |
| Callee down ⇒ caller fails | ✅ | ❌ ⭐ **queue buffers it** |
| Latency added to the request | ✅ | ⭐ **none** |
| Ordering / delivery guarantees | Immediate | At-least-once, per-partition order |

> ⭐⭐ **This is exactly what Session 12 specifies:** *"(async) the search microservice will inform the
> /typeahead microservice that this search has been made."* **Analytics must never be on the critical
> path** — if logging an event can fail the user's action, you've coupled a
> don't-care system to a must-work one.

**Decision guide:**
```
Do I need the answer to respond to the user?
├── YES → synchronous
│          ├── user-facing / cross-org → ⭐ HTTP/REST
│          └── internal, high volume   → ⭐ RPC (gRPC)
└── NO  → ⭐ ASYNC via a queue   (analytics, notifications, thumbnails, indexing)
```

---

## 🖼️ Image Upload in Messages

The naive approach and why it fails:

### ❌ Naive — POST the image through your app server
```
Client ──[5 MB image]──▶ App Server ──▶ S3
```
| Problem |
|---|
| ⭐ The app server's bandwidth and memory become the bottleneck |
| ⭐ A slow mobile upload **holds an app-server thread/connection open for minutes** |
| Request size limits, timeouts |
| You pay to move the same bytes twice |

### ✅ Pre-signed URLs ⭐⭐
```
1. Client ──▶ App Server:  "I want to upload image.jpg (5 MB, image/jpeg)"
2. App Server validates (auth, size, mime type, quota)
3. App Server ──▶ Client:  a ⭐ PRE-SIGNED S3 URL (time-limited, write-only, one object)
4. Client ──[5 MB]──▶ ⭐ S3 DIRECTLY   (never touches your servers)
5. Client ──▶ App Server:  "done — here's the object key"
6. App Server stores the ⭐ ATTACHMENT_URL in the message row
7. (async) queue a task: virus scan · generate thumbnails · register with the CDN
8. Readers get the ⭐ CDN URL, never the S3 URL
```

> ⭐ **Session 14's message schema already anticipates this:** `attachment_url: string (200b avg)` —
> the message row stores a **URL**, never the bytes.
>
> ⭐ **Session 3 supplies the last two steps verbatim:** *"Facebook will store this video in a file
> storage (like S3)… Facebook will hit the CDN servers and configure a URL… the backend server must
> embed the CDN url instead of the database URL."*

### Why thumbnails go through a queue
> Generating thumbnails is **CPU-bound** (Session 5: *"never multi-thread CPU-bound processes"*) and
> takes seconds. It belongs on a **worker pool behind a queue**, exactly like the Netflix
> downsampling service (Session 17).

### The full storage split ⭐
| What | Where | Why |
|---|---|---|
| **Image/video bytes** | ⭐ **Object store (S3)** | Session 15: large files, >10 KB, mostly static |
| **Message row + `attachment_url`** | ⭐ **Wide-column DB** | Session 14: fast writes + time pagination |
| **Delivery to readers** | ⭐ **CDN** | Session 3: *"CDNs handle almost 70% of all internet traffic"* |
| **Thumbnails** | Generated **async**, stored in S3, served via CDN | CPU-bound work off the request path |

---

## 📰 The Newsfeed Problem

> **Design the Facebook newsfeed:** when a user opens the app, show a list of recent posts from the
> people they follow, most relevant/recent first.

### Why it's hard
| Property | Consequence |
|---|---|
| ⭐ **Extremely read-heavy** | Session 1's estimate: a Twitter-like feed is **~50:1 reads to writes** — 200,000 reads/sec vs 4,000 writes/sec |
| ⭐ **The feed is a JOIN across users** | *"give me posts from the 500 people I follow"* — and Session 9 says **cross-shard joins are impossibly slow** |
| ⭐ **Fan-out is unbounded** | One post by a celebrity must reach **100 million** followers |
| ⭐ **Eventual consistency is fine** | Session 7 states it explicitly: *"if a new post doesn't appear in your friend's newsfeed immediately, it's not the end of the world"* — this is a textbook **A+P** system |

> ⭐ **That last row is the licence for everything below.** Because staleness is acceptable, we are
> free to **precompute** — which is the only way to make the reads cheap.

---

## ⚖️ Fan-out on Write vs Fan-out on Read

This is the central trade-off, and it is **the same read-fanout-vs-write-fanout dilemma** the class
doc analyses for Slack in Session 9 and for groups in Session 14.

### Fan-out on **Read** (pull)
> Store each post once. **When a user opens their feed, query every person they follow and merge.**

```
   WRITE: post → ⭐ 1 write (author's own timeline)
   READ : feed → ⭐ query 500 followees, merge, sort, paginate
```
| ✅ | ❌ |
|---|---|
| **Cheap, constant-time writes** | ⭐ **Very expensive reads** — a fan-out/scatter-gather across many shards |
| **No storage duplication** | ⭐ **Read latency grows with how many people you follow** |
| **Always fresh** | Bad for a **read-heavy** system — you've optimised the rare operation |

### Fan-out on **Write** (push) ⭐
> **When a user posts, immediately write that post into the precomputed feed of every follower.**

```
   WRITE: post → ⭐ N writes (one per follower)
   READ : feed → ⭐ ONE read of a precomputed list
```
| ✅ | ❌ |
|---|---|
| ⭐ **Extremely cheap reads** — one key lookup, already sorted | ⭐ **Writes cost O(followers)** |
| ⭐ **Perfect for read-heavy systems** | **Storage duplication** (the post sits in N feeds) |
| Feed can be served straight from a cache | ⭐ **Catastrophic for celebrities** (100M writes for one post) |

> ⭐⭐ **This is *exactly* the Session-13 typeahead pattern:** precompute the answer for every possible
> query key (there: `prefix → top-5`; here: `user → feed`) so the read is a single O(1) lookup, and
> pay for it on the write path. **Same idea, different domain.**

### The comparison
| | Fan-out on **Read** | ⭐ Fan-out on **Write** |
|---|---|---|
| Post cost | O(1) | ⭐ **O(followers)** |
| Feed read cost | ⭐ **O(followees)** — multi-shard | **O(1)** — one lookup |
| Freshness | Immediate | Eventual |
| Storage | Minimal | Duplicated |
| Suits | Write-heavy | ⭐ **Read-heavy (i.e. reality)** |
| Breaks on | Users following thousands | ⭐ **Celebrities** |

---

## 🌟 The Celebrity Problem & Hybrid Fan-out

> ⭐ Session 1 names this directly: *"One celebrity with 100M followers breaks fan-out-on-write"*, and
> Session 9 warns that even `user_id` sharding isn't immune — *"this is not always true: eg, the
> **celebrity problem**, especially for notification systems."*

**The numbers:** a celebrity with 100M followers posting once ⇒ **100 million writes**. At even a
handful of celebrity posts per second, the write path collapses.

### ⭐⭐ The solution — Hybrid fan-out
> **Fan-out on write for normal users; fan-out on read for celebrities.**

```
   Normal user posts (99.9% of users, < ~10k followers)
        └──▶ ⭐ PUSH into each follower's precomputed feed

   Celebrity posts (few thousand accounts, > ~10k followers)
        └──▶ ⭐ store ONCE; do NOT fan out

   Reading a feed:
        1. read my precomputed feed          (one lookup — has all normal posts)
        2. ⭐ pull the recent posts of the few celebrities I follow
        3. ⭐ MERGE the two lists and return
```

**Why it works:**
| Fact | Consequence |
|---|---|
| ⭐ **Celebrities are few** | Step 2 pulls from a handful of accounts, not 500 — so the read stays cheap |
| ⭐ **Celebrity posts are hot** | Their timeline is in cache anyway (Session 1: replicate hot keys) |
| ⭐ **Normal users are many but small** | Fan-out-on-write cost stays bounded |

> 🧠 **The general lesson — and it recurs all over this course:** when a **power-law distribution**
> breaks your uniform algorithm, **special-case the head and keep the algorithm for the tail.**
> Session 13 did the same thing when it grouped rare 3-letter prefixes into one shard while giving
> `why` a dedicated shard.

### Other optimisations
| Optimisation | Detail |
|---|---|
| ⭐ **Don't fan out to inactive users** | Why precompute a feed for someone who hasn't opened the app in 6 months? Compute theirs **on read** |
| ⭐ **Cap the feed length** | Store only the most recent ~800 entries per user; older pages fall back to a pull |
| ⭐ **Async fan-out via a queue** | The post returns as soon as it's durably stored; the fan-out happens in workers |
| **Feed in a cache, not a DB** | The precomputed feed is derived data — Session 5's *"cache doesn't store any 'real' data"* |
| **Store post IDs, not posts** | The feed is a list of ids; hydrate post bodies from a cache in one batch |

---

## 🏗️ Newsfeed Architecture

```
   ┌──────────┐   POST /posts
   │  Client  │────────────────▶ ┌──────────────────┐
   └──────────┘                  │   Post Service   │
        ▲                        └────────┬─────────┘
        │                                 │ 1. store post (durable)  ⭐ return 201 now
        │                                 ▼
        │                        ┌──────────────────┐
        │                        │   Posts DB       │  wide-column, shard: user_id
        │                        └──────────────────┘
        │                                 │ 2. ⭐ ASYNC
        │                                 ▼
        │                        ┌──────────────────┐
        │                        │  Message Queue   │
        │                        └────────┬─────────┘
        │                                 ▼
        │                        ┌──────────────────┐   is the author a celebrity?
        │                        │  Fan-out Workers │   ├─ no  → ⭐ push to followers' feeds
        │                        └────────┬─────────┘   └─ yes → ⭐ skip (pull at read time)
        │                                 ▼
        │                        ┌──────────────────┐
        │  GET /feed             │  Feed Cache      │  user_id → [post_id, …] (capped)
        └───────────────────────▶│  (Redis)         │
                                 └────────┬─────────┘
                                          │ ⭐ merge with celebrity pull
                                          ▼
                                 ┌──────────────────┐
                                 │ Post hydration   │  batch fetch post bodies
                                 └────────┬─────────┘
                                          ▼
                                 media URLs ──▶ ⭐ CDN
```

### The design decisions, and where each came from
| Decision | Justification | Source session |
|---|---|---|
| **Eventual consistency** | *"if a new post doesn't appear immediately, it's not the end of the world"* — **A+P** | ⭐ **7** |
| **Precompute the feed (fan-out on write)** | Read-heavy ⇒ **absorb reads in cache, optimise DB for writes** | ⭐ **12, 13** |
| **Hybrid fan-out for celebrities** | The **hot key / celebrity problem** | ⭐ **1, 9** |
| **Async fan-out via a queue** | Never put O(followers) work on the request path | ⭐ **6, 12** |
| **Feed in a cache, capped** | It's **derived data** — losing it is not data loss | ⭐ **5** |
| **Cursor pagination** | The feed is constantly appended to | ⭐ **14** |
| **Wide-column posts DB** | Fast writes + **time-based pagination** | ⭐ **14, 15** |
| **Media via S3 + CDN, `attachment_url` in the row** | *"CDNs perform the heavy lifting"* | ⭐ **3, 17** |
| **Store post IDs, hydrate separately** | Avoid duplicating post bodies N times | — |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **API vs Protocol** | ⭐ API = the **interface** (in/out); protocol = **how it travels** (REST/RPC) |
| **Idempotent write** | ⭐ Safe to retry — accept a client-generated id, return success on duplicates |
| **4xx vs 5xx** | ⭐ Client's fault (**not** an availability problem) vs server's fault |
| **Offset pagination** | `?offset&limit` — ⭐ O(offset), **breaks when rows are inserted** |
| ⭐ **Cursor/keyset pagination** | `?after=<cursor>` — ⭐ **O(1) and stable**; correct choice for feeds & message history |
| **Microservice split rule** | ⭐⭐ Split along **consistency** and **scaling** boundaries |
| **HTTP/REST** | Text/JSON, browser-native, debuggable — ⭐ **use at the edge** |
| **RPC / gRPC** | ⭐ Binary (protobuf), HTTP/2, enforced `.proto` contract — ⭐ **use internally** |
| ⭐ **Async messaging** | Queue between services — ⭐ **analytics must never be on the critical path** |
| ⭐ **Pre-signed URL** | ⭐⭐ Client uploads **directly to S3**; bytes never touch your app servers |
| **`attachment_url`** | The message row stores a **URL**, never the bytes |
| ⭐ **Fan-out on read (pull)** | Cheap writes, ⭐ **expensive multi-shard reads** |
| ⭐ **Fan-out on write (push)** | ⭐ **O(1) reads from a precomputed feed**, O(followers) writes |
| ⭐ **Celebrity problem** | One 100M-follower post ⇒ 100M writes — breaks fan-out-on-write |
| ⭐⭐ **Hybrid fan-out** | ⭐ **Push for normal users, pull for celebrities, merge at read time** |
| **Feed capping** | Keep only the newest ~800 entries; older pages fall back to a pull |
| **Inactive-user skip** | Don't precompute feeds nobody reads |

---

## 🎯 Session Takeaways

1. ⭐ **API is the interface; protocol is the transport.** Mark every endpoint **internal** or
   **user-facing** — they have different requirements.
2. ⭐ **Make every write endpoint idempotent**, because the frontend will retry eventually whether or
   not it does today (Session 14).
3. ⭐ **4xx is not an availability failure; 5xx is** — the distinction Session 7's CAP definition
   rests on.
4. ⭐⭐ **Use cursor pagination for feeds and message history.** Offset pagination is O(offset) and
   silently duplicates/skips rows when data is being appended.
5. ⭐⭐ **Split microservices along consistency and scaling boundaries** — the Message Service cannot
   lose data, the Analytics Service doesn't care. That difference *is* the boundary.
6. ⭐ **REST at the edge, RPC inside**, and **async queues whenever the caller doesn't need the
   answer**. Analytics belongs on a queue, never on the critical path.
7. ⭐⭐ **Never upload images through your app server.** Issue a **pre-signed URL**, let the client
   write straight to S3, store only the `attachment_url`, and serve reads through the **CDN**.
8. ⭐ **Thumbnail generation is CPU-bound** ⇒ queue + worker pool, exactly like Netflix's downsampling
   service.
9. ⭐⭐ **The newsfeed is read-heavy and tolerates staleness**, which is precisely what makes
   **precomputation** legal — and precomputation is what makes the reads cheap.
10. ⭐⭐ **Fan-out on write gives O(1) reads at O(followers) write cost;** fan-out on read is the
    reverse. Given a 50:1 read:write ratio, **push wins** — the same precompute-per-key trick as the
    typeahead suggestions cache.
11. ⭐⭐ **Celebrities break push**, so go **hybrid**: push for normal users, pull for the handful of
    celebrities, merge at read time. **When a power law breaks your uniform algorithm, special-case
    the head.**
12. ⭐ **Cap feed length, skip inactive users, fan out asynchronously, and store post IDs rather than
    post bodies** — the feed is **derived data** living in a cache, so losing it is not data loss.

---

## ➡️ Next
**[Session 7 — CAP & PACELC, Replication vs Sharding](./07_CAP_PACELC_Replication_vs_Sharding.md)**
