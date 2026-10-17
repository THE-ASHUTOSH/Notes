# ⚡ S04 · Networking Fundamentals

> *Revision card.* Full notes → [Session 4](../04_Networking_Fundamentals.md)

---

## 🔑 One-line core

***Network bits + host bits = 32. Usable hosts = 2^host − 2.*** And when it breaks,
it's DNS.

---

## 🪜 Layers you actually touch

| L | | Example |
|---|---|---|
| **7** | Application | HTTP, DNS, SSH |
| **4** | Transport | **TCP / UDP** — ports |
| **3** | Network | **IP** — addresses, routing |
| **2** | Data link | Ethernet, MAC, ARP |
| **1** | Physical | copper, fibre, radio |

---

## 🔢 CIDR — the whole exam

```
/24  →  255.255.255.0    →  2^8  − 2 = 254 hosts
/25  →  255.255.255.128  →  2^7  − 2 = 126
/26  →  255.255.255.192  →  2^6  − 2 =  62
/27  →  255.255.255.224  →  2^5  − 2 =  30
/28  →  255.255.255.240  →  2^4  − 2 =  14
/16  →  255.255.0.0      →  65,534
```

> ⭐ **Bigger number = smaller network.** `−2` is the **network address** and the
> **broadcast address**.

**Worked:** `192.168.10.0/26` → block size 64 → subnets `.0 .64 .128 .192`;
for `.64`: network `.64`, usable `.65–.126`, **broadcast `.127`**.

---

## 🏠 Private ranges (RFC 1918) — memorise

```
10.0.0.0/8          ← VPCs, pod networks
172.16.0.0/12       ← docker0 is 172.17.0.0/16
192.168.0.0/16      ← home routers
127.0.0.1           ← loopback
0.0.0.0             ← "all interfaces" / "any destination"
169.254.0.0/16      ← link-local (APIPA = DHCP failed)
```

---

## 🚪 Ports to know cold

| | | | |
|---|---|---|---|
| **22** SSH | **53** DNS | **80** HTTP | **443** HTTPS |
| 25 SMTP | 3306 MySQL | **5432** Postgres | **6379** Redis |
| 27017 Mongo | 9090 Prometheus | 3000 Grafana | **6443** K8s API |

`0–1023` = well-known, **root only** · `1024+` = anyone · `32768–60999` = ephemeral

---

## 🔁 TCP vs UDP

| TCP | UDP |
|---|---|
| handshake (SYN/SYN-ACK/ACK) | none |
| ordered, reliable, retransmits | fire and forget |
| flow + congestion control | nothing |
| **20-byte** header | **8-byte** header |
| HTTP, SSH, DB | **DNS**, VoIP, video, gaming |

***TCP = reliable. UDP = fast.*** A late audio frame is as useless as a lost one.

---

## 🧭 DNS

| Record | |
|---|---|
| `A` / `AAAA` | name → IPv4 / IPv6 |
| `CNAME` | name → name |
| `MX` | mail |
| `TXT` | SPF, verification |
| `NS` | nameservers |

Order: **`/etc/hosts` → cache → resolver → root → TLD → authoritative**. TTL controls caching.

---

## 🩺 The troubleshooting ladder

```
1. ping host           L3 — is it reachable?
2. nc -zv host port    L4 — is the port open?
3. curl -v URL         L7 — does the app answer?
4. dig name            is DNS even right?
```

| Symptom | Means |
|---|---|
| **Connection refused** | reached the host, **nothing listening** |
| **Timeout / hang** | firewall or wrong route |
| `NXDOMAIN` | DNS has no record |
| 502 / 503 from a proxy | backend down or **no healthy endpoints** |

---

## ⚠️ Traps

- Binding `127.0.0.1` instead of **`0.0.0.0`** → unreachable from outside the container
- `/24` has **254** usable, not 256
- 4xx = client's fault, **5xx = server's**

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Hosts in `/27`? | **30** |
| Broadcast of `10.0.1.0/24`? | `10.0.1.255` |
| Refused vs timeout? | nothing listening vs firewall |
| Why `0.0.0.0`? | listen on **all** interfaces |

---

⬅️ [S03](./03_Shell_Scripting.md) · ➡️ [S05 · Git](./05_Git_and_GitHub.md)
