# Session 11 — NoSQL Internals: Reads, Sparse Index & Bloom Filter 🔍

> **Topics:** Read queries in LSM tree · Sparse index · Bloom Filter
>
> 📄 Class doc: [\[SST-2028\] NoSQL Internals — LSM Tree + Bloom Filter + Sparse Index](https://docs.google.com/document/d/1U8E-VUnnCDyiQYjiRThqEGFbNAxFr_H_1npiK-_lD1Y/edit?tab=t.0)
> *(notes credited to **Pragy Agarwal**)*
>
> 🎮 **LSM Visualizer:** https://kshitijmishra23.github.io/lsm-tree-visualizer/
> ([source](https://github.com/kshitijmishra23/lsm-tree-visualizer))

---

## 📑 Table of Contents
1. [The Read Problem](#-the-read-problem)
2. [Full Index — and Why It Fails](#-full-index--and-why-it-fails)
3. [Sparse Index](#-sparse-index)
4. [Deletion — Tombstones](#-deletion--tombstones)
5. [The Complete Write Algorithm](#-the-complete-algorithm--writes)
6. [The Complete Read Algorithm](#-the-complete-algorithm--reads)
7. [Bloom Filter](#-optimizing-containment-checks--bloom-filter)
8. [How Bloom Filters Work](#-how-a-bloom-filter-actually-works)
9. [The Full Picture](#-the-full-lsm-tree-picture)
10. [Key Terms Recap](#-key-terms-recap)

---

## 🐌 The Read Problem

### Why binary search matters at all
> **Binary Search O(log n) is ultra fast compared to Linear Search O(n).**
>
> Consider a database with **1 trillion entries**:
> - **Binary Search** takes `O(log₂ 1 trillion)` = **40 steps**
> - **Linear Search** takes **1 trillion steps**
>
> ⭐ **Binary Search is 25 billion times faster than Linear Search in this example!**

### But binary searching an SSTable **on disk** is still terrible
> **Binary Searching the SSTable is expensive, because the SSTable size can be large.**
```
Typical WAL size = 100 MB
size of SSTable on Level 1  ≤ 100 MB
size of SSTable on Level 2  ≤ 200 MB
size of SSTable on Level 3  ≤ 400 MB
...
```

**The arithmetic that motivates everything in this session:**
> **Consider an SSTable of size 100 GB. Assume each entry (key, value, timestamp) on average is
> 100 bytes.**
```
Number of entries in the SSTable = 100 GB / 100 bytes = 1G = 1 billion

For a binary search, # iterations = log₂(10^9) = 9 × log₂(10) ≈ 30 iterations

⭐ Each iteration on the disk is a RANDOM READ. Each random read takes ~18 ms

Total time for checking 1 SSTable = 30 × 18 ms = 540 ms
```
> ⭐⭐ **If we have 10 SSTables, then each read potentially takes 5.4 SECONDS worst case.**
>
> **Therefore, we need an index.**

*(The 18 ms figure is straight from Session 9: 10 ms seek + 8 ms rotation.)*

### The idea
> ⭐ **What if we get rid of the binary search O(log n) and instead use an in-memory (RAM) index to
> exactly pin-point the location of an entry in the SSTable — O(1)?**
>
> **This will give us a 30× speedup** (in the above example of an SSTable with 1 billion entries).
>
> **So each SSTable lookup is now just 18 ms, and since you've 10 SSTables, your reads take 180 ms
> total worst case (30× faster compared to 5.4 seconds).**

### The real-world effective latency ⭐
> **Notice that this is not always the case** — ⭐ **90% of the reads are being served directly from
> the RAM thanks to the MemTable which acts as a read cache. Reading from the MemTable takes 0.1 ms
> at worst.**
>
> **Effective read latency is actually much better. Only 10% of the time you need to hit the disk,
> and in the worst case of that, you will hit 180 ms of read latency.**
>
> ⭐ **Effective read latency ~20 ms on average.**

```
   90% of reads → MemTable (RAM)  →   0.1 ms
   10% of reads → disk           → 180 ms  (worst case)
   ───────────────────────────────────────────
   effective average             ≈  20 ms   ⭐
```

---

## 📚 Full Index — and Why It Fails

> **Instead of binary searching the SSTable, what if we maintain a hashmap of `{key: offset}` in the
> RAM for each SSTable?**
>
> - **Given a key, we don't have to binary search the SSTable.**
> - **We just check the Index to find if the key is there in the SSTable. If the key is there in the
>   index, the index will give us the exact offset within the file to read.**
> - ⭐ **Reads: O(1) per SSTable. 30× speedup**

### The problem — RAM
> **However, maintaining a full index in the RAM will take a lot of space:**
```
Our SSTable has 1 billion entries. So the index will also have 1 billion entries.
For each entry we need: the key (say 20 bytes on avg) + the offset (8 bytes) = 28 bytes

Total = 1 billion entries × 28 bytes/entry  =  28 GB   for ONE SSTable
For 10 SSTables                             = 280 GB
```
> ⭐⭐ **That's too much RAM.**

---

## 🎯 Sparse Index

> - ⭐ **Sparse Index is built for each SSTable, and is stored in the RAM.**
> - ⭐ **Sparse Index is built when the SSTable is created.**

### The key insight
> ⭐⭐ **Because data is always read/written in BLOCKS, we don't need to maintain an index of ALL the
> keys in the SSTables. We can just maintain an index of the FIRST KEY of each block.**

```
Typical block size: 4 KB
Assume each entry (key, value, timestamp) on average is 100 bytes.

Keys in each block = 4K bytes / 100 bytes = 40 keys
```
> ⭐ **Our sparse index will be smaller in size by a factor of 40.**
>
> ⭐ **Sparse Index will now only have 25 million entries (~100 MB) for a 100 GB SSTable.**

```
   Full index   : 28 GB   per SSTable   ❌
   Sparse index : 100 MB  per SSTable   ✅  (280× smaller)
```

> ⭐ **Sparse Index is just a SORTED LIST of keys (we only take the first key of each block) of the
> SSTable. Sparse Index is stored in the RAM.**

### How it's used
```
   SPARSE INDEX (RAM)              SSTABLE (disk, 4KB blocks)
   ──────────────────              ─────────────────────────────────────
   "apple"   → offset 0            ┌ block 0: apple, ant, … (40 keys)
   "cat"     → offset 4096         ├ block 1: cat, cow, dog, … (40 keys)
   "monkey"  → offset 8192         ├ block 2: monkey, mouse, … (40 keys)
   "zebra"   → offset 12288        └ block 3: zebra, zoo, … (40 keys)

   Looking up "dog":
   1. ⭐ Binary search (LOWERBOUND) the sparse index in RAM → "cat" block  (0 disk reads)
   2. ⭐ Read that ONE 4KB block into RAM                    (1 disk read)
   3. ⭐ Binary search within the block, in RAM              (free)
```

> 🧠 **Why this works so beautifully:** the disk is **not byte addressable** — you pay for a whole
> 4 KB block whether you want 1 byte or 4000. So indexing *finer* than a block gains you **nothing**.
> The sparse index is exactly as precise as the hardware allows, and not one bit more.

---

## 🪦 Deletion — Tombstones

How do you delete from an **immutable** structure?

### Naive Approach 1 — delete the key from the MemTable
> ⭐ **Will this work? NO!**
>
> **After this delete, if we try to read the value, we will end up searching the SSTables.**
> ⭐ **Effectively, this approach will not really delete the key — it will just undo the last write.**

### Naive Approach 2 — delete from everywhere
> - Delete the key from MemTable
> - Delete the key from WAL
> - Delete the key from **all SSTables**
>
> **This will certainly get rid of the key. But it is incredibly expensive.**
>
> ⭐ **Note that SSTables are immutable. If you delete data, since you can't shift all the other data,
> there will be GAPS in the disk.**

### The solution — Tombstone ⭐
> ⭐ **Tombstone (aka Sentinel / Flag / Marker / Guard) is a special marker that indicates that the
> value has been deleted.**
>
> ⭐⭐ **Any deletes happen via WRITES.**

```java
TOMBSTONE = "PZpaIBk8rbaIQVoUqGD2NS04qD3gONn0QH1Cm2DKBkoktwGuEt"
// it is practically impossible for your data to contain this exact random string by sheer chance.

void set(key, value) {
    ...
}

void delete(key) {
    set(key, TOMBSTONE)          // ⭐ a delete IS a write
}

string _get(key) {
    // check memtable
    // check sstables
    // ...
}

string get(key) {
    value = _get(key)
    if (value == TOMBSTONE) {
        raise KeyNotFoundError!
    }
    return value
}
```

> 💡 **Note the trick with the sentinel value:** rather than adding a "deleted" flag to the storage
> format, they pick a **random 50-character string** that real data will never contain. Crude, but it
> requires **no format change at all**.

### Tombstones and compaction ⭐
> ⭐ **Note: Compaction can only delete Tombstones from the OLDEST SSTable (the one starting from
> SSTable 0). If an SSTable is not the oldest, the tombstone entries must still be stored in the
> SSTable.**

**Why?** If you dropped a tombstone from a middle SSTable, an **older** SSTable might still contain
the original value — and the read (scanning newest → oldest) would find that stale value and
**resurrect the deleted key**. Only when nothing older exists is it safe to forget.

```
   SSTable 2 (new) : key42 → TOMBSTONE     ← drop this…
   SSTable 1       : key42 → "value"       ← …and key42 comes back to life 💥
   SSTable 0 (old) : —
```

---

## ✍️ The Complete Algorithm — Writes

> 1. ⭐ **We first append the entry into the WAL file** (for **durability**)
> 2. ⭐ **We then set the value in the MemTable** (for **fast reads**)
>
> **The following events can be triggered after any write:**
> - ⭐ **Flush:** If the **WAL file gets full**, we flush it into a **new SSTable**
> - ⭐ **Compaction:** If there are **too many SSTables on any level**, we trigger compaction
> - ⭐ **Eviction:** If the **MemTable gets full**, we use **LRU eviction** to remove the oldest entry
>
> **Also:**
> - ⭐ **Deletions happen by setting the value to TOMBSTONE**
> - ⭐ **Bloom Filter also gets updated for each write**

```
   WRITE(key, value)
     │
     ├─▶ 1. append to WAL          (disk, sequential)  → durability ✅
     ├─▶ 2. set in MemTable        (RAM)               → fast reads ✅
     └─▶ 3. insert key into Bloom Filter
              │
              ├─ WAL full?       → FLUSH to new SSTable
              ├─ too many SSTs?  → COMPACTION
              └─ MemTable full?  → LRU EVICTION
```

---

## 📖 The Complete Algorithm — Reads

### Step 1 — Check the MemTable
> **We first check the MemTable (which acts as a cache).**
>
> **If the data is found in the MemTable, then the value is GUARANTEED to be the latest value:**
> - ⭐ **because any changes first go to the MemTable (write-through) + WAL**
> - ⭐ **data in MemTable can never be stale**
> - ⭐ **Any recently written/accessed data is guaranteed to be in the MemTable**
> - ⭐ **Majority of the reads are incredibly fast — O(1) access in the RAM** (if your cache hit ratio
>   is high). **Majority of the time, we won't even have to touch the disk**
>
> ⭐ **Note that after reading the value, we must update the last-accessed timestamp in the MemTable
> for that key** *(to keep LRU correct)*.

### Step 2 — Skip the WAL entirely ⭐
> **If we don't find the data in the MemTable — note that we DON'T have to check the WAL file.**
>
> ⭐⭐ **Because the MemTable is significantly larger than the WAL and follows LRU eviction, it means
> that any data in the WAL will also be in the MemTable.**

> 💡 **This is why "MemTable > WAL" was a design decision in Session 10** — it lets you eliminate an
> entire lookup path.

### Step 3 — Scan all SSTables, newest → oldest
> ⭐ **We must now scan ALL the SSTables one by one, in REVERSE order (starting from the most recent
> to the least recent).**
>
> **For each SSTable, do:**
> 1. **Check if the key is present in the SSTable.** Since the SSTable is sorted, this would be
>    `O(log n)` **disk reads** (n = number of entries in the SSTable) — **so instead:**
> 2. ⭐ **First, Binary Search (LOWERBOUND) the key in the Sparse Index from the RAM for this
>    SSTable.** The Sparse Index will tell us **which BLOCK of the SSTable to read** — ⭐ **this
>    requires NO disk reads, since the Sparse Index is in the RAM**
> 3. ⭐ **We will read the ENTIRE BLOCK into the RAM** — **reading the entire block takes just 1 disk
>    access**
> 4. ⭐ **We can now Binary Search this block within the RAM** — **RAM is 1 million times faster than
>    disk ⇒ binary search in RAM is free**
> 5. ⭐ **If the key is found, then this MUST be the latest value (because we're scanning from recent
>    to old). We can return this value**
> 6. **If not found, we continue to the next older SSTable**
>
> **If the key is not found in any SSTable, then we raise a `KeyNotFoundError`.**
>
> ⭐ **Once we find the value, we must update the MemTable so that any subsequent accesses for this
> key are fast.**
>
> ⭐ **Note: during a read, if the value is found to be TOMBSTONE, we return a `KeyNotFoundError`.**

```
   READ(key)
     │
     ├─▶ Bloom Filter says NO?  →  ⭐ KeyNotFound (instantly, 0 disk reads)
     │
     ├─▶ MemTable hit?          →  ⭐ return (guaranteed latest, ~0.1 ms)
     │
     └─▶ for SSTable in [newest … oldest]:
             ├─ binary search SPARSE INDEX in RAM   → which block?   (0 disk reads)
             ├─ read that ONE block into RAM                          (1 disk read)
             ├─ binary search inside the block in RAM                 (free)
             └─ found? → return it (latest, since newest-first) + populate MemTable
         not found anywhere → KeyNotFound
```

### Isn't scanning all SSTables one by one slow?
> ⭐ **Yes. This is why we have the following optimizations:**
> - ⭐ **Compaction:** will **reduce the number of SSTables**. **Typically a database LSM tree will
>   have ≤ 10 SSTables**
> - ⭐ **Sparse Index:** Binary Search on disk is slow — **reduce that to O(1) search**
> - *(and the Bloom Filter, next)*

---

## 🌸 Optimizing Containment Checks — Bloom Filter

### The worst case for reads
> ⭐ **If we try to `get(key)` for a key which was NEVER inserted in the DB, then this leads to the
> SLOWEST POSSIBLE READ — the worst case for reads!**
> - **first check MemTable** — we won't find it (never inserted)
> - **scan each SSTable one by one** — we won't find it (never inserted)
>
> ⭐ **In a lot of databases, it is common to have to check if an entry was never inserted.**
>
> **For example — signing up to a website.** You have to create a username, and this username must
> be **distinct**. The user supplies a unique username `pragy1234` — we must ensure that this
> username doesn't exist in the DB already. ⭐ **This is an example of a read for a key that was
> never inserted.**

> 🧠 **The cruel irony:** the *most common* success case (a username that's free) is the *most
> expensive* read the database can perform. The bloom filter exists to fix exactly this.

### What a Bloom Filter is
> - ⭐ **Bloom Filter is a PROBABILISTIC data structure.**
> - ⭐ **Bloom Filters only support Inserts & Containment Checks.**
>   **They do NOT support reads / updates / deletes / iteration.**
> - ⭐ **Containment checks can be faulty (it can lie to you):**
>   - ⭐ **False Positive is POSSIBLE:** *if a key was **not** inserted in the bloom filter, it can
>     still say that the key exists*
>   - ⭐⭐ **False Negative is IMPOSSIBLE:** *if a key **was** inserted in the bloom filter, it will
>     NEVER say that the key does not exist*
> - ⭐ **BloomFilter is just a BIT ARRAY.**

```
   ┌──────────────────────────────────────────────────────────┐
   │  Bloom filter says "NO"   ⇒  ⭐ DEFINITELY not present    │  ← trustworthy
   │  Bloom filter says "YES"  ⇒  ⭐ MAYBE present             │  ← must verify
   └──────────────────────────────────────────────────────────┘
```

### How it's wired into the LSM tree
> - ⭐ **Whenever we insert anything into our LSM tree, we will also insert the key into the bloom
>   filter.**
> - ⭐ **Whenever we read a value from the LSM tree, we will FIRST check if the key exists in the
>   Bloom Filter:**
>   - **Bloom Filter says "Yes, key exists"** → **we will read the LSM tree**
>     - it is possible for the key to be **actually present** in the database
>     - it is also possible for the key **not** to be present (**bloom filter gave a false
>       positive**)
>     - ⭐ **no issues — we just read the LSM tree for a key which was not present (worst case
>       read). But this will happen only RARELY — the false positive rate will be low**
>   - **Bloom Filter says "No, key not found"** → ⭐ **guaranteed that this key was NEVER inserted in
>     the DB. Just return KeyNotFound!**

```java
void set(key, value) {
    bloom_filter.insert(key)
    // … proceed with the DB insertion
}

string get(key) {
    if (! bloom_filter.contains(key))
        raise KeyNotFound!
    // if bloom filter says key found
    // the DB might have the key, or might not have the key
    // proceed with normal DB check
}
```

### The cost
> ⭐⭐ **On average, a properly tuned bloom filter uses only 10 BITS PER INSERTED KEY.**

```
   1 billion keys × 10 bits  =  10 Gbit  =  1.25 GB
   ⭐ Compare with the FULL INDEX: 28 GB for the same 1 billion keys.
```

### Resources (optional)
- **Quick Demo:** https://llimllib.github.io/bloomfilter-tutorial/
- **Math & Code:** https://brilliant.org/wiki/bloom-filter/
- **Calculate optimal capacity & hashes:** https://hur.st/bloomfilter/

---

## 🔬 How a Bloom Filter Actually Works

*(Filling in the mechanism — useful for interviews.)*

**Structure:** a bit array of size **m**, and **k** independent hash functions.

### Insert(key)
```
for each of the k hash functions:
    set bit[ hash_i(key) % m ] = 1
```

### Contains(key)
```
for each of the k hash functions:
    if bit[ hash_i(key) % m ] == 0:
        return NO      ⭐ definitely absent
return YES             ⭐ probably present
```

```
   m = 16 bits, k = 3 hash functions

   insert("cat")  → bits 2, 7, 11
   insert("dog")  → bits 4, 7, 14

   index:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
   bits :  0  0  1  0  1  0  0  1  0  0  0  1  0  0  1  0

   contains("cow") → hashes to 2, 7, 14 → all three are 1
                   → ⭐ says YES, but "cow" was never inserted = FALSE POSITIVE
                     (the bits were set by "cat" and "dog")

   contains("ant") → hashes to 3, 9, 11 → bit 3 is 0
                   → ⭐ says NO — and that is GUARANTEED correct
```

### Why false negatives are impossible ⭐
Bits are only ever **set**, never cleared. So if a key was inserted, **all k of its bits are 1
forever** — the check can never fail for a key that's present.

### Why deletes are unsupported ⭐
To delete you'd have to clear bits — but those bits may be **shared** with other keys, and clearing
them would create **false negatives**, destroying the one guarantee the structure provides.
*(Variants like Counting Bloom Filters use counters instead of bits to allow deletion.)*

**Tuning:** false positive rate ≈ `(1 - e^(-kn/m))^k`, minimised at `k = (m/n) ln 2`. At ~10 bits
per key with the optimal k (≈7), the false-positive rate is **~1%** — i.e. 99% of "never inserted"
reads are answered instantly with **zero disk access**.

---

## 🖼️ The Full LSM Tree Picture

```
                                  WRITE(k, v)
                                       │
             ┌─────────────────────────┼──────────────────────────┐
             ▼                         ▼                          ▼
   ┌───────────────────┐   ┌───────────────────────┐   ┌────────────────────┐
   │  WAL FILE (disk)  │   │   MEMTABLE (RAM)      │   │  BLOOM FILTER (RAM)│
   │  append-only      │   │  hashmap, write-thru  │   │  bit array         │
   │  sequential ⇒fast │   │  LRU eviction         │   │  10 bits/key       │
   │  max ~100 MB      │   │  bigger than the WAL  │   │  no false negatives│
   └─────────┬─────────┘   └───────────────────────┘   └────────────────────┘
             │ WAL full → FLUSH (dedupe + sort)
             ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │  SSTABLES (disk) — sorted by key, deduplicated, ⭐ IMMUTABLE          │
   │                                                                      │
   │   L1: ≤100MB    L2: ≤200MB    L3: ≤400MB    …                        │
   │   each has a ⭐ SPARSE INDEX in RAM (first key of every 4KB block)    │
   │   deletes are ⭐ TOMBSTONE values                                     │
   │        ▲                                                             │
   │        └── COMPACTION: merge-sort 2 same-level tables, keep latest,  │
   │            drop tombstones only from the OLDEST table                │
   └──────────────────────────────────────────────────────────────────────┘

   READ(k):  Bloom(NO→done) → MemTable(hit→done) → SSTables newest→oldest
                                                     via Sparse Index (1 block read each)
```

### The three optimisations, and what each one buys

| Optimisation | Problem solved | Gain |
|---|---|---|
| ⭐ **MemTable** | Most reads shouldn't touch disk | **90%** of reads at **0.1 ms** |
| ⭐ **Sparse Index** | Binary search on disk = 30 random reads | **30×** — 540 ms → 18 ms per SSTable |
| ⭐ **Compaction** | Too many SSTables to scan | keeps it to **≤ 10** SSTables |
| ⭐ **Bloom Filter** | Reads for keys that were never inserted | **~99%** answered with **0 disk reads** |

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Random read cost** | ⭐ **~18 ms** on HDD (10 ms seek + 8 ms rotation) |
| **Naive SSTable search** | 30 random reads × 18 ms = **540 ms**; ×10 SSTables = ⭐ **5.4 s** |
| **Full index** | `{key: offset}` hashmap in RAM — O(1) but ⭐ **28 GB per SSTable**: too big |
| ⭐ **Sparse Index** | Sorted list of the **first key of each 4 KB block**, in RAM; **~100 MB for a 100 GB SSTable** |
| **Block** | ⭐ 4 KB — the unit the disk actually transfers; indexing finer gains nothing |
| **Lowerbound search** | Binary search for "the last key ≤ target" → tells you which block |
| ⭐ **Tombstone** | Sentinel value marking a deletion — ⭐ **deletes happen via writes** |
| **Tombstone + compaction** | ⭐ Only removable from the **oldest** SSTable, else deleted keys resurrect |
| **Read order** | ⭐ Bloom → MemTable → SSTables **newest to oldest**, first hit wins |
| **WAL is skipped on reads** | ⭐ Because MemTable **⊇** WAL (MemTable is larger, LRU) |
| **Effective read latency** | ⭐ **~20 ms average** (90% RAM at 0.1 ms, 10% disk at ≤180 ms) |
| ⭐ **Bloom Filter** | Probabilistic **bit array**; supports only **insert + contains** |
| **False positive** | ⭐ **Possible** — says present when absent (harmless, just a wasted read) |
| **False negative** | ⭐⭐ **Impossible** — never says absent when present |
| **Bloom filter cost** | ⭐ **~10 bits per key** (≈1% false positive rate) |
| **Why no deletes in a bloom filter** | Clearing shared bits would create **false negatives** |

---

## 🎯 Session Takeaways

1. **Binary search on disk is still slow** — 30 iterations × 18 ms random reads = **540 ms per
   SSTable**, and **5.4 seconds** across 10 SSTables.
2. ⭐ **A full in-RAM index would be 28 GB per SSTable** — correct but unaffordable.
3. ⭐⭐ **Sparse Index: index only the first key of each 4 KB block.** 40 entries per block ⇒
   **40× smaller** (100 MB for a 100 GB SSTable). Precise to exactly the granularity the hardware
   charges for.
4. ⭐ **Lookup becomes: binary search the index in RAM (free) → read 1 block (1 disk read) → binary
   search in RAM (free).**
5. ⭐⭐ **Deletes are writes.** A **tombstone** sentinel marks deletion, because SSTables are immutable
   and physically deleting would leave gaps.
6. ⭐ **Tombstones can only be dropped from the oldest SSTable** — otherwise an older copy resurrects
   the deleted key.
7. ⭐ **Reads never touch the WAL**, because the MemTable is larger than the WAL and LRU-evicted, so
   it's a superset.
8. ⭐ **Scan SSTables newest → oldest and stop at the first hit** — that's guaranteed to be the
   latest value.
9. ⭐ **Effective read latency ≈ 20 ms**: 90% served from the MemTable in 0.1 ms, 10% from disk.
10. ⭐⭐ **The worst read is for a key that was never inserted** — and that's a very common query
    (username availability).
11. ⭐⭐ **Bloom filter: "NO" is a guarantee, "YES" is a maybe.** False negatives are impossible
    because bits are only ever set.
12. ⭐ **~10 bits per key** answers ~99% of never-inserted lookups with **zero disk reads** — and
    deletion is unsupported because clearing shared bits would break the guarantee.

---

## ➡️ Next
**[Session 12 — Case Study: Google Search Typeahead](./12_Case_Study_Search_Typeahead.md)**
