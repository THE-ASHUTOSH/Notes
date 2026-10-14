# Session 5 — Evolution of HTTP 🌐

> **Topics:** HTTP/1.0 · Persistence & `Host` · ETags · `Vary` · `Range` · Chunked encoding ·
> The 2-connection rule · RFC 2616 → 7230 → 9110 · Request smuggling · Head-of-line blocking ·
> Header bloat · Nagle · HTTP/2 · HPACK · CRIME · Server push · QUIC · 0-RTT · Connection
> migration · QPACK · Alt-Svc
>
> 📄 Source: *CN at Scaler — Lesson 5*, "HTTP, 1996 → now".
> RFC 1945 → 2068 → 2616 → 7230 → 9110 → 9113 → 9000 → 9114.

> ⭐ **Same words. Three completely different ways of writing them down.**
> The protocol did not drift — **it was pushed.**

---

## 📑 Table of Contents

1. [HTTP/1.0 — the whole protocol on one slide](#-http10--the-whole-protocol-on-one-slide)
2. [Speak it by hand, once](#-speak-it-by-hand-once)
3. [One response. Then the socket dies](#-one-response-then-the-socket-dies)
4. [No `Host` header. One IP, one website](#-no-host-header-one-ip-one-website)
5. [Caching, with a clock as the fingerprint](#-caching-with-a-clock-as-the-fingerprint)
6. [What HTTP/1.0 could not do](#-what-http10-could-not-do)
7. [Persistence became the default](#-persistence-became-the-default)
8. [`Host:` — the same move, four layers, thirty years](#-host--the-same-move-four-layers-thirty-years)
9. [ETag — a fingerprint, not a clock](#-etag--a-fingerprint-not-a-clock)
10. [`Accept-*` and `Vary`](#-accept--and-vary)
11. [`Range` — the header that runs your data lake](#-range--the-header-that-runs-your-data-lake)
12. [Chunked encoding](#-chunked-encoding)
13. [And the rest of it, in one breath](#-and-the-rest-of-it-in-one-breath)
14. ["SHOULD NOT maintain more than 2 connections"](#-should-not-maintain-more-than-2-connections)
15. [1999: mostly tightening, and why 307 exists](#-1999-mostly-tightening-and-why-307-exists)
16. [Watch Postel's law lose an argument](#-watch-postels-law-lose-an-argument)
17. [Request smuggling](#-request-smuggling)
18. [One document became six](#-one-document-became-six)
19. [Why your JWT is base64](#-why-your-jwt-is-base64)
20. [Semantics vs wire format — and a teapot](#-semantics-vs-wire-format--and-a-teapot)
21. [Head-of-line blocking, measured](#-head-of-line-blocking-measured)
22. [There is no request id on the wire](#-there-is-no-request-id-on-the-wire)
23. [97.5% of what you upload is a repeat](#-975-of-what-you-upload-is-a-repeat)
24. [When keep-alive made it slower](#-when-keep-alive-made-it-slower)
25. [The bill for HTTP/1.1](#-the-bill-for-http11)
26. [HTTP/2: ship it to a billion users, then standardise](#-http2-ship-it-to-a-billion-users-then-standardise)
27. [The connection preface](#-the-connection-preface)
28. [Nine bytes, and 31 of them are the answer](#-nine-bytes-and-31-of-them-are-the-answer)
29. [Ten frame types](#-ten-frame-types)
30. [HPACK: 174 → 79 → 6 bytes](#-hpack-174--79--6-bytes)
31. [CRIME — why not just gzip the headers?](#-crime--why-not-just-gzip-the-headers)
32. [Multiplexing, measured](#-multiplexing-measured)
33. [A protocol can only give you permission](#-a-protocol-can-only-give-you-permission)
34. [Server push: nobody deprecated it, everybody removed it](#-server-push-nobody-deprecated-it-everybody-removed-it)
35. [The one thing HTTP/2 could not fix](#-the-one-thing-http2-could-not-fix)
36. [QUIC: why UDP](#-quic-why-udp)
37. [One handshake, not two](#-one-handshake-not-two)
38. [0-RTT, and the price of it](#-0-rtt-and-the-price-of-it)
39. [Head-of-line blocking, gone](#-head-of-line-blocking-gone)
40. [Connection IDs — surviving a network change](#-connection-ids--surviving-a-network-change)
41. [QPACK](#-qpack)
42. [Discovery and fallback](#-discovery-and-fallback)
43. [Where the web actually is](#-where-the-web-actually-is)
44. [Key Terms Recap](#-key-terms-recap)
45. [Session Takeaways](#-session-takeaways)

---

## 📜 HTTP/1.0 — the whole protocol on one slide

**RFC 1945, May 1996.**

| Methods | Status codes |
|---|---|
| `GET` `HEAD` `POST` | **2xx** 200 OK · 201 Created · 202 Accepted · 204 No Content |
| `PUT` `DELETE` `LINK` `UNLINK` *(Appendix D: "additional methods" that exist but are not in the spec)* | **3xx** 300 · 301 Moved Permanently · 302 Moved Temporarily · 304 Not Modified |
| | **4xx** 400 · 401 · 403 · 404 |
| | **5xx** 500 · 501 · 502 · 503 |

**Sixteen headers, total:** `Allow` `Authorization` `Content-Encoding` `Content-Length`
`Content-Type` `Date` `Expires` `From` `If-Modified-Since` `Last-Modified` `Location`
`Pragma` `Referer` `Server` `User-Agent` `WWW-Authenticate`.

> 💡 **Today: 62 assigned status codes** (IANA, Sep 2025).

---

## 🗣️ Speak it by hand, once

```text
$ printf 'GET / HTTP/1.0\r\n\r\n' | nc localhost 8010

HTTP/1.0 200 OK
Date: Fri, 04 Sep 2026 07:11:27 GMT
Server: server10/1.0 (RFC 1945)
Content-Type: text/html
Content-Length: 263
Last-Modified: Fri, 04 Sep 2026 07:11:14 GMT
Expires: Fri, 04 Sep 2026 07:12:27 GMT
                                    ← the blank line is the delimiter
<!doctype html>
<title>site-a</title>
...
--- server closed the connection (FIN) at 2.9 ms
```

> ⭐ **Not `curl`.** curl adds four headers you did not write and hides two the server sent.
> Use a raw socket at least once.

---

## ☠️ One response. Then the socket dies

> **RFC 1945 §1.3:** *"current practice requires that the connection be established by the
> client prior to each request and closed by the server after sending the response."*

```python
s.sendall(b"GET /style.css HTTP/1.0\r\n\r\n")
r1 = recv_until_eof(s)        # 274 bytes, server sent FIN

s.sendall(b"GET /app.js HTTP/1.0\r\n\r\n")   # same socket
r2 = s.recv(4096)             # b''
```

⚠️ **Nothing. Not an error — an empty read.** The connection was closed the moment the first
response finished.

**The arithmetic, on a 24-object page at 200 ms RTT:**

```
24 TCP handshakes     = 4.8 s
24 request/response   = 4.8 s
                      ───────
                        9.6 s      …and 24 congestion windows that each start from nothing
```

---

## 🏠 No `Host` header. One IP, one website

```text
$ talk.py 8010 --req "GET / HTTP/1.0" "Host: site-b.example" ""

HTTP/1.0 200 OK
<h1>site-a</h1>              ← not site-b. it never had a choice.

# server log: (ignoring Host: site-b.example — HTTP/1.0 has no vhosts)
```

| **1 : 1** | **~1.1 B** | **SNI** |
|---|---|---|
| sites per IP address, until **January 1997** | websites today — ⚠️ **a third of all of IPv4** would be needed | the **same problem one layer down**, once TLS hid the `Host` |

> ⭐ **The fix — a single header field — arrives nine months later and is arguably the
> highest-leverage line in the whole standard.**

---

## 🕐 Caching, with a clock as the fingerprint

```text
$ talk.py 8010 --req "HEAD /style.css HTTP/1.0" ""
Last-Modified: Fri, 04 Sep 2026 07:11:14 GMT

$ talk.py 8010 --req "GET /style.css HTTP/1.0" \
      "If-Modified-Since: Fri, 04 Sep 2026 07:11:14 GMT" ""

HTTP/1.0 304 Not Modified     ← no body. 202,000 bytes → 0.
```

**Three things wrong with a timestamp:**

| **1 s drift** | **Clock skew** | **mtime ≠ identity** |
|---|---|---|
| No sub-second field. ⚠️ **Two writes in one second are one write to every cache alive.** | Your clock, my clock, the proxy's clock. The spec has to legislate for disagreement. | ⚠️ **A rebuild changes every mtime and none of the bytes.** |

---

## 🧾 What HTTP/1.0 could not do

| The limitation | Concretely | Fixed in |
|---|---|---|
| Connection is not persistent | One request per TCP handshake, forever | RFC 2068 §8.1 |
| Sixteen headers, three methods | No `OPTIONS`: you cannot ask what a server supports | RFC 2068 §9.2 |
| Caching exists but is thin | `Expires` + `If-Modified-Since`. A clock, not a fingerprint | RFC 2068 §14.19 |
| **No `Host`** | One IP address per website | RFC 2068 §14.23 |

> ⚠️ **One correction.** HTTP/1.0 is usually listed as having *head-of-line blocking*. It does
> not, quite. **Head-of-line blocking needs a queue**, and HTTP/1.0 has no pipelining to queue
> anything on. What it has is a **serialisation cost**: one round trip per object, no
> exceptions.

> ⭐ **Real head-of-line blocking arrives in HTTP/1.1, as a side effect of the fix for this.
> Watch for that pattern all day — every solution today is the cause of the next slide.**

---

## 🔗 Persistence became the default

**RFC 2068, January 1997.**

| **HTTP/1.0** | **HTTP/1.1** |
|---|---|
| `Connection: keep-alive` — *ask, and maybe receive* | `Connection: close` — *opt out* |
| A **non-standard extension**. Some servers honoured it, some ignored it, ⚠️ **some crashed**. Documented in §19.7.1 as a compatibility note, **not a feature**. | *"persistent connections are the **default behavior** of any HTTP connection."* |
| **The default was: hang up.** | ⭐ **Every implementation that did nothing at all got the fast path.** The default was: **stay**. |

```text
/           HTTP/1.1 200 OK    socket still open: True
/style.css  HTTP/1.1 200 OK    socket still open: True
/app.js     HTTP/1.1 200 OK    socket still open: True
                               ← three responses, one TCP handshake
```

> ⭐ **Keeping the connection open forces a question HTTP/1.0 never asked:** *where does this
> request end and the next one begin?* While you were hanging up, the answer was **"at EOF"**,
> for free. Now you must consume **exactly `Content-Length` bytes and not one more** — byte
> *n+1* belongs to somebody else.

---

## 🏷️ `Host:` — the same move, four layers, thirty years

```text
$ talk.py 8011 --req "GET / HTTP/1.1" ""      # no Host
HTTP/1.1 400 Bad Request

$ ... "Host: site-a.local"  →  <h1>site-a</h1>
$ ... "Host: site-b.local"  →  <h1>site-b</h1>
       same IP. same port. same socket.
```

| Layer | The problem | The fix |
|---|---|---|
| **HTTP/1.0** | The four-tuple was the address; one IP = one site | **`Host:`** — put the name **in the message** |
| **TLS** | `Host` is encrypted; the cert must be chosen first | **SNI** in the ClientHello, in the clear |
| **HTTP/2** | Headers are compressed and unordered | **`:authority`** as a pseudo-header |
| **Everywhere else** | Many logical destinations, one connection | Topic. Routing key. Ingress host rule. |

⭐ **Same move, four times.** When one pipe must serve many logical destinations, **the
destination has to travel inside the message.**

---

## 🔐 ETag — a fingerprint, not a clock

```text
$ talk.py 8011 --req "HEAD /big.txt HTTP/1.1" "Host: site-a.local" ""
ETag: "55274ac22c651b90"          ← sha256 of the bytes, first 16 hex

$ talk.py 8011 --req "GET /big.txt HTTP/1.1" \
      "Host: site-a.local" "If-None-Match: \"55274ac22c651b90\"" ""

HTTP/1.1 304 Not Modified
--- received 256 bytes            ← 202,000 bytes of body became 0
```

| | |
|---|---|
| **`W/"..."`** | A **weak** validator: *equivalent*, not *identical*. ⚠️ **Range requests need a strong one.** |
| **`If-Match`** | The same idea pointed at **writes**: optimistic concurrency, and the fix for lost updates. |

---

## 🗜️ `Accept-*` and `Vary`

```text
Accept-Encoding: identity  →  Content-Length: 202000
Accept-Encoding: gzip      →  Content-Length:   5763      ← 2.8% of original
Accept-Encoding: deflate   →  Content-Length:   5751
```

> ⭐ **Which quietly undercuts "HTTP/1.1 is slow because it is text".** Text compresses. **The
> body was never the problem — the headers were**, because `Content-Encoding` compresses the
> **body only**.

**`Vary` is a cache-key instruction.** It says: *this URL has more than one answer, and here is
what the answer depends on.*

| | |
|---|---|
| `Vary: Accept-Encoding` | ✅ correct |
| `Vary: User-Agent` | ⚠️ **millions of keys, hit rate ≈ 0** |
| `Vary: *` | ⚠️ **caching off entirely** |

---

## 📏 `Range` — the header that runs your data lake

```text
Range: bytes=100-199   →  HTTP/1.1 206 Partial Content
                          Content-Range: bytes 100-199/202000

Range: bytes=-50       →  Content-Range: bytes 201950-201999/202000
                          the last 50 bytes, size not known in advance

Range: bytes=999999-   →  HTTP/1.1 416 Range Not Satisfiable
                          Content-Range: bytes */202000
```

**What one header bought:**

| **Video scrubbing** | **Resumable downloads** | **Parquet / ZIP footers** |
|---|---|---|
| The player asks for the bytes **around the timestamp you clicked** — not the film. | Died at 60%? `Range: bytes=600000000-` and carry on. | ⭐ The directory is at the **end**. Read the last few KB, then fetch **only the columns you need**. |

> 💡 `416` was not in RFC 2068 — RFC 2616 added it to separate *"your syntax is wrong"* from
> *"that file is smaller than you think"*.

---

## 🧩 Chunked encoding

```http
HTTP/1.1 200 OK
Content-Type: text/css
Transfer-Encoding: chunked
                                   ← and NO Content-Length

37
body{font-family:monospace;background:#111;color:#eee}
0
                                   ← 0x37 = 55 bytes, then the empty chunk
```

> ⭐ [Session 2](./02_Computer_Networking_Eagle_Eye_View.md)'s closing idea: **framing is length
> or delimiter — there is no third option.** Chunked encoding is **both, nested**: each chunk
> is length-prefixed, and the sequence is delimited by an **empty one**.

**That is FastCGI's record structure from [Session 3](./03_Server_Side_Considerations_for_Scale.md),
exactly.** Same shape, different decade — and it is what **streaming JSON, server-sent events
and gRPC trailers** are all standing on.

---

## 🎁 And the rest of it, in one breath

| Arrival | What it is for | Where you meet it now |
|---|---|---|
| **`OPTIONS`** | Ask what a server supports | Every **CORS preflight** your browser sends |
| **`PUT` · `DELETE`** | Write and remove, not just read | The R and D of every REST API since |
| `TRACE` | Echo my request back, proxies and all | ⚠️ **Disabled everywhere** — Cross-Site Tracing, 2003 |
| `Via` | Each proxy appends itself | Working out **which box in the chain is lying** |
| `Expect: 100-continue` | Ask before uploading four gigabytes | curl's mysterious 1-second pause on big PUTs |
| **`Cache-Control`** | A **vocabulary** instead of one timestamp | `max-age`, `s-maxage`, `no-cache`, `no-store` |
| ~40 status codes | 303, 405, 409, 410, 412, 413, 415, 504… | 504 is **already here** — not a 1999 addition |

> ⚠️ **`no-cache` means *revalidate before use*. `no-store` means *do not write it down*.
> Everybody gets this wrong exactly once.**

---

## 🔢 "SHOULD NOT maintain more than 2 connections"

**RFC 2068 §8.1.4.** Six assets, RTT 150 ms:

| Mode | Bytes | Round trips | TCP conns | Wall ms |
|---|---|---|---|---|
| close (HTTP/1.0) | 4867 | 12 | 6 | **1369.2** |
| keepalive (1 conn) | 5095 | 7 | 1 | 985.4 |
| parallel2 (RFC says) | 5095 | 4 | 2 | 607.0 |
| parallel6 (browsers) | 5095 | 2 | 6 | 608.2 |
| **pipelined (1 batch)** | 5095 | **2** | **1** | ⭐ **303.7** |

| **6** | **18** | **dropped** |
|---|---|---|
| connections per origin — what every browser actually shipped by ~2008 | via **domain sharding** (`img1`, `img2`, `img3`). ⚠️ A hack on top of a violated rule. | **RFC 7230 removed the sentence in 2014.** The spec conceded. |

> ⭐ **The best row in that table is the one nobody shipped** — pipelining. Why, next.

---

## 🧷 1999: mostly tightening, and why 307 exists

**RFC 2616, June 1999.** Genuinely new: `307 Temporary Redirect` · `416` · `417` + `Expect:` ·
`identity` content-coding · `TE:` · **`Host` is now a MUST (and a MUST-400)** · ETag required
on resource creation · charset wildcards · byte ranges without a known length.

> ⚠️ **NOT new: `504 Gateway Timeout`.** It is in RFC 2068 §10.5.5 already — the whole 5xx
> family arrived in 1997.

### Why 307 exists — a standard losing to deployed reality

1. RFC 2068 said: **302 keeps the method.**
2. ⚠️ **Every browser turned the POST into a GET anyway.**
3. RFC 2616 could have said *"no, really"*. Instead it **renamed 302 to "Found"**, wrote down
   what implementations do, and **added 307** for people who meant what 302 originally said.

> ⭐ **It is easier to add a number than to fix a billion deployed clients.**

---

## ⚖️ Watch Postel's law lose an argument

| **RFC 2616 §4.4 — June 1999** | **RFC 9112 §6.3 — June 2022** |
|---|---|
| *"If a message is received with **both** a `Transfer-Encoding` header field **and** a `Content-Length` header field, **the latter MUST be ignored**."* | *"A server **MAY reject** a request that contains both … or process such a request in accordance with the Transfer-Encoding alone. Regardless, **the server MUST close the connection** after responding."* |
| **Recover. Do not reject.** In 1999 this was simply what good engineers did. | **Rejection is now allowed. Recovery is now optional.** And either way, **destroy the connection**. |

> ⭐ ***Be liberal in what you accept*** **is a fine rule for two programs. It is a catastrophic
> rule for a chain of five.**

---

## 🕵️ Request smuggling

**One byte stream. Two readings. One attack.**

```http
POST /echo HTTP/1.1
Host: site-a.local
Content-Length: 6
Transfer-Encoding: chunked

0

GET /admin HTTP/1.1
Host: site-a.local
```

| Reading it with `Content-Length: 6` | Reading it with `Transfer-Encoding` |
|---|---|
| **ONE** request. Its 6-byte body is `0\r\n\r\nG` | **TWO** requests. The second is `GET /admin` |

> ⚠️ Put a **CDN that does the first** in front of an **origin that does the second**, and you
> have **posted a request the CDN never saw** — and left a spare response in the connection
> **for whoever is routed onto it next**.

```text
$ python3 framing.py --port 8011
this server answered with 2 response(s):
| HTTP/1.1 200 OK
| HTTP/1.1 404 Not Found      ← the request nobody sent
```

> ⭐ **HTTP/2 makes this unrepresentable:** the length is in the **frame header**, and there is
> **no second opinion to disagree with**.

---

## 📚 One document became six

**RFC 7230–7235, June 2014.**

| RFC | Title | Who has to read it carefully |
|---|---|---|
| **7230** | Message Syntax and Routing | Proxies, load balancers, CDNs — and the `https` scheme lives here now |
| **7231** | Semantics and Content | Application frameworks: methods, status codes, representations |
| **7232** | Conditional Requests | Anything with an ETag: browsers, caches, object stores |
| **7233** | Range Requests | Video, downloads, **Parquet readers** |
| **7234** | Caching | **Every CDN on earth** |
| **7235** | Authentication | The `WWW-Authenticate` / `Authorization` framework |

> 💡 *"Microservices, for RFCs."* Same year, same argument: **one large artefact with many
> stakeholders becomes several with clear ownership**, versioned independently, so a change to
> caching does not require re-ratifying the definition of `GET`.
> ⚠️ **Same trade-off too** — 2616 was *one place to look*, and everyone still says "2616" when
> they mean HTTP/1.1.

---

## 🔤 Why your JWT is base64

```abnf
tchar = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." /
        "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
token = 1*tchar

excluded:  " ( ) , / : ; < = > ? @ [ \ ] { }
```

> ⚠️ **Correction:** this is **not a 2014 rule**. RFC 7230 §3.2.6 only wrote it as a *list*.
> The rule is **RFC 2616 §2.2 (1999)**, where `token` = any CHAR except CTLs or separators —
> and the separators list already contains `{` and `}`. **Same rule, better prose, fifteen
> years earlier.**

**And the JWT reason is broader.** A JWT must survive an `Authorization` header, a URL query
string, a cookie, a form field **and** a JSON body. `base64url` also swaps `+` and `/` for `-`
and `_` so it is URL-safe — **and the signature is raw bytes, which need encoding whatever the
grammar says.**

> ⭐ **Every layer you pass through has an alphabet. The intersection of all of them is about
> sixty-four characters wide** — which is exactly why base64 exists, and why
> [Session 2](./02_Computer_Networking_Eagle_Eye_View.md) met the same problem in MIME.

---

## 🫖 Semantics vs wire format — and a teapot

**RFC 9110–9114, June 2022.**

| RFC | What it is | Version-specific? |
|---|---|---|
| **9110** | HTTP **Semantics** — methods, status, headers, ranges, auth | ⭐ **No.** Shared by 1.1, 2 and 3. |
| **9111** | HTTP **Caching** | ⭐ **No.** Shared by all three. |
| 9112 | **HTTP/1.1** | Wire format only |
| 9113 | **HTTP/2** | Wire format only |
| 9114 | **HTTP/3** | Wire format only |

> ⭐ **The table of contents is the argument.** Everything HTTP *means* is in 9110 and 9111.
> 9112–9114 only describe **how to write it down on a socket**. **Three encodings, one
> language.**

> 💡 **418 (Unused)** — an April Fool's joke (RFC 2324, 1998) that *"has been widely implemented
> as an easter egg, and therefore is effectively consumed by this use."* **Reserved forever —
> not because it is useful, but because too many people shipped the joke.**

---

## 🚦 Head-of-line blocking, measured

| **Pipelined, one connection** | **One connection each** |
|---|---|
| `/big.txt?delay=2.0` **2003.4 ms** | `/big.txt?delay=2.0` **2006.0 ms** |
| `/style.css` **2003.6 ms** | `/style.css` **3.2 ms** |
| `/app.js` **2003.8 ms** | `/app.js` **5.7 ms** |
| `/logo.png` **2004.1 ms** | `/logo.png` **6.1 ms** |
| `/icon.png` **2004.2 ms** | `/icon.png` **6.9 ms** |
| `/hero.png` **2004.4 ms** | `/hero.png` **7.2 ms** |

> ⚠️ **Every one of those five was ready in microseconds. They waited two seconds for a file
> none of them needed.**
> Same server. Same files. Same work. **The only difference is whether they had to queue behind
> each other.**

---

## 🆔 There is no request id on the wire

> ⭐ **The order IS the identifier.** Nothing in an HTTP/1.1 response says which request it
> answers. The client knows **only because it counted**. Which makes **order mandatory** — and
> makes **the slowest response set the pace for everything behind it**.

**Multiplexing is only possible if messages carry identity:**

| Protocol | The identifier | Where you met it |
|---|---|---|
| **TCP** | source port / destination port | Session 2 |
| **SS7 / TCAP** | transaction id | Session 2 — SMS and call setup |
| **FastCGI** | `requestId`, in every record header | Session 3 — php-fpm behind nginx |
| **HTTP/1.1** | ⚠️ **— nothing —** | and so: **strict response ordering** |
| **HTTP/2 · HTTP/3** | **stream identifier, 31 bits, every frame** | here |

---

## 📦 97.5% of what you upload is a repeat

```text
one request, headers only           805 bytes
× 80 requests for one page        64320 bytes
  new information (the paths)      1600 bytes    2.5%
  byte-for-byte repeats           62720 bytes   97.5%
```

> ⚠️ On a **1 Mbit uplink** that is **0.51 s of upload** before a single byte of your
> application data has moved — **the direction you have least of, spent at the start of the
> page, while the user watches.**

**805 B** of headers on one realistic request: cookies, `User-Agent`, `Accept-*`, `sec-fetch-*`.

> ⚠️ *"Why not gzip them?"* — the obvious answer, and **the wrong one**. See
> [CRIME](#-crime--why-not-just-gzip-the-headers).

---

## 🐌 When keep-alive made it slower

**Two algorithms, both correct:**

| **Nagle — RFC 896, 1984** | **Delayed ACK — RFC 1122** |
|---|---|
| Do **not** send a small segment while an earlier one is unacknowledged. | Do **not** acknowledge immediately; wait **up to 40 ms** to piggyback it. |

**Together:**

```
write(head)  → goes out, nothing unacked
write(body)  → ⚠️ Nagle HOLDS it (head is unacked)
client       → nothing to send, so the ACK is DELAYED
... 40 ms ...
ACK, then body.          Every request but the first.
```

```text
write(head); write(body)        one write, + TCP_NODELAY
/style.css   0.9 ms             total 3.2 ms
/app.js     41.5 ms  ← delayed ACK
/logo.png   44.0 ms  ← delayed ACK
/icon.png   43.9 ms  ← delayed ACK
/hero.png   44.0 ms  ← delayed ACK
total      174.3 ms
```

> ⭐ **It only appears on a PERSISTENT connection** — `close()` pushes it out. **The fix for one
> problem exposed it.**

> ⭐ **Your protocol sits on a protocol with its own opinions.** nginx and Apache both coalesce
> writes **and** set `TCP_NODELAY` — now you know why.

---

## 🧾 The bill for HTTP/1.1

| The wall | Measured today | Fixed by |
|---|---|---|
| Head-of-line blocking | 2003 ms vs 3 ms for the same file, pipelined | **Stream ids** — HTTP/2 |
| Header bloat | 97.5% of uploaded header bytes are repeats | **HPACK** — HTTP/2 |
| Too many connections | 6 per origin, 18 with domain sharding | **One connection** — HTTP/2 |
| Ambiguous framing | One byte stream, two readings, one attack | **Frame headers** — HTTP/2 |
| **TCP itself** | 3 round trips before the first byte | **QUIC** — HTTP/3 |

> ⭐ **Text framing is why HTTP won.** Anyone could implement it, anyone could debug it with
> telnet. That beat every better-engineered rival of the 1990s.
> ⭐ **But "text is slow" is not the finding — we measured gzip at 2.8%.** The problem was **text
> *without lengths* and *without identifiers*.** **HTTP/2 is not "HTTP but binary"; it is "HTTP
> but with lengths and ids", and binary is the consequence.**

---

## 🚢 HTTP/2: ship it to a billion users, then standardise

| When | What | The number that made the case |
|---|---|---|
| **Nov 2009** | SPDY announced — Belshe & Peon, Chromium blog | *"up to 55% faster"*, top 25 sites, **in a lab** |
| 2010–2014 | Chrome, Firefox, nginx, Twitter, Facebook ship it | Google runs **both ends** and measures **production** |
| **Feb 2015** | Google announces SPDY's retirement | **>25%** of Chrome resources on HTTP/2 vs **<5%** SPDY |
| **May 2015** | **RFC 7540 (HTTP/2) + RFC 7541 (HPACK)** | SPDY with the edges filed off |
| May 2016 | SPDY removed in Chrome 51 | six and a half years, experiment → obsolete |
| **Jun 2022** | **RFC 9113** obsoletes 7540 | deprecates priorities and the h2c Upgrade dance |

> 💡 **It is called HTTP/2, not HTTP/2.0, on purpose.** The working group dropped the minor
> version because "1.1" produced a decade of confusion about what a 1.x server must support.
> **There is no HTTP/2.1 and there will not be one** — the next version is a new number and a
> new wire format.

---

## 🔑 The connection preface

```text
PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n

50 52 49 20 2a 20 48 54 54 50 2f 32 2e 30 0d 0a
0d 0a 53 4d 0d 0a 0d 0a            ← exactly 24 octets, always
```

> ⭐ An **HTTP/1.1 server** that receives this sees method `PRI`, version `HTTP/2.0`, and
> **fails cleanly with 501** — instead of trying to parse the binary frames behind it as text.
> 💡 `PRI…SM` is what is left of **"PRISM"**. It was 2013. The RFC does not say so.

| **Over TLS — how it actually happens** | **Cleartext — the dance that died** |
|---|---|
| **ALPN** (RFC 7301). The client lists `h2` and `http/1.1` **inside the ClientHello**; the server picks one in the ServerHello. ⭐ **Zero extra round trips** — it rides in a handshake you already paid for. | RFC 7540 had an `Upgrade: h2c` dance. RFC 9113 §3.1: it *"was never widely deployed and is deprecated by this document."* ⚠️ **No browser ever shipped cleartext HTTP/2 at all.** |

---

## 🧱 Nine bytes, and 31 of them are the answer

```
┌───────────────────────┬──────────┬───────────┬─┬────────────────────────────┐
│      Length (24)      │ Type (8) │ Flags (8) │R│  Stream Identifier (31)    │
└───────────────────────┴──────────┴───────────┴─┴────────────────────────────┘
│                   Frame Payload (0 … Length)                                │
```

```text
-> preface  b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'
-> HEADERS  stream=1  GET /        67B of text -> 15B hpack
<- 00 00 2a 04 00 00 00 00 00      SETTINGS len=42 stream=0
<- 00 00 4d 01 04 00 00 00 01      HEADERS  len=77 stream=1  END_HEADERS
<- 00 01 07 00 00 00 00 00 01      DATA     len=263 stream=1
<- 00 00 00 00 01 00 00 00 01      DATA     len=0 stream=1   END_STREAM
```

| | |
|---|---|
| **Client streams are odd, server streams are even** | ⭐ so **nobody has to coordinate** (§5.1.1) |
| **Stream 0 is the connection itself** | SETTINGS, PING, GOAWAY |

> ⭐ **Request smuggling is not *fixed* here. It is *unrepresentable*:** the length is in a
> fixed place, at a fixed size, **with no second opinion**.

---

## 🧩 Ten frame types

| Type | Name | What it does | What it replaced in HTTP/1.1 |
|---|---|---|---|
| `0x00` | **DATA** | The body, in chunks ≤ `MAX_FRAME_SIZE` | `Content-Length` / chunked encoding |
| `0x01` | **HEADERS** | Opens a stream; carries an HPACK block | The request line and header block |
| `0x02` | PRIORITY | ⚠️ Deprecated by RFC 9113 → RFC 9218 `PRIORITY_UPDATE` | — |
| `0x03` | **RST_STREAM** | ⭐ Cancel **ONE** stream | Closing the TCP connection, **killing everything** |
| `0x04` | **SETTINGS** | Announce your limits, **both directions** | Nothing — there was no way to say |
| `0x05` | PUSH_PROMISE | Server push | Nothing — **and it did not last** |
| `0x06` | PING | Round-trip time; keep intermediaries awake | Nothing |
| `0x07` | **GOAWAY** | *"Last stream id I will process"* — **drain** | `Connection: close`, mid-flight |
| `0x08` | **WINDOW_UPDATE** | Flow control, **per stream AND per connection** | TCP's window, and only TCP's |
| `0x09` | CONTINUATION | A header block bigger than one frame | Nothing — ⚠️ and a **2024 DoS class** |

💡 §6.5.2 defaults: `HEADER_TABLE_SIZE` 4096 · `INITIAL_WINDOW_SIZE` 65535 ·
`MAX_FRAME_SIZE` 16384 · `MAX_CONCURRENT_STREAMS` has none *("no smaller than 100")*.

---

## 🗜️ HPACK: 174 → 79 → 6 bytes

**Three mechanisms, none of them clever.**

| # | Mechanism | |
|---|---|---|
| **1** | **Static table — 61 entries** | Fixed, identical everywhere (App. A). ⭐ Index 2 is `:method: GET` — **name AND value**. The whole of GET costs **`0x82`**. **Not compressed. Indexed.** |
| **2** | **Dynamic table — from index 62** | Anything sent before **on this connection** gets an index. ⭐ Your 300-byte cookie costs **300 bytes once, then 1–2 bytes forever**. |
| **3** | **Huffman — Appendix B** | A canonical code built from real header text: `e` is 5 bits, `X` is 8. Per string, **and only when it actually shrinks it**. |

```text
the same header set, three ways:
HTTP/1.1 text         174 bytes
HPACK, first time      79 bytes   −55%
HPACK, second time      6 bytes   −97%
                        ↑ six one-byte indices for six header fields
```

> ⭐ **The dynamic table is per connection — which is why HTTP/2 wants ONE.** Domain sharding
> was clever under 1.1 and is **actively harmful** here.

---

## 🔓 CRIME — why not just gzip the headers?

> ⭐ **Because compressed size leaks the secret.**

```text
// the attacker cannot decrypt anything. it only watches SIZE.
GET /aaaa?guess=a  Cookie: session=SECRET…   → compressed length 412
GET /aaaa?guess=b  Cookie: session=SECRET…   → compressed length 412
GET /aaaa?guess=S  Cookie: session=SECRET…   → compressed length 411
                                               ↑ the compressor found "S" twice
// one byte smaller means "correct". repeat per character.
```

**HPACK's defence is structural:**

- The **Huffman table is FIXED** — built once from a corpus, published in Appendix B, **never
  adapted to the data flowing through it**. There is no shared adaptive dictionary for attacker
  text and secret text to meet in.
- The **dynamic table is an exact-match index, not a substring matcher.** Guessing a *prefix*
  of your cookie wins nothing.
- RFC 7541 §7.1 goes further: mark sensitive fields **"never indexed"**.

> ⚠️ **Yours too:** gzip a JSON response containing a **user-supplied search term** and an **API
> key** together, and you have rebuilt CRIME.

---

## ⚡ Multiplexing, measured

| **HTTP/1.1 pipelined** | **HTTP/2** |
|---|---|
| `/big.txt?delay=2.0` 2003.4 ms | stream 3 `/style.css` **4.9 ms** |
| `/style.css` 2003.6 ms | stream 7 `/logo.png` **5.7 ms** |
| `/app.js` 2003.8 ms | stream 9 `/icon.png` **6.9 ms** |
| `/logo.png` 2004.1 ms | stream 5 `/app.js` **6.9 ms** |
| `/icon.png` 2004.2 ms | stream 11 `/hero.png` **7.8 ms** |
| `/hero.png` 2004.4 ms | stream 1 `/big.txt` 2005.9 ms |
| Responses **must** arrive in request order, because **order is the only identifier there is**. | ⭐ Arriving **out of order, on purpose**, because **each frame says who it is for**. |

And the dynamic table warming up in real time:

```text
-> HEADERS stream=1 GET /big.txt?delay=2.0   84B of text -> 30B hpack
-> HEADERS stream=3 GET /style.css           76B of text -> 12B hpack
-> HEADERS stream=5 GET /app.js              73B of text -> 11B hpack
-> HEADERS stream=7 GET /logo.png            75B of text -> 12B hpack
```

> 💡 Same `GET`. Same `200`. Same `ETag`. The h2 handler is **line-for-line the shape of the
> HTTP/1.1 one** — that is **RFC 9110 doing its job**.

---

## 🧠 A protocol can only give you permission

| **Handling requests inline in the read loop** | **One thread per stream** |
|---|---|
| ```for event in conn.receive_data(data):```<br>`    if isinstance(event, RequestReceived):`<br>`        self.serve(event.stream_id, …)` | `threading.Thread(target=self.safe_serve,`<br>`    args=(event.stream_id, …),`<br>`    daemon=True).start()` |
| stream 1 `/big.txt?delay=2` 2005.6 ms | stream 3 `/style.css` 4.9 ms |
| stream 3 `/style.css` 2005.7 ms | stream 7 `/logo.png` 5.7 ms |
| stream 5 `/app.js` 2005.7 ms | stream 9 `/icon.png` 6.9 ms |
| ⚠️ **Exactly the HTTP/1.1 numbers.** | stream 1 `/big.txt?delay=2` 2005.9 ms |

> ⭐ **Same frames. Same client. Same wire. You serialised the work yourself.**
> You will meet this exact shape again: a worker pool sharing one database connection · a
> blocking call inside a coroutine · a gRPC handler holding a global mutex · six goroutines
> waiting on one channel. **The transport is fine.**

---

## 💀 Server push: nobody deprecated it, everybody removed it

| **What the RFC says** | **What implementers did** |
|---|---|
| **Still standard, today.** Retained in RFC 9113 §8.4 and RFC 9114 §4.6 (HTTP/3). | **Chrome 106, 27 September 2022** — removed. |
| Search RFC 9113 for *"deprecat"* and you get **exactly two hits, neither of them push**: RFC 7540 `PRIORITY`, and the `h2c` Upgrade token. | **1.25%** of HTTP/2 sites used it. Later **0.7%**. *"no clear net performance gain and in many cases performance regressions"* |

> ⚠️ **The fundamental problem: the server does not know what is in your cache.** So it pushes
> a file you already have — **spending bandwidth AND competing with what you actually needed**,
> on the same connection and congestion window.

> ⭐ **The replacement: `103 Early Hints` (RFC 8297).** Do not push the file — say *"you are
> going to want style.css"*. The client checks its own cache and decides.
> **When one side has the knowledge and the other has the state: inform — do not act.**

---

## 🕳️ The one thing HTTP/2 could not fix

> **RFC 9114 §1.1:** *"because the parallel nature of HTTP/2's multiplexing is **not visible to
> TCP's loss recovery mechanisms**, a lost or reordered packet causes **all** active
> transactions to experience a stall **regardless of whether that transaction was directly
> impacted**."*

```text
stall: holding the stream at byte 3000 for 300 ms

run 1  logo 4.5  style 4.7 | app 306.3  hero 307.0  icon 307.3  big 308.9
run 2  style 4.0 icon 5.2  | logo 308.2 big 308.3   hero 308.4  app 308.4
run 3  style 3.5           | big 306.4  app 306.5   icon 306.5  logo 306.7  hero 306.8
       ↑ through before      ↑ everything behind the hole, whether or not
         the hole              it lost a single byte
```

> ⚠️ **The later bytes had ARRIVED** — they were in the receive buffer. **The kernel may not
> hand them over without breaking the in-order guarantee that is the reason you chose TCP.**
> And **which** streams get caught **changes every run**: the blast radius is *"whoever had
> bytes behind the gap"*, and you do not get to choose.

> 💡 Google's SPDY data: **11.81% speedup at 0% loss, 47.7% at 2% loss.** ⭐ **Multiplexing helps
> most exactly where TCP hurts most.**

---

## 🕸️ QUIC: why UDP

| **The obvious answer, and why it fails** | **And so: encrypt almost everything** |
|---|---|
| `TCP = 6` `UDP = 17` `SCTP = 132` — just take protocol number 253 and build a proper transport. | **RFC 8999 §7:** *"middleboxes could observe traits of a specific version of QUIC and assume that when other versions exhibit similar traits the same underlying semantic is being expressed."* |
| ⚠️ **Except:** every NAT, firewall, CGNAT, corporate proxy and hotel router on earth **drops what it does not recognise**. | ⭐ **Anything a middlebox CAN read, it will eventually depend on — and then you can never change it.** That is how TCP options became unusable. |
| **SCTP is a good protocol**, standardised in 2000, **and you cannot use it across the public internet.** | QUIC encrypts packet numbers and most of the header — **not only for privacy, but to keep the protocol changeable**. |

> ⭐ **UDP is not a good foundation. It is a hole that already exists.**
> And it lives in **userspace**: a TCP change is a kernel upgrade on a billion machines and a
> decade. **A QUIC change ships with your app.**

---

## 🤝 One handshake, not two

| **TCP + TLS 1.3 + HTTP/2** | **QUIC + HTTP/3** |
|---|---|
| `SYN →` `← SYN/ACK` `ACK →` — **1 RTT**, and *nothing has been said yet* | `Initial →` TLS ClientHello **inside a QUIC CRYPTO frame** |
| `ClientHello →` (ALPN rides here) `← ServerHello` `Finished →` — **2 RTT** | `← Handshake` — **1 RTT** |
| `GET →` `← 200` — **3 RTT** | `GET →` `← 200` — **2 RTT** |

> ⭐ **RFC 9001 §2.1: there is no transport handshake and *then* a crypto handshake. There is
> one handshake.**

```text
                                              measured   round trips
TCP + TLS 1.3 + h2 (new connection)           456.6 ms       3.0
QUIC + HTTP/3    (new connection, 1-RTT)      319.8 ms       2.1
```

💡 With TLS 1.2 it was **four**. And **TLS is not optional — there is no unencrypted QUIC.**

> ⭐ **Layering is how we make systems comprehensible — and every layer boundary is a place you
> may pay a round trip.**

---

## 0️⃣ 0-RTT, and the price of it

```text
                                              measured   round trips
TCP + TLS 1.3 + h2 (new connection)           456.6 ms       3.0
QUIC + HTTP/3    (new connection, 1-RTT)      319.8 ms       2.1
QUIC + HTTP/3    (0-RTT, request in flight 1) 161.7 ms       1.1
```

Cold connection: QUIC saves **137 ms**. Resumed: 0-RTT saves **295 ms**.

> ⚠️ **RFC 9001 §9.2:** *"use of TLS early data comes with an exposure to **replay attack**…
> Endpoints MUST implement and use the replay protections described in \[TLS13], however it is
> recognized that **these protections are imperfect**."*
> **Imperfect because** the defence is a single-use ticket cache, **and a server farm has many
> servers**. An attacker who captured your early data sends it to a different one.

**So the rule is yours to make.** *"An application protocol that uses QUIC MUST describe how the
protocol uses 0-RTT and the measures that are employed to protect against replay attack."*

> ⭐ **In practice: idempotent requests only.** `GET` is fine; a `POST` that charges a card is
> not. **Cloudflare allows only GET and HEAD**, and sets an `Early-Data` header so your origin
> can refuse with **425 Too Early**.

> ⭐ **0-RTT is a cache of a negotiation. Every cache of a negotiation trades a round trip for
> the possibility of a replay.**

---

## ✂️ Head-of-line blocking, gone

| **HTTP/2 over TCP** — one 300 ms stall | **HTTP/3 over QUIC** — 18 datagrams really deleted (5%) |
|---|---|
| `/logo.png` 4.5 ms *(before the hole)* | `/style.css` 4.5 ms |
| `/style.css` 4.7 ms *(before the hole)* | `/app.js` 5.4 ms |
| `/app.js` **306.3 ms** | `/logo.png` 6.7 ms |
| `/hero.png` **307.0 ms** | `/icon.png` 7.8 ms ← *lost packets* |
| `/icon.png` **307.3 ms** | `/hero.png` 11.0 ms |
| `/big.txt` **308.9 ms** | `/big.txt` 78.2 ms |
| ⚠️ Streams that lost **nothing** stalled — **and a different set of them each run**. | ⭐ **Only the stream that lost data waited.** |
| TCP cannot see your streams. One ordered byte pipe, one gap, everything behind it waits. | Every `STREAM` frame carries a **stream id and an offset**. **Ordered within a stream, unordered between them.** |

> ⚠️ **Be precise about this experiment.** The TCP side *delays* a chunk (the shape a lost
> segment makes); the QUIC side *really deletes* 18 datagrams. **Different perturbations — do
> not read 307 vs 78 as a benchmark.**
> ⭐ **What *is* comparable is the blast radius:** on TCP it is *"whoever had bytes behind the
> gap"*, different every run. **On QUIC it is exactly one stream, every time.**

---

## 🚶 Connection IDs — surviving a network change

| **TCP: the connection IS the four-tuple** | **QUIC: identity is not addressing** |
|---|---|
| `(src IP, src port, dst IP, dst port)`. Change any one and it is a **different** connection — which is to say, **a dead one**. | §5.1: *"The primary function of a connection ID is to ensure that **changes in addressing at lower protocol layers (UDP, IP) do not cause packets … to be delivered to the wrong endpoint**."* |
| ⚠️ Walk out of the coffee shop: Wi-Fi → LTE, your IP changes, **every TCP connection dies** — video buffers, downloads restart, websockets reconnect, spinner. | ⭐ **New address, same connection id, path validated, connection carries on.** |
| Same thing when your NAT quietly rebinds your external port after idle. | ⚠️ **And the abuse case**, handled in the same section: a stable visible id is a **tracking identifier**. So ids *"MUST NOT contain any information that can be used by an external observer to correlate them"* — endpoints **issue a pool and rotate**. |

> ⭐ **Identity belongs at the layer that owns the semantics.** TCP made addressing and identity
> the same thing, and **inherited every problem mobility causes**.

---

## 🗃️ QPACK

> **RFC 9204:** *"If HPACK were used for HTTP/3, it would induce head-of-line blocking for field
> sections due to **built-in assumptions of a total ordering** across frames on all streams."*

| **The problem QUIC created** | **QPACK's fix** |
|---|---|
| HPACK's dynamic table is **shared mutable state**. *"Field number 67"* only means something if you have **already processed every insertion that made 67 mean it**. | ⭐ **Take the mutable state off the request streams.** |
| On TCP that is free — **total ordering**. | **encoder stream (0x02)** — encoder → decoder: table insertions |
| ⚠️ **QUIC deliberately removed exactly that guarantee.** A block on stream 12 could reference an entry inserted on stream 8 **that has not arrived**. So: **stall stream 12.** | **decoder stream (0x03)** — decoder → encoder: *"I have seen these"*. The encoder **only references entries it knows are safe**. |

💡 `QPACK_BLOCKED_STREAMS` default **0** · `QPACK_MAX_TABLE_CAPACITY` default **0**.
Static table: HPACK has **61 entries from 1**; QPACK has **99 from 0**, rebuilt on newer
traffic — **the `sec-fetch-*` headers are in it**.

> ⭐ **Shared mutable state and out-of-order delivery do not mix. Relax an ordering guarantee,
> then go and find what was relying on it.**

---

## 🔎 Discovery and fallback

| Mechanism | RFC · date | How it works | What it costs |
|---|---|---|---|
| **ALPN** | RFC 7301 · Jul 2014 | Protocol chosen **inside the TLS handshake** — `h2`, `h3` | Nothing. ⚠️ But it needs a handshake first. |
| **Alt-Svc** | RFC 7838 · Apr 2016 | A response header: `h3=":443"`. The browser remembers. | ⚠️ **One full TCP+TLS connection, every cold cache** |
| **HTTPS DNS RR** | RFC 9460 · Nov 2023 | Record type **65** carries the ALPN list **in the DNS answer** | ⭐ Nothing — you were doing the lookup anyway |

| **3–5%** | **95.3%** | **downgrade** |
|---|---|---|
| of networks block **all UDP traffic** (RFC 9308 §2) | of Google's clients could use QUIC; **4.4%** blocked or packet-size problems | drop the UDP and **wait for the client to fall back to TCP by itself** |

> ⚠️ **RFC 9308 §2:** *"A fallback to TCP and TLS **exposes control information to modification
> and manipulation** in the network."*
> ⭐ **Any protocol with a fallback path has, by construction, a downgrade attack. The only
> question is what the fallback costs you.**

---

## 📊 Where the web actually is

| Source | Measurement | Figure | Read it how? |
|---|---|---|---|
| HTTP Archive | By **request**, real crawl | HTTP/1.1 **15%** · HTTP/2+ **85%** | Cleanest number here |
| Web Almanac 2024 | By **homepage** | h1 **21–22%** · h2 **70–71%** · h3 **7–9%** | Cleanest number here |
| Web Almanac 2024 | Advertising | h3 `Alt-Svc` **26–28%** · DNS HTTPS RR **9–10%** | ⚠️ The DNS record is the laggard |
| W3Techs (Sep 2026) | By **website** | HTTP/2 **34.6%** · HTTP/3 **40.3%** | ⚠️ Treat with suspicion — h3 > h2 means the categories are not what they look like |

> ⭐ **Fifteen per cent of requests are still HTTP/1.1, in 2026, eleven years after HTTP/2
> shipped.** Internal services, embedded devices, that one load balancer nobody wants to touch,
> a thousand APIs behind a gateway.
> **You will write HTTP/1.1 parsers in your career. There is no cutover — there is a very long
> tail, and most engineering happens at the boundary between versions rather than inside one.**

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **RFC 1945 / 2068 / 2616** | HTTP/1.0 (1996) / early HTTP/1.1 (1997) / HTTP/1.1 (1999) |
| **RFC 7230–7235** | 2014: one document split into six by stakeholder |
| **RFC 9110 / 9111** | ⭐ **Semantics** and **Caching** — shared by all three versions |
| **RFC 9112 / 9113 / 9114** | Wire formats: HTTP/1.1 / HTTP/2 / HTTP/3 |
| **`Host:`** | Put the destination name **in the message**; SNI and `:authority` are the same move |
| **`Last-Modified` / `If-Modified-Since`** | Clock-based validation — ⚠️ 1 s resolution, skew, mtime ≠ identity |
| **ETag / `If-None-Match` / `If-Match`** | Content fingerprint; weak (`W/`) vs strong; optimistic concurrency |
| **`Vary`** | Cache-key instruction — ⚠️ `Vary: User-Agent` destroys hit rate |
| **`Range` / 206 / 416** | Partial content — video scrubbing, resumable downloads, Parquet footers |
| **Chunked encoding** | ⭐ Length **and** delimiter, nested — same shape as FastCGI records |
| **`no-cache` vs `no-store`** | ⚠️ *Revalidate before use* vs *do not write it down* |
| **Pipelining** | Send all requests at once; ⚠️ responses **must** come back in order |
| **Head-of-line blocking** | The slowest response sets the pace for everything behind it |
| **Domain sharding** | `img1`, `img2`… to beat the 6-connection cap; ⚠️ harmful under HTTP/2 |
| **Request smuggling** | `Content-Length` vs `Transfer-Encoding` disagreement between two hops |
| **`tchar` / token** | The HTTP header alphabet — why JWTs are base64url |
| **SPDY** | Google's 2009 experiment that became HTTP/2 |
| **Connection preface** | `PRI * HTTP/2.0…SM` — 24 octets that make a 1.1 server fail cleanly |
| **ALPN** | Protocol negotiation inside the TLS ClientHello; **free** |
| **Stream id** | ⭐ 31 bits in every frame — odd = client, even = server, 0 = connection |
| **HPACK** | Static table (61) + dynamic table + fixed Huffman; 174 → 79 → **6 bytes** |
| **CRIME** | Compressed length leaks secrets; HPACK's fixed table is the structural defence |
| **`GOAWAY` / `RST_STREAM`** | Drain a connection / cancel one stream |
| **`WINDOW_UPDATE`** | Flow control per stream **and** per connection |
| **`103 Early Hints`** | The replacement for server push — ⭐ inform, don't act |
| **QUIC** | TCP+TLS rebuilt over UDP in userspace; RFC 9000 |
| **0-RTT** | Resumed handshake with data in flight 1; ⚠️ replayable — idempotent requests only |
| **425 Too Early** | Refuse a 0-RTT request you don't want replayed |
| **Connection ID** | ⭐ Identity decoupled from addressing — survives Wi-Fi → LTE |
| **QPACK** | HPACK for out-of-order delivery: encoder/decoder streams, blocked-streams limit |
| **Alt-Svc / HTTPS RR** | *"I also speak h3"* — in a header (costs a connection) or in DNS (free) |

---

## 🎯 Session Takeaways

1. ⭐ **Multiplexing needs identity.** HTTP/1.1 had no request id, so **order became the identifier** and ordering became mandatory. 31 bits fixed it. **Same move as TCP ports, SS7 transaction ids, FastCGI request ids and QUIC stream ids.** *When a client must wait before sending the next message — check whether you left the identifier out.*
2. ⭐ **Every fix is the next problem.** Persistence made pipelining possible; pipelining created head-of-line blocking. HTTP/2 fixed it above TCP and **exposed it inside TCP**. QUIC fixed that and **broke HPACK**, which needed QPACK. **There is no final version — only a sequence of trades, and knowing which one you are standing on.**
3. ⭐ **Semantics and encoding differ.** RFC 9110 is what HTTP *means*; 9112/9113/9114 are **three ways of writing it down**. `GET` has not changed since 1996; **the wire format has changed three times.** Every long-lived system needs this seam.
4. ⭐ **Deployed reality beats specification.** 302 lost to browsers, so we got 307. Two connections lost to six, and the sentence was deleted. Postel's law lost to request smuggling. 418 was a joke that got reserved forever. Push was never deprecated and is dead. **QUIC runs on UDP because middleboxes have a veto.**
5. **HTTP/2 is not "HTTP but binary" — it is "HTTP but with lengths and ids".** Binary is the *consequence*. gzip on a body is 2.8%; the body was never the problem.
6. **`Host:` is the highest-leverage line in the standard** — and the same idea reappears as SNI, `:authority` and every routing key you've written.
7. **An ETag is a fingerprint; `Last-Modified` is a clock.** Clocks drift, skew and change on rebuild.
8. ⭐ **97.5% of your uploaded header bytes are repeats**, on the direction you have least of, at the start of the page.
9. **You cannot gzip headers — compressed size leaks secrets (CRIME).** HPACK's fixed Huffman table and exact-match index are the structural answer.
10. ⭐ **A protocol can only give you permission.** HTTP/2 multiplexing does nothing if you serialise the work in your own handler.
11. **Server push failed because the server doesn't know your cache.** `103 Early Hints` informs instead of acting — **when one side has the knowledge and the other has the state, inform.**
12. ⭐ **TCP can't see your streams.** One gap stalls everything behind it, and *which* streams get caught changes every run. QUIC's blast radius is **exactly one stream, every time**.
13. **0-RTT is a cache of a negotiation** — it trades a round trip for the possibility of a replay. Idempotent requests only.
14. **Identity belongs at the layer that owns the semantics.** TCP conflated addressing and identity and inherited every mobility problem.
15. ⚠️ **Any protocol with a fallback has a downgrade attack by construction.**
16. **15% of requests are still HTTP/1.1 in 2026.** There is no cutover — **most engineering happens at the boundary between versions.**

---

## 🔗 References

- RFC 1945 — HTTP/1.0 — https://www.rfc-editor.org/rfc/rfc1945
- RFC 2068 / RFC 2616 — HTTP/1.1 — https://www.rfc-editor.org/rfc/rfc2616
- RFC 7230–7235 — the 2014 split — https://www.rfc-editor.org/rfc/rfc7230
- RFC 9110 — HTTP Semantics — https://www.rfc-editor.org/rfc/rfc9110
- RFC 9111 — HTTP Caching — https://www.rfc-editor.org/rfc/rfc9111
- RFC 9112 / 9113 / 9114 — HTTP/1.1, /2, /3 wire formats
- RFC 7541 — HPACK — https://www.rfc-editor.org/rfc/rfc7541
- RFC 9204 — QPACK — https://www.rfc-editor.org/rfc/rfc9204
- RFC 9000 / 9001 — QUIC & QUIC-TLS — https://www.rfc-editor.org/rfc/rfc9000
- RFC 8999 — Version-independent QUIC — https://www.rfc-editor.org/rfc/rfc8999
- RFC 9308 — QUIC applicability — https://www.rfc-editor.org/rfc/rfc9308
- RFC 7301 — ALPN · RFC 7838 — Alt-Svc · RFC 9460 — HTTPS/SVCB records
- RFC 8297 — 103 Early Hints — https://www.rfc-editor.org/rfc/rfc8297
- RFC 896 — Nagle · RFC 1122 — delayed ACK
- IANA HTTP Status Code Registry — https://www.iana.org/assignments/http-status-codes/
- HTTP Archive / Web Almanac — https://almanac.httparchive.org/
- Chrome: removing HTTP/2 push — https://developer.chrome.com/blog/removing-push
- PortSwigger, request smuggling — https://portswigger.net/web-security/request-smuggling

---

## ➡️ Next

[Session 6 — (Ab)using CDNs](./06_Abusing_CDNs.md) — *where did the state go?* Sessions and
sticky routing, what "stateless" actually costs, TLS termination, shared caches and the
thundering herd.
