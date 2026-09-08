# Session 14 — Case Study: Messaging Applications 💬

> **Topics:** Design FB Messenger / WhatsApp / Slack · Sharding key choices for 1:1 vs group ·
> Engineering low latency **and** immediate consistency
>
> 📄 Class doc: [\[SST-2028\] Case Study: Messaging Apps (FB Messenger, WhatsApp, Slack)](https://docs.google.com/document/d/13sJnV5Xj1ZPalJeA0uuiJqe0oJYZ0U4b-0IfXjxmJac/edit?usp=sharing)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [Problem Statement](#1️⃣-problem-statement)
2. [Functional Requirements](#2️⃣-functional-requirements-fr)
3. [NFR — Message Order](#-nfr-1--message-order)
4. [NFR — Idempotency](#-nfr-2--idempotency)
5. [NFR — Consistency vs Availability](#-nfr-3--consistency-vs-availability)
6. [NFR — Consistency vs Latency](#-nfr-4--consistency-vs-latency)
7. [Scale Estimation](#4️⃣-scale-estimation)
8. [Read Heavy vs Write Heavy](#-read-heavy-vs-write-heavy)
9. [Design — Idempotency & UUID v7](#-design--idempotency--uuid-v7)
10. [Design — Message Chain for Ordering](#-design--message-chain-for-ordering)
11. [Sharding by user_id](#-sharding-key-option-1--user_id)
12. [Sharding by conversation_id](#-sharding-key-option-2--conversation_id)
13. [The Illusion of Consistency](#-the-illusion-of-consistency)
14. [Choosing the Database](#-choosing-the-right-database)
15. [Cache Design](#-cache-design)
16. [Key Terms Recap](#-key-terms-recap)

---

## 1️⃣ Problem Statement

> **"Design a messaging application"** — ⭐ **reason by analogy.**

| Product | Comparable | Defining characteristic |
|---|---|---|
| **WhatsApp** | Telegram / Signal / Hike / iMessage / Arattai | ⭐ **Mobile first** · **Realtime chat (ultra low latency < 3 sec** for the other person to receive the message) · **built as an SMS replacement** |
| **Slack** | MS Teams / Flock | ⭐ **B2B — built for enterprise chat** · **Group chat (channel) — 100k employees** |
| **Facebook Messenger** | Instagram Messages / Orkut messages | ⭐ **Messages for social media** · **1-1 messages** |

### What NOT to build
| Product | Why it's out of scope |
|---|---|
| **Discord** | ⭐ **Voice chat — low latency** |
| **Orkut** | Social Media |
| **Twitter** | X / Threads — **Social Media** |
| **Skype** | FaceTime, Zoom — **Video Chat & Screen Sharing** |
| **Hangouts / Google Meet** | **Video Calling** |
| **Snapchat** | ⭐ **Privacy — disappearing messages** |

---

## 2️⃣ Functional Requirements (FR)

> ⭐ **Some feature/functionality that you offer to the client (user / another internal system). You
> explicitly expose an API / write code for a functional requirement.**
>
> ⭐ **"Who is doing what, and based on that, what happens."**

### Actors
> - **Users** — (**sender**, **receiver**)
> - **(enterprise software — Slack)** ⭐ **Organisation:** org ⇔ admin ⇔ HR
>
> ⭐ **Whenever you think of features, think of what things the Actors can do in the app.**

> ⭐ **Always keep the "minimal" in your mind. MVP features is not a feature suggestion competition.**
> **KISS: keep it simple, silly.**
>
> ⭐ **Practice makes perfect! — *Correct* practice makes perfect. Incorrect practice harms you.**

### ✅ MVP (v0)

**1. A user should be able to send messages to other users**
```
sendMessage(sender_id: uuid,
            recipient_id: uuid,
            message: json      ): ack/failure
⭐ user-facing
```
> ⭐ **At this moment, it will be premature to try to figure out the exact contents of a message. We
> can just have it as JSON for now** — because the content of a message will change based on how
> "fancy" we want the app to be. **Also, it will frequently change in the future, so we should just
> make it schemaless.**

**2. Users should be able to receive messages, & view the past messages in a conversation (most
recent first). Users should only be able to view messages of conversations that they're a part of.**
```
getMessages(user_id: uuid,
            conversation_id: uuid,
            pagination_offset: int,
            pagination_limit: int  ): list of messages
⭐ user-facing
```
> **`conversation_id`: identifies the conversation** (Tarun+Sanjana, or Harini+Pallavi, …)

**3. Users should be able to view the conversations that they're a part of (most recent first)**
```
getConversations(user_id: uuid,
                 pagination_offset: int,
                 pagination_limit: int  ): list of conversations
                 ({conversation_id, name, unread count, a quick summary of the latest message})
⭐ user-facing
```

**4. Users can participate & send messages inside groups.** ⭐ **A single group can potentially have
100,000+ users**
```
sendMessageGroup(sender_id: uuid, group_id: uuid, message: json): ack/failure
getMessagesGroup(user_id: uuid, group_id: uuid,
                 pagination_offset: int, pagination_limit: int): list of messages
⭐ user-facing
```

### 🔜 Future Scope (v1+)
| Feature | Note |
|---|---|
| **Users should be able to see the status of the messages they've sent** | ⭐ **Sent:** received by backend server — **single tick** · ⭐ **Delivered:** delivered to the recipient's app, but not read yet — **double tick** · ⭐ **Read:** the recipient has actually read the message — **double tick (blue)** |
| **Rich messages** | react with Emojis · Videos / Images · Gifs |
| **Updating/Deleting already sent messages** | ⭐ **extremely hard to do correctly** |
| **Profile management** | |
| **Notifications** | in-App · Push |
| **Broadcast the same message to multiple people** | (batch processing) |
| **Multi-device support** | ⭐ **extremely hard to do correctly — CRDTs** |
| **Group Management** | creating · adding people · permissions · group description |
| **App should suggest / load contacts from the user's phone** | |
| **Message Forwarding** | |
| **Start a new conversation from contacts/friends** · Create/Delete conversation · Mark as Spam | |
| **Syncing messages b/w the app cache & cloud** | |
| **End to end encryption** | |

---

## 🔢 NFR 1 — Message Order

> ⭐ **Design Goals: additional constraints/behaviour that you want your system to adhere to. These
> are NOT "functionality" or "features" that you're offering to the client.**

> ⭐⭐ **Message ordering must be maintained: the messages must be seen by the recipient in the SAME
> ORDER as they're sent in by the sender.**

**Why is message order important?**
> ⭐⭐ **The meaning of a conversation can change based on the message order.**

```
   ORDER A                          ORDER B
   ───────                          ───────
   "Should I quit my job?"          "No"
   "No"                             "Should I quit my job?"
   ⭐ Same two messages. Opposite meaning.
```

---

## 🔁 NFR 2 — Idempotency

> ⭐ **Messaging apps are typically MOBILE FIRST. Mobile users don't always get perfect internet
> connections. Therefore, messaging apps have to frequently deal with n/w failures.**
>
> ⭐ **In a lot of scenarios, the frontend app (client-side) is coded to AUTOMATICALLY RETRY sending
> messages/posts/comments if the sending fails — because we don't want the user to re-type the entire
> message.**

```html
<input id="message" type="text" placeholder="send a message" onkeydown="sendMessage" />
<script>
    function sendMessage() {
        message = document.getElementById("message").text;
        sendWithRetries(message);
    }

    function sendWithRetries(message) {
        fetch("/backend-api-url/sendMessage", "POST", {
            message: message
        }).then(() => console.log("success"))
          .error(() => {
              // automatic retry after 1 second
              setTimeout(() => sendWithRetries(message), 1)
          })
    }
</script>
```

### The failure mode ⭐
> **However, if:**
> 1. **the initial request successfully goes to the server**
> 2. **the server acts on the request (stores the message/post/…)**
> 3. **responds with an ACK**
> 4. ⭐ **but the acknowledgement gets LOST and never reaches the user**
>
> **In this case:**
> - **the frontend will assume (incorrectly) that the server didn't receive our request** →
>   **automatically retry**
> - **Due to this, the server will end up storing the message/post AGAIN** → **there will be
>   duplicates**
>
> ⭐⭐ **Automatic retries on the frontend can cause duplicates in the database!**

```
   Client ──sendMessage──▶ Server ──stores it──▶ DB  ✅
   Client ◀────ACK────✗──  Server                     (ACK lost)
   Client ──sendMessage──▶ Server ──stores it AGAIN──▶ DB  💥 duplicate
```

> *(This is the same "we can't distinguish a lost message from a dead machine" problem from
> Session 4's 2PC discussion.)*

### Idempotency ⭐
> ⭐⭐ **A function f(x) is said to be IDEMPOTENT if and only if `f(x) = f(f(x))`.**
> **Repeated application of the same function does nothing more than a single application.**
>
> - **`f(x) = x²` is NOT idempotent.** Because `f(4) = 16`, but `f(f(4)) = 256`
> - **`f(x) = |x|` IS idempotent.** Because `f(-5) = 5` and `f(f(-5)) = 5`
>
> ⭐⭐ **Any WRITE (post/update/delete) API endpoint should be idempotent if your frontend can retry.**

> **Q: Does the backend engineer know / care about whether the frontend guy used automatic retries?**
> ⭐ **No. They don't care.** It could be that currently the frontend doesn't retry, but **later on,
> someone adds auto-retries to the frontend.**
>
> ⭐⭐ **Therefore, irrespective of what the frontend does, we should ALWAYS try to make our backend
> POST APIs idempotent whenever possible.**

### The subtlety ⭐
> **Note that if the user wants to purposefully resend the same message again & again, they should be
> allowed to.** 😄 *When I want to annoy my friends, I will send them "Hi" 20 times in a row. This
> should be allowed!*
>
> ⭐⭐ **Duplicates due to automatic RETRIES should be prevented — duplicates due to the USER'S INTENT
> must be allowed.**

> 🧠 **This is why you can't dedupe on content.** `("Hi", sender, receiver)` is a legitimate repeat.
> You need a **per-attempt identifier** that stays the same across retries but differs between
> genuine sends — which is exactly what the client-generated `message_id` provides.

---

## ⚖️ NFR 3 — Consistency vs Availability

> **PACELC. ⭐ Do NOT jump to an answer.**

#### Q: What is the data?
> **The messages that are being sent.**

#### Q: What does eventual consistency (stale reads) mean in this context?
> **Messages are out of order on the recipient's side / can't see the latest message.**

**Sender side:**
> - **If Pujan sends a message to Minesh at t=0, the server ACK'd Pujan's message**
> - **When Pujan reloaded his app at t=1, he is not able to see the message that he sent** (because
>   the read was stale)
> - ⭐ **Pujan thinks that his message got DELETED by the app**
> - **In reality the message is not deleted/lost — if Pujan waits long enough, he will be able to see
>   it eventually**
> - ⭐ **This type of thing is typically solved by providing "read-your-write" consistency**

**Receiver side:**
> - **If Pujan sends a message to Minesh at t=0, the server ACK'd**
> - **At t=1 when Minesh (recipient) tries to load his messages, he isn't able to see the message**
> - ⭐ **Pujan says he has sent the message. But Minesh cannot receive the message**

#### Q: Can we afford stale reads?
> ⭐⭐ **No, we cannot afford to have such stale reads.**

#### Q: What does data loss mean here?
> **Sender sent a message, and the server ACK'd — but the message actually got lost by the backend.**

#### Q: Can we afford data loss?
> ⭐⭐ **Very very bad. No.**

> ⭐⭐ **"Communication is the backbone of Human Society. Communication needs STRONG CONSISTENCY!"**

> 💡 **Contrast with Typeahead (Sessions 12–13):** there we could afford *both* stale reads *and* data
> loss, which unlocked batching and sampling. **Here we can afford neither** — so neither lever is
> available, and the design must work much harder.

---

## ⏱️ NFR 4 — Consistency vs Latency

> **What are our latency requirements?** ⭐ **Low Latency: < 5 seconds.**
>
> **We need realtime chat: if PersonA has sent a message to PersonB, and PersonB is online, then
> PersonB should receive the message within a few seconds.**
>
> **But availability is also important!**

### The apparent impossibility ⭐
> **But the PACELC theorem says that we can't have both Consistency & Latency!**
>
> **Is it possible to achieve high consistency along with high availability & low latency?**
> ⭐ **No — PACELC says it's impossible.**
>
> ⭐⭐ **However, we can create the ILLUSION of consistency with availability & low latency.**
> **In reality we will give up on consistency just a little bit, but to the end user, things will
> still appear consistent 99.xxx% of the time.**

> 🧠 **This is the single most valuable idea in the session.** When a theorem says you can't have
> what you need, the engineering answer isn't to give up — it's to ask **"who actually observes the
> inconsistency, and can I hide it from them?"** The design below does exactly that.

---

## 4️⃣ Scale Estimation

```
assumption: Total users = (web/planet scale) = 2 billion

Daily Active Users (DAU): ⭐ 80% of all users = 1.6 billion ≈ 2 billion
```
> ⭐ **Typically we consider the Pareto Principle & say that only 20% of users will be active. Will
> this be true for messaging apps like WhatsApp? NO!**
> - **Instead of only 20%, for messaging apps like WhatsApp, the number will be much higher**
> - **Note, for FB Messenger, it might still be as low as 20%**

```
assumption: Avg. number of messages per active-user per day = 10 to 20

Total number of messages / day
= (20 messages / active-user / day) × (2 billion active-users)
= ⭐ 40 billion messages / day

Avg. messages / second
= 4 × 10^10 messages / (10^5 seconds)
= ⭐ 400,000 messages / second
```

### Per-API load
| API | Load | Reasoning |
|---|---|---|
| **`sendMessage(...)`** | ⭐ **400,000 / second** avg | |
| **`getMessages(...)`** | ⭐ **800,000 / second** (assumption: **2× of sendMessage** — each message read twice on avg) | ⭐ **A message is sent once, but read multiple times — *but not by a huge margin*.** In StackOverflow/Twitter a post is made once and read **thousands or millions** of times; **in WhatsApp a message is sent once and read a handful of times** |
| **`getConversations(...)`** | ⭐ **200,000 requests/sec** | **only when the user re-opens the app.** A typical user might reopen WhatsApp **5–10 times/day** → 10 × 2 billion = **20 billion reopens/day** |
| **Peak Load** | ⭐ **2 million messages / second** | assumption: **5× the avg load** during global events like **Covid or New Year** |

### The group caveat ⭐
> **This statistic will change for groups** — in a large group, a message is sent once but read
> thousands of times.
> - ⭐ **If we have 400,000 messages/sec and each message is read 100,000 times then we have
>   40 billion requests/sec — this number is insane. No system (not even Google with its 10 million
>   servers) can handle this as of 2025**
> - ⭐ **However, in groups, the number of users participating across the globe is much lower.**
>   **Slack users ≪ WhatsApp users** — ⭐ **Slack only has 42 million DAU compared to WhatsApp's
>   2 billion**

### The data model
```
message: {
    sender_id: uuid (16b)
    receiver_id/group_id/conversation_id: uuid (16b)
    message_id: uuid (16b)
    text: string (200b avg)
    when: timestamp  (8b)
    where: geolocation (16b)
    delivery_status: enum (1b)
    attachment_url: string (200b avg)
}
```

### ⭐ Why `conversation_id` and not separate tables
> - **1:1 messages — we could have a separate table** (sender_id, receiver_id, message)
> - **In that case our group messages table will have to be separate** (sender_id, group_id, message)
> - ⭐ **What if we want 3-people messages? Should we create another table? What about ad-hoc messages
>   between 5 people? Another table? NO.**
>
> ⭐⭐ **Let's merge this. Let's just have `conversation_id`:**
> - **1:1 conversations** → `conversation_id` can just be a **tuple** of `(sender_id, receiver_id)`
> - **group conversations** → just use the **`group_id`** as the `conversation_id`
> - **ad-hoc conversations** → a separate table that incorporates all scenarios (1:1, group, 1:any):
>   ```
>   conversation_participants
>       conversation_id    user_id
>   ```

*(Exactly the Slack conclusion from Session 9: **treat a DM as an ad-hoc 2-person group**.)*

### Storage
```
Avg. size = 500 bytes/message

Amount of data / day
= (500 bytes / message) × (40 billion messages / day)
= 20 trillion bytes / day
= ⭐ 20 TB / day

Amount of data over 20 years
= (20 TB / day) × (20 × 365 days)  ≈  (20 TB/day) × (~10,000 days)
= ⭐⭐ 200 Petabytes
```
> **Can this amount of data fit on a single server?**
> ⭐ **No. As of 2026, we can store up to 3 PB on a single server, not 200 PB. Even if we could, a
> single server won't be able to handle 2 million messages/sec.**
>
> ⭐ **We definitely need sharding!**

---

## ⚖️ Read Heavy vs Write Heavy

```
Writes (sendMessage): ⭐ 400,000 / second (avg)   →  2 million/sec (peak)
Reads  (getMessages): ⭐ 800,000 / second (avg)   →  4 million/sec (peak)
```
> ⭐⭐ **Neither is 10× or more larger than the other — neither is dominating. This is BOTH read &
> write heavy, but neither dominates!**
>
> ⭐ **It is very challenging to design systems which are both read & write heavy. This means that we
> will either have to convert this into a read-heavy system or into a write-heavy system.**

### Applying the Session-13 decision table ⭐
| Lever | Available? | Why |
|---|---|---|
| **Batching** | ❌ | ⭐ causes **stale reads** — **but we want low latency** |
| **Sampling** | ❌ | ⭐ causes **potential data loss** — **we cannot afford data loss** |
| ⭐ **Absorb reads in a cache** | ✅ | ⭐ **the only option left** |

> ⭐⭐ **So the only solution is to reduce the reads that go to the database — by absorbing the reads
> in the cache. Also, since the messages are mostly IMMUTABLE (edits/deletes are rare), caching will
> work well.**
>
> ⭐⭐ **So we will have LOTS of cache, and the database will be optimized for WRITES.**

---

## 🆔 Design — Idempotency & UUID v7

> ⭐ **Each message will have a unique `message_id` that is generated on the CLIENT SIDE.**

### UUID v7 ⭐
| Property | Detail |
|---|---|
| **universally unique** | no coordination needed |
| **decentralized** | ⭐ generated on the client, no server round-trip |
| **sparse** | not guessable/enumerable |
| ⭐ **roughly sortable** | **time-ordered prefix** — sorts approximately by creation time |
| **widely accepted spec** | popular implementations in every major language |
| **128 bit** | |
| **high performance** | |

### The idempotency rule
> - ⭐ **Whenever the backend receives a `sendMessage` API call, it stores the message in the DB ONLY
>   IF the `message_id` is not already there in the DB**
> - ⭐⭐ **If the `message_id` is already there in the DB, it will just IGNORE the request — but it
>   will STILL SEND A SUCCESS RESPONSE (so the frontend can stop retrying)**

```html
<input id="message" type="text" placeholder="send a message" onkeydown="sendMessage" />
<script>
     function sendMessage() {
          var content = document.getElementById("message").text;
          var message = {
              id: uuid_v7(), // ⭐ note that this id will
                             // remain UNCHANGED for the retries
              content: content,
              timestamp: new Date(),
          }
          sendWithRetries(message);
      }
      function sendWithRetries(message) {
          fetch("/backend-api-url/messages", "POST", {
              message: message
          }).then(() => console.log("success"))
            .error(() => {
                // automatic retry after 1 second
                setTimeout(() => sendWithRetries(message), 1)
          })
      }
</script>
```

> ⭐ **Returning success on a duplicate is the crucial detail.** If you returned an error, the client
> would retry forever. Idempotency isn't just "don't double-write" — it's **"make the retry look
> like it worked"**.
>
> And note this solves the earlier subtlety: sending "Hi" 20 times deliberately produces **20
> different UUIDs**, so all 20 are stored. Only *retries* share an id.

---

## 🔗 Design — Message Chain for Ordering

### Why timestamps don't work ⭐
> ⭐ **Sorting based on `created_time` timestamp will NOT work:**
> - **because the recipient doesn't even know that there's a message pending until the message
>   arrives**
> - ⭐ **by the time the receiver's app realises that an intermediate message arrived late, it was
>   already too late — it had already shown the later messages to the user**
>
> ⭐⭐ **Note that NO backend-based solution (SQS / buffer / …) will work — because the backend doesn't
> even know that there's a message pending until the message arrives. By the time the server realises
> that an intermediate message arrived late, it had already put later messages in the queue.**

```
   sent:      M1 ──▶ M2 ──▶ M3
   arrives:   M1 ──▶ M3 ──────▶ M2   (M2 delayed)
                      ↑
              ⭐ the moment M3 is shown, it's too late — you can't un-show it.
                 Nobody (client or server) KNOWS M2 exists until it arrives.
```

### The solution — a message chain ⭐⭐
> - ⭐ **Every new message should contain the `previous_message_id` inside it**
> - ⭐ **On the recipient's side, the app will NOT SHOW a message unless its previous message has also
>   been received & shown**
> - ⭐ **Instead, if a message appears out-of-order, it will show *waiting-for-messages* until all the
>   previous messages have arrived**

```html
<input id="message" type="text" placeholder="send a message" onkeydown="sendMessage" />
<script>
     var previous_id = null;
     function sendMessage() {
          var content = document.getElementById("message");
          var id = uuid_v4()
          var message = {
              previous_id,     // ⭐ id of last message that I sent
              id: id,
              content: content,
              timestamp: new Date(),
          }
          previous_id = id;
          sendWithRetries(message);
      }
</script>
```

```
   M1 {id: a, prev: null}
   M2 {id: b, prev: a}
   M3 {id: c, prev: b}

   Receiver gets M1, M3:
     M1 → prev is null            → ⭐ SHOW
     M3 → prev is b, not shown yet → ⭐ HOLD ("waiting for messages…")
   Receiver gets M2:
     M2 → prev is a, shown        → ⭐ SHOW, then M3 unblocks → SHOW
```

> 🧠 **The insight: ordering is a CLIENT-side problem, not a server-side one**, because only the chain
> itself carries the knowledge that something is missing. It's a linked list transmitted out of
> order and reassembled at the destination — essentially what TCP sequence numbers do, applied at the
> application layer.

### The multi-sender question ⭐
> **Q: What happens when there are multiple devices, or multiple people sending messages in the same
> chat (group chat maybe) concurrently? How do we maintain the previous-message-id?**
>
> ⭐ **Don't worry. We're NOT guaranteeing any sort of message order ACROSS multiple senders.**
>
> ⭐⭐ **The intent of maintaining message order is to ensure that all messages sent by "Subhadeep"
> appear in the correct order. Messages sent by multiple senders can be interleaved in any way — we
> don't care, as long as the messages of each individual sender are in the correct order!**

> 💡 **This is a per-sender causal ordering guarantee**, and it's the *right* guarantee — a global
> total order across senders would require distributed consensus, and nobody would notice the
> difference anyway.

---

## 🔑 Sharding Key Option 1 — `user_id`

> ⭐ **This means that all the data (messages sent & received) of a particular user will be within the
> same shard.**

> **Q: Does sharding by `user_id` mean that if we have 2 billion users, we need 2 billion servers?**
> ⭐ **No! A single server will hold the data for hundreds of thousands of users.**

### 1-1 messages ✅
| API | Shards hit |
|---|---|
| `getMessages(user_id, conversation_id, …)` | ⭐ **Only the user's shard** — because all messages sent/received by the user are in their shard |
| `sendMessage(sender_id, receiver_id, …)` | ⭐ **Both sender & receiver's shard** (data replication) |
| `recentConversations(user_id)` | ⭐ **Only the user's shard** |

### Group messages ❌
| Design | `getMessages` | `sendMessage` |
|---|---|---|
| **Store in Sender Only** | ⭐ **Reads will be FAN-OUT** — because messages sent by different senders in the same group are stored in different shards | Store it only in the sender's shard |
| **Store in All Participants** | **Fast reads** — we can read from any shard | ⭐ **FAN-OUT writes** |

> ⭐⭐ **Basically, sharding by `user_id` will NOT work for group conversations. Either reads will be
> fan-out, or writes will be fan-out.**

*(Identical to the Slack analysis in Session 9.)*

---

## 🔑 Sharding Key Option 2 — `conversation_id`

> - **For groups,** `conversation_id = group_id`
> - **For 1-1 chats,** `conversation_id =` **a unique id assigned to a pair of users**

### 1-1 messages
| API | Shards hit |
|---|---|
| `getMessages(user_id, conversation_id, …)` | ⭐ **Only the conversation's shard** — because all messages sent/received by any participant of that conversation are in that shard |
| `sendMessage(sender_id, receiver_id, …)` | ⭐ **Go to the conversation's shard.** *What's the conversation id? It's just the pair `(sender_id, receiver_id)`* |
| `recentConversations(user_id)` | ⭐ **Will be FAN-OUT ⇒ bad** |

### The fix for `recentConversations` ⭐
> ⭐ **We can have a SEPARATE DB to store the most recent conversations. Note that now, the
> `sendMessage` must ALSO update the recentConversations DB.**
>
> ⭐ **Note: the recentConversations DB holds information (last message timestamp) about ALL
> conversations. It doesn't only store recent conversations. It's called the recentConversations DB
> because we're using it to answer the `recentConversations(...)` query exclusively.**

> 💡 **Same pattern as IRCTC (Session 9) and the leaderboard (Session 5): when one access pattern
> disagrees with your sharding key, give it its own database sharded its own way.**

### Group messages ✅
> **Note that a group is just a conversation amongst a lot of people.**

| API | Shards hit |
|---|---|
| `getMessages(user_id, group_id, …)` | ⭐ **just go to the group's shard** |
| `sendMessage(sender_id, group_id, …)` | ⭐ **just store in the group's shard** |
| `recentConversations(user_id)` | ⭐⭐ **No matter what you do, the moment a message is sent in a group, the most recent conversation gets updated for potentially 100,000 users! This will ALWAYS be a fan-out no matter what you do** |

**So what do you do?**
> ⭐⭐ **Therefore, you will NOT provision this API for group conversations.**
> **Practically: it happens only at the frontend:**
> - ⭐ **Client side app can maintain a cache of recent conversations**
> - ⭐ **This cache data is updated thanks to NOTIFICATIONS**

> 🧠 **A great instance of "the right answer is not to build it".** When an API is inherently
> fan-out, the move is to **not offer that API** and let the client derive the answer from a stream
> it's already receiving.

### The schema
```sql
users (id, name, age, avatar_url)

conversations (id, title, description)
conversation_participants (conversation_id, user_id)
messages (id, sender_id, conversation_id, message)
```

### ⭐ What to choose?
| Product | Sharding key | Why |
|---|---|---|
| ⭐ **Facebook Messenger / WhatsApp** | **`user_id`** | ⭐ **Group size is limited — sharding by `user_id` is ideal** |
| ⭐ **Slack / MS Teams** | **`conversation_id`** | ⭐ **Groups are a core feature, and groups can potentially get very large (100,000+ users) — sharding by `conversation_id` is ideal** |

### How do you shard a table that has no `user_id` column? ⭐
```
messages
id   sender_id   recipient_id   message
1    Jinesh      Anika          Hi
```
> **When we say that we're sharding by `user_id`, what does this mean? How do we shard this table by
> `user_id`, when it doesn't even have a `user_id` column?**
>
> ⭐ **You add one — and store the row TWICE:**
```
row_id   user_id   id   sender_id   recipient_id   message
123      Jinesh    1    Jinesh      Anika          Hi      → ⭐ goes to Jinesh's shard
321      Anika     1    Jinesh      Anika          Hi      → ⭐ goes to Anika's shard
```
**After sharding by `user_id`:**
```
Jinesh's shard:   123  Jinesh  1  Jinesh  Anika  Hi
Anika's shard:    321  Anika   1  Jinesh  Anika  Hi
```
> *(Session 9's rule in action: **every table must contain the sharding key column.**)*

---

## 🎭 The Illusion of Consistency

> **PACELC says if we want consistency, we have to give up on availability & latency. We DO want
> consistency.**
>
> **Assume that we're sharding by `user_id`. In this case, any write must go to 2 shards — sender &
> receiver. And we must maintain consistency during this write.**

### ❌ Option 1 — 2 Phase Commit
> **Use 2PC to write to both shards atomically:**
> - ⭐ **extremely slow (low throughput & high latency)**
> - ⭐ **low availability**

### ✅ Option 2 — write one at a time, in the right order

> ⭐⭐ **Can we instead create an ILLUSION of consistency? Instead of trying to write atomically,
> let's try to write 1 by 1.**

#### ❌ Write to the **Sender** shard first
```
Riya – "bro can I copy your project submission?" → Aditya
(sender)                                            (recipient)
```
> **1. Write the message to the Sender's shard:**
> - **Failure (low latency)** → immediately return a failure, and we're done. Client can retry
> - **Success** → ⭐ **At this point, can we return "success" to the sender? NO! Because the data has
>   not been written to the receiver shard yet.** This means that if the receiver tries to
>   `getMessages`, they will not see this message, **even though the sender believes the message has
>   been sent** → ⭐ **Inconsistency:**
>   > *Sender: "bro, I sent it"* · *Receiver: "bro, you didn't!"*
>
> **2. Write to the Receiver's shard:**
> - **Success (low latency)** → immediately return success ✅
> - ⭐ **Failure (high latency)** → **the data is in an INCONSISTENT state** (written to sender shard,
>   but not to receiver shard). **Right now the sender thinks the message has been sent, but if the
>   recipient loads their messages, they don't see it. This is extremely bad.** Options:
>   - **Retry** → ⭐ **the sender has to wait until the retry succeeds — very high latency**
>   - **Rollback** → we can return an error, **but now the system is in an inconsistent state until
>     the rollback completes**, so **we cannot let the sender make any reads until the rollback
>     completes — we've to acquire LOCKS** → ⭐ **reads for the sender will have high latency**

#### ✅ Write to the **Receiver** shard first ⭐⭐
> **1. Write to the Recipient's shard:**
> - **Failure (low latency)** → **immediately return a failure.** Client (sender) can retry
> - **Success** → ⭐⭐ **the message has ACTUALLY been sent! At this point, if the recipient fetches
>   their messages, they will be able to see this new message.** ⭐ **Immediately return a success
>   (without even writing to the sender shard) — very low latency**
>
> **2. (async) Write to the Sender's shard:**
> - **Success** → great, we're done
> - **Fails** → ⭐ **just keep retrying until it succeeds. The sender isn't waiting — they've already
>   received an acknowledgement. So no added latency here**

```
   ⭐⭐ THE KEY ASYMMETRY:

   The RECIPIENT is the one who must not miss the message  →  write there FIRST, synchronously
   The SENDER already knows what they sent                 →  write there LATER, asynchronously
```

### The remaining hole, and its fix ⭐
> **Note that if the initial write to the Recipient's shard succeeds, but the write to the Sender's
> shard fails — when the sender reloads their app, they will not see the message they just sent.
> This means the sender thinks their message has been deleted ⇒ bad!**
>
> ⭐⭐ **We can fix this by simply having a FRONTEND CACHE (a cache inside the client app).**
> **The app will know what messages have been sent. Even though the `getMessages` API doesn't show
> this message, the frontend app will know that this message was sent and acknowledged by the
> server.**
>
> ⭐ **The only situation when this will be an issue is when: the sender sends a message, the sender's
> shard is misbehaving in the backend, the sender reinstalls their frontend app (or clears the app
> cache), and then tries to see the message. This is very very rare, so not an issue.**
>
> ⭐ **Note the message has NOT been lost. Eventually the sender shard will come back up, and the
> message will be replicated there from the receiver shard.**

> ⭐⭐ **By cleverly writing to the recipient's shard first, and utilizing the frontend cache at the
> sender side, we can create an ILLUSION of immediate consistency. It solves the practical problem
> for us.**

### Consistency vs Availability — under a partition ⭐
> **Imagine that there's a partition:**
```
Harini ----- "Hi" -----> Srinidhi
```
> - **App Server 1 receives this request**
> - **App server 1 is able to communicate with Srinidhi's shard, but because of a n/w partition, it
>   is NOT able to communicate with Harini's shard**
>
> ⭐ **App server will just write to Srinidhi's shard (recipient), and return success to Harini. It
> will also drop a message in a TASK QUEUE to add this message to Harini's shard asynchronously.**
>
> - ⭐ **Even in case of n/w partition, `sendMessage` & `getMessages` remain available ⇒ HIGH
>   AVAILABILITY**
> - ⭐ **Srinidhi can see the message because it is written to her shard. And because of the frontend
>   cache, Harini can also see the message ⇒ (illusion of) IMMEDIATE CONSISTENCY**
>
> **Note: if the write to Srinidhi's shard fails, then we can return an error to Harini and they can
> retry.**

### Consistency vs Latency
> ⭐ **Because we're not actually trying to write to both shards in an atomic manner, we don't have to
> wait for retry/rollback to complete. We can just return success the moment we write to the
> recipient shard ⇒ LOW LATENCY.**

> 🧠 **What actually happened here:** the system is genuinely only **eventually consistent** — but the
> **only two observers** are the sender (who has a local cache) and the recipient (who was written to
> first). Since **nobody is in a position to observe the staleness**, the illusion is complete. This
> is engineering around a theorem rather than fighting it.

---

## 🗄️ Choosing the Right Database

```
Writes (sendMessage): 400,000 / second avg (peak: 2 million / sec)
Reads  (getMessages): 800,000 / second avg (peak: 4 million / sec)
⭐ Both Read & Write Heavy!    ⭐ No database is optimized for both!
```

### Optimizing reads/writes
| Can we optimize **writes**? | |
|---|---|
| **Batching** | ⭐ causes stale reads — **but we want low latency** ❌ |
| **Sampling** | ⭐ causes potential data loss — **we cannot afford data loss** ❌ |

| Can we optimize **reads**? | |
|---|---|
| ⭐ **Yes** | **Just try to absorb as many reads as possible via a cache** |

> ⭐ **Now that we're absorbing the majority of reads in the cache, we can optimize our database for
> WRITES!**

### The requirements for the ideal database
> - ⭐ **High write throughput** (400,000 writes/sec avg)
> - ⭐ **No need of joins**
>   - **No:** *find all messages of all friends of Akshay*
>   - **Yes:** *find all messages of Akshay (filter: within a conversation)*
> - **No need of search** *(if we need it later, we can provision another database in a separate
>   microservice)*
> - ⭐⭐ **Paginated reads (by timestamp)**
> - **No need of transactions**
> - **We want disk persistence**

### Evaluating the options ⭐
| Database type | Strengths | Weaknesses | Verdict |
|---|---|---|---|
| **SQL** | ACID transactions, normalization, joins, schema | ⭐ **low throughput, can't scale horizontally** | ❌ |
| **Key-Value** | **High throughput, simplicity** | **No search, No joins,** ⭐ **No pagination** | ❌ **We need pagination!** |
| **Document** | **Schemaless, search, (local) index on any attribute** | **No joins,** ⭐ **No pagination** | ❌ **We do need pagination. We don't need search** |
| ⭐ **Column-Family DB** | ⭐ **Fast writes, TIME-BASED PAGINATION, fast aggregate queries** | No joins, no search | ✅ ⭐⭐ **This is exactly what we need!** |

> ⭐⭐ **Ideal database is therefore a WIDE COLUMN DATABASE — HBase / Cassandra / ScyllaDB.**

> 💡 **Note how "pagination" — a humble-sounding requirement — is what actually eliminates key-value
> and document stores.** This is why you enumerate requirements *before* picking technology.
> *(And per Session 5: in an interview say "wide column database", not "Cassandra".)*

---

## 💾 Cache Design

Following the **5-step cache design process** (Session 5):

### Local vs Global (Single) vs Global (Distributed)
> **Should we go with a Single, global cache?**
> ⭐ **No! We need lots of cache, so we need something distributed (local/global).**
>
> **Do we need to transfer lots of data between app server & cache server to handle a read request?
> Is the n/w overhead going to be an issue for every call?** *(`getMessages(user_id,
> conversation_id, pagination)`)*
> ⭐ **No. In a given call, I'm only reading a few messages. Low n/w overhead.**
>
> **We should probably think of a Global Cache. Will a single cache server be able to handle all the
> data?** **No. We're looking at a distributed global cache.**

### But then… ⭐⭐
> **But in this case, what is the app server for the `getMessages` API doing?**
> ⭐ **Nothing — just passing the request forward to the cache server.**
>
> - ⭐⭐ **If we go with a global cache, we now have 2× the number of servers (app servers + cache
>   servers), and half of them are not doing anything!**
> - ⭐⭐ **If we go with a global cache, getting READ-YOUR-WRITE consistency will be hard! In a local
>   cache it will be very simple (because local writes will succeed)**
>
> ⭐⭐ **So instead of having a global cache and then having useless app servers, we can simply use a
> LOCAL cache. App servers now double as the cache.**

> 🧠 **A lovely piece of reasoning.** The usual instinct is "global cache = good, keeps app servers
> stateless". But here the app server has **no work of its own** — so a separate cache tier is pure
> waste. Collapsing the two tiers halves the fleet *and* makes strong consistency easy.

### Invalidation
> - **We want immediate consistency, but we don't want the latency that comes with immediate
>   consistency**
> - **If we have a separate app server & cache server, immediate consistency requires 2 phase commit**
>   (because we have to keep the cache & db up to date — 2 places)
> - ⭐ **If we have a local cache, then writing to the cache is ALWAYS successful. No need of 2PC here**
>
> ⭐⭐ **Because of the local cache, we can get WRITE-THROUGH invalidation (immediate consistency)
> without high latency.**

*(Precisely the Session-4 rule: *"if the cache is local, you will ALWAYS use write through — no
latency issues, no 2PC required."*)*

### Eviction
> ⭐ **LRU eviction.**

### Routing ⭐
> ⭐ **Our app servers are STATEFUL. If an app server holds Harini's messages in cache, we want
> Harini's requests to ALWAYS go to that app server ⇒ CONSISTENT HASHING.**
>
> - **`getMessages(user_id, conversation_id)`** ⇒ ⭐ **this request just goes to my shard & to my
>   app-server+cache, because all my messages are contained there**
> - **`sendMessages(sender_id, recipient_id)`** ⇒ ⭐ **this request will be routed to the recipient
>   shard & app-server+cache first (via the routing) and the data will be written there. (Async) via
>   a message queue, we will replicate this data in the sender shard & app-server+cache**

*(Session 3's rule: a **local cache makes app servers stateful, which means the application LB must
use consistent hashing.**)*

### What happens if a cache server crashes?
> - **The users originally going to this server have to be redirected to another server. This other
>   server doesn't have their messages cached**
> - ⭐ **COLD CACHE problem — data not in cache, fetch it from DB**
> - ⭐ **Some of the time (when the cache server crashes), some of the users (only those that were
>   originally going to the now-crashed server) will see a larger latency for the first few reads.
>   That is perfectly okay.**

---

## 🖼️ The Final Design

```
                 ┌──────────────────────────────────────────────────────┐
   Client         │  ⭐ generates UUID v7 (idempotency key)              │
   (mobile)       │  ⭐ carries previous_message_id  (ordering chain)    │
                  │  ⭐ FRONTEND CACHE (sender's illusion of consistency)│
                  └───────────────────────┬──────────────────────────────┘
                                          │ sendMessage / getMessages
                                          ▼
                            ┌─────────────────────────────┐
                            │  LB — ⭐ CONSISTENT HASHING  │  (app servers are stateful)
                            └──────────┬──────────────────┘
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │ App Server 1      │ │ App Server 2      │ │ App Server 3      │
        │ ⭐ + LOCAL CACHE   │ │ + LOCAL CACHE     │ │ + LOCAL CACHE     │
        │   (write-through, │ │                   │ │                   │
        │    LRU)           │ │                   │ │                   │
        └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                  ▼                     ▼                     ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  ⭐ WIDE COLUMN DB (Cassandra/HBase/ScyllaDB) — write-optimised│
        │  sharded by user_id (WhatsApp/Messenger) or                   │
        │            conversation_id (Slack/Teams)                      │
        └──────────────────────────────────────────────────────────────┘
                  │                                    ▲
                  │  ⭐ write RECIPIENT shard first (sync)│
                  └──▶ ⭐ TASK QUEUE ──▶ sender shard (async, retry forever)

        ┌──────────────────────────────────┐
        │ recentConversations DB           │  ⭐ separate DB, own sharding
        │ (1-1 only; groups → client side) │
        └──────────────────────────────────┘
```

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **NFR / Design goal** | ⭐ A constraint on behaviour, **not** a feature you expose |
| **Message order** | ⭐⭐ Messages must appear in the order the **sender** sent them — meaning depends on order |
| ⭐ **Idempotent** | ⭐⭐ `f(x) = f(f(x))` — repeating the operation changes nothing more |
| **Why idempotency** | ⭐ Frontend **auto-retries** + a **lost ACK** ⇒ duplicate writes |
| **Idempotency rule** | ⭐ Store only if the `message_id` is new; **return SUCCESS on a duplicate** so retries stop |
| **UUID v7** | ⭐ Universally unique, **decentralized (client-generated)**, sparse, **roughly sortable**, 128-bit |
| **Retry vs intent** | ⭐ Dedupe **retries**, but allow the user to deliberately send "Hi" 20 times |
| **Read-your-write consistency** | The author immediately sees their own write |
| **Message chain** | ⭐⭐ Each message carries `previous_message_id`; the client **holds** a message until its predecessor arrives |
| **Why timestamps fail** | ⭐ Nobody — client *or* server — **knows a message is missing** until it arrives |
| **Per-sender ordering** | ⭐ We guarantee order **within one sender**, not across senders |
| **conversation_id** | ⭐ Unifies 1:1, group and ad-hoc chats into one model |
| **Sharding: user_id** | ✅ 1-1 (all APIs single-shard) · ❌ **groups fan out on reads or writes** |
| **Sharding: conversation_id** | ✅ groups · ❌ `recentConversations` fans out → **separate DB** |
| ⭐ **The product choice** | **WhatsApp/Messenger → `user_id`** (small groups); **Slack/Teams → `conversation_id`** (huge groups) |
| **Not provisioning an API** | ⭐ Group `recentConversations` is inherently fan-out ⇒ **do it client-side via notifications** |
| ⭐ **Recipient-first write** | ⭐⭐ Write the **recipient's** shard synchronously, the sender's **async** |
| ⭐ **Illusion of consistency** | ⭐⭐ Recipient-first write + **frontend cache** ⇒ appears immediately consistent while being eventually consistent |
| **Task queue** | Carries the async replication to the sender's shard; retries forever |
| **Wide column DB** | ⭐⭐ Fast writes + **time-based pagination** ⇒ Cassandra / HBase / ScyllaDB |
| **Why not KV/Document** | ⭐ **No pagination** |
| ⭐ **App server = cache** | ⭐⭐ A global cache would leave app servers doing nothing and make read-your-write hard ⇒ use a **local** cache |
| **Cold cache** | ⭐ After a cache server dies, its users see slow first reads — acceptable |

---

## 🎯 Session Takeaways

1. ⭐ **Communication needs strong consistency** — this system can afford **neither stale reads nor
   data loss**, which removes batching and sampling from the toolbox.
2. ⭐ **DAU is ~80%, not 20%,** for WhatsApp-style apps — Pareto doesn't apply to messaging.
   **40 billion messages/day ⇒ 400K/sec avg, 2M/sec peak, 200 PB over 20 years.**
3. ⭐⭐ **Both read- AND write-heavy with neither dominating** — the hardest shape. The only escape is
   **absorb reads in cache and write-optimise the DB** (messages are near-immutable, so caching works).
4. ⭐ **Frontend auto-retries + a lost ACK = duplicates.** Fix with a **client-generated UUID v7** and
   an idempotent write that **returns success on duplicates**.
5. ⭐ **Dedupe retries, not intent** — 20 deliberate "Hi"s get 20 different UUIDs.
6. ⭐⭐ **Ordering cannot be solved on the backend** — nobody knows a message is missing until it
   arrives. Use a **message chain** (`previous_message_id`) and hold messages on the **client**.
7. ⭐ **Only per-sender order is guaranteed.** Interleaving across senders is fine and nobody notices.
8. ⭐ **Unify 1:1, group and ad-hoc chats behind `conversation_id`** instead of a table per shape.
9. ⭐⭐ **The sharding key depends on the product:** `user_id` for WhatsApp/Messenger (small groups),
   `conversation_id` for Slack/Teams (100,000-member channels).
10. ⭐ **When an API is inherently fan-out, don't provision it** — group `recentConversations` lives on
    the client, fed by notifications.
11. ⭐⭐ **The headline trick: write the RECIPIENT's shard first and synchronously; replicate to the
    sender asynchronously.** Combined with a **frontend cache**, this creates an **illusion of
    immediate consistency** with low latency and high availability — engineering *around* PACELC
    rather than against it.
12. ⭐⭐ **Pagination is what selects the database:** KV and document stores can't paginate, so the
    answer is a **wide column store** (Cassandra/HBase/ScyllaDB).
13. ⭐⭐ **Make the app servers the cache.** A separate global cache tier would double the fleet, leave
    app servers idle, and make read-your-write hard — while a **local** cache gives free
    **write-through** consistency (no 2PC) at the cost of statefulness ⇒ **consistent hashing**.

---

## ➡️ Next
**[Session 15 — Types of NoSQL Databases](./15_Types_of_NoSQL_Databases.md)**
