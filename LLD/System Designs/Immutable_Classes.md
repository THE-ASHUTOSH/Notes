# 🔒 Immutable Classes in Java
**(Thread-Safe, Unchanging State)**

## 🎯 Context
**Intent:** Objects whose state cannot change after construction.
**Use cases:** Payment receipts, order snapshots, currency/money values, configuration objects, DTOs shared across threads.

---

## 1️⃣ Step 1: Why Immutability?

### ❓ Why do we want immutable objects?
**Answer:** They are inherently thread-safe, easy to reason about, and prevent accidental changes.

---

## 2️⃣ Step 2: First Attempt — Simple Immutable Class

### ❓ How can we make a class immutable?
**Answer:**
- Make fields `private` and `final`.
- Provide values via constructor.
- Do not provide setters.

```java
import java.time.Instant;

public final class PaymentReceipt {
    private final String id;
    private final double amount;
    private final Instant timestamp;

    public PaymentReceipt(String id, double amount, Instant timestamp) {
        if (id == null || id.isBlank()) throw new IllegalArgumentException("id required");
        this.id = id;
        this.amount = amount;
        this.timestamp = timestamp;
    }

    public String getId() { return id; }
    public double getAmount() { return amount; }
    public Instant getTimestamp() { return timestamp; }
}
```

**Reflection:**
- This works perfectly for scalar and already-immutable types.
- But what if a field is a mutable collection?

---

## 3️⃣ Step 3: The Mutable Field Problem

### ❓ What happens if our immutable class contains a `List`?
**Answer:** Callers could modify the list outside, causing the supposedly immutable object to change indirectly!

```java
public final class Order {
    private final List<String> items;

    public Order(List<String> items) {
        this.items = items; // ❌ Dangerous!
    }

    public List<String> getItems() { return items; }
}
```

**Problem:** A caller could do:
```java
List<String> list = new ArrayList<>();
list.add("Laptop");

Order order = new Order(list);
list.add("Phone"); // ⚠️ Mutates Order indirectly!
```

---

## 4️⃣ Step 4: Defensive Copying

### ❓ How do we prevent external mutation of internal state?
**Answer:** Make a **defensive copy** in the constructor and return **unmodifiable views** in getters.

```java
import java.util.*;

public final class Order {
    private final List<String> items;

    public Order(List<String> items) {
        this.items = List.copyOf(items); // ✅ Defensive copy
    }

    public List<String> getItems() {
        return Collections.unmodifiableList(items); // ✅ Safe view
    }
}
```

**Reflection:** Now outside changes to the original list do not affect our object.

---

## 5️⃣ Step 5: Inheritance Risks

### ❓ Can subclasses break immutability?
**Answer:** Yes, a subclass could add setters or expose mutable state.
**Solution:** Mark the class `final` or hide the constructors by making them private (e.g., using a Builder or Factory Method).

---

## 6️⃣ Step 6: Thread-Safety and Performance

### ❓ Do immutable objects need synchronization?
**Answer:** No. Since they never change, they can be safely shared across threads without locks. 
**Extra benefit:** They work exceptionally well as keys in hash-based collections (like `HashMap` or `HashSet`).

---

## 🌟 Complete Example: GameConfig

```java
import java.util.*;

public final class GameConfig {
    private final String name;
    private final List<String> rules;

    public GameConfig(String name, List<String> rules) {
        this.name = Objects.requireNonNull(name);
        this.rules = List.copyOf(rules); // defensive copy
    }

    public String getName() { return name; }

    public List<String> getRules() {
        return Collections.unmodifiableList(rules);
    }

    @Override
    public String toString() {
        return name + " with rules " + rules;
    }
}
```

**Result:** Immutable, thread-safe, no surprises.

---

## ✨ Quick Recap

- 🛠️ Use `private final` fields and constructor injection.
- 🚫 **Do not provide setters.**
- 🛡️ Make **defensive copies** of mutable inputs in constructors.
- 👀 Return **unmodifiable views** in getters.
- 🛑 Mark the class `final` to prevent subclassing.
- 🧵 Immutable objects are inherently **thread-safe**.

---

## 🎤 Practice Questions

1. **Why should immutable classes make defensive copies of mutable fields?**
2. **How does immutability improve thread-safety?**
3. **Why is marking the class `final` recommended?**
4. **What is the difference between returning a defensive copy and an unmodifiable view?**
5. **Give two real-world use cases where immutability is essential.**
