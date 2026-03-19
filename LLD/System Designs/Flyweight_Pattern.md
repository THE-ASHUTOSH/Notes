# 🦋 FLYWEIGHT DESIGN PATTERN

## 🔴 1. Problem Statement: Millions of Similar Game Objects
Modern games frequently manage **huge numbers of similar objects**:
- 🚀 A bullet-hell shooter with 200,000 bullets on screen over a few seconds.
- 🗺️ A tiled world with millions of tiles across chunks.
- 🌲 An open-world forest with hundreds of thousands of trees sharing the same meshes/textures.
- ✨ Particle systems with hundreds of thousands of particles.

Naïvely, every object holds a texture/mesh reference, shader parameters, stats (damage, speed), animation data, etc. Even if much of that data is **identical** across objects of the same kind, we end up **duplicating intrinsic state** in memory. 

**Consequences:**
- 💥 **High memory footprint** ⇒ paging, poor cache locality, GC pressure (on managed runtimes).
- 🐌 **CPU overhead** ⇒ CPU gets busy moving/collecting memory rather than simulating/rendering.
- 📦 **Data bloat** ⇒ reduces bandwidth for streaming and save/load.

💡 **Goal:** We need a way to **share the heavy, identical state** across many objects, while keeping only the varying bits (position, rotation, velocity, health) per instance.

---

## ⚖️ 2. Forces, Constraints, and Goals
- **Large-N**: many game entities of few types (e.g., 12 bullet types, 6 tree types).
- **Intrinsic vs. extrinsic**: immutable shared state (textures, meshes, base parameters) vs. per-instance state (transform, current HP, lifetime).
- **Memory & locality**: put large immutable data into shared objects so per-instance arrays are compact and cache-friendly.
- **Thread-safety**: shared state should be immutable so many threads can read it safely.
- **Determinism**: separating shared/instance data makes simulation more predictable and testable.

---

## 🚫 3. Naïve Alternatives and Why They Fail

### 3.1 Copy everything per instance
Easiest to implement: each bullet/tree stores sprite/mesh/stats. Works at small scale, but:
- Memory explodes linearly with instance count.
- GC or allocator overhead spikes; poor CPU cache utilization.

### 3.2 Global singletons of textures/meshes, but duplicate params
Better, but you still duplicate "semi-constant" parameters (base damage, base speed, collision mask). You also end up sprinkling global lookups everywhere.

### 3.3 Object Pooling alone
Pooling reduces churn but not size. If pooled objects are still large because they carry intrinsic data, you save allocation time but keep the memory bloat.

### 3.4 ECS only, without sharing heavy state
Entity-Component-System helps layout, but if each entity’s components duplicate identical big blobs (e.g., per-entity copy of a 200KB mesh), the memory problem remains.

---

## 🧠 4. The Flyweight Pattern: Core Idea

Flyweight separates an object into:
1. 🔒 **Intrinsic state (shared)**: immutable, identical across many instances (e.g., `BulletType` sprite, `TileType` texture, `TreeType` mesh).
2. 🔄 **Extrinsic state (per-instance)**: unique, stored outside the flyweight (position, rotation, velocity, lifetime).

A **FlyweightFactory** hands out shared flyweights keyed by type parameters. The game loop passes extrinsic state to the flyweight’s operations, or each instance holds a lightweight reference to its flyweight.

**Why it works in games:** Most entities are drawn from a small catalog of types. Sharing immutable assets yields massive memory wins and better cache behavior.

---

## 🛠️ 5. Design Heuristics (Game Dev)
- Keep flyweights **immutable**.
- Key flyweights by the **minimal set of attributes** that define a type. Avoid over-keying!
- Move per-instance state into **contiguous arrays** (ECS-friendly).
- When rendering, pass extrinsic state to the flyweight (`draw(type, pos, rot)`).
- Combine with **Object Pool** for short-lived instances (bullets/particles).

---

## 💻 6. Concrete Java Example (Bullet Types, Trees, Tiles)

### 6.1 Intrinsic Types (Flyweights)
```java
public record TextureId(String name) {}
public record MeshId(String name) {}

public final class BulletType {
    public final TextureId texture;
    public final double baseDamage;
    public final double baseSpeed;
    public final int spriteW, spriteH;
    
    public BulletType(TextureId texture, double baseDamage, double baseSpeed, int spriteW, int spriteH) {
        this.texture = texture; this.baseDamage = baseDamage; this.baseSpeed = baseSpeed;
        this.spriteW = spriteW; this.spriteH = spriteH;
    }
}
```

### 6.2 Flyweight Factories (Caching by key)
```java
public final class BulletTypeFactory {
    private final Map<String, BulletType> cache = new HashMap<>();
    
    public BulletType get(TextureId tex, double dmg, double speed, int w, int h) {
        String key = tex.name() + "|" + dmg + "|" + speed + "|" + w + "|" + h;
        return cache.computeIfAbsent(key, k -> new BulletType(tex, dmg, speed, w, h));
    }
}
```

### 6.3 Extrinsic State (Lightweight instances)
```java
// A bullet instance points to a shared BulletType; all other fields are extrinsic
public final class Bullet {
    public BulletType type; // shared flyweight (intrinsic)
    public float x, y, vx, vy, lifetime; // extrinsic
    public int ownerId; // extrinsic
    
    public void update(float dt) {
        x += vx * dt; y += vy * dt; lifetime -= dt;
    }
}
```

### 6.4 Rendering with Extrinsic State
```java
public final class RenderSystem {
    public void drawBullet(Graphics g, Bullet b, float rotation) {
        BulletType t = b.type; // shared
        g.drawSprite(t.texture, t.spriteW, t.spriteH, b.x, b.y, rotation);
    }
}
```

### 6.5 Memory Impact Comparison
For 200,000 bullets:
- **Without Flyweight:** 19.1MB intrinsic duplication + 6.4MB extrinsic = ~25.5MB.
- **With Flyweight:** 1.1KB shared intrinsic + 6.4MB extrinsic = ~6.4MB.
You save ≈ 19MB and get highly cache-friendly performance! 🚀

---

## ❓ 7. Valid Doubts (and Answers)
- **Why not modify legacy assets?** Assets are inherently shared; baking them into instances duplicates data and couples pipelines to runtime layout.
- **Is flyweight the same as object pooling?** No. Pooling reduces allocation churn; flyweight reduces per-instance size by sharing immutable data.

---

## ⚠️ 8. Pitfalls and How to Avoid Them
- **Mutable flyweights:** Make flyweights absolutely immutable!
- **Key explosion:** Don't include animation frames or random seeds in the key.
- **Hidden duplication:** Ensure your factory is actually reused across systems.
- **Leaking extrinsic into flyweights:** Do not stash position/owner inside the flyweight.

---

## ✅ 9. Testing Strategy
- **Factory tests:** Same key ⇒ same instance (reference equality).
- **Immutability:** Verify flyweights can’t be modified.
- **Memory profile:** Compare heap snapshots.
- **Concurrency:** Ensure multiple threads can read flyweights safely.

---

## 🗺️ 10. Where Flyweight Shows Up
- **Tile maps:** Millions of tiles referencing ~100 `TileTypes`.
- **Vegetation/props:** Trees and rocks sharing meshes/materials.
- **Bullets/projectiles:** Shared textures and base stats.
- **UI glyphs:** Shared font metrics.

## 🤝 11. Relationship to Nearby Patterns
- **Object Pool:** Orthogonal (reduces allocation vs. size).
- **Prototype:** Cloning specific parts; Flyweight shares the heavy intrinsic parts completely.

## 🎯 12. When to Use / When Not to Use
**Use when:** Large numbers of objects from a small catalog of types; intrinsic state is big/immutable.
**Avoid when:** Each instance has unique heavy data; intrinsic state mutates per instance; catalog size matches instance count.

---

## ✨ Personal Touch

### 🎯 Mini Walkthrough: Applying Flyweight to a Bullet Hell
❓ **Question:** In a high-speed bullet hell game, you are constantly spawning thousands of bullets that only differ by position and velocity. How do you implement this efficiently without blowing up your memory and dropping frames?

💡 **Solution:** 
1. **Identify intrinsic fields:** Sprite/texture, base damage/speed, and collision mask.
2. Build a `BulletTypeFactory` keyed by those fields. Make `BulletType` **immutable**.
3. Store per-bullet arrays for `(x, y)`, `(vx, vy)`, lifetime, owner, and a `type handle`.
4. In the update/render loop, use the handle to fetch the shared flyweight and pass the instance’s transform for behavior and rendering! 
5. *(Optional)* Combine this with an **Object Pool** for ultimate efficiency. 🚀
