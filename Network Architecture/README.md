# Network Architecture Notes 🌐

Detailed study notes for the **8-session Network Architecture** course — *CN at Scaler*.
One markdown file per session, built bottom-up: from a twenty-line C socket server to one live
cricket match on fifty million phones.

**Source material:** the eight *CN at Scaler* lecture decks, plus the course syllabus.
Where a slide was thin, wrong or ambiguous, the notes say so and give the correct version.

---

## 📚 Sessions

| # | Session | Topics covered |
|---|---|---|
| **01** | [Network Programming 101](./01_Network_Programming_101.md) | The seven syscalls · Ports & privilege · The accept queue · SIGPIPE · telnet/nc/openssl · Ephemeral ports · Byte order · DNS in a function call · fork vs select/epoll · tcpdump · TLS · Framing · BCD · ASN.1 · TLV · RPC · gRPC |
| **02** | [Computer Networking: Eagle Eye View](./02_Computer_Networking_Eagle_Eye_View.md) | OSI L1–L7 · CSMA/CA vs CD · Starlink as a physical layer · **SS7** · Encapsulation · Why an SMS is 140 bytes · GSM-7 · ISUP & SIP · BBR · TCP handshake & teardown · SYN cookies · The RTT tax · UDP · QUIC · SMTP · MIME · POP3 · IMAP · FTP |
| **03** | [Server Side Considerations for Scale](./03_Server_Side_Considerations_for_Scale.md) | fork vs thread vs event loop · `select` & `epoll` · Timeouts · **CGI & FastCGI** · Servlets · Four walls (fds, memory, context switches, queue) · C10K · **Little's Law** · Apache · HAProxy · Varnish · nginx |
| **04** | [nginx Deep Dive](./04_Nginx_Deep_Dive.md) | A corrected lineage · Apache's decade chasing `fork()` · Process model · **The loop in six lines** · `accept_disabled` · The stale-event bug · **`sendfile`** · Reverse proxy · Caching · `location` precedence · Smooth WRR · `try_files` · Reading the source |
| **05** | [Evolution of HTTP](./05_Evolution_of_HTTP.md) | HTTP/1.0 · Persistence & `Host` · ETags · `Vary` · `Range` · Chunked encoding · Request smuggling · Head-of-line blocking · Header bloat · Nagle · **HTTP/2** · HPACK · CRIME · Server push's death · **QUIC** · 0-RTT · Connection migration · QPACK |
| **06** | [(Ab)using CDNs](./06_Abusing_CDNs.md) | The speed-of-light budget · **Consistent hashing** · Anycast · `cf-cache-status` · SSI/ESI/Ajax/Railgun · Cache poisoning & deception · BBR · **Connection pooling** · Request collapsing & tiered cache · WAF · Rate limiting · DDoS · API gateway · Workers · What you hand over |
| **07** | [Building for Failures](./07_Building_for_Failures.md) | Failure taxonomy · What a retry *is* · Idempotency · **Backoff & full jitter** · `Retry-After` · **Circuit breakers** · A video player's 96 failure modes · Fallback vs retry · Failover & graceful degradation · `stale-if-error` · The herd on recovery |
| **08** | [Streaming Video at Large Scale](./08_Streaming_Video_at_Large_Scale.md) | Polling vs push · SSE · WebSockets · MQTT · The cost of a held socket · **Little's Law twice** · Stacked TTLs · Negative caching · **HLS** · 188-byte packets · Segment length · Buffers · LL-HLS · The spoiler problem · ABR · Multi-CDN · ffmpeg |

---

## 🗺️ How the sessions connect

```
  01 Sockets                   ← the seven syscalls everything else wraps
        │
        ▼
  02 Eagle eye view            ← encapsulation, framing, and a second internet (SS7)
        │                        TCP/UDP/QUIC · SMTP/POP3/IMAP/FTP
        ▼
  03 Scaling servers           ← one box, ten thousand clients
        │                        select → epoll · CGI → FastCGI · Little's Law
        ▼
  04 nginx deep dive           ← the server that got there first, read properly
        │
        ▼
  05 Evolution of HTTP         ← 1.0 → 1.1 → 2 → 3, and why each fix caused the next
        │
        ▼
  06 (Ab)using CDNs            ← put a network in front of the origin
        │
        ▼
  07 Building for failures     ← what happens when a piece of it breaks
        │
        ▼
  08 Streaming video           ← all of it at once, on fifty million phones
```

**The thread that runs through all eight:**

> A socket is seven system calls. A protocol is **framing plus identity**. A server is **an
> event loop plus a small pool of workers**. A fast system is one that **amortises setup** and
> **never does the same work twice**. And a system that survives is one that can **answer with
> something worse rather than nothing**.

---

## 🔁 Ideas that reappear across sessions

| Idea | First seen | Comes back as |
|---|---|---|
| **Framing: length or delimiter** | 01 — fixed / delimited / length-prefixed | SMS `TP-UDL` & SMTP's lone dot (02) · FastCGI records (03) · chunked encoding (05) · WebSocket lengths & SSE blank lines (08) |
| **Multiplexing needs identity** | 01 — ports | SS7 transaction ids (02) · FastCGI `requestId` (03) · ⭐ HTTP/2 stream ids (05) · QUIC stream ids (05) |
| **Amortise the setup** | 03 — prefork, FastCGI | upstream keepalive (04) · connection pools & Pingora (06) · V8 isolates (06) · `split=3` in ffmpeg (08) |
| **The event loop** | 03 — select/epoll | nginx's six lines (04) · Varnish's waiter, Apache's event MPM (03) |
| **Encapsulation** | 02 — Ethernet→IP→TCP→HTTP | MTP2→…→TPDU (02) · MPEG-TS packets inside segments (08) |
| **Caching & staleness** | 04 — `proxy_cache` | `cf-cache-status` (06) · `stale-if-error` (07) · playlist vs segment TTLs (08) |
| **The thundering herd** | 03/04 — `proxy_cache_lock` | request collapsing & tiered cache (06) · recovery storms (07) · TTL expiry (08) |
| **Jitter** | 07 — full jitter | ±20% poll jitter across 50M phones (08) |
| **Head-of-line blocking** | 05 — pipelining | TCP's version under HTTP/2 (05) · solved by QUIC stream offsets (05) |
| **Control vs data planes** | 02 — SS7 out-of-band signalling | SIP + RTP (02) · FTP's two connections (02) · playlists vs segments (08) |
| **Round trips are the tax** | 02 — TCP/TLS handshakes | TLS 1.3, TFO, QUIC (05) · the 126 ms Mumbai↔Virginia floor (06) |
| **"Worse beats nothing"** | 07 — graceful degradation | serve stale (06, 07) · lower bitrate via ABR (08) |
| **base64 / the 64-char alphabet** | 01 — debugging binary | MIME (02) · JWTs and `tchar` (05) · the WebSocket `Accept` (08) |

---

## ⭐ Highest-value takeaway per session

| # | If you only remember one thing |
|---|---|
| **01** | **A TCP server is `socket → bind → listen → accept → read → write → close`.** Every framework wraps that sequence — and **TCP is a byte stream, not messages**, so you must pick a framing strategy. |
| **02** | **One layer's headers are another layer's body.** `Ethernet→IP→TCP→HTTP` is the same picture as `MTP2→MTP3→SCCP→TCAP→MAP→TPDU`. **Reliability and framing each have an address — the only argument is which layer owns them.** |
| **03** | **The loop is the architecture.** Four teams, thirty years apart, all converged on an event loop plus a small worker pool. And **concurrency = throughput × latency**: slowness is a memory bug. |
| **04** | **Ask the other question.** Apache spent a decade making the worker cheaper; nginx asked why there was one. **The data structure is the documentation** — prefixes are a tree, regexes are an array. |
| **05** | **Multiplexing needs identity.** HTTP/1.1 had no request id, so order became the identifier. **Every fix is the next problem**, and **semantics (RFC 9110) outlive encodings (9112/9113/9114)**. |
| **06** | **The speed of light is a fixed budget** — a cache MISS through the edge is no faster than going direct. The edge earns its keep by **warm connections** and **deleting the origin round trip**. |
| **07** | **Classify before you retry.** A timeout means *"I don't know"*, not *"it didn't happen"*. **Full jitter**, cap attempts, honour `Retry-After`, and **the most dangerous moment is recovery**. |
| **08** | **Pull scales through caches; push scales through machines.** Number the pieces and cache them forever — **the versioned scorecard and the HLS playlist are one design**. |

---

## 📌 Conventions used in these notes

| Marker | Meaning |
|---|---|
| ⭐ | The thing most worth remembering / the most common exam or interview point |
| ⚠️ | A trap, a gotcha, or something that will cost you money, data or an outage |
| 🐛 | A genuine bug or inconsistency **in the source material**, with the fix |
| 💡 | Useful context, an analogy, or something slightly beyond the slides |
| 📍 | A file and function name in a real codebase you can go and read |

Each file follows the same shape: **Topics + source → Table of Contents → content →
Key Terms Recap → Session Takeaways → References → Next**.

---

## 🔗 Key references

- Beej's Guide to Network Programming — https://beej.us/guide/bgnet/
- The C10K problem — http://www.kegel.com/c10k.html
- nginx source & docs — https://github.com/nginx/nginx · https://nginx.org/en/docs/
- RFC 9110 (HTTP Semantics) — https://www.rfc-editor.org/rfc/rfc9110
- RFC 9000 (QUIC) — https://www.rfc-editor.org/rfc/rfc9000
- RFC 8216 (HLS) — https://www.rfc-editor.org/rfc/rfc8216
- Karger et al., *Consistent Hashing*, STOC 1997
- Cardwell et al., *BBR*, ACM Queue 2016 — https://queue.acm.org/detail.cfm?id=3022184
- AWS, *Exponential Backoff and Jitter* — https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- Google SRE Book — https://sre.google/sre-book/table-of-contents/
- Hotstar, *Building Pubsub for 50M concurrent socket connections* (2019)
- Apple HLS Authoring Specification — https://developer.apple.com/documentation/http-live-streaming/
