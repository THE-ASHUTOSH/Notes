# Session 8 — Master-Slave Replication & Tunable Consistency 🎛️

> **Topics:** Master Slave Replication · Tunable Consistency
>
> 📄 Class doc: [\[SST-2028\] Master Slave](https://docs.google.com/document/d/10oYoc-Jnzj0B_mowFyp8DtIGT6d99V7Ni7UJpWXtvm8/edit?tab=t.0)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [Terminology](#-terminology)
2. [Basic Setup & Replication Factor](#-basic-setup--replication-factor)
3. [Operational Questions](#-operational-questions)
4. [Choosing the Replication Factor](#-choosing-the-replication-factor)
5. [Config 1 — No Consistency (R=1, W=1)](#1️⃣-no-consistency--r1-w1)
6. [Config 2 — Eventual Consistency (R=1, W=2)](#2️⃣-eventual-consistency--r1-w2)
7. [Config 3 — Write Everywhere (R=1, W=X)](#3️⃣-immediate-consistency--write-everywhere-r1-wx)
8. [Config 4 — Quorum](#4️⃣-immediate-consistency--quorum)
9. [Tunable Consistency — the Full Spectrum](#-tunable-consistency--unlocking-the-spectrum)
10. [The R + W > X Rule](#-the-rw--x-rule)
11. [Summary Table](#-summary-of-all-configurations)
12. [Key Terms Recap](#-key-terms-recap)

---

## 🏷️ Terminology

> **The terms "Master" and "Slave" have a lot of historical baggage — and some communities don't
> like these words.**

**Also known as:**
| Alternative naming |
|---|
| **Leader – Follower** |
| **Active – Passive** |
| **Primary – Secondary** |

---

## 🏗️ Basic Setup & Replication Factor

```
                     ┌──────────────┐
        WRITES ─────▶│    MASTER    │   ⭐ always has the latest data
                     └──────┬───────┘
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Slave 1  │  │ Slave 2  │  │ Slave 3  │  ⭐ may lag behind
        └──────────┘  └──────────┘  └──────────┘
              ▲             ▲             ▲
              └─────────────┴─────────────┘
                         READS
```

> **Typically in Master-Slave replication, we have an ODD number of total servers (replicas).**
> ⭐ *Note: this is **NOT mandatory** — you can totally have an even number of total "replicas" as
> well.*
>
> ⭐ **Reason: with an odd number of servers, you have a clear majority.**

### Replication Factor (X)
> ⭐ **Replication Factor (X): number of total *copies* of the same data**
> **(X = 1 master + slaves)**

| X | Composition |
|---|---|
| **X = 3** | 1 master + **2** slaves |
| **X = 5** | 1 master + **4** slaves |
| **X = 2** | 1 master + **1** slave |

> ⭐⭐ **Note: replication factor is the number of COPIES. It is NOT the total number of servers.**
> If the database is **sharded**, we will have **shards & replicas**. A database can have
> **S = 100 shards**, each shard having **X = 3 copies** each, for a total of **N = 300 servers**.

```
   S = 100 shards  ×  X = 3 copies  =  N = 300 servers
   ⭐ X is per-shard, not cluster-wide.
```

> **Typical values of X = {3, 5}**

---

## ⚙️ Operational Questions

| Question | Answer |
|---|---|
| **What happens if the master goes down?** | ⭐ **A re-election will happen. One of the slaves will get elected as the new master** |
| **What happens when the old master comes back online?** | ⭐ **It will join as a new slave** |
| **What if a slave crashes?** | ⭐ **Nobody cares. Slaves die all the time.** Basically the read will go to a different slave |
| **How does master election happen?** | **Typically via some "distributed configuration management system"** (e.g. **Zookeeper**). But there are other algorithms as well |
| **How do the slaves sync with the master?** | ⭐ **Asynchronously, using a Write Ahead Log (WAL)** |
| **Where do the writes happen?** | ⭐ **Always happen at least in the master.** *(In some configurations, the writes can also happen in a subset of the slaves)* |
| **Where do the reads happen?** | **In a subset of the slaves** |
| **How many slaves?** | **Typically an even number** (so that the total number of servers is odd, because there's 1 master) |
| **Why an odd number of servers?** | ⭐ **So that we can have a clear majority — easy to do tie breaking (in quorum)** |

> 💡 **The asymmetry is the point:** the master is a **single writer** (so writes are ordered and
> unambiguous), while slaves are **many readers** (so reads scale). This is why replication is
> fundamentally a **read-scaling** technique — exactly as Session 7's table said.

---

## 🔢 Choosing the Replication Factor

> - ⭐ **We need at least 2 copies (1 master + 1 slave)** — because if we have only 1 copy, there's
>   **no replication in the first place** (which will lead to data loss)
> - ⭐ **Typically we keep 3 copies of data (1 master + 2 slaves)**

### When do you need more?
> **If the data is critical and you don't want any data loss whatsoever → set the replication factor
> to X = 5.**
>
> ⭐ **Values above 5 are not used** because they don't really provide any significant benefit in
> terms of data-loss prevention — **it is already very unlikely that 5 different servers from the
> same shard will fail at the same time.**

### The exception — replication for read throughput
> **If you're using replication to improve the read throughput** (read load can be distributed
> amongst the slaves), **then there's no upper limit** — you can have systems with **100 replicas**
> (⭐ but this won't be done for the entire database; **it will only be done for the cache**).

With ~100 replicas, your consistency options narrow:

| Requirement | Approach | Problem |
|---|---|---|
| **Immediate consistency** | use **write quorum / tunable consistency** | ⭐ **quorum worsens the read load** |
| | **write-everywhere** | ⭐ **bad, because there are so many replicas** — the assumption would be that the write load is low enough that you can write to 98 servers before committing (**very very rare**) |
| **Eventual consistency** | ⭐ **just write to master + 1 slave** | **Typically when we have so many read replicas, we need it for a "cache" and usually it is okay to be eventually consistent in this case** |

---

## 1️⃣ No Consistency — R=1, W=1

> **Where writes and reads go, and what it costs:**

| | **Where?** | **Availability** | **Latency** |
|---|---|---|---|
| **Reads (R = 1)** | at **any 1 random slave** *(random slave is different for each read, via **Round Robin**)* | ⭐ **Very High** (if any slave goes down, the request can just be sent to a different slave) | ⭐ **Very Low** (because you're reading from only 1 place) |
| **Writes (W = 1)** | **only at the master** | ⭐ **Very High** (if master goes down, it will just be re-elected) | ⭐ **Very Low** (because you're writing to only 1 place) |

> ⭐ **Note that the writes going only to the master doesn't mean that slaves don't have any data.**
> The slaves **will periodically sync-up** with the master. Instead:
> - ⭐ **the master contains the latest data always**
> - ⭐ **the slaves don't have the latest data always**

### Can there be data loss?
> ⭐ **Yes.** Writes are happening only at the master; slaves sync up with master **periodically**.
> **If the master goes down (HDD failure) with unsynced changes ⇒ these changes are lost forever!**

### Can stale reads happen?
> **There can be stale reads** because the slaves sync up only periodically.
>
> ⭐ **Note: data loss is even worse than stale reads. Because this config gives us data loss, we
> don't even care about stale reads.**

> 🧠 A neat way to think about it: **once you admit data loss, consistency is a moot question** —
> there's nothing to be consistent *about*.

---

## 2️⃣ Eventual Consistency — R=1, W=2

> **We will use this when eventual consistency is good enough.**

| | **Where?** | **Availability** | **Latency** |
|---|---|---|---|
| **Reads (R = 1)** | at **any 1 random slave** *(different for each read)* | **Very High** | **Very Low** |
| **Writes (W = 2)** | ⭐ **Master + 1 random slave (atomically)** — *at least 2 places*; random slave is different for each write, using **Round Robin** | **Decent** (if master goes down it's re-elected; if a slave goes down, just choose another random slave) | **Decent** (⭐ you need to write to 2 places at the same time — using **2 phase commit**) |

### How are we writing to two places at the same time?
> ⭐ **By using Two Phase Commit (2PC)** — we will **acquire distributed locks** to ensure that this
> write to (master + 1 random slave) is **atomic**. If the write doesn't succeed at both places, we
> will **return an error to the client and the client can retry** (meanwhile we will **rollback** the
> partial write).

### Can there be data loss?
> ⭐ **No. Because the data is in at least 2 places.**
>
> - *What happens if the HDD fails in both the places?* That will certainly lead to data loss.
> - *What happens if Thanos attacks earth? Supernova? Black hole?* … if earth explodes, that means
>   data loss. 😄
> - ⭐ **HDDs fail extremely rarely (once every 2–3 years). The chances that these exact two HDDs
>   fail before the rest of the slaves can sync up is astronomically low. Don't worry about it. It's
>   very rare.**
>
> **If we still wish to minimize data loss, then you just write to more places.**

### Can stale reads happen?
> ⭐ **Yes.** The reads are happening at any 1 random slave, and the slaves are **not guaranteed to
> always have the latest data**.
>
> **The latest write went to Master + Slave A, but the read went to Slave B, and Slave B hasn't been
> able to sync up yet — there will be a stale read.**

```
   write ──▶ Master ✅  Slave A ✅        read ──▶ Slave B ❌ (stale)
                                        ⭐ no overlap between the write set and the read set
```

> ⭐ **Remember this picture — "no overlap" is precisely what the quorum rule fixes.**

---

## 3️⃣ Immediate Consistency — Write Everywhere (R=1, W=X)

> **We will use this when we require immediate consistency, and the writes are rare (read heavy
> system).**

| | **Where?** | **Availability** | **Latency** |
|---|---|---|---|
| **Reads (R = 1)** | at **any 1 random slave** | **Very High** | ⭐ **Very Low** |
| **Writes (W = X)** | ⭐ **all nodes — master + all slaves** (write happens at X servers atomically) | ⭐ **Very Low** (if even 1 replica goes down, or fails to acknowledge, your writes have to be denied, and other replicas will have to roll back) | ⭐ **Very High** (you've to wait for **all** servers to respond — **limited by the slowest server**. Apart from that, in failure scenarios you might have to wait for retry/rollback) |

> ⭐⭐ **Note that the protocol says we must write to all X nodes. It does NOT say you should write
> to all replicas which are *alive*. In write-everywhere, if even 1 replica is down, the writes have
> to be DENIED!**

> ⭐ **In write-everywhere the master's boundary is blurred. There's basically no difference between
> the master and the slave.** *(Every node has identical, current data — so "master" loses meaning
> except for coordination.)*

### Can there be data loss?
> **No. All the copies are always in sync, and each write is replicated in multiple places.**

### Can stale reads happen?
> **No. All copies are always in sync.**

> 🧠 **This is the purest expression of PACELC's "ELC":** perfect consistency, perfect read latency,
> and you pay **entirely** on the write side — in both latency *and* availability.

---

## 4️⃣ Immediate Consistency — Quorum

> **We will use this when we require immediate consistency, and the writes are frequent (write heavy
> system, or it's a balanced system).**
>
> ⭐ **Idea: Improve the writes at the cost of reads.** In write-everywhere, the reads are very fast
> but the writes are very slow. **If we trade off, then both will be decent.**

| | **Where?** | **Availability** | **Latency** |
|---|---|---|---|
| **Reads** `R = (X+1)/2` | ⭐ **to a majority** (more than half of the total replicas — any random copies) | **Decent** (at least half the servers have to go down for the request to be denied) | **Decent** |
| **Writes** `W = (X+1)/2` | ⭐ **to a majority (atomically)** — master + at least a random half of the slaves | **Decent** (at least half the servers have to go down for the request to be denied) | **Decent** |

### Majority
> **Majority = More than half the total amount.**
>
> ⭐ **If the Replication Factor = X, then majority will be `ceil((X+1)/2)`**
>
> For example, **if your replication factor is X = 5, then any reads or writes must succeed at at
> least 3 nodes** for the request to be successful.

| X | Majority `ceil((X+1)/2)` |
|---|---|
| 3 | **2** |
| 5 | **3** |
| 7 | **4** |

### Can there be data loss?
> **No. Because we're writing to a majority, and the majority is at least 2.**

### Can stale reads happen?
> ⭐ **No. You always read the latest data, because there's at least 1 overlap** (there's at least
> one server that you're reading from that **also got the latest write**).

```
   X = 5 replicas:   [1] [2] [3] [4] [5]
   WRITE to 3    :    ✔   ✔   ✔
   READ  from 3  :            ✔   ✔   ✔
                              ↑
                    ⭐ GUARANTEED overlap → you see the latest write
```

### Resolving which value is latest
> **Since different reads will return different values, we will always maintain the TIMESTAMP
> whenever writes happen. And then when reading, we will return the value which has the latest
> timestamp.**

> **Q: Does this mean we have to synchronize the clocks across all the replicas to generate the
> timestamp during write?**
> ⭐ **No. The timestamp can be generated at the "coordinator"** (the database app server that is
> coordinating the write across the various replicas).

> 💡 **Neat escape from a hard problem.** Distributed clock synchronisation is notoriously difficult
> (it's why Google Spanner needs atomic clocks). By stamping at the **coordinator**, a single clock
> orders the write — no cluster-wide time agreement needed.

### What if some servers are down?
> - ⭐ **The replication factor X tells you the MINIMUM number of copies of data you must maintain at
>   all times.** You might maintain more copies for whatever reason. **Momentarily (when a replica
>   crashes), the number of copies may fall below X. But it is the DB's responsibility to ensure
>   that for most of the time, the number of copies remains at least X.**
> - **Does the replication factor X change when a replica crashes?** ⭐ **No — the replication factor
>   is a CONFIGURATION PARAMETER. It is not the live number of replicas.**
> - ⭐ **Irrespective of how many servers have crashed, Quorum requires you to read/write successfully
>   to at least `ceil((X+1)/2)` replicas.**
>
> **Example:** if **X = 7**, our desired majority is **4**. Now imagine **4 of the servers have
> crashed**. ⭐ **In this case, no reads or writes can happen** (because there are only 3 servers
> remaining, but Quorum says you need to read/write to at least 4).

> ⭐ **This is CAP made concrete:** the cluster is *alive* but **refuses healthy requests** to
> protect consistency. Textbook **C+P**.

---

## 🎚️ Tunable Consistency — Unlocking the Spectrum

> ⭐⭐ **Idea: for immediate consistency, the number of reads & writes don't have to be EQUAL. All we
> need to do is ensure that there's an OVERLAP.**

### The three configurable parameters
| Parameter | Definition |
|---|---|
| **X** = Replication Factor | ⭐ **Minimum number of copies that must be maintained for each piece of data at all times** |
| **R** = Number of Reads | ⭐ **Minimum number of servers which must respond with data for the read to succeed** |
| **W** = Number of Writes | ⭐ **Minimum number of servers which must acknowledge the write for the write to succeed** |

### The configurations, unified

| R, W | Equivalent to | Consistency | Notes |
|---|---|---|---|
| **R = 1, W = 1** | Master-Slave with **no consistency** — data loss | ❌ **None** | write at master, read from any 1 random slave. ⭐ **No consistency, but perfect availability!** |
| **R = 1, W = 2** | Master-Slave with **eventual consistency** | ⚠️ **Eventual** | write at master + any 1 random slave; read from any 1 random slave. **Eventual consistency, and high availability** |
| **R + W ≤ X, and W > 1** | — | ⚠️ **Eventual** | ⭐ **we will get eventual consistency** |
| **R + W > X** | — | ✅ ⭐ **IMMEDIATE** | see the rule below |
| **R = 1, W = X** | ⭐ **write everywhere** | ✅ Immediate | |
| **R = W = (X+1)/2** | ⭐ **quorum** | ✅ Immediate | |

---

## 🎯 The R + W > X Rule

> ⭐⭐ **R + W > X**
>
> *(the number of servers that we're writing to) + (the number of servers that we're reading from)*
> **is more than the total number of available servers**
>
> ⇒ ⭐ **there's at least one server that is being both written to and being read from — there's an
> OVERLAP!** *(proof: **pigeonhole principle**)*
>
> ⇒ ⭐ **we've immediate consistency!**

```
   ⭐ THE ONE FORMULA TO REMEMBER FROM THIS SESSION:

            R + W  >  X    ⇒   IMMEDIATE  consistency  (guaranteed overlap)
            R + W  ≤  X    ⇒   EVENTUAL   consistency  (overlap not guaranteed)
```

**Verify the special cases:**
| Config | R | W | X | R+W vs X | Consistency |
|---|---|---|---|---|---|
| No consistency | 1 | 1 | 3 | 2 ≤ 3 | ❌ (+ data loss) |
| Eventual | 1 | 2 | 3 | 3 ≤ 3 | ⚠️ Eventual |
| Quorum (X=3) | 2 | 2 | 3 | **4 > 3** | ✅ Immediate |
| Write everywhere | 1 | 3 | 3 | **4 > 3** | ✅ Immediate |
| Read everywhere | 3 | 1 | 3 | **4 > 3** | ✅ Immediate |

> 💡 **Notice "read everywhere" (R = X, W = 1)** — the mirror image of write-everywhere. It gives
> **immediate consistency with very fast writes and very slow reads**. Ideal for a **write-heavy**
> system that reads rarely. This is the power the formula unlocks: you're no longer limited to the
> four named configurations.

### The tuning levers
> - ⭐ **If R is low ⇒ reads are faster & more available** (because you're reading from only a few
>   servers)
> - ⭐ **If W is low ⇒ writes are faster & more available**
> - ⭐ **If R + W > X ⇒ system is immediately consistent**

### As R+W increases
> - ⭐ **availability becomes LOWER, and your latency is getting HIGHER** (because you need more
>   servers to be alive for the reads/writes to succeed)
> - ⭐ **consistency becomes HIGHER** (because you're more likely to find an overlap — a server which
>   you're reading from which also has the latest write)

```
        R + W  →  ────────────────────────────────────────▶
                  low                                  high
   availability   ████████████████░░░░░░░░░░░░░░░░░░░░░░  falling
   latency        ░░░░░░░░░░░░░░░░████████████████████████  rising
   consistency    ░░░░░░░░░░░░░░░░████████████████████████  rising
                                  ↑
                              R + W = X   (the immediate-consistency threshold)
```

### The big idea ⭐⭐
> **Since we can now choose any values of R + W, this gives us a tremendous amount of power.**
>
> - ⭐ **We can not only decide our consistency, we can also tune the system for read-heavy or
>   write-heavy operation!**
> - ⭐⭐ **In fact, we are no longer limited only to availability *or* consistency — we can choose ANY
>   POINT ON THE SPECTRUM!**

> 🧠 **This is the answer to Session 7's dilemma.** CAP presents A-vs-C as a binary. **Tunable
> consistency reveals it as a continuum** — and even better, it's a **per-query** decision in real
> databases (Cassandra lets you set consistency level per operation: `ONE`, `QUORUM`, `ALL`).
> So a single system can serve an analytics read at `R=1` and a payment write at `W=QUORUM`.

### How to write to more than one place atomically?
> ⭐ **Two Phase Commit (2PC)**
>
> **Resources:**
> - Theory: https://www.youtube.com/watch?v=-_rdWB9hN1c
> - Explanation 1: https://www.youtube.com/watch?v=eltn4x788UM
> - Explanation 2: https://www.youtube.com/watch?v=7FgU1D4EnpQ
> - Implementation: https://www.youtube.com/watch?v=oMhESvU87jM

---

## 📊 Summary of All Configurations

| Config | R | W | Data loss? | Stale reads? | Read latency | Write latency | Read avail. | Write avail. | Use when |
|---|---|---|---|---|---|---|---|---|---|
| **No consistency** | 1 | 1 | ⭐ **YES** | Yes | Very Low | Very Low | Very High | Very High | Analytics / trends only |
| **Eventual** | 1 | 2 | No | Yes | Very Low | Decent | Very High | Decent | ⭐ **99% of systems** |
| **Write Everywhere** | 1 | X | No | **No** | ⭐ **Very Low** | ⭐ **Very High** | Very High | ⭐ **Very Low** | Immediate consistency + **rare writes** (read-heavy) |
| **Quorum** | (X+1)/2 | (X+1)/2 | No | **No** | Decent | Decent | Decent | Decent | Immediate consistency + **frequent writes** (write-heavy/balanced) |
| **Read Everywhere** | X | 1 | No | **No** | Very High | Very Low | Very Low | Very High | Immediate consistency + **rare reads** |
| **Any point** | R | W | No | iff R+W>X | tunable | tunable | tunable | tunable | ⭐ **Tune per workload** |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Master / Slave** | Also **Leader/Follower**, **Active/Passive**, **Primary/Secondary** |
| **Replication Factor (X)** | ⭐ Number of **copies** of each piece of data (**not** total servers) — typically **3 or 5** |
| **S × X = N** | ⭐ shards × copies-per-shard = total servers (100 × 3 = 300) |
| **Odd server count** | Gives a **clear majority** for tie-breaking in quorum |
| **Master re-election** | On master failure a slave is elected (often via **Zookeeper**) |
| **Old master returns** | ⭐ **Joins as a new slave** |
| **Write Ahead Log (WAL)** | How slaves sync **asynchronously** from the master |
| **R** | Min servers that must respond for a **read** to succeed |
| **W** | Min servers that must acknowledge a **write** to succeed |
| **Majority** | `ceil((X+1)/2)` — more than half |
| **Quorum** | R = W = majority → immediate consistency with balanced latency |
| **Write Everywhere** | W = X → fast reads, ⭐ **writes denied if even 1 replica is down** |
| **Read Everywhere** | R = X → fast writes, slow reads |
| ⭐ **R + W > X** | ⭐⭐ **The immediate-consistency condition** (guaranteed overlap, by pigeonhole) |
| **Coordinator** | The node orchestrating a write; ⭐ **generates the timestamp** (no clock sync needed) |
| **Tunable consistency** | Choosing R and W to place the system anywhere on the A↔C and read↔write spectrum |
| **2PC** | Two Phase Commit — makes multi-server writes atomic |

---

## 🎯 Session Takeaways

1. **Master takes writes; slaves serve reads.** The master **always** has the latest data; slaves
   may lag.
2. ⭐ **Replication factor X = number of copies, not servers.** With sharding, `N = S × X`
   (100 shards × 3 copies = 300 servers). Typical X is **3**, or **5** for critical data;
   **above 5 adds nothing**.
3. **Odd counts give a clear majority** — that's the only reason for the convention.
4. **Slave death is a non-event; master death triggers re-election** (often via Zookeeper), and the
   **old master rejoins as a slave**.
5. ⭐ **R=1, W=1 loses data** — and once you accept data loss, stale reads stop mattering.
6. ⭐ **R=1, W=2 is the workhorse:** no data loss, high availability, eventual consistency — the 99%
   case. Two-place writes need **2PC**.
7. ⭐ **Write Everywhere denies writes if even ONE replica is down** — the protocol says all **X**,
   not "all that are alive". Fast reads, terrible write availability.
8. ⭐ **Quorum trades read speed for write speed** so both are "decent", and resolves conflicts by
   **coordinator-generated timestamps** — no clock synchronisation required.
9. ⭐ **X is a config parameter, not the live replica count.** With X=7 and 4 servers dead, the
   cluster correctly **refuses all reads and writes**.
10. ⭐⭐ **The one formula: `R + W > X` ⇒ immediate consistency**, guaranteed by the **pigeonhole
    principle**. `R + W ≤ X` ⇒ eventual.
11. ⭐ **As R+W rises: consistency ↑, latency ↑, availability ↓.** Lower R for fast reads, lower W for
    fast writes.
12. ⭐⭐ **Tunable consistency turns CAP's binary choice into a continuum** — you pick any point, and
    can even tune per query.

---

## ➡️ Next
**[Session 9 — SQL vs NoSQL + Sharding Key](./09_SQL_vs_NoSQL_and_Sharding_Key.md)**
