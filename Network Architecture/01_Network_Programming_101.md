# Session 1 — Network Programming 101 🔌

> **Topics:** The seven system calls · Ports & privilege · The accept queue · Signals &
> SIGPIPE · Clients you already have · Ephemeral ports · Byte order · DNS in a function call ·
> HTTP & curl · Many clients (fork / select / epoll) · tcpdump · TLS · Protocol design
>
> 📄 Source: *CN at Scaler — Lesson 1*, "Network programming, from the socket up".

Built **bottom-up**. We start with the smallest program that can accept a TCP connection and
end by designing a binary protocol. Everything you have ever used — Express, Flask,
`net/http`, Spring — is a wrapper around the same seven calls.

```
socket → bind → listen → accept → read → write → close
```

---

## 📑 Table of Contents

1. [The server is seven system calls](#-the-server-is-seven-system-calls)
2. [A working echo server in 20 lines](#-a-working-echo-server-in-20-lines)
3. [Ports, and why 1024 is a line in the sand](#-ports-and-why-1024-is-a-line-in-the-sand)
4. [Thought experiment: what breaks if you skip a call?](#-thought-experiment-what-breaks-if-you-skip-a-call)
5. [One `read()` is not a conversation](#-one-read-is-not-a-conversation)
6. [The accept queue — `listen(fd, backlog)`](#-the-accept-queue--listenfd-backlog)
7. [Signals, and the one that will kill you](#-signals-and-the-one-that-will-kill-you)
8. [You already have a client](#-you-already-have-a-client)
9. [Writing the client](#-writing-the-client)
10. [Ephemeral ports](#-ephemeral-ports)
11. [Byte order and `htons()`](#-byte-order-and-htons)
12. [`gethostbyname()` is a whole protocol](#-gethostbyname-is-a-whole-protocol)
13. [Where we are on the OSI stack](#-where-we-are-on-the-osi-stack)
14. [HTTP & curl](#-http--curl)
15. [Many clients at once](#-many-clients-at-once)
16. [Socket options worth knowing](#-socket-options-worth-knowing)
17. [Stop guessing — look at the bytes](#-stop-guessing--look-at-the-bytes)
18. [SSL/TLS secures TCP, not HTTP](#-ssltls-secures-tcp-not-http)
19. [Protocol design](#-protocol-design)
20. [Key Terms Recap](#-key-terms-recap)
21. [Session Takeaways](#-session-takeaways)

---

## 🧱 The server is seven system calls

```
    1        2        3         4        5       6        7
 socket → bind → listen → accept → read → write → close
          └──── only a server makes these four ────┘
```

> 💡 **The shop analogy.** `socket()` = buy a telephone. `bind()` = get assigned a phone
> *number*. `listen()` = plug it in and switch the ringer on. `accept()` = pick up a specific
> call. `read`/`write` = the conversation. `close()` = hang up.
> A **client** skips the first three middle steps entirely — it just dials.

⭐ A client only needs `socket → connect → write → read → close`. **`bind`, `listen` and
`accept` are the server's half of the contract.**

---

## 💻 A working echo server in 20 lines

Send it anything; it sends it back, once.

```c
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

int main() {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in addr = {0};
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;      // every interface
    addr.sin_port        = htons(2026);     // host → network byte order

    bind(server_fd, (struct sockaddr*)&addr, sizeof(addr));
    listen(server_fd, 1);                   // 1 = backlog

    while (1) {
        int client_fd = accept(server_fd, NULL, NULL);
        char buf[4096];
        int n = read(client_fd, buf, sizeof(buf));
        write(client_fd, buf, n);
        close(client_fd);
    }
}
```

| Argument | Meaning |
|---|---|
| `AF_INET` | IPv4 address family (`AF_INET6` for IPv6) |
| `SOCK_STREAM` | TCP — a reliable byte stream (`SOCK_DGRAM` = UDP) |
| `INADDR_ANY` | bind to **all** interfaces, not one address |
| `htons(2026)` | the port, converted to network byte order |

Compile it and talk to it:

```bash
gcc -o echo_server echo_server.c
./echo_server &
nc localhost 2026
```

⭐ Two commands and you have a network service running on your laptop. That is the whole
mystery removed.

---

## 🚪 Ports, and why 1024 is a line in the sand

> **Everything below 1024 belongs to root.** Not a rule you cannot break — a rule about *who
> is allowed* to break it.

| Range | Who may bind | Examples |
|---|---|---|
| **< 1024** (well-known) | **root only** | 80 HTTP · 443 HTTPS · 25 SMTP · 21 FTP · 110 POP |
| **≥ 1024** | anyone | 3000 Node · 8080 alt-HTTP · 6379 Redis · 2026 ours |

> ⚠️ **Why it matters.** Binding port 80 means running as **root**. Running as root means a
> bug in your request parser is a **root compromise** — not a crashed web app, a owned machine.

⭐ That is why real deployments bind **8080 as an unprivileged user** and let a front proxy —
which does almost nothing, and is heavily audited — own 80 and 443. You will meet that proxy
properly in [Session 4](./04_Nginx_Deep_Dive.md).

> 💡 Other ways around it without running as root: `setcap
> 'cap_net_bind_service=+ep' ./server`, a systemd socket unit, or port-forwarding with
> iptables. All of them exist because "just run as root" is the wrong answer.

---

## 🤔 Thought experiment: what breaks if you skip a call?

Worth arguing about before reading the answer.

| You skip… | What the client sees | Why |
|---|---|---|
| **`bind()`** | **Connection refused** — instantly | Nothing owns the port, so the kernel answers the SYN with an **RST** straight away. Fast, loud, easy to debug. The client knows nobody is home. |
| **`accept()`** (but you did bind + listen) | **It just hangs** | ⭐ The **kernel completes the handshake on your behalf**. The connection is *established* and sitting in the queue. Your process never picks it up, so the client waits until TCP times out. |

> ⭐ **That second row is the whole lesson.** Silent, slow, and it looks *exactly* like an
> overloaded server. A hung connection and a busy server are indistinguishable from outside —
> which is why "it's just slow" is the hardest production symptom to diagnose.

---

## 🔁 One `read()` is not a conversation

The first server reads **once**, replies once, hangs up. Loop the read instead:

```c
while (1) {
    int client_fd = accept(server_fd, NULL, NULL);
    char buf[4096];
    int n;
    while ((n = read(client_fd, buf, sizeof(buf))) > 0) {   // ← until EOF
        write(client_fd, buf, n);
    }
    close(client_fd);
}
```

`read()` returns **0** when the peer closes cleanly (EOF) and **−1** on error, which is what
ends the inner loop.

> ⚠️ **`read()` is not message-shaped.** It returns *whatever has arrived*, which may be half
> a message or three messages glued together. TCP gives you a **byte stream**, not messages.
> That is the framing problem — [below](#message-framing).

---

## 📥 The accept queue — `listen(fd, backlog)`

That second argument is a **queue**. The kernel accepts connections on your behalf and stacks
them up, and the stack has a size.

> 💡 **The waiting-room analogy.** `listen(fd, 5)` is putting five chairs in the waiting room.
> The receptionist (kernel) seats people whether or not the doctor (your `accept()` loop) is
> free. When the chairs are full, new arrivals are turned away.

| Fact | Consequence |
|---|---|
| **The kernel finishes the handshake without you** | By the time `accept()` returns, the connection has been established for a while. ⭐ The client has been *waiting in line* — your latency graph starts before your code runs. |
| **Full-queue behaviour is not portable** | *Connection refused* on some systems; an indefinite `Trying...` on others. ⚠️ Never build logic on top of whichever you happened to see locally. |
| **We passed `1`. Real servers pass hundreds** | And Linux silently caps you at **`net.core.somaxconn`**, so the number in your code may not be the number in effect. |

```bash
sysctl net.core.somaxconn          # the real ceiling
ss -ltn                            # Send-Q column = backlog, Recv-Q = waiting connections
```

⭐ A full accept queue is a classic "the server is up but nothing works" outage. The process is
healthy, the port is open, and connections rot in the kernel.

---

## ⚡ Signals, and the one that will kill you

| № | Signal | Meaning |
|---|---|---|
| **2** | `SIGINT` | Ctrl-C |
| **9** | `SIGKILL` | ⚠️ **cannot be caught** — the kernel just removes you |
| **13** | `SIGPIPE` | ⭐ **write to a closed peer** |
| **15** | `SIGTERM` | the polite kill — what you should handle |

Also: `SIGHUP` on SSH disconnect · `SIGSTOP` / `SIGTSTP` on Ctrl-Z.

> ⭐ **SIGPIPE is the one that will kill you.** Write to a socket the peer already closed and,
> **by default, your process dies**. No error return, no exception — gone.

### Reproducing it

**Server** — two writes, the second never runs:

```c
int client_fd = accept(server_fd, NULL, NULL);
char buf[4096];
int n = read(client_fd, buf, sizeof(buf));

sleep(1);                      // give the client time to force-close (RST)

write(client_fd, buf, n);      // peer already reset → SIGPIPE raised here
write(client_fd, buf, n);      // never reached: default action kills the process
```

**Client** — `SO_LINGER {1, 0}` makes `close()` send **RST** instead of **FIN**:

```c
connect(fd, (struct sockaddr*)&addr, sizeof(addr));
write(fd, "hello", 5);

struct linger l = {1, 0};      // abortive close
setsockopt(fd, SOL_SOCKET, SO_LINGER, &l, sizeof(l));
close(fd);
```

| Close type | Sends | Meaning |
|---|---|---|
| Normal `close()` | **FIN** | "I'm done sending." Graceful, four-way teardown. |
| `SO_LINGER {1, 0}` | **RST** | ⚠️ "Forget this connection existed." Abortive — unsent data discarded. |

### The fix, in every language

```c
signal(SIGPIPE, SIG_IGN);                      // then write() returns -1 with errno == EPIPE
send(fd, buf, n, MSG_NOSIGNAL);                // or suppress per-call (Linux)
```

> 💡 Python, Java and Go all ignore `SIGPIPE` for you and surface it as an exception or error
> (`BrokenPipeError`, `EPIPE`). **C does not.** This is why "my server randomly dies with no
> log line" is almost always SIGPIPE.

---

## 🔭 You already have a client

> **If a protocol is text, your keyboard is a perfectly good implementation of it.**

```bash
telnet google.com 80
telnet localhost 2026
telnet mail.example.com 25
```

Four lines of typing and Google answers:

```text
$ telnet google.com 80
Trying 142.251.222.142...
Connected to google.com.
Escape character is '^]'.
GET / HTTP/1.1
Host: google.com

HTTP/1.1 301 Moved Permanently
Location: http://www.google.com/
Content-Type: text/html; charset=UTF-8
Date: Wed, 12 Aug 2026 16:06:35 GMT
Cache-Control: public, max-age=2592000
Server: gws
Content-Length: 219
X-Frame-Options: SAMEORIGIN

<HTML><HEAD>…<TITLE>301 Moved</TITLE></HEAD><BODY>…</BODY></HTML>
```

⭐ Note what made that work: the request line, the **mandatory `Host:` header** (HTTP/1.1
requires it), and the **blank line** that says "headers are over".

### Beyond port 80

Most services do not speak HTTP — and once TLS is in the way, `telnet` is useless because it
cannot do the handshake.

```bash
openssl s_client -connect www.hotstar.com:443   # TLS, then type the protocol
nc localhost 2026                               # netcat for everything else
nc -l 9000                                      # …and as a throwaway server
```

> 💡 `openssl s_client` prints the full certificate chain before handing you the socket — it is
> the fastest way to answer "is the cert expired / is the chain complete?".

---

## ✍️ Writing the client

The client is **shorter**. Notice what is missing.

```c
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>

int main() {
    struct hostent *he = gethostbyname("localhost");   // ← DNS hiding here

    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    addr.sin_port   = htons(8080);

    connect(fd, (struct sockaddr*)&addr, sizeof(addr));
    write(fd, "hello", 5);
    close(fd);
    return 0;
}
```

**No `bind()`. No `listen()`. No `accept()`. And no port number of its own.**

---

## 🎲 Ephemeral ports

> **Clients never bind. The kernel picks a port for you.**

| Server | Client |
|---|---|
| Binds a **known** port | Gets a **random high** port |
| It has to — clients need a fixed address to aim at. That is the entire reason well-known ports exist. | Assigned by the kernel at `connect()` time from the **ephemeral range** — typically **32768–60999** on Linux. |
| `bind()` `listen()` `accept()` | ⚠️ Finite, and **TIME_WAIT holds each one for ~60s** after close. Busy clients *do* run out. |

> 💡 **The return-address analogy.** You don't need a shopfront to send a letter — but you do
> need a return address, or the reply can't find you. The kernel writes one on for you.

A TCP connection is identified by the **4-tuple**:

```
(source IP, source port, destination IP, destination port)
```

⭐ That is why one client can hold thousands of connections to the *same* server — only the
source port differs. And why running out of ephemeral ports (`EADDRNOTAVAIL`, "cannot assign
requested address") is a real production failure on busy proxies and load generators.

```bash
sysctl net.ipv4.ip_local_port_range        # 32768 60999
ss -s                                      # count sockets by state, incl. timewait
```

---

## 🔀 Byte order and `htons()`

> **Your CPU and the network disagree on byte order.**

```
port 2026 = 0x07EA

little endian  (your x86 / ARM laptop)     EA 07     ← least significant byte first
big endian     (network byte order)        07 EA     ← most significant byte first
```

`htons` = **h**ost **to** **n**etwork, **s**hort.

| Function | Converts |
|---|---|
| `htons()` / `ntohs()` | 2 bytes (ports) |
| `htonl()` / `ntohl()` | 4 bytes (IPv4 addresses) |

> 💡 **The date analogy.** `03/04` means 3 April in India and 4 March in the US. Nothing is
> wrong with either — they just need an agreed wire format. Network byte order **is** big
> endian, by decree, so everyone converts on the way in and out.

> ⚠️ Forget `htons()` and your server binds port **59911** instead of 2026 (the bytes swapped),
> with no error anywhere. It is one of the classic first-day bugs.

---

## 🌐 `gethostbyname()` is a whole protocol

> **One function call is a whole protocol.** `gethostbyname()` *is* DNS — a UDP request, a
> recursive resolver and a cache — hidden behind a **synchronous call that can block for
> seconds**.

| Step | What happens |
|---|---|
| **1. `/etc/hosts` first** | Before any network traffic. ⭐ This is why editing hosts overrides everything, and why a stale entry there is so hard to debug. |
| **2. UDP query to your resolver** | One small datagram to whatever is in `/etc/resolv.conf`. It recurses on your behalf: **root → TLD → authoritative**. |
| **3. Cached for the TTL — and it blocks** | Fast when warm, **seconds when cold**, with no timeout you control. |

> ⚠️ Use **`getaddrinfo()`** in real code. `gethostbyname()` is IPv4-only, not thread-safe, and
> long deprecated.

⭐ A blocking DNS lookup inside a request path is a classic hidden latency source: your p99
isn't your code, it's a cold cache.

---

## 🪜 Where we are on the OSI stack

> **We have been writing layer 7 this whole time** — and touched layers 4 and 3 in twenty
> lines without ever naming them.

| Layer | | In our code |
|---|---|---|
| **7** | Application | our echo protocol, HTTP |
| **4** | Transport | **TCP** · ports · `htons(2026)` |
| **3** | Network | **IP** · `INADDR_ANY` · `127.0.0.1` |
| **2** | Data link | Ethernet, Wi-Fi · MAC addresses |
| **1** | Physical | copper, fibre, radio |

The full model and its missing layers come in [Session 2](./02_Computer_Networking_Eagle_Eye_View.md).

---

## 🌍 HTTP & curl

> **An HTTP client is `client.c` with a string in it.** Point it at port 80, write the request
> text, read until close. That is the whole protocol.

```http
GET / HTTP/1.1
Host: google.com

```

> ⚠️ **CRLF (`\r\n`) line endings, and that blank line is mandatory.** The blank line is the
> delimiter that says "headers finished" — a *framing* decision, which we come back to below.

```bash
curl google.com
curl -i google.com                      # include response headers
curl -vv https://google.com 2>&1 | less # the whole conversation, TLS included
```

⭐ `curl -v` is the best HTTP teaching tool you have: it shows DNS, the TCP connect, the TLS
handshake and certificate, the exact request bytes and the response headers — in order.

---

## 👥 Many clients at once

**The debt comes due.** Our server serves exactly **one** client. There are two ways out, and
both are still shipping in production today.

| One process per connection | One process, many sockets |
|---|---|
| **`fork()`** | **`select` / `epoll`** |
| Dead simple, and the OS does the scheduling for you. Each child has its own memory, so a crash is **contained**. | Ask the kernel which sockets are ready, then handle only those. **No context switching, no per-client memory.** |
| ⚠️ Costs a process per client. Fine for hundreds, hopeless at ten thousand. | ⚠️ Harder to write, and **one slow handler blocks everything**. |
| | ⭐ This is what **nginx and Node** do. |

### `fork()` returns twice

The same line of code runs in two processes, and the only way to tell which one you are is
**what came back**.

| Return | You are |
|---|---|
| **`0`** | the **child**. Handle this one client, then exit. |
| **`> 0`** | the **parent**. That number is the child's PID. Close your copy of the fd and go back to `accept()`. |
| **`-1`** | fork **failed** — out of processes or memory. ⚠️ Almost nobody checks for this. |

```c
while (1) {
    int client_fd = accept(server_fd, NULL, NULL);

    if (fork() == 0) {                 // child
        char buf[4096];
        int n;
        while ((n = read(client_fd, buf, sizeof(buf))) > 0) {
            write(client_fd, buf, n);
        }
        close(client_fd);
        return 0;                      // ⭐ the child MUST exit
    }

    close(client_fd);                  // parent drops its copy of the fd
}
```

> ⚠️ Both `close()` calls matter. A file descriptor is only really closed when **every** copy
> is closed — forget the parent's and the connection never tears down. And a child that
> forgets to `return` falls back into `accept()`, giving you two processes fighting over the
> same listening socket.

> 💡 Also reap your children (`waitpid`, or `signal(SIGCHLD, SIG_IGN)`) or you accumulate
> **zombies** — dead processes still holding a slot in the process table.

### `select` vs `epoll`

| `select` | `epoll` |
|---|---|
| **Portable, and O(n)** | **Linux, and O(ready)** |
| Rebuild the fd set on **every call**; the kernel walks all of them every time. | **Register interest once.** The kernel returns only the descriptors that actually changed. |
| ⚠️ `FD_SETSIZE` caps you around **1024** descriptors. | `kqueue` on BSD/macOS, **IOCP** on Windows. |
| Works everywhere, which is why it is still around. | ⭐ What nginx and Node are built on. |

> 💡 **The waiter analogy.** `select` is a waiter who walks past *every* table on every lap to
> see who's ready. `epoll` is a waiter with a buzzer system — only the tables that buzzed get
> visited. At 10 tables you can't tell the difference; at 10,000 only one of them is still
> standing. This is the **C10K problem**.

### The client side has the same limits

| | |
|---|---|
| **6** | Chrome's old **per-host connection cap**. Requests 7–10 simply queued. ⭐ Not a browser quirk — the client-side version of the same resource problem. |
| **`ulimit -n`** | Your hard ceiling on open file descriptors. **Sockets count.** Often just 1024. |
| **pool** | Open once, reuse many times — you skip the TCP *and* TLS handshake every time after the first. |

```bash
ulimit -n            # soft limit
ulimit -Hn           # hard limit
```

⭐ Connection pooling is the single highest-leverage client-side optimisation there is, and the
reason HTTP/1.1 keep-alive and HTTP/2 multiplexing exist
([Session 5](./05_Evolution_of_HTTP.md)).

---

## ⚙️ Socket options worth knowing

Read the man page for socket options once — some of it is a networking history lesson.

| Option | What it does |
|---|---|
| **`INADDR_ANY`** | Listen on **every** interface. Convenient in development; a decision worth making deliberately in production. ⚠️ Bind to a specific address when you mean one. |
| **Promiscuous mode** | See traffic that is **not yours**. On a hub, every frame reached every port — this is how packet sniffers work, and **why plaintext protocols died**. |
| **`SO_REUSEADDR`** | ⭐ The one you will actually use. Without it, restarting your server fails with **"address already in use"** while the old socket sits in `TIME_WAIT`. |
| `SO_LINGER` | Controls what `close()` sends — FIN or RST (above). |
| `TCP_NODELAY` | Disables **Nagle's algorithm**, which buffers small writes. Essential for latency-sensitive protocols. |
| `SO_KEEPALIVE` | Detect peers that vanished without a FIN. |

---

## 🔬 Stop guessing — look at the bytes

```bash
sudo tcpdump -ni any port 2026 -w 1.pcap   # capture
tcpdump -r 1.pcap -A                       # read as ASCII
tcpdump -r 1.pcap -X                       # read as hex + ASCII
```

Then open the same `.pcap` in **Wireshark** for a decoded, clickable view. `strace -e trace=network ./server`
shows the system calls themselves.

⭐ Everything discussed above — the handshake, the backlog, the RST, the byte order — is
visible in a capture. **Stop guessing. Look at the bytes.**

---

## 🔐 SSL/TLS secures TCP, not HTTP

> ⭐ TLS sits **under** the application protocol, which is why the same machinery protects SSH,
> SMTP, database connections and anything else you put on a socket. "HTTPS" is just HTTP with
> TLS underneath.

| Step | |
|---|---|
| **1. Exchange keys and certificates** | **Asymmetric** crypto to agree on a shared secret, then **symmetric** crypto for the data — because symmetric is dramatically faster. |
| **2. The certificate binds a key to an identity** | And the **CA chain** is the reason you believe it. ⚠️ This is the part that expires at 3am and takes your site down. |
| **3. Pinning removes the CA from the trust equation** | Common in mobile apps: trust *this exact* certificate, not whatever any CA in the world is willing to sign. |

> 💡 **Why two kinds of crypto?** Asymmetric (RSA/ECDHE) solves "how do two strangers agree on
> a secret over a tapped wire" but is slow. Symmetric (AES) is fast but needs a shared secret
> first. So: use the slow one *once* to agree a key, then the fast one for everything else.

---

## 🧩 Protocol design

> **Text won. Now protocols are going binary again.** HTTP proves how far human-readable can
> take you — and **HTTP/2 is binary**.

| Text | Binary |
|---|---|
| **You can read it** | **The machine can read it faster** |
| telnet into it, tcpdump it, eyeball the logs. A real and large advantage — most of why HTTP won. | Compact, unambiguous, cheap to parse. No whitespace rules, no case-sensitivity arguments. |
| ⚠️ Verbose, ambiguous at the edges, slower to parse than it looks. | ⚠️ You need tooling to see anything at all — which is why **hex and base64 fluency stops being optional**. |

### Message framing

> ⭐ **How does the receiver know the message ended?** TCP gives you a **byte stream, not
> messages**. This is the single most important decision in your protocol — and there are only
> three answers.

| # | Strategy | Trade-off |
|---|---|---|
| **1** | **Fixed length** — every message is exactly N bytes | Trivial to parse, zero ambiguity. You pay in **padding**, and you can never change your mind about N. |
| **2** | **Delimited** — read until the sentinel | HTTP's blank line between headers and body. Simple, until the delimiter **appears inside your data** and you need escaping. |
| **3** | **Length prefix** — send the size, then the bytes | `Content-Length: 219`. Read exactly that many and stop. ⭐ Robust, binary-safe, and what most modern protocols do. |

> 💡 **The telegram analogy.** A stream of letters with no spaces is unreadable. You can fix it
> by agreeing every word is 5 letters (fixed), by writing STOP between words (delimited), or by
> writing the word's length in front of it (length-prefixed). Only the third is safe when the
> word itself might contain "STOP".

### BCD — binary coded decimal

Four bits per digit. The curious part is that the digits **just show up** — convert to hex and
the representation does not change.

```text
decimal   98765
nibbles   1001 1000 0111 0110 0101
hex       98 76 5F          ← 'F' is the pad nibble for the odd digit count
```

Half the size of ASCII · no conversion step · exact decimal arithmetic (no float error) ·
still used in **SIM cards, SMS and card transactions**.

### ASN.1 — write the grammar, generate the codec

> Describe the shape of your data **once**, in a language-neutral grammar, and the encoder and
> decoder are produced for you. You never hand-write parsing.

```asn1
MyModule DEFINITIONS ::= BEGIN

    Item ::= SEQUENCE {
        itemCode   INTEGER (1..99999),
        color      VisibleString ("Black" | "Blue" | "Brown"),
        isTaxable  BOOLEAN
    }

END
```

From **1984**, and still under **X.509 certificates, LDAP, SNMP** and the whole telecom stack
today.

### TLV — ASN.1 you can write on a napkin

```text
<Type><Length><Value><Type><Length><Value> …
```

> ⭐ **Self-describing:** a parser that has never seen a field type can still **skip** it,
> because the length tells it how far to jump. That one property is what makes TLV **forward
> compatible** — and it is why TLS extensions, ISO 8583 and protobuf all work this way.

### base64 and hex — how you *see* a binary protocol

| Hex | Base64 |
|---|---|
| **For reading** | **For transport** |
| Two characters per byte; `tcpdump -X` puts it beside the ASCII. | Survives text-only channels: Basic auth, JWTs, email attachments, data URIs. |
| Fluency means spotting a length prefix or a repeated tag **by eye**. | ⚠️ Costs **33% more bytes** — 3 bytes become 4 characters. A wrapper, not a design. |

### RPC — framing plus a function name

| Step | |
|---|---|
| **1. Marshal** — objects become bytes | Function name, then the arguments. This is the easy part. |
| **2. Frame it and send it** | Every decision from the last four sections is now doing real work. |
| **3. ⭐ The network is not a function call** | Calls fail halfway, **time out with the work possibly done**, and get retried. Every RPC framework rediscovers this the hard way. |

> ⚠️ Point 3 is the one that bites. A timeout does **not** mean "it didn't happen" — it means
> "I don't know whether it happened". That is why retries need **idempotency**, a theme that
> runs through [Session 8](./08_Building_for_Failures_and_Video_at_Scale.md).

### gRPC — RPC with protobuf underneath

| | |
|---|---|
| **`.proto`** | Schema first. Generate client and server code in any language. |
| **TLV on the wire** | So new fields do not break old clients. |
| **HTTP/2** | Binary and **multiplexed** — many streams over one connection. |
| **no curl** | ⚠️ The cost: you cannot read it without tooling. **Speed bought with debuggability.** |

Much faster to encode and decode than JSON, and much easier to understand than ASN.1. That
combination is why it won.

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Socket** | An endpoint for communication; a file descriptor you can `read`/`write` |
| **`bind()`** | Claim a specific port on a specific address |
| **`listen(fd, backlog)`** | Mark the socket passive and size the **accept queue** |
| **`accept()`** | Take the next **already-established** connection off the queue |
| **Backlog / `somaxconn`** | Queue depth, and the kernel's cap on it |
| **Well-known ports** | < 1024, root-only to bind |
| **Ephemeral port** | Random high port the kernel gives a client at `connect()` |
| **4-tuple** | `(src IP, src port, dst IP, dst port)` — what identifies a connection |
| **`TIME_WAIT`** | ~60s hold after close; why `SO_REUSEADDR` exists |
| **`SIGPIPE`** | Signal 13 — write to a closed peer; ⭐ **kills the process by default** |
| **FIN vs RST** | Graceful close vs abortive reset (`SO_LINGER {1,0}`) |
| **Network byte order** | **Big endian**; convert with `htons`/`htonl`/`ntohs`/`ntohl` |
| **`gethostbyname()`** | Blocking DNS lookup; use `getaddrinfo()` instead |
| **`fork()` model** | One process per connection — simple, isolated, expensive |
| **`select` / `epoll`** | Readiness notification; O(n) vs O(ready) — the **C10K** answer |
| **`ulimit -n`** | Max open file descriptors; sockets count |
| **`SO_REUSEADDR`** | Rebind a port still in `TIME_WAIT` |
| **Framing** | Fixed-length / delimited / **length-prefixed** |
| **TLV** | Type-Length-Value — self-describing, forward compatible |
| **ASN.1** | Schema language (1984) behind X.509, LDAP, SNMP |
| **BCD** | 4 bits per decimal digit; SIM cards, card transactions |
| **Marshalling** | Turning objects into bytes (and back: demarshalling) |

---

## 🎯 Session Takeaways

1. ⭐ **A TCP server is seven system calls:** `socket → bind → listen → accept → read → write → close`. Every framework you have used is a wrapper around that sequence.
2. **Skip `bind()` → instant *connection refused*. Skip `accept()` → silent hang** that looks exactly like an overloaded server.
3. ⭐ **The kernel completes the handshake before your code sees the connection.** Clients queue in `listen()`'s backlog, capped by `net.core.somaxconn`.
4. **Ports below 1024 need root**, so bind 8080 as a normal user and let an audited proxy own 80/443.
5. ⭐ **`SIGPIPE` kills your process by default.** Ignore it and handle `EPIPE` instead.
6. **Clients never `bind()`** — the kernel hands out an ephemeral port, and `TIME_WAIT` means busy clients can run out of them.
7. ⭐ **The network is big endian and your laptop probably isn't.** `htons()` is not optional.
8. **`gethostbyname()` is DNS in disguise** — `/etc/hosts`, a UDP query, a recursive resolver, a cache, and a blocking call with no timeout you control.
9. **TLS secures TCP, not HTTP** — which is why SSH, SMTP and database connections use the same machinery.
10. ⭐ **`fork()` per connection is simple and bounded; `epoll` is harder and scales.** nginx and Node chose the second, and [Session 4](./04_Nginx_Deep_Dive.md) shows what that bought.
11. ⭐ **TCP is a byte stream, not messages.** Pick a framing strategy deliberately: fixed, delimited, or **length-prefixed** (usually the right answer).
12. **TLV's length field is what makes a protocol forward compatible** — old parsers can skip fields they don't understand.
13. **`telnet`, `nc`, `openssl s_client`, `curl -vv` and `tcpdump` are the whole toolkit.** Stop guessing; look at the bytes.

---

## 🔗 References

- Beej's Guide to Network Programming — https://beej.us/guide/bgnet/
- `man 2 socket`, `man 2 listen`, `man 7 tcp`, `man 7 socket`, `man 2 select`, `man 7 epoll`
- The C10K problem — http://www.kegel.com/c10k.html
- RFC 9110 — HTTP Semantics — https://www.rfc-editor.org/rfc/rfc9110
- RFC 9293 — TCP — https://www.rfc-editor.org/rfc/rfc9293
- Wireshark — https://www.wireshark.org/docs/
- gRPC — https://grpc.io/docs/what-is-grpc/introduction/
- Protocol Buffers — https://protobuf.dev/
- ASN.1 (ITU-T X.680) — https://www.itu.int/rec/T-REC-X.680

---

## ➡️ Next

[Session 2 — Computer Networking Eagle Eye View](./02_Computer_Networking_Eagle_Eye_View.md) —
we wrote layer 7 without naming the layers. Now the whole stack, properly.
