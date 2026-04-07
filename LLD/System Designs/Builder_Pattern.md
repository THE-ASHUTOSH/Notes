# 🏗️ Builder Pattern
**(Constructing Complex Objects Step-by-Step)**

## 🎯 Context
**Intent:** Simplify the creation of complex immutable objects by separating construction from representation.
**Use cases:** Classes with many parameters (some optional), configuration objects, constructing immutable aggregates.

---

## 1️⃣ Step 1: The Problem — Telescoping Constructors

### ❓ What pain are we feeling? (Socratic prompts)
- **Question:** What happens if a class has many fields (e.g., 8–10)? 
- **Answer:** We either need one huge constructor or many overloaded constructors (telescoping constructors).

```java
public class Order {
    private final String customerId;
    private final int priority;
    private final boolean giftWrap;
    private final boolean expressDelivery;

    // Telescoping constructor
    public Order(String customerId, int priority, boolean giftWrap, boolean expressDelivery) {
        this.customerId = customerId;
        this.priority = priority;
        this.giftWrap = giftWrap;
        this.expressDelivery = expressDelivery;
    }
}
```
**Problem:** Hard to read, hard to maintain, and confusing for callers.

---

## 2️⃣ Step 2: The Idea of Builder

### ❓ How can we make object creation clearer?
**Answer:** Use a separate Builder that sets fields step by step, then calls `build()`.

```java
public class Order {
    private final String customerId;
    private final int priority;
    private final boolean giftWrap;
    private final boolean expressDelivery;

    private Order(Builder b) {
        this.customerId = b.customerId;
        this.priority = b.priority;
        this.giftWrap = b.giftWrap;
        this.expressDelivery = b.expressDelivery;
    }

    public static class Builder {
        private String customerId;
        private int priority = 1; // default
        private boolean giftWrap = false;
        private boolean expressDelivery = false;

        public Builder customerId(String id) { this.customerId = id; return this; }
        public Builder priority(int p) { this.priority = p; return this; }
        public Builder giftWrap(boolean g) { this.giftWrap = g; return this; }
        public Builder expressDelivery(boolean e) { this.expressDelivery = e; return this; }

        public Order build() {
            if (customerId == null) throw new IllegalStateException("customerId required");
            return new Order(this);
        }
    }
}
```

**Usage:**
```java
Order order = new Order.Builder()
    .customerId("C101")
    .priority(2)
    .giftWrap(true)
    .build();
```

---

## 3️⃣ Step 3: Enforcing Required Fields

### ❓ How do we ensure mandatory fields are set?
**Answer:** Validate in `build()`, or require them in the Builder’s constructor.

```java
public static class Builder {
    private final String customerId; // required
    private int priority = 1;
    private boolean giftWrap = false;

    public Builder(String customerId) {
        this.customerId = Objects.requireNonNull(customerId);
    }

    public Builder priority(int p) { this.priority = p; return this; }
    public Builder giftWrap(boolean g) { this.giftWrap = g; return this; }

    public Order build() {
        return new Order(this);
    }
}
```

---

## 4️⃣ Step 4: Complex Example — GameConfig

### ❓ What if we have a collection of rules and want to add them step by step?
**Answer:** Builder can accumulate them and build an immutable object.

```java
import java.util.*;

public final class GameConfig {
    private final String name;
    private final List<String> rules;

    private GameConfig(Builder b) {
        this.name = b.name;
        this.rules = List.copyOf(b.rules); // defensive copy
    }

    public static class Builder {
        private String name;
        private List<String> rules = new ArrayList<>();

        public Builder name(String n) { this.name = n; return this; }
        public Builder addRule(String r) { this.rules.add(r); return this; }
        public Builder addAllRules(List<String> rs) { this.rules.addAll(rs); return this; }

        public GameConfig build() {
            if (name == null) throw new IllegalStateException("Name required");
            return new GameConfig(this);
        }
    }
}
```

**Usage:**
```java
GameConfig config = new GameConfig.Builder()
    .name("Battle Royale")
    .addRule("No cheating")
    .addRule("Time limit: 10 min")
    .build();
```

---

## 5️⃣ Step 5: Practical Considerations

- 🏗️ Builders work best for **immutable classes**.
- 🛠️ Defaults can be set directly in the Builder.
- ✅ Validation should happen in `build()`.
- 🔄 Copy-builder or `toBuilder()` can simplify modifications.
- 🪄 Libraries like **Lombok** can auto-generate builders, but may hide validation logic.

---

## ✨ Quick Recap

- ❌ **Telescoping constructors** are unreadable.
- 🏗️ **Builder** separates construction from representation.
- 🔗 **Fluent setters** improve readability.
- 🛡️ Enforce **required fields** via Builder constructor or validation.
- 🔒 Use **defensive copies** for collections to preserve immutability.

---

## 🎤 Frequently Asked Interview Questions

1. **What problem does the Builder pattern solve?**
2. **How can required fields be enforced in a Builder?**
3. **Why is Builder often used with immutable objects?**
4. **Compare Builder with telescoping constructors in readability.**
