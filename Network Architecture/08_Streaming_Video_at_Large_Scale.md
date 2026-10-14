# Session 8 — Streaming Video at Large Scale 📺

> **Topics:** Polling vs push · Long polling · SSE · WebSockets · MQTT · The cost of a held
> socket · Little's Law twice · Conditional GET · Stacked TTLs · Request collapsing · Negative
> caching · Diffs · HLS · Master & media playlists · 188-byte packets · Segment length ·
> Buffers · LL-HLS · The spoiler problem · ABR · Multi-CDN & content steering · ffmpeg
>
> 📄 Source: *CN at Scaler — Lesson 8*, "Streaming video at large scale".

> ⭐ **It starts with a live cricket scorecard.**

```http
GET /match/412/score.json      200 ·   1,088 bytes · every 15 s
GET /stream_1/index.m3u8       200 ·     228 bytes · every 4 s
GET /stream_1/seg_000008.ts    200 · 823,440 bytes · once
```

**One live match on fifty million phones** — and every week of this course shows up in it.

---

## 📑 Table of Contents

1. [The brief: one small file, fifty million times](#-the-brief-one-small-file-fifty-million-times)
2. [Two families of answers](#-two-families-of-answers)
3. [Polling](#-polling)
4. [Long polling](#-long-polling)
5. [Server-Sent Events](#-server-sent-events)
6. [WebSockets](#-websockets)
7. [MQTT](#-mqtt)
8. [How Hotstar held 50 million sockets](#-how-hotstar-held-50-million-sockets)
9. [What a held socket costs](#-what-a-held-socket-costs)
10. [Little's Law, twice](#-littles-law-twice)
11. [The arithmetic before the architecture](#-the-arithmetic-before-the-architecture)
12. [Four ways to pay for one match](#-four-ways-to-pay-for-one-match)
13. [S3 runs out of requests before money](#-s3-runs-out-of-requests-before-money)
14. [On a CDN, a 1 KB file is billed per request](#-on-a-cdn-a-1-kb-file-is-billed-per-request)
15. [Conditional GET: what 304 does and doesn't save](#-conditional-get-what-304-does-and-doesnt-save)
16. [TTLs add up](#-ttls-add-up)
17. [The thundering herd at expiry](#-the-thundering-herd-at-expiry)
18. [Request collapsing needs a shareable answer](#-request-collapsing-needs-a-shareable-answer)
19. [Negative caching: 404 and 5xx](#-negative-caching-404-and-5xx)
20. [Send diffs, not the whole card](#-send-diffs-not-the-whole-card)
21. [A versioned scorecard is a playlist](#-a-versioned-scorecard-is-a-playlist)
22. [HLS in one picture](#-hls-in-one-picture)
23. [The master playlist](#-the-master-playlist)
24. [The media playlist, polled](#-the-media-playlist-polled)
25. [VOD is a playlist that stopped changing](#-vod-is-a-playlist-that-stopped-changing)
26. [A segment is 188-byte packets](#-a-segment-is-188-byte-packets)
27. [How long should a segment be?](#-how-long-should-a-segment-be)
28. [Playlist traffic is harder than segment traffic](#-playlist-traffic-is-harder-than-segment-traffic)
29. [The buffer](#-the-buffer)
30. [Latency is a budget](#-latency-is-a-budget)
31. [The spoiler problem](#-the-spoiler-problem)
32. [ABR: the player picks the next rendition](#-abr-the-player-picks-the-next-rendition)
33. [Many origins, many CDNs](#-many-origins-many-cdns)
34. [Stale playlists and deleted segments](#-stale-playlists-and-deleted-segments)
35. [Caching rules for a live stream](#-caching-rules-for-a-live-stream)
36. [Making the stream with ffmpeg](#-making-the-stream-with-ffmpeg)
37. [The whole course in one cricket match](#-the-whole-course-in-one-cricket-match)
38. [Key Terms Recap](#-key-terms-recap)
39. [Session Takeaways](#-session-takeaways)

---

## 🏏 The brief: one small file, fifty million times

| **25–45 s** | **50 M** | **~1 KB** | **100** |
|---|---|---|---|
| between balls; an over every 4–5 minutes | peak concurrent viewers; **20 M average** across a 4-hour match | per scorecard: 4–5 KB of JSON, **about 1 KB gzipped** | events a year, each one the same file downloaded again and again |

---

## 🔀 Two families of answers

| **NON-PERSISTENT — the client asks** | **PERSISTENT — the server tells** |
|---|---|
| **Polling:** GET the same URL every few seconds | **Long poll:** a GET the server answers only when there is news |
| **Conditional GET:** 304 when nothing changed | **Server-Sent Events:** one response that never ends |
| **Caches:** nginx in front, then a CDN | **WebSockets:** HTTP upgrades into a two-way, framed pipe |
| **Any server:** no memory of who asked last time | **PubSub (MQTT):** topics, a broker, fan-out to every subscriber |
| | **Plain binary socket:** your own protocol |
| ⭐ Every request is an ordinary GET: **stateless servers, cacheable answers, and a CDN can stand in front.** | ⚠️ Every viewer holds a connection for the whole match: **stateful servers, and nothing a CDN can cache.** |

---

## 🔁 Polling

```js
let etag = null;
const EVERY = 15_000;                                   // ms

async function poll() {
  const res = await fetch("/match/412/score.json", {
    headers: etag ? { "If-None-Match": etag } : {},
  });
  if (res.status === 200) {                             // something changed
    etag = res.headers.get("ETag");
    render(await res.json());
  }                                                     // 304: keep what we have
  const jitter = 0.8 + Math.random() * 0.4;             // ⭐ ±20%
  setTimeout(poll, EVERY * jitter);
}
poll();
```

| | |
|---|---|
| **ETag + `If-None-Match`** | Nothing changed → **304 and an empty body**. ⚠️ **The request still happens.** |
| **Jitter** | ±20%, so ⭐ **fifty million phones do not poll on the same second** (Session 7). |
| **Freshness** | ⚠️ At worst **one poll interval plus every cache TTL on the path**. |

---

## ⏸️ Long polling

```http
GET /match/412/score?after=1841 HTTP/1.1
    … the server holds the request open …
    … until ball 1842 is bowled, or 25 s pass

HTTP/1.1 200 OK
{"version":1842,"over":"15.4","total":"146/4"}

GET /match/412/score?after=1842 HTTP/1.1      … and ask again at once
```

| | |
|---|---|
| ⚠️ **A held request is a held socket** | Every viewer has one open almost all the time: **W is 25 s, not 30 ms**. |
| ⚠️ **Beat every idle timeout** | Answer before nginx's `proxy_read_timeout` and the ALB idle timeout — **both default to 60 s** (Session 4). |
| ⚠️ **It synchronises the herd** | A wicket completes **20M responses in one second**, and **20M new requests arrive in the next** (Session 7). |
| ⭐ **It came back, standardised** | **Low-Latency HLS's blocking playlist reload is long polling.** |

---

## 📡 Server-Sent Events

```http
GET /match/412/events HTTP/1.1
Accept: text/event-stream
Last-Event-ID: 1841

HTTP/1.1 200 OK
Content-Type: text/event-stream

retry: 5000

id: 1842
event: ball
data: {"over":"15.4","runs":4,"total":"146/4"}

id: 1843
event: ball
data: {"over":"15.5","runs":0,"total":"146/4"}
```

| | |
|---|---|
| **Framing by delimiter** | ⭐ An event ends at a **blank line**: **SMTP's lone dot in a different costume** (Session 2). |
| **Resume from a version** | On reconnect the browser sends **`Last-Event-ID`**, and the server replays only what was missed. |
| ⚠️ **About six per browser** | Over HTTP/1.1 each tab holds its own connection; **HTTP/2 multiplexes them onto one** (Session 5). |
| **One way only** | Server → client. Anything the phone says goes in ordinary requests. |

---

## 🔌 WebSockets

```http
GET /live HTTP/1.1
Host: score.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13

HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

**After the 101, every frame starts like this:**

| Field | Bytes | What it says |
|---|---|---|
| FIN · RSV · opcode | 1 | last fragment? text, binary, ping, pong, close |
| MASK · length | 1 | **0–125 is the length; 126 or 127 means read more** |
| extended length | 0, 2 or 8 | a 16- or 64-bit length |
| masking key | 0 or 4 | present on **every client-to-server** frame |
| payload | length | your 183-byte scorecard diff |

> 💡 The `Accept` value is `base64(SHA-1(key + a fixed GUID))` — **base64 again** (Session 1).
> ⭐ **Client frames are masked so stray bytes can never look like a request to a caching
> proxy** (Session 6 — cache poisoning).

> ⭐ **A length, not a delimiter: the other answer from Session 2.**

---

## 📬 MQTT

```text
phone                                                broker
  ──CONNECT client=phone-8812 keepalive=60─────────▶
  ◀─CONNACK accepted────────────────────────────────
  ──SUBSCRIBE match/412/score qos=1────────────────▶
  ◀─SUBACK──────────────────────────────────────────
  ◀─PUBLISH match/412/score retain=1 {"v":1842,…}───
  ──PINGREQ  C0 00─────────────────────────────────▶   two bytes, every keepalive
  ◀─PINGRESP D0 00──────────────────────────────────
```

⭐ **One PUBLISH from the scorer; the broker copies it to every subscriber of the topic.**
Hotstar picked MQTT with the **EMQX** broker for exactly this fan-out.

| | |
|---|---|
| **Retained message** | The broker keeps the last score and hands it to each new subscriber at once — ⭐ **a cache, inside the broker**. |
| **QoS 1 is at-least-once** | ⚠️ Duplicates happen; **apply updates by version number** and they become harmless (Session 7). |
| **Remaining Length is a varint** | 7 bits per byte, top bit says *"more"* — ⭐ **a type, a length, a value** (Session 1's TLV). |
| ⚠️ **Keepalives cost** | Two bytes, **but they wake the phone's radio** and keep a NAT mapping alive. |

---

## 🏗️ How Hotstar held 50 million sockets

| # | Step | |
|---|---|---|
| **1** | **One node** | EMQX on one `c5.4xlarge`: **250k connections**, latency in bounds |
| **2** | **A cluster** | Publisher split from subscribers: **2M**. ⚠️ Mnesia wants **fewer than 10 nodes**. |
| **3** | **The ELB wall** | ⚠️ Drops at **~500k without pre-warming**; **4M** per pre-warmed Classic ELB |
| **4** | **Five clusters** | 5 clusters × 8 subscribe nodes, bridged: **past 10M** |
| **5** | **Reverse bridge** | A Go service on each subscriber **pulls** from the publisher. **200 nodes: 50M** |

> ⚠️ *"Caching at any level is also not possible."* Their social feed was tied to live moments,
> so it **had to be pushed**.
> ⭐ **A scorecard is the opposite case: one file, identical for everyone.**

---

## 💸 What a held socket costs

| | |
|---|---|
| **Machines** | ⚠️ **Stateful: each phone lives on one box for hours.** 100k–200k connections per box; Hotstar measured 250k. **New boxes sit empty until someone reconnects, so rebalancing means disconnecting people.** |
| **Memory** | Kernel socket buffers, TLS state, the broker's per-client process. **250k phones on a 32 GiB box is ~137 KB each.** And the soft `ulimit -n` still starts at **1,024**. |
| **Network** | ⚠️ Keepalives with nothing to say: at a 60 s keepalive, **20M idle phones send 333k pings a second before the first ball is bowled**. |
| **Load balancers** | One address instead of 200 for DNS to hand out, and an even spread. ⚠️ **But the LB holds every socket too** — Hotstar hit **4M per Classic ELB**. |

> 💡 **Testing it:** one client IP has **28,232 ephemeral ports** (32768–60999) *per
> destination*, so **250k test sockets need at least 9 source IPs**. Session 1: a port is 16
> bits.

---

## ⚖️ Little's Law, twice

```
L = λ × W
```

| **Polling through a CDN** | **Push over held sockets** |
|---|---|
| 1.67 M requests/s × ~0.03 s at the edge | W is **the whole match**: four hours |
| ⭐ **≈ 50,000 requests in flight** | ⭐ **50,000,000 sockets held, ball or no ball** |

> ⭐ **Same audience, same scorecard: a thousand times the concurrency, because W went from
> milliseconds to hours.**

---

## 🧮 The arithmetic before the architecture

```
requests / match = 20M viewers × 14,400 s ÷ 30 s   =  9.6 B
peak rate        = 50M viewers ÷ 30 s              =  1.67 M req/s
bytes / match    = 9.6 B × 1 KB                    =  9.6 TB
```

| **9.6 B** | **1.67 M** | **9.6 TB** |
|---|---|---|
| requests per match | requests a second at the peak | of scorecard per match |

| Variant | |
|---|---|
| **poll every 15 s** | 19.2 B requests, 3.33 M req/s, 19.2 TB |
| **push each ball** | ~9.6 B messages, one every ~30 s per phone |
| **× 100 events a year** | ⭐ **960 B requests and 960 TB a year** |

> ⭐ **Multiply before you choose** (Session 3).

---

## 💰 Four ways to pay for one match

| Design | Per match | × 100 events | Mostly paying for | Breaks first |
|---|---|---|---|---|
| **S3 straight to phones** | $4.7K | $470K | GET fees | ⚠️ **5,500 GET/s per prefix** |
| **nginx fleet + ALB** | $1.2–1.8K | $120–180K | egress + **load balancer units** | 20–50M idle keep-alive sockets at the LB |
| **CDN (CloudFront, India)** | $12.5K | $1.25M | ⚠️ **request fees: 92%** | *nothing; it is just the bill* |
| **Push: 200 × c5.4xlarge** | $0.9–1.6K | $90–160K | a peak-sized fleet + egress | reconnect storms, rebalancing |

> ⭐ **At list price, push is the cheapest per match and the CDN the dearest. Hold that
> thought** — and then read the next two slides.

---

## 🪣 S3 runs out of requests before money

| **5,500** | **1.67 M** | **303×** |
|---|---|---|
| GETs a second that one S3 prefix promises, **at least** | GETs a second that 50M phones polling every 30 s ask for | **over**, and **one key lives under one prefix** |

> ⚠️ *"While Amazon S3 is scaling to your new higher request rate, you may see some **503 (Slow
> Down)** errors."*
> ⭐ **Fifty million clients retrying a 503 without backoff is Session 7's retry storm, pointed
> at your own bucket.**

---

## 🧾 On a CDN, a 1 KB file is billed per request

| Per million responses | Request fee | Byte fee |
|---|---|---|
| **Scorecard, 1 KB** | **$1.20** | $0.11 |
| **480p segment, 823 KB** | $1.20 | **$59–90** |

```
you pay per REQUEST  ←──────── break-even ≈ 11 KB ────────▶  you pay per BYTE
playlist 228 B · scorecard 1 KB        360p 459 KB · 480p 823 KB · 720p 1.6 MB
```

> ⭐ **92% of the scorecard's CDN bill is request fees, not bytes.**

> ⭐ **And the honest framing:** *"I prefer polling because I want to tell you how it's used
> for video too."*
> **Cacheable** — one file, identical for fifty million people. **Stateless** — any server, any
> edge, any CDN can answer any phone. **Already paid for** — at list price **the scorecard is
> 0.28% of the same match's video bill**.

---

## 🔖 Conditional GET: what 304 does and doesn't save

```http
GET /match/412/score.json HTTP/1.1
If-None-Match: "v1841"

HTTP/1.1 304 Not Modified
ETag: "v1841"
Cache-Control: public, max-age=10
```

| | |
|---|---|
| ✅ **Saves** | the 1 KB body, the JSON parse, the re-render |
| ⚠️ **Does NOT save** | **the request fee, the round trip, the headers** |
| ⭐ **Pays most between CDN tiers** | edge → mid-tier, mid-tier → origin: **304s instead of copies** |

💡 Make the ETag **the scorecard's version number** — a fingerprint, not a clock.
`If-Modified-Since` works too, **but only to the second**.

---

## ⏱️ TTLs add up

```
client poll 30 s  +  edge TTL 30 s  +  mid-tier TTL 30 s
     = up to 90 s stale — two or three balls behind the stadium

client poll 15 s  +  edge TTL 5 s  +  mid-tier TTL 5 s
     = up to 25 s — inside one ball
```

> ⭐ **Worst-case staleness = the poll interval + every cache TTL on the path.**
> **Keep each CDN TTL at ⅓ of the freshness you promise or less**, and **refresh the edge
> before it expires** — a prefetch at ~25 s of a 30 s TTL (Akamai calls it **prefresh**).

---

## 🐘 The thundering herd at expiry

> At 10.000 s the edge's copy expires. **Every request in that instant is a miss, and all of
> them head for the origin.**

| | |
|---|---|
| **Request collapsing** | One fetch per edge per object; everyone else **waits in a queue** |
| **Serve stale while updating** | Answer from the old copy while one request refreshes it (RFC 5861) |
| **Prefetch before expiry** | Refresh at ~25 s of a 30 s TTL, so **no viewer meets an empty cache** |
| **Jitter from the client** | Spread polls across the interval, **not on the same second** |

```nginx
proxy_cache_lock on;
proxy_cache_use_stale updating error timeout http_500 http_502 http_503 http_504;
proxy_cache_background_update on;
proxy_cache_valid 200 10s;
```

---

## 🧲 Request collapsing needs a shareable answer

```
20,000 phones ask one edge  →  edge sends 1 request upstream  →  origin sees 1 request
for score.json in the same      19,999 wait in a queue
50 ms
```

| | |
|---|---|
| ⭐ **Make it public early** | **The first response decides.** `Cache-Control: public` **releases every waiter at once**. ⚠️ A `private` answer, or a stray `Set-Cookie`, **dequeues them one by one** — and Fastly then **skips collapsing for that object for 2 minutes**. |
| **Early hints** | Name the next thing **before it exists**: HTTP **103** for pages; in **Low-Latency HLS**, a **preload hint** names the next piece, requests for it **queue at the edge**, and **one arrival releases them all**. |

> ⚠️ **Check the default first:** Cloudflare **does not cache `.json`** out of the box
> (Session 6). Without a cache rule, `cf-cache-status` says **DYNAMIC** and every poll reaches
> you.

---

## 🚫 Negative caching: 404 and 5xx

| **5xx — cache it, briefly** | **404 — almost never** |
|---|---|
| ⭐ One or two seconds of a cached 503 **shields a struggling origin from fifty million retries**. The edge answers; the origin sees **one probe per TTL per edge**. | ⚠️ A 404 for a file **that is about to exist** keeps being served until its TTL runs out — the next match's scorecard, **the newest live segment**. Cloudflare's default edge TTL for a 404 is **3 minutes**. |

```nginx
proxy_cache_valid 200           10s;
proxy_cache_valid 404            1s;
proxy_cache_valid 500 502 503 504 2s;
```

> ⭐ **Rule: a negative TTL must be far shorter than the time it takes the missing thing to
> appear.**

---

## 🪄 Send diffs, not the whole card

| **4,117 B** | **1,088 B** | **183 B** |
|---|---|---|
| the full scorecard JSON | the same card, **gzipped** | ⭐ one ball as a **gzipped JSON Patch** |

| **Push: send the patch** | **Pull: version the file** |
|---|---|
| SSE or MQTT carry the 183-byte patch. A phone that missed one **sees a version gap and fetches the full card once**. | ⚠️ `?since=1841` gives every client **its own URL and the hit rate collapses**. ⭐ **Publish one file with the version and the last few changes instead.** |

---

## 🧩 A versioned scorecard is a playlist

| `score.json` — polled every 15 s | `index.m3u8` — polled every 4 s |
|---|---|
| `"version": 1842` | `#EXT-X-MEDIA-SEQUENCE:2` |
| `"recent": [ {v:1839,…}, {v:1840,…}, … {v:1842,…} ]` | the last N segments: `seg_000002.ts … seg_000011.ts` |
| poll interval | `#EXT-X-TARGETDURATION:4` |

> ⭐ **A small index everyone polls, pointing at numbered pieces that never change.**
> **That design has a name: HTTP Live Streaming.**

---

## 🎞️ HLS in one picture

| | **CONTROL** | |
|---|---|---|
| **1 — once** | `master.m3u8` | the menu: 3 renditions with bandwidth, resolution, codecs |
| **2 — every 4 s** | `stream_1/index.m3u8` | the last 10 segments, 4 s each; **changes every 4 s** |
| **3 — each new one** | `stream_1/seg_000011.ts` | **DATA** — 4 s of audio+video, 823 KB; **never changes** |

**The player:**

1. Read the master **once**; pick a rendition
2. Reload its playlist **every target duration**
3. Fetch each new segment **into the buffer**
4. **Play from the buffer**; switch rendition when throughput changes

> ⭐ **Control and data want separating** — Session 2's closing idea, as a file format.

---

## 📋 The master playlist

```m3u8
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-STREAM-INF:BANDWIDTH=3440800,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
stream_0/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1755600,RESOLUTION=854x480,CODECS="avc1.4d401f,mp4a.40.2"
stream_1/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=950400,RESOLUTION=640x360,CODECS="avc1.4d401e,mp4a.40.2"
stream_2/index.m3u8
```

| | |
|---|---|
| **"Do not poll this again"** | ⭐ It **does not change during the match**: fetch once, cache for minutes. |
| **"Some people poll: switch CDNs"** | Re-reading the menu is how a player learns a new path. Standardised later as **Content Steering**. |
| **"Falling back to another codec"** | ⭐ `CODECS` lets the player **skip what it cannot decode** — HEVC down to H.264. **A fallback, not a retry** (Session 7). |

💡 `BANDWIDTH = (video + audio) × 1.1`: `(3000k + 128k) × 1.1 = 3,440,800`.

---

## 🔄 The media playlist, polled

```m3u8
# reload at t = 47.0 s          # reload at t = 51.5 s
#EXT-X-TARGETDURATION:4         #EXT-X-TARGETDURATION:4
#EXT-X-MEDIA-SEQUENCE:1         #EXT-X-MEDIA-SEQUENCE:2
#EXTINF:4.000000,               #EXTINF:4.000000,
#EXT-X-PROGRAM-DATE-TIME:…      #EXT-X-PROGRAM-DATE-TIME:…
seg_000001.ts                   seg_000002.ts
  … 8 more …                      … 8 more …
seg_000010.ts                   seg_000011.ts
```

**RFC 8216 §6.3.4 — the reload rules:**

| | |
|---|---|
| **Changed?** | Wait **at least one target duration** before reloading again. |
| **Unchanged?** | Wait **half a target duration**, then try again. |
| ⚠️ **Same number, different URI?** | *"It SHOULD halt playback."* |

---

## 🎬 VOD is a playlist that stopped changing

```m3u8
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10,
1719543778001_4328560526001_s-1.ts?pubId=1719543778001&videoId=4328294689001
  … 62 more …
#EXTINF:5,
1719543778001_4328560526001_s-64.ts?pubId=…
#EXT-X-ENDLIST
```

| | |
|---|---|
| **`#EXT-X-ENDLIST`** | ⭐ No more segments: **read it once, stop polling**. |
| **10 s segments** | old advice. **Apple now says 6 s.** |
| **`?pubId=…&videoId=…`** | ⭐ **Same for everyone, so it caches.** ⚠️ A **per-viewer token would not** — the query string is in the cache key (Session 6). |

---

## 📦 A segment is 188-byte packets

```
┌──────────────────────┬─────────────────────────────────────────┐
│ 4-byte header        │ 184-byte payload                        │
│ 0x47 · PID (13 bits) │ a slice of video, audio, or PAT/PMT     │
│      · counter       │                                         │
└──────────────────────┴─────────────────────────────────────────┘
```

| Rendition | One segment | 188-byte packets | Overhead |
|---|---|---|---|
| 720p | 1,613,416 B | 8,582 | 3.3% |
| 480p | 823,440 B | 4,380 | 4.1% |
| 360p | 452,328 B | 2,406 | 5.6% |

> ⭐ **Fixed length and a sync byte. Both of Session 2's framing answers at once.** 188 was
> chosen for ATM.
> **A 13-bit PID says whose packet it is** — audio, video and tables share one byte stream
> (Session 5's multiplexing).
> 💡 **fMP4 and CMAF segments are boxes instead: size, type, payload — TLV again** (Session 1).

---

## 📐 How long should a segment be?

| Segment | Peak segment requests | Latency floor (3×) | |
|---|---|---|---|
| **2 s** | 25 M/s | 6 s | |
| **3 s** | 16.7 M/s | 9 s | our ffmpeg run |
| **4 s** | 12.5 M/s | 12 s | |
| **6 s** | 8.3 M/s | 18 s | **Apple's advice** |
| **30 s** | 1.7 M/s | 90 s | ⚠️ *"Too late!"* |

> ⭐ **The trade:** shorter → **more requests, more keyframes, more round trips**. Longer →
> **more latency, slower reaction to bandwidth**.

💡 **Adaptive / hybrid:** 1–2 s segments at start-up for a fast first frame, longer ones later.
ffmpeg has a knob: `-hls_init_time 1 -hls_time 4`.

---

## ⚠️ Playlist traffic is harder than segment traffic

| | **Media playlist** | **Segment** |
|---|---|---|
| **Size** | ~230 B gzipped | 450–1,600 KB |
| **Changes** | **every 4 s** | **never** |
| **Cache TTL** | ⚠️ ≤ target duration | minutes to forever |
| **A stale copy** | ⚠️ **stalls, or points at deleted files** | harmless |
| **Billed by** | ⭐ **requests, like the scorecard** | bytes |

> ⚠️ *"Rendition: poll every second → RPS?"* At 1 s that is **50 M requests a second** at the
> peak. At the RFC's one target duration, **12.5 M**.

---

## 🪣 The buffer

```
  played │ seg 9 │ seg 10 │ seg 11 │ seg 12 │ …        live edge
         ▲
      playhead — 12 s buffered ahead of it, the next segment still downloading
```

| **Large buffer** | **One-segment buffer** |
|---|---|
| Survives a bad minute on a train, ⚠️ but **costs latency**, and memory on low-end phones and TV sticks. | Lowest latency. ⚠️ **One slow segment and the picture stalls.** |
| **More network, less buffer** — on a fast link a refill takes a fraction of a segment, so a small buffer is enough. | ⭐ **Stale playlist:** when the playlist stops moving, **the buffer is what keeps the picture going.** |

> ⭐ **The buffer is the stale cache** (Session 7).

---

## ⏳ Latency is a budget

```
encode   segment fills   to CDN   player hold-back: 3 × target duration
 ~2 s        4 s          ~2 s                12 s
                                                        ≈ 20 s behind the stadium
```

**Low-Latency HLS shrinks the biggest bar with four ideas from the first half of the course:**

| | |
|---|---|
| **Parts** | ~1 s pieces of a segment. Apple: at least **3× the P95 round trip** (Session 6). |
| **Blocking reload** | `?_HLS_msn=…` is **held until that segment exists**. ⭐ **Long polling.** |
| **Preload hints** | Name the next part early. ⭐ **Replaced HTTP/2 push** in Jan 2020 (Session 5). |
| **Delta updates** | `EXT-X-SKIP` drops old entries from the reply — **diffs, for playlists**. |

> ⭐ **With 1-second parts the 12 s hold-back becomes about 3 s.** Apple requires
> `PART-HOLD-BACK` of **at least three parts**.

---

## 🙈 The spoiler problem

```
0 s  — wicket at the stadium
       ↓
~10 s — the scorecard says W        ⟍
                                      spoiler window ≈ 10 s
~20 s — the video shows it          ⟋
```

> ⭐ **Hold the score until the picture catches up.** Stamp each update with the ball's
> **wall-clock time**. The player knows the wall-clock time of every segment, so the app
> **reveals an update only when playback passes it.**

```json
{"v": 1842, "ball": "15.4", "at": "2026-09-27T03:16:44.1Z"}
```
```m3u8
#EXT-X-PROGRAM-DATE-TIME:2026-09-27T03:16:44.365+0000
```

> 💡 **Two polling loops, one clock.** This is why `EXT-X-PROGRAM-DATE-TIME` exists.

---

## 📶 ABR: the player picks the next rendition

> Session 7 asked: *every fallback gives you something worse than ideal. When does worse stop
> being acceptable, and who decides?*
> ⭐ **The player decides, at every segment, under a policy the product sets.**

| **Throughput-based** | **Buffer-based** |
|---|---|
| Measure how fast the last segments arrived; pick the highest rendition that fits. ⭐ **Congestion control, one layer up.** | Watch the buffer: nearly empty → step down; full → step up. **Netflix's A/B tests: 10–20% fewer rebuffers at a similar video rate.** |

> ⭐ **The policy: a stall is worse than a lower rendition.**
> **Even the default is policy** — Apple suggests starting **cellular** viewers on the 730 kbps
> variant and **Wi-Fi** viewers on 2 Mbps.

---

## 🌐 Many origins, many CDNs

```
Android app ──▶ CDN A edge ──▶ CDN A mid-tier ──▶ Origin 1 (packager A)
                 primary        shields origin         │  same
            ──▶ CDN B edge ──▶ CDN B mid-tier ──▶ Origin 2 (packager B)
                 fallback       shields origin         │  names
```

| | |
|---|---|
| **DNS** | Hand out a CDN per region or ISP. ⚠️ **Slow to change: resolvers cache.** |
| **Listed twice** | The master lists **each rendition once per CDN**, for stream failover. |
| **Content Steering** | ⭐ A JSON file, polled every TTL, **names the preferred CDN**. |
| **Client failover** | Errors on one CDN **trip a circuit breaker**; the next segment tries the other (Session 7). |

---

## 🧟 Stale playlists and deleted segments

**The failure chain, observed in a real ffmpeg run:**

1. ffmpeg's `delete_segments` keeps **one** unreferenced segment; `seg_000000` vanished **4 s
   after it left the playlist**.
2. ⚠️ RFC 8216 says a removed segment **MUST stay for its duration plus the playlist's**:
   `4 + 40 = 44 s` here.
3. During an origin blip the CDN **serves a stale playlist**. It still lists a segment the
   origin has **deleted**.
4. ⚠️ **404, negatively cached, and the player stalls.** ⭐ *"Serve stale may cause player
   issues."*

```text
t = 47.0 s   playlist: seg_000001 … seg_000010   on disk: seg_000000 … seg_000010
t = 51.5 s   playlist: seg_000002 … seg_000011   on disk: seg_000001 … seg_000011
```

**Fixes:**

- `-hls_delete_threshold 12`
- **Playlist TTL at ½ target duration or less**; serve it stale **for one target duration at
  most**
- ⭐ **Segments never change: serve them stale freely**
- Apple: treat a playlist as **invalid when `Last-Modified` is more than 3 target durations
  behind `Date`**

---

## ⚙️ Caching rules for a live stream

| Object | TTL | Serve stale | 404 |
|---|---|---|---|
| `master.m3u8` | minutes | yes | 1 s |
| **media playlist** | ⚠️ ≤ target duration | **one target duration at most** | 1 s, or not at all |
| **segment `.ts`** | ⭐ **long: it never changes** | yes | 1 s at most, at the live edge |
| `score.json` | ≤ ⅓ your promise | while updating | 1 s (5xx: 2 s) |

```nginx
location ~ \.m3u8$ { proxy_cache_valid 200 2s;  proxy_cache_lock on;
                     proxy_cache_use_stale updating; }
location ~ \.ts$   { proxy_cache_valid 200 10m; proxy_cache_valid 404 1s; }

gzip_types application/vnd.apple.mpegurl application/json;
```

> ⭐ **Also: gzip every playlist** (Apple says **MUST**), and **keep per-viewer tokens out of
> the cache key**.

---

## 🎛️ Making the stream with ffmpeg

### From an mp4: the one-liner

```bash
ffmpeg -re -i input.mp4 -codec: copy -hls_time 4 -hls_list_size 5 \
       -hls_playlist_type event -f hls index.m3u8
```

| Flag | What it does |
|---|---|
| `-re` | read at native speed: **a file pretending to be a camera** |
| `-codec: copy` | no re-encode, ⚠️ **so it can only cut at existing keyframes** |
| `-hls_time 4` | a **target** segment length, **not a promise** |
| `-hls_list_size 5` | a 5-segment window, unless… |
| `-hls_playlist_type event` | …the playlist is **append-only** |

> ⚠️ **What running it actually showed:**
> **8.33 s segments, not 4.** x264's default keyframe interval is **250 frames = 8.33 s at 30
> fps**. ⭐ **A segment can only start on a keyframe.**
> **The window was ignored** — an `EVENT` playlist only grows: **11 segments listed at the
> end**.

💡 **For real:** camera → RTMP or SRT → transcoder → packager → origin → CDN.

### The ABR ladder

```bash
ffmpeg -re -stream_loop -1 -i input.mp4 \
  -filter_complex "[0:v] split=3[v720][v480][v360]; …scale+pad…; [0:a]asplit=3[a0][a1][a2]" \
  -map "[v720o]" -map "[a0]" -map "[v480o]" -map "[a1]" -map "[v360o]" -map "[a2]" \
  -c:v libx264 -preset veryfast -profile:v main -sc_threshold 0 -g 120 -keyint_min 120 \
  -c:a aac -ac 2 -ar 48000 \
  -b:v:0 3000k -maxrate:v:0 3210k -bufsize:v:0 4500k -b:a:0 128k \
  -b:v:1 1500k -maxrate:v:1 1605k -bufsize:v:1 2250k -b:a:1  96k \
  -b:v:2  800k -maxrate:v:2  856k -bufsize:v:2 1200k -b:a:2  64k \
  -f hls -hls_time 4 -hls_list_size 10 \
  -hls_flags independent_segments+delete_segments+omit_endlist+program_date_time \
  -hls_segment_filename "out/stream_%v/seg_%06d.ts" -master_pl_name master.m3u8 \
  -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2" "out/stream_%v/index.m3u8"
```

| | |
|---|---|
| `split=3` | ⭐ **decode once, encode three times** — *amortise the setup* (Session 3) |
| `-g 120` | **4 s at 30 fps only.** ⚠️ A 24 fps source gave **5 s** segments. |
| `-hls_flags …` | a 40 s window that never ends, **stamped with wall-clock time** |

---

## 🧵 The whole course in one cricket match

| | |
|---|---|
| **Week 1 — Sockets** | Ports are 16 bits: **28k test sockets per client IP**. Base64 in the WebSocket handshake. |
| **Week 2 — Wire** | Framing: SSE's blank line, WebSocket lengths, 188-byte packets. **Playlists as control, segments as data.** |
| **Week 3 — Scale** | Fifty million held sockets, **Little's Law**, and nothing free per connection. |
| **Week 4 — nginx** | The origin: `proxy_cache_lock`, `use_stale`, **one `location` per file type**. |
| **Week 5 — HTTP** | ETag and 304, keep-alive, 101 Upgrade, and **push's death shaping LL-HLS**. |
| **Week 6 — CDNs** | Tiers, collapsing, negative caching, and **paying per request or per byte**. |
| **Week 7 — Failures** | Jitter, the live-edge 404, `stale-if-error`, failover, and **who decides "worse"**. |
| **Week 8 — Video** | **HLS: a playlist, polled like a scorecard, pointing at bytes that never change.** |

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Polling / long polling** | Ask every N seconds / ask once and let the server hold it open |
| **SSE** | One never-ending response; events delimited by a **blank line**; `Last-Event-ID` resumes |
| **WebSocket** | `101 Switching Protocols`, then **length-framed** bidirectional frames; client frames **masked** |
| **MQTT** | Topic pub/sub via a broker; **retained message** = a cache inside the broker; QoS 1 = at-least-once |
| **Little's Law here** | ⭐ Polling ≈ 50k in flight; push = **50M held sockets** — W went from ms to hours |
| **Negative caching** | Short TTLs on 404/5xx; ⚠️ **a negative TTL must be shorter than the time the thing takes to appear** |
| **Request collapsing** | One upstream fetch; ⚠️ needs a **`public`, shareable** first response |
| **Prefresh** | Refresh the edge copy **before** the TTL expires |
| **HLS** | Master playlist → media playlist → numbered segments |
| **`EXT-X-TARGETDURATION`** | Max segment length; also the **playlist reload interval** |
| **`EXT-X-MEDIA-SEQUENCE`** | The sequence number of the first segment listed |
| **`EXT-X-PROGRAM-DATE-TIME`** | ⭐ Wall-clock time of a segment — what fixes the spoiler problem |
| **`EXT-X-ENDLIST`** | VOD: no more segments, stop polling |
| **MPEG-TS packet** | **188 bytes**: 4-byte header (sync `0x47`, 13-bit PID, counter) + 184 payload |
| **CMAF / fMP4** | Box-based segments — size, type, payload (**TLV**) |
| **Hold-back** | Player stays **3 × target duration** behind the live edge |
| **LL-HLS** | Parts · blocking reload · preload hints · `EXT-X-SKIP` delta updates |
| **ABR** | Throughput-based vs **buffer-based** rendition selection |
| **Content Steering** | A polled JSON file naming the preferred CDN |
| **Break-even ≈ 11 KB** | Below it you pay **per request**; above it **per byte** |

---

## 🎯 Session Takeaways

1. ⭐ **Pull scales through caches; push scales through machines.** The same answer for everyone belongs in a CDN. **A different answer per person means you are buying sockets.**
2. ⭐ **Number the pieces, then cache them forever.** A small changing index plus numbered pieces that never change — **the versioned scorecard and the HLS playlist are one design**.
3. ⭐ **Latency is a budget you spend on safety.** Poll intervals, TTLs, segment length and hold-back all add up. **Decide where each second goes.**
4. ⭐ **Know which bill you are on.** Below ~11 KB you pay **per request**; above it **per byte**. Scorecards and playlists are the first kind; segments the second.
5. **A held socket costs a machine slot for four hours** — Little's Law turns the same audience into a thousand times the concurrency.
6. **Do the arithmetic before the architecture.** 9.6 B requests and 9.6 TB per match; ×100 events a year.
7. ⚠️ **S3 runs out of requests before it runs out of your money** — 5,500 GET/s per prefix vs 1.67 M/s needed, and then it's a 503 retry storm at your own bucket.
8. **304 saves the body, not the request fee or the round trip** — it pays most **between CDN tiers**.
9. ⭐ **Worst-case staleness = poll interval + every TTL on the path.** Keep each at ⅓ of what you promise, and **prefresh**.
10. **Request collapsing only works if the first response is shareable** — one stray `Set-Cookie` dequeues 20,000 waiters one at a time.
11. ⚠️ **Never negatively cache a live-edge 404 for long.** The segment is about to exist.
12. **A stale *playlist* stalls the player; a stale *segment* is harmless.** Cache them completely differently.
13. ⭐ **A segment can only start on a keyframe** — which is why `-hls_time 4` gave 8.33 s segments until `-g` was set.
14. **The buffer is the stale cache**, and `EXT-X-PROGRAM-DATE-TIME` is what stops the scorecard spoiling the video.
15. ⭐ **ABR is Session 7's "who decides worse?" answered every four seconds** — and *a stall is worse than a lower rendition* is a product policy, not a technical fact.
16. **LL-HLS is this course's greatest hits:** long polling, preload hints replacing push, and delta updates.

---

## 🔗 References

- RFC 8216 — HTTP Live Streaming — https://www.rfc-editor.org/rfc/rfc8216
- Apple, HLS Authoring Specification — https://developer.apple.com/documentation/http-live-streaming/hls-authoring-specification-for-apple-devices
- Apple, Low-Latency HLS — https://developer.apple.com/documentation/http-live-streaming/enabling-low-latency-http-live-streaming-hls
- MPEG-DASH / CMAF — ISO/IEC 23009-1, 23000-19
- RFC 6455 — The WebSocket Protocol — https://www.rfc-editor.org/rfc/rfc6455
- WHATWG — Server-Sent Events — https://html.spec.whatwg.org/multipage/server-sent-events.html
- MQTT 5.0 — https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
- Chaudhari & Gupta, *Building Pubsub for 50M concurrent socket connections*, Hotstar Engineering, 6 Jun 2019
- Huang et al., *A Buffer-Based Approach to Rate Adaptation*, SIGCOMM 2014 — https://dl.acm.org/doi/10.1145/2619239.2626296
- Amazon S3 — Best practices design patterns — https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html
- RFC 5861 — `stale-while-revalidate` / `stale-if-error`
- RFC 6902 — JSON Patch — https://www.rfc-editor.org/rfc/rfc6902
- ffmpeg HLS muxer — https://ffmpeg.org/ffmpeg-formats.html#hls-2
- HLS Content Steering — https://developer.apple.com/streaming/HLSContentSteeringSpecification.pdf

---

## 🏁 End of the course

```
01 Sockets      → the seven syscalls everything else wraps
02 Wire         → encapsulation, framing, and a second internet
03 Scale        → the loop is the architecture
04 nginx        → and the code that explains it
05 HTTP         → three encodings, one language
06 CDNs         → someone else's computers, closer to your users
07 Failures     → classify, back off, break the circuit, degrade
08 Video        → all of the above, on fifty million phones
```

⬅️ Back to the [Network Architecture index](./README.md).
