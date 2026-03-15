# Prototype Pattern (with Registry)
**Vector Graphics / Diagramming Editor**

## Context
You are building a vector graphics editor (or diagramming tool) with a palette of tools: Rectangle, Ellipse, TextBox, Arrow, etc. Each shape comes with style, constraints, and sometimes nested parts. Constructing a fully wired shape from scratch can be costly. Users pick a tool and place many instances of the same kind of shape.

---

## 1 Part A — Why Prototype?

### 1) What pains are we feeling?
- Are shape constructors doing heavy, repetitive work (loading styles, adding handles, attaching constraints)?
- Do we want to create new shapes by example, not by knowing their concrete class names?
- Can the set of shapes change at runtime (plugins, feature flags), so hard-coding constructors is brittle?

### 2) What properties do we desire?
- On click, the palette should produce a fresh shape by **copying a prototypical instance**.
- Creation should be fast and decoupled from concrete types.
- We should be able to **add, remove, or reconfigure available shapes without touching client code**.

### 3) Insight
Keep one configured exemplar per shape type. To create a new instance, clone the exemplar. Keep those exemplars in a **registry** (a small in-memory catalog) so tools and frameworks can request clones by key.

---

## 2 Part B — Solution: Prototype + Registry (Shapes)

### 1) Roles
- **Prototype** (`Shape`) exposes `copy()` (or `clone()`) to duplicate itself.
- **Concrete Prototypes** (`Rectangle`, `Ellipse`, `TextBox`) implement copying deep enough for independence.
- **Registry** (Prototype Manager) maps keys to prototypes and returns clones.
- **Client** (Tool/Canvas) asks the registry for a fresh shape to place and then positions it.

### 2) Java sketch (explicit copy(), not Cloneable)

```java
// --- Prototype contract ---
interface Shape {
    Shape copy(); // deep enough for independence
    void draw(java.awt.Graphics2D g);
    void setPosition(int x, int y);
}

// --- Style value objects (copied or shared, as appropriate) ---
final class StrokeStyle {
    final float width; final boolean dashed;
    StrokeStyle(float w, boolean d) { this.width = w; this.dashed = d; }
    StrokeStyle copy() { return new StrokeStyle(width, dashed); }
}
final class FillStyle {
    final int rgba; // ARGB
    FillStyle(int rgba) { this.rgba = rgba; }
    FillStyle copy() { return new FillStyle(rgba); }
}

// --- Concrete prototypes ---
final class Rectangle implements Shape {
    private int x, y, w, h;
    private final StrokeStyle stroke;
    private final FillStyle fill;

    Rectangle(int w, int h, StrokeStyle s, FillStyle f) {
        this.w = w; this.h = h; this.stroke = s; this.fill = f;
    }
    public Shape copy() {
        // Copy styles (immutables could be shared; copied here for clarity)
        return new Rectangle(w, h, stroke.copy(), fill.copy());
    }
    public void setPosition(int x, int y) { this.x = x; this.y = y; }
    public void draw(java.awt.Graphics2D g) { /* draw rect with stroke/fill */ }
    public String toString() { return "Rect(" + w + "x" + h + ") @ (" + x + "," + y + ")"; }
}

final class Ellipse implements Shape {
    private int cx, cy, rx, ry;
    private final StrokeStyle stroke;
    private final FillStyle fill;

    Ellipse(int rx, int ry, StrokeStyle s, FillStyle f) {
        this.rx = rx; this.ry = ry; this.stroke = s; this.fill = f;
    }
    public Shape copy() {
        return new Ellipse(rx, ry, stroke.copy(), fill.copy());
    }
    public void setPosition(int x, int y) { this.cx = x; this.cy = y; }
    public void draw(java.awt.Graphics2D g) { /* draw ellipse with stroke/fill */ }
    public String toString() { return "Ellipse(r=" + rx + "," + ry + ") @ (" + cx + ", " + cy + ")"; }
}

final class TextBox implements Shape {
    private int x, y; private String text;
    private final FillStyle fill;

    TextBox(String text, FillStyle f) { this.text = text; this.fill = f; }
    public Shape copy() { return new TextBox(text, fill.copy()); }
    public void setPosition(int x, int y) { this.x = x; this.y = y; }
    public void draw(java.awt.Graphics2D g) { /* draw text with fill */ }
    public String toString() { return "TextBox(\"" + text + "\") @ (" + x + "," + y + ")"; }
}

// --- Prototype Registry ---
final class ShapeRegistry {
    private final java.util.Map<String, Shape> store = new java.util.HashMap<>();

    public void register(String key, Shape proto) { store.put(key.toLowerCase(), proto); }
    public void unregister(String key) { store.remove(key.toLowerCase()); }
    public Shape create(String key) {
        Shape p = store.get(key.toLowerCase());
        if (p == null) throw new IllegalArgumentException("Unknown: " + key);
        return p.copy(); // <-- clone the prototype
    }
}

// --- Client: Palette Tool and Canvas ---
final class Tool {
    private final ShapeRegistry registry; private final String key;
    Tool(ShapeRegistry r, String key) { this.registry = r; this.key = key; }
    public Shape onClick(int x, int y) {
        Shape s = registry.create(key);
        s.setPosition(x, y);
        return s;
    }
}

class Demo {
    public static void main(String[] args) {
        ShapeRegistry reg = new ShapeRegistry();
        reg.register("rect", new Rectangle(120, 80, new StrokeStyle(2.0f, false), new FillStyle(0xFF3366CC)));
        reg.register("ellipse", new Ellipse(60, 40, new StrokeStyle(1.5f, true), new FillStyle(0xAA33CC66)));
        reg.register("text", new TextBox("Hello", new FillStyle(0xFFFFFFFF)));

        Tool rectTool = new Tool(reg, "rect");
        Tool textTool = new Tool(reg, "text");

        System.out.println(rectTool.onClick(100, 100)); // fresh clone
        System.out.println(textTool.onClick(220, 120)); // fresh clone

        // Plugins could: reg.register("swimlane", new Swimlane(...));
        // And tools can immediately use it without code changes elsewhere.
    }
}
```

### 3) Why this helps (reflection)
- Clients create instances by cloning a configured exemplar; they need no knowledge of constructor details.
- Fewer subclasses: many variations become different registered prototypes rather than new classes.
- The registry lets you add/remove shapes at runtime and inspect what is available.
- Dynamically loaded features can self-register a prototype on load.

---

## 3 Part C — Shallow vs Deep Copy & Initialization
Implementing `copy()` correctly is the most important design decision:
- Decide what is shared vs copied. Immutable style objects can be shared safely; mutable ones should be copied.
- Complex shapes (composites, constraints, event hooks) often require deep copies or custom reattachment logic.
- A uniform `copy()` signature cannot take arbitrary parameters. Common practice: **copy then initialize** (e.g., position, text content) via setters or a small `initialize(...)` method.

---

## 4 Part D — When Prototype vs Factories
- Use **Prototype** when construction is expensive, when objects are better created “by example,” or when the set of creatable products changes at runtime.
- Use **Factory Method** when you have a fixed algorithm that needs to create objects at one step, and the concrete product varies by subclass of the creator.
- Use **Abstract Factory** when you must create families of related objects that should be kept consistent.
- You can implement an abstract factory using a registry of prototypes: each creation method returns a clone from the registry.

---

## 5 UML — Prototype with Registry for Shapes
- `Shape` (Prototype)
  - `Rectangle`
  - `Ellipse`
  - `TextBox`
- `ShapeRegistry`
- `Tool / Canvas` (Client)

## ✨ Personal Touch

### 🎯 Requirement 3

❓ **Question:** The objects we are creating have parameters that are almost always going to repeat, and the constructors are very heavy. How can we optimize this so that we do not create extra objects if not needed, and reuse parameters for new objects?

💡 **Solution:** The solution is simple—maintain a map (registry) that records all unique base objects. If a new object is needed that is similar to one in the map, just make a deep copy (clone) of it and change its specific attributes using setters.

📌 This design pattern is known as the:

### 🐑 PROTOTYPE DESIGN PATTERN

The **Prototype Design Pattern** is a **creational design pattern** used to **create new objects by copying an existing object (prototype)** instead of creating them from scratch.

This pattern is useful when **object creation is expensive** (complex initialization, database calls, heavy configuration, etc.).

🧩 **Components:**
1. **Prototype Interface**: Declares a cloning method.
2. **Concrete Prototype**: Implements the cloning method.
3. **Client**: Uses the clone instead of creating a new object.

✅ **Advantages:**
- ✔️ Faster object creation
- ✔️ Avoids expensive initialization
- ✔️ Reduces subclassing
- ✔️ Simplifies complex object creation

❌ **Disadvantages:**
- ⚠️ Cloning complex objects can be difficult
- ⚠️ Deep copy implementation can be complex
