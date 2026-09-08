# High Level Design (HLD) Notes 🏗️

Section-wise study notes for **Term 8 — High Level Design (SST-2028)**, instructor Kshitij.
One markdown file per session, same format as the [DevOps notes](../DevOps/README.md).

---

## 📚 Sessions

| # | Session | Topics (from syllabus) | Notes file | Class doc |
|---|---|---|---|---|
| **1** | System Design 101 | Why & What of HLD · How the internet works · Challenges at Scale · Vertical vs Horizontal Scaling · Intro to Load Balancing | [01](./01_System_Design_101.md) | [HLD 1 — System Design 101](https://docs.google.com/document/d/13GWDsE0rlfIKNVnBv3ThYPHoX3yEHDzArLMLG15Ifp4/edit?usp=sharing) |
| **2** | Load Balancing and Consistent Hashing | Load Balancing Algorithms — Round Robin & Consistent Hashing | [02](./02_Load_Balancing_and_Consistent_Hashing.md) | [Load Balancing & Consistent Hashing](https://docs.google.com/document/d/1ywh8AHebgelMwIWJ1zPQEIbeEavR1F1Y_RBfKizTWKc/edit?usp=sharing) |
| **3** | Caching – 1 | The Caching Hierarchy: Browser, CDN, Backend · Types of backend caches: Local vs Global, Single vs Distributed · Challenges with Caching — Eviction & Invalidation | [03](./03_Caching_Hierarchy_and_Types.md) | [Intro to Caching](https://docs.google.com/document/d/1wCMktm6Yh_XHoN5o0YvDsRLMYPGBIYpAs3B6jn4oYes/edit?tab=t.0) |
| **4** | Caching – 2 | Eviction mechanisms · Immediate & Eventual Consistency · Invalidation Mechanisms · Case Study — Scaler Code Judge | [04](./04_Caching_Eviction_and_Invalidation.md) | [Caching 2](https://docs.google.com/document/d/12tdw0PoZAOhgCH8A9HgWu9zYYjUDS4lzaq3gqcrLZq8/edit?tab=t.0) |
| **5** | Caching: Case Studies | Scaler Code Judge (continued) · Scaler Leaderboard · Social Media Newsfeed | [05](./05_Caching_Case_Studies.md) | [Caching Case Studies](https://docs.google.com/document/d/13GogwThXSMBB5lXPKAuoMm3lNKx4Yn0NZcOEVaQ2IpQ/edit?tab=t.0) |
| **6** | Facebook Newsfeed | Building a simple Chat Application · HTTP APIs & API Design Practices · Microservices in Python (Message Service, Analytics Service) · HTTP vs RPC between services · Image upload in messages | [06](./06_APIs_Microservices_and_Newsfeed.md) | ⚠️ *(no doc linked)* |
| **7** | Storage layer — CAP dilemma, Replication | CAP & PACELC theorems · Replication vs Sharding | [07](./07_CAP_PACELC_Replication_vs_Sharding.md) | [CAP-PACELC](https://docs.google.com/document/d/1hrZ9_18wXISAUqoztCwEF1z9q4hAuXpL5hpNvl00LlA/edit?tab=t.0) |
| **8** | Master-Slave | Master-Slave Replication · Tunable Consistency | [08](./08_Master_Slave_and_Tunable_Consistency.md) | [Master Slave](https://docs.google.com/document/d/10oYoc-Jnzj0B_mowFyp8DtIGT6d99V7Ni7UJpWXtvm8/edit?tab=t.0) |
| **9** | SQL vs NoSQL + Sharding Key | Pros of SQL: ACID + Normalization + Defined Schema + Indexes · Cons: how sharding invalidates all benefits · How to choose the sharding key | [09](./09_SQL_vs_NoSQL_and_Sharding_Key.md) | [Sql vs NoSql + Sharding Key](https://docs.google.com/document/d/1Pdck0k2_GpUoHGFQ_dmcH0pSPwKIdssuPsnKyyidUso/edit?tab=t.0) |
| **10** | NoSQL Internals (LSM Tree) | Basics of RDBMS internals · Designing a NoSQL DBMS · LSM Tree | [10](./10_NoSQL_Internals_LSM_Tree.md) | [NoSQL Internals — LSM Tree](https://docs.google.com/document/d/1fJMHZAqAUKQVuZUkqp9t7-KIGvh6ZbT1gtOwUK9AUhg/edit?usp=sharing) |
| **11** | NoSQL Internals (LSM Tree) – 2 | Read queries in LSM tree · Sparse index · Bloom Filter | [11](./11_NoSQL_Internals_Sparse_Index_and_Bloom_Filter.md) | [LSM Tree + Bloom Filter + Sparse Index](https://docs.google.com/document/d/1U8E-VUnnCDyiQYjiRThqEGFbNAxFr_H_1npiK-_lD1Y/edit?tab=t.0) |
| **12** | Case Study 1 — Search Typeahead | Google Search Typeahead | [12](./12_Case_Study_Search_Typeahead.md) | [Case Study: Google Search Typeahead](https://docs.google.com/document/d/11YhxJwEiwWLVUoSAfFEacY0e49hb7zg_enOLpsIvNIc/edit?tab=t.0) |
| **13** | Case Study — Search Typeahead-2 | Typeahead continued | [13](./13_Case_Study_Search_Typeahead_2.md) | [Case Study: Typeahead-2](https://docs.google.com/document/d/1AjOS8itQOsg6VSjrUbKuiVg_6hsgeSStQKc_39DjTcw/edit?tab=t.0) |
| **14** | Case Study 2 — Messaging Application-1 | Design FB Messenger · Sharding key choices 1:1 vs group · Low latency + immediate consistency | [14](./14_Case_Study_Messaging_Applications.md) | [Case Study: Messaging Apps (FB Messenger, WhatsApp, Slack)](https://docs.google.com/document/d/13sJnV5Xj1ZPalJeA0uuiJqe0oJYZ0U4b-0IfXjxmJac/edit?usp=sharing) |
| **15** | Types of NoSQL Databases and Messaging Application-2 | Key-value, document, column-family, object/large-file, graph, vector | [15](./15_Types_of_NoSQL_Databases.md) | [Types of NoSQL Databases](https://docs.google.com/document/d/1cZ3HRQwR9r7fLboa6kSS6nXxKoVLmq0xrfeCSXFCMjA/edit?usp=sharing) |
| **16** | Case Study 3 — IRCTC | Ticket booking · ACID to avoid double booking · Multi-service | [16](./16_Case_Study_IRCTC.md) | ⚠️ *(no doc linked — built from the IRCTC passages inside the Session 9 & 7 docs)* |
| **17** | Case Study 4 — Video Streaming Platform (Netflix) | Thumbnails, multiple resolutions, live broadcast to millions | [17](./17_Case_Study_Video_Streaming_Netflix.md) | [Case Study: Video Streaming — Netflix](https://docs.google.com/document/d/1FHxmMkLWDxiSz43qucIJxAK3Fl-yZCmGKPjxRwn_nNY/edit?usp=sharing) |
| **18** | Case Study 5 — Cab Booking Application (Uber) | Uber design · QuadTrees — Nearest Neighbour Search | [18](./18_Case_Study_Uber_and_QuadTrees.md) | [Case Study: Uber](https://docs.google.com/document/d/1WN1DdgdgjnqlFbWuRwua0dfNWHFwDCLuHFQHNAzs0nU/edit?tab=t.0) · *QuadTrees doc link not recoverable — see note* |

> ⚠️ **Sessions 6 and 16 have no class doc** in the course sheet. Their notes are assembled from the
> syllabus topics plus the substantial material other class docs contain on those subjects
> (Session 9 & 7 cover IRCTC's sharding and CAP position in depth; Sessions 12 & 14 cover API design
> and messaging). Each file states this at the top.

> ℹ️ **Doc links** were recovered from the hyperlink relationships inside the course timetable
> spreadsheet (*"Kshitj Term 8 - High Level Desi"* tab, Notes column). Cell **D20** contained
> **two** links (Uber + QuadTrees) but the spreadsheet format stores only one hyperlink per cell,
> so the **QuadTrees — Nearest Neighbor Search** doc URL could not be recovered — please paste it
> if you want it indexed.

---

## 📝 Assessment structure (from the syllabus sheet)

| Component | Weightage | When |
|---|---|---|
| Assignments | 20% → later rows show 30% | Continuous; due one day before exam. `Assignment Score = PSP × [Assignment section in end-term exam]` |
| Quiz | 20% | 24th May — based on case studies and concepts discussed in class |
| Mock Interview | 20% | Last week of course |
| Final Exam | 40% (50% for internship-exempted students) | — |
| **Credits** | **3** | — |

**Linked assignment:** [HLD101 Assignment: Search Typeahead](https://docs.google.com/document/d/1GyQX3dNrcq5YlBiAxq9MNzS9wPwu_ZmRslAEjvhw8Bo/edit?tab=t.0) *(opens before the Caching–1 class)*

**Assigned readings listed in the sheet**
- Session 1 — [Cassandra: A Decentralized Structured Storage System](https://www.cs.cornell.edu/projects/ladis2009/papers/lakshman-ladis2009.pdf) (Lakshman & Malik, LADIS 2009)
- Session 5 — [Kafka: a Distributed Messaging System for Log Processing](https://pages.cs.wisc.edu/~akella/CS744/F17/838-CloudPapers/Kafka.pdf) (Kreps et al., NetDB 2011)

---

## 🗺️ How the sessions build on each other

```
  01 System Design 101              ← scale, bottlenecks, scaling axes, load balancing
        │
        └── 02 Load Balancing + Consistent Hashing   ← how to spread load WITHOUT reshuffling
                  │
                  ├── 03 Caching: hierarchy & types  ← the biggest latency win
                  ├── 04 Caching: eviction + invalidation + consistency intro
                  └── 05 Caching case studies        ← Code Judge, Leaderboard, Newsfeed
                            │
                            └── 06 APIs & Microservices (FB Newsfeed / chat app)
                                      │
   ┌──────────────────────────────────┘
   │  STORAGE LAYER
   ├── 07 CAP & PACELC · Replication vs Sharding     ← the central trade-off
   ├── 08 Master-Slave replication · Tunable consistency
   ├── 09 SQL vs NoSQL · choosing the sharding key
   ├── 10 NoSQL internals: LSM tree
   ├── 11 NoSQL internals: sparse index + bloom filter
   └── 15 Types of NoSQL databases
                    │
                    ▼
   CASE STUDIES (apply everything above)
   12–13 Search Typeahead (tries, prefix aggregation)
   14    Messaging apps  (FB Messenger / WhatsApp / Slack)
   16    IRCTC           (ACID, double-booking, locking)
   17    Netflix         (video encoding, CDN, live streaming)
   18    Uber            (geospatial indexing, QuadTrees)
```

**The spine of the course:** *scale forces distribution → distribution forces trade-offs
(CAP) → trade-offs are made concrete by caching, replication and sharding → case studies are
where you defend your choices.*

---

## 🧭 Recurring concepts to watch for

| Concept | Introduced | Reappears in |
|---|---|---|
| Read:write ratio drives design | 01 | 03–05 (caching), 08 (replicas), 12–18 |
| `hash(key) % N` breaks on resize | 01 | **02** (consistent hashing), 09 (sharding key) |
| Eventual vs immediate consistency | 04 | 07 (CAP), 08 (tunable), 14 (messaging) |
| Hot keys / celebrity problem | 01 | 02, 05 (newsfeed), 09 (sharding key), 14 |
| Sequential writes beat random writes | 01 (latency ladder) | **10** (LSM tree) |
| Sharding removes joins & transactions | 01 | 07, **09**, 16 (IRCTC) |
| Precompute vs compute-on-read | 05 | 12–13 (typeahead), 14 (newsfeed fan-out) |
| Quorums (R + W > N) | 07 | 08 (tunable consistency) |

---

## 🔗 References
- Course timetable sheet — [April 23–June 30 Weekly Schedule](https://docs.google.com/spreadsheets/d/1ZBRR1epIUoSO2WJ32Fi6qcoWC2cWtmXFVOr80wfE1RE/edit?gid=77917834)
- Cassandra paper — https://www.cs.cornell.edu/projects/ladis2009/papers/lakshman-ladis2009.pdf
- Kafka paper — https://pages.cs.wisc.edu/~akella/CS744/F17/838-CloudPapers/Kafka.pdf
