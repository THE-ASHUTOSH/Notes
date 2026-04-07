# 🧍 Singleton Design Pattern

**Date:** August 29, 2025

## 🎯 Intent
Ensure exactly **one instance** of a class exists and provide a **global access point** to it.

## 💡 Use Cases
- Logging service 📝
- Configuration manager ⚙️
- Feature flag provider 🚩
- Connection pool manager 🔌
- Metrics reporter 📊

---

## 🏗️ Step-by-Step Evolution of Singleton

### Step 1: Restricting Object Creation
❓ **Question:** How can we stop others from creating multiple objects?
💡 **Answer:** By making the constructor `private`.

```java
public class Logger {
    private Logger() {}
}
```
*Reflection:* This prevents external instantiation, but then how do we create an object?

### Step 2: Providing a Single Instance (Eager Initialization)
❓ **Question:** If only the class can call the private constructor, how do we give others access?
💡 **Answer:** By holding a single instance inside the class and exposing it via a static method.

```java
public class Logger {
    private static final Logger INSTANCE = new Logger();
    
    private Logger() {}
    
    public static Logger getInstance() {
        return INSTANCE;
    }
}
```
⚠️ **Problem:** This is *eager initialization*. The instance is created even if it is never used, which wastes memory.

### Step 3: Lazy Loading
❓ **Question:** How to create the instance only when needed?
💡 **Answer:** Initialize it inside the accessor method.

```java
public class Logger {
    private static Logger instance;
    
    private Logger() {}
    
    public static Logger getInstance() {
        if (instance == null) {
            instance = new Logger();
        }
        return instance;
    }
}
```
⚠️ **Problem:** *Not thread-safe*. Two threads calling `getInstance()` simultaneously could create two separate objects.

### Step 4: Synchronization
❓ **Question:** How to stop multiple threads from creating two objects?
💡 **Answer:** Synchronize the accessor method.

```java
public class Logger {
    private static Logger instance;
    
    private Logger() {}
    
    public static synchronized Logger getInstance() {
        if (instance == null) {
            instance = new Logger();
        }
        return instance;
    }
}
```
⚠️ **Problem:** Correct, but synchronization is expensive and slows down *every* call to `getInstance()`.

### Step 5: Double-Checked Locking (DCL)
❓ **Question:** Can we reduce synchronization overhead?
💡 **Answer:** Yes, use double-checked locking to synchronize only during initialization.

```java
public class Logger {
    private static Logger instance;
    
    private Logger() {}
    
    public static Logger getInstance() {
        if (instance == null) { // First check
            synchronized (Logger.class) {
                if (instance == null) { // Second check
                    instance = new Logger();
                }
            }
        }
        return instance;
    }
}
```

#### Step 5a: The Role of `volatile`
❓ **Question:** Why is this code still unsafe without `volatile`?
💡 **Answer:** Because of two issues:
1. **Instruction reordering:** Object creation is not atomic. It consists of:
   - (a) Allocate memory.
   - (b) Initialize the object.
   - (c) Assign reference to the variable.
   Without `volatile`, steps (b) and (c) can be reordered. Another thread might see a non-null reference to a half-constructed object.
2. **Caching and visibility:** Without `volatile`, one thread may update its CPU cache with the new object reference, while other threads still see `null`.

✅ **Solution:** Declare the instance as `volatile`. This ensures:
- **Visibility:** All writes are immediately visible to other threads.
- **Ordering:** A “happens-before” relationship guarantees object construction completes before reference assignment.

```java
public class Logger {
    private static volatile Logger instance;
    
    private Logger() {}
    
    public static Logger getInstance() {
        if (instance == null) {
            synchronized (Logger.class) {
                if (instance == null) {
                    instance = new Logger();
                }
            }
        }
        return instance;
    }
}
```
*Note:* This is correct since Java 5, but it is verbose and harder to read.

### Step 6: Static Inner Class (Holder Idiom)
❓ **Question:** Is there a simpler way to get lazy loading and thread safety without `volatile`?
💡 **Answer:** Yes, the **Holder idiom**.

```java
public class Logger {
    private Logger() {}
    
    private static class Holder {
        private static final Logger INSTANCE = new Logger();
    }
    
    public static Logger getInstance() {
        return Holder.INSTANCE;
    }
}
```
🌟 **Benefit:** Lazy, thread-safe, clean, and no synchronization needed. Relies on JVM classloading guarantees.

🔒 **How it works:** Class initialization happens only once and is inherently synchronized by the JVM. Therefore, when the JVM loads the `Holder` class, it guarantees that the `INSTANCE` will be created atomically before any thread can access it, removing the need for manual synchronization blocks.

### Step 7: Enum Singleton
❓ **Question:** Is there a way to resist reflection and serialization attacks?
💡 **Answer:** Yes, use an `enum`.

```java
public enum Logger {
    INSTANCE;
    
    public void log(String msg) {
        System.out.println(msg);
    }
}
```
🌟 **Benefit:** Simplest and safest form of Singleton. 
⚠️ **Limitation:** No lazy initialization, cannot subclass.

---

## 🛡️ Special Concerns

- 📦 **Serialization:** Regular singletons require `readResolve()`; enums are safe by default.
- 🪞 **Reflection:** Can break private constructors; enums resist this.
- 🧪 **Testing:** Singletons are hard to mock; prefer dependency injection if testability matters.

---

## 📌 Quick Recap

- **Private constructor** restricts instantiation.
- **Eager init:** Simple but wastes memory.
- **Lazy init:** Saves memory, but not thread-safe.
- **Synchronization:** Safe, but slow.
- **DCL without `volatile`:** Broken due to instruction reordering and caching.
- **DCL with `volatile`:** Safe and efficient since Java 5.
- **Holder idiom:** Cleanest balance of lazy + safe.
- **Enum:** Safest overall, reflection/serialization proof.

---

## 🧠 Frequently Asked Interview Questions

1. How to make a class Singleton?
2. What problem does eager initialization cause?
3. How does lazy initialization solve this, and what problem does it introduce?
4. What is Double Check Locking? How to achieve it?
5. What two problems arise without `volatile` in double-checked locking?
6. Which Singleton approach is the safest overall, and why?
