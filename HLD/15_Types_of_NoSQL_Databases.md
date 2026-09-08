# Session 15 — Types of NoSQL Databases 🗂️

> **Topics:** Key-Value · Document · Column Family / Wide Column · Large File / Object ·
> Graph · Vector · Choosing the right database
>
> 📄 Class doc: [\[SST-2028\] Types of NoSQL Databases](https://docs.google.com/document/d/1cZ3HRQwR9r7fLboa6kSS6nXxKoVLmq0xrfeCSXFCMjA/edit?usp=sharing)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [The Specialisation Principle](#-the-specialisation-principle)
2. [Key-Value](#1️⃣-key-value)
3. [Document](#2️⃣-document)
4. [Addressability](#-addressability--why-size-limits-exist)
5. [Column Family / Wide Column](#3️⃣-column-family--wide-column)
6. [Large File / Object](#4️⃣-large-file--object)
7. [Others: Graph, Vector, OO](#5️⃣-others)
8. [Summary Table](#-the-summary-table)
9. [Choosing the Right Database — Twitter Hashtag](#-choosing-the-right-database--twitter-hashtag)
10. [Key Terms Recap](#-key-terms-recap)

---

## 🎯 The Specialisation Principle

> ⭐ **Different types of NoSQL databases SPECIALIZE for specific features & use-cases.**
>
> ⚠️ **Be careful about the features you see being claimed by popular NoSQL databases.**

*(Session 9: **"NoSQL databases specialize — jack of 1 trade, and master of it."** This session is the
catalogue of those trades. And the warning matters because vendors advertise features that exist but
**don't scale** — the exact criticism levelled at SQL.)*

---

## 1️⃣ Key-Value

> ⭐ **The simplest type of NoSQL database. Think of it as just a giant hashmap distributed across
> servers.**

**Examples:**
| Database | Note |
|---|---|
| **Redis** | **in-memory + optional disk persistence** |
| **Memcached** | **in-memory** |
| **DynamoDB** | **disk persistence** |

### How data is stored
> - **Keys & Values (hashmap)**
> - ⭐ **Both the key & the value are just plain strings** — *the database doesn't know & doesn't care
>   about what is contained inside those*
> - ⭐ **Violated by most modern key-value stores.** **Redis:** Key ⇒ string, but **Value ⇒ Redis
>   supports multiple data structures** (arrays, JSON, sets, **sorted sets**, **bloom filter**, custom
>   data structures)

| Key (string) | Value (string) |
|---|---|
| `"contest:13:page:10"` | `"{ ["rank" 130, "..."], [...], [...] }"` |
| `"contest:13:winner"` | `1361` |

### Strengths
> - ⭐ **Extremely simple**
> - ⭐ **Because they're typically in-memory (RAM), they're ridiculously fast!**
>   **A single Redis server can handle 100,000+ reads & writes per second!**
>   ⭐ **Compared to a SQL server which can only handle 100 writes/sec and 1000 reads/sec.** A well
>   optimized Postgres server can probably handle a few thousand reads/writes per second

### Queries
```
get(key)         ⇒ value
set(key, value)  ⇒ ack/failure
delete(key)      ⇒ ack/failure
```

### ⭐ The race condition — why `inc` exists
> **Imagine that you're storing a counter inside the key-value db. How will you increment it?**
> **In your application code:**
```python
value = key_value_db.get(key)
value += 1
key_value_db.set(value)
```
> ⭐⭐ **If you increment the counter in this manner, it will lead to a RACE CONDITION.**
>
> **Modern databases like Redis allow you to do much more than these 3 simple operations.**
> ⭐ **Typically increment == Get + Set. But Redis allows you to do this in a single `inc`
> operation.**

> 💡 *(This is the same lost-update problem as the ACID **Isolation** example in Session 9 — two
> readers see the same value and one increment vanishes. An **atomic `inc`** is the fix.)*

### Weaknesses
> - **No complex queries (joins / filtering)**
> - **No search**
> - **No indexing**
> - **No relations**

### Keys
> - ⭐ **Sharding Key = Key** — **automatically sharded by `hash(key)`**
> - ⭐ **Primary Key = Key**

### When to use
> - ⭐ **Cache** (global, single or distributed)
> - ⭐ **Storing very simple data (key-value) that needs to be queried extremely frequently** — user
>   preferences, rules, **rate-limiter bucket counts**, **view counts**

### ⚠️ Sizing rules
> **In Redis any string has a limitation of max 500 MB.**
>
> **Q: Does this mean that storing 500 MB of data per entry is a good idea?**
> ⭐ **Absolutely NO!**
>
> ⭐⭐ **To use a key-value database: your keys ≲ 100 bytes, values ≲ 10 KB**
> - **If your keys are longer than 100 bytes, then perhaps you should look at some other database**
> - **If your value is > 10 KB, then you probably need to dive deeper into the value — key-value is
>   probably a poor choice**

### 📖 Redis
**Mandatory Reading for SDE2+**
- Try online: https://onecompiler.com/redis
- Quick start: https://redis.io/learn/howtos/quick-start
- [Eviction policies & Cluster mode](https://docs.google.com/document/d/1k4nzubvtX_yLctUT4VWK8ZJt4KCcOEdRJdxQgWCaiU8/)

**Optional Reading:** [Tutorial](https://redis.io/university/) · [Docs](https://redis.io/docs/latest/)

---

## 2️⃣ Document

> ⭐ **Storing unstructured / semi-structured data. Think of this as a collection of JSON/JSONB files
> distributed across multiple servers.**
>
> ⭐⭐ **A single document will NEVER be sharded — a single document is always stored completely
> within a single server (+ replicated across multiple servers).**

**Examples:** **MongoDB, ElasticSearch, Couchbase, …**

### How data is stored
```javascript
{
    _id:   uuidv4
    product_id: int
    name: string
    type: string            // (t-shirt)
    brand: string
    color: string

    neck_type: byte
    sleeve_length: byte
    image_url: string
}

{
    _id:   uuidv4
    product_id: int
    name: string
    type: string            // (laptop)
    brand: string
    color: string

    ram: {
        size: integer
        technology: string      // (ddr4/ddr5/..)
        cas_latency: string
    }
    cpu: string
    image_url: [string, string, string]
}
```
> - **Every document in MongoDB has a unique document id**
> - ⭐ **Any document can have any set of attributes**
> - ⭐ **`_id` is automatically created on the CLIENT SIDE when the document is being inserted**

*(This is the **direct answer to the Amazon product catalogue problem** from Session 9 — 10,000
categories, each with different attributes, and no nulls wasted.)*

### Strengths
> - ⭐ **Can store semi-structured / unstructured data**
>   - ⭐ **Schema must be enforced by the developer at the app-server level. The database will NOT
>     enforce any schema**
> - ⭐ **Powerful query & search capabilities via indexes (B+ trees)**
>   - **You can put an index on any TOP LEVEL attribute (not-nested)**
> - ⭐ **Provides full-text-search**

### ⚠️ The critical caveat — no global indexes ⭐⭐
> ⭐ **Caution: indexes are maintained LOCALLY — there's no GLOBAL index.**
>
> **Example:** suppose we have Amazon's product listing, and we have an index on the attribute
> `brand`:
> - ⭐ **`mongoClient.find({brand: "dell"})` will be a FAN-OUT read!** This query will go to **every
>   shard (broadcast query)** and then **within each shard**, the shard will use the index on `brand`
>   to return the relevant documents
> - ⭐ **`mongoClient.find({brand: "dell", type: "laptop"})` will NOT be fan-out** — assuming that it
>   is sharded by either the `brand` or the `type`

```
   ⭐ A local index makes the search fast WITHIN a shard.
      It does nothing to tell you WHICH shard to look in.
      → Without the sharding key in your query, you still broadcast.
```

### Queries
```javascript
mongoClient.find( {_id: "..."} )      // fetch the document with the given document_id
mongoClient.find( {brand: "dell"} )   // fetch documents where brand == "dell"
                                      // ⭐ if there's an index on the column it uses it,
                                      //    otherwise it searches through ALL documents
```

### Keys
> - ⭐ **Primary Key = `_id`**
> - ⭐ **Sharding Key:** the **default** (if nothing else is configured) is **`_id`**. **But any
>   top-level attribute (or composite of top-level attributes) can be configured as the sharding key**
>   - *For example, for the Amazon products listing we could set the sharding key as `product_type`
>     (laptop/tshirt/…)*

### Weaknesses
> - **No relations & joins**
> - ⭐ **No global indexes**
> - **(typically) no ACID transactions**
>   - ⭐ **MongoDB provides ACID transactions, even across shards** — **caution: ACID *within* the same
>     shard is fast, but ACID *across* shards is extremely slow**

### When to use
> - ⭐ **Unstructured / Semi-structured data**
> - ⭐ **Full-text search**
> - *Examples:* **Amazon product listing / social media posts / user notes / LinkedIn job posting /
>   user reviews / …**

### ⚠️ Size limit
> ⭐ **Documents should be ≲ 10 MB.** **MongoDB has a cap of 16 MB for their documents.**

### 📖 MongoDB
- Try online: https://mongoplayground.net/
- Tutorial: https://www.mongodb.com/docs/manual/tutorial/getting-started/
- Docs: https://www.mongodb.com/docs/manual/

---

## 📐 Addressability — Why Size Limits Exist

> **Why such a hard limit?**
>
> ⭐⭐ **Because any read/write inside a document database is at the DOCUMENT LEVEL.**
> - ⭐ **If you modify even 1 character inside 1 attribute of a 16 MB document, the database will
>   COMPLETELY REWRITE this document. You cannot modify individual attributes/values inside the
>   document**
> - ⭐ **Similarly when you read the document, you cannot read just a particular attribute — the
>   database will always read the ENTIRE document from disk**

### The boolean analogy ⭐
> **What is the size of the boolean data type (doesn't matter what programming language)?**
> - **1 bit?** Because a boolean is just true/false, so it should just need 1 bit
> - ⭐ **Java / C++ / C / Rust… a boolean is 1 BYTE (8 bits) where 7 bits are completely wasted!**
> - ⭐ **Python: a boolean is 4 bytes**
>
> **Why? Are programmers stupid? Are the people who created these languages stupid?** **No.**
>
> ⭐⭐ **Your HDD / RAM / CPU Cache / Registers — any memory is "BYTE ADDRESSABLE". You can read/write
> individual bytes, but you can NEVER read/write individual bits.**

### The generalisation ⭐⭐
> **Similarly:**
> | Store | Addressable unit |
> |---|---|
> | **Key-Value** | ⭐ **key-addressable** — read/write the **entire entry** *(unless you're using special datatypes in Redis)* |
> | **SQL DB** | ⭐ **row-addressable** — read/write the **entire row** |
> | **Document DB** | ⭐ **document-addressable** — read/write the **entire document** |

> 🧠 **This one idea explains every size guideline in the session.** *"Values ≲ 10 KB"*,
> *"documents ≲ 10 MB"* — these aren't arbitrary. They're the answer to **"how much am I willing to
> rewrite to change one field?"** It also explains Session 11's 4 KB block: the disk is
> **block-addressable**.

---

## 3️⃣ Column Family / Wide Column

> ⭐ **Wide-Column, Column Family, Columnar… all of these are the same thing.**
> ⭐ **Timeseries databases are just a subset (special type) of Wide-column databases.**

> - **The data is still TABULAR in format (just like relational databases)**
> - **However:**
>   - ⭐ **Data is stored in WIDE-COLUMN format (as opposed to row-wise of SQL)** ⇒ ⭐ **very fast
>     aggregate queries**
>   - **No joins** — **data is tabular, but no relations between tables**

**Examples:** **Cassandra (popular), BigTable (⭐ the first NoSQL db ever), ScyllaDB, HBase, …**

### How data is stored
> ⭐ **Every column family database models data in a very different manner!** **The common thing is
> that all of them store the data in tables, and these tables are "partitioned" (sharded) across the
> servers.**

```
   ROW-WISE (SQL)                        COLUMN-WISE (wide column)
   ──────────────                        ─────────────────────────
   [id1, name1, age1]                    [id1, id2, id3, …]
   [id2, name2, age2]                    [name1, name2, name3, …]
   [id3, name3, age3]                    [age1, age2, age3, …]

   "give me row 2"  → 1 read             "average of all ages" → ⭐ read ONE contiguous run
   "average of all ages" → read          "give me row 2" → touch every column
       every row, discard most
```

### Strengths
> - ⭐ **Highly performant for ANALYTICS** (aggregate queries that span a **few columns but many
>   rows**)
> - ⭐⭐ **Provide easy PAGINATION (time based)**
> - ⭐ **Extremely fast WRITES!** — **not as fast as key-value, but still much faster than others.**
>   ⭐ **Writes are fast because they use LSM TREES, and because they try to make the writes
>   SEQUENTIAL**

*(Sessions 9–11 in one bullet: sequential > random ⇒ LSM tree ⇒ fast writes.)*

### Weaknesses
> **(same as previous — no joins, no relations, no search, no indexes…)**

### When to use
> - ⭐ **Analytics**
> - ⭐ **High write throughput** — **sensor data (GPS coordinates / IoT sensor data / …)**
> - ⭐ **Paginated queries / time based queries** — *fetch the location history of a user in the last
>   month*

### 📖 Cassandra (Optional)
1. Try online: https://jbcodeforce.github.io/db-play/
2. Introduction: https://cassandra.apache.org/_/cassandra-basics.html
3. Case Studies: https://cassandra.apache.org/_/case-studies.html
4. [Architecture — Overview](https://cassandra.apache.org/doc/stable/cassandra/architecture/overview.html)
5. [Architecture — Guarantees](https://cassandra.apache.org/doc/stable/cassandra/architecture/guarantees.html)
6. Data Modeling: Introduction — Apache Cassandra Documentation

---

## 4️⃣ Large File / Object

**Examples:** **S3 · Google Cloud Storage · Git Large File Storage (Git LFS) · Hadoop Distributed
File System (HDFS)**

### How data is stored
> ⭐ **Flat files directly on the disk (files are chunked & distributed across servers).**
> ⭐ **The same file CAN be split across multiple servers.**

*(Contrast with a **document** DB, where a single document is **never** split.)*

### Strengths
> - ⭐ **These files can be extremely large (100 TB file — for example, log files)**
> - ⭐ **Can STREAM the data**

### Weaknesses
> - **No search**
> - **No relations**
> - ⭐ **Difficult to modify files (can append, can replace, but NOT modify)**
> - ⭐ **Reads & writes are slow**

### When to use
> - ⭐ **Any sort of user-generated multimedia** (pdf, images, videos, audios, csv, zip, …)
> - **HTML/CSS/JS** (if they're static, and client side)
> - ⭐ **Any large files (> 10 KB) that are mostly static**

*(Session 3: **"Any data that you add to a CDN must be backed by a file storage service like S3."**
Session 5: the Code Judge's 1 GB testcase files lived in S3.)*

---

## 5️⃣ Others

### Graph
> - 😄 **Famous, because people have a weird attraction to graphs. ⭐ But RARE in practice!**
> - **Facebook friendship / LinkedIn follower / Twitter follower ⇒ social connection graphs**
> - ⭐⭐ **NONE of these companies stores the relationships in a graph DB — all of them use SQL to
>   store the relations. They use a graphDB for the SEARCH queries (as a CACHE) in front of the SQL
>   db**
> - ⭐ **Good when your queries require "PATH-FINDING":**
>   - **Recommender systems** (Amazon / Netflix)
>   - **Shortest route between two places** (Uber / Google Maps)

### Vector
> - ⭐ **More popular due to AI**
> - ⭐ **Provide fast K-Nearest Neighbor (KNN) queries — extremely useful for searching over an
>   EMBEDDING SPACE**

### Object Oriented
> - **Table inheritance (Postgres)**

> 😄 **…every kid and their grandmother have their own NoSQL database type.**

### Multimodal ⭐
> ⭐ **All modern databases are multi-modal — they provide multiple features.**

*(Which loops back to the warning at the top: **a feature existing ≠ that feature scaling.**)*

---

## 📊 The Summary Table

| Type | Examples | Stores | Strengths | Weaknesses | Sharding key | Size guidance | Use when |
|---|---|---|---|---|---|---|---|
| ⭐ **Key-Value** | Redis, Memcached, DynamoDB | Hashmap of strings | **Simplest**, **100,000+ ops/sec**, in-memory | No joins/search/indexing/relations, ⭐ **no pagination** | ⭐ **the key** (auto `hash(key)`) | ⭐ **keys ≲100 B, values ≲10 KB** | **Cache**; tiny data queried very frequently (preferences, rate limits, view counts) |
| ⭐ **Document** | MongoDB, ElasticSearch, Couchbase | JSON documents | **Semi/unstructured data**, **indexes on top-level attributes**, ⭐ **full-text search** | No joins, ⭐ **no GLOBAL indexes**, ⭐ **no pagination**, typically no ACID | `_id` by default; any top-level attribute | ⭐ **≲10 MB** (Mongo caps at 16 MB) | Product listings, posts, reviews, job postings |
| ⭐ **Wide Column** | Cassandra, BigTable, ScyllaDB, HBase | Tabular, column-wise | ⭐ **Fast writes (LSM)**, ⭐ **time-based pagination**, **fast aggregates** | No joins/search/indexes/relations | per-DB (partition key) | — | ⭐ **Analytics, high write throughput, time-series, paginated queries** |
| **Object / Large File** | S3, GCS, Git LFS, HDFS | Chunked flat files | ⭐ **Huge files (100 TB)**, **streaming** | No search/relations, ⭐ **can't modify (only append/replace)**, slow | — | ⭐ **>10 KB, mostly static** | User multimedia, static assets, logs |
| **Graph** | Neo4j, … | Nodes & edges | ⭐ **Path-finding** | ⭐ **Rare in practice** | — | — | Recommenders, routing — ⭐ *usually as a cache in front of SQL* |
| **Vector** | Pinecone, Milvus, … | Embeddings | ⭐ **Fast KNN** | — | — | — | AI / semantic search |

> ⭐⭐ **The two properties that decide most real designs: does it support PAGINATION, and how fast are
> its WRITES?** That's exactly what selected the wide-column DB in Session 14.

---

## 🐦 Choosing the Right Database — Twitter Hashtag

### Requirements
> - ⭐ **Store the most popular & most recent tweets for each hashtag**
> - ⭐ **Paginated queries** (first 20 tweets, next 20 tweets, …)
> - ⭐ **Very large volume of tweet writes**

### ❌ SQL
> ⭐ **Scale is too large!** For popular hashtags like `#US-Elections-2025`, `#Diwali`, … **a single
> server won't be able to store all the tweets (even for 1 hashtag).**

### ❌ Key-Value
> - **Key?** `"#Diwali2025 : popular"` or `"#Diwali2025 : recent"`
> - **Value?** all the top-100 popular/recent tweets for the hashtag, or all the tweets for the
>   hashtag
>
> **Problems:**
> - ⭐ **Value is way too large** (`#Diwali` will have 100 millions of tweets ⇒ **multiple GBs of
>   data**) — *far beyond the ≲10 KB guideline*
> - ⭐ **Pagination will not be possible**
> - ⭐ **Inserting a tweet will require RE-WRITING the "recent" key's value, which will be costly**
>   *(key-addressable!)*

### ❌ Document DB
> ⭐ **Same reasons as key-value.**

**Option A — one document per hashtag:**
```javascript
{
    __doc_id: …,
    hashtag: "Diwali 2025",
    tweets: [
          {user_id: …, …},
          {user_id: …, …},
          {user_id: …, …},
    ]
}
```
⭐ *The document grows to GBs, blows past the 16 MB cap, and every new tweet rewrites the whole
document.*

**Option B — one document per tweet:**
```javascript
{
    __doc_id:  /* == tweet_id */,
    hashtag: "Diwali 2025",
    content: "Celebrating crackerless pollution less diwali <3",
    author_id: "Krishna",
    likeCount: 1234,
    viewCount: 12322
}
```
⭐ *Solves the size problem, but you still can't paginate, and querying by hashtag would be a
**fan-out** unless sharded by hashtag.*

### ✅ Column Family
> ⭐ **HBase, for example.**
> ⭐⭐ **All our requirements match EXACTLY with the strengths of Column Family DBs:**

| Requirement | Wide-column strength |
|---|---|
| **Very large volume of tweet writes** | ⭐ **Extremely fast writes (LSM trees, sequential)** |
| **Paginated queries** | ⭐ **Easy time-based pagination** |
| **Most popular & most recent per hashtag** | ⭐ **Fast aggregate queries; partition by hashtag, sort by time** |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Specialisation** | ⭐ Each NoSQL type is **master of one trade** — and vendors overclaim |
| **Key-Value** | ⭐ Distributed hashmap; **100,000+ ops/sec**; keys ≲100 B, values ≲10 KB |
| **Atomic `inc`** | ⭐ Avoids the **race condition** of get→+1→set |
| **Document DB** | ⭐ Collection of JSON docs; **a document is never sharded**; ≲10 MB (Mongo caps 16 MB) |
| ⭐ **No global index** | ⭐⭐ Document indexes are **per-shard** — querying without the sharding key still **fans out** |
| **Schema enforcement** | ⭐ In document DBs it's the **developer's** job at the app layer |
| ⭐ **Addressability** | ⭐⭐ KV = **key**-addressable · SQL = **row**-addressable · Document = **document**-addressable · memory = **byte**-addressable |
| **Why booleans are 1 byte** | ⭐ Memory is byte-addressable — you cannot read/write a single bit |
| **Wide column** | ⭐ Tabular but stored **column-wise**; fast **aggregates**, fast **writes (LSM)**, ⭐ **time-based pagination** |
| **Timeseries DB** | ⭐ A **subset** of wide-column databases |
| **BigTable** | ⭐ The **first NoSQL database ever** |
| **Object store** | S3/GCS/HDFS — chunked flat files, ⭐ **can be split across servers**, streaming, **append/replace only** |
| **Graph DB** | ⭐ Rare; good for **path-finding**; the big social networks store relations in **SQL** and use a graph DB as a **cache** |
| **Vector DB** | ⭐ Fast **KNN** over an embedding space (AI) |
| **Multimodal** | ⭐ All modern DBs offer many features — but not all of them **at scale** |

---

## 🎯 Session Takeaways

1. ⭐ **Each NoSQL type is a specialist.** Pick by matching your **access patterns** to its strengths —
   and be sceptical of advertised features.
2. ⭐ **Key-Value = a distributed hashmap.** Blazing fast (100k+ ops/sec vs SQL's ~100 writes/sec), but
   **no joins, no search, no indexes, no pagination**. Keep **keys ≲100 B and values ≲10 KB**.
3. ⭐ **Use atomic operations like `inc`** — get→increment→set is a **race condition**.
4. ⭐ **Document DBs solve the Amazon-catalogue problem** — any document can have any attributes, and
   **a document is never split across servers**.
5. ⭐⭐ **Document indexes are LOCAL, not global.** `find({brand:"dell"})` **fans out to every shard**;
   only including the sharding key avoids the broadcast.
6. ⭐⭐ **Addressability explains every size limit:** KV is key-addressable, SQL row-addressable,
   documents document-addressable. **Change one character in a 16 MB document and the whole document
   is rewritten** — just as a boolean costs a whole byte because memory is byte-addressable.
7. ⭐ **Wide column = tabular but stored column-wise** ⇒ fast aggregates, **fast writes via LSM trees**,
   and **time-based pagination**. Timeseries DBs are a subset. **BigTable was the first NoSQL DB.**
8. ⭐ **Object stores (S3/HDFS) handle 100 TB files and streaming**, but you can only **append or
   replace** — never modify.
9. ⭐ **Graph DBs are rare in practice** — Facebook/LinkedIn/Twitter keep relationships in **SQL** and
   put a graph DB in front as a **search cache**. Use them for genuine **path-finding**.
10. ⭐⭐ **Twitter hashtags: SQL can't hold one hashtag, key-value and document both fail on size,
    rewrite cost and pagination — the answer is a wide column store**, because **pagination + write
    volume** is exactly its specialty.

---

## ➡️ Next
**[Session 16 — Case Study: IRCTC](./16_Case_Study_IRCTC.md)**
