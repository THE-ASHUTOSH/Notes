# Session 4 — nginx Deep Dive 🅝

> **Topics:** A corrected web-server lineage · Apache's decade chasing `fork()` · What nginx
> actually changed · Process model · The event loop in six lines · `accept_disabled` ·
> select vs epoll · The stale-event bug · `sendfile` · Reverse proxy · Caching · `location`
> precedence · Weighted round robin · `try_files` · A walk through the source
>
> 📄 Source: *CN at Scaler — Lesson 4*, "nginx, and the code that explains it"
> (nginx 1.31.5 · companion repo *nginx-from-scratch*).

---

## 📑 Table of Contents

1. [Why the history matters](#-why-the-history-matters)
2. [A correction worth making](#-a-correction-worth-making)
3. [The actual lineage](#-the-actual-lineage)
4. [Apache spent a decade trying to outrun `fork()`](#-apache-spent-a-decade-trying-to-outrun-fork)
5. [Java's answer: stop creating things](#-javas-answer-stop-creating-things)
6. [So here is 2002](#-so-here-is-2002)
7. [Igor Sysoev, Rambler, 2002](#-igor-sysoev-rambler-2002)
8. [Apache asked a question. nginx asked a different one](#-apache-asked-a-question-nginx-asked-a-different-one)
9. [The process model](#-the-process-model)
10. [All of nginx, in six lines](#-all-of-nginx-in-six-lines)
11. [Load balancing between workers, in one line of arithmetic](#-load-balancing-between-workers-in-one-line-of-arithmetic)
12. [select is O(watched). epoll is O(active)](#-select-is-owatched-epoll-is-oactive)
13. [The bug every event-loop author writes exactly once](#-the-bug-every-event-loop-author-writes-exactly-once)
14. [`sendfile`: four copies become two](#-sendfile-four-copies-become-two)
15. [Now the honest part](#-now-the-honest-part)
16. [Why "reverse" proxy?](#-why-reverse-proxy)
17. [The cache: two structures, one of them on disk](#-the-cache-two-structures-one-of-them-on-disk)
18. [The LRU is one line](#-the-lru-is-one-line)
19. [Two lines that save you at 3am](#-two-lines-that-save-you-at-3am)
20. [`location` precedence](#-location-precedence)
21. [Why 500 prefixes are free and 500 regexes are not](#-why-500-prefixes-are-free-and-500-regexes-are-not)
22. [Smooth weighted round robin](#-smooth-weighted-round-robin)
23. [`try_files` and named locations](#-try_files-and-named-locations)
24. [Reading the source](#-reading-the-source)
25. [The HTTP parser is a resumable state machine](#-the-http-parser-is-a-resumable-state-machine)
26. [Eleven phases, and `return` means "suspended"](#-eleven-phases-and-return-means-suspended)
27. [FastCGI: length *and* delimiter](#-fastcgi-length-and-delimiter)
28. [The ladder](#-the-ladder)
29. [Key Terms Recap](#-key-terms-recap)
30. [Session Takeaways](#-session-takeaways)

---

## 🕰️ Why the history matters

> **Remember the evolution. You can forget the dates.**

> ⭐ **Understanding history is how you get to create a different timeline.** Every design in
> this session was somebody's answer to a constraint that **no longer exists**. Knowing which
> constraint is **how you tell a law from a habit**.

Understanding the evolution tells you what the limitation was and what was proposed to fix it.
Sometimes you look at the same limitation and **fix it a completely different way**.

---

## 📚 A correction worth making

| The story you often hear | What actually happened |
|---|---|
| *"Berners-Lee wrote the first server. It was called Mosaic. Mosaic became Apache."* | Berners-Lee's server was **CERN httpd**, on a NeXT, **1990**. |
| | **Mosaic** (NCSA, 1993) was a **browser** — Andreessen's, not a server. |
| | Apache descends from **NCSA HTTPd** — a *different* NCSA program. |

⭐ Three separate programs, two of them at NCSA, one of them a browser. Getting it right is
**the difference between a story and a lineage**.

---

## 🧬 The actual lineage

| Year | | |
|---|---|---|
| **1990** | **CERN httpd** | Berners-Lee, on a NeXT. The first web server. |
| **1993** | **NCSA Mosaic** | A **browser**. Inline images. The web goes mainstream. |
| **1993** | **NCSA HTTPd** | Rob McCool. A server — ⭐ **and it invents CGI**. |
| **1994** | McCool leaves | Development stalls. Webmasters trade patches by mail. |
| **1995** | **Apache** | That patch set, continued as a project. *"A patchy server."* |
| **1996** | **Apache #1** | Passes NCSA HTTPd. **Stays #1 for twenty years.** |
| **1996–99** | IIS, then the boom | Microsoft fights for single-digit share. lighttpd and friends arrive. |

---

## 🏃 Apache spent a decade trying to outrun `fork()`

| **Apache 1.3 — prefork** | **Apache 2.0 — worker MPM** | **Apache 2.4 — event MPM** |
|---|---|---|
| A pool of processes, forked **at startup** instead of per request. The setup cost moves off the request path. ⚠️ One process still parks on one connection. | Processes each running many threads. 8 MB of stack becomes 8 MB **shared** plus a stack each. | ⭐ A **listener thread** parks idle keep-alives on `epoll` and only hands a worker a connection **when it has actual work**. Default on Unix since 2.4. |
| | ⚠️ 1999–2002: pthreads on Linux are new, buggy, and everyone is learning what *reentrant* means. | |

> ⭐ **Three architectures, one question: how do I make the per-connection worker cheaper?**
> Every answer was a good answer. **None of them was a different question.**

---

## ☕ Java's answer: stop creating things

```java
// CGI, 1993
per request: fork() + exec() + load interpreter + parse script + run + exit

// Servlet, 1997
at startup:  load class, instantiate once
per request: service(req, res)        ← a method call

// the object outlives the request. that is the trick.
```

**J2EE (1999)** made the multi-layer application server the default shape: **web tier, EJB
tier, database**. A servlet is instantiated once and serves every request on a thread from a
pool. **Connection pools** do the same thing for the database handshake.

> ⭐ Same move as prefork. Same move as FastCGI. **Take the expensive setup off the request
> path and pay it once.** *"Our primary goal was to avoid creating a new process. Everything
> else was consequence."*

---

## 📉 So here is 2002

| **10,000** | **8 MB** | **1024** |
|---|---|---|
| concurrent connections on one box. Dan Kegel names it **C10K** in 1999. | of stack **per thread**, the default on Linux. ⚠️ Ten thousand threads is **80 GB of address space**. | descriptors, hard-coded as **`FD_SETSIZE`** in a header. ⚠️ **`ulimit` does not move it.** |

Hardware is getting fast enough to serve ten thousand people from one machine. **The software
cannot** — and not for want of trying. The limits are a per-connection stack, a per-connection
scheduler entry, and **a 1983 API with a bitmap in it**.

> ⭐ **Everyone is optimising the worker. Somebody is about to delete it.**

---

## 🇷🇺 Igor Sysoev, Rambler, 2002

- **Rambler** was one of Russia's largest portals. Its Apache servers were falling over under
  **connection volume, not request volume**.
- He started writing nginx in **2002** to solve C10K specifically.
- First public release **4 October 2004** — chosen for the **anniversary of Sputnik**.
- **1.0.0 did not arrive until April 2011.** Seven years of shipping before the version number
  said *"ready"*.

> ⭐ **He did not set out to write a faster Apache.** He set out to serve ten thousand
> *mostly-idle* connections from one process, **and let something else generate the dynamic
> content.** That second half is why nginx is a **reverse proxy and not an application
> server**.

---

## ❓ Apache asked a question. nginx asked a different one

> **Apache:** *how do I make the worker cheaper?*
> **nginx:** ⭐ ***why is there a worker per connection at all?***

> A connection is **not a thing that needs a thread**. It is a thing that needs **a few hundred
> bytes of state and a place in a list**, until it has something to say. When it does, some CPU
> handles it, finishes, and moves on.

**One process per core. One event loop each. Ten thousand connections, and none of them owns
anything.**

---

## 🏗️ The process model

```
  worker 0        worker 1        …   worker N
 event loop      event loop          event loop

  master              cache manager        cache loader
  binds :80, reads    evicts LRU           warms index
  config, forks,
  handles signals.
  Nothing else.
```

```bash
$ ps -o pid,ppid,args -C nginx
2663     1  nginx: master process
2665  2663  nginx: worker process
2666  2663  nginx: worker process
2667  2663  nginx: cache manager process
```

> ⭐ **The count does not move under load.** Run the same command against a `fork()`-per-client
> server and watch it move. **Same `fork()` syscall — the only difference is how often you call
> it.**

📍 `ngx_process_cycle.c` → `ngx_master_process_cycle()` ~L74 → `ngx_start_worker_processes()` ~L358 ·
`ngx_process.c` → `ngx_spawn_process()` ~L87

---

## 🔁 All of nginx, in six lines

```c
timer = ngx_event_find_timer();
ngx_process_events(cycle, timer, flags);        /* epoll_wait() */
ngx_event_process_posted(cycle, &ngx_posted_accept_events);
ngx_shmtx_unlock(&ngx_accept_mutex);
ngx_event_expire_timers();
ngx_event_process_posted(cycle, &ngx_posted_events);
```

| | |
|---|---|
| ⭐ **Line 2 is where a worker spends 99.9% of its life: asleep.** | |
| **The timer is an *argument* to the sleep.** | nginx **never polls** for timeouts. |
| **Handlers do not run inside the poll** | they are **posted** and drained after. |

> ⭐ **Everything else in `src/http/` is a callback reached from line 2 or line 6. Read these
> six lines until they are boring.**

📍 `src/event/ngx_event.c` → `ngx_process_events_and_timers()` ~L195

---

## ⚖️ Load balancing between workers, in one line of arithmetic

```c
ngx_accept_disabled = ngx_cycle->connection_n / 8 - ngx_cycle->free_connection_n;
```

> **Read it as English:** *once I am using more than seven eighths of my connection slots, stop
> competing for new connections and let my siblings take them.*

| | |
|---|---|
| **No coordinator** | No shared counter, no leader, no heartbeat. ⭐ **Each worker decides alone, from a number it already has.** |
| **`accept_mutex` is now off** | Default off since **1.11.3**. `EPOLLEXCLUSIVE` (Linux 4.5+) and `SO_REUSEPORT` let the **kernel** do the fan-out instead. |
| **A userspace fix for a kernel problem** | The **thundering herd** was real in 2004. ⭐ The kernel fixed it; the workaround became dead weight — **and nginx removed it.** |

📍 `src/event/ngx_event_accept.c` ~L139 · `ngx_process_events_and_timers()` ~L224 (`ngx_trylock_accept_mutex`)

---

## 📊 select is O(watched). epoll is O(active)

| | **`select()`** | **`epoll()`** |
|---|---|---|
| **Where the watch list lives** | In **your process**. Rebuilt every call. | ⭐ In the **kernel**. Edited with `epoll_ctl()`. |
| **Cost per iteration** | O(n) to build + O(n) in kernel + O(n) to scan | **O(number of ready events)** |
| **10,000 idle, 10 active** | ⚠️ **30,000 units of work to find 10 events** | **10** |
| **Descriptor ceiling** | `FD_SETSIZE` = 1024, **compile-time, in a header** | `ulimit -n` |
| **What `ulimit -n` does** | ⚠️ **Nothing.** The limit is a bitmap width. | Everything. |
| **Portable?** | Everywhere since 1983 | Linux only (`kqueue` on BSD) |

📍 `ngx_select_module.c` → `ngx_select_process_events()` ~L222 **vs**
`ngx_epoll_module.c` → `ngx_epoll_process_events()` ~L784

> 💡 Open both in a split window. **Same signature, same job, ~200 lines each.** Everything
> else in this comparison is downstream of one decision: **who owns the watch list.**

---

## 🐛 The bug every event-loop author writes exactly once

```c
c        = event_list[i].data.ptr;
instance = (uintptr_t) c & 1;
c        = (ngx_connection_t *) ((uintptr_t) c & (uintptr_t) ~1);

if (c->fd == -1 || rev->instance != instance) {
    /* a stale event from a file descriptor
       that was just closed in this iteration */
    continue;
}
```

> ⚠️ **`epoll_wait` returns a BATCH.** Handling event 1 can **close the connection event 7
> points at**. A new client on the **recycled fd** then gets event 7 delivered to it.

> ⭐ **The fix is beautiful.** Structs are aligned, so the **low bit of the pointer is always
> zero**. nginx borrows it as a **generation flag** and flips it on reuse. **Free bit, no extra
> memory, one branch.**

📍 `ngx_epoll_module.c` → `ngx_epoll_process_events()` ~L839

---

## 📤 `sendfile`: four copies become two

```
read() + write()  —  4 copies, 2 mode switches per chunk
   disk → page cache → YOUR BUFFER → socket buffer → NIC
                         ↑ the copy you pay CPU for

sendfile()        —  2 copies, both DMA, 0 mode switches per chunk
   disk → page cache → socket buffer → NIC
```

> ⭐ **The data never enters your process.** `sendfile` deletes the copy through your address
> space — and with it, the **two mode switches per 64 KiB chunk**.

> ⚠️ **Why you can't use it for everything.** `sendfile` copies **kernel-side**. If you need to
> **touch the bytes** — gzip, TLS, templating — they must come into user space. **That is why
> `gzip on` and `sendfile on` fight, and why kTLS exists.**

📍 `ngx_linux_sendfile_chain.c` → `ngx_linux_sendfile_chain()` ~L50 → `ngx_linux_sendfile()` ~L232

---

## 🔬 Now the honest part

```text
$ ./sendfiled 8005 www/big.bin          # 64 MB, over loopback

mode=read      wall 37.4 ms | sys 37.3 | 2048 syscalls
mode=mmap      wall 23.3 ms | sys 23.1 |    4 syscalls
mode=sendfile  wall 33.2 ms | sys 32.3 |    1 syscall
```

> ⚠️ **On loopback, `sendfile` does not win on wall-clock time.** There is no NIC and no DMA.
> The kernel `memcpy`s into the receiver's buffer either way, and `curl` is competing for the
> same CPU. The transfer is **memory-bandwidth bound**, so all three land in the same place.

**What *is* real on any machine:** 2048 syscalls become **1**, and 64 MB **never enters the
process's address space**.

> ⭐ The win shows up as **headroom under concurrency** — CPU you did not spend copying is CPU
> you spend on somebody else's request — **not as a faster single transfer**.

> ⭐ **A benchmark that does not model the bottleneck measures the wrong thing. That lesson is
> worth as much as `sendfile` is.**

---

## 🔄 Why "reverse" proxy?

> **Because *proxy* was taken.**

| **Forward proxy — Squid, 1996** | **Reverse proxy — nginx** |
|---|---|
| Sits next to the **clients**. | Sits next to the **servers**. |
| One person on campus downloads an image; it is cached, and nobody else on campus downloads it again. It knows **your users** and protects **your uplink**. | Same caching. **Plus:** route by path or host, distribute across upstreams by weight or least-connections, fall back when one dies, terminate TLS, and **hold ten thousand slow clients so your app never meets one**. |
| `client → [proxy] → the whole internet` | `the whole internet → [nginx] → your app servers` |

⭐ Same machinery, **opposite side of the internet**. The client does not configure a reverse
proxy and usually cannot tell it is there — **which is exactly why it can do things the client
would never agree to**.

> ⭐ **And the killer feature nobody lists: it absorbs slow clients. Your app server never
> talks to a phone on 2G.**

---

## 🗃️ The cache: two structures, one of them on disk

```nginx
proxy_cache_path temp/cache levels=1:2 keys_zone=demo:10m
                 max_size=100m inactive=60s use_temp_path=off;
```

| Option | What it is |
|---|---|
| **`keys_zone=demo:10m`** | **10 MB of shared memory** holding the **rbtree and the LRU queue**. ⭐ **The index, not the data.** Roughly **8,000 keys per megabyte**. |
| **`levels=1:2`** | Two directory levels on disk, so **no single directory holds a million files** and destroys your filesystem's lookup time. |
| **`max_size=100m`** | Disk ceiling. The **cache manager** process evicts from the LRU tail to stay under it. |
| **`inactive=60s`** | ⚠️ Evicted if not **READ** for 60s — **regardless of TTL**. A different knob from `proxy_cache_valid`, and **the one people confuse**. |

> 💡 **Worth arguing about:** `proxy_cache_valid` is 10s and `inactive` is 60s. Which wins, and
> what does each mean? — `proxy_cache_valid` decides **how long the copy is considered fresh**;
> `inactive` decides **how long an unread copy is kept at all**. An object can be stale but
> present (revalidated), or fresh but evicted (never read again).

📍 `ngx_http_file_cache.c` → `..._lookup()` ~L1029 · `..._open()` ~L265

---

## 🧹 The LRU is one line

```c
q   = ngx_queue_last(&cache->sh->queue);        /* take the tail */
fcn = ngx_queue_data(q, ngx_http_file_cache_node_t, queue);

wait = fcn->expire - now;
if (wait > 0) { ... break; }                    /* tail is still fresh → stop */

if (fcn->count == 0) {                          /* nobody is streaming it */
    ngx_http_file_cache_delete(cache, q, name);
}
```

> ⭐ **Take the tail. Is it old? Is nobody using it? Delete it.** That is the entire eviction
> policy.
> **`count == 0`** is why an object being streamed to a client *right now* cannot be evicted
> out from under it.

> 💡 **Read `src/core/ngx_queue.h` first** — fifty lines of macros for an **intrusive
> doubly-linked list**. The cache LRU, the posted-events list and half of `src/core/` ride on
> it.

📍 `ngx_http_file_cache.c` → `ngx_http_file_cache_expire()` ~L1860

---

## 🚑 Two lines that save you at 3am

```nginx
proxy_cache_lock on;
proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
```

| | |
|---|---|
| **`proxy_cache_lock on`** | ⭐ **The anti-stampede switch.** A popular object expires. Without this, **every** request arriving in the next 200 ms is a MISS and **every one goes to the origin**. With it, **one goes and the rest wait** for the answer. ⚠️ **Off by default.** |
| **`proxy_cache_use_stale …`** | ⭐ **Serve stale rather than fail.** Your origin is down and you have a copy from four minutes ago. *Which would your users rather have — a slightly old page, or a 502?* `updating` also means **one request refreshes while everyone else keeps getting the stale copy instantly**. |

```bash
$ curl -i localhost:8082/ | grep X-Cache     # X-Cache-Status: MISS
$ curl -i localhost:8082/ | grep X-Cache     # X-Cache-Status: HIT
```

> ⭐ `add_header X-Cache-Status $upstream_cache_status;` — **put this in every cache config you
> ever write.**

---

## 🧭 `location` precedence

> ⚠️ **It has nothing to do with the order you wrote them in.**

| # | Form | Rule |
|---|---|---|
| **1** | `location = /exact` | **Exact match.** Wins immediately, search stops. |
| **2** | `location ^~ /images/` | **Longest prefix**, and it **suppresses the regex search**. |
| **3** | `location ~ \.php$` | **Regex.** ⭐ **FIRST match in file order, not longest.** |
| **4** | `location /` | Longest prefix, used **only if no regex matched**. |

| Request | Wins |
|---|---|
| `/exact` | **1** |
| `/images/a.php` | ⭐ **2** — `^~` suppressed the regex |
| `/other/a.php` | **3** |
| `/anything` | **4** |

> ⚠️ **Roughly half the room gets `/images/a.php` wrong** — they expect the regex to win.

> 💡 **nginx has no `.htaccess`.** That is **not a missing feature**. It is the reason nginx
> does not `stat()` its way up the directory tree on **every single request**.

---

## 🌲 Why 500 prefixes are free and 500 regexes are not

```c
n  = (len <= node->len) ? len : node->len;
rc = ngx_filename_cmp(uri, node->name, n);

if (rc != 0) {                                  /* a TREE */
    node = (rc < 0) ? node->left : node->right;
    continue;
}

if (len > node->len && node->inclusive) {
    node = node->tree; uri += n; len -= n;      /* descend */
}
```

| **Prefixes** | **Regexes** |
|---|---|
| A **ternary search tree**, built **at config-parse time**, walked **one URI segment at a time**. | ⚠️ A **plain array**, walked **in order, every request**. |

> ⭐ **The data structure is the documentation.** Once you have seen that **prefixes are a tree
> and regexes are an array**, the precedence rules stop being trivia you memorise and become
> **the only rules those two structures could have**.

📍 `ngx_http_core_module.c` → `ngx_http_core_find_location()` ~L1446 → `ngx_http_core_find_static_location()` ~L1542

---

## 🎚️ Smooth weighted round robin

```c
peer->current_weight += peer->effective_weight;
total                += peer->effective_weight;

if (peer->effective_weight < peer->weight)
    peer->effective_weight++;                   /* passive health check recovery */

if (best == NULL || peer->current_weight > best->current_weight)
    best = peer;
...
best->current_weight -= total;
```

```
weights 3 : 1
naive WRR    a a a b      ← bursts
nginx smooth a b a a      ← same ratio, no bursts at the origin
```

```bash
$ for i in $(seq 24); do curl -s "localhost:8082/x-$i-$RANDOM" -o /dev/null; done
$ grep -o 'upstream=[0-9.:]*' logs/access.log | sort | uniq -c
   6 upstream=127.0.0.1:8001
  18 upstream=127.0.0.1:8004      ← exactly 3:1
```

> ⭐ **Same ratio, spread evenly.** `effective_weight++` is a **passive health check**: a peer
> that failed is demoted and then **slowly earns its weight back**.

📍 `ngx_http_upstream_round_robin.c` → `ngx_http_upstream_get_peer()` ~L811

---

## 🪃 `try_files` and named locations

```nginx
location / {
    try_files $uri $uri/ /index.html?$args;
}
```

> *"Is this a real file? A real directory? No? Then hand the whole URI to the app and let it
> route."*

> ⭐ **The last entry is the only one that is never tested.** It is the **fallback**, not a
> candidate.

**Fallback across a network boundary:**

```nginx
location /maybe/ {
    try_files $uri @app;
}
location @app {
    proxy_pass http://app;
}
```

⭐ `@app` is a **named location**: reachable **only** from `try_files` or `error_page`, never
from a URL. **Try disk first; if it is not there, ask the upstream.**

> 💡 **WordPress, Rails, Django, every SPA router: all of them are this directive plus an
> application that reads `REQUEST_URI`.** Once you see it, the magic evaporates.

📍 `ngx_http_try_files_module.c` → `ngx_http_try_files_handler()` ~L79

---

## 🗺️ Reading the source

> **Line numbers drift. Function names do not.**

```bash
git clone --depth 1 https://github.com/nginx/nginx.git
cd nginx && git log -1 --oneline        # 231a60ee nginx-1.31.5-RELEASE

grep -rn "^ngx_epoll_process_events" src/
```

> ⭐ **nginx puts the return type on its own line.** So **`^name(`** finds the **definition**
> and nothing else — not the declarations, not the call sites. **One habit, and the whole tree
> becomes navigable.**

> ⭐ That is not a disclaimer, it is the skill: **navigate a codebase by structure, not by
> coordinates.**

### The tree in two minutes

| Directory | What's in it |
|---|---|
| **`src/core/`** | nginx's own **standard library** — string, array, list, hash, rbtree, queue, palloc, buf, conf, cycle, connection. It has its own everything because **in 1999 you could not portably rely on anyone else's**. |
| **`src/event/`** | **The loop.** `modules/` holds **six ways to wait** — epoll, kqueue, select, poll, devpoll, eventport. Same interface, chosen at `./configure` time. |
| **`src/http/`** | The HTTP state machine, the **phase engine**, the upstream framework. `modules/` is **every directive you have ever typed**. |
| **`src/os/unix/`** | The syscall layer. `sendfile` per OS, process spawning, shared memory, atomics. |
| **`src/stream/`** | ⭐ **The same architecture again**, for raw TCP and UDP — nginx as an **L4 load balancer**. |
| **`src/mail/`** | And **a third time**, for IMAP, POP3 and SMTP proxying. |

> ⭐ **Three protocol trees, one core.** When you have read `src/http/` you can read
> `src/stream/` in an afternoon — **and that repetition is the argument for the architecture**.

### Two files to read before any of the code

| | |
|---|---|
| **`src/core/ngx_queue.h`** | ~50 lines of macros. An **intrusive doubly-linked list**: the link pointers live **inside the node**, so putting something in a list costs **no allocation**, and getting from a link back to the data is **a pointer subtraction**. |
| **`src/core/ngx_palloc.h`** | ⭐ **The memory pool.** nginx **does not free per-request memory.** It allocates from a pool attached to the request and **destroys the whole pool at the end**. **No refcounting. No leak class. No `free()` on the hot path** — and almost no cleanup branches anywhere in the codebase. |

> ⭐ Read these two and a large fraction of nginx **stops looking like C and starts looking like
> a language with a runtime**. Skip them and every function has three constructs you don't
> recognise.

### Ten stops

| What | File | Function |
|---|---|---|
| Process model | `os/unix/ngx_process_cycle.c` | `ngx_start_worker_processes` |
| **The loop** | `event/ngx_event.c` | `ngx_process_events_and_timers` |
| Accept + herd | `event/ngx_event_accept.c` | `ngx_event_accept` |
| epoll + stale events | `event/modules/ngx_epoll_module.c` | `ngx_epoll_process_events` |
| The parser | `http/ngx_http_parse.c` | `ngx_http_parse_request_line` |
| Phases | `http/ngx_http_core_module.c` | `ngx_http_core_run_phases` |
| Routing | `http/ngx_http_core_module.c` | `ngx_http_core_find_static_location` |
| `sendfile` | `os/unix/ngx_linux_sendfile_chain.c` | `ngx_linux_sendfile` |
| Cache LRU | `http/ngx_http_file_cache.c` | `ngx_http_file_cache_expire` |
| FastCGI records | `http/modules/ngx_http_fastcgi_module.c` | `ngx_http_fastcgi_process_record` |

---

## 🔤 The HTTP parser is a resumable state machine

```c
enum {
    sw_start = 0, sw_method, sw_spaces_before_uri, sw_schema,
    sw_schema_slash, sw_schema_slash_slash, sw_host_start,
    sw_host, sw_port, sw_after_slash_in_uri, sw_check_uri,
    sw_uri, sw_http_09, sw_http_H, sw_http_HT, ...
} state;

state = r->state;                    /* ← resume where we stopped */

for (p = b->pos; p < b->last; p++) {
    ch = *p;
    switch (state) { ... }
}
```

| | |
|---|---|
| **27 states** for the request line alone | |
| **No regex. No `strtok`. No substring. No allocation.** | One byte at a time, **and it can stop between any two.** |

> ⭐ **Why?** Because the request line may arrive in **three TCP segments**. `r->state`
> survives between calls, so the parser **picks up mid-method** if it has to.

> ⭐ **This is what non-blocking costs you at the source level: every parser has to be
> resumable, because you can be interrupted anywhere.**

📍 `ngx_http_parse.c` → `ngx_http_parse_request_line()` ~L108 → `..._header_line()` ~L871

---

## 🎛️ Eleven phases, and `return` means "suspended"

```
POST_READ → SERVER_REWRITE → FIND_CONFIG → REWRITE → POST_REWRITE →
PREACCESS → ACCESS → POST_ACCESS → PRECONTENT → CONTENT → LOG
```

```c
while (ph[r->phase_handler].checker) {
    rc = ph[r->phase_handler].checker(r, &ph[r->phase_handler]);
    if (rc == NGX_OK) { return; }     /* NOT done. SUSPENDED. */
}
```

> ⭐ **A coroutine, hand-rolled, in C, in 1999.** The request resumes in a later loop iteration
> when its event fires, **re-entering this same `while` at the phase it left off**.

Where the familiar directives live:

| Directive | Phase |
|---|---|
| `limit_req` | **PREACCESS** |
| `auth_basic` | **ACCESS** |
| `try_files` | **PRECONTENT** |
| `proxy_pass`, `fastcgi_pass`, static | **CONTENT** |

```bash
grep -rn "NGX_HTTP_.*_PHASE\].handlers" src/http/modules/
# ⭐ the map of which module runs when — a one-line answer to
#    "why did my directive not fire?"
```

📍 `ngx_http_core_module.c` → `ngx_http_core_run_phases()` ~L894

---

## 📼 FastCGI: length *and* delimiter

```
┌─────────┬──────┬───────────┬───────────────┬────────┬──────────┐
│ version │ type │ requestId │ contentLength │ padLen │ reserved │   8-byte record header
└─────────┴──────┴───────────┴───────────────┴────────┴──────────┘
  contentData[contentLength]  ·  padding

>> BEGIN_REQUEST
   01 01 00 01 00 08 00 00     ← the first 8 bytes of every FastCGI connection on earth

>> PARAMS                      ← EMPTY = end of stream
   01 04 00 01 00 00 00 00
```

> ⭐ **The empty record IS the delimiter.** An empty `PARAMS` record means *"no more environment
> variables"*. An empty `STDIN` means *"no more body"*. ⚠️ **There is no other end-of-stream
> signal. Forget it and the responder waits forever.**

**A length inside every header, and an empty record between streams** —
[Session 2](./02_Computer_Networking_Eagle_Eye_View.md)'s closing idea, **at two levels, in one
twenty-page spec**.

📍 `ngx_http_fastcgi_module.c` → `ngx_http_fastcgi_process_record()` ~L2742 → `..._create_request()` ~L858

---

## 🪜 The ladder

Seven servers, ~1,200 lines total, each one a rung:

| | What | Era | What you observe |
|---|---|---|---|
| **01-fork** | `fork()` per client | Apache 1.3, 1995 | `ps` shows one process per in-flight request |
| **02-thread** | pthread per client | Apache 2.0 worker, 1999 | prints its own **8 MB stack size** at startup |
| **03-select** | one thread, `select()` | …and the 1024 wall | ⚠️ **dies at fd 1024, and `ulimit` does not help** |
| **04-epoll** | one thread, `epoll()` | nginx, 2004 | **5,000 connections, nothing happens** |
| **05-sendfile** | read vs mmap vs sendfile | the copies, counted | **2048 syscalls become 1** |
| **06-fastcgi** | the wire protocol, both ends | CGI without the fork | your own 200-line responder |
| **07-nginx** | one `nginx.conf`, five demos | all of it, for real | routing, cache, weights, fallbacks |

> ⭐ **nginx is 200,000 lines, and the difference is every error path we ignored.** That is the
> honest reason nginx is big — **not complexity for its own sake**.

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **CERN httpd / NCSA HTTPd / Mosaic** | First server (1990) / the server Apache descends from / a **browser** |
| **MPM** | Apache's Multi-Processing Module: prefork → worker → **event** |
| **Master / worker / cache manager / cache loader** | nginx's four process roles; ⭐ the master never touches a connection |
| **`ngx_accept_disabled`** | A worker stops competing for connections past **⅞ capacity** |
| **Thundering herd** | Every worker woken by one incoming connection; fixed by `EPOLLEXCLUSIVE` / `SO_REUSEPORT` |
| **`accept_mutex`** | The old userspace workaround — **off by default since 1.11.3** |
| **Posted events** | Handlers queued during the poll and drained after it |
| **Stale event** | An `epoll` batch entry for an fd closed earlier in the same batch; caught with a **pointer low-bit generation flag** |
| **`sendfile`** | Disk → socket in-kernel; ⚠️ incompatible with anything that touches bytes (`gzip`, TLS) |
| **kTLS** | Kernel TLS — lets `sendfile` survive encryption |
| **Forward vs reverse proxy** | Next to the clients vs next to the servers |
| **`keys_zone`** | Shared memory for the cache **index** (rbtree + LRU), ~8,000 keys/MB |
| **`levels=1:2`** | Two directory levels so no directory holds a million files |
| **`inactive` vs `proxy_cache_valid`** | ⚠️ Evict-if-unread vs how-long-it's-fresh |
| **`proxy_cache_lock`** | ⭐ Anti-stampede: one request refills, the rest wait |
| **`proxy_cache_use_stale`** | Serve an old copy instead of a 502 |
| **`=` `^~` `~` prefix** | `location` forms: exact / prefix-suppressing-regex / regex / plain prefix |
| **Smooth WRR** | Weighted round robin without bursts; `effective_weight` is a passive health check |
| **`try_files`** | Try each candidate; ⭐ **the last entry is never tested** |
| **Named location `@name`** | Reachable only from `try_files` / `error_page` |
| **`ngx_queue.h`** | Intrusive doubly-linked list — allocation-free list membership |
| **`ngx_palloc.h`** | ⭐ Per-request memory pool, destroyed wholesale; no `free()` on the hot path |
| **Phase engine** | Eleven phases; `return NGX_OK` means **suspended**, not finished |
| **Resumable parser** | State survives between calls because a request can arrive in pieces |

---

## 🎯 Session Takeaways

1. ⭐ **Ask the other question.** Apache spent a decade making the per-connection worker cheaper; nginx asked **why there was one**. When a whole industry is optimising the same thing, **the opportunity is usually one level up**.
2. ⭐ **Check whether the constraint still exists.** Thread-per-connection died because a thread cost 8 MB and a context switch. **Goroutines and virtual threads brought it back** when those numbers changed. **Know which of your rules are laws and which are 2004.**
3. ⭐ **The data structure is the documentation.** Prefixes are a tree, so longest wins. Regexes are an array, so first wins. The precedence rules are **the only rules those structures could have**.
4. ⭐ **Amortise the setup.** Prefork, pre-thread, servlets, connection pools, FastCGI, upstream keepalive — **six names for one move**.
5. **All of nginx is six lines**, and line 2 (`epoll_wait`) is where a worker spends 99.9% of its life. The timer is an *argument* to the sleep — nginx never polls for timeouts.
6. **One process per core, a master that never touches a connection**, and the process count does not move under load.
7. ⭐ **`select` is O(watched), `epoll` is O(active)** — 30,000 units of work vs 10, for the same ten events. And `ulimit -n` cannot move `FD_SETSIZE`.
8. **Every event-loop author writes the stale-event bug once.** nginx steals the always-zero low bit of an aligned pointer as a generation flag.
9. ⭐ **`sendfile` removes the copy through your address space** — but it wins as *headroom under concurrency*, not as a faster single transfer. **A benchmark that doesn't model the bottleneck measures the wrong thing.**
10. **A reverse proxy's killer feature is absorbing slow clients** — your app server never talks to a phone on 2G.
11. ⭐ **`proxy_cache_lock on` and `proxy_cache_use_stale` are the two lines that save you at 3am**, and both are off by default.
12. **`^~` beats a regex; a regex beats a plain prefix; `=` beats everything.** Order in the file only matters *among regexes*.
13. **`try_files`' last argument is the fallback, never a candidate** — and it is the whole of "pretty URLs" in every framework.
14. ⭐ **Navigate by structure, not coordinates.** `grep -rn "^function_name("` works because of nginx's brace style; line numbers drift, names don't.

---

## 🔗 References

- nginx source — https://github.com/nginx/nginx
- nginx docs — https://nginx.org/en/docs/
- Development guide — https://nginx.org/en/docs/dev/development_guide.html
- `ngx_http_core_module` (location, try_files) — https://nginx.org/en/docs/http/ngx_http_core_module.html
- `ngx_http_proxy_module` (caching) — https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- `ngx_http_upstream_module` — https://nginx.org/en/docs/http/ngx_http_upstream_module.html
- "Inside NGINX" — https://blog.nginx.org/blog/inside-nginx-how-we-designed-for-performance-scale
- The C10K problem — http://www.kegel.com/c10k.html
- Apache MPMs — https://httpd.apache.org/docs/2.4/mpm.html
- FastCGI spec — https://fastcgi-archives.github.io/FastCGI_Specification.html
- `man 2 sendfile`, `man 7 epoll`

---

## ➡️ Next

[Session 5 — Evolution of HTTP](./05_Evolution_of_HTTP.md) — we put a reverse proxy in front of
everything and made the app servers interchangeable. **Where did all the state go?**
