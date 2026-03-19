# 🛡️ PROXY DESIGN PATTERN — Controlled Access and Lazy Loading

## 🔴 1. Problem Statement (Motivating Scenario)

***Context:*** We have an `ITextParser` interface with methods such as `getWordCount()`, `getSentenceCount()`, `searchWord(word)`. 
The concrete implementation `BookParser` takes a book (string) in its constructor and immediately performs heavy work:
- Parsing the entire text 📖
- POS tagging 🏷️
- Storing structures in vectors and XML trees 🌳

This constructor is **very expensive**.

***The Client Issue:***
- **Client1** depends on an `ITextParser`, injected via its constructor, but only uses some of its methods.
- **Client2** needs to use Client1. However, even if Client2 *never* calls the methods that rely on the parser, the `BookParser` is still eagerly constructed during Client1’s creation. This wastes time, resources, and causes unnecessary blocking! ⏳

---

## 🚫 2. Naïve Alternative: Manual Lazy Loading in Client

One idea is to avoid constructing the parser in Client1’s constructor and defer it until the first method call:

```java
class Client1 {
    private ITextParser parser;
    private final String book;
    
    public Client1(String book) {
        this.book = book;
        this.parser = null;
    }
    
    public int getWordCount() {
        if (parser == null) parser = new BookParser(book); // heavy call
        return parser.getWordCount();
    }
}
```

**Why this is not good:**
- **Violates SRP:** Client1 now does its own logic + manages lifecycle of the parser.
- **Violates OCP:** Every new parser-using method must repeat the "if null then create" logic.
- **Violates DIP:** The client is tied to the `BookParser` constructor.
- **Encapsulation leak:** Client code is burdened with decisions about when to construct dependencies.

---

## 💡 3. Proxy as the Solution

Instead of pushing lazy loading into the client, we introduce a **Proxy object** that implements the same `ITextParser` interface.
- The proxy stores the book text but does **not** create the heavy `BookParser` immediately.
- On the first actual method call, the proxy constructs the real `BookParser` and delegates.
- All subsequent calls go directly to the cached real parser.

```java
// Subject
interface ITextParser {
    int getWordCount();
    boolean searchWord(String w);
}

// RealSubject (heavy)
class BookParser implements ITextParser {
    public BookParser(String book) {
        System.out.println("Heavy BookParser initialized");
        // heavy parsing...
    }
    public int getWordCount() { return 1000; }
    public boolean searchWord(String w) { return true; }
}

// Proxy (Virtual Proxy for Lazy Loading)
class LazyBookParserProxy implements ITextParser {
    private final String book;
    private BookParser realParser;
    
    public LazyBookParserProxy(String book) {
        this.book = book;
        this.realParser = null;
    }
    
    private BookParser getReal() {
        if (realParser == null) {
            realParser = new BookParser(book); // construct only on demand
        }
        return realParser;
    }
    
    @Override
    public int getWordCount() { return getReal().getWordCount(); }
    
    @Override
    public boolean searchWord(String w) { return getReal().searchWord(w); }
}
```

**Benefits:**
- **Clients stay clean:** Client1 just uses `ITextParser`, unaware of lazy loading.
- **Lazy loading guaranteed:** Parser only constructed if needed.
- **Preserves SOLID:** SRP, OCP, and DIP are maintained cleanly.

---

## 🎯 4. Proxy Use-Cases

Sometimes we need to work with objects that are **expensive, remote, or sensitive**:
- 🖼️ A large image that should only be loaded when displayed.
- 🌐 A remote service call to another server or microservice.
- 🔒 A document object where only certain users may edit.
- 🧵 An object that must be reference-counted or locked before use.

**Proxy intuition:** Introduce a stand-in object with the same interface as the real subject. The proxy decides when/how to forward calls, adding control, laziness, or optimizations.

---

## ⚖️ 5. Forces and Goals
- **Transparency:** Clients see the same interface.
- **Indirection:** Proxy controls access, defers creation, or redirects boundaries.
- **Extensibility:** Easy to add different policies without changing clients.

---

## 🧠 6. Proxy: Core Idea and Intuition

**Definition:** Provide a surrogate or placeholder for another object to control access to it.

🧩 **Participants:**
1. **Subject:** Common interface (e.g., `Graphic`).
2. **RealSubject:** The real object (e.g., `Image`).
3. **Proxy:** Holds reference to RealSubject, implements Subject, and controls access.

📌 **Types of proxies:**
- **Remote Proxy:** Represents an object in another address space.
- **Virtual Proxy:** Creates expensive objects lazily, may cache state.
- **Protection Proxy:** Checks access rights before forwarding.
- **Smart Reference:** Adds housekeeping (ref-counting, locking, loading).

---

## ✅ 7. Consequences & Doubts

**Benefits:**
- Control access, add optimizations (lazy load, caching).
- Maintain identical interface to RealSubject.
- Hide distribution or reference counting from the client.

**Liabilities:**
- Adds indirection (extra call overhead).
- Must preserve semantics (don't surprise clients).

❓ **Doubt: Is Proxy the same as Decorator?**
- **No.** Decorator adds new behavior/responsibilities. Proxy *controls access* or optimizes interaction with the real subject.

❓ **Doubt: Couldn’t I just use Adapter?**
- **No.** Adapter changes the interface. Proxy keeps the *same interface* but inserts control logic.

---

## 🗺️ 8. Mapping to SOLID
- **SRP:** Proxy focuses on access control/lazy init; RealSubject focuses on core logic.
- **OCP:** New policies = new proxy classes; no need to change RealSubject.
- **LSP:** Proxy and RealSubject share Subject interface.
- **DIP:** Clients depend on Subject abstraction.

---

## ✨ Personal Touch

### 🎯 Takeaway & Summary

❓ **Question:** You have a massive, heavy asset (like an Image or a Document Parser) that drastically slows down initialization if loaded eagerly. You don't want to pollute your client codebase with endless `if (object == null)` checks. How do you manage this cleanly?

💡 **Solution:** Proxy inserts a level of indirection to control access to the real object. By wrapping the heavy object in a **Virtual Proxy**, you defer the expensive loading until the exact moment a method is *actually* called. It’s fundamental for lazy loading, distributed systems, security, and memory optimization! 🌟
