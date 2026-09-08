# Session 9 — SQL vs NoSQL + Choosing the Sharding Key 🗃️

> **Topics:** Pros of SQL databases: ACID + Normalization + Defined Schema + Indexes · Cons of SQL
> databases — how sharding invalidates all benefits · How to choose the sharding key
>
> 📄 Class doc: [\[SST-2028\] Sql vs NoSql + Sharding Key](https://docs.google.com/document/d/1Pdck0k2_GpUoHGFQ_dmcH0pSPwKIdssuPsnKyyidUso/edit?tab=t.0)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [SQL is a Language, not a Database](#-sql-is-a-language-not-a-database-type)
2. [Strengths of RDBMS](#-strengths-of-rdbms-at-low-scale)
3. [ACID](#-acid-transactions)
4. [ACID Consistency ≠ CAP Consistency](#-acid-consistency--cap-consistency)
5. [Weaknesses of RDBMS at Scale](#-weaknesses-of-rdbms-at-large-scale)
6. [The Amazon Product Catalogue Problem](#-the-amazon-product-catalogue-problem)
7. [Sharding Nullifies ACID](#-sharding-nullifies-acid)
8. [NoSQL](#-nosql-databases)
9. [BASE](#-base)
10. [SQL vs NoSQL Summary](#-sql-vs-nosql-summary)
11. [Choosing a Sharding Key](#-choosing-a-sharding-key)
12. [Primary Key vs Sharding Key](#-primary-key-vs-sharding-key)
13. [Rules About Sharding Keys](#-rules-about-sharding-keys)
14. [What Makes a Good Sharding Key](#-what-constitutes-a-good-sharding-key)
15. [Worked Example — Banking](#-worked-example-1--banking-system)
16. [Worked Example — IRCTC](#-worked-example-2--irctc)
17. [Worked Example — FB Messenger](#-worked-example-3--facebook-messenger)
18. [Worked Example — Slack](#-worked-example-4--slack)
19. [Sequential vs Random Access](#-how-storage-works--sequential-vs-random-access)
20. [Key Terms Recap](#-key-terms-recap)

---

## 📝 SQL is a Language, not a Database Type

> **Structured Query Language (SQL)**
> - **It's a "query" language** — a way of specifying **what** to fetch from the DB
> - ⭐ **SQL is not a DB type — it's just a query language**
> - **SQL is the de-facto query language for Relational DBs**
> - ⭐ **When people say SQL, they mean Relational DB**
> - **Even in Relational DBs, you can choose other querying languages** — example: **GraphQL**

**Common Relational Database implementations:** MySQL, PostgreSQL, OracleDB, MSSQL, SQLite,
IBM DB2, Amazon RDS, …

---

## 💪 Strengths of RDBMS (at low scale)

> ⭐ **All these strengths apply at LOW SCALE.**
>
> **Low Scale:** *"queries/second, amount of data"* **is small enough to be handled by a single
> server.**

### 1. Relations & Normalization
> - **Data is stored in tables** — tables can have **relations** with each other (via **foreign
>   keys**)
> - **It is recommended to model data in a normalized manner**
> - ⭐ **Normalization prevents anomalies & reduces redundancy**

### 2. Strong Schema
| Property | Meaning |
|---|---|
| **Well Defined** | **You know exactly what tables exist**; **what columns exist** in each table; **the data-type of each column**. ⭐ **Allows you to allocate a fixed amount of space for each row on the disk** |
| **Static** | ⭐ **The schema does not change for different rows.** Changing the schema is **not encouraged, and is difficult** — it is possible to add/remove columns, **however that requires a complete table re-write**: **extremely slow (table migration)**, **requires the service to be down** *(there are ways around this — **rolling migration**)* |
| **Enforced** | ⭐ **If a row violates the table's schema, then the DB will let you know. It won't let the write succeed** |

---

## 🔐 ACID Transactions

> **Extremely powerful & good to have.**

### **A** — Atomicity
> ⭐ **All or nothing:** Each transaction is either executed **completely** (all rows) **or not at
> all**. **There are no partial states.**

> **Imagine that Khushboo is transferring 1 million $ to Vishudh:**
> 1. Check if Khushboo has sufficient account balance
> 2. Deduct 1 million $ from Khushboo's account
> 3. Add 1 million $ to Nimish's account
>
> ⭐ **It should not be the case that the money gets deducted from Khushboo, but isn't credited to
> Nimish.** We want to ensure that **either the money is not deducted from Khushboo, or, if
> deducted, it must be successfully credited.**

### **C** — Consistency
> ⭐ **ACID consistency ≠ CAP consistency** *(wait, what!!?)* — see the next section.

### **I** — Isolation
> ⭐ **Multiple transactions that are running simultaneously don't mess with each other.**
> **There are different isolation levels.** *(📝 homework: read up on this)*

**The classic failure — lost update:**
```
Transaction 1: Khushboo –1 million $→ Vishudh      Transaction 2: Khushboo –1 million $→ Nandani
  1. balance = get_balance(Khushboo)                 1. balance = get_balance(Khushboo)
  2. assert balance > 1 million $                    2. assert balance > 1 million $
  3. new_balance = balance - 1 million $             3. new_balance = balance - 1 million $
  4. set_balance(Khushboo, new_balance)              4. set_balance(Khushboo, new_balance)
  5. receiver_balance = get_balance(Vishudh)         5. receiver_balance = get_balance(Nandani)
  6. set_balance(Vishudh, receiver_balance + 1M)     6. set_balance(Nandani, receiver_balance + 1M)
```
> **Khushboo started with 1 million $:**
> ```
> T1: steps 1..3
> T2: steps 1..3            ← both read the SAME balance
> T1: step 4    →  Khushboo's new balance = 0
> T2: step 4    →  Khushboo's new balance = 0
> T1: steps 5..6            ← Vishudh gets 1M
> T2: steps 5..6            ← Nandani ALSO gets 1M
> ```
> ⭐ **This is lack of isolation! This should NOT happen.**
> *(₹1M became ₹2M — the bank just printed money.)*

### **D** — Durability
> **Any transaction that has been executed will be stored in non-volatile storage (HDD/SSD) and not
> just the volatile RAM.**
>
> ⭐ **Note: Durability does NOT protect you against HDD failures — only replication does.**
> *(Session 7.)*

### Other Strengths
> **Very powerful querying capabilities:** **joins** · filtering by column values · **aggregate
> calculations** · grouping · **nested queries** · **recursive queries (CTEs)**
>
> **Extra features:** Full text search · Geospatial queries · JSON · …
>
> ⭐ **They offer pretty much every feature that any other database in the world provides!**
> *(just at low scale)*
>
> **Relational DBs are extremely mature:**
> - ⭐ **Relational database theory predates modern computer hardware!**
> - **Battle tested across thousands of various scenarios, by millions of companies!**

---

## 🔀 ACID Consistency ≠ CAP Consistency

⭐⭐ **A guaranteed interview question.** They are completely different things that share a word.

| | **CAP Consistency** | **ACID Consistency** |
|---|---|---|
| **Means** | ⭐ **No stale reads** | ⭐ **DB constraints are enforced** |
| **About** | Multiple **copies** of data (replicas/cache) being in sync | A **single** database's rules being satisfied |
| **Precisely** | When we have multiple copies of the data (replicas/cache), and some copy is out-of-sync with other copies, **then we should not read from the stale copy** | **Every transaction should leave the database in a consistent state** |
| **Examples** | Replication lag, cache staleness | **schema** (columns & data-types) · **not-null / unique / foreign key constraints** · **custom constraints** (e.g. "the value in this column should only be a lowercase string") · **triggers** |

> 🧠 **Mnemonic:** **CAP-C is about *copies*. ACID-C is about *constraints*.**

---

## 📉 Weaknesses of RDBMS (at large scale)

> ⭐⭐ **When the scale becomes large, ALL the strengths become weaknesses!**
>
> **Large Scale:** data or req/s is **too large to fit on a single server**.

### Weakness 1 — Normalization
> - ⭐ **On the frontend, we (almost) always need to show "denormalized" data** (data about a lot of
>   entities)
> - **Therefore, to display the data, we need to perform joins**
> - For example, to display [this StackOverflow page](https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array)
>   ⭐ **you will need to join around 30–40 tables**
> - **If you have lots of tables, then joining all of them grinds to a halt**
> - ⭐ **What if the data is too large to fit on a single server? Joins have to be executed across
>   servers!** → **impossibly slow**, **too much n/w overhead**

> ⭐ **The irony:** normalization is *good practice* that creates *the exact work* (joins) that
> becomes *impossible* at scale.

---

## 🛒 The Amazon Product Catalogue Problem

### Weakness 2 — Strong Schema
> **What if the data itself is inherently unstructured?**
>
> **Q: How to model product listings for Amazon in a SQL DB?**
> - **Amazon has 10 million+ products across 10,000+ categories**
> - ⭐ **Every category has a different attribute set:**
>   - **T-shirts:** Brand, Price, Color, Fabric, Neck-shape, Sleeve length
>   - **Laptops:** Brand, Price, Screen Size, RAM, CPU, GPU, OS
>   - **Notebook:** Brand, Price, Page thickness, Number of Pages, Ruled

Three attempts, all bad:

### Attempt 1 — Giant table with all columns
```sql
products: id, name, brand, price, Color, Fabric, Neck-shape, Sleeve length,
          Screen Size, RAM, CPU, GPU, OS, Page thickness, Number of Pages, Ruled, ...
```
> - ⭐ **Too many columns** — 10,000 categories × 10 unique cols per category ⇒ **100,000 columns**
> - **Every row will only store data for 10 columns** — rest of the 100,000 columns will be **nulls**
> - ⭐ **`null` in itself is bad — because it is ambiguous.** `null` can mean two things:
>   - **missing data:** the data is there, but we just don't know it
>   - **undefined value:** *what's the Page-Thickness of this t-shirt?*
> - ⭐ **SQL pre-allocates space for the entire row** (all columns included) — **even for the columns
>   where the value is null** → **you're effectively wasting 99.99% of the disk space**

### Attempt 2 — Multiple tables
```sql
products:   id, name, brand, price
tshirts:    product_id, Color, Fabric, Neck-shape, Sleeve length
laptops:    product_id, Screen Size, RAM, CPU, GPU, OS
notebooks:  product_id, Page thickness, Number of Pages, Ruled
… 10,000 such tables, one for each product type
```
> - ⭐ **If you want to fetch data like "find top 10 most expensive products which are of colour red",
>   then you will have to join across 10,000 tables**
> - ⭐⭐ **SQL is not designed for this scale:** **SQL can handle lots of rows and terabytes of data**
>   (few tables, lots of data in those tables) — **but SQL cannot handle lots of "schema" (many
>   tables)**

### Attempt 3 — Attribute List (EAV)
```sql
products:            id, name, brand, price
product_attributes:  product_id, attribute_name, attribute_value
```
| product_id | attribute_name | attribute_value |
|---|---|---|
| 1 | RAM | 16GB |
| 1 | CPU | i9 14400k |
| 1 | Screen Size | 17" |
| 1 | **Fabric** | **cotton** |
| 2 | Neck Type | Rounded |
| 2 | Sleeve Length | full |
| 2 | Fabric | cotton |

> - ⭐ **Schema enforcement is LOST: laptops can now have fabric** *(see row 4 above!)*
>   - You can still enforce attributes on the **application layer** — ⭐ **but that breaks separation
>     of concerns.** Now your data validation lives **partially in the DB layer and partially in the
>     App server layer**
>   - **The DB has lost the ability to enforce a schema** (you can assign any attribute to any entity)
> - ⭐ **Fetching data about a single entry is too expensive:** if you need to show the details of the
>   laptop, **you have to fetch all attributes of the laptop, and then join them into an array**

> ⭐ **Conclusion: since the data was inherently "semi-structured", SQL was not a good choice.**
> **At low scale (only 2–3 different product categories) SQL could've worked.**

> **Q: But modern SQL databases support JSON. So can't I just use that?**
> ⭐ **Yes, and no!** Relational DBs like Postgres, MySQL have **1st class support for JSON**.
> **However, it still is not designed to handle scale.**

---

## ⛓️ Sharding Nullifies ACID

### Weakness 3 — ACID Transactions
> **When the data is large (high scale), then you need sharding — because you can't store all the
> data in a single server.**
>
> ⭐⭐ **Sharding nullifies ACID.**
>
> **SQL DBs provide ACID guarantees only within a single server.** Because it is easy to do that:

| Inside a **single** server | With **multiple** servers |
|---|---|
| ⭐ **you can acquire locks easily** (OS, hardware facilitates locks/semaphores) | ⭐ **distributed locks are extremely hard & extremely slow** (because **PACELC**) — 2PC / Zookeeper |
| ⭐ **you can share memory** (RAM, HDD) — so **no n/w overhead** to communicate across transactions, and **no consistency (stale read) issues** when two threads read from the same RAM location | ⭐ **sharing memory is not possible** — keep copies, **and that leads to consistency challenges** |
| ⭐ **you know whether the write has succeeded or failed** | ⭐ **you don't know if the writes succeeded** — you have to pass acknowledgements |
| **writes mostly always succeed** | ⭐ **networks & servers regularly fail** |

> ⭐ **Providing ACID guarantees across shards is extremely difficult** — **possible, but very slow,
> and very complex!**

```
   ⭐ THE CENTRAL ARGUMENT OF THIS SESSION:

      scale  ⇒  sharding  ⇒  no cheap joins, no cheap ACID
      …which are precisely the two things you chose SQL for.
```

---

## 🆕 NoSQL Databases

### What is NoSQL?
> - **NoSQL ≠ No SQL** *(what??)*
> - **No SQL ≠ don't use SQL**
> - ⭐⭐ **NoSQL = "Not Only SQL"** — **we will still continue using relational databases, but we
>   will augment their capabilities with additional non-relational databases**

### History
> - **SQL DBs have existed for a very long time** — even before modern computers came into picture,
>   the theoretical foundations for **relational algebra** were already laid
> - **NoSQL DBs are extremely recent:**
>   - ⭐ **the first NoSQL db was BigTable by Google**
>   - **NoSQL dbs started getting popular only after 2005**
>   - ⭐ **most internet giants did not even exist before 2005**
> - 😄 **Around 2009/2010 there was a conference about non-relational DBs. The promoters needed a
>   Twitter hashtag to go viral — `#NoSQL`**

### ⭐ Don't jump to NoSQL
> - ⭐⭐ **Your de-facto choice should ALWAYS be Relational (SQL) databases.**
> - **You can use NoSQL — but only if you can justify the need for it.**
> - **Modern SQL databases (like Postgres, MySQL) can do absolutely everything that any NoSQL can do
>   & even more** — *just at a low scale*
> - ⭐ **The bar of "low scale" keeps increasing every day**
> - ⭐ **For up to a 1 million userbase, a SQL db will just work flawlessly**
> - ⭐⭐ **99% of the companies use SQL databases, and 99% of companies do NOT need NoSQL databases
>   primarily!**

---

## ⚖️ BASE

> 📖 https://aws.amazon.com/compare/the-difference-between-acid-and-base-database/

| Letter | Meaning |
|---|---|
| **Ba** — **Basically Available** | ⭐ **The system as a whole will remain available, even though some services might be unavailable for a small fraction of the users for some time.** High availability **for the entire system, not for individual services/users** |
| **S** — **Soft State** | ACID transactions provide atomicity (all or nothing). ⭐ **Soft state: transactions can be in a partial state for some time (even for extended time — weeks!) — they're not all-or-nothing — but eventually the data will become consistent and atomic.** *(we will see this in the last class of HLD — **distributed transactions in microservices — Saga Pattern**)* |
| **E** — **Eventually Consistent** | **There might be stale reads. But eventually (if we wait long enough) every write will be reflected across the entire system (all replicas)** |

### Horizontally Scalable ⭐
> - **SQL databases require MANUAL sharding** — they don't provide built-in support for sharding
>   *(note: most modern SQL DBs have built-in support for **replication**, but not **sharding**)*
> - **You can shard a SQL database either:**
>   - by using a **3rd party extension**
>   - by doing it **manually** (writing LB code, managing the server state…)
>   - by using a **"managed" cloud service** like Amazon RDS
> - ⭐⭐ **NoSQL DBs are automatically sharded — they're built with horizontal scaling in mind. You
>   just have to get a bunch of servers and install the database on them, and they will figure stuff
>   out themselves** (LB, autoscaling, sharding, data distribution, replication, fault tolerance…)

### Denormalization & Replication
> - **SQL databases discourage denormalization & redundancy to remove anomalies**
> - **NoSQL databases realise that:**
>   - ⭐ **in the frontend you're anyway going to show denormalized data**
>   - ⭐ **to prevent data loss, we're going to have multiple copies of the data anyway**
> - ⭐ **NoSQL DBs ENCOURAGE storing data in a denormalized / semi-structured (sometimes even
>   schemaless) manner**

---

## 📊 SQL vs NoSQL Summary

| | **SQL** | **NoSQL** |
|---|---|---|
| Guarantees | ⭐ **ACID** | ⭐ **BASE** |
| Data modelling | **Normalization** | ⭐ **Denormalized data & redundancy** |
| Philosophy | ⭐ **Do everything, decently well** (**Jack of all trades**) | ⭐ **Do 1 thing, extremely well** (**Master of one**) |
| Servers | ⭐ **1 server** | ⭐ **Multiple servers** (built-in sharding, auto scaling, load balancing, …) |

### Weaknesses of NoSQL databases
> **SQL databases have tons of features:** joins · powerful ways to structure data · enforceable
> constraints · triggers · **ACID guarantees** · powerful indexing · powerful filtering · recursive
> queries
>
> **Modern features:** full text search · semi-structured data (first class JSON support) ·
> **spatial indexing (nearest neighbour queries)** · **vector support (KNN queries)** ·
> denormalized views (table views)
>
> ⭐ **Any feature that you can think of, modern SQL DBs have it. The only con of SQL is that it is
> feasible only at low scale.**
>
> - ⭐ **SQL databases "generalize" — jack of all trades, master of none** (they don't work at scale)
> - ⭐ **NoSQL databases can work at massive scale because they DON'T support most of the features**
>   - **it is hard to do everything perfectly**
>   - **it is easy to do a few things flawlessly**
> - ⭐⭐ **NoSQL databases "specialize" — jack of 1 trade, and master of it**

> 🧠 **This reframes the whole SQL-vs-NoSQL debate.** NoSQL isn't "better" or "newer" — it is
> **narrower on purpose**, and that narrowness is exactly what buys the scale.

### When *not* to use a relational DB — the row-size rule ⭐
> **You should only use it if your individual data items (1 row) are "small": < 1 KB, or a few KB
> max. If your rows are usually > 10 KB, then you should probably not use a SQL database.**
>
> *Note that your database will not complain even if you try to store a 100 MB row. It's just
> stupid / a bad database choice to store such large values in a SQL DB row.*
>
> ⭐ **This does NOT mean that SQL can only handle 10 KB of data. SQL can handle terabytes of data —
> it's just that the data must be in multiple rows and tables; the individual rows should not be too
> large.**

---

## 🔑 Choosing a Sharding Key

> - ⭐ **The sharding key decides how your data gets distributed across various DB servers.**
> - ⭐ **It will also determine how the queries need to be routed to fetch the data.**

*(Session 2: "sharding is a side effect of routing".)*

---

## 🆔 Primary Key vs Sharding Key

### Primary Key
> ⭐ **Uniquely identifies an item in the data** (e.g. a row in a table) — **what you're talking
> about.**

| Question | Answer |
|---|---|
| **Does a Primary key have to be unique across *tables*?** | ⭐ **No.** It is totally okay for there to be a `user_id = 1` and a `product_id = 1`. Both can have the value 1, **because we are querying different tables — we're talking about different entities** |
| **Does a Primary key have to be unique across *shards*, for the same table?** | ⭐ **Yes!** The primary key should be unique for each row within a table, **irrespective of whether the table is on a single server or sharded** |

**The following is WRONG:**
```
Shard 1 has  user_id = 1,  name = Sai
Shard 2 has  user_id = 1,  name = Abhishek      ❌
```

### Sharding Key
> ⭐ **Just tells you how to distribute the data: what data goes to what server — WHERE TO FIND THE
> DATA.**

**Example schema:**
```
users (id, name, gender)                      PK = id,  SK = id
   A, Akshay, Male
   B, Balaji, Male
   C, Chandani, Female

user_posts (id, user_id, title, content)      PK = id,  SK = user_id
   1, A, Hi, Hello World
   2, A, Bye, Going to sleep
   3, B, Wassup, What's everyone doing
   4, C, Context?, Who are you guys? Why are you in my home?

user_friendship (id, user_id, friend_id, affinity)   PK = id,  SK = user_id
   1, A, B, 100%
   2, B, A, 100%
   3, A, C, 50%
   4, C, A, 50%
```

**Sharding by `user_id` puts all of one user's data on one shard:**
```
Shard 1:                              Shard 2:                    Shard 3:
  users:            A, Akshay, Male     users:  B, Balaji, Male     users:  C, Chandani, Female
  user_posts:       1, A, Hi, …         user_posts: 3, B, …         user_posts: 4, C, …
                    2, A, Bye, …
  user_friendship:  1, A, B, 100%       user_friendship: 2, B, A    user_friendship: 4, C, A
                    3, A, C, 50%
```
> ⭐ **Suppose we're sharding by the `user_id` — then ALL tables must have `user_id`.**

| Question | Answer |
|---|---|
| **Does the Sharding key have to be unique across tables?** | **No.** *This question is weird, because all the tables are sharded in the same way* |
| **Does the Sharding key have to be unique across shards?** | ⭐ **Yes. Because if it were the same, then we wouldn't route to different shards** |

### Which should we use — Primary Key or Sharding Key?
> ⭐ **Both! Both of these keys will coexist.**
>
> - **It is common to use the same column as both the primary & sharding key** — e.g. `user_id` as
>   PK for the `users` table and also shard by `user_id`
> - **But not always.** It is totally possible to have a different PK and SK — for the `posts` table
>   the primary key is `post_id`, but the sharding key is `user_id`

**If you want to read/write some data, which key should you use? ⭐ You need to use both!**
> - ⭐ **Sharding key will tell you WHICH SERVER to go to (routing)**
> - ⭐ **Primary key will tell you WHICH ENTRY to touch inside that server**
>
> **It is possible to omit the Sharding Key** — just the PK is enough to uniquely identify a row.
> ⭐ **However, if the Sharding key is not used, then our query will be a FAN-OUT query (we will
> have to hit all shards).**

### 🏫 The school analogy ⭐
> **Suppose you're going to school to find your little sister:**
> - **Primary Key:** your sister's **name & her student id**
> - **Sharding Key:** the **class number**
>
> - **To find your sister, you MUST know the primary key**
> - ⭐ **If you also know the Sharding key, then your search will be faster, because you will know
>   exactly which classroom (server) to go to**
> - ⭐ **If you don't know the sharding key, then you will have to fan-out and search through all
>   classrooms (servers)**

---

## 📋 Rules About Sharding Keys

| Question | Answer |
|---|---|
| **Can we have more than 1 sharding key in the same database?** | ⭐ **No.** The sharding key **can be composite** (have multiple columns), **but it MUST be the same group of columns across the entire database.** ⭐ **If you need different sharding keys, you need different databases** |
| **If there are multiple tables in the DB, must ALL these tables have this sharding key column?** | ⭐ **Yes.** |
| **What if some data doesn't need to be split, or is required across all shards?** | Either: **(1) Replicate it across all shards** — if a table is very small you can omit the sharding key, but then this table will be **replicated across ALL shards**. ⭐ **You MUST make sure that the table doesn't get modified frequently.** **(2)** You can have a **separate database** for it |
| **Can a sharding key be composite?** | ⭐ **Yes. Totally allowed.** For example `(class-number, gender)` as sharding key, like in a non-co-ed school |
| **Is it possible to change the sharding key later?** | ⭐ **Yes, possible. But NOT recommended!** Changing the sharding key would require **complete re-shuffling of the data across all the servers** — **very very expensive, and will most likely require database downtime.** ⭐⭐ **This is why it is very important to choose a good sharding key upfront when you're designing the architecture** |
| **What if some row has the sharding key value set to null?** | **Bad idea.** Still, **the LB won't care — it will just treat "null" as any other value. So all rows which have `sharding_key = null` will end up in the SAME shard** *(a guaranteed hot shard)* |

---

## ✅ What Constitutes a "Good" Sharding Key

### The mental model ⭐
> Suppose you're sharding by column **SK**. Consider 2 rows, **R1** and **R2**:
> - **If `R1.SK == R2.SK`** → ⭐ **these two rows will end up in the SAME shard (guaranteed)**
> - **If `R1.SK ≠ R2.SK`** → **they will MOST LIKELY end up in different shards** (at least, we
>   should assume so). **They *can* end up in the same shard** (because 1 shard holds multiple
>   sharding keys, based on consistent hashing)

### Property 1 — Equal data & load distribution
> ⭐ **All key values should be equally likely.** If some values are more likely than others, that
> will lead to **"hot shards"** (a shard that is overwhelmed with data/requests).

| Candidate | Verdict |
|---|---|
| **Age** | ⭐ **Bad.** Ages 0–5 are less likely. Ages 50+ are less likely. **Ages 15–30 are most likely.** There will be no users above age 100 → **poor load distribution** |
| **Gender** | ⭐ **Bad** — depending on the application you can have hot shards. *Most of the students @ Scaler are male (because there's gender disparity in higher technical studies)* |
| **User id** | ⭐ **Good.** Of course some users make many posts and some make 0 posts. **But since each server has 100,000s of users, overall the data distribution across the servers will be pretty even** — the normal users & the influencers will get distributed more or less equally |

> ⭐ **Note: this is not always true — e.g. the "celebrity problem", especially for notification
> systems.**

> **Q: If we're sharding by `user_id`, does each user get a dedicated server? If we have 2 billion
> users, do we need 2 billion servers?**
> ⭐ **No. A single server will house multiple users** (because multiple values of the key can hash
> to the same server). **If Post_13 is by User_1 and Post_20 is by User_2, then most likely these
> posts will end up in different servers.**

### Property 2 — High Cardinality
> ⭐ **Cardinality = count of the set of possible values.**

| Candidate | Cardinality | Consequence |
|---|---|---|
| **Age** | `{0..123}` → **124 possibilities max** | ⭐ **If we have 125 servers, then 1 server will not get any value. We're limited to max 124 servers — we cannot scale any further** |
| **Gender** | `{Male, Female, LGBTQ+}` → **3 possibilities** | ⭐ **If you have 4 servers, 1 server will be idle. Max scaling possible is only 3 servers. Even if you have 1 billion users, you will be forced to somehow fit them into 3 shards** |
| **User_Id** | 64-bit value → **16 quintillion possibilities** | ⭐ **There's no limit to the number of servers we can scale to. 10 million servers? No issue** |

> ⭐⭐ **Cardinality of the sharding key doesn't define how many servers you have. But it gives you an
> UPPER LIMIT on how many servers you can scale to in the future.**

### Property 3 — Part of every read/write request
> ⭐ **If the sharding key is not part of the request, then how will you route the request in the
> first place? You will have to go to every shard — fan-out (bad).**

**Example — sharding by gender, loading Tanisq's profile page:**
```sql
select * from user_profiles
where user_id = 1234;
```
> ⭐ **This query will fan out**, because the DB LB doesn't know which shard to hit — **it doesn't
> know the gender of Tanisq.**

```sql
select * from user_profiles
where user_id = 1234
  and gender = 'MALE';
```
> **This query will not fan out. But do you think your app server will make this query?**
> ⭐ **When the app server is trying to render the profile page, how on earth does it get the value
> for the gender column?** *(It would have to query the DB to learn the gender — the very query it's
> trying to route. Circular.)*

### Property 4 — No fan-outs
> - ⭐ **Most frequent queries should have to hit only 1 (or at most 2) shards.**
> - ⭐ **No frequent query should lead to a fan-out request.**
> - ⭐ **Note: rare queries are okay to fan-out — you cannot optimize every single query.**

### Property 5 — Immutable
> ⭐ **The value of the sharding key should not change for any row.** Because **if we change the value
> of the sharding key, then we will have to re-shuffle the data.**
>
> **Age:** ⭐ *what happens when the user's birthday comes?* We will have to **move the user to a
> different server** because the age has changed.

### The checklist 📝
```
A GOOD SHARDING KEY IS:
  1. ⭐ Evenly distributed   (no hot shards)
  2. ⭐ High cardinality     (room to scale out)
  3. ⭐ Present in every request (else you can't route)
  4. ⭐ Fan-out free for frequent queries
  5. ⭐ Immutable            (never changes for a row)
```

---

## 🏦 Worked Example 1 — Banking System

> **Users can have active bank accounts across cities.**
>
> **Most frequent operations:**
> - **Balance Query** `(user_id, account_id)`
> - **Fetch Transaction History** `(user_id, account_id, date_range)`
> - **Fetch list of accounts of a user** `(user_id)`
> - **Create new transactions** `(sender_id, receiver_id, amount)`
>   *(note: `sender_id` and `receiver_id` are both composite columns comprising `(user_id, account_id)`)*

| Candidate | Verdict |
|---|---|
| **location (city_id)** | ❌ **A user can have accounts across multiple cities** → we'd store the user's data across multiple shards. **Fetching the list of accounts of a user → fan-out.** ⭐ **Poor load distribution** (large cities have much more data than small cities). **Not part of request.** **Low cardinality** |
| **branch_id** | ❌ **Same issues as location** — branch_id is just more granular |
| ⭐ **user_id** | ✅ ⭐ **Ideal sharding key here.** 1 user's data is housed entirely within a single server *(note: 1 server still houses thousands of users)* |
| **transaction_id** | ❌ ⭐ **Is not even available for any of our queries. Transaction id is generated in the RESPONSE — it's not part of the request query.** ⭐⭐ **Any id/entity that is generated by the system (ticket / booking / transaction) cannot be used as the sharding key** |
| **account_balance** | ❌ ⭐ **Subject to change** — every time the user adds/removes money we'd have to move their data. **Not part of the request. Poor load distribution** |
| **timestamp** | ❌ ⭐⭐ **NEVER choose timestamp.** **Unequal load distribution** (recent days are hot, future days have 0 data) · **subject to change** (`updated_at` can be changed) · **not part of the request** |
| **account_id** | ⚠️ ⭐ **Fine for most queries, but not for the basic user dashboard.** In the interface the user wants to see **the list of accounts they have** — if we shard by `account_id`, **different accounts of the same user might go to different servers**, so the dashboard request becomes a **fan-out** |

### Verifying `user_id`
| Operation | Shards hit |
|---|---|
| **Balance enquiry** `(user_id, account_id)` | ⭐ **only 1 shard** (the user's shard) |
| **Transaction history** | ⭐ **only 1 shard** (all the user's transactions will be there) |
| **List of accounts of the user** | ⭐ **only 1 shard** |
| **Transaction** | ⭐ **This transaction is data about both the sender and the receiver → each transaction has to be stored in 2 shards** (sender's + receiver's). ⭐ **This is NOT a fan-out. Hitting 2 shards is okay.** **This is still difficult, because you will need to do this atomically (2 Phase Commit) — it will have high latency and low availability** |

> **Q: Isn't the `user_id` also generated by the system?**
> ⭐ **Yes, but only ONCE, when the user registers. For any subsequent request made by the user, the
> `user_id` is available at the client side, and the client will send this user id along with every
> request (via cookie or auth-token).**

---

## 🚆 Worked Example 2 — IRCTC

> **Requirements:**
> - ⭐ **Prevent double booking of seats** (at least for confirmed, non-RAC tickets)
> - ⭐ **Handle peak load during the Tatkal window (20× or more than the average load)**
>
> ```
> book_ticket(user_id, train_id, date_of_journey, class, seat_preference, meal_preference, ...)
>     => ticket: {id, details}
> ```

| Candidate | Verdict |
|---|---|
| **Ticket ID** | ❌ **Not part of the request — it is generated in the response** |
| **Date of travel** | ❌ ⭐ **Timestamp — so big no-no.** *Interesting note: **any data for past dates is now immutable.** You cannot book a ticket for a journey that has already happened, nor modify (cancel, add lunch services) a ticket whose journey has completed* |
| **User ID** | ❌ ⭐ **Users are distributed across the shards.** Suppose Ashok is trying to book in Rajdhani for 15 Feb. Sanjana has booked, Rohit has booked. **If we shard by `user_id`, Sanjana's ticket is in her shard and Rohit's in his.** ⭐ **To ensure Ashok doesn't get a duplicate seat, we have to hit both — in fact we need to hit ALL the shards, because we don't know which users have booked which tickets → FAN-OUT** |
| ⭐ **Train ID** | ✅ ⭐ **If we shard by `train_id`, then tickets of 1 train are stored completely within a single shard.** Sanjana & Rohit travelling in Rajdhani on 15 Feb → **both tickets in the same shard** *(note: not the user data, just the ticket data)*. Vijay travelling in Shatabdi → **can their seats collide? No, the trains are different!** ⭐ **So when checking for duplicates, we only need to check the tickets for this train — just 1 shard.** **IRCTC facilitates ~13k passenger trains ⇒ cardinality is decent** |

### Handling the "but a user books many trains" objection ⭐
> **Q: But a single user can also book tickets in multiple trains — how will we store the user data
> then? Will that be split across servers?**
>
> ⭐ **Note that user data can be sharded by `user_id`** (user dashboard service), **and for booking
> tickets, the ticket data can be sharded by `train_id`** (booking microservice).
>
> ⭐⭐ **Each ticket will be stored in 2 databases — the tickets DB (sharded by `train_id`), and the
> user's DB (sharded by `user_id`).**

> 🧠 **This is the resolution of the "only one sharding key per database" rule.** You don't compromise
> the key — **you use two databases (i.e. two microservices), each sharded for its own access
> pattern.** Store the data twice. Same denormalisation instinct as the leaderboard cache.

> **Q: Suppose we wish to find all the journeys happening on a given day?**
> - ⭐ **That will be a fan-out. But note that this is NOT a frequent query!**
> - **If it were a frequent query, then we would come up with another solution** — ⭐ **another
>   solution does NOT mean that we change the sharding key.** We can't change it, because `train_id`
>   is the ideal sharding key for preventing double-booking
> - ⭐ **We can have another database that is sharded by date that provides this data to us
>   (IRCTC actually does this!)**

---

## 💬 Worked Example 3 — Facebook Messenger

> **Requirements:** Send & Receive **1-1** messages
> ```
> sendMessage(sender_id, recipient_id, message)  → Ack/Failure
> viewMessages(user_id, other_person_id)         → List of messages
> ```

| Candidate | Verdict |
|---|---|
| ⭐ **User ID** | ✅ **This means that all messages that are (both) sent and received by Sanjana will be in 1 shard.** ⭐ **If Sanjana wants to view the conversation history between herself and Sachin, her requests only have to go to her shard** — her shard will contain all messages she has sent to Sachin **and** all messages Sachin has sent to her. **Sanjana ⇒ Sachin: this message must be stored in BOTH Sanjana's shard & Sachin's shard. Not a fan-out** |
| **Message ID / Message Digest** | ❌ ⭐ **It is created in the response** — once the message has been sent (it's not part of the request). *What if we generate the message id on the client side? Then it can be part of the request* — **but sharding by message id would mean the messages are distributed across servers; any message can go to any server (based on the hash of message id).** ⭐ **If I want to find all messages that Sanjana sent to Sachin, I will have to go to all shards — a fan-out** |

---

## 🗣️ Worked Example 4 — Slack

> **Requirements:**
> - **Send & Receive messages in groups** — ⭐ **a group can have up to 100,000 participants**
> - **Send & Receive 1-1 messages**

### Candidate: User ID ❌
> **Consider an "Announcements" group that has 100,000 participants. Sanjana sends "Hi" in that
> group.** If we shard by `user_id`, we can design in 2 ways:

| Design | Writes | Reads |
|---|---|---|
| **"Hi" stored only in Sanjana's (sender) shard** — when any participant (Tarun) wants to view the conversation, they **must hit all shards** (because anyone could've sent a message in that group) | ⭐ **1 shard** | ⭐ **100,000 shards** 💥 |
| **"Hi" stored in both Sanjana's shard & the receiver's shard** — there are **100,000 receivers**, so the message has to be written to all those shards | ⭐ **100,000 shards** 💥 | ⭐ **1 shard** |

> ⭐ **Both are catastrophic — you just get to choose whether the disaster is on reads or writes.**
> *(This read-fanout vs write-fanout dilemma is exactly the **newsfeed fan-out problem** — Session 6.)*

### Candidate: Group ID ✅
> ⭐ **All messages that are sent & received within any group ("Announcements" for example) will be in
> a single shard.**
>
> **Sanjana ⇒ "Hi" ⇒ Announcements:**
> - ⭐ **Write: only 1 shard** (the shard where all messages of the Announcements group are stored)
> - ⭐ **Read: only 1 shard**

### Q: Slack has both 1-1 messages and group conversations. So what's the final sharding key?
> ⭐ **2 possible approaches:**
>
> **1. Two separate databases**
> - **Group conversation database** — sharded by **group id**
> - **1-1 conversation database** — sharded by **user id**
>
> **2. Treat 1-1 conversations as "ad-hoc" groups of 2 participants** ⭐
> - *"Sanjana => Hi => Tarun"* is treated as a message in the group `(sanjana_id, tarun_id)` — or
>   `conversation_id` (if the conversation involves 2+ people)

> 🧠 **Approach 2 is the elegant one** — it collapses two problems into one by redefining a DM as a
> 2-person channel. One sharding key (`conversation_id`), one code path. *(This is what Slack, and
> most modern chat systems, actually do.)*

---

## 💿 How Storage Works — Sequential vs Random Access

### The HDD arithmetic
> **The HDD might be spinning at 7200 RPM. How much time will it take to complete 1 spin?**
```
7200 rpm ⇒ 7200/60 rps ⇒ 120 rps
time to complete 1 rotation ⇒ 1/120 s = 8 ms
```
> **How much time does it take to move the spindle (read head)?** ⭐ **~10 ms**

### Reading 100 MB of **sequential** data (an entire track)
```
10 ms  to move the spindle to the correct track
 8 ms  to spin the disk once
─────
18 ms  total

bandwidth = 100 MB / 18 ms = 100 MB / 0.018 s = 5.5 Gbps    ⭐
```

### Reading 4 KB of **random** data
> **Why 4 KB?** ⭐ **Because your disk is NOT byte addressable. Whenever you read/write, you always
> do it in chunks of 4 KB.**
```
Because random data will be on some different track:
10 ms  to move the spindle to the correct track
 8 ms  to spin the disk once
─────
18 ms  total

bandwidth = 4 KB / 18 ms = 222 kbps    ⭐
```

### The conclusion ⭐⭐
```
        5.5 Gbps  (sequential)
        ───────────────────────  ≈  25,000×
        222 kbps  (random)
```
> ⭐⭐ **Sequential access is up to 10,000× faster than random access!**
> ⭐ **True irrespective of the storage technology (HDD, SSD, RAM, L3 cache, Brain).**

> 🧠 **This single fact is the entire foundation of the next two sessions.** A B-tree does **random**
> writes; an **LSM tree** turns every write into a **sequential append**. That's the whole trick —
> and it's why the Cassandra paper says *"Cassandra morphs all writes to disk into sequential
> writes"*.

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **SQL** | ⭐ A **query language**, not a DB type; when people say SQL they mean **Relational DB** |
| **Low scale** | Queries/sec and data fit on **a single server** |
| **Large scale** | Data or req/s **too large for one server** |
| **Normalization** | Prevents anomalies & reduces redundancy — but forces **joins** |
| **Strong schema** | Well defined, **static** (migrations are slow & need downtime), **enforced** |
| **ACID** | Atomicity · Consistency · Isolation · Durability |
| **Atomicity** | All or nothing; no partial states |
| ⭐ **ACID Consistency** | **Constraints are enforced** (schema, not-null, unique, FK, triggers) |
| ⭐ **CAP Consistency** | **No stale reads** across copies — *a totally different thing* |
| **Isolation** | Concurrent transactions don't interfere; **read up on isolation levels** 📝 |
| **Durability** | Survives power loss; ⭐ **does NOT survive HDD failure — only replication does** |
| **EAV / attribute list** | `(entity, attribute, value)` modelling — ⭐ **loses schema enforcement** |
| ⭐ **Sharding nullifies ACID** | Distributed locks, no shared memory, unknown write status, frequent failures |
| **NoSQL** | ⭐ **"Not Only SQL"** — augment relational DBs, don't replace them |
| **First NoSQL DB** | ⭐ **Google BigTable**; popular only after **2005**; `#NoSQL` hashtag ~2009/10 |
| **BASE** | **Ba**sically Available · **S**oft state · **E**ventually consistent |
| **Soft state** | Transactions may sit **partially applied** for a long time (→ **Saga Pattern**) |
| **SQL vs NoSQL** | ⭐ **Jack of all trades (1 server)** vs **Master of one (many servers)** |
| **Row-size rule** | ⭐ Rows > **10 KB** ⇒ probably the wrong choice for SQL |
| **Primary Key** | Uniquely identifies a row — ⭐ **which entry** |
| **Sharding Key** | ⭐ **Which server** — determines data distribution *and* routing |
| **Fan-out query** | A query that must hit **all** shards (no sharding key available) |
| **Hot shard** | A shard overwhelmed with data/requests due to skewed key values |
| **Cardinality** | Number of possible key values — ⭐ **caps how far you can scale out** |
| **Good sharding key** | ⭐ Even · high cardinality · in every request · fan-out free · **immutable** |
| **Never shard by** | ⭐ **timestamp**, system-generated ids (ticket/booking/transaction), mutable values, low-cardinality fields |
| **Sequential vs random** | ⭐⭐ **Sequential is up to 10,000× faster** — true for every storage medium |

---

## 🎯 Session Takeaways

1. **SQL is a query language; "SQL database" means relational.** All its strengths are **low-scale**
   strengths.
2. ⭐ **ACID Consistency (constraints) ≠ CAP Consistency (no stale reads).** Know both cold.
3. ⭐⭐ **At large scale, every RDBMS strength inverts:** normalization ⇒ cross-server joins;
   strong schema ⇒ can't model 10,000 product categories; **ACID ⇒ nullified by sharding.**
4. **The Amazon catalogue has no good SQL answer** — one giant table wastes 99.99% of disk on nulls,
   10,000 tables can't be joined, and EAV throws away schema enforcement.
5. **SQL handles lots of *rows*, not lots of *schema*.** Terabytes across few tables is fine;
   10,000 tables is not.
6. ⭐ **NoSQL = "Not Only SQL".** Default to relational; **99% of companies don't need NoSQL**, and
   a SQL DB serves a **1 million** userbase flawlessly.
7. ⭐ **SQL generalises (jack of all trades); NoSQL specialises (master of one).** NoSQL scales
   *because* it drops features — and it **auto-shards**, which SQL does not.
8. ⭐ **PK tells you which row; SK tells you which server.** You need both — omit the SK and you get
   a **fan-out**.
9. ⭐ **One sharding key per database**, it must be in **every table**, and **changing it later means
   reshuffling everything**. Choose it upfront.
10. ⭐ **Five properties of a good key:** even distribution · high cardinality · present in every
    request · no fan-out on frequent queries · **immutable**.
11. ⭐ **Never shard by timestamp**, nor by anything the *system generates in the response*
    (ticket/transaction ids), nor by anything mutable (age, balance).
12. ⭐ **When two access patterns need different keys, use two databases** — IRCTC shards tickets by
    `train_id` and users by `user_id`, storing each ticket twice.
13. ⭐ **Slack's answer: shard by `conversation_id`,** treating a DM as an ad-hoc 2-person group —
    otherwise you fan out 100,000× on either reads or writes.
14. ⭐⭐ **Sequential access is up to 10,000× faster than random access** — the fact that makes the
    **LSM tree** (next session) possible.

---

## ➡️ Next
**[Session 10 — NoSQL Internals: LSM Tree](./10_NoSQL_Internals_LSM_Tree.md)**
