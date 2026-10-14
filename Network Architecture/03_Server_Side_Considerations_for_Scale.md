# Session 3 — Server Side Considerations for Scale 📈

> **Topics:** fork vs thread vs event loop · `select` & `epoll` · Timeouts · CGI · FastCGI ·
> Servlets · Is everything a web server? · File descriptors, memory, context switches, queueing
> · C10K · Little's Law · Apache · HAProxy · Varnish · nginx
>
> 📄 Source: *CN at Scaler — Lesson 3*, "One Process, Many Clients — Scaling Servers".

**One question: how does one box hold ten thousand clients at the same time?**

> ⭐ The answer every team reached independently, thirty years apart: **the loop is the
> architecture.**

---

## 📑 Table of Contents

1. [Three ways to serve many clients](#-three-ways-to-serve-many-clients)
2. [`fork()`: a whole process per client](#-fork-a-whole-process-per-client)
3. [`select()`: one thread, every client](#-select-one-thread-every-client)
4. [select's ceiling is compiled in](#-selects-ceiling-is-compiled-in)
5. [In production you don't pick one — you stack them](#-in-production-you-dont-pick-one--you-stack-them)
6. [Timeouts are the client's half of the contract](#-timeouts-are-the-clients-half-of-the-contract)
7. [CGI: every request forks a copy of your program](#-cgi-every-request-forks-a-copy-of-your-program)
8. [HTTP headers become environment variables](#-http-headers-become-environment-variables)
9. [The CGI program is just a program that prints](#-the-cgi-program-is-just-a-program-that-prints)
10. [Copy the whole program, then throw it away](#-copy-the-whole-program-then-throw-it-away)
11. [FastCGI: keep the process, talk over a socket](#-fastcgi-keep-the-process-talk-over-a-socket)
12. [A FastCGI request is a stream of typed records](#-a-fastcgi-request-is-a-stream-of-typed-records)
13. [The empty record is the delimiter](#-the-empty-record-is-the-delimiter)
14. [Servlets are the same idea wearing a JVM](#-servlets-are-the-same-idea-wearing-a-jvm)
15. [Isn't everything a web server?](#-isnt-everything-a-web-server)
16. [HTTP is stateless. What you scale next may not be](#-http-is-stateless-what-you-scale-next-may-not-be)
17. [Four walls, and you will hit all of them](#-four-walls-and-you-will-hit-all-of-them)
18. [C10K, C10M, and today](#-c10k-c10m-and-today)
19. [Every thread costs memory before it does any work](#-every-thread-costs-memory-before-it-does-any-work)
20. [The syscall tax](#-the-syscall-tax)
21. [Little's Law: concurrency = throughput × latency](#-littles-law-concurrency--throughput--latency)
22. [In the wild: Apache, HAProxy, Varnish, nginx](#-in-the-wild-apache-haproxy-varnish-nginx)
23. [Go and read the actual code](#-go-and-read-the-actual-code)
24. [Key Terms Recap](#-key-terms-recap)
25. [Session Takeaways](#-session-takeaways)

---

## 🔀 Three ways to serve many clients

> **A thread per client is a bet you lose at ten thousand.** Only one of these survives contact
> with scale.

| **Fork per request** | **Thread per request** | **One loop, many sockets** |
|---|---|---|
| A whole **process** copied for every client. | Cheaper than fork — latency drops. **It does not go away.** | `select` or `epoll`. One thread watches every socket and **only wakes for the ones that are ready**. |
| Simple, isolated, and the **most expensive thing you can do** per connection. | Every thread still costs **a stack** before it does any work. | ⭐ **This is the one that scales.** |

> ⭐ **What actually ships:** most of the time we do **neither purely** — we **pre-fork or
> pre-thread a pool**, and each worker runs its **own `select`/`epoll` loop**.
> **Isolation from the processes, concurrency from the loop.**

---

## 🍴 `fork()`: a whole process per client

```c
while (1) {
    int client_fd = accept(server_fd, NULL, NULL);

    if (fork() == 0) {                 // child
        char buf[4096];
        int n;
        while ((n = read(client_fd, buf, sizeof(buf))) > 0)
            write(client_fd, buf, n);
        close(client_fd);
        return 0;
    }
    close(client_fd);                  // parent drops its copy
}
```

**What it costs:**

- A full **process image** per connection
- **Page tables, file descriptors, scheduler entry** — all duplicated
- ⚠️ **You pay it while the user waits**

Read the code: `listen(server_fd, 1)` is a backlog of **one**; the child echoes then exits; the
parent closes its copy and loops.

---

## 🔁 `select()`: one thread, every client

```c
int clients[FD_SETSIZE];
int nclients = 0;

while (1) {
    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(server_fd, &readfds);
    int maxfd = server_fd;

    for (int i = 0; i < nclients; i++) {          // ⚠️ rebuild the set EVERY time
        FD_SET(clients[i], &readfds);
        if (clients[i] > maxfd) maxfd = clients[i];
    }

    select(maxfd + 1, &readfds, NULL, NULL, NULL);
    /*     readfds ──┘  writefds  exceptfds  timeout ──┘ */

    if (FD_ISSET(server_fd, &readfds))
        clients[nclients++] = accept(server_fd, NULL, NULL);

    for (int i = 0; i < nclients; i++) {
        int fd = clients[i];
        if (!FD_ISSET(fd, &readfds)) continue;

        char buf[4096];
        int n = read(fd, buf, sizeof(buf));
        if (n <= 0) {
            close(fd);
            clients[i] = clients[--nclients];     // ⭐ O(1) delete
            i--;
        } else {
            write(fd, buf, n);
        }
    }
}
```

> ⭐ **Two lines worth stopping on.**
> `clients[i] = clients[--nclients]; i--;` — an **O(1) delete**: move the last element into the
> hole instead of shifting everything.
> `select(..., NULL)` — **that last `NULL` is the timeout.** See [below](#-timeouts-are-the-clients-half-of-the-contract).

---

## 🧱 select's ceiling is compiled in

> **`FD_SETSIZE` = 1024.** That array is not a style choice — **it is the hard limit.**

`fd_set` is a **fixed-width bitmap**. On glibc that width is 1024 bits — **descriptor 1024
cannot be represented at all.**

| **`select` — O(n) every call** | **`epoll` — O(ready)** |
|---|---|
| You **rebuild the set on every iteration** | **Register each fd once**, with `epoll_ctl` |
| The kernel **scans every fd**, ready or not | `epoll_wait` returns **only what actually fired** |
| ⚠️ **10,000 idle sockets cost the same as 10,000 busy ones** | ⭐ **Idle connections cost nothing to wait on** |

Same idea, different name: **`kqueue`** (BSD, macOS) · **IOCP** (Windows) · **`io_uring`**
(modern Linux).

> ⭐ **The number to remember: 1024.** It is `FD_SETSIZE`, it is your default `ulimit`, and it
> is the **K in C10K**. *One wall, three names.*

---

## 🏗️ In production you don't pick one — you stack them

```
AT STARTUP          PER WORKER           ON ACCEPT              RESULT
fork/spawn a pool   each runs its own    SO_REUSEPORT lets      crash isolation from
of workers —   ──▶  select or epoll ──▶  the kernel spread ──▶  the processes,
often one per core  loop over many       new connections        concurrency from
                    sockets              across them            the loop
```

> ⭐ This is **not a theoretical design.** It is **Apache's event MPM**, it is **nginx's
> master-and-workers**, and it is what **the Go runtime does for you invisibly** — goroutines
> multiplexed onto OS threads by a scheduler sitting on top of `epoll`.

---

## ⏲️ Timeouts are the client's half of the contract

The server may be busy reading, writing, or accepting. **Never wait indefinitely.**

In a `select` loop you are waiting on three different things:

| Set | Waiting for |
|---|---|
| **`readfds`** | some new content to arrive |
| **`writefds`** | some socket allowing us to write |
| **`exceptfds`** | sockets being connected and closed |

```c
select(maxfd + 1, &readfds, NULL, NULL, NULL);
/*                                      ↑ timeout — we passed NULL */
```

> ⚠️ **`NULL` timeout = block forever.** One wedged client and the whole loop — **every other
> connection on it** — stops.

⭐ On the client side the same rule: **set a deadline, then retry with backoff.**

---

## 🧰 CGI: every request forks a copy of your program

Apache was the most popular HTTP server on earth, and **this is how it ran your code.**

```
                  HTTP request
                       │
                       ▼
                ┌──────────────┐
                │ Apache httpd │
                └──┬───┬───┬───┘
            envp   │   │   │  stdin pipe / stdout pipe
                   ▼   ▼   ▼
               ┌──────────────┐
               │ CGI process  │
               └──────┬───────┘
                      │ stderr
                      ▼
               Apache error log
```

**Server side: wire up three pipes, then `exec`.**

```text
Set stdin  for the new process to a pipe/fd we control
Set stdout for the new process to another pipe/fd we control
Set stderr for the new process to yet another pipe/fd we control

text from client      → stdin
text written to stdout → client
text written to stderr → error log
```

> 💡 **The real thing:** `apache/httpd` → `modules/generators/mod_cgi.c` L576
> `run_cgi_child()`. Creates the child, attaches the three pipes, and **sets a timeout on each**
> so a hung script cannot hold the worker forever.

---

## 🔤 HTTP headers become environment variables

The translation layer between **a protocol** and **a process**.

> ⭐ **The convention:** header `User-Agent: curl` becomes `HTTP_USER_AGENT=curl`.
> **Upper-case it, swap dashes for underscores, prefix with `HTTP_`.**
> **Every framework you have ever used still carries this shape.**

Plus the non-header variables: `GATEWAY_INTERFACE`, `SERVER_PROTOCOL`, `REQUEST_METHOD`,
`QUERY_STRING`.

> 💡 The real thing: `server/util_script.c` L409 `ap_add_cgi_vars()`, with
> `ap_add_common_vars()` above it doing the rest.

---

## 🖨️ The CGI program is just a program that prints

**No server library. No framework.** Read the environment, write to stdout.

```text
Get environment variable REQUEST_METHOD      // GET or POST
If POST → read from stdin
If GET  → parse QUERY_STRING
Output "Content-Type: text/html", a blank line, then the body
```

> ⭐ **Two lines.** The header block, then **a blank line**, then the body. That blank line is
> **the delimiter** — the same framing question from
> [Session 2](./02_Computer_Networking_Eagle_Eye_View.md). Apache reads your headers up to it
> and streams everything after it to the client.

> 💡 **That is the whole contract.** Any language that can read an environment variable and
> print to standard output can serve HTTP — **which is exactly why the early web was written
> in Perl and shell.**

---

## ♻️ Copy the whole program, then throw it away

Forking and executing is costly. **CGI does it on every single hit.**

| **The copy** | **The fix people tried** | **The fix that won** |
|---|---|---|
| The whole program image is created, run **once**, and discarded. | **Compile the module *into* the server** — `mod_php`, `mod_perl`. No new process per request… | **Keep a long-lived process of your own** and let the web server talk to it over a Unix or TCP socket, with a reduced vocabulary. |
| That is what your shell does for every command you type — ⚠️ except your shell is not doing it **a thousand times a second**. | ⚠️ …but now your application **shares an address space** with your web server, and **one segfault takes both down**. | ⭐ **That is FastCGI.** |

> ⭐ **Notice the move:** take the setup cost **off the request path** and pay it **once at
> startup**. Exactly what pre-forking did for connections.

---

## 🔌 FastCGI: keep the process, talk over a socket

```
  clients    ──HTTP──▶   nginx / httpd   ──FastCGI──▶   php-fpm
thousands,                user-facing:                  internal:
many of them slow          absorbs slow connections,    a fixed pool of
                           TLS, buffering               long-lived workers
```

> ⭐ **You define an upstream.** The user-facing server handles **slow clients**; an internal
> server does **the work**. That split is the whole design — and it comes back in
> [Session 4](./04_Nginx_Deep_Dive.md).

| | |
|---|---|
| **A modified HTTP, with less vocabulary** | Same information — method, headers, query string, body — but **binary, typed, and multiplexed**. **No parsing a text protocol twice.** |
| **What you actually write** | You may still get environment variables — but more often a **request object** with the headers and query string already decoded. |

---

## 📼 A FastCGI request is a stream of typed records

```text
FCGI_BEGIN_REQUEST

FCGI_PARAMS
    REQUEST_METHOD  = POST
    SCRIPT_FILENAME = /var/www/test.php
    QUERY_STRING    = x=10
    CONTENT_TYPE    = application/x-www-form-urlencoded
    CONTENT_LENGTH  = 17
    HTTP_HOST       = localhost
    HTTP_USER_AGENT = curl/...

FCGI_PARAMS
    <empty record means parameters finished>

FCGI_STDIN
    name=alice&age=20

FCGI_STDIN
    <empty record means stdin finished>
```

…and the response comes back the same way:

```text
FCGI_STDOUT
    Content-Type: text/html

    <html>...</html>

FCGI_STDOUT
    <empty>

FCGI_STDERR
    ...

FCGI_END_REQUEST
```

| | |
|---|---|
| **Same nouns as CGI** | `REQUEST_METHOD`, `QUERY_STRING`, `CONTENT_LENGTH` — ⭐ **the CGI environment survived. Only the transport changed:** records on a socket instead of `envp` on a fork. |
| **stdin is the body** | `name=alice&age=20` — seventeen bytes, exactly the `CONTENT_LENGTH` declared above it. |
| **stdout goes to the client** | Headers, blank line, body — **byte for byte what a CGI program printed**. |
| **stderr goes to the log** | ⭐ A **separate record type**, so your debug output can never corrupt the page. The same split as the three pipes. |

---

## 🧩 The empty record is the delimiter

[Session 2](./02_Computer_Networking_Eagle_Eye_View.md) ended on framing: **length or
delimiter, no third option.** Here they are, **in one protocol**.

| **Length** | **Delimiter** |
|---|---|
| Every **record header carries its own content length**. The reader knows exactly how many bytes to take **before** it takes them — so a body can contain **any byte at all**, including newlines and nulls. | A **record of length zero** means "that stream is finished". ⭐ Not a byte pattern in the data — **a structural marker that cannot collide with your content**. |
| `CONTENT_LENGTH = 17` does the same job one level up. | The blank line after `Content-Type` is the same trick in text. |

> ⭐ SMS chose length. SMTP chose a dot. IMAP chose both. **FastCGI chose both too — and for
> the same reason.**

---

## ☕ Servlets are the same idea wearing a JVM

| | |
|---|---|
| **The server is the runtime** | Jetty and Tomcat **act as the web server themselves**. There is no separate httpd in front doing the forking — the JVM is already running your code. |
| **Pre-threading** | A pool of threads created at startup. A request is handed to an idle thread, which runs your servlet and returns to the pool. ⭐ Exactly the pre-threading from block 01. |
| **Isolation by convention** | Servlets are isolated by **class loader and thread**, not by process. Cheaper than fork — ⚠️ and **one runaway servlet can still hurt its neighbours**. |

> ⭐ **CGI, FastCGI, servlets and every modern framework are answering one question: how do we
> run user code per request without paying to create the world each time?**

---

## 🌍 Isn't everything a web server?

**Almost everything runs one.** Not everything *is* one — and the difference decides which
scaling tricks you get.

| **Yes — it speaks HTTP** | **No — and it does not need to** |
|---|---|
| Your Wi-Fi router admin page | **Redis** — its own line protocol, RESP |
| Modern agent runtimes and cloud tooling | **MySQL** — its own binary wire protocol |
| Most Node applications | **MQTT** brokers across the whole IoT estate |
| Firestore | Messenger backends — WhatsApp-shaped things |
| CouchDB, which has had REST for years | **Kafka** natively — a binary protocol |
| Kafka, *if* you put the REST proxy in front | |

> ⚠️ **Everything you are about to learn about scaling web servers assumes HTTP's properties.
> Change the protocol and the advice changes with it.**

---

## 🧊 HTTP is stateless. What you scale next may not be

| **A web server can hang up** | **A database wants to stay** |
|---|---|
| Every request carries everything it needs. So **any box can answer any request**, you can close the connection when you like, and a load balancer can send the next one anywhere. | Redis or MySQL would rather hold a **persistent connection** than pay TCP connect **+ handshake + auth + session setup** on every query. |
| ⭐ **Horizontal scaling is free-ish.** Add a server, add it to the pool, done. **The statelessness is what makes that legal.** | ⭐ **So the problem changes shape.** The question is no longer requests per second. It is: **how many persistent connections can one box hold at once?** |

---

## 🧱 Four walls, and you will hit all of them

> Every scaling technique in this course is a way of **dodging one of these**.

| # | Wall | |
|---|---|---|
| **01** | **File descriptors** | A connection **is** a descriptor, and descriptors are rationed. Your default is still **1024**. |
| **02** | **Memory** | A **stack per thread**, a **buffer per connection**. Paid **before any work happens**. |
| **03** | **Context switches** | Every `read` and `write` crosses the kernel boundary. So does **every syscall**. |
| **04** | **The queue** | Latency and throughput are **not independent**. ⭐ **Being slow costs you memory.** |

---

## 📊 C10K, C10M, and today

| **1999 — C10K** | **2013 — C10M** | **Today** |
|---|---|---|
| **10,000** | **10,000,000** | **2–3M** |
| Dan Kegel names the problem: can one box hold ten thousand simultaneous persistent connections? **At the time, no.** | Robert Graham argues **the kernel is the problem, not the solution.** Bypass it and the number moves by **three orders of magnitude**. | People have demonstrated **two to three million** connections on a single server. |

```bash
$ ulimit -n
1024    # ⚠️ the soft limit on most distributions, unchanged since the problem was named
```

> ⭐ **The problem moved; the default did not.**

---

## 💾 Every thread costs memory before it does any work

| **OS thread** | **Goroutine** |
|---|---|
| **8 MB** default stack, **reserved up front** | **2 KB** initial stack, **grown on demand** |
| ⚠️ 10,000 threads reserves roughly **80 GB of address space** before a single byte of your data exists | ⭐ **Four thousand times smaller.** This single number is most of why **Go took over this problem space**. |

> ⭐ **And underneath, it is the same loop.** Goroutines are lightweight because the Go runtime
> multiplexes them onto a few OS threads using a **netpoller built on `epoll`**, and runs its
> own scheduler on top. **You write blocking reads; the runtime parks you on a poll.**

> 💡 The more requests you handle at the same time, the more memory you need — **the only
> question is how much per request.**

---

## 🚧 The syscall tax

> Every read and write is a trip across the kernel boundary. **In fact, every system call is.
> At a million operations a second, the tax *is* the workload.**

**The tax:** user space → kernel space and back: save state, switch page tables, validate,
copy, return. **Hundreds of nanoseconds each** — and ⚠️ **Spectre and Meltdown mitigations made
it worse, not better.**

| **Bypass the kernel** | **Or make fewer calls** |
|---|---|
| Some people have implemented **TCP in user space** and bypassed the kernel entirely for well-known internal networks: **DPDK, netmap, mTCP, Seastar**. | ⭐ **`sendfile()`** moves a file to a socket **without a user-space round trip**. |
| ⚠️ You give up **every tool you own** and you get the packets. | **`io_uring`** submits a **batch** of operations through a shared ring instead of one syscall each. |

> ⭐ **Remember `sendfile`** — it is the reason nginx serves static files the way it does, and
> it comes back below.

---

## ⚖️ Little's Law: concurrency = throughput × latency

```
connections in flight  =  requests per second  ×  seconds per request
```

| | |
|---|---|
| **Ten times the cost** | At **100 ms** you hold a **thousand** connections. At **one second**, **ten thousand** — for ***identical* traffic**. |
| ⭐ **Slowness is a memory bug** | Which is why high-latency work goes **asynchronous**: take it off the request path and the queue drains. |

> ⚠️ **You cannot configure your way past this one.** Getting faster is the only thing that
> reduces what you are holding.

> 💡 **The restaurant analogy.** Tables occupied = diners arriving per hour × hours per meal.
> Serve the same number of people but make each meal twice as long and you need twice the
> tables. No amount of "tuning the waiter" changes that arithmetic.

```bash
ss -s         # sockets in flight — check the prediction
```

---

## 🏭 In the wild: Apache, HAProxy, Varnish, nginx

### Apache: prefork → worker → event

> **It took twenty years, and it ended up at a loop too.**

| **prefork MPM** | **worker MPM** | **event MPM** |
|---|---|---|
| A pool of **processes, one connection each**. Bulletproof, compatible with every non-thread-safe module ever written — and the **most expensive per connection**. | Processes each running **many threads**. Cheaper per connection — ⚠️ but **a thread is still pinned to a connection, including while it sits idle on keep-alive**. | ⭐ A dedicated **listener thread** per process parks idle keep-alive sockets on **`epoll`** and hands a worker thread **only the sockets with actual work**. **The default on Unix today.** |

> ⭐ **The keep-alive problem in one line:** under *worker*, a client that has finished its
> request but is holding the connection open **still owns a thread**. *Event* takes the socket
> back and gives the thread away. **That is our `select` loop, arriving inside Apache in 2012.**

### HAProxy: a select loop from before epoll existed

- **The timeline explains the design.** HAProxy arrives in **2001**; `epoll` only lands in Linux
  2.5.44 in late **2002**. So it was largely `select`, **because `select` was what there was**.
  It moved to `epoll` later, and only became **multi-threaded in 1.8, in 2017**.
- **One process, enormous throughput.** For most of its life a **single event-driven process
  saturated a NIC**. ⭐ That is the loop argument made as loudly as it can be made.
- **It introduced the load balancer** as a tier of its own — for many teams the first box that
  sat in front of the application servers and chose between them.
- **And it absorbs connection churn** by holding a **pool** open to the upstream — the
  persistent-connection argument, applied by a proxy on your behalf.

### Varnish: the first popular caching reverse proxy

| | |
|---|---|
| **Squid cached for the client** | Squid sat **next to the users**, on the way out. ⭐ **Varnish turned it around** and put the cache **in front of the origin**, on the way in. Same mechanism, opposite direction, entirely different business. |
| **How it actually runs** | An **acceptor thread** per listening point per pool. A **worker thread per active connection**, from pools defaulting to **min 100 / max 5000**. **Idle descriptors** — clients between requests, backends between fetches — are handed to a **waiter**, which is `epoll` on Linux and `kqueue` on BSD. |
| **Still everywhere** | **Fastly's edge is built on Varnish, VCL and all.** ⭐ When you write a VCL snippet for a CDN in 2026, you are configuring a program written in **2006**. |

> ⭐ **Threads for the work, a loop for the waiting** — the same split Apache arrived at with
> the event MPM.

### nginx: epoll plus sendfile — never copy the bytes at all

```c
read(file_fd, buf, n);                  /* disk → kernel → your buffer */
write(sock_fd, buf, n);                 /* your buffer → kernel → socket */

sendfile(sock_fd, file_fd, NULL, n);    /* kernel → socket. you never touch it. */
```

| | |
|---|---|
| **Master and workers** | One **master**, then **one worker process per CPU core**. Each worker is a **single thread running one `epoll` loop** over thousands of connections. |
| **The first reverse proxy** | Then promptly **abused** for caching, load balancing, TLS termination, rate limiting and everything else. ⭐ **It became the default shape of an edge.** |
| **And a thread pool, later** | ⚠️ **Disk reads can block even in a loop.** Since **1.7.11** nginx offloads those to a thread pool — because a **page fault on a cache miss stalls every connection on that worker**. |

### All the options, side by side

| | Concurrency model | Born as | The idea it popularised | In the wild |
|---|---|---|---|---|
| **Apache** | prefork → worker → event (listener thread + epoll) | **1995** — the web server | Modules, and **CGI** as a way to run anyone's code | Everywhere. **Akamai started here** |
| **HAProxy** | select, then epoll; multi-threaded only since 1.8 | **2001** — TCP/HTTP proxy | **The load balancer as a tier of its own** | The default LB in front of everything |
| **Varnish** | thread per active connection + epoll waiter for idle | **2006** — HTTP accelerator | **Caching reverse proxy** — Squid, turned around | **Fastly's edge**, VCL and all |
| **nginx** | master + worker per core, one epoll loop each | **2004** — the answer to C10K | **`sendfile`**: never copy the bytes into user space | The default edge. Most CDNs |

> ⭐ **Read the "born as" column top to bottom: four independent teams, four starting points,
> and every one of them ended up with an event loop and a small pool of workers.**

---

## 📖 Go and read the actual code

Every claim above is a file you can open this evening.

| Repo | File | What's in it |
|---|---|---|
| `apache/httpd` | `modules/generators/mod_cgi.c` L576 | `run_cgi_child()` — fork, three pipes, a timeout on each |
| `apache/httpd` | `server/util_script.c` L409 | `ap_add_cgi_vars()` — HTTP headers become the environment |
| `nginx/nginx` | `src/event/modules/ngx_epoll_module.c` | The epoll loop itself |
| `nginx/nginx` | `src/os/unix/ngx_linux_sendfile_chain.c` | `sendfile()`, where the copy does not happen |
| `haproxy/haproxy` | `src/ev_epoll.c` | The poller — one file per platform; `ev_select.c` still sits beside it |
| `varnishcache/varnish-cache` | `bin/varnishd/waiter/cache_waiter_epoll.c` | The waiter that holds idle connections |
| `golang/go` | `src/runtime/netpoll_epoll.go` | Where your blocking read actually parks |

> ⭐ **Pick one.** Reading a poller implementation end to end is a two-hour job and it changes
> how you read every server you meet afterwards — **they are all the same shape once you have
> seen one.**

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Multiplexing** | One thread watching many sockets, waking only for ready ones |
| **`FD_SETSIZE`** | ⭐ 1024 — `select`'s compiled-in ceiling; the **K in C10K** |
| **`select` vs `epoll`** | O(n) rebuild-every-call vs O(ready) register-once |
| **`kqueue` / IOCP / `io_uring`** | The same idea on BSD/macOS, Windows, modern Linux |
| **Pre-fork / pre-thread** | Create the pool at startup; pay setup once, not per request |
| **`SO_REUSEPORT`** | Let the kernel spread new connections across worker processes |
| **CGI** | Fork+exec a program per request; headers become env vars, stdout is the response |
| **`HTTP_*` convention** | `User-Agent:` → `HTTP_USER_AGENT` — upper-case, dashes→underscores |
| **`mod_php` / `mod_perl`** | Compile the interpreter into the server; ⚠️ shared address space |
| **FastCGI** | Long-lived worker pool reached over a socket with typed binary records |
| **`FCGI_PARAMS` / `FCGI_STDIN` / `FCGI_STDOUT` / `FCGI_STDERR`** | The record types; an **empty record ends a stream** |
| **php-fpm** | The FastCGI process manager for PHP |
| **Servlet** | Java's answer: the JVM *is* the server, with a pre-threaded pool |
| **C10K / C10M** | 10,000 (1999) and 10 million (2013) concurrent connections |
| **Kernel bypass** | DPDK, netmap, mTCP, Seastar — userspace TCP, no kernel |
| **`sendfile()`** | ⭐ Disk → socket without a user-space copy |
| **`io_uring`** | Batch syscalls through a shared ring |
| **Little's Law** | ⭐ `concurrency = throughput × latency` |
| **MPM** | Apache's Multi-Processing Module: prefork / worker / **event** |
| **VCL** | Varnish Configuration Language — still what you write at Fastly |

---

## 🎯 Session Takeaways

1. ⭐ **The loop is the architecture.** Four independent teams, thirty years apart, all converged on an **event loop plus a small pool of workers**.
2. ⭐ **Amortise the setup.** Pre-fork, pre-thread, FastCGI, connection pools, servlets — every one is the same move: **take the expensive setup off the request path and pay it once at startup.**
3. ⭐ **Nothing is free per connection:** a descriptor, a stack, a buffer, a scheduler entry. **Multiply by ten thousand before you choose a design** — that multiplication is the whole discipline.
4. ⭐ **Framing is still length or delimiter.** FastCGI uses a length *inside* a record and an **empty record** between them. **There is never a third option.**
5. ⭐ **Concurrency = throughput × latency.** You cannot configure past it. **Slowness is a memory bug**, and getting faster is the only fix.
6. **`select` is O(n) and capped at 1024; `epoll` is O(ready) and costs nothing for idle connections.** 1024 is also your default `ulimit`, and the K in C10K.
7. **`NULL` as `select`'s timeout blocks forever** — one wedged client stalls every connection on that loop. Always set a deadline.
8. **CGI's contract survived everything.** `REQUEST_METHOD`, `QUERY_STRING`, headers-blank-line-body — FastCGI changed only the **transport**.
9. **An 8 MB thread stack × 10,000 is 80 GB of address space before any data exists.** A goroutine starts at **2 KB** — and still parks on `epoll` underneath.
10. **Every syscall is a kernel crossing**, made worse by Spectre/Meltdown mitigations. `sendfile` and `io_uring` exist to make **fewer** of them.
11. **HTTP's statelessness is what makes horizontal scaling legal.** Databases want persistent connections, so their scaling question is *connections held*, not *requests per second*.
12. **Keep-alive is what killed thread-per-connection.** An idle client holding a thread is pure waste — Apache's event MPM takes the socket back.

---

## 🔗 References

- The C10K problem (Dan Kegel) — http://www.kegel.com/c10k.html
- The C10M problem (Robert Graham) — http://c10m.robertgraham.com/
- `man 2 select`, `man 7 epoll`, `man 2 sendfile`, `man 7 io_uring`
- CGI — RFC 3875 — https://www.rfc-editor.org/rfc/rfc3875
- FastCGI specification — https://fastcgi-archives.github.io/FastCGI_Specification.html
- Apache MPMs — https://httpd.apache.org/docs/2.4/mpm.html
- nginx architecture — https://nginx.org/en/docs/events.html
- HAProxy — https://docs.haproxy.org/
- Varnish architecture — https://varnish-cache.org/docs/trunk/reference/
- Go netpoller — https://github.com/golang/go/blob/master/src/runtime/netpoll_epoll.go
- Little's Law — https://en.wikipedia.org/wiki/Little%27s_law

---

## ➡️ Next

[Session 4 — nginx Deep Dive](./04_Nginx_Deep_Dive.md) — we keep arriving at the same shape.
Now take the server that got there first and read it properly.
