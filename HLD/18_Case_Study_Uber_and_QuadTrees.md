# Session 18 — Case Study: Cab Booking Application (Uber) 🚕

> **Topics:** Designing Uber · Sharding for geospatial data · QuadTrees — Nearest Neighbour Search ·
> Booking request flow · Optimizing location updates · H3
>
> 📄 Class doc: [\[SST-2028\] Case Study: Uber](https://docs.google.com/document/d/1WN1DdgdgjnqlFbWuRwua0dfNWHFwDCLuHFQHNAzs0nU/edit?tab=t.0)
> *(notes credited to **Pragy Agarwal**)*
>
> ℹ️ The sheet also lists a separate **"QuadTrees — Nearest Neighbor Search"** doc, but the
> spreadsheet stores only one hyperlink per cell so that URL could not be recovered. QuadTree
> material below comes from the Uber doc plus standard theory (marked where added).

---

## 📑 Table of Contents
1. [Actors & Features](#-actors--features)
2. [The Core Problem](#-the-core-problem)
3. [The Sharding Key](#-the-sharding-key-for-driver-location)
4. [Sharding the QuadTree](#-sharding-the-quadtree)
5. [QuadTrees — how they work](#-quadtrees--nearest-neighbour-search)
6. [Tracking Driver Location](#-tracking-driver-location)
7. [Choice of Database](#-choice-of-database)
8. [Booking Request Flow](#-booking-request-flow)
9. [Ping All vs Ping One-by-One](#-ping-all-at-once-vs-one-by-one)
10. [Scale Estimation](#-scale-estimation)
11. [Optimizing QuadTree Updates](#-optimizing-quadtree-updates)
12. [Location Updates vs Grid Updates](#-location-updates-vs-grid-updates)
13. [Does Uber Actually Use QuadTrees?](#-does-uber-actually-use-quadtrees)
14. [Key Terms Recap](#-key-terms-recap)

---

## 👥 Actors & Features

### Actors
> - ⭐ **Drivers:** the ones providing the ride services
> - ⭐ **Riders:** the customers availing the ride services

### Core Feature
> ⭐⭐ **Given a Ride Booking Request made by a rider, allocate a nearby driver — FIND NEAREST
> DRIVERS.**

### Other features
| Feature | Note |
|---|---|
| **Price calculation** | **In reality, Uber has a base-price/km for each ride type that is set by the business people.** Apart from that Uber takes the **ETA** into account — ⭐ **uses maps API by other providers (Google Maps for example)**, **delegates the timing calculation to this maps provider**, and **just uses the time estimated by the maps provider and multiplies that with a fixed cost/time** |
| **Surge pricing** | 😄 ⭐ **interesting part — this is where Uber gets to rip off their customer.** *User's phone brand* |
| **Map navigation** · **Analytics** · **Driver onboarding** · **Ratings** · **Cab tiers** · **Payments** · **Auth** | |

*(Per Session 12: **auth and payments are dependencies, not what you were asked to design.**)*

---

## 🎯 The Core Problem

> **Q: When I book a ride in Mumbai, should my driver come from London?**
> ⭐ **No! The driver should come from a nearby place.**
>
> **This means that I somehow need to:**
> 1. ⭐ **track the drivers' locations**
> 2. ⭐ **store these locations in some database**
> 3. ⭐ **query these locations**

---

## 🔑 The Sharding Key (for driver location)

> **Q: What's the ideal sharding key in Uber (for driver location data)?**
> **When I'm doing this nearest-driver query, I need to look at the driver location data.**
>
> **Country would be too large, state would be too large, city would be good — maybe we can make it
> more granular…**

### How to decide the correct granularity? ⭐
> **We want things to be as large as possible — not too granular:**
> - ⭐ **because if we make a separate quadtree for every 10 m² then we will never find sufficient
>   drivers in our shard** — it has to be sufficiently large
> - ⭐ **the issue is that different regions have different density — this is why we wanted a quadtree
>   in the first place**
> - ⭐ **the ideal granularity from the perspective of a quadtree will be THE ENTIRE WORLD! Because
>   then the quadtree can adjust the grid size based on the regional density perfectly**
>
> **But we also want HIGH ENOUGH CARDINALITY:**
> - ⭐ **otherwise, we won't be able to scale horizontally**

> ⭐⭐ **Just go with `city_id`.**

```
   ⭐ THE TENSION:
      QuadTree wants ONE BIG region (so it can adapt to density itself)
      Sharding wants MANY SMALL regions (so it can scale horizontally)
      → city_id is the compromise.
```

### The three obvious objections
> - **Q: Won't some cities be much larger than other cities? Won't this cause a hot shard problem?**
> - **Q: If I'm at the edge of a city, and the closest driver is just across the city boundary, then
>   `city_id`-based sharding will not give me this closest driver.**
> - **Q: What about cross-region trips?**

### The answer — it's a real-world constraint, not a technical one ⭐⭐
> - ⭐ **In fact, there are GOVERNMENT REGULATIONS that Taxi/Commercial drivers registered within the
>   city cannot cross the city boundary**
> - ⭐⭐ **Uber's entire organisation is actually "MULTI-TENANT" — the entire org is sharded by
>   `city_id`**
> - ⭐ **"Outstation rides" in Uber — notice that this is a SEPARATE PRODUCT!**
> - **Taxi drivers that operate across cities have to pay tolls every time they cross region
>   boundaries**
>
> ⭐ **Today we will focus on the intra-city (within the city) rides flow.**

> 🧠 **A wonderful lesson:** the "flaw" in the sharding key mirrors a **real constraint in the
> business domain**. Cross-city rides are genuinely a different product with different regulation,
> pricing and supply. **The best sharding keys often follow the natural seams of the business, not
> just the data.**

---

## 🗺️ Sharding the QuadTree

> ⭐ **If Uber builds a Quadtree, then it will build a SEPARATE QuadTree FOR EACH CITY. Uber will also
> build "GLOBAL" quadtrees for each country/state.**

```
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │  Mumbai      │  │  Bangalore   │  │  Delhi       │   ⭐ one QuadTree per city
   │  QuadTree    │  │  QuadTree    │  │  QuadTree    │      (sharded by city_id)
   └──────────────┘  └──────────────┘  └──────────────┘
   ┌───────────────────────────────────────────────────┐
   │  India — global QuadTree (country/state level)     │  for outstation / analytics
   └───────────────────────────────────────────────────┘
```

---

## 🌳 QuadTrees — Nearest Neighbour Search

*(The Uber doc uses QuadTrees throughout; this section fills in the mechanism.)*

### The problem
Finding "all drivers within 2 km of me" from a flat list of 8 million drivers means computing 8
million distances. We need a **spatial index**.

### The structure
> A **QuadTree** recursively divides a 2D plane into **4 quadrants** (NW, NE, SW, SE). A node
> **splits** when the number of points inside it exceeds a threshold.

```
   ┌───────────────┬───────────────┐        ⭐ Dense downtown → splits deeply
   │               │  ┌──┬──┐      │        ⭐ Empty outskirts → stays one big cell
   │   few drivers │  │▪▪│▪▪│      │
   │               │  ├──┼──┤      │
   │               │  │▪▪│▪▪│      │
   ├───────────────┼──┴──┴──┴──────┤
   │               │               │
   │   few drivers │  few drivers  │
   │               │               │
   └───────────────┴───────────────┘
```

| Property | Detail |
|---|---|
| **Split rule** | A node holding more than *k* points splits into 4 children |
| **Adapts to density** | ⭐ **This is exactly why a QuadTree beats a fixed grid** — dense areas get fine cells, sparse areas get coarse ones |
| **Nearest-neighbour query** | Descend to the leaf containing the query point; if too few drivers, **expand to neighbouring cells / walk up a level** |
| **Complexity** | ~`O(log n)` to locate the cell |
| **Storage** | ⭐ **In-memory** (the class treats it as an in-memory service, not a disk DB) |

> ⭐ **Note the leaf capacity is what the class later calls the "split threshold" (~10 drivers).**

---

## 📍 Tracking Driver Location

> ⭐ **The driver's Uber app (frontend) will periodically ping location updates to the backend.**
>
> **We will store this location information:**
> 1. ⭐ **in the QuadTree — for finding the nearest driver**
> 2. ⭐ **in a database — for tracing the driver path & other analytics**

```
   Driver app ──location ping──▶ ┌──────────────────┐
                                 │  App Server      │
                                 └────┬────────┬────┘
                        ⭐ always      │        │  ⭐ only when needed
                                      ▼        ▼
                        ┌──────────────────┐  ┌──────────────────┐
                        │ Wide-Column DB   │  │  QuadTree        │
                        │ (location history)│  │ (nearest driver) │
                        └──────────────────┘  └──────────────────┘
```

---

## 🗄️ Choice of Database

### 1. User details
> **Data:**
> - **Customer (Rider) profile:** Name · Age · Gender · **Favorite Locations: Home/Work** · Rating
> - **Driver profile & compliance:** Name · Gender · **Cab number plate** · **License &
>   Registration** · Color of Cab · Cab model · **Pets allowed**

| Question | Answer |
|---|---|
| **schema?** | ⭐ **Unstructured data** |
| **joins?** | ⭐ **Mostly no** — *but sometimes yes: e.g. if a user has multiple fav addresses you can store addresses in a different table if you're going with SQL. If you're going with a document db, the addresses will just be an array inside the document* |
| **transactions?** | **No** |
| **Analytics?** | **No** |

> ⭐ **Ideal DB: Document Database / SQL**
> ⭐ **Sharding Key: `user_id`**

### 2. Bookings
> **Data:** for riders, for drivers

| Question | Answer |
|---|---|
| **schema?** | ⭐ **Yes** — `(user_id, driver_id, date, type of ride, status, from_location, to_location, rating, payment_id)` |
| **joins?** | ⭐ **Yes** — *find all past bookings of a rider; find all past services provided by a driver* |
| **transactions?** | ⭐ **Yes** — *each booking is an ongoing transaction. Also for payments* |

> ⭐⭐ **Ideal DB: SQL**
> ⭐ **Sharding Key: `user_id`** — **each booking must be stored in BOTH the rider shard & the driver
> shard**

> **If we shard by the `booking_id`, then how do we answer the query "given a user, find my recent
> rides"?** *(You'd fan out — exactly the Session-9 rule that **system-generated ids make bad
> sharding keys**.)*
>
> **If we have 1 billion users, does this mean we need 1 billion shards/servers?**
> ⭐ **No, a single shard/server will house millions of users.**

### 3. Driver Location data
> **Data:** **latest location** · **historical location**

| Data | Ideal DB |
|---|---|
| ⭐ **only latest location** | ⭐ **key-value** (`key = driver_id`, `value = current location`) |
| ⭐ **location history** | ⭐ **this is timeseries data / sensor readings** — we need **very fast writes**, **time based pagination**, **aggregate queries** (calculate distance, …) ⇒ ⭐⭐ **Wide Column database (timeseries)** |

> **Sharding Key:**
> - ⭐ **`user_id`** ⇒ **wide col database**
> - ⭐⭐ **Note that the nearest-driver queries will NOT go to this database** — they will instead go to
>   the **QuadTree (Nearest Driver Service)**, which is sharded by ⭐ **`city_id`**

> 🧠 **Two different sharding keys for what looks like "location data"**, because there are **two
> different access patterns**: *"where has this driver been?"* (by driver) and *"who is near me?"*
> (by place). Same lesson as IRCTC (`train_id` vs `user_id`) in Session 9.

### Database summary
| Data | Database | Sharding key |
|---|---|---|
| **User/driver profiles** | ⭐ Document DB / SQL | `user_id` |
| **Bookings** | ⭐ **SQL** (needs transactions + joins) | `user_id` (stored in **both** rider & driver shards) |
| **Latest driver location** | ⭐ **Key-Value** | `driver_id` |
| **Location history** | ⭐ **Wide Column (timeseries)** | `user_id` |
| **Nearest-driver index** | ⭐ **QuadTree (in-memory)** | ⭐ **`city_id`** |

---

## 🔄 Booking Request Flow

> **Q: Should the driver allotment for a booking request be sync (respond after finding a driver), or
> async?**

| Mode | What happens |
|---|---|
| ❌ **sync** | When the rider makes a booking request, the request goes to the backend server, **the backend allots a driver, and only then responds with success**. ⭐ **In this case the rider's booking request will TIME OUT — because it might take 10 mins to allot a driver. That's too long!** |
| ✅ ⭐ **async** | **The backend server stores the "request" in a db, and returns success to the rider (along with the `booking_id`). Then IN THE BACKGROUND it allots a driver** |

> ⭐ **This is similar to a video processing website:**
> 1. **you submit a task** (video processing / allot driver / …)
> 2. **you get a task id**
> 3. **then you periodically check / get notified if the task status has changed**

### The request flow ⭐
```
1. Rider makes a booking request  →  Booking microservice
2. Booking microservice stores this request in the booking database,
   and returns the booking_id to the rider
3. (async) it adds a task in the MESSAGE QUEUE
4. Driver Allotment microservice picks this task
5. Find k nearby drivers via the ⭐ Nearest Driver microservice
6. Notify drivers about this request via the Notifications microservice
7. Once a driver accepts, update the status in the Bookings database
8. Notify the rider about the status via the Notifications service
```

**The bookings row:**
```
bookings
id  rider_id  driver_id  source  destination  cab_type  created_at  payment_mode  status
5   durga     pragy      mumbai  pune         XL        10.44pm     upi           driver-arriving
```

```
   Rider ──▶ [Booking svc] ──▶ Booking DB ──▶ returns booking_id immediately ⭐
                   │
                   └─▶ [Message Queue] ──▶ [Driver Allotment svc]
                                                 │
                                                 ├─▶ [Nearest Driver svc (QuadTree)] → k drivers
                                                 ├─▶ [Notification svc] → ping drivers
                                                 └─▶ update Booking DB → notify rider
```

---

## 📞 Ping All at Once vs One by One

> **The Nearest Driver microservice returns k nearby drivers. Should we ping them all at once, or one
> by one?**

### Option A — Ping all drivers at once
> **Send out the booking request to all nearby drivers in PARALLEL. ⭐ Fastest-finger-first — the
> first driver to accept the booking wins.**

| | Verdict |
|---|---|
| **Rider experience** | ⭐ **low latency** for driver allotment, because we're reaching out to all nearby drivers in parallel |
| **Driver experience** | ⭐⭐ **extremely bad!** Drivers complain: *"you say this ride is available, I click accept, then you say ride no longer available"* — **because all drivers will try to click "accept" at the same time, but only 1 will win. For all other drivers, they're being fooled** |

> ⭐ **Note that multiple drivers accepting at the same time is NOT a reason for poor driver
> experience**, since the SQL schema & transaction will ensure that only 1 driver can be allotted to
> any booking:
```sql
update bookings set driver_id = 'pragy'
where id = :booking_id and driver_id is null;
```
> 💡 **That `and driver_id is null` is a compare-and-swap** — the database itself guarantees exactly
> one winner. **The problem is UX, not correctness.**

### Option B — Ping one by one ✅
> **Send out the booking request to the nearest driver (or some other way of ranking/rating/random
> ranking). Wait for a fixed time (say 10 seconds) for them to Accept. If the request gets
> Rejected/Timed out, move to the next nearest driver. If the driver accepts, update the booking
> status in the database and stop.**

| | Verdict |
|---|---|
| **Rider experience** | ⭐ **high latency** for finding drivers — **mostly this is a necessary evil, because we need to balance both rider & driver experience.** ⭐ **It's also okay, because usually the time it will take for the driver to actually ARRIVE will far exceed the allotment latency** — provided there are sufficient drivers (**bootstrapping problem**) |
| **Driver experience** | ⭐ **much more reasonable** — the driver gets a sufficient amount of time to respond |

> ⭐⭐ **Uber is a 2-SIDED MARKETPLACE — you have to please both the riders AND the drivers.**

> 🧠 **A design decision made on product grounds, not technical ones.** Both options are technically
> correct; option B is *slower* and still wins, because **driver churn is more expensive than 10
> seconds of rider wait**. Note too the justification that allotment latency is hidden inside the
> much larger arrival time.

---

## 📊 Scale Estimation

### Scale of Uber (as of 2025)
> - ⭐ **operates across 13,000+ cities globally**
> - ⭐ **8+ million drivers**
> - ⭐ **30+ million completed trips per day** ≈ **500 completed trips / second**

### Location updates per second (WRITES)
> **Let us assume that each driver works an average of 12 hours a day, and sends location updates
> every 10 seconds.**
```
#location updates / second
= (8 million drivers) × (12 hours / day / driver) × (1 update / 10 seconds)
≈ ⭐ 400,000 updates / second
```
> - ⭐ **A cluster of column-family db servers will be able to handle 400,000 writes/second. But this
>   cluster will be EXPENSIVE.**
> - ⭐⭐ **A single QuadTree server will most likely NOT be able to handle 400,000 writes per second.**
> - ⭐ **Hence, we need to OPTIMIZE the location updates.**

### Nearest-driver queries per second (READS)
> **Let us assume that each completed trip requires 3 booking attempts on average. Each booking
> attempt requires the nearest-driver API to be called once.**
```
#nearest driver queries / second
= (30 million trips / day) × (3 queries / trip)
≈ 100 million queries / day
≈ ⭐ 1,000 queries / second
```

### The verdict ⭐⭐
```
   QuadTree WRITES : 400,000 / sec
   QuadTree READS  :   1,000 / sec
   ⭐⭐ writes are 400× the reads — an extremely WRITE-HEAVY system
```
> ⭐ **Presently, the QuadTree writes are 400× more than the QuadTree reads! It's a write-heavy
> system.**

> 💡 **The surprise:** you'd assume a ride-hailing app is dominated by *searches for drivers*. It
> isn't — it's dominated by **drivers telling you where they are**.

### To optimize write-heavy systems
> - ⭐ **optimize db for writes** *(we've already done that — wide-col database, in-memory quadtree)*
> - ⭐ **reduce the # of writes if you can:**
>   - **batching** — *write-back cache ⇒ potential data loss; without write-back cache ⇒ eventual
>     consistency*
>   - **sampling** — *guaranteed data loss*
>   - ⭐⭐ **domain specific reduction logic**

> ⭐ **That third bullet is the star of this session.** Sessions 12–13 gave us the generic levers
> (batching, sampling). Here the biggest wins come from **understanding the domain**: drivers stuck
> in traffic, drivers on a break, and drivers who haven't left their cell.

---

## ⚡ Optimizing QuadTree Updates

### Optimisation 1 — Don't update if the driver hasn't moved
> **Q: If the driver is not moving / stuck in traffic, should they send location updates every 10
> seconds?**
> ⭐ **No.**
> - ⭐ **We should send location updates only if the location has changed by at least a distance
>   D = 100 m**
> - **This will reduce the number of updates to BOTH the wide-col database and the quadtree**
> - ⭐ **As a fallback, if the location hasn't changed significantly, still send an update but at a
>   lower frequency (say once every 2 mins)**

> ⭐ **Kathan's logic:** *send a location update **every 100 m or every 1 min, whichever is earlier**
> — this logic will automatically send updates **more frequently when the driver is at high speed**,
> and fall back to slow updates when the driver is stuck/not moving.*

> 💡 **Elegant:** one rule that is **self-adapting to speed**, with no explicit speed calculation.

### Optimisation 2 — Don't update if the driver isn't available
> **Q: If the driver is not available, should they send location updates?**

| Situation | Update the **DB**? | Update the **QuadTree**? |
|---|---|---|
| ⭐ **On a break** | ❌ **don't send location updates at all** | ❌ |
| ⭐ **Already in a ride** | ✅ **yes — because we want to keep track of the ride's route** | ❌ ⭐ **no — because they should not be available for the nearest-driver query** |

> ⭐ *Unless they're **close to the destination** — in which case you want to make them available
> again (**"your driver is completing a ride nearby"**).*

### Optimisation 3 — Don't update if the driver hasn't crossed the node boundary ⭐⭐
> **Q: If the driver hasn't crossed the node boundary, is there any point in updating the quadtree?**
>
> - ⭐ **Update location in Database** — so that we can track the driver location — **perform ALWAYS**
> - ⭐ **Update location in QuadTree** — **only perform when the driver has CROSSED THE NODE
>   BOUNDARY**
>   - **After an update, the quadtree will return the new node boundary**
>   - **Then the app server can check whether the new location is within the node boundary or not:**
>     ```
>     not (node.left <= x <= node.right && node.top <= y <= node.bottom)
>     ```

**The memory cost of caching boundaries:**
```
driver_id  ⇒  node boundary
   8b           8b + 8b + 8b + 8b
= 40 b / driver

8 million drivers × 40 b = 320 million bytes
= ⭐ 320 MB  ⇒  easily fits in the RAM
```
> ⭐⭐ **Since the drivers will drive WITHIN the node boundary most of the time, this significantly
> reduces the number of updates to the quadtree.**

> 🧠 **The best optimisation in the case study.** The QuadTree only cares **which cell** a driver is
> in — not the exact coordinates. So **most location updates are irrelevant to it**. Caching 40 bytes
> per driver (320 MB total) filters out the vast majority of the 400,000 writes/sec.

---

## 🔲 Location Updates vs Grid Updates

> **When a driver crosses a node boundary, perform the following:**

### 1. Location Updates — ⭐ **perform always**
> **Move the driver into the other node.**
> ⭐ **Location updates are needed so that we can find the drivers within the cell for the
> nearest-driver query.**

### 2. Grid Updates — ⭐ **doesn't need to be performed always**
> **Whenever the grid structure changes — this INVALIDATES the node-boundary cache that we have in
> the app server for all the drivers in the changed nodes.**
>
> ⭐ **Grid updates are needed so that the grid can react to the changes in the density of various
> regions.**

**Two techniques to reduce grid churn:**

| Technique | Detail |
|---|---|
| ⭐ **Cron Job (batching)** | **Update the grid structure every 5 mins.** ⭐ **This is much better than doing it 400,000 times per second** (for every update that comes to the quadtree) |
| ⭐ **Soft Threshold** | **Instead of having a HARD split threshold like 10, make it a SOFT value:** **split** when #drivers in a node **exceeds 15**; **merge** when #drivers in a node **falls below 5** |

> 💡 **The soft threshold prevents "thrashing"** — with a hard threshold of 10, a node hovering at
> 9–11 drivers would split and merge repeatedly, invalidating caches each time. A **hysteresis band
> (5…15)** stops the oscillation. *(Same idea as scaling cooldowns in autoscalers.)*

```
   ⭐ Two separate concerns, two separate cadences:
      LOCATION update (which cell is this driver in?)  → always, on boundary crossing
      GRID update     (should this cell split/merge?)  → batched every 5 min, with hysteresis
```

---

## 🔷 Does Uber Actually Use QuadTrees?

> ⭐⭐ **No 😛**
>
> **Uber primarily uses an ⭐ H3 Hexagonal Hierarchical Spatial Index rather than Quadtree or Geohash
> for geospatial indexing.**

### Why Not Quadtree?
> **Quadtree-based spatial indexing recursively divides a 2D plane into 4 quadrants. This has some
> drawbacks:**
> - ⭐ **Inefficient for load balancing:** Popular city areas (like downtown) would require a **deeper
>   quadtree structure** due to high density, **making lookups slower**
> - ⭐ **Fragmentation issues:** Unevenly sized cells mean some areas get very small cells, while
>   others remain large, **leading to inefficiencies in searching**
> - ⭐ **Edge problems:** When a driver and rider are near a cell boundary, **additional computations
>   are needed to query neighbouring cells**

### Why Not Geohash?
> **Geohash divides the world into rectangular grids and represents them as a string. This too has
> drawbacks:**
> - ⭐ **Rectangular distortion:** Geohash grids **vary in size based on latitude** due to Earth's
>   curvature, leading to **inconsistent spatial resolution**
> - ⭐ **Neighbor lookup inefficiency:** Finding adjacent regions (drivers near cell boundaries)
>   requires additional computation, as **Geohash does not have an intrinsic neighbourhood structure**
> - ⭐ **Poor hierarchical properties:** Geohash does not support multi-resolution indexing as
>   efficiently as Uber's H3

### H3 Hexagonal Hierarchical Spatial Index ⭐
> **Uber developed H3, a hexagonal hierarchical spatial index, to overcome these limitations:**
> - ⭐ **Hexagonal cells:** provide **better spatial uniformity** compared to rectangles in Geohash
> - ⭐ **Hierarchical indexing:** each hexagonal cell can be **subdivided into smaller hexagons**,
>   making **multi-resolution queries efficient**
> - ⭐⭐ **Neighboring lookup efficiency:** **hexagons have SIX EQUIDISTANT neighbours**, reducing
>   complexity in nearest-driver searches
> - ⭐ **Better load balancing:** hexagons provide a **more even distribution** of spatial data,
>   avoiding fragmentation issues seen in Quadtrees
> - ⭐ **Scalability:** H3 allows Uber to efficiently group drivers into hexagonal regions and
>   **dynamically adjust search radii based on demand**

```
   SQUARE grid                       HEXAGON grid
   ───────────                       ────────────
   ┌───┬───┬───┐                        ⬡ ⬡ ⬡
   │ ↖ │ ↑ │ ↗ │                       ⬡ ⬢ ⬡        ⭐ 6 neighbours,
   ├───┼───┼───┤                        ⬡ ⬡ ⬡           ALL equidistant
   │ ← │ ▪ │ → │
   ├───┼───┼───┤     ⭐ 8 neighbours, but the 4 diagonal
   │ ↙ │ ↓ │ ↘ │        ones are √2× further away
   └───┴───┴───┘        → "distance" depends on direction
```

### How Uber Finds the Nearest Driver ⭐
> 1. **Convert driver & rider coordinates to H3 indices at a suitable resolution**
> 2. **Lookup drivers within the same hexagon (fast query)**
> 3. **Expand search to neighbouring hexagons if necessary**
> 4. ⭐ **Compute actual distance using Haversine or road network data to refine results**

📖 https://www.uber.com/en-IN/blog/h3/

> 🧠 **Note step 4.** The spatial index only gives you **candidates**. The *real* answer needs
> **road-network distance** — the driver 200 m away across a river is useless. **The index narrows;
> it does not decide.**

---

## 🖼️ The Final Design

```
   Driver app                                         Rider app
   (location ping,                                    (booking request)
    every 100m or 1min ⭐)                                   │
        │                                                    ▼
        ▼                                          ┌──────────────────┐
   ┌─────────────────┐                             │ Booking service  │
   │  App Server     │                             └────────┬─────────┘
   │ ⭐ caches driver │                        stores request │ returns booking_id ⭐
   │   node boundary │                                       ▼
   │   (320 MB total)│                             ┌──────────────────┐
   └───┬──────────┬──┘                             │   Booking DB     │  ⭐ SQL
       │ always   │ only on boundary cross ⭐       │   (shard: user_id)│
       ▼          ▼                                └────────┬─────────┘
 ┌───────────┐  ┌────────────────────────┐                  │ (async)
 │ Wide-Col  │  │ NEAREST DRIVER SERVICE │                  ▼
 │ DB        │  │ ⭐ QuadTree / H3        │◀────────┌──────────────────┐
 │(timeseries│  │ ⭐ shard: city_id       │ k drivers│ Driver Allotment │
 │ history)  │  │ grid rebuilt: 5 min cron│         │ ⭐ ping ONE-BY-ONE│
 └───────────┘  └────────────────────────┘         └────────┬─────────┘
 ┌───────────┐                                              ▼
 │ Key-Value │  latest location                    ┌──────────────────┐
 │(driver_id)│                                     │  Notifications   │
 └───────────┘                                     └──────────────────┘
```

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Core feature** | ⭐ Given a booking request, **find the nearest drivers** |
| ⭐ **`city_id` sharding** | Balances the QuadTree's desire for **one big region** against sharding's need for **cardinality** |
| ⭐ **Multi-tenant by city** | ⭐⭐ **Uber's entire org is sharded by `city_id`** — regulation forbids cross-city taxis; **outstation is a separate product** |
| **QuadTree** | Recursively splits a plane into **4 quadrants**; ⭐ **adapts cell size to density** |
| **Split / merge threshold** | ⭐ **Soft: split at 15, merge at 5** — hysteresis prevents thrashing |
| **Node boundary cache** | ⭐⭐ `driver_id → boundary`, **40 B/driver = 320 MB** for 8M drivers; skips most QuadTree writes |
| **Location update vs Grid update** | ⭐ Location = always on boundary crossing; **Grid = batched every 5 min** |
| **Async booking** | ⭐ Return a `booking_id` immediately, allot the driver via a **message queue** (like video processing) |
| **Compare-and-swap allotment** | `update … where id = ? and driver_id is null` — ⭐ DB guarantees one winner |
| ⭐ **Ping one-by-one** | Slower for riders but **far better for drivers** — Uber is a ⭐ **2-sided marketplace** |
| **Bootstrapping problem** | Allotment latency is only acceptable if there are **enough drivers** |
| **Scale** | ⭐ 13,000+ cities · 8M+ drivers · 30M+ trips/day · **400,000 location writes/sec** vs **1,000 nearest-driver reads/sec** |
| ⭐ **400× write-heavy** | The system is dominated by **drivers reporting position**, not riders searching |
| ⭐ **Domain-specific reduction** | ⭐⭐ The third write-reduction lever, alongside batching and sampling |
| **Geohash** | Rectangular string-encoded grid; ⭐ distorts with latitude, poor neighbour lookup |
| ⭐ **H3** | Uber's **hexagonal hierarchical** index — ⭐ **6 equidistant neighbours**, uniform, multi-resolution |
| **Haversine** | Great-circle distance formula used to **refine** candidates from the spatial index |

---

## 🎯 Session Takeaways

1. ⭐ **The core problem is nearest-neighbour search over moving points** — everything else (pricing,
   navigation, ratings) is secondary or delegated.
2. ⭐⭐ **Shard by `city_id`.** The QuadTree wants one big region (to adapt to density); sharding wants
   many regions (for cardinality). City is the compromise — **and it matches a real regulatory
   boundary**, which is why Uber's whole org is multi-tenant by city and outstation is a separate
   product.
3. ⭐ **One QuadTree per city**, plus global quadtrees per country/state.
4. ⭐ **Different access patterns ⇒ different databases:** profiles (Document/SQL by `user_id`),
   bookings (**SQL**, needs transactions + joins, stored in **both** rider and driver shards), latest
   location (**key-value**), history (**wide-column timeseries**), nearest-driver (**QuadTree by
   `city_id`**).
5. ⭐ **Booking allotment must be async** — a synchronous request would time out. Return a
   `booking_id`, then work the queue, exactly like a video-processing job.
6. ⭐⭐ **Ping drivers one-by-one, not all at once.** Both are technically correct (the DB's
   compare-and-swap guarantees one winner), but broadcast **fools every losing driver**. Uber is a
   **2-sided marketplace**, and allotment latency hides inside arrival time anyway.
7. ⭐⭐ **Uber is 400× write-heavy** — 400,000 location updates/sec vs 1,000 nearest-driver
   queries/sec. Not what intuition suggests.
8. ⭐⭐ **Beyond batching and sampling there is a third lever: domain-specific reduction.** Skip
   updates when the driver hasn't moved 100 m, is on a break, or is mid-ride.
9. ⭐⭐ **The best optimisation: cache each driver's node boundary** (40 B × 8M = **320 MB in RAM**) and
   only touch the QuadTree when they **cross a cell** — since the tree only cares which cell they're
   in.
10. ⭐ **Separate location updates from grid updates:** rebuild the grid on a **5-minute cron**, and
    use a **soft split/merge threshold (15/5)** to avoid thrashing the boundary caches.
11. ⭐⭐ **Uber doesn't actually use QuadTrees — it uses H3 hexagons**, because hexagons have **six
    equidistant neighbours**, uniform spatial resolution, and clean multi-resolution hierarchy, unlike
    QuadTrees (fragmentation, deep dense areas, edge problems) or Geohash (latitude distortion).
12. ⭐ **A spatial index only produces candidates** — the final ranking uses **Haversine or road-network
    distance**.

---

## ➡️ Series complete
Back to the **[HLD index](./README.md)**.
