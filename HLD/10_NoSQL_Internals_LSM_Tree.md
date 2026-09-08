# Session 10 — NoSQL Internals: LSM Tree 🌲

> **Topics:** Basics of RDBMS internals · Designing a NoSQL DBMS · LSM Tree
>
> 📄 Class doc: [\[SST-2028\] NoSQL Internals — LSM Tree](https://docs.google.com/document/d/1fJMHZAqAUKQVuZUkqp9t7-KIGvh6ZbT1gtOwUK9AUhg/edit?usp=sharing)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [The Update Problem](#-the-update-problem)
2. [SQL: Schema-on-Write](#1-sql-has-a-strong-explicit-schema)
3. [Data Type ≠ Fixed Size](#2-data-type-does-not-always-mean-fixed-size-storage)
4. [Pages & Dirty Pages](#4-rows-are-stored-inside-pages)
5. [Write-Ahead Log in SQL](#5-write-ahead-log-the-key-idea)
6. [Variable-Length Updates](#11-variable-length-updates)
7. [Schema Changes](#12-14-schema-changes)
8. [NoSQL: No Preallocation](#-nosql-no-preallocation)
9. [Why In-Place Updates Are Impossible](#-why-in-place-updates-are-impossible-in-nosql)
10. [LSM Tree — The Three Structures](#-log-structured-merge-lsm-tree)
11. [WAL File](#1️⃣-quick-persistence--wal-file)
12. [MemTable](#2️⃣-read-cache--memtable)
13. [SSTables](#3️⃣-long-term-persistence--sstables)
14. [Compaction](#-removing-redundancies--compaction)
15. [Compaction Strategies](#-compaction-strategies)
16. [Key Terms Recap](#-key-terms-recap)

---

## 🎯 The Update Problem

The whole session builds to one question: **how do you update a value on disk when you don't know
how big the new value will be?**

SQL solves it one way (pages + WAL + in-place updates). NoSQL **can't** use that solution — and
the LSM tree is the answer.

---

## 1. SQL has a strong, explicit schema

In SQL databases, data is stored in tables. Each table has a defined schema:
```sql
CREATE TABLE users (
    id integer PRIMARY KEY,
    name varchar(20),
    age smallint
);
```

**The schema tells the database:**
- what tables exist
- what columns exist in each table
- what type each column has
- what constraints each column has

```
id   -> integer
name -> varchar(20)
age  -> smallint
```

> ⭐ **This is called schema-on-write:** whenever data is inserted or updated, **the database checks
> whether the new data follows the schema.**

```sql
INSERT INTO users (id, name, age)
VALUES (1, 'Abdur', 20);
```
**The database checks:**
- Is `id` an integer?
- Is `name` within 20 characters?
- Is `age` a valid smallint?
- Is `id` unique?

---

## 2. Data type does not always mean fixed-size storage

> ⭐ **A common misconception is that `varchar(20)` means the database always reserves 20 bytes for
> the column in every row. That is generally NOT true.**

| Value in `name` | Fits `varchar(20)`? | Storage implication |
|---|---|---|
| `Abdur` | **Yes** | Short value; **variable-length storage usually stores only the actual value plus metadata** |
| `Abdur Rehman` | **Yes** | Larger than `Abdur`, but still within the `varchar(20)` constraint |
| `Abdur Rehman Ibne Munir Bin Abdul Aziz` | **No** | Too long for `varchar(20)`; **the database usually rejects the insert/update** |

> - **Some data types are fixed-size**, such as `integer` or `smallint`
> - **But many types are variable-size**, such as `varchar`, `text`, and `varbinary`
> - ⭐ **Therefore, two valid rows may occupy different amounts of physical storage even though they
>   follow the same schema**

```
1 | Abdur        | 20
2 | Abdur Rehman | 21      ← physically larger row
```

> **Real databases also store** row metadata, null markers, transaction information, alignment
> padding, page headers, and index references. ⭐ **So the physical row size is not simply the sum of
> the declared column sizes.**

---

## 3. How updates work conceptually

Suppose we run:
```sql
UPDATE users
SET name = 'Abdur Rehman'
WHERE id = 1;
```

**The database needs to:**
1. find the row
2. check whether the new value follows the schema
3. **modify the row or create a new row version**
4. **update relevant indexes**
5. make the change **durable**
6. **keep the database recoverable if a crash happens**

> ⭐ **This is not as simple as directly going to disk and overwriting the old value.** Modern SQL
> databases combine a **buffer pool, pages, indexes, a write-ahead log, transaction metadata, and
> background flushing.**

---

## 4. Rows are stored inside pages

> ⭐ **Databases usually do not read and write individual rows directly from disk. Data is stored in
> fixed-size blocks called PAGES.**

```
Page 1
  |-- row: id=1, name='Abdur', age=20
  |-- row: id=2, name='Abdur Rehman', age=21
  |-- free space
```

> **When the database needs to update a row, it usually loads the WHOLE PAGE into memory. The row is
> modified in memory first. The page is then marked as a DIRTY PAGE.**

> ⭐ **Dirty page:** A page that has **changed in memory** but whose modified version **may not yet
> have been written back** to the table or index file on disk.

---

## 5. Write-Ahead Log: the key idea

> **Before the database safely writes the modified page to the actual table or index file, it first
> records the change in a special append-only log called the Write-Ahead Log, or WAL.**

> ⭐⭐ **WAL rule: The log record must reach durable storage BEFORE the modified data page is
> considered safely written. The log is written *ahead* of the actual data page.**

> **In B-tree-based storage engines, data and index pages are updated IN PLACE.** If a crash happens
> while only some pages have been written, **the structure could become inconsistent.** WAL prevents
> this by giving the database enough information to **recover safely** after a crash.

### 6. Update flow with WAL
```
UPDATE issued
     ↓
Find row/page                        (often using an index)
     ↓
Load page into memory                (if not already in the buffer pool)
     ↓
Check schema constraints             ('Abdur Rehman' fits varchar(20))
     ↓
Modify page in memory  → mark DIRTY
     ↓
Write WAL record
     ↓
⭐ Flush WAL before commit
     ↓
Commit transaction
     ↓
Flush dirty data/index pages LATER   (background processes)
```

### 7. Why WAL is needed
> **A single update may affect multiple physical structures:**
> - the table page containing the row
> - the **primary key index** page
> - one or more **secondary index** pages
> - transaction metadata
>
> ⭐ **If the database directly overwrote these pages and crashed halfway, the database might become
> inconsistent.** For example, **the table row could be updated while the index is not updated**, or
> **a B-tree page split could happen without its parent page being updated.**
>
> **With WAL, the database first records enough information to redo or recover the operation. After
> a crash, it can replay WAL records and bring the table and index files back to a consistent state.**

### 8. WAL is not the main table storage
> ⭐ **The WAL is usually NOT the final home of the row.** The main row still belongs in the table
> and index files.

| Structure | Purpose |
|---|---|
| **Table/index files** | **Main database storage** |
| **WAL file** | ⭐ **Recovery log** used to reconstruct committed changes after a crash |

> **The WAL answers the question:** *if the database crashes before all changed pages are written,
> how do we reconstruct the committed changes?*

### 9. Are updates applied in batches later?
> ⭐ **Yes, but with nuance.** The update is usually applied to the page **in memory immediately**,
> but the modified page **may be written to disk later**. This delayed writing can happen due to
> **checkpointing, background writer activity, buffer pool eviction, memory pressure, or shutdown**.
>
> ⭐ **Before the transaction is committed, the WAL records for that transaction must be durable.
> That is the core safety guarantee.**

---

## 10. What if the new value is too large?

```sql
UPDATE users
SET name = 'Abdur Rehman Ibne Munir Bin Abdul Aziz'
WHERE id = 1;
```
> If `name` is defined as `varchar(20)`, this value **violates the schema**. ⭐ **The database does
> NOT overflow into the next row. It usually REJECTS the update** because the value is too large for
> the declared column limit.

> ⭐⭐ **Important: `varchar(20)` is a CONSTRAINT ON ALLOWED VALUES. It is NOT a promise that 20 bytes
> were preallocated for every row.**

---

## 11. Variable-length updates

Consider this change:
```
Old value: Abdur
New value: Abdur Rehman
```
> The new value is larger, but **still fits `varchar(20)`**. Since `varchar` is usually
> variable-length, **this may require more physical storage.** The storage engine may handle this in
> different ways:
> - **use free space on the same page**
> - **create a new row version elsewhere**
> - **move large values out-of-line**
> - **update pointers or indexes**
> - **leave old row versions for later cleanup**
> - **split or reorganize pages**

> ⭐⭐ **So updates are not easy *because space was fully preallocated*. Updates are manageable
> because the storage engine knows how to modify pages safely, maintain indexes, and recover using
> WAL.**

---

## 12–14. Schema changes

### Adding a column
```sql
ALTER TABLE users
ADD COLUMN gender smallint;
```
> Conceptually the table changes from `id | name | age` to `id | name | age | gender`.
>
> ⭐ **Physically, the database may NOT immediately rewrite every row.** In many modern databases,
> **adding a nullable column can be fast** because existing rows can be treated as if the new column
> has `NULL`. **The database can store this information in metadata.**

### Adding a column with a default value
```sql
ALTER TABLE users
ADD COLUMN country text DEFAULT 'India';
```
> **Older systems might rewrite every row** to physically add the default value. **Modern databases
> may optimize this by storing the default in metadata** and returning it when old rows are read.
> **However, not all schema changes are cheap.**

### Schema changes that may require a table rewrite
```sql
ALTER TABLE users ALTER COLUMN age TYPE bigint;
ALTER TABLE users ADD COLUMN created_at timestamp DEFAULT clock_timestamp();
```

> ⭐⭐ **The correct statement is NOT: "adding or deleting a column always rewrites the table."**
> **The correct statement is: SOME schema changes are metadata-only and fast; SOME require rewriting
> the table and are slow. It depends on the database and the exact `ALTER TABLE` operation.**

> 💡 This is a useful correction to the Session-9 claim that schema changes "require a complete table
> re-write" — that's the **worst case**, not the general case.

---

## 🔓 NoSQL: No Preallocation

> ⭐ **NoSQL databases are mostly schemaless** (or semi-structured / loose schema).
> ⭐ **We don't know the size of a particular entry.**

| Key | Value | Entry Size |
|---|---|---|
| `item` | `10` | **9 bytes** (key: 4b, value: 4b, separator: 1b) |
| `preferences` | `{"theme": "dark", "autoSave": false}` | **62 bytes** (key: 11b, value: 50b, separator: 1b) |
| `contest:[id]:page[10]` | `[{user_id, rank, submission_details}, {…}, …]` | **2 Kb maybe?** |

### No Preallocation
> - **NoSQL databases do not pre-allocate max-space for an entry.**
> - ⭐⭐ **They CANNOT pre-allocate max-space. Because the possible maximum is just too large**
>   (**Redis: size limit for a string is 500 MB**) ⇒ **preallocating such large values would be a
>   massive waste of space.**

---

## 🚫 Why In-Place Updates Are Impossible in NoSQL

> **When we're updating an entry in NoSQL, the size of the entry can change.**
>
> **What happens if the value is larger than the allocated space?**
> ⭐ **Updating a value when the size has increased will cause OVERFLOW — it will end up overwriting
> the adjacent entry.**

```
   BEFORE:  ... | key1:val1 | key2:val2 | key3:val3 | ...
                      ↑ update val1 to something bigger
   AFTER:   ... | key1:LONGERVALUE2:val2 | key3:val3 | ...
                             ↑ 💥 key2 has been destroyed
```

**Two naive fixes, both bad:**
| Fix | Verdict |
|---|---|
| **Truncate** — enforce that you can't update a value to a larger size | ⭐ **Bad design — useless database** |
| **Shift** — shift all the subsequent entries to the right | ⭐ **Ridiculously slow** |

### Why is truncation OK in SQL but not NoSQL? ⭐
> - **In SQL, the developer decides the schema** — the dev is **aware of & wants to enforce** the max
>   size. ⭐ **Truncation in SQL is not unexpected behaviour.**
> - **In NoSQL the dev doesn't have any such schema.** ⭐ **Truncation will be unexpected.**

> ⭐⭐ **Therefore, in a NoSQL database it is IMPOSSIBLE to update the value on the disk in the
> traditional manner!**
>
> ⭐⭐ **Any entry inside a NoSQL database can only be APPENDED — entries are IMMUTABLE.**
>
> **Challenge: how do you perform updates & deletes?**

> 🧠 **This is the pivot of the entire session.** Immutability isn't a design *preference* in NoSQL —
> it's **forced by the absence of a schema.** Everything that follows (LSM tree, tombstones,
> compaction) is machinery built to fake mutability on top of an append-only store.
>
> *(And recall Session 5's Code Judge: we chose immutability + versioning voluntarily there, and got
> free consistency. Here the database is forced into the same trick.)*

---

## 🌲 Log-Structured Merge (LSM) Tree

The answer: **three structures working together.**

```
                    ┌──────────────────────────────────────────────┐
   WRITE ──┬───────▶│  WAL FILE      (disk, append-only)           │  durability
           │        └──────────────────────────────────────────────┘
           │        ┌──────────────────────────────────────────────┐
           └───────▶│  MEMTABLE      (RAM, hashmap)                │  fast reads
                    └──────────────────┬───────────────────────────┘
                                       │ WAL full → FLUSH
                                       ▼
                    ┌──────────────────────────────────────────────┐
                    │  SSTABLES      (disk, sorted, IMMUTABLE)     │  long-term storage
                    │   L1: ≤100MB   L2: ≤200MB   L3: ≤400MB  …    │
                    └──────────────────────────────────────────────┘
                                       ▲
                                       │ COMPACTION (merge + dedupe)
```

---

## 1️⃣ Quick Persistence — WAL File

> **Any operation (insert/update/delete) should be durable — persisted on the disk.**

> - ⭐ **Write-Ahead Log (WAL) file is an APPEND-ONLY file on the hard-disk.** Any new write
>   (insertion/deletion/updation) to the database is **just appended as a new entry at the end** of
>   the WAL file.
> - ⭐⭐ **Because the file is append-only, the writes are SEQUENTIAL. The write throughput is HIGH.**
> - **WAL file acts as temporary storage.** Data is **committed & durable**, but **it has not yet
>   been fully absorbed into the database** (internal bookkeeping is pending).
> - ⭐ **WAL file has a max size (typically: 100 MB).** Once the WAL file reaches max size ⇒ **we must
>   dump it into an SSTable.**

> ⭐ **This is the Session-9 payoff:** sequential access is up to **10,000× faster** than random
> access. By making every write a **sequential append**, an LSM tree converts the slowest disk
> operation into the fastest one.

### Can we directly read from the WAL file?
> ⭐ **Bad.**
> - **WAL file is append only**
> - **WAL file has duplicates**
> - **WAL file is not sorted**
> - **WAL file is large: 100 MB**
>
> ⭐ **You would have to scan the entire 100 MB to find the latest entry for the key.**

> **Can we have some sort of an index to give us quick access to the data?**
> ⭐ **Yes — MemTable!**

---

## 2️⃣ Read Cache — MemTable

> - ⭐ **MemTable is just a hashmap in the RAM.**
>   *(a lot of times, MemTable is also implemented as a **BBST tree** or a **sorted linked list** in
>   RAM)*
> - ⭐ **While the writes must mandatorily go to the disk (durability), the reads can be served from
>   the RAM (for ultra-high throughput).**

### MemTable as a cache — apply Sessions 3 & 4 ⭐
> **MemTable acts as an in-memory cache:**
> - **Invalidation:** ⭐ **write-through cache** — but it is **super simple (no 2PC)** because
>   **the entire LSM tree is within a single server**
>   - *if the DB is sharded, then **each shard will build its own LSM tree***
> - **Eviction:** ⭐ **Least Recently Used (LRU) eviction**

> ⭐ **Beautiful callback to Session 4:** *"if the cache is LOCAL, you will ALWAYS use immediate
> consistency (write through) — no latency issues, no 2PC required."* The MemTable is exactly that
> case: a local cache, so write-through is free.

### Sizing
> - **The maximum size of the MemTable will be limited by the DB server's RAM.** The more RAM we
>   have, the larger the db-internal cache.
> - ⭐ **Typically, the size of the MemTable is kept LARGER than the max size of the WAL file**
>   (simplifies our eviction & read queries).

> 💡 **Why "MemTable larger than WAL" matters:** it guarantees that **anything in the WAL is also in
> the MemTable** — which is why reads never need to consult the WAL at all (Session 11).

---

## 3️⃣ Long Term Persistence — SSTables

> - **SSTables are also files on the hard disk.**
> - ⭐ **Sorted String (SS) Table:** when the WAL file gets full, **we dump it into a NEW SSTable.**
> - ⭐⭐ **SSTables are IMMUTABLE! Once created, they're NEVER updated.**
>   - **They can be deleted (during compaction), but we NEVER insert/update in them.**
>   - *Note that the compaction process can delete old tables and create new ones. **But it will
>     never "edit" a table.***
> - ⭐ **The entries inside the SSTable are SORTED BY THE KEY.**
> - ⭐ **Entries inside the SSTable have NO DUPLICATES** (we deduplicate the WAL file data before
>   dumping it in the SSTable).

### Duplicates across SSTables
> **Q: Can there be duplicate entries in the SSTables?**
> - ⭐ **A single SSTable is deduplicated and sorted by key.**
> - ⭐ **However, it is possible to have duplicate entries for the same key ACROSS different
>   SSTables.**
> - **Any old entries of the key will be "overridden" by the latest write.** ⭐ **Old entries of the
>   key are now redundant.**

```
   SSTable 3 (newest):   ... key42 → "new value"   ⭐ this one wins
   SSTable 2         :   ... key42 → "older value"
   SSTable 1 (oldest):   ... key42 → "oldest value"
```
> ⭐ **This is why reads scan SSTables newest → oldest and stop at the first hit** (Session 11).

---

## 🔄 Removing Redundancies — Compaction

> **Whenever we have multiple SSTables, there's a possibility of having duplicate (redundant) entries
> across them, which leads to space wastage. We therefore need to remove the duplicates.**
>
> ⭐ **Additionally, for reads, we have to scan the SSTables one by one, so we don't want the number
> of SSTables to be large. Therefore, we need compaction to reduce the number of SSTables.**

### How it works
> - **We will take 2 consecutive SSTables and we will merge them into a single SSTable.**
> - ⭐ **While merging, we can use the MERGE algorithm from merge sort** (because each SSTable is
>   individually sorted by key). **However, for duplicate key entries, instead of taking both
>   entries, we will just take the LATEST entry.**
> - **Note that after compaction the original SSTables get deleted.**

```
   SSTable A (sorted)     SSTable B (sorted)          MERGED (sorted, deduped)
   ─────────────────      ─────────────────           ────────────────────────
   a → 1                  a → 9   (newer)     ──▶     a → 9      ⭐ latest wins
   c → 3                  b → 2                       b → 2
   e → 5                  d → 4                       c → 3
                                                      d → 4
                                                      e → 5
   ⭐ classic merge-sort merge, O(n+m), streaming
```

> ⭐ **Note that you don't have to read the entire file into RAM while compacting — you can do it in
> a STREAMING manner (because the tables are sorted).**

### When does compaction happen?
> - ⭐ **Compaction requires at least 2 tables on the SAME LEVEL.** If there are 2 tables on the same
>   level, we can compact them **to the next level**.
> - ⭐ **Compacting happens in the BACKGROUND during the usual database operations. There's no
>   downtime.**
> - ⭐ **However, compaction is EXPENSIVE** (reads, writes, deletes on disk).
> - **Therefore, we don't usually do compaction immediately when there are 2 tables on the same
>   level.**
>
> **Compaction can be done according to:**
> - **amount of tables** (`tableCountThreshold`)
> - **time passed** (compact at every midnight)
> - **low load time** (when the load is minimum or below a threshold, detect it, and start compacting)
> - …

---

## 📊 Compaction Strategies

> **Most Common Compaction Strategies:**

| Strategy | Rule |
|---|---|
| ⭐ **Levelling** | **The moment you get 2 SSTables on a level, you trigger compaction.** `tableCountThreshold = 2` |
| ⭐ **Tiering** | **There can be MORE than 2 SSTables on a level — you maintain a compaction threshold** `tableCountThreshold > 2` |

> - ⭐ **The compaction strategy is decided differently for EACH LEVEL.**
> - ⭐⭐ **Poorly tuned compaction can make or break the database performance. You have to be careful
>   while choosing the compaction strategy.**

### Level sizes
> **Q: Can we compact across levels?**
```
Typical WAL size = 100 MB
size of SSTable on Level 1  ≤ 100 MB   (because it is compacted from the WAL file)
size of SSTable on Level 2  ≤ 200 MB   (because it is compacted from 2 SSTables from Level 1)
size of SSTable on Level 3  ≤ 400 MB   (because it is compacted from 2 SSTables from Level 2)
...
```
> ⭐ **No! That's not recommended, because across levels the file sizes differ significantly. So
> compaction will be inefficient.**

*(Merging a 100 MB file with a 400 MB file means rewriting 500 MB to absorb 100 MB of new data —
enormous **write amplification**. This is exactly the reasoning in the Cassandra paper: *"there will
never be a situation where a 100GB file is compacted with a file which is less than 50GB."*)*

### Levelling vs Tiering — the trade-off
| | **Levelling** | **Tiering** |
|---|---|---|
| SSTables per level | **2** | **> 2** |
| Compaction frequency | ⭐ **More often** | Less often |
| Write amplification | ⭐ **Higher** (more rewriting) | **Lower** |
| Read amplification | ⭐ **Lower** (fewer SSTables to scan) | **Higher** (more SSTables to scan) |
| Space amplification | Lower (fewer duplicates linger) | Higher |
| Good for | **Read-heavy** | **Write-heavy** |

> 🧠 **The universal LSM trade-off triangle: read amplification ↔ write amplification ↔ space
> amplification.** Compaction tuning is just choosing where on that triangle you want to sit.

### Resources (optional)
- **[LSM-Tree Compaction Visualization](https://kshitijmishra23.github.io/lsm-tree-visualizer/)**
- *An In-depth Discussion on the LSM Compaction Mechanism* — Alibaba Cloud Community

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Schema-on-write** | ⭐ The DB validates data against the schema at **insert/update** time (SQL) |
| **Schema-on-read** | Data is stored as-is; interpretation happens at read time (NoSQL) |
| **`varchar(20)`** | ⭐ A **constraint on allowed values**, **not** a 20-byte preallocation |
| **Page** | ⭐ Fixed-size block; DBs read/write **pages**, not individual rows |
| **Buffer pool** | The in-memory cache of pages |
| **Dirty page** | ⭐ A page changed in memory but not yet written to disk |
| **WAL (SQL)** | ⭐ Append-only recovery log; **must be durable before commit** |
| **WAL rule** | ⭐⭐ The log record reaches durable storage **before** the data page is written |
| **Metadata-only ALTER** | ⭐ Some schema changes are fast (nullable column); **some rewrite the table** |
| **No preallocation** | ⭐ NoSQL **cannot** reserve max space (Redis string limit = **500 MB**) |
| **Overflow problem** | ⭐ A larger updated value would **overwrite the adjacent entry** |
| ⭐ **Append-only / immutable** | ⭐⭐ The forced consequence: NoSQL entries can **only be appended** |
| **LSM Tree** | Log-Structured Merge tree = **WAL + MemTable + SSTables + Compaction** |
| **WAL file (LSM)** | Append-only, **sequential ⇒ high write throughput**; max ~**100 MB** |
| **MemTable** | ⭐ **Hashmap in RAM** (or BBST / sorted list); **write-through** cache with **LRU** eviction; kept **larger than the WAL** |
| **SSTable** | ⭐ **Sorted String Table** on disk — **sorted by key, deduplicated, IMMUTABLE** |
| **Flush** | Dumping a full WAL into a new SSTable |
| **Compaction** | ⭐ Merge-sort 2 same-level SSTables into one, **keeping only the latest entry per key** |
| **Levelling** | `tableCountThreshold = 2` — read-optimised |
| **Tiering** | `tableCountThreshold > 2` — write-optimised |
| **Write amplification** | Extra physical writes caused by compaction rewriting data |

---

## 🎯 Session Takeaways

1. **SQL updates in place** using **pages**, a **buffer pool**, **dirty pages** and a **WAL** — and
   the WAL exists because one update touches the row page *plus* every index page.
2. ⭐ **`varchar(20)` is a constraint, not a preallocation.** Variable-length types mean two
   schema-valid rows can have different physical sizes.
3. ⭐ **WAL rule: the log must be durable before commit;** data pages are flushed lazily afterwards.
4. **Not all `ALTER TABLE`s are slow** — some are metadata-only, some rewrite the table. It depends.
5. ⭐⭐ **NoSQL cannot preallocate** (Redis strings can be 500 MB), so a grown value would **overflow
   into the next entry**. Truncating is fine in SQL (the dev chose the limit) but **unacceptable in
   NoSQL**, and shifting is impossibly slow.
6. ⭐⭐ **Therefore NoSQL entries are append-only and immutable** — and the LSM tree is the machinery
   that fakes updates and deletes on top of that.
7. ⭐ **WAL = durability via sequential appends** — the direct application of "sequential is 10,000×
   faster than random".
8. ⭐ **MemTable = a local, write-through, LRU cache in RAM** — write-through is free here because
   there's no network, hence no 2PC. Each **shard has its own LSM tree**.
9. **Keep the MemTable bigger than the WAL** so reads never have to touch the WAL.
10. ⭐ **SSTables are sorted, deduplicated and immutable.** Duplicates exist **across** SSTables, so
    newer tables shadow older ones.
11. ⭐ **Compaction merge-sorts same-level SSTables, keeping the latest value per key**, runs in the
    background with no downtime, and can stream (no need to load files into RAM).
12. ⭐ **Never compact across levels** — mismatched file sizes cause huge write amplification.
    **Levelling** favours reads; **tiering** favours writes; **poor tuning breaks the database.**

---

## ➡️ Next
**[Session 11 — NoSQL Internals: Sparse Index, Tombstones & Bloom Filter](./11_NoSQL_Internals_Sparse_Index_and_Bloom_Filter.md)**
