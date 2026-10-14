# Session 7 — Building for Failures 🧯

> **Topics:** Failure taxonomy · What a retry actually is · When to retry · Idempotency ·
> Exponential backoff & full jitter · `Retry-After` · Circuit breakers · A video player's 96
> failure modes · Fallback vs retry · Failover, feature flags, graceful degradation ·
> `stale-if-error` · The thundering herd on recovery
>
> 📄 Source: *CN at Scaler — Lesson 7*, "Building for Failures".

> ⭐ **One discipline: fail on purpose.**

---

## 📑 Table of Contents

1. [One request, six places to fail](#-one-request-six-places-to-fail)
2. [HTTP status, revisited with one new question](#-http-status-revisited-with-one-new-question)
3. [Is this actually a retry?](#-is-this-actually-a-retry)
4. [Classify before you decide](#-classify-before-you-decide)
5. [No point retrying](#-no-point-retrying)
6. [Worth retrying](#-worth-retrying)
7. [Idempotency — the question that decides if blind retry is safe](#-idempotency--the-question-that-decides-if-blind-retry-is-safe)
8. [The retry loop everyone writes first](#-the-retry-loop-everyone-writes-first)
9. [Exponential backoff, with jitter](#-exponential-backoff-with-jitter)
10. [When the server tells you exactly how long to wait](#-when-the-server-tells-you-exactly-how-long-to-wait)
11. [The circuit breaker](#-the-circuit-breaker)
12. [Case study: a video player's 96 reasons to retry](#-case-study-a-video-players-96-reasons-to-retry)
13. [Network issues — same taxonomy, tighter clock](#-network-issues--same-taxonomy-tighter-clock)
14. [When 404 doesn't mean "give up"](#-when-404-doesnt-mean-give-up)
15. [Sometimes the answer isn't retry — it's fall back](#-sometimes-the-answer-isnt-retry--its-fall-back)
16. [Not every retry decision is a network decision](#-not-every-retry-decision-is-a-network-decision)
17. [49 minutes, and the thing still serving traffic](#-49-minutes-and-the-thing-still-serving-traffic)
18. [Failover, feature flags, graceful degradation](#-failover-feature-flags-graceful-degradation)
19. [The second outage: everyone recovering at once](#-the-second-outage-everyone-recovering-at-once)
20. [One flowchart for every failure in this session](#-one-flowchart-for-every-failure-in-this-session)
21. [Key Terms Recap](#-key-terms-recap)
22. [Session Takeaways](#-session-takeaways)

---

## 🎯 One request, six places to fail

```
  1            2              3              4              5                  6
DNS       TCP handshake  TLS handshake  Request write  Server processing  Response read
lookup
name→IP   SYN/SYN-ACK/   cert + key     bytes leave    their problem,     bytes arrive,
          ACK            exchange       your socket    now yours          or stop arriving
```

> ⭐ **Nothing fails generically — it fails at a specific stage, and the stage decides whether
> a retry can possibly help.**

> ⚠️ **A DNS timeout and a read timeout are both "timeouts" in your logs and completely
> different problems:** one **never reached a server**; the other **reached one that might have
> half-done the work.**

---

## 📊 HTTP status, revisited with one new question

| Class | Meaning | What actually happened | Retry? |
|---|---|---|---|
| **1xx** | Informational | Interim — keep listening, not a final answer | n/a |
| **2xx** | Success | The server did the thing | no need |
| **3xx** | Redirection | Ask again, somewhere else, maybe with a different method | depends |
| **4xx** | Client error | You sent something the server **will refuse every time** you send it unchanged | usually **not** |
| **5xx** | Server error | ⚠️ The server admits it failed — **but says nothing about whether it changed anything** | usually **yes** |

> ⭐ Session 5 taught **what each status means**. This session adds one question: **"does
> receiving it tell you anything about whether trying again will change the outcome?"**
> **That single question is the entire retry decision.**

---

## 🔍 Is this actually a retry?

| **RETRY** | **NOT A RETRY** |
|---|---|
| Trying the **exact same step** again, **with nothing changed**. | A valid, **different** action that looks similar. |
| Same request. Same method, same body, same headers that matter. ⭐ **You are betting that the SAME action will get a DIFFERENT result**, because you believe the failure was **transient** — the network blinked, the server was briefly overloaded, a load balancer picked an unhealthy backend. | **Refreshing an expired token and re-sending is NOT a retry** — it is a different request (new `Authorization` header), responding to information the server just gave you. ⚠️ **Auth failing outright is usually not something a retry fixes at all:** it needs a **different credential**, not another attempt with the old one. |

> ⭐ **The test:** *if you changed nothing about the request and only waited, would you call the
> second attempt identical to the first?* **If the answer is no — new token, different endpoint,
> altered payload — you are not retrying, you are handling.**

---

## 🧭 Classify before you decide

| # | Question |
|---|---|
| **1** | **Where in the request did it fail?** Before a connection existed (DNS, handshake) vs after (mid-response) |
| **2** | **Is the server admitting fault?** 5xx says *"I failed"*. 4xx says *"you failed"*. |
| **3** | **Is the action idempotent?** Same effect no matter how many times it runs? |
| **4** | **Is this transient or structural?** Will waiting 200 ms change anything, or is the resource actually gone? |

---

## 🚫 No point retrying

| | |
|---|---|
| **404 — the resource is not there** | If it doesn't exist now, it won't exist 200 ms from now — ⚠️ *unless* you have specific reason to believe otherwise ([the live-edge exception](#-when-404-doesnt-mean-give-up)). |
| **Before the handshake completes** | DNS never resolved, or TCP/TLS never finished. ⭐ **You never reached a server, so nothing about "the server" failed.** Retrying the same broken path just burns time twice. |
| **Geo-blocks** | Refused **by policy, not by accident**. **No amount of retrying changes geography.** |
| **Preflight failures** | The client already decided the real request is not allowed (CORS, mixed content). ⭐ **The real request was never sent.** |
| **Auth failing outright** | Not *"don't handle it"* — **handle it with a token refresh**, which is a different, valid flow, **not a retry**. |

---

## ✅ Worth retrying

> **Nothing was decided against you.**

| **Server admits fault** | **Environment shifted under you** |
|---|---|
| **5xx** from the server (500 / 502 / 503 / 504) | Network switch mid-flight (4G ↔ 5G, wifi ↔ cellular) |
| **Connection timeout** — you never got a socket | CDN edge / load balancer momentarily can't take the request |
| **Read timeout** — you had one, then it went quiet | Cache not found (an upstream fetch will repopulate it) |
| **DNS server not responding** — ⚠️ note: *no answer at all*, **not** *"no record"* | TLS handshake failure on an otherwise-healthy host |

---

## 🔁 Idempotency — the question that decides if blind retry is safe

| Method | Idempotent? | Retry after timeout? | Why |
|---|---|---|---|
| **GET** | yes | **safe, blindly** | reading twice changes nothing |
| **PUT** | yes | **safe, blindly** | *"set it to X"* twice = set to X |
| **DELETE** | yes | **safe, blindly** | already gone → already gone |
| **POST** | ⚠️ **no** | **only with an idempotency key** | *"charge the card"* twice = **two charges** |

> ⭐ **You didn't get a response — you don't know if the server finished the work before the
> connection died.**
> For a non-idempotent action, **blind retry can double-execute**. ⭐ **The fix isn't "don't
> retry", it's "make the server able to tell attempt #2 was the same as attempt #1"** — an
> **idempotency key** sent with the request, checked and deduplicated server-side.

> 💡 This is [Session 1](./01_Network_Programming_101.md)'s *"the network is not a function
> call"* with a concrete remedy attached. A timeout means **"I don't know"**, not **"it didn't
> happen"**.

---

## 💣 The retry loop everyone writes first

```python
while True:
    try:
        return call_upstream(request)
    except TimeoutError:
        continue        # try again. immediately. forever.
```

| ⚠️ | |
|---|---|
| **No max count** | a permanently-down dependency becomes an **infinite loop**, not a fast failure |
| **No delay** | every client **hammers the upstream at wire speed** the instant it starts failing |
| **No coordination across clients** | ⭐ when the upstream recovers, **every retry loop fires on the same tick**. This is the **thundering herd**, and it can **re-crash a server that had just come back up**. |

---

## ⏳ Exponential backoff, with jitter

```python
def retry(fn, max_attempts=5, base=0.2, cap=8.0):
    for attempt in range(max_attempts):
        try:
            return fn()
        except Retryable:
            if attempt == max_attempts - 1:
                raise
            delay = min(cap, base * 2 ** attempt)
            delay = random.uniform(0, delay)      # ⭐ "full jitter" — AWS, 2015
            time.sleep(delay)
```

**Three knobs, three jobs:**

| | |
|---|---|
| **MAX ATTEMPTS** | caps total damage — **a dead dependency fails in seconds, not forever** |
| **EXPONENTIAL** | `base × 2^attempt` spaces retries out so load on the upstream **decays** instead of holding steady |
| **FULL JITTER** | ⭐ `uniform(0, delay)` — **not `delay ± a bit`** — **decorrelates clients**. ⚠️ Without it, every client computes **the same delay** and they all retry **in lockstep** — the herd, just delayed. |

> 💡 **The analogy:** exponential backoff is *"knock less often"*. Jitter is *"and don't all
> knock at the same moment"*. **You need both** — the second one is the one people skip.

---

## 📨 When the server tells you exactly how long to wait

| Code | Name | What it means |
|---|---|---|
| **429** | Too Many Requests | Rate limit hit — **the server is fine, you're asking too fast** |
| **503** | Service Unavailable | Often paired with `Retry-After` during planned maintenance / load shedding |
| **408** | Request Timeout | Server gave up waiting for you to finish sending. Retry is fine — **nothing about your request was rejected** |

> ⭐ **Honour the `Retry-After` header. Don't backoff blindly on top of it.**
> **Rule of thumb: a server that hands you a number is smarter about its own load than your
> exponential curve is. Use the number.**

> ⚠️ Connection limits and 5/10-second interval caps exist for exactly this reason — **clients
> that ignore `Retry-After` and back off on their own schedule can still cumulatively overwhelm
> a server that told them, explicitly, to slow down.**

---

## ⚡ The circuit breaker

> *Stop asking a question you already know the answer to.* — Nygard, *Release It!* (2007)

```
   CLOSED  ──failure threshold crossed──▶  OPEN
     ▲                                       │
     │                                  cooldown
  success                                    ▼
     └────────────────────────────────  HALF-OPEN  ──failure──▶ OPEN
```

| State | Behaviour |
|---|---|
| **CLOSED** | Requests flow through normally. **Failures are counted.** |
| **OPEN** | ⭐ Requests **fail instantly, locally** — **no call is even attempted**. |
| **HALF-OPEN** | After a cooldown, let **ONE** request through as a probe. Success → close. Failure → re-open. |

> ⭐ **Backoff protects the upstream from ONE client retrying too fast. A circuit breaker
> protects the upstream from an ENTIRE FLEET still calling a service everyone already knows is
> down** — and protects the caller from **paying the full timeout cost on every one of those
> doomed calls**.

> ⭐ **This is the max-retry-count idea, one level up:** instead of capping **retries per
> request**, cap **failures per dependency**, and **remember the verdict for a while**.

---

## 🎬 Case study: a video player's 96 reasons to retry

**Why a player's retry logic is harder than an API client's:**

- ⚠️ An API client **fails visibly** — an exception, a 5xx in a log. A player that mishandles a
  failure **fails silently**, as a frozen frame or a spinner the user stares at.
- A single *"play"* session makes **hundreds of requests** — manifest, key, and dozens of
  segments — **each with a different retry policy, on one continuous user-visible timeline**.
- ⭐ **Some failures aren't network failures at all:** a DRM key can be **denied**, a codec can
  be **unsupported**, a decoder can **crash** — and the correct response is often **not
  "retry"** but **"fall back to a different stream entirely."**
- ⭐ **The retry budget is a human one:** a viewer tolerates **a few seconds of rebuffering**,
  not a few minutes of exponential backoff playing out correctly.

---

## 📶 Network issues — same taxonomy, tighter clock

| Failure | What's different for a player | Retry? |
|---|---|---|
| **DNS server not responding** | A player often has a **fallback CDN with a different hostname** to try instead | retry, **or switch CDN** |
| **Connection / read timeout** | ⭐ **Differential timeouts by request type** — a manifest fetch and a segment fetch **don't get the same budget** | yes, **tuned per type** |
| **Network switch (4G↔5G)** | ⚠️ The IP address can change **mid-download** — the in-flight request is **dead, not slow** | yes, **fresh request** |
| **Wifi off mid-playback** | ⭐ **The buffer keeps playing while offline** — retry only needs to start **once the buffer runs low** | yes, **deferred** |
| **CDN edge not responding** | Multi-CDN players **fail over to a second CDN** rather than retry the same one | ⭐ **switch, don't retry** |

---

## 🧩 When 404 doesn't mean "give up"

| **The exception: 404 on a live segment** | **Custom codes: 419 / 474 / 475** |
|---|---|
| The general rule says 404 means *don't retry*. ⚠️ **Exception:** a live stream's **newest** segment can 404 for a real reason — **the origin is still encoding it**, or the CDN hasn't finished propagating. ⭐ **It WILL exist in a few hundred milliseconds.** | Real deployments layer **application-specific codes** on top of the HTTP registry: **419** (token/session expiry — handle like auth, **not** a retry), **474/475** (internal codes seen when a segment is retried in a way that returns a **mismatched, partial** result). |
| ⭐ **The fix isn't "retry blindly"** — it's a **short, bounded retry (2–3 attempts, small fixed delay) specifically for live-edge segment requests, and nowhere else.** A 404 on an on-demand asset still means give up. | ⭐ **The lesson isn't the specific numbers** — it's that **your OWN system's status codes deserve the same classify-before-retry discipline as the RFC ones.** Document what they mean and whether they're retryable. |

---

## 🪂 Sometimes the answer isn't retry — it's fall back

| Failure | The right move |
|---|---|
| **DRM key denied / L1 vs L3** | Retrying the same licence request returns **the same denial**. ⭐ Fall back to a **lower DRM security level** or a different key system. |
| **Decoder / codec unsupported** | ⚠️ **Not transient** — the device genuinely **cannot decode this**. Fall back to an **alternate codec rendition** in the manifest. |
| **Master manifest failure** | If the **DASH** manifest fails, some players fall back to an **HLS** rendition of the same content rather than retrying DASH. |
| **Child manifest / segment / init failure** | Retryable in the network sense (backoff applies) — ⚠️ but **repeated failure escalates to a fatal, coded error** (e.g. 8018, 8022), **not an infinite retry loop**. |
| **Ad failure or timeout** | ⭐ Falls back to **content**, not to a retried ad — **the user's time budget for an ad failure is near zero**. |
| **iOS `ResetMedia`** | A platform-specific recovery: **tear down and rebuild the entire AVPlayer pipeline**, because **the failure is in device media state, not in a request at all**. |

---

## 🧠 Not every retry decision is a network decision

| | |
|---|---|
| **Business-rule-based retries** | Retry a payment-gated stream start **only if the entitlement check itself times out** — **not** if it cleanly returns *"not entitled"*. ⭐ **The HTTP layer succeeded; the business layer made a decision.** |
| **Read the response body, not just the status** | The body can carry a signal — *"degraded, use lower bitrate"*, *"maintenance, try again in N minutes"* — that changes what the client does next **far more precisely than a status code alone could**. |

> ⭐ **The general lesson:** everything above classified failures using **transport-layer**
> signals (status code, timeout type). **Real systems also carry application-layer signals, and
> a mature retry policy reads both.**

---

## 🕰️ 49 minutes, and the thing still serving traffic

| **85%** | **~1 min** | **49 min** |
|---|---|---|
| of Fastly's network returning errors | to detect the fault | to 95% recovered — **8 June 2021** |

> ⭐ [Session 6](./06_Abusing_CDNs.md)'s closing question: today's edge survives **your origin**
> dying, because a cache can serve a stale hit. **What does your system do when the edge — or a
> whole region — is the thing that dies?**

**`stale-if-error` (RFC 5861)** is the same idea pointed the other way: a cache configured to
**keep serving its last good copy even after it can no longer reach the origin to revalidate
it**. ⭐ **Not a retry at all — a decision to serve something known-stale rather than nothing.**

> ⭐ **The lesson generalises past caches: a system that can answer with slightly-wrong data
> survives outages that a system demanding perfectly-fresh-or-nothing does not.**

---

## 🛟 Failover, feature flags, graceful degradation

| **Failover** | **Feature flags** | **Graceful degradation** |
|---|---|---|
| **Primary → backup.** A circuit breaker trips **OPEN** on the primary and routes to a backup — different region, different provider, different CDN. | **Turn off the expensive part.** During an incident, a flag can disable a non-essential feature (recommendations, personalisation) to **shed load off the critical path** — ⭐ **without a deploy**. | **Answer smaller, not "no".** Lower bitrate instead of full quality. Cached recommendations instead of live ones. A slightly stale price instead of a spinner. |
| ⭐ **The client doesn't retry a dead dependency; it stops asking it and asks someone else.** | ⭐ **Graceful degradation as a lever you can pull in seconds.** | ⭐ **Every case study today has one:** the player's own buffer, the CDN's `stale-if-error`, a lower DRM tier. |

---

## 🌊 The second outage: everyone recovering at once

> ⭐ **The moment a dependency comes back up is the most dangerous moment of the whole incident
> — not the failure itself.**

- Every client that was retrying, backing off, or waiting on a circuit breaker's cooldown
  **now tries again** — and ⚠️ **without jitter they tend to be synchronised**, because they
  all started failing around the same moment, **so their backoff schedules line up**.
- ⚠️ The recovering service, at **1% of normal capacity** while it warms caches and
  re-establishes connections, receives **close to 100% of normal traffic in the first second
  it's reachable** — **and can fall right back over.**

**Mitigations:**

| | |
|---|---|
| **Jitter** | you already have it — and **this is what it was for** |
| **Staggered half-open probes** | not every circuit breaker probing on the same tick |
| **Slow start on the recovering side** | accept traffic at a **ramped** rate, not instantly at full capacity |

---

## 🗺️ One flowchart for every failure in this session

```
1. CLASSIFY        Where did it fail? Server-admitted (5xx) or client-refused (4xx)?
                   Is it idempotent?
        │
        ▼
2. STRUCTURAL?     404 / geo-block / preflight / bad auth
                   → STOP. Handle, don't retry.
        │
        ▼
3. TRANSIENT?      → RETRY. Backoff + full jitter. Cap attempts.
                     Honour Retry-After if given.
        │
        ▼
4. DEPENDENCY      Repeated failures trip a CIRCUIT BREAKER
   LEVEL           → stop asking, fail fast.
        │
        ▼
5. NO GOOD         Fail over, degrade gracefully, or serve stale
   ANSWER LEFT     → anything but nothing.
```

> ⭐ **The closing question to sit with:** every fallback here — stale cache, backup region,
> lower bitrate — **answers with something *worse* than the ideal. At what point does "worse"
> stop being acceptable, and who decides?**

---

## 📝 Key Terms Recap

| Term | Meaning |
|---|---|
| **Failure stage** | DNS → TCP → TLS → request write → server processing → response read; ⭐ the stage decides whether retry can help |
| **Retry** | The **exact same** request again, **nothing changed** |
| **Handling** (not a retry) | Token refresh, different endpoint, altered payload |
| **Idempotent** | Same effect however many times it runs — GET, PUT, DELETE |
| **Idempotency key** | ⭐ Client-supplied id so the server can deduplicate attempt #2 of a POST |
| **Transient vs structural** | Will waiting change anything, or is the resource genuinely gone? |
| **Exponential backoff** | `base × 2^attempt` — load **decays** instead of holding steady |
| **Full jitter** | ⭐ `uniform(0, delay)` — decorrelates clients; without it the herd is only delayed |
| **`Retry-After`** | 429/503/408 — ⭐ **trust the server's number over your own curve** |
| **Circuit breaker** | CLOSED → OPEN → HALF-OPEN; cap failures **per dependency**, not per request |
| **Thundering herd on recovery** | ⭐ Synchronised clients re-crash a service at 1% capacity |
| **Slow start (recovery)** | Ramp accepted traffic instead of taking 100% instantly |
| **`stale-if-error`** | RFC 5861 — serve the last good copy when the origin is unreachable |
| **Failover** | Stop asking the dead dependency; ask a different one |
| **Feature flag** | Shed load by disabling non-essential work, **without a deploy** |
| **Graceful degradation** | ⭐ Answer **smaller**, not *"no"* |
| **Live-edge 404** | The one 404 worth a short bounded retry — the segment doesn't exist **yet** |
| **DRM L1/L3 fallback** | Retry returns the same denial; drop to a lower security tier instead |

---

## 🎯 Session Takeaways

1. ⭐ **Nothing fails generically.** Six stages, and the stage decides whether a retry can possibly help. A DNS timeout and a read timeout are both "timeouts" and are **completely different problems**.
2. ⭐ **5xx says "I failed" but says nothing about whether it changed anything.** That ambiguity is the whole problem.
3. ⭐ **If you changed anything, it isn't a retry — it's handling.** Token refresh is a different request, not another attempt.
4. **Don't retry 404s, geo-blocks, preflight failures, bad auth, or anything that failed before a connection existed.** You never reached a server.
5. ⭐ **A timeout means "I don't know", not "it didn't happen".** For non-idempotent work, that's an **idempotency key**, not a prohibition on retrying.
6. **The naive loop has no cap, no delay and no coordination** — and the third one is what re-crashes the recovering server.
7. ⭐ **Full jitter, not `delay ± a bit`.** Without it every client computes the same delay and the herd is merely postponed.
8. ⭐ **A server that hands you `Retry-After` is smarter about its own load than your curve. Use the number.**
9. **Backoff protects an upstream from one client; a circuit breaker protects it from the whole fleet** — and saves the caller the full timeout cost on every doomed call.
10. ⭐ **Sometimes the answer isn't retry — it's fall back.** A denied DRM key, an unsupported codec and a failed ad all return the same result next time.
11. **A player's retry budget is human:** a few seconds of rebuffering, not a correctly-executed exponential backoff.
12. ⭐ **Your own status codes deserve the same classify-before-retry discipline as the RFC's.**
13. **Read the body, not just the status.** Application-layer signals are more precise than transport-layer ones.
14. ⭐ **A system that can answer with slightly-wrong data survives outages that a "fresh-or-nothing" system does not.**
15. ⭐ **The most dangerous moment is recovery, not failure.** Jitter, staggered probes and slow start are what stop the second outage.
16. **Every fallback answers with something worse than the ideal** — deciding *how much worse is acceptable, and who decides*, is a product question, not an engineering one.

---

## 🔗 References

- Michael Nygard, *Release It!* (circuit breakers, bulkheads, timeouts) — https://pragprog.com/titles/mnee2/release-it-second-edition/
- AWS Architecture Blog, *Exponential Backoff and Jitter* (2015) — https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- AWS Builders' Library, *Timeouts, retries and backoff with jitter* — https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- RFC 9110 §9.2 — Idempotent methods — https://www.rfc-editor.org/rfc/rfc9110#section-9.2
- RFC 9110 §10.2.3 — `Retry-After` — https://www.rfc-editor.org/rfc/rfc9110
- RFC 5861 — `stale-while-revalidate` / `stale-if-error` — https://www.rfc-editor.org/rfc/rfc5861
- draft-ietf-httpapi-idempotency-key-header — https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/
- Fastly, *Summary of June 8 outage* — https://www.fastly.com/blog/summary-of-june-8-outage
- Google SRE Book — *Addressing Cascading Failures* — https://sre.google/sre-book/addressing-cascading-failures/
- Google SRE Book — *Handling Overload* — https://sre.google/sre-book/handling-overload/
- Polly (.NET) / resilience4j (Java) / Hystrix (archived) — reference implementations

---

## ➡️ Next

[Session 8 — Streaming Video at Large Scale](./08_Streaming_Video_at_Large_Scale.md) — the
retry policy, circuit breaker and fallback logic built here go **inside a real video
pipeline**: adaptive bitrate, segment prefetch, and the CDN material from Session 6, all at
once.
