# Session 16 — Case Study: IRCTC 🚆

> **Topics (from the syllabus):** Design IRCTC · **ACID properties to avoid double booking** ·
> Multi-service
>
> ⚠️ **No class doc is linked for this session** in the course sheet (both the Topics and Notes cells
> are empty for row 16). However, **IRCTC is worked through in real depth inside two other class
> docs**, and those passages are quoted verbatim throughout below:
> - **Session 9** (*SQL vs NoSQL + Sharding Key*) — the **full sharding-key analysis** for IRCTC
> - **Session 7** (*CAP-PACELC*) — IRCTC as a **C+P vs A+P** example, and the **RAC** mechanism
>
> Everything not quoted from those docs is standard material, marked where it extends beyond them.

---

## 📑 Table of Contents
1. [The Requirements](#-the-requirements)
2. [The Core Problem — Double Booking](#-the-core-problem--double-booking)
3. [ACID and Isolation](#-acid--why-isolation-is-the-crux)
4. [Preventing Double Booking](#-preventing-double-booking)
5. [The Sharding Key](#-the-sharding-key-the-class-analysis)
6. [Two Databases, Two Keys](#-two-databases-two-sharding-keys)
7. [Where IRCTC Sits on CAP](#-where-irctc-sits-on-cap)
8. [RAC — Eventual Consistency by Design](#-rac--eventual-consistency-by-design)
9. [The Tatkal Problem](#-the-tatkal-problem)
10. [Multi-Service Architecture](#-multi-service-architecture)
11. [Key Terms Recap](#-key-terms-recap)

---

## 📋 The Requirements

Straight from the Session 9 class doc:

> **IRCTC (Railway ticket booking service in India)**
> - ⭐ **Prevent double booking of seats** (at least for confirmed, non-RAC tickets)
> - ⭐ **Handle peak load during the Tatkal window (20× or more than the average load)**
>
> ```
> book_ticket(user_id, train_id, date_of_journey, class, seat_preference, meal_preference, ...)
>     => ticket: {id, details}
> ```

**Scale context:** IRCTC facilitates ⭐ **~13k passenger trains** *(Session 9)*.

### Functional requirements
| Feature | In MVP? |
|---|---|
| **Search trains** (source, destination, date) | ✅ |
| **Check seat availability** | ✅ |
| ⭐ **Book a ticket** (no double booking) | ✅ **the core feature** |
| **Cancel a ticket** | ✅ |
| **View my bookings** | ✅ |
| Payments · Auth · Meal preferences · PNR status | ⭐ *dependencies / v1+ — per Session 12, **not what you were asked to design*** |

---

## 💥 The Core Problem — Double Booking

> ⭐⭐ **Two people must never be allotted the same seat on the same train on the same date.**

This is the **opposite** of almost every other case study in this course:

| System | Consistency need |
|---|---|
| Typeahead (12–13) | ⭐ tolerates **stale reads AND data loss** |
| Newsfeed (6) | tolerates staleness |
| Leaderboard (5) | eventual is fine — *"nobody has complained"* |
| ⭐ **IRCTC** | ⭐⭐ **cannot tolerate a double booking, ever** |

> Session 7 places it explicitly in the **C+P** bucket, alongside:
> > *"Ticket Booking (BookMyShow) / Product Purchase (**ensure that customers are not ordering more
> > than the inventory amount**)"*

---

## 🔐 ACID — Why Isolation Is the Crux

Session 9's **Isolation** example is *literally* the double-booking bug, with bank balances instead
of seats:

```
Transaction 1                          Transaction 2
1. balance = get_balance(K)            1. balance = get_balance(K)
2. assert balance > 1 million          2. assert balance > 1 million
3. new_balance = balance - 1 million   3. new_balance = balance - 1 million
4. set_balance(K, new_balance)         4. set_balance(K, new_balance)
```
> **Khushboo started with 1 million $:**
> ```
> T1: steps 1..3
> T2: steps 1..3            ← ⭐ both read the SAME value
> T1: step 4   → balance = 0
> T2: step 4   → balance = 0
> T1: steps 5..6            ← recipient 1 credited
> T2: steps 5..6            ← ⭐ recipient 2 ALSO credited
> ```
> ⭐⭐ **"This is lack of isolation! This should NOT happen."**

**Translate it to seats:**
```
Ashok's booking                        Sanjana's booking
1. read seats for Rajdhani/15-Feb      1. read seats for Rajdhani/15-Feb
2. seat B2-31 appears FREE             2. seat B2-31 appears FREE   ⭐ same read
3. assign B2-31 to Ashok               3. assign B2-31 to Sanjana
4. commit                              4. commit
                                       💥 ⭐ TWO passengers, ONE seat
```

> ⭐⭐ **Double booking is not a "distributed systems" problem — it is a classic lost-update /
> write-skew problem, and ACID isolation is the tool built to prevent it.** This is precisely why
> IRCTC's booking store is **SQL**, and why Session 9 lists ACID as the reason.

### The four ACID properties, applied
| Property | What it buys IRCTC |
|---|---|
| **Atomicity** | ⭐ A booking is *seat reserved + payment recorded + PNR generated* — **all or nothing**. Never a paid ticket with no seat, nor a seat with no payment |
| **Consistency** *(ACID sense — constraints)* | ⭐ A **unique constraint** on `(train_id, date, seat_no)` makes a double booking **structurally impossible** |
| ⭐ **Isolation** | ⭐⭐ **The property that actually prevents double booking** — concurrent bookings must not see the same seat as free |
| **Durability** | A confirmed ticket survives a crash *(but per Session 7, **only replication survives disk failure**)* |

---

## 🛡️ Preventing Double Booking

*(Extending beyond the class docs — these are the standard mechanisms.)*

### Option 1 — Pessimistic locking (`SELECT … FOR UPDATE`)
```sql
BEGIN;
SELECT seat_no FROM seats
 WHERE train_id = :t AND journey_date = :d AND status = 'FREE'
 LIMIT 1
 FOR UPDATE;                      -- ⭐ locks the row; other txns block here

UPDATE seats SET status = 'BOOKED', ticket_id = :tid
 WHERE train_id = :t AND journey_date = :d AND seat_no = :s;
COMMIT;
```
| ✅ | ❌ |
|---|---|
| Simple, correct | ⭐ **Serialises bookings for the same train** — brutal under Tatkal load |
| No retry logic needed | Lock contention, deadlock risk |

### Option 2 — Optimistic locking / compare-and-swap ⭐
```sql
UPDATE seats
   SET status = 'BOOKED', ticket_id = :tid
 WHERE train_id = :t AND journey_date = :d AND seat_no = :s
   AND status = 'FREE';           -- ⭐ the guard

-- if rows_affected = 0 → someone else won → pick another seat and retry
```
> ⭐ **This is exactly the pattern Session 18 uses for Uber's driver allotment:**
> ```sql
> update bookings set driver_id = 'pragy' where id = :booking_id and driver_id is null
> ```
> ⭐⭐ **The `AND status = 'FREE'` clause makes the database itself the arbiter — exactly one writer
> can win, with no application-level locking at all.**

| ✅ | ❌ |
|---|---|
| ⭐ **No blocking** — high concurrency | Needs retry logic |
| Fails fast and cheaply | Wasted work under very high contention |

### Option 3 — Unique constraint as the backstop ⭐
```sql
ALTER TABLE seat_allocations
  ADD CONSTRAINT uq_seat UNIQUE (train_id, journey_date, seat_no);
```
> ⭐ **Even if the application logic is buggy, the database physically refuses the second insert.**
> This is **ACID "Consistency"** in the Session-9 sense — *constraints are enforced* — and it's the
> safety net you always want under the locking scheme.

### Option 4 — Two-phase booking with a hold ⭐
```
1. RESERVE the seat with a short TTL (e.g. 10 minutes) → status = 'HELD'
2. User completes payment
3. CONFIRM → status = 'BOOKED'
   (or the hold expires and the seat returns to 'FREE')
```
> ⭐ **Why this matters:** payment is a **third-party call taking seconds to minutes**. You cannot
> hold a database lock across it *(Session 4: distributed atomicity across services is 2PC — slow,
> low availability)*. **The hold decouples the seat decision from the payment outcome.**

### Why the sharding key makes this possible ⭐⭐
> All four mechanisms assume the contending rows are **in one database**, so that ACID applies.
> Session 9 is emphatic: *"SQL DBs provide ACID guarantees only within a single server"* and
> **"Sharding nullifies ACID."**
>
> ⭐⭐ **So the entire double-booking defence depends on choosing a sharding key that keeps one train's
> seats on one shard.** That is the next section — and it is why `train_id` is the answer.

---

## 🔑 The Sharding Key (the class analysis)

Quoted from the Session 9 class doc:

| Candidate | Verdict |
|---|---|
| **Ticket ID** | ❌ **"`ticket_id` is not part of the request — it is generated in the response"** *(Session 9's general rule: **any id the system generates in the response cannot be the sharding key**)* |
| **Date of travel** | ❌ ⭐ **"Timestamp — so big no-no."** *Interesting aside from the doc: **"Any data for past dates will now be immutable. You cannot book a ticket for a journey that has already happened in the past. You cannot modify (cancel, add lunch services) the ticket if the journey has already completed."*** |
| **User ID** | ❌ ⭐⭐ **"Users are distributed across the shards."** *"Let's suppose Ashok is trying to book a ticket in Rajdhani… Sanjana has booked a ticket in Rajdhani for 15 Feb, Rohit has also booked… **If we shard by `user_id`, then Sanjana's ticket data is in her shard, Rohit's ticket is in his shard. To ensure Ashok doesn't get a duplicate seat, we've to hit both Sanjana & Rohit's shards. In fact we need to hit ALL the shards. We don't know which users have booked which tickets.** We have to hit all shards to check if a particular seat has been booked or not — **fan out**."* |
| ⭐ **Train ID** | ✅ ⭐⭐ **"If we shard by `train_id`, then tickets of 1 train are stored completely within a single shard."** *"Sanjana & Rohit are travelling in Rajdhani on 15th Feb, so both these tickets will be in the same shard (**note: not the user data, just the ticket data**). Vijay is travelling in Shatabdi on 15th Feb — **can their seats collide? No, the trains are different!** So when checking for duplicates, we only need to check the tickets for this train — **just 1 shard**."* **"IRCTC facilitates ~13k passenger trains ⇒ cardinality is decent."** |

### Checking `train_id` against the five properties (Session 9's checklist)
| Property | `train_id` |
|---|---|
| **1. Even distribution** | ⚠️ **Imperfect** — Rajdhani is far busier than a rural passenger train. A real **hot shard** risk |
| **2. High cardinality** | ✅ ⭐ **~13,000 trains — "cardinality is decent"** |
| **3. Part of every request** | ✅ ⭐ **`book_ticket(user_id, train_id, …)`** — always supplied |
| **4. No fan-out on frequent queries** | ✅ ⭐ **Booking and availability both hit exactly 1 shard** |
| **5. Immutable** | ✅ A ticket's train never changes |

> ⭐ **Note property 1 is the weak one, and it's accepted anyway** — because property 4 (no fan-out on
> the double-booking check) is **worth more** here than perfect load balance. *This is HLD:
> justified trade-offs, not perfect answers.*
>
> 💡 A natural refinement is the **composite key `(train_id, journey_date)`**, which multiplies
> cardinality by the booking window and spreads a popular train's load across dates. Session 9
> confirms composites are allowed: *"Can a sharding key be composite? **Yes. Totally allowed.**"*

---

## 🗄️ Two Databases, Two Sharding Keys

The obvious objection, answered in the class doc:

> **Q: But a single user can also book tickets in multiple trains — how will we store the user data
> then? Will that be split across servers?**
>
> ⭐ **"Note that user data can be sharded by `user_id` (user dashboard service). And for booking
> tickets, the ticket data can be sharded by `train_id` (booking microservice)."**
>
> ⭐⭐ **"Each ticket will be stored in 2 databases — the tickets db (sharded by `train_id`), and the
> user's db (sharded by `user_id`)."**

```
   ┌───────────────────────────────┐      ┌───────────────────────────────┐
   │  BOOKING SERVICE              │      │  USER DASHBOARD SERVICE       │
   │  tickets DB                   │      │  user bookings DB             │
   │  ⭐ shard: train_id            │      │  ⭐ shard: user_id             │
   │  answers: "is seat X free?"   │      │  answers: "my bookings"       │
   │  ⭐ ACID double-booking check   │      │  read-optimised               │
   └───────────────────────────────┘      └───────────────────────────────┘
              │                                          ▲
              └──────── ⭐ each ticket written to BOTH ───┘
```

> ⭐⭐ **This is the resolution of Session 9's rule that a database can have only ONE sharding key:**
> *"If you need different sharding keys, you need different databases."* You don't compromise the
> key — **you duplicate the data into a second store shaped for the second access pattern.**
>
> The same move appears three times in this course: **IRCTC** (train_id + user_id), the
> **leaderboard** (`page:*` + `user:*`, Session 5), and **messaging** (the separate
> `recentConversations` DB, Session 14).

### The fan-out that's allowed ⭐
> **Q: Suppose we wish to find all the journeys happening on a given day?**
>
> - ⭐ **"That will be a fan-out. But note that this is NOT a frequent query!"**
> - ⭐ **"If it were a frequent query, then we would come up with another solution — another solution
>   does NOT mean that we change the sharding key. We can't change it, because `train_id` is the
>   ideal sharding key for preventing double-booking."**
> - ⭐⭐ **"We can have another database that is sharded by date that provides this data to us
>   (IRCTC actually does this!)"**

> 🧠 **Two lessons in one paragraph:** ⭐ **rare queries are allowed to fan out** (Session 9:
> *"you cannot optimize every single query"*), and ⭐ **you never change the sharding key to fix a
> query — you add a store.**

---

## 🎭 Where IRCTC Sits on CAP

Session 7 lists ticket booking under **C+P** — *"When data is critical"* — but then says something
more interesting about IRCTC specifically:

> ⭐⭐ **"IRCTC makes ticket booking eventually consistent (they offer you RAC tickets which are
> resolved later – 'eventually')"**

So the honest positioning is **split by operation**:

| Operation | Consistency | Why |
|---|---|---|
| ⭐ **Confirmed seat allocation** | ⭐⭐ **Immediate (C+P)** | A double booking is unacceptable — *"at least for confirmed, non-RAC tickets"* |
| ⭐ **RAC / waitlist resolution** | ⭐⭐ **Eventual (A+P)** | Resolved later, by design |
| Search / availability display | Eventual | A slightly stale seat count is fine — the booking transaction is the real gate |
| PNR status, notifications | Eventual | |

> ⭐ **This is tunable consistency in the Session-8 sense, applied per operation.** The system isn't
> uniformly CP or AP — **the booking write uses a strict quorum while a search read can be R=1.**
> *Session 8: "we can choose ANY point on the spectrum."*

### And note the availability cost
> Session 7's C+P definition applies directly: **when a partition isolates a train's shard, bookings
> for that train must be REFUSED** — a healthy server denying a healthy request, which is exactly
> Session 7's definition of low availability. **IRCTC accepts that**, because selling the same berth
> twice is worse than an error message.

---

## 🎫 RAC — Eventual Consistency by Design

> ⭐ **RAC (Reservation Against Cancellation)** and the waiting list are not a technical compromise —
> they're a **product feature that converts a hard consistency problem into a soft one.**

```
   Seats: 100 confirmed berths
   ┌──────────────────────────────────────────────────────────────┐
   │ CNF  1…100   ⭐ immediate consistency — never double-booked   │
   │ RAC  101…120 ⭐ eventual — "you'll get a berth if someone      │
   │                cancels"; two passengers share one berth      │
   │ WL   121…    ⭐ eventual — resolved as cancellations arrive    │
   └──────────────────────────────────────────────────────────────┘
```

**Why this is clever engineering, not just business policy:**
| Effect | Detail |
|---|---|
| ⭐ **Caps contention on the strict path** | Only the ~100 confirmed berths need strong isolation. Everything above that is an **append to a queue** |
| ⭐ **Turns a scarce resource into an ordered list** | Issuing RAC/WL #157 needs only an **atomic counter increment**, not a seat-level lock |
| ⭐ **Makes overbooking safe** | Session 7's bank parallel — *"banks have found a way to earn from their own mistakes"*. IRCTC's version: **the inconsistency is disclosed to the user upfront** |
| ⭐ **Resolution is a batch job** | Cancellations trickle in; a background process promotes WL → RAC → CNF. Classic **write-around/cron** shape (Session 4) |

> 🧠 **The general pattern: when strong consistency is expensive, shrink the set of things that need
> it.** IRCTC doesn't make 500 bookings strongly consistent — it makes **100** strongly consistent
> and the rest **eventually** consistent, with the user's informed consent.

---

## 🔥 The Tatkal Problem

> Session 9's second requirement: ⭐ **"Handle peak load during the Tatkal window (20× or more than
> the average load)"**

Tatkal opens at a fixed time (10:00/11:00 AM), so this isn't merely high load — it's a
**thundering herd** *(Session 1)* aimed at **a handful of hot shards** (the popular trains).

### The compounding problems
| Problem | Source |
|---|---|
| ⭐ **20× spike, instantaneously** | Everyone submits at the same second |
| ⭐ **Hot shard** | All the load lands on the few popular `train_id` shards |
| ⭐ **Maximum lock contention** | Thousands of transactions racing for the same rows — precisely when pessimistic locking is worst |
| ⭐ **Payment latency inside the window** | A third-party call of seconds, while seats are held |

### Mitigations
| Technique | Detail |
|---|---|
| ⭐ **Queue the requests** | Admit bookings into a **FIFO queue** per train and process at a sustainable rate. Users get a **position**, not a timeout — the same **async task + poll for status** shape as Uber's booking (Session 18) |
| ⭐ **Optimistic locking, not pessimistic** | Under this contention, blocking locks serialise everything; compare-and-swap fails fast |
| ⭐ **Two-phase hold with a short TTL** | Never hold a lock across the payment call |
| ⭐ **Cache the availability count** | Reads vastly outnumber writes during Tatkal; serve availability from a cache (**eventually consistent**) and let the **booking transaction** be the real gate |
| ⭐ **Rate limiting + bot detection** | Most Tatkal traffic is automated agents |
| ⭐ **Pre-scale** | The spike is **scheduled** — provision capacity in advance rather than reactively autoscaling |
| ⭐ **Composite shard key `(train_id, date)`** | Spreads one popular train's load across journey dates |

> ⭐ **The key realisation:** you cannot make the seat allocation itself concurrent — it's inherently
> serialised on a scarce resource. **So you serialise it deliberately and cheaply (a queue) rather
> than accidentally and expensively (lock contention).**

---

## 🏗️ Multi-Service Architecture

> The syllabus explicitly says **"Multi-service"**.

```
                            ┌──────────────────┐
   Client ──────────────────▶│   API Gateway    │  auth, rate limit ⭐ (Tatkal!)
                            └───┬────┬────┬─────┘
            ┌───────────────────┘    │    └──────────────────┐
            ▼                        ▼                       ▼
  ┌───────────────────┐   ┌────────────────────┐   ┌────────────────────┐
  │  SEARCH SERVICE   │   │  BOOKING SERVICE   │   │ USER DASHBOARD SVC │
  │  trains, routes,  │   │ ⭐ SQL + ACID       │   │  "my bookings"     │
  │  availability     │   │ ⭐ shard: train_id  │   │ ⭐ shard: user_id   │
  │  ⭐ cached (eventual)│   │  the ONLY strict   │   │  read-optimised    │
  └───────────────────┘   │  consistency point │   └────────────────────┘
                          └────────┬───────────┘             ▲
                                   │ ⭐ each ticket ──────────┘
                                   │   written to both
                    ┌──────────────┼──────────────┬────────────────┐
                    ▼              ▼              ▼                ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │  PAYMENT SVC │ │ WL/RAC       │ │ NOTIFICATION │ │ DATE-SHARDED │
          │  (3rd party) │ │ RESOLVER     │ │ SVC (SMS/    │ │ QUERY DB     │
          │  ⭐ outside   │ │ ⭐ cron/batch │ │ email/push)  │ │ ⭐ "journeys  │
          │  the txn     │ │ WL→RAC→CNF   │ │  async       │ │  on date X"  │
          └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                    ▲
          ┌─────────┴──────────┐
          │  ⭐ BOOKING QUEUE   │  admits Tatkal traffic at a sustainable rate
          └────────────────────┘
```

### Service boundaries — and why each one is where it is
| Service | Consistency | Store | Why separate |
|---|---|---|---|
| **Search / availability** | ⭐ Eventual | Cache + read replicas | ⭐ Read-heavy; staleness harmless because booking re-validates |
| ⭐ **Booking** | ⭐⭐ **Immediate** | ⭐ **SQL, sharded by `train_id`** | ⭐ **The single place that needs ACID** — keep the strict-consistency surface as small as possible |
| **User dashboard** | Eventual | Sharded by `user_id` | Different access pattern ⇒ **different sharding key ⇒ different database** |
| **Payments** | External | 3rd party | ⭐ Must sit **outside** the DB transaction (Session 4: cross-service atomicity = 2PC = slow) |
| **WL/RAC resolver** | Eventual, batch | — | ⭐ Cron-driven promotion, like the leaderboard's write-around job |
| **Notifications** | Eventual, async | Queue | ⭐ Never on the critical path (Session 6) |
| **Date-sharded query DB** | Eventual | Sharded by date | ⭐ *"IRCTC actually does this!"* — for the rare fan-out query |

> ⭐⭐ **The architectural principle:** **isolate the strongly-consistent component and let everything
> else be eventual.** Exactly one box in that diagram needs ACID. Session 7's PACELC warning —
> *"immediate consistency comes at a huge cost"* — is why you pay it in one place only.

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| ⭐ **Double booking** | Two passengers allotted the same seat — ⭐ **a lost-update / isolation failure**, not a distributed-systems problem |
| ⭐ **Isolation** | ⭐⭐ The ACID property that actually prevents it |
| **Pessimistic lock** | `SELECT … FOR UPDATE` — correct but **serialises** bookings |
| ⭐ **Optimistic lock / CAS** | `UPDATE … WHERE status = 'FREE'` — ⭐ **the DB picks exactly one winner**, no blocking (same as Uber's driver allotment) |
| ⭐ **Unique constraint** | `UNIQUE(train_id, date, seat_no)` — the structural backstop (ACID "Consistency") |
| ⭐ **Two-phase hold** | `HELD` with a TTL → payment → `BOOKED`; keeps the payment call **outside** the lock |
| ⭐ **`train_id` sharding** | ⭐⭐ Keeps **all of one train's tickets on one shard** ⇒ the double-booking check hits **1 shard**; ~13k trains = decent cardinality |
| **Why not `user_id`** | ⭐ Tickets scatter across shards ⇒ checking for a duplicate seat is a **fan-out** |
| **Why not `ticket_id` / date** | ⭐ Generated in the **response** / it's a **timestamp** |
| ⭐ **Two DBs, two keys** | ⭐⭐ tickets by `train_id` **+** user bookings by `user_id`; **each ticket stored twice** |
| ⭐ **Date-sharded query DB** | For the rare *"journeys on day X"* fan-out — *"IRCTC actually does this"* |
| **C+P for confirmed seats** | Refuse the booking rather than risk a duplicate |
| ⭐ **RAC / waitlist** | ⭐⭐ **Eventual consistency turned into a product feature** — shrinks the strictly-consistent set to the confirmed berths only |
| ⭐ **Tatkal** | ⭐ **20×+ scheduled spike** onto **hot shards** ⇒ queue admissions, optimistic locking, pre-scale, rate-limit bots |
| **Thundering herd** | Simultaneous burst at a fixed time (Session 1) |

---

## 🎯 Session Takeaways

1. ⭐⭐ **Double booking is an isolation failure, not a distributed-systems failure** — it's Session 9's
   lost-update example with seats instead of rupees. **ACID is the tool**, which is why the booking
   store is **SQL**.
2. ⭐ **Layer the defences:** optimistic **compare-and-swap** (`WHERE status = 'FREE'`) for
   concurrency, a **unique constraint** as the structural backstop, and a **two-phase hold** so the
   payment call never sits inside a lock.
3. ⭐⭐ **Everything depends on the sharding key, because "sharding nullifies ACID"** — you can only
   use a transaction if the contending rows live on one shard.
4. ⭐⭐ **Shard by `train_id`:** all of one train's tickets land on one shard, so the duplicate-seat
   check hits **exactly one shard**. `user_id` would force a **fan-out across every shard**;
   `ticket_id` is generated in the response; date is a **timestamp**.
5. ⭐ **`train_id` fails the even-distribution property and is chosen anyway** — avoiding the fan-out
   matters more than perfect balance. A composite `(train_id, journey_date)` softens the hot shard.
6. ⭐⭐ **When two access patterns need different keys, use two databases** — tickets by `train_id`,
   user bookings by `user_id`, **each ticket written to both**.
7. ⭐ **Rare queries may fan out**, and **you never change the sharding key to fix a query** — you add
   a purpose-shaped store (the date-sharded DB *IRCTC actually operates*).
8. ⭐⭐ **IRCTC is CP for confirmed seats and AP for RAC/waitlist** — consistency chosen **per
   operation**, exactly the tunable-consistency spectrum from Session 8.
9. ⭐⭐ **RAC is eventual consistency sold as a product feature.** It shrinks the strongly-consistent
   set to the ~100 confirmed berths and turns everything above it into an **atomic counter** plus a
   **batch resolver**.
10. ⭐ **Tatkal is a scheduled thundering herd onto hot shards.** You cannot parallelise allocation of
    a scarce seat — so **serialise it deliberately with a queue** rather than accidentally through
    lock contention, and **pre-scale** because you know exactly when it's coming.
11. ⭐⭐ **Keep the strongly-consistent surface as small as possible:** exactly one service in the
    architecture needs ACID; search, dashboards, notifications and waitlist resolution are all
    eventual.

---

## ➡️ Next
**[Session 17 — Case Study: Video Streaming (Netflix)](./17_Case_Study_Video_Streaming_Netflix.md)**
