# Session 2 — Computer Networking: Eagle Eye View 🦅

> **Topics:** OSI L1–L7 · CSMA/CA vs CSMA/CD · Starlink as a physical layer · SS7 ·
> Encapsulation · Why an SMS is 140 bytes · ISUP & SIP · BBR · TCP handshake & teardown ·
> SYN cookies · The round-trip tax · UDP · QUIC/HTTP3 · SMTP · MIME · POP3 · IMAP · FTP
>
> 📄 Source: *CN at Scaler — Lesson 2*, "OSI · SS7 · Hands-on Protocols".

> ⭐ **One idea runs through the entire session:**
> **One layer's headers are another layer's body.**
> In Ethernet, in SS7, in email, in FTP. Two committees, fifty years apart, one idea.

Seven syscalls make a server. Seven layers of nesting carry eleven bytes. Today we open both
ends.

---

## 📑 Table of Contents

1. [Sockets, in one slide](#-sockets-in-one-slide)
2. [OSI — seven layers](#-osi--seven-layers)
3. [L1/L2: on a wire you detect collisions, on radio you can only avoid them](#-l1l2-on-a-wire-you-detect-collisions-on-radio-you-can-only-avoid-them)
4. [L1: your packet can go to space and nothing above L2 notices](#-l1-your-packet-can-go-to-space-and-nothing-above-l2-notices)
5. [SS7 — the second internet](#-ss7--the-second-internet)
6. [SS7 vs TCP/IP, stack to stack](#-ss7-vs-tcpip-stack-to-stack)
7. [Packet shape — the onion](#-packet-shape--the-onion)
8. [Seven layers of nesting to carry eleven bytes](#-seven-layers-of-nesting-to-carry-eleven-bytes)
9. [Why an SMS is 140 bytes](#-why-an-sms-is-140-bytes)
10. [GSM-7: 160 characters in 140 bytes](#-gsm-7-160-characters-in-140-bytes)
11. [Sending a text is a database lookup wrapped in a queue](#-sending-a-text-is-a-database-lookup-wrapped-in-a-queue)
12. [ISUP — a phone call](#-isup--a-phone-call)
13. [SIP — the same call, HTTP-shaped](#-sip--the-same-call-http-shaped)
14. [SS7 vs TCP — the same eleven problems](#-ss7-vs-tcp--the-same-eleven-problems)
15. [BBR — loss is the wrong signal](#-bbr--loss-is-the-wrong-signal)
16. [TCP open — the three-way handshake](#-tcp-open--the-three-way-handshake)
17. [SYN cookies](#-syn-cookies)
18. [TCP close — four segments](#-tcp-close--four-segments)
19. [The round-trip tax](#-the-round-trip-tax)
20. [UDP](#-udp)
21. [QUIC and HTTP/3](#-quic-and-http3)
22. [SMTP — speak it by hand](#-smtp--speak-it-by-hand)
23. [MIME — images travel as text](#-mime--images-travel-as-text)
24. [POP3](#-pop3)
25. [IMAP vs POP](#-imap-vs-pop)
26. [Framing, again: length or delimiter](#-framing-again-length-or-delimiter)
27. [FTP — two connections, always](#-ftp--two-connections-always)
28. [Key Terms Recap](#-key-terms-recap)
29. [Session Takeaways](#-session-takeaways)

---

## 🔌 Sockets, in one slide

A recap of [Session 1](./01_Network_Programming_101.md) — the six calls plus `close`:

```
socket → bind → listen → accept → read → write → close
```

Everything else in `echo_server.c` is **address bookkeeping**.

| | |
|---|---|
| **`listen(fd, 1)`** | The `1` is the **accept-queue depth**, not a connection limit. ⭐ Remember it — it comes back under **SYN floods**. |
| **`htons`** | Host to network, short. The wire is **big-endian**; your laptop probably isn't. |
| **Client** | **No bind, no listen.** The kernel picks an ephemeral source port; `connect()` triggers the handshake. |
| **`SO_LINGER {1,0}`** | Normal `close()` sends **FIN** and leaves the socket in `TIME_WAIT` for **2 MSL**. Linger-zero sends **RST**: immediate teardown, unsent data discarded, no `TIME_WAIT`. ⚠️ Fast. Also lossy. Demonstration only. |

---

## 🪜 OSI — seven layers

> A **1984 committee model** that has outlived almost everything built on top of it. Seven
> layers, each one refusing to care about the others.

| | Layer | Examples |
|---|---|---|
| **L7** | Application | HTTP · FTP · DNS · SMTP |
| **L6** | Presentation | Encryption, compression, encoding |
| **L5** | Session | Session management, authentication |
| **L4** | Transport | **TCP · UDP** |
| **L3** | Network | **IP · ICMP** · routing |
| **L2** | Data link | Ethernet · MAC · ARP · switches |
| **L1** | Physical | Cables, signals, hardware |

### Both of L4's answers

| **TCP** | **UDP** |
|---|---|
| Connection-oriented | Connectionless |
| Reliable, ordered delivery | No delivery guarantee, no ordering |
| Flow and congestion control | Fast, low overhead |
| Error recovery | Low latency |
| ⚠️ Higher latency | |
| HTTP, FTP, SMTP, SSH | DNS, VoIP, video calls, gaming |

> 💡 **The postal analogy.** TCP is registered post: numbered, signed for, re-sent if lost,
> delivered in order. UDP is dropping postcards in a box: cheap, fast, and some won't arrive.
> For a video call a *late* frame is as useless as a lost one — so UDP is the **correct**
> choice, not the lazy one.

---

## 📡 L1/L2: on a wire you detect collisions, on radio you can only avoid them

Same L3 and above. A **completely different L1 and L2 problem**.

### CSMA/CA — 802.11 (Wi-Fi)

```
Want to transmit?
   ↓
Listen to channel  (carrier sense)
   ↓
Someone transmitting? ──YES──▶ wait / defer, listen again
   ↓ NO
Random backoff  (contention window)
   ↓
Transmit frame  (out over radio)
   ↓
ACK received? ──NO──▶ back off and retransmit
   ↓ YES
Success
```

> ⭐ **Why not CSMA/CD?** A radio **cannot listen while it transmits** — its own signal drowns
> everything else out. So Wi-Fi cannot *detect* a collision the way Ethernet can. It **avoids**
> instead: sense, back off, transmit, and demand an **explicit ACK for every single frame**.

> ⚠️ **Where the time goes:** ~2 ms of contention delay before a frame even leaves. And every
> frame is individually acknowledged **at L2 — long before TCP at L4 has any idea anything
> happened.** This is why "the Wi-Fi is slow" and "the network is slow" are different problems.

---

## 🛰️ L1: your packet can go to space and nothing above L2 notices

**Starlink is a physical layer.** That is the entire point of having layers.

```
Your laptop → Ethernet/Wi-Fi → Starlink terminal → RF uplink → LEO satellite
            local network      phased-array dish   Ku/Ka-band   ~550 km · ~20 ms
            → laser crosslink → ground gateway → the internet
              optional sat-to-sat  terrestrial handoff   same IP packet
```

> ⭐ **The whole argument for layering:** nine physical hops, one of them 550 km straight up,
> and the IP header written by your laptop **arrives unchanged** — except TTL, checksum and any
> NAT rewrite. **L3 and above never learn that space was involved.**

---

## ☎️ SS7 — the second internet

> There is a second internet. **You used it this morning and you have never seen a packet from
> it.**

### SS7's one big idea (1975): get the signalling out of the voice channel

**Before — in-band signalling**

```
│ Voice │ 2600 Hz tone │ Voice │ … dialled digits as MF tones …
   what you say   "this trunk is idle"
```

One channel carries **both** the conversation and the control.
⚠️ **Anyone who can make the sound can make the decision** — this is literally how *phone
phreaking* and blue boxes worked.

**After — out-of-band signalling (SS7, 1975)**

```
Voice bearer — 64 kbps DS0        the conversation, and nothing else
─────────────────────────────────────────────────────────────────
Signalling network — MTP / SCCP / TCAP / MAP / ISUP
                                  a separate packet-switched network
                                  the caller never touches
```

> ⭐ Same separation of concerns as a **control plane and a data plane**. Fifty years old, and
> every network you build still does it — Kubernetes, SDN, SIP, even FTP's two connections.

---

## 🧱 SS7 vs TCP/IP, stack to stack

> ⚠️ **SS7 is a whole stack; TCP is one protocol at L4.** The fair comparison is stack to stack.

| OSI | **SS7 stack** | **TCP/IP stack** |
|---|---|---|
| **L7** | **MAP · INAP · CAP · ISUP** — call setup, roaming, SMS | **HTTP · DNS · SMTP · SIP** |
| **L5–L6** | **TCAP** — dialogues, components, ASN.1 BER | TLS / app framing — no distinct layer, folded into the app |
| **L4** | **SCCP** (classes 0–3) — subsystem numbers, Global Title Translation | **TCP / UDP** — ports, byte-stream sequencing, windowing |
| **L3** | **MTP3** — point-code routing, SLS load sharing | **IP** — best-effort datagrams, fragmentation, TTL |
| **L2** | **MTP2** — signal units, FSN/BSN, CRC-16, retransmission | **Ethernet · PPP · HDLC** — framing, MAC, FCS |
| **L1** | **MTP1** — 64 kbps DS0 on E1/T1 | copper · fibre · radio |

---

## 🧅 Packet shape — the onion

A browser on `192.168.1.42` sending `GET /` to example.com. Read top to bottom = **peeling the
onion at the receiver**.

```
L2 — ETHERNET II FRAME
┌──────────┬──────────┬───────────────┬────────────────────────────┬──────────┐
│ Dst MAC  │ Src MAC  │ EtherType     │ Payload = the whole IP pkt │ FCS      │
│   6 B    │   6 B    │ 2 B · 0x0800  │      46–1500 B (MTU)       │ 4B CRC32 │
└──────────┴──────────┴───────────────┴────────────────────────────┴──────────┘

L3 — IPv4 PACKET (20 B header)
┌─────────┬───────────┬─────┬──────────┬──────────┬────────┬────────┬───────────────┐
│ Ver/IHL │ Total Len │ TTL │ Proto=6  │ Checksum │ Src IP │ Dst IP │ TCP segment   │
│  4b+4b  │    2 B    │ 1 B │   TCP    │   2 B    │  4 B   │  4 B   │               │
└─────────┴───────────┴─────┴──────────┴──────────┴────────┴────────┴───────────────┘

L4 — TCP SEGMENT (20 B header)
┌──────────┬──────────┬─────┬─────┬─────────────┬────────┬────────────────────────┐
│ Src Port │ Dst Port │ Seq │ Ack │ Flags       │ Window │ Payload = app data     │
│   2 B    │   2 B    │ 4 B │ 4 B │ SYN/ACK/FIN │  2 B   │ MSS, typically 1460 B  │
└──────────┴──────────┴─────┴─────┴─────────────┴────────┴────────────────────────┘

L7 — APPLICATION DATA
GET / HTTP/1.1 · Host: example.com
   — an opaque byte stream TCP neither knows nor cares about
```

> ⭐ **Byte budget:** `1500 B MTU − 20 B IP − 20 B TCP = 1460 B MSS`.
> Add 14 B Ethernet + 4 B FCS and the wire frame is **1518 B**.

> 💡 This is why MTU matters. Add a VPN or a tunnel header and the MSS shrinks; get it wrong
> and large packets silently vanish (**PMTU black holes**).

---

## 📦 Seven layers of nesting to carry eleven bytes

A GSM handset sending `"Hello World!"` — MO-ForwardSM, all the way down to the octets.

```
1 MTP2 MSU   Flag · BSN+BIB · FSN+FIB · LI · [ SIO+SIF ] · CRC-16 · Flag   SIF cap 273 octets
 2 MTP3      SIO 0x83 · DPC 2065 · OPC 2050 · SLS 5                        payload 129 octets
  3 SCCP UDT Msg 0x09 · class 1 · Called GT +447700900999 · Calling GT …     99 octets
   4 TCAP    BEGIN Tag 0x62 · OTID 0x00000001 · Dialogue AARQ ACN = shortMsgMO-Relay v3
    5 Invoke Tag 0xA1 · Invoke ID 1 · opCode 46 (0x2E) = mo-ForwardSM        47 octets
     6 MAP   MO-ForwardSM-Arg · sm-RP-DA · sm-RP-OA · sm-RP-UI = 25 octets
      7 SMS-SUBMIT TPDU  MTI · TP-MR · TP-DA · TP-PID · TP-DCS 0x00 (GSM-7) · TP-VP · TP-UDL 0x0C
       8 TP-UD
         C8 32 9B FD 06 5D DF 72 36 39 04
         "Hello World!" · 12 chars · 84 bits · 11 octets
```

> ⭐ **Identical picture to Ethernet → IP → TCP → HTTP.** Different names, same onion. The
> payload just caps at **272 octets** instead of 1460 B.

---

## 📏 Why an SMS is 140 bytes

**Three independent length limits, stacked. The smallest one wins, and it defines the product.**

| Limit | Field | What it is |
|---|---|---|
| **272 octets** | **SIF** — MTP2's hard ceiling | The physical limit of a single **Message Signal Unit** |
| **~200 octets** | **sm-RP-UI** — MAP's field | What MAP is willing to carry as opaque user data |
| **140 octets** | **TP-UD** — the SMS itself | ⭐ Chosen so the whole MAP operation **always fits in one MSU** |

> ⭐ **No segmentation, no reassembly.** The 140-octet limit exists so that one text message is
> **always exactly one signalling packet**. Nothing to fragment, nothing to reorder, nothing to
> hold state for — which is precisely why SMS ran on 1980s hardware, and **why it still works
> when the data network is down**.

---

## 🔤 GSM-7: 160 characters in 140 bytes

*"I said 140 bytes, but you can send 160."* The discrepancy is a packing trick.

```
140 octets  ×8 bits  = 1120 bits  ÷7 bits/char  = 160 characters
 (TP-UD)                            (GSM 7-bit alphabet, TP-DCS = 0x00)
```

**The packing trick.** Each character is **7 bits, not 8**. The septets are pushed into one
continuous bit stream and re-sliced into octets — so after the first character, **character
boundaries stop lining up with byte boundaries**.

```
12 chars × 7 bits = 84 bits → 11 octets (88 bits), with 4 bits of zero padding
```

> ⚠️ **And the moment it breaks:** switch `TP-DCS` to **UCS-2** for an emoji or any non-Latin
> script and it is `140 ÷ 2 = 70` characters. Same 140-octet field either way.
> ⭐ **That is why one emoji can more than halve your message length — and silently cost you a
> second SMS.**

---

## 🗄️ Sending a text is a database lookup wrapped in a queue

```
Phone A → VMSC/VLR → SMSC → HLR → MSC B → Phone B
 handset  A's switch  store &  subscriber  B's switch  handset
                      forward  database
```

```
Phone A  ──SMS-SUBMIT (TPDU, ≤140 octets)──▶ VMSC
VMSC     ──MAP mo-ForwardSM, opCode 46─────▶ SMSC
SMSC     ──TCAP END: accepted, queued──────▶            ⭐ STORED. Delivery is now
                                                           the SMSC's problem.
SMSC     ──MAP sendRoutingInfoForSM(MSISDN)▶ HLR
HLR      ──IMSI + serving MSC address──────▶ SMSC
SMSC     ──MAP mt-ForwardSM (SMS-DELIVER)──▶ MSC B
MSC B    ──SMS-DELIVER over the air────────▶ Phone B
Phone B  ──delivery ack────────────────────▶
SMSC     ──SMS-STATUS-REPORT (only if you asked)──▶ Phone A
```

> 💡 **Store-and-forward is why SMS "works" when the recipient is off.** The SMSC accepts
> responsibility the moment it says *queued* — exactly like a mail server, or a message broker.
> The **HLR** is just a subscriber database: "which switch is this number on right now?"

---

## 📞 ISUP — a phone call

```
Phone A ─ off-hook + dialled digits ─▶ MSC A

MSC A  ──IAM  Initial Address Message──────▶ MSC B   (called number, bearer request)
                                             MSC B ──ring──▶ Phone B
MSC A  ◀─ACM  Address Complete──────────────  MSC B   caller hears ringback
                                             Phone B answers
MSC A  ◀─ANM  Answer Message────────────────  MSC B   voice path cut through

··· conversation: 64 kbps bearer circuit, NO SS7 involvement at all ···

Phone A ─ on-hook ─▶ MSC A
MSC A  ──REL  Release───────────────────────▶ MSC B
MSC A  ◀─RLC  Release Complete──────────────  MSC B   circuit freed
```

> ⭐ **Four messages set up a call.** During the conversation itself the signalling network is
> **completely idle** — it did its job at the edges.

---

## 🌐 SIP — the same call, HTTP-shaped

In 5G/IMS the same call is **text over IP**.

```
Alice ──INVITE sip:bob@scaler.com (SDP offer)──▶ Proxy/SBC ──INVITE──▶ Bob
      ◀──────────────────────────────────────── 100 Trying · 180 Ringing
      ◀─────────────────────────────────────────────────── 200 OK (SDP answer)
      ──ACK — end to end, past the proxy────────────────────────────▶

··· RTP / SRTP media flows DIRECTLY between the endpoints, over UDP ···

      ──BYE──▶   ◀──200 OK──
```

> ⭐ **100, 180, 200 — SIP borrowed HTTP's status codes wholesale.** Signalling is text; media
> is **RTP over UDP**. Control and data stay on **separate paths** — the same instinct as SS7,
> fifty years later.

> 💡 Try it: **Asterisk** or **FreeSWITCH**, a softphone (Linphone, Zoiper), and Wireshark with
> the SIP dissector on. *Telephony → VoIP Calls* will play the audio out of your own capture.

---

## ⚖️ SS7 vs TCP — the same eleven problems

> ⭐ **SS7 makes every hop reliable. TCP makes only the endpoints reliable.**

| Function | **SS7** | **TCP** |
|---|---|---|
| Sequencing | FSN — 7 bits, per signal unit, wraps at 128 | Sequence number — 32 bits, **per byte** |
| Acknowledgement | BSN + BIB, piggybacked on every SU | ACK number + flag, cumulative (+ SACK) |
| Retransmission | BIB toggle; PCR on long / satellite links | RTO timers, **fast retransmit** on 3 dup-ACKs |
| Flow control | SIB in an LSSU — a blunt stop/go signal | **Sliding window** advertised in every segment |
| Error detection | CRC-16 per signal unit | 16-bit ones-complement checksum |
| Addressing | Point Code (OPC/DPC) + SSN + Global Title | IP address + port number |
| Connection setup | Connectionless; SCCP class 2/3 if needed | **3-way handshake** |
| Congestion control | Hop-by-hop via MTP3 transfer-controlled | End-to-end (Reno, CUBIC, **BBR**) |
| Scope of reliability | **Per hop**, between adjacent signalling points | **End to end**, across arbitrary hops |
| Max payload | 272 octets (SIF) | ~1460 B typical, 64 KB with window scaling |
| Security | ⚠️ **None — trust by point code** | None natively; **TLS layered above** |

> ⭐ Both stacks solve the same eleven problems. **The only real disagreement is which layer
> gets to be responsible.**

---

## 📈 BBR — loss is the wrong signal

> **BBR (2016) stops treating packet loss as the signal for congestion.**

**The sawtooth is the bug.** Reno and CUBIC grow until a packet is dropped, then halve. So they
**need loss to make progress** — and on a link that drops packets for reasons *other* than
congestion (Wi-Fi, mobile, satellite), they crawl.

**What BBR measures instead:** bottleneck **bandwidth** × round-trip **propagation time**. Send
at the rate the path can actually carry, keeping the **queue near empty**.

> ⭐ Google reports up to **2,000× throughput** on some benchmarks — and much **lower latency**,
> because it stops filling buffers. Loss-based control causes **bufferbloat**: a full buffer is
> latency you added yourself.

---

## 🤝 TCP open — the three-way handshake

> **Three messages, because each direction needs its own sequence number confirmed.**

```
Client                                                    Server
  │  CLOSED — app calls connect()
  │ ──SYN  seq=1000───────────────────────────────────────▶   (in backlog)
  │ ◀─SYN ACK  seq=5000 ack=1001  MSS 1460, wscale 7───────
  │ ──ACK  seq=1001 ack=5001  (no payload)────────────────▶
  │  ESTABLISHED — both ISNs agreed        ESTABLISHED — accept() returns
  │ ──PSH ACK  seq=1001  first payload bytes──────────────▶
```

| Segment | Does |
|---|---|
| **1** | announces the **client's** initial sequence number |
| **2** | acknowledges it **and** announces the **server's** |
| **3** | acknowledges the server's |

⭐ **The server's SYN is what forces the third leg.**

> ⚠️ **SYN and FIN each consume a sequence number.** That is why `ack=1001` answers `seq=1000`
> even though the SYN carried no payload — otherwise a bare SYN would be indistinguishable from
> a retransmission.

> 💡 **Random ISN.** Early stacks counted predictably, so an attacker could guess sequence
> numbers and inject segments blind — **the Mitnick attack**. RFC 6528: the ISN is now a keyed
> hash of the 4-tuple plus a timer.

---

## 🍪 SYN cookies

Between segment 1 and segment 3 the server holds an entry in a **finite backlog**. That backlog
is the target.

| **The attack** | **The defence (1996)** |
|---|---|
| Send SYNs from **spoofed** source addresses and never complete the handshake. | ⭐ **Do not store anything.** Encode the connection parameters into the server's own **initial sequence number** — a keyed hash of the 4-tuple, a coarse timestamp and the MSS. |
| Each one costs the attacker **a single packet** and costs the server a half-open entry that lingers until it times out. | The client's ACK carries that number back, **incremented**. The server recomputes, validates, and **reconstructs the entire connection from a packet it has never seen before**. |
| Fill the backlog and legitimate connections are refused. | |

> ⚠️ **The cost:** most TCP options do not survive — you only have **32 bits of ISN** to work
> with, so window scale, SACK and timestamps are mostly lost for that connection. Which is why
> cookies **switch on under pressure** rather than always.

> ⭐ Remember `listen(server_fd, 1)` from the very first slide? That number is the thing being
> attacked. And notice the pattern: **push the state into a token the client hands back** —
> the same trick as a JWT, a signed session cookie, or a pre-signed URL.

---

## 👋 TCP close — four segments

> **Closing takes four segments, not three.** `SYN+ACK` can be combined; **`FIN+ACK` cannot** —
> because the other side may still have data to send.

```
Client                                                    Server
  │ ──FIN ACK  seq=2000 ack=6000──────────────────────────▶   the active close
  │ ◀─ACK  ack=2001───────────────────────────────────────    CLOSE_WAIT — app may still have data
  │  FIN_WAIT_2 — half-closed, still receiving
  │ ◀─ …any remaining data the server still owes…─────────
  │ ◀─FIN ACK  seq=6000 ack=2001──────────────────────────
  │ ──ACK  ack=6001───────────────────────────────────────▶
  │  TIME_WAIT — 2 MSL, then CLOSED
```

**Half-close** is **not an error** — it's a real state. After the first FIN and its ACK the
connection is **one-directional**: the client sends no more; the server keeps sending until it
closes its own side.

> ⚠️ **Sockets stuck in `CLOSE_WAIT`** are almost always **an application that forgot to call
> `close()`**. ⭐ **Not a network problem. Look at your code, not your switch.**

> ⭐ **`TIME_WAIT` is why you get "address already in use" on server restart** — and why
> `SO_REUSEADDR` exists.

```bash
ss -tan state close-wait      # your bug
ss -tan state time-wait       # normal, just wait 2 MSL
```

---

## ⏱️ The round-trip tax

> **Every round trip before your first byte is a tax, and everything modern is an attack on it.**

| Setup | Round trips before app data |
|---|---|
| **TCP** | **1 RTT** — the handshake |
| **TCP + TLS 1.2** | **3 RTT** — handshake, then ClientHello/ServerHello, then key exchange |
| **TCP + TLS 1.3** | **2 RTT** — one round trip of crypto instead of two |
| **TCP Fast Open** | **1 RTT** — a returning client puts data **in the SYN itself** |
| **QUIC / HTTP3** | ⭐ **1 RTT** — transport and crypto setup folded into a single round trip (**0-RTT** on resumption) |

> ⭐ **Bandwidth you can buy. Round trips you cannot.** Mumbai to Virginia is ~190 ms and no
> amount of money changes the speed of light. This single fact drives CDNs
> ([Session 6](./06_Abusing_CDNs.md)), edge compute, and every protocol revision since 2015.

---

## 📨 UDP

> **UDP is TCP with every promise removed.** The packets look similar; the handshake is missing
> and the retries are not there at all.

```
TCP — 20 B header, minimum
┌────┬────┬────┬────┬─────┬──────┬──────┬──────┬────────┬─────────┐
│Src │Dst │Seq │Ack │Flags│Window│Chksum│Urgent│Options │ Payload │
│2 B │2 B │4 B │4 B │     │ 2 B  │ 2 B  │ 2 B  │0–40 B  │   MSS   │
└────┴────┴────┴────┴─────┴──────┴──────┴──────┴────────┴─────────┘

UDP — 8 B header, that's all of it
┌────────┬────────┬────────┬──────────┬──────────────────┐
│Src Port│Dst Port│ Length │ Checksum │ Payload ≤65,507 B│
│  2 B   │  2 B   │  2 B   │   2 B    │                  │
└────────┴────────┴────────┴──────────┴──────────────────┘
```

**Who actually uses it:** Zoom, WebRTC, game servers, **DNS**, and every real-time streaming
protocol.

> ⭐ **A retransmitted audio frame arrives too late to play. Dropping it is the correct
> behaviour.** UDP isn't "unreliable TCP" — it's the right tool when *freshness beats
> completeness*.

> 💡 **The broadcast promise.** UDP was loved for broadcast — easy system discovery on a LAN,
> no registry, no config. In practice people just hard-coded the IPs they had already
> allocated. Some popular systems did use it; it never became what was expected.

> ⚠️ With only **length and checksum**, the application must rebuild everything else itself:
> ordering, retransmission, flow control, congestion control, connection state. Which is
> exactly what QUIC does.

---

## 🚀 QUIC and HTTP/3

> **QUIC rebuilds TCP inside UDP, in userspace.**

```
HTTP/1.1 · HTTP/2 over TCP          HTTP/3 over QUIC
┌──────────────────────────┐        ┌──────────────────────────────┐
│ HTTP/2  streams, muxed   │        │ HTTP/3  same streams,        │
├──────────────────────────┤        │         mapped onto QUIC's   │
│ TLS     separate h/s,    │        ├──────────────────────────────┤
│         extra round trips│        │ QUIC    independent streams  │
├──────────────────────────┤        │         + TLS 1.3, ONE h/s   │
│ TCP     one ordered byte │        ├──────────────────────────────┤
│         stream — 1 loss  │        │ UDP     8 bytes the kernel   │
│         stalls every     │        │         and middleboxes      │
│         stream           │        │         leave alone          │
├──────────────────────────┤        ├──────────────────────────────┤
│ IP                       │        │ IP                           │
└──────────────────────────┘        └──────────────────────────────┘
```

| | |
|---|---|
| **Head-of-line blocking, gone** | HTTP/2 multiplexes streams over one TCP connection — but **TCP still delivers one ordered byte stream**, so a single lost packet stalls all of them. ⭐ QUIC gives each stream **its own sequence space**: lose a packet, only that stream waits. |
| **Why userspace matters** | TCP lives in the **kernel**. Changing it means shipping an OS update to the entire planet and hoping no middlebox objects. ⭐ QUIC ships **in the browser** — Google can deploy a congestion-control change on Tuesday. |
| **Where it actually is** | ⚠️ People are still adopting HTTP/2. HTTP/3 is not yet QUIC-everywhere. The lecturer's read: **media over QUIC becomes widespread in the next two to five years.** |

---

## ✉️ SMTP — speak it by hand

> **The S in SMTP is Simple — it has never stood for Secure.** A mail transfer is a
> conversation, and both halves are human-readable ASCII.

| Port | Role |
|---|---|
| **25** | SMTP relay — server to server, plaintext |
| **587** | **Submission** — client to server, STARTTLS. ⭐ Use this one |
| **465** | SMTPS — implicit TLS from the first byte |
| **110 / 143** | POP3 / IMAP — retrieval |

**Why it stayed text.** Every intermediate relay must be able to **read, rewrite and add
headers**. A text protocol with a fixed delimiter is trivially extensible — you add a header
nobody understands and nothing breaks. That is why forty years of extensions bolted on cleanly:
**STARTTLS, SPF, DKIM, DMARC are all just headers and verbs**.

> ⚠️ **And why it stayed insecure.** `MAIL FROM` is **whatever you type**. There is no
> authentication in the base protocol at all. SPF, DKIM and DMARC are later patches trying to
> answer a question SMTP never asked: *is this sender allowed to say that?*

### A whole mail server in one container

```bash
# mailpit — SMTP + web UI. Accepts anything, delivers nothing, shows you everything.
podman run -d --name mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit
#   SMTP on 1025, web UI at http://localhost:8025

# greenmail — a real mailbox with a real user, and POP3 so we can fetch it back
podman run -d --name greenmail \
  -e 'GREENMAIL_OPTS=-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 \
      -Dgreenmail.users=bob:secret@localhost -Dgreenmail.verbose' \
  -p 3025:3025 -p 3110:3110 docker.io/greenmail/standalone:2.1.12
#   SMTP on 3025, POP3 on 3110, user bob / secret
```

Docker works identically — swap `podman` for `docker`. Neither container touches the internet.

### Now be the mail client

```text
$ telnet localhost 3025

EHLO scaler-demo
MAIL FROM:<jeet@scaler.com>
RCPT TO:<kshitij@scaler.com>
DATA
From: Jeet <jeet@scaler.com>
To: Kshitij <kshitij@scaler.com>
Subject: SMTP is surprisingly simple

Hello K,

We just sent this email by manually speaking SMTP.
.
QUIT
```

> ⭐ **The envelope vs the letter.** `MAIL FROM` and `RCPT TO` are the **envelope** — they
> decide where it goes. `From:` and `To:` inside `DATA` are **just text printed on the letter**,
> and your mail client shows you the letter. **They do not have to match. Nothing checks.**
> That is email spoofing in two lines.

> ⚠️ **The lone dot.** A single `.` on its own line ends the message. That is the delimiter —
> and the reason a line in your body starting with a dot gets **an extra one added**
> (*dot-stuffing*). And the **blank line between headers and body** is mandatory: miss it and
> your subject becomes body text.

---

## 🖼️ MIME — images travel as text

> A text protocol cannot carry arbitrary bytes. **So the bytes stop being arbitrary.**

```
3 BYTES IN                           4 CHARACTERS OUT
01001101 01100001 01101110     →     T   W   F   u
  0x4D     0x61     0x6E              ↑
                                 24 bits regrouped as 6 —
010011 010110 000101 101110      and 6 bits maps onto 64 safe printable characters
```

| | |
|---|---|
| **4/3** | size on the wire — ⚠️ **33% overhead, always** |
| **76** | characters per line (RFC 2045 line-length limit) |
| **The 64 characters** | `A–Z a–z 0–9 + /` and `=` for padding — chosen because **every mail system, gateway and 7-bit link ever built passes them through unchanged** |

**And how the parts are separated:**

```text
Content-Type: multipart/mixed; boundary="=_a7f3c91"

--=_a7f3c91
Content-Type: text/plain

...the message...

--=_a7f3c91
Content-Type: image/png
Content-Transfer-Encoding: base64

iVBORw0KGgoAAAANSUhEUg...

--=_a7f3c91--
```

⭐ Same delimitation idea as binary protocols: **pick a boundary that cannot appear in the body**.

---

## 📬 POP3

> **POP is four verbs, and you can hold all of it in your head.** IMAP is more popular; POP is
> easier to understand — so learn this one first.

```text
$ telnet localhost 3110

USER bob
PASS secret
STAT
LIST
RETR 1
DELE 1
QUIT
```

| Verb | Does |
|---|---|
| `STAT` | how many messages, how many bytes |
| `LIST` | one line per message: number and size |
| `RETR n` | send me message *n*, in full |
| `DELE n` | mark *n* for deletion — **applied at `QUIT`** |

> ⚠️ **Plaintext password.** `USER` and `PASS` go over the wire in the clear. **POP3S on 995**
> exists for exactly this reason.

💡 Send the SMTP message above to `bob@localhost` via port 3025, then fetch it back here on
3110. **Same bytes, two protocols.**

---

## 📂 IMAP vs POP

> IMAP fixes a lot of problems with POP — **you only feel them once you have used POP.**

| | **POP3 — port 110** | **IMAP — port 143** |
|---|---|---|
| **Where the mail lives** | On your **device**. The server is a spool to be emptied. | On the **server**. The client holds a cache. |
| **Second device** | ⚠️ Sees nothing — the first client already took it. | Same mailbox, same state, same moment. |
| **Read / unread** | Local only. Nobody else knows what you opened. | A **server-side flag**: `\Seen`, `\Answered`, `\Flagged`. |
| **Folders** | There is one. It is called the inbox. | Arbitrary hierarchy, created and renamed over the wire. |
| **Search** | Download everything first, then search locally. | `SEARCH` runs on the **server**; `IDLE` **pushes** new mail to you. |
| **Partial fetch** | No. `RETR` gives you the whole message, attachments and all. | `FETCH BODY[1]` — one MIME part, headers only, whatever you want. |

> ⭐ **The trade: POP puts the state on your machine, IMAP puts it on the server. Everything
> else follows from that one decision.**

---

## 🧩 Framing, again: length or delimiter

> **Every protocol today picked one, and some picked both.**

| | **Delimiter** | **Length** | **Both** |
|---|---|---|---|
| **Idea** | Agree on a byte sequence that ends the message. | Put the size in front and read exactly that many bytes. | Delimit the frame, then length-prefix the payload inside it. |
| **Examples** | SMTP — a lone `.` on its own line · HTTP/1.1 headers `CRLF CRLF` · MIME `--=_boundary--` · Redis CRLF between parts | SMS TPDU `TP-UDL` · HTTP `Content-Length: 4096` · SS7 MTP2 `LI`, SIF 273 · Protobuf varint prefix | IMAP literals `{310}` then 310 bytes · HTTP/1.1 CRLF headers + `Content-Length` · HTTP/2 binary framing over a stream · POP3 `+OK` line then a dotted body |
| **Good** | Cheap to write, human-readable, **streams without knowing the size in advance**. | Content can **never be confused for protocol**. No escaping, no scanning. | Human-readable control, safe binary payload. ⭐ The pragmatic answer. |
| **Cost** | ⚠️ You must **escape the delimiter** if it appears in the payload — dot-stuffing. Get it wrong and **content becomes protocol**. | ⚠️ You must know the size **before you start sending** — which is exactly what **chunked transfer encoding** exists to avoid. | ⚠️ Two parsers, two failure modes — and **request smuggling lives in the gap between them**. |

> ⭐ **There is no third option.** SMS chose length, SMTP chose a dot, IMAP chose both.

---

## 📁 FTP — two connections, always

> **FTP refuses to mix commands and data at all.** One connection for the conversation. A
> second, brand-new connection **for every file**.

### Active mode — the original design, 1971

```
Client ──control connection, port 21 ── USER, PASS, LIST, RETR ──▶ Server
Client ◀── data connection FROM port 20, INTO the client ──────── Server
```

⚠️ **The server dials back into you.** Every NAT and every firewall on earth now blocks this.

### Passive mode — added later, now effectively mandatory

```
Client ──control connection, port 21 ── PASV ──────────────────▶ Server
Client ◀── 227 Entering Passive Mode (h,h,h,h,p1,p2) ─────────── Server
Client ──data connection to the port the server just named ────▶ Server
```

⭐ **Both connections are always opened by the client** — which is the only shape NAT was ever
going to allow.

### A throwaway FTP server

```bash
mkdir -p ftp-demo && echo "hello from ftp" > ftp-demo/hello.txt

podman run --rm -it --name ftp-demo \
  -p 2121:2121 -p 30000-30009:30000-30009 \
  -v "$PWD/ftp-demo:/srv" \
  docker.io/library/python:3.13-slim \
  sh -lc 'pip install -q pyftpdlib && python -m pyftpdlib \
      --interface=0.0.0.0 --port=2121 --directory=/srv \
      --username=scaler --password=demo --write \
      --range=30000-30009 --nat-address=127.0.0.1 --debug'
```

| Flag | Why |
|---|---|
| `--range 30000-30009` | The passive-mode **data ports**, pinned to a small range so we can publish them. A real server does the same so **the firewall rule stays finite**. |
| `--nat-address` | The address the server should advertise in its `227` reply. ⭐ Inside a container it does not know its own reachable address — **so you tell it**. |
| `--debug` | Leave it on. The server log is the other half of the conversation. |

### Watch a file arrive on a socket you opened yourself

```text
terminal 1 — control                 terminal 2 — data
$ telnet localhost 2121
USER scaler
PASS demo
PWD
LIST          ─────────────────────▶ $ telnet localhost 30000
                                     (the listing appears HERE)
PASV
227 Entering Passive Mode (127,0,0,1,117,48)
RETR hello.txt ────────────────────▶ $ telnet localhost 30001
                                     (the file body appears HERE)
```

> ⭐ **Why is a port split across two numbers?** Because the reply is **text**, and in 1971
> nobody wanted a client to parse a number larger than 255 out of a comma-separated line.
> So a 16-bit port ships as **two 8-bit halves, high byte first**:
> ```
> port = 117 × 256 + 48 = 30000
> ```
> That is **network byte order — the same `htons()` from the very first slide, written by hand.**

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Encapsulation** | ⭐ One layer's headers are another layer's body |
| **MTU / MSS** | 1500 B link limit / 1460 B of TCP payload after IP+TCP headers |
| **CSMA/CD vs CSMA/CA** | Detect collisions (wire) vs avoid them (radio, + per-frame L2 ACK) |
| **SS7** | The out-of-band telecom signalling network (1975) |
| **In-band vs out-of-band signalling** | Control shares the voice channel vs control on its own network |
| **MTP1/2/3 · SCCP · TCAP · MAP · ISUP** | The SS7 stack, L1 → L7 |
| **MSU / SIF** | SS7 Message Signal Unit; its 272-octet payload ceiling |
| **TP-UD** | The 140-octet SMS payload field |
| **GSM-7** | 7-bit alphabet — 160 chars in 140 bytes; UCS-2 halves it to 70 |
| **HLR / SMSC / VLR / MSC** | Subscriber DB / store-and-forward SMS centre / visitor DB / switch |
| **IAM · ACM · ANM · REL · RLC** | The five ISUP call-setup/teardown messages |
| **SIP / RTP** | Text signalling (HTTP-shaped) / the media stream over UDP |
| **ISN** | Initial sequence number; randomised per RFC 6528 |
| **SYN cookie** | Encode connection state into the ISN so there is no backlog to exhaust |
| **`CLOSE_WAIT`** | ⭐ Your app forgot to `close()` |
| **`TIME_WAIT` / 2 MSL** | Post-close hold; why `SO_REUSEADDR` exists |
| **Half-close** | One direction shut, the other still sending — a valid state |
| **BBR** | Congestion control on bandwidth × RTT instead of loss |
| **Bufferbloat** | Latency you added yourself by filling buffers |
| **Head-of-line blocking** | One lost TCP packet stalls every multiplexed HTTP/2 stream |
| **QUIC** | TCP+TLS rebuilt over UDP in userspace; per-stream sequence spaces |
| **STARTTLS** | Upgrade a plaintext connection to TLS mid-conversation |
| **Envelope vs letter** | `MAIL FROM`/`RCPT TO` vs the `From:`/`To:` headers — ⚠️ unrelated |
| **Dot-stuffing** | Escaping a leading `.` so content can't end the message |
| **MIME / base64** | Multipart boundaries / binary-as-text at **+33%** |
| **Active vs passive FTP** | Server dials back vs client opens both connections |

---

## 🎯 Session Takeaways

1. ⭐ **One layer's headers are another layer's body.** `Ethernet → IP → TCP → HTTP` is the same picture as `MTP2 → MTP3 → SCCP → TCAP → MAP → TPDU`. Two committees, fifty years apart, one idea.
2. ⭐ **Framing has an address: length or delimiter.** SMS chose length, SMTP chose a dot, IMAP chose both. **There is no third option.**
3. ⭐ **Reliability has an address too.** SS7 put it at L2, per hop. TCP put it at L4, end to end. QUIC put it in userspace. All three were right for their network.
4. ⭐ **Control and data want separating.** Blue boxes died when SS7 split them. SIP keeps media off the proxy. FTP opens a second socket. Same instinct, three eras.
5. **Layering means a packet can go 550 km into space and nothing above L2 notices.**
6. **Wi-Fi can't detect collisions** — a radio can't hear while it transmits — so it avoids, backs off, and ACKs every frame at L2.
7. ⭐ **An SMS is 140 bytes because three limits stack and the smallest wins** — and because one message must always be exactly one signalling packet, with nothing to fragment or reassemble.
8. **An emoji halves your SMS length** (GSM-7 → UCS-2) and silently costs you a second message.
9. ⭐ **The three-way handshake exists because each direction needs its own ISN confirmed**, and SYN/FIN each consume a sequence number.
10. ⭐ **SYN cookies push state into a token the client hands back** — the same trick as JWTs and pre-signed URLs.
11. **Closing takes four segments**, `FIN+ACK` can't be merged, and **`CLOSE_WAIT` is your bug, not the network's**.
12. ⭐ **Round trips are the tax you cannot buy your way out of.** TLS 1.3, TCP Fast Open and QUIC are all attacks on the same number.
13. **UDP is the correct choice when late data is useless** — a retransmitted audio frame arrives too late to play.
14. ⭐ **QUIC moved transport to userspace** so it can ship in a browser instead of an OS update — and gave every stream its own sequence space, killing head-of-line blocking.
15. **SMTP's envelope and letter are unrelated, and nothing checks** — that's spoofing, and SPF/DKIM/DMARC are the patches.
16. **POP puts mailbox state on your device, IMAP puts it on the server.** Everything else follows.

---

## 🔗 References

- RFC 9293 — TCP — https://www.rfc-editor.org/rfc/rfc9293
- RFC 6528 — Defending against sequence-number attacks — https://www.rfc-editor.org/rfc/rfc6528
- RFC 4987 — TCP SYN flooding mitigations — https://www.rfc-editor.org/rfc/rfc4987
- RFC 9000 — QUIC — https://www.rfc-editor.org/rfc/rfc9000
- RFC 9114 — HTTP/3 — https://www.rfc-editor.org/rfc/rfc9114
- RFC 5321 — SMTP — https://www.rfc-editor.org/rfc/rfc5321
- RFC 2045 — MIME — https://www.rfc-editor.org/rfc/rfc2045
- RFC 1939 — POP3 — https://www.rfc-editor.org/rfc/rfc1939
- RFC 9051 — IMAP4rev2 — https://www.rfc-editor.org/rfc/rfc9051
- RFC 959 — FTP — https://www.rfc-editor.org/rfc/rfc959
- TCP BBR comes to GCP — https://cloud.google.com/blog/products/networking/tcp-bbr-congestion-control-comes-to-gcp-your-internet-just-got-faster
- BBR talk — https://youtu.be/VIX45zMMZG8 · Bufferbloat (2011) — https://youtu.be/qbIozKVz73g
- 3GPP TS 23.040 — SMS realisation — https://www.3gpp.org/ftp/Specs/archive/23_series/23.040/
- Mailpit — https://mailpit.axllent.org/ · GreenMail — https://greenmail-mail-test.github.io/greenmail/

---

## ➡️ Next

[Session 3 — Server Side Considerations for Scale](./03_Server_Side_Considerations_for_Scale.md)
— we can now speak every protocol on the wire. Next: what happens when a lot of people speak
them at you at once.
