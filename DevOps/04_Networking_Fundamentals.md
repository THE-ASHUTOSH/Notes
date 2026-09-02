# Session 4 — Networking Fundamentals 🌐

> In DevOps, **everything is a network call**: a browser hitting a load balancer, a container
> talking to a database, a pod resolving a Service name, a CI runner pulling an image.
> Most "the app is down" incidents are really **DNS, port, firewall or routing** problems.

---

## 📑 Table of Contents
1. [Why Networking Matters](#-why-networking-matters-in-devops)
2. [The OSI & TCP/IP Models](#-the-osi--tcpip-models)
3. [IP Address](#-ip-address)
4. [IP Address Classes](#-ip-address-classes)
5. [Subnet Mask & Network vs Host](#-subnet-mask--network-vs-host-bits)
6. [CIDR Notation](#-cidr-notation)
7. [Calculating Hosts & Broadcast](#-calculating-hosts--broadcast-worked-examples)
8. [Public vs Private IP](#-public-vs-private-ip)
9. [Special Addresses & NAT](#-special-addresses--nat)
10. [MAC Address & ARP](#-mac-address--arp)
11. [Ports](#-ports)
12. [TCP vs UDP](#-tcp-vs-udp)
13. [DNS](#-dns)
14. [HTTP & HTTPS](#-http--https)
15. [DHCP](#-dhcp)
16. [Load Balancing, Proxies & Firewalls](#-load-balancers-proxies--firewalls)
17. [Networking Commands](#-basic-networking-commands)
18. [Troubleshooting Ladder](#-the-network-troubleshooting-ladder)

---

## 🎯 Why Networking Matters in DevOps

| Task | Networking concept behind it |
|---|---|
| `docker run -p 8080:80` | **Port mapping** / NAT |
| Container calls `http://backend:5000` | **DNS** + **service discovery** |
| Kubernetes `ClusterIP` / `NodePort` | **Private IP**, ports, load balancing |
| Terraform VPC + subnets + route tables | **CIDR**, subnetting, routing |
| Security groups / firewall rules | **Ports**, **protocols** (TCP/UDP), CIDR sources |
| Ingress with TLS | **HTTPS**, certificates, host/path routing |
| "Service unreachable" | **DNS → routing → firewall → port → process** |

---

## 🧱 The OSI & TCP/IP Models

The **OSI model** breaks communication into 7 layers so problems can be isolated to one layer.

| # | OSI Layer | Job | Unit | Examples | Devices |
|---|---|---|---|---|---|
| **7** | **Application** | User-facing protocols | Data | **HTTP/HTTPS**, DNS, SSH, FTP, SMTP | — |
| **6** | Presentation | Encoding, encryption, compression | Data | TLS/SSL, JPEG, ASCII | — |
| **5** | Session | Establish/manage sessions | Data | Sockets, RPC | — |
| **4** | **Transport** | End-to-end delivery, **ports** | Segment | **TCP**, **UDP** | Firewall, L4 LB |
| **3** | **Network** | Logical addressing & **routing** | Packet | **IP**, ICMP (ping), ARP-adjacent | **Router**, L3 switch |
| **2** | **Data Link** | Local delivery, **MAC** addresses | Frame | Ethernet, ARP, VLAN, PPP | **Switch**, bridge, NIC |
| **1** | Physical | Bits over the wire/air | Bits | Cables, fibre, Wi-Fi radio | Hub, repeater |

**Mnemonic (7 → 1):** **A**ll **P**eople **S**eem **T**o **N**eed **D**ata **P**rocessing.

**TCP/IP (DoD) model** — the practical 4-layer version actually implemented:

| TCP/IP Layer | Maps to OSI |
|---|---|
| Application | 7 + 6 + 5 |
| Transport | 4 |
| Internet | 3 |
| Network Access / Link | 2 + 1 |

**Why DevOps engineers care:** it tells you *where to look*.
```
Can't ping the IP?          → Layer 3 (routing/IP) or Layer 1/2 (link)
Ping works, port refused?   → Layer 4 (port closed / process not listening / firewall)
Port open, 502 error?       → Layer 7 (application / upstream misconfigured)
Name doesn't resolve?       → Layer 7 DNS
Certificate error?          → Layer 6 TLS
```

---

## 🔢 IP Address

> **IP address = a unique numeric identifier for a device on a network.**
> **IP = Internet Protocol** (Layer 3 — logical addressing and routing).

### IPv4 structure
- **32 bits**, written as **4 octets** (bytes) in dotted-decimal.
- Each octet is 8 bits → decimal **0–255**.
- Total address space: `0.0.0.0` → `255.255.255.255` (2³² ≈ 4.29 billion).

```
        192   .    168   .     1    .    10
     ┌────────┬──────────┬──────────┬──────────┐
     │11000000│ 10101000 │ 00000001 │ 00001010 │   = 32 bits
     └────────┴──────────┴──────────┴──────────┘
       octet1    octet2     octet3     octet4
```

All-zero binary and its decimal form (from class notes):
```
0000 0000.0000 0000.0000 0000.0000 0000   =   0.0.0.0
```

### Every IP has two parts
```
       ┌─────────── NETWORK part ───────────┬── HOST part ──┐
       │  which network the device is on    │ which device  │
       └────────────────────────────────────┴───────────────┘
```
- **Network ID** — identifies the network (routers use this to forward packets).
- **Host ID** — identifies the individual device inside that network.
- **The subnet mask decides where the split happens.**

### IPv4 vs IPv6
| | IPv4 | IPv6 |
|---|---|---|
| Size | 32 bits | 128 bits |
| Format | `192.168.1.10` | `2001:0db8:85a3::8a2e:0370:7334` |
| Notation | Dotted decimal | Hex, colon-separated (`::` collapses zeros) |
| Address count | ~4.3 billion | ~3.4 × 10³⁸ |
| NAT | Usually required | Not needed |
| Loopback | `127.0.0.1` | `::1` |

---

## 🏷️ IP Address Classes

Classful addressing splits the IPv4 space by the value of the **first octet**:

| Class | First octet range | Default mask | Network / Host bits | Networks | Hosts per network | Use |
|---|---|---|---|---|---|---|
| **A** | **1 – 127** | `255.0.0.0` (/8) | 8 / 24 | 126 | 16,777,214 | Very large networks |
| **B** | **128 – 191** | `255.255.0.0` (/16) | 16 / 16 | 16,384 | 65,534 | Medium networks |
| **C** | **192 – 223** | `255.255.255.0` (/24) | 24 / 8 | 2,097,152 | 254 | Small networks / LANs |
| **D** | **224 – 239** | — | — | — | — | **Multicast** |
| **E** | 240 – 255 | — | — | — | — | Experimental / reserved |

From the class notes:
```
Class A:  1 - 127
Class B:  128 - 191
Class C:  192 - 223
Class D:  224 - 239

255.0.0.0        - class A mask
255.255.0.0      - Class B mask
255.255.255.0    - Class C mask
255.255.255.255  - (all-ones; the limited broadcast address)
```

> 📌 **Note on the class-D line in the raw notes:** `255.255.255.255` is written next to "Class D".
> To be precise: **Class D is the address range `224.0.0.0 – 239.255.255.255` (multicast)**, and
> **`255.255.255.255` is the *limited broadcast* address**, not a class-D mask. Classes D and E do
> not use subnet masks at all because they aren't divided into networks and hosts.

**Quick identification examples**
| Address | First octet | Class |
|---|---|---|
| `120.27.1.0` | 120 | **A** |
| `126.34.0.1` | 126 | **A** |
| `194.23.56.10` | 194 | **C** |
| `197.23.45.10` | 197 | **C** |
| `10.0.0.1` | 10 | **A** (private) |

> 🧭 **Reality check:** classful addressing is *historical*. Modern networks use **CIDR**
> (classless), where the mask is arbitrary. But interviews and exams still ask for the classes,
> and the default masks remain a useful shorthand.

---

## 🎭 Subnet Mask & Network vs Host bits

> **Subnet mask: used to differentiate the *host part* from the *network part* of an IP address.**

The mask is also 32 bits: a run of **1s marking the network part**, followed by **0s marking the
host part**.

```
IP      : 197.23.45.10   → 11000101.00010111.00101101.00001010
Mask /24: 255.255.255.0  → 11111111.11111111.11111111.00000000
                            └────── network (24) ──────┘└host(8)┘
Network : 197.23.45.0
```

**Standard masks**
| Mask | CIDR | Network bits | Host bits | Class |
|---|---|---|---|---|
| `255.0.0.0` | /8 | 8 | 24 | A |
| `255.255.0.0` | /16 | 16 | 16 | B |
| `255.255.255.0` | /24 | 24 | 8 | C |

**The core arithmetic**
```
network bits + host bits = 32

Class A:  network bits = 8   →  32 - 8  = 24 host bits
Class B:  network bits = 16  →  32 - 16 = 16 host bits
Class C:  network bits = 24  →  32 - 24 =  8 host bits
```

**Binary values of a single mask octet** (memorise these — subnetting depends on them):
| Bits set | Binary | Decimal |
|---|---|---|
| 1 | `10000000` | 128 |
| 2 | `11000000` | 192 |
| 3 | `11100000` | 224 |
| 4 | `11110000` | 240 |
| 5 | `11111000` | 248 |
| 6 | `11111100` | 252 |
| 7 | `11111110` | 254 |
| 8 | `11111111` | 255 |

---

## ✂️ CIDR Notation

**CIDR (Classless Inter-Domain Routing)** writes the mask as `/N` — the **number of network bits**.

```
120.27.1.0/8     →  8 network bits, 24 host bits    (mask 255.0.0.0)
120.27.1.0/16    → 16 network bits, 16 host bits    (mask 255.255.0.0)
127.0.0.1/24     → 24 network bits,  8 host bits    (mask 255.255.255.0)
127.0.0.1/16     → 16 network bits, 16 host bits
127.0.0.1/32     → ⭐ 32 network bits, 0 host bits → EXACTLY ONE address
```

| CIDR | Mask | Total addresses | Usable hosts |
|---|---|---|---|
| `/8` | 255.0.0.0 | 16,777,216 | 16,777,214 |
| `/16` | 255.255.0.0 | 65,536 | 65,534 |
| `/24` | 255.255.255.0 | 256 | **254** |
| `/25` | 255.255.255.128 | 128 | 126 |
| `/26` | 255.255.255.192 | 64 | 62 |
| `/27` | 255.255.255.224 | 32 | 30 |
| `/28` | 255.255.255.240 | 16 | 14 |
| `/30` | 255.255.255.252 | 4 | 2 (point-to-point links) |
| `/32` | 255.255.255.255 | 1 | 1 (**a single host**) |

> 🔑 **The rule:** *bigger `/N` = smaller network.* `/32` is one address; `/0` is the whole internet.

**Where you'll actually type CIDR every day**
```hcl
# Terraform / AWS VPC
cidr_block = "10.0.0.0/16"           # the VPC: 65,536 addresses
subnet     = "10.0.1.0/24"           # one subnet: 256 addresses

# Security group / firewall rule
cidr_blocks = ["0.0.0.0/0"]          # ⚠️ THE ENTIRE INTERNET — use sparingly
cidr_blocks = ["203.0.113.42/32"]    # ⭐ exactly one trusted IP
cidr_blocks = ["10.0.0.0/8"]         # all private class-A space
```

---

## 🧮 Calculating Hosts & Broadcast (worked examples)

### The formulas
```
Number of addresses         = 2 ^ (host bits)
Number of USABLE hosts      = 2 ^ (host bits) − 2
```
**Why minus 2?** Two addresses in every subnet are reserved:
- **Network address** — all host bits `0` (identifies the network itself)
- **Broadcast address** — all host bits `1` (sends to every host in the subnet)

### Example 1 — Class A (from class notes)
```
IP           : 120.27.1.0/8
Class        : A
Network bits : 8
Host bits    : 32 − 8 = 24
No. of hosts          = 2^24 = 16,777,216
No. of USABLE hosts   = 2^24 − 2 = 16,777,214

With mask 255.0.0.0:
  Network address   = 120.0.0.0
  Broadcast address = 120.255.255.255
```

### Example 2 — Class C (from class notes)
```
IP        : 197.23.45.10
Mask      : 255.255.255.0   (/24)
Class     : C
Host bits : 8
Usable hosts = 2^8 − 2 = 254

  Network address   = 197.23.45.0
  First usable host = 197.23.45.1
  Last usable host  = 197.23.45.254
  Broadcast address = 197.23.45.255      ⭐
```

> 📌 The raw notes contain the line `197.23.45.10 - 255.255.255.0 - 197.23.34.255`.
> That third value is a slip: with a `/24` mask, only the **last** octet is host bits, so the
> broadcast is **`197.23.45.255`** (the third octet `45` is part of the network and does not change).

### Example 3 — Class B
```
IP        : 172.16.5.20/16
Host bits : 16
Usable hosts = 2^16 − 2 = 65,534
Network   = 172.16.0.0
Broadcast = 172.16.255.255
```

### How to find the network address (bitwise AND)
```
IP      197 . 23 . 45 . 10   → 11000101.00010111.00101101.00001010
Mask    255 .255 .255 .  0   → 11111111.11111111.11111111.00000000
AND ────────────────────────────────────────────────────────────────
Network 197 . 23 . 45 .  0   → 11000101.00010111.00101101.00000000
```
Rule: where the mask bit is **1**, keep the IP bit; where it is **0**, force it to **0**.
For the broadcast, force all mask-0 bits to **1**.

### Practice table
| IP / CIDR | Class | Mask | Host bits | Usable hosts | Network | Broadcast |
|---|---|---|---|---|---|---|
| `10.0.0.5/8` | A | 255.0.0.0 | 24 | 16,777,214 | `10.0.0.0` | `10.255.255.255` |
| `172.16.5.20/16` | B | 255.255.0.0 | 16 | 65,534 | `172.16.0.0` | `172.16.255.255` |
| `192.168.1.100/24` | C | 255.255.255.0 | 8 | 254 | `192.168.1.0` | `192.168.1.255` |
| `192.168.1.100/26` | C | 255.255.255.192 | 6 | 62 | `192.168.1.64` | `192.168.1.127` |
| `203.0.113.7/30` | C | 255.255.255.252 | 2 | 2 | `203.0.113.4` | `203.0.113.7` |

---

## 🏠 Public vs Private IP

| | **Public IP** | **Private IP** |
|---|---|---|
| **Reachability** | Routable on the **internet** | Only inside a **local network / VPC** |
| **Uniqueness** | Globally unique | Unique only within its own network |
| **Assigned by** | ISP / cloud provider (via IANA) | Network admin, DHCP, or the cloud VPC |
| **Cost** | Usually paid (elastic IP) | Free |
| **Internet access** | Direct | Needs **NAT** / a NAT gateway |
| **Example** | `8.8.8.8`, `142.250.183.14` | `10.0.1.15`, `192.168.1.10`, `172.16.0.5` |

### Private IP ranges (RFC 1918) — memorise these
| Class | Range | CIDR | Addresses |
|---|---|---|---|
| **A** | `10.0.0.0` – `10.255.255.255` | `10.0.0.0/8` | 16,777,216 |
| **B** | `172.16.0.0` – `172.31.255.255` | `172.16.0.0/12` | 1,048,576 |
| **C** | `192.168.0.0` – `192.168.255.255` | `192.168.0.0/16` | 65,536 |

From the class notes:
```
# Range of private IP addresses:
10.0.0.0 - 10.255.255.255      (class A private range)
```

> 💡 **Where you meet these daily:**
> - Home router LAN: `192.168.0.0/24` or `192.168.1.0/24`
> - AWS/Azure VPC: usually `10.0.0.0/16`
> - **Docker default bridge: `172.17.0.0/16`** ⭐
> - Kubernetes pod/service CIDRs: e.g. `10.244.0.0/16`, `10.96.0.0/12`
>
> ⚠️ **Practical tip:** don't pick a VPC CIDR that overlaps your office/VPN network, or routing
> between them becomes impossible without NAT.

---

## ⭐ Special Addresses & NAT

| Address / Range | Name | Meaning |
|---|---|---|
| `127.0.0.0/8` (usually `127.0.0.1`) | **Loopback / localhost** | The machine itself; traffic never leaves it |
| `0.0.0.0` | Unspecified / "all interfaces" | ⭐ As a **bind** address = "listen on every interface"; as a **route** = default route |
| `0.0.0.0/0` | Default route / "any" | ⭐ In firewall rules = **the whole internet** |
| `255.255.255.255` | Limited broadcast | To every host on the local link |
| `x.x.x.255` (in a /24) | Directed broadcast | Every host in that subnet |
| `169.254.0.0/16` | **APIPA / link-local** | ⭐ Self-assigned when **DHCP fails** — a diagnostic clue! Also cloud metadata: `169.254.169.254` |
| `224.0.0.0/4` | Multicast (class D) | One-to-many delivery |

> 🩺 **Diagnostic gold:** if a machine has a `169.254.x.x` address, it **never got a DHCP lease** —
> check the DHCP server/network before anything else.

> 🐳 **`0.0.0.0` in containers:** an app bound to `127.0.0.1` inside a container is
> **unreachable from outside**, even with `-p` published. Container apps must bind `0.0.0.0`.
> That's why the class Flask app uses `app.run(host="0.0.0.0", port=5000)`.

### NAT — Network Address Translation
NAT lets many private addresses share one public address.

| Type | What it does | Where you see it |
|---|---|---|
| **SNAT / Masquerade** | Rewrites the **source** private IP → public IP on the way out | Home router, cloud **NAT Gateway**, Docker containers reaching the internet |
| **DNAT / Port forwarding** | Rewrites the **destination** so inbound traffic reaches an internal host | ⭐ `docker run -p 8080:80` is exactly this |

```
Container (172.17.0.2:80)  ←── DNAT ──  Host (0.0.0.0:8080)  ←── Client
```

---

## 🔗 MAC Address & ARP

| | MAC address | IP address |
|---|---|---|
| Layer | **2** (Data Link) | **3** (Network) |
| Size | 48 bits (`00:1A:2B:3C:4D:5E`) | 32 bits (IPv4) |
| Scope | **Local link only** | End-to-end, routable |
| Assigned by | Burned into the NIC by the manufacturer | Network / DHCP / admin |
| Changes | Fixed to the hardware | Changes with the network |

**ARP (Address Resolution Protocol)** answers *"which MAC address owns this IP on my local link?"*
so a frame can actually be delivered.

```bash
ip neigh                    # ⭐ view the ARP table (modern)
arp -a                      # legacy equivalent
ip -s neigh                 # with statistics
ip neigh add 192.168.1.1 lladdr 1:2:3:4:5:6 dev eth1   # static entry
ip neigh del 192.168.1.1 dev eth1                      # invalidate an entry
ip neigh replace 192.168.1.1 lladdr 1:2:3:4:5:6 dev eth1

arping -I eth0 192.168.1.1      # send an ARP request to a neighbour
arping -D -I eth0 192.168.1.1   # ⭐ detect DUPLICATE IP addresses
```

---

## 🚪 Ports

> A **port** is a 16-bit number identifying a **specific process/service** on a host.
> **IP address = which machine. Port = which application on it.**

```
        http://192.168.1.10:8080/api
               └─────┬─────┘ └┬─┘
                     IP      PORT
```
An **endpoint/socket** is the pair `IP:PORT`. Range: **0 – 65535**.

### Port ranges
| Range | Name | Notes |
|---|---|---|
| **0 – 1023** | **Well-known** | Reserved for standard services; **binding needs root** on Linux ⭐ |
| **1024 – 49151** | Registered | Assigned to specific applications (8080, 3306, 5432…) |
| **49152 – 65535** | Dynamic / ephemeral | Temporary source ports for outgoing client connections |

### Ports every DevOps engineer must know
| Port | Protocol | Service |
|---|---|---|
| **22** | TCP | **SSH** ⭐ |
| 20 / 21 | TCP | FTP (data / control) |
| 23 | TCP | Telnet (insecure — don't use) |
| 25 | TCP | SMTP (mail send) |
| **53** | **UDP** (TCP for large/zone transfer) | **DNS** ⭐ |
| 67 / 68 | UDP | DHCP (server / client) |
| **80** | TCP | **HTTP** ⭐ |
| 123 | UDP | NTP (time sync) |
| 143 / 993 | TCP | IMAP / IMAPS |
| 389 / 636 | TCP | LDAP / LDAPS |
| **443** | TCP | **HTTPS** ⭐ |
| 445 | TCP | SMB |
| **3306** | TCP | **MySQL / MariaDB** ⭐ |
| 3389 | TCP | RDP |
| **5432** | TCP | **PostgreSQL** ⭐ |
| **6379** | TCP | **Redis** ⭐ |
| 8080 | TCP | HTTP alternate (app servers, Tomcat, proxies) ⭐ |
| 8443 | TCP | HTTPS alternate |
| 27017 | TCP | MongoDB |
| 9090 | TCP | **Prometheus** |
| 3000 | TCP | **Grafana** / Node dev servers |
| 5000 | TCP | Flask dev server ⭐ |
| 9200 / 5601 | TCP | Elasticsearch / Kibana |
| **2375 / 2376** | TCP | Docker daemon (plain / TLS) |
| **2377** | TCP | Docker Swarm cluster management |
| **6443** | TCP | **Kubernetes API server** ⭐ |
| 2379 / 2380 | TCP | **etcd** (client / peer) |
| 10250 | TCP | **kubelet** API |
| 30000–32767 | TCP | Kubernetes **NodePort** range ⭐ |

### Working with ports
```bash
ss -tulnp                   # ⭐ what is listening, and which process owns it
ss -tulnp | grep :8080      # who has 8080?
lsof -i :8080               # same question
netstat -tulnp              # legacy equivalent
curl -I http://localhost:8080          # is it answering?
nc -zv localhost 8080                  # ⭐ is the port open? (no data sent)
nmap -p 1-1000 10.0.0.5                # scan a range of ports
telnet dbhost 3306                     # crude TCP connectivity test
```

> 🐳 **`EXPOSE` vs `-p`:** `EXPOSE 80` in a Dockerfile is **documentation only** — it publishes
> nothing. Only `-p 8080:80` (or `-P`) actually maps a host port. Also: **two processes cannot
> bind the same host port** → "address already in use" (`EADDRINUSE`).

---

## 🔁 TCP vs UDP

Both are **Layer 4 (Transport)** protocols that use ports; they trade reliability against speed.

### TCP — Transmission Control Protocol
**Connection-oriented and reliable.**
- **3-way handshake** before any data flows:
  ```
  Client ──SYN──────▶ Server
  Client ◀──SYN-ACK── Server
  Client ──ACK──────▶ Server      → connection ESTABLISHED
  ```
- **Acknowledgements + retransmission** — lost segments are resent.
- **Ordered delivery** — sequence numbers reassemble data in order.
- **Flow control** (receive window) and **congestion control** — slows down instead of flooding.
- Teardown via `FIN`/`ACK` (or an abrupt `RST`).

### UDP — User Datagram Protocol
**Connectionless and unreliable ("fire and forget").**
- No handshake, no ACKs, no retransmission, no ordering guarantee.
- Tiny **8-byte header** (TCP's is 20+ bytes) → very low overhead.
- Ideal when *late data is worse than lost data*.

### Side-by-side

| Feature | **TCP** | **UDP** |
|---|---|---|
| Connection | Connection-oriented (handshake) | Connectionless |
| Reliability | ⭐ Guaranteed delivery | Best effort |
| Ordering | Guaranteed in order | No ordering |
| Error handling | Detect + **retransmit** | Detect (checksum) + **discard** |
| Flow / congestion control | Yes | No |
| Header size | 20–60 bytes | **8 bytes** |
| Speed | Slower | ⭐ Faster |
| Overhead | Higher | Minimal |
| Broadcast / multicast | No | ✅ Yes |
| Analogy | Registered post with delivery receipt | Dropping a postcard in the box |
| **Used by** | HTTP/HTTPS, SSH, FTP, SMTP, MySQL, PostgreSQL, Redis | **DNS**, DHCP, NTP, SNMP, VoIP, video streaming, online games, QUIC |

**How to choose**
```
Need every byte, in order, guaranteed?          → TCP  (web, APIs, databases, file transfer)
Need low latency, can tolerate a lost packet?   → UDP  (voice, video, metrics, DNS queries)
```

> 💡 DNS uses **UDP/53** for normal queries (small, fast, retry is cheap) and switches to
> **TCP/53** for responses larger than 512 bytes and for zone transfers.

> 🐳 In Docker you must declare UDP explicitly: `docker run -p 53:53/udp dns-server`.

---

## 🧭 DNS

> **DNS (Domain Name System) = the internet's phone book:** it translates
> **human-readable names → IP addresses** (`google.com` → `142.250.183.14`).

Humans remember names; routers only understand IPs. DNS bridges the two — and it also lets you
change the IP behind a name (deploy, failover, scale) without changing any client.

### Name structure (read right to left)
```
        api.staging.example.com.
        │    │        │      │ └── root (the implicit trailing dot)
        │    │        │      └──── TLD  (Top-Level Domain)
        │    │        └─────────── Domain (second-level)
        │    └──────────────────── Subdomain
        └───────────────────────── Host / record name
```

### The DNS hierarchy & resolution flow
```
1. Browser cache        ──▶ already known? done.
2. OS cache / hosts file──▶ /etc/hosts wins over DNS ⭐
3. Recursive resolver   ──▶ your ISP, 8.8.8.8 (Google), 1.1.1.1 (Cloudflare)
4.   └─▶ Root servers (.)          "ask the .com servers"
5.       └─▶ TLD servers (.com)    "ask ns1.example.com"
6.           └─▶ Authoritative NS  "example.com = 93.184.216.34" ✅
7. Answer cached at each level for TTL seconds, then returned
```

### Record types
| Type | Purpose | Example |
|---|---|---|
| **A** | Name → **IPv4** | `example.com → 93.184.216.34` |
| **AAAA** | Name → **IPv6** | `example.com → 2606:2800:220::` |
| **CNAME** | Alias → another **name** | `www → example.com` |
| **MX** | Mail servers (with priority) | `10 mail.example.com` |
| **NS** | Authoritative name servers | `ns1.example.com` |
| **TXT** | Arbitrary text — SPF/DKIM, domain verification | `"v=spf1 include:..."` |
| **PTR** | IP → name (**reverse** DNS) | `34.216.184.93.in-addr.arpa` |
| **SRV** | Service location (host + port) | used by K8s/AD service discovery |
| **SOA** | Zone authority & serial metadata | one per zone |
| **ALIAS / ANAME** | CNAME-like at the zone apex (cloud-specific) | AWS Route 53 alias |

**TTL (Time To Live)** — how long resolvers may cache a record.
⭐ **Lower the TTL *before* a planned migration** (e.g. to 60 s), or clients will keep hitting the
old IP for hours.

### `/etc/hosts` — the local override
```
127.0.0.1     localhost
::1           localhost
10.0.0.50     myapp.local
```
Checked **before** DNS. Great for local testing (e.g. pointing an Ingress hostname at a cluster
IP), and a classic source of "it works on my machine only".
Resolver configuration lives in `/etc/resolv.conf` (`nameserver 8.8.8.8`).

### DNS tools
```bash
dig google.com                 # ⭐ full query/answer detail
dig +short google.com          # just the IP
dig google.com MX              # a specific record type
dig @8.8.8.8 google.com        # ⭐ query a SPECIFIC resolver (bypass local DNS)
dig -x 8.8.8.8                 # reverse lookup (PTR)
dig +trace google.com          # walk the full delegation chain
nslookup google.com            # simpler, cross-platform
host google.com                # one-line answer
getent hosts myapp             # ⭐ resolves the way applications do (hosts + DNS)
cat /etc/resolv.conf           # which nameservers am I using?
systemd-resolve --status       # on systemd-resolved systems
```

### DNS in containers & Kubernetes ⭐
- **Docker:** on a **user-defined** network, Docker runs an embedded DNS server so containers
  resolve each other by **container name** or service name.
  In the class demo, nginx proxies to `http://backend:5000` and Flask connects to `host="database"` —
  those are DNS names resolved by Docker.
  *(The default `bridge` network does **not** provide name resolution — that's why you always create
  a user-defined network.)*
- **Kubernetes:** CoreDNS gives every Service a name:
  ```
  <service>.<namespace>.svc.cluster.local
  e.g. backend.default.svc.cluster.local   (short form: `backend` inside the same namespace)
  ```

> 🩺 **"It's always DNS."** When something breaks, prove name resolution separately from
> connectivity: `ping <IP>` (network fine?) then `dig <name>` (DNS fine?).

---

## 🔒 HTTP & HTTPS

### HTTP — HyperText Transfer Protocol
- **Layer 7**, runs over **TCP port 80**.
- **Request/response** and **stateless** — each request is independent (state is added with
  cookies, tokens or sessions).

**Request structure**
```http
GET /api/users?page=2 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGci...
Content-Type: application/json
User-Agent: curl/8.5.0
```

**Methods**
| Method | Purpose | Idempotent? |
|---|---|---|
| **GET** | Retrieve a resource | ✅ |
| **POST** | Create / submit | ❌ |
| **PUT** | Replace a resource entirely | ✅ |
| **PATCH** | Partially update | ❌ |
| **DELETE** | Remove a resource | ✅ |
| HEAD | Headers only (no body) | ✅ |
| OPTIONS | Supported methods / CORS preflight | ✅ |

**Status codes** — read the *first digit* first
| Class | Meaning | Key codes |
|---|---|---|
| **1xx** | Informational | 101 Switching Protocols (WebSocket) |
| **2xx** | ✅ Success | **200** OK, 201 Created, 204 No Content |
| **3xx** | Redirect | 301 Moved Permanently, 302 Found, 304 Not Modified |
| **4xx** | ❌ **Client** error | **400** Bad Request, **401** Unauthorized, **403** Forbidden, **404** Not Found, 409 Conflict, 429 Too Many Requests |
| **5xx** | 💥 **Server** error | **500** Internal Server Error, **502** Bad Gateway, **503** Service Unavailable, **504** Gateway Timeout |

> 🩺 **DevOps triage by code:**
> - **401/403** → auth/permissions (token, IAM, RBAC)
> - **404** → wrong path/route, or Ingress/Service selector doesn't match
> - **502 Bad Gateway** → ⭐ the proxy is up but the **upstream is down/crashed** (check the app container)
> - **503** → no healthy backends (all replicas failing readiness probes)
> - **504** → upstream too slow (timeout tuning, slow query)

### HTTPS = HTTP + TLS
- Runs on **TCP port 443**.
- Adds three guarantees:
  1. **Encryption** — nobody on the path can read the traffic
  2. **Authentication** — the certificate proves you're talking to the real server
  3. **Integrity** — tampering is detected

**TLS handshake (simplified)**
```
1. Client Hello   → supported cipher suites, TLS version, SNI (hostname)
2. Server Hello   → chosen cipher + X.509 CERTIFICATE (contains the public key)
3. Client verifies the certificate against trusted CAs (chain, expiry, hostname)
4. Key exchange   → both derive a shared SESSION key (ECDHE)
5. Encrypted symmetric-key communication from here on
```
- **Asymmetric** crypto (slow) is used only to agree on a **symmetric** session key (fast).
- **CA (Certificate Authority)** — the trusted third party that signs certificates
  (Let's Encrypt is the free, automated one).
- **SNI (Server Name Indication)** — lets one IP serve many HTTPS hostnames ⭐ (this is how
  Ingress host-based routing works).
- **TLS termination** — the load balancer/Ingress decrypts and forwards plain HTTP internally.

```bash
curl -I https://example.com                     # headers + status
curl -v https://example.com                     # full TLS handshake detail
openssl s_client -connect example.com:443       # inspect the certificate chain
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -dates                  # ⭐ check expiry dates
```

> ⚠️ **Expired certificates are a top-5 outage cause.** Automate renewal (cert-manager +
> Let's Encrypt in Kubernetes) and alert 30 days before expiry.

**HTTP versions**
| Version | Transport | Highlight |
|---|---|---|
| HTTP/1.1 | TCP | One request at a time per connection (keep-alive) |
| HTTP/2 | TCP | Multiplexing, header compression, server push |
| HTTP/3 | **QUIC over UDP** ⭐ | Faster handshakes, no TCP head-of-line blocking |

---

## 📡 DHCP

**DHCP (Dynamic Host Configuration Protocol)** automatically hands a device its IP configuration
so nobody has to configure it by hand. Runs on **UDP 67 (server) / 68 (client)**.

**The DORA process** ⭐
```
1. DISCOVER  — client broadcasts "does anyone have an IP for me?"
2. OFFER     — DHCP server offers an address + mask + gateway + DNS
3. REQUEST   — client formally requests that offer
4. ACK       — server acknowledges and records the LEASE
```

What DHCP delivers: **IP address, subnet mask, default gateway, DNS servers, lease time**
(and optionally NTP servers, domain name, routes).

> 🩺 If DHCP fails, the OS self-assigns a **`169.254.x.x`** (APIPA) address — a dead giveaway.
> Servers usually get **static** or **DHCP-reserved** addresses instead, so their IP never changes.

---

## ⚖️ Load Balancers, Proxies & Firewalls

### Load Balancer
Distributes incoming traffic across multiple backend instances → **scalability + high availability**.

| Type | Layer | Decides on | Example |
|---|---|---|---|
| **L4 load balancer** | 4 (Transport) | IP + port only. Fast, protocol-agnostic. | AWS NLB, `kube-proxy` |
| **L7 load balancer** | 7 (Application) | URL path, hostname, headers, cookies | AWS ALB, nginx, **Kubernetes Ingress** ⭐ |

**Algorithms:** Round Robin · Least Connections · IP Hash (sticky) · Weighted · Least Response Time.
**Health checks** are essential — the LB must stop sending traffic to a dead backend
(this is exactly what Kubernetes **readiness probes** do).

### Proxies
| Type | Sits in front of | Purpose |
|---|---|---|
| **Forward proxy** | The **client** | Egress control, caching, anonymity, corporate filtering |
| **Reverse proxy** ⭐ | The **server** | TLS termination, load balancing, caching, routing, hiding internal topology |

**nginx as a reverse proxy** — exactly the pattern used in the Session-8 demo:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;

    location / {
        try_files $uri $uri/ =404;      # serve static frontend files
    }

    location /api {
        proxy_pass http://backend:5000/api;   # ⭐ forward /api to the backend container
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
This solves CORS neatly: the browser only ever talks to **one** origin (port 8080), and nginx
routes `/api` internally over the Docker network.

### Firewalls & Security Groups
Filter traffic by **source/destination IP (CIDR), port and protocol**.

```bash
# ufw (Ubuntu)
ufw status
ufw allow 22/tcp
ufw allow from 10.0.0.0/8 to any port 3306 proto tcp
ufw enable

# firewalld (RHEL)
firewall-cmd --list-all
firewall-cmd --permanent --add-port=80/tcp && firewall-cmd --reload

# iptables (low level — what Docker/K8s manipulate under the hood)
iptables -L -n -v
iptables -t nat -L -n            # ⭐ see Docker's port-mapping DNAT rules
```

**Cloud security groups** are stateful, allow-list-only firewalls attached to instances:
| Rule | Type | Protocol | Port | Source |
|---|---|---|---|---|
| SSH from office only | Inbound | TCP | 22 | `203.0.113.0/24` ✅ |
| Public web | Inbound | TCP | 443 | `0.0.0.0/0` ✅ |
| DB from app tier only | Inbound | TCP | 3306 | *sg-app* / `10.0.2.0/24` ✅ |
| SSH from anywhere | Inbound | TCP | 22 | `0.0.0.0/0` ⚠️ **never do this** |

> 🔑 **Principle of least privilege:** open the narrowest port range from the narrowest source
> that works. `0.0.0.0/0` belongs on 80/443 — nowhere else.

---

## 🛠️ Basic Networking Commands

| Command | Description | Example |
|---|---|---|
| `ping` | Check reachability (ICMP) | `ping google.com` |
| `ip a` / `ifconfig` | Show IP / interface config | `ip a` |
| `ip r` / `route` | Routing table | `ip r` |
| `ip neigh` / `arp -a` | ARP table (IP ↔ MAC) | `ip neigh` |
| `ss -tulnp` | Listening ports + owning process | `ss -tulnp` |
| `netstat -tulnp` | Legacy equivalent of `ss` | `netstat -tulnp` |
| `traceroute` | Path (hops) to a host | `traceroute google.com` |
| `mtr` | Continuous traceroute + loss stats | `mtr google.com` |
| `dig` / `nslookup` / `host` | DNS lookups | `dig +short google.com` |
| `curl` | HTTP client / API testing | `curl -I https://example.com` |
| `wget` | Download files | `wget https://example.com/f.zip` |
| `nc` (netcat) | Test if a port is open | `nc -zv host 3306` |
| `nmap` | Port/host scanning | `nmap -p 1-1000 10.0.0.5` |
| `tcpdump` | Packet capture | `tcpdump -i eth0 port 80` |
| `lsof -i :PORT` | Which process owns a port | `lsof -i :8080` |
| `ethtool` | NIC driver/hardware info | `ethtool -S eth0` |
| `arping` | ARP-level reachability / duplicate IPs | `arping -D -I eth0 192.168.1.1` |

**Frequently used forms**
```bash
ping -c 4 8.8.8.8              # ⭐ 4 packets then stop (default is forever)
ping -c 4 google.com           # tests DNS *and* connectivity together

ip a                           # my addresses
ip r                           # my routes
ip route get 8.8.8.8           # ⭐ which interface/gateway would be used?
hostname -I                    # just my IP(s)
curl ifconfig.me               # ⭐ my PUBLIC IP as seen from the internet

ss -tulnp                      # ⭐ the single most useful port command
ss -tan state established      # active TCP connections

traceroute -n google.com       # numeric, faster
mtr -r -c 10 google.com        # report mode

dig +short google.com
dig @1.1.1.1 example.com       # bypass the local resolver

nc -zv localhost 8080          # ⭐ port open?
nc -zv -u localhost 53         # UDP port check
nc -l 9000                     # listen on 9000 (quick server for testing)

tcpdump -i any -n port 5000 -c 20        # 20 packets on port 5000
tcpdump -i any -n host 10.0.0.5          # traffic to/from one host
tcpdump -i any -n -w capture.pcap        # save for Wireshark
```

---

## 🪜 The Network Troubleshooting Ladder

Work **bottom-up through the layers** — each step eliminates one layer.

```
1. Is the interface up, do I have an IP?
   ip a          →  ip link show
   (169.254.x.x? → DHCP failed)

2. Can I reach my own gateway?  (Layer 2/3 local)
   ip r          →  ping <gateway-ip>

3. Can I reach the internet by IP?  (Layer 3 routing)
   ping -c 4 8.8.8.8
   ✗ → routing / firewall / NAT problem

4. Does DNS work?  (Layer 7 DNS)
   ping -c 4 google.com   |   dig google.com   |   cat /etc/resolv.conf
   IP works but name doesn't → ⭐ it's DNS

5. Is the remote PORT open?  (Layer 4)
   nc -zv host 3306   |   telnet host 3306
   ✗ → service not listening, or firewall/security group blocking

6. Is the service listening LOCALLY, and on which address?
   ss -tulnp | grep :3306
   ⭐ bound to 127.0.0.1 → unreachable from outside; must bind 0.0.0.0

7. Does the application respond correctly?  (Layer 7)
   curl -v http://host:8080/health
   4xx → client/auth/path    5xx → server/upstream

8. Still stuck? Look at the packets.
   tcpdump -i any -n port 3306
   SYN with no SYN-ACK  → blocked/dropped (firewall)
   SYN → RST            → nothing listening on that port
```

**Reference cheat sheet: common failures**
| Symptom | Most likely cause |
|---|---|
| `Destination host unreachable` | Routing / wrong subnet / gateway down |
| `Request timed out` | Firewall silently dropping (DROP, not REJECT) |
| `Connection refused` | ⭐ Nothing is listening on that port |
| `Name or service not known` | DNS failure / typo / wrong resolver |
| `Connection reset by peer` | Server closed abruptly, or TLS/protocol mismatch |
| Works by IP, not by name | DNS (records, TTL, resolver, `/etc/hosts`) |
| Works locally, not remotely | Bound to `127.0.0.1` instead of `0.0.0.0`, or firewall |
| `502 Bad Gateway` | Reverse proxy up, upstream app down |
| `503 Service Unavailable` | No healthy backends behind the LB |
| Intermittent failures | Only *some* replicas are broken (LB spreading traffic) |
| `169.254.x.x` address | DHCP did not respond |

---

## 🔗 References

**From the session's resource list** (github.com/Nency-Ravaliya):
- Network Troubleshooting — https://github.com/Nency-Ravaliya/Network-Troubleshooting
- OSI & Network Devices — https://github.com/Nency-Ravaliya/OSI-Network-devices
- Networking — https://github.com/Nency-Ravaliya/Networking
- Subnetting — https://github.com/Nency-Ravaliya/Subnetting
- IP-quest — https://github.com/Nency-Ravaliya/IP-quest
- IPFIX / NetFlow / NTP — https://github.com/Nency-Ravaliya/IPFIX-NETFLOW-NTP
- How DHCP Works — https://github.com/Nency-Ravaliya/How-DHCP-Works
- Networking list — https://github.com/stars/Nency-Ravaliya/lists/networking

**Other**
- Linux `ip` command cheat sheet — http://www.LinuxTrainingAcademy.com
- RFC 1918 (private addresses) — https://www.rfc-editor.org/rfc/rfc1918
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
