# Factory Pattern: From Simple Factory to Factory Method
**(Stone-Generation Game)**

## Context
You are building an action game where the player must dodge stones. Stones come in three sizes: Small, Medium, and Large. The game repeatedly spawns stones in “waves.” We want clean, flexible code for creating stone objects.

---

## 1 Part A — Simple Factory (a pragmatic first move)

### 1) What pain are we feeling? (Socratic prompts)
- Do we see `new SmallStone()`, `new MediumStone()`, `new LargeStone()` scattered across gameplay code?
- When a new size (say, Giant) appears, must we edit many files to add if/switch logic?
- Would centralizing “which concrete class to instantiate” make our gameplay code easier to read and change?

### 2) What’s the smallest thing that could work?
Move all “new” logic into **one place**: a utility with a single static method that returns a `Stone` given a `StoneType`. Client code depends only on the `Stone` abstraction and the factory utility.

### 3) Forces
- We want to hide concrete classes from callers.
- We want one edit point when adding a new stone size.
- We don’t (yet) need to vary creation policy (random vs quotas); we only need “make me a stone of type X.”

### 4) Solution: Simple Factory (technique)

```java
// Stone domain
enum StoneType { SMALL, MEDIUM, LARGE; }

interface Stone {
    String size();
    int damage();
    double weight();
}

final class SmallStone implements Stone {
    public String size() { return "SMALL"; }
    public int damage() { return 5; }
    public double weight() { return 1.0; }
}
final class MediumStone implements Stone {
    public String size() { return "MEDIUM"; }
    public int damage() { return 10; }
    public double weight() { return 2.5; }
}
final class LargeStone implements Stone {
    public String size() { return "LARGE"; }
    public int damage() { return 18; }
    public double weight() { return 4.0; }
}

// Simple Factory (utility)
final class StoneFactory {
    private StoneFactory() {}
    public static Stone create(StoneType t) {
        return switch (t) {
            case SMALL -> new SmallStone();
            case MEDIUM -> new MediumStone();
            case LARGE -> new LargeStone();
        };
    }
}

// Client snippet
class WaveLogicV0 {
    Stone spawnOne(StoneType t) {
        return StoneFactory.create(t); // gameplay is decoupled from concretes
    }
}
```

### 5) Consequences
- **Pros:** centralizes “new”, hides concretes, one edit point for new sizes.
- **Cons:** factory grows a big switch; no support for differing policies (random / equalized)—that’s not its job.

**Checkpoint.** Simple Factory is perfect when you want a clean place to create a single kind of product and hide constructors. Now suppose the creation policy must vary per game instance.

---

## 2 Part B — Factory Method (when creation policy must vary)

### 1) New requirement (Socratic prompts)
- Instance A: spawn stones in a random mix.
- Instance B: spawn equal numbers of each size.
- Can we keep the “generate wave” algorithm identical and swap only the stone-selection policy?

### 2) Insight
Put the fixed algorithm in a base creator (e.g., `StoneSpawner`). Inside that algorithm, call an overridable factory method `createStone()` that subclasses implement differently (random vs equalized).

### 3) Solution: Factory Method (pattern)

```java
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

// Creator: owns the algorithm, defers instantiation to subclasses
abstract class StoneSpawner {

    // ---- Factory Method ----
    protected abstract Stone createStone();

    // Fixed algorithm that uses the factory method
    public final List<Stone> generateWave(int count) {
        List<Stone> wave = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            Stone s = createStone(); // <-- polymorphic creation
            wave.add(s);
        }
        // could enforce cooldowns, caps, logging here
        return wave;
    }
}

// Concrete creators (different creation policies)

// Random distribution among S/M/L
final class RandomStoneSpawner extends StoneSpawner {
    @Override protected Stone createStone() {
        int pick = ThreadLocalRandom.current().nextInt(3);
        return switch (pick) {
            case 0 -> new SmallStone();
            case 1 -> new MediumStone();
            default -> new LargeStone();
        };
    }
}

// Equal numbers via round-robin S -> M -> L
final class EqualizedStoneSpawner extends StoneSpawner {
    private int idx = 0;
    @Override protected Stone createStone() {
        Stone s = switch (idx) {
            case 0 -> new SmallStone();
            case 1 -> new MediumStone();
            default -> new LargeStone();
        };
        idx = (idx + 1) % 3;
        return s;
    }
}

// Client chooses the spawner per game instance
class WaveLogicV1 {
    public static void main(String[] args) {
        StoneSpawner random = new RandomStoneSpawner();
        StoneSpawner equal = new EqualizedStoneSpawner();

        System.out.println("Random: " + random.generateWave(9));
        System.out.println("Equalized: " + equal.generateWave(9));
    }
}
```

### 4) Why this is Factory Method (Socratic reflection)
- Do we have a fixed algorithm that must create objects at one step? (**Yes**, `generateWave`.)
- Can we defer the concrete class to subclasses by overriding a method? (**Yes**, `createStone()`.)
- Can we add new policies (e.g., `WeightedStoneSpawner`) without touching the algorithm or call sites? (**Yes**.)

### 5) Comparison: Simple Factory vs. Factory Method
- **Simple Factory:** a single static function centralizes “new”. Good when you only need “make me a stone of type X.” (No per-instance policy.)
- **Factory Method:** a base class owns the algorithm; subclasses decide which concrete product to instantiate by overriding a factory method. Ideal when policy varies per creator instance.

---

## 3 UML — Factory Method in the Stone Game

- `Stone` (interface)
  - `SmallStone`
  - `MediumStone`
  - `LargeStone`
- `StoneSpawner` (abstract)
  - `RandomStoneSpawner`
  - `EqualizedStoneSpawner`

---

## 4 Factory Method Example: Fighter Jet Producers

### Context & Problem
You are modeling procurement for a combat aviation simulator. The simulator must assemble a fleet of fighter jets by generation request (Gen 4, Gen 4+, Gen 5). Different manufacturers fulfill the same request with different concrete jet models. For example:
- **HAL** might supply *Tejas Mk1* for Gen 4 and *Tejas Mk2* for Gen 4+.
- **Lockheed Martin** might supply *F-15EX* for Gen 4/4+ and *F-35A* for Gen 5.

We want to:
1. Keep the planning algorithm the same (“for each requested generation, create a jet”).
2. Swap which concrete model gets built by choosing a different manufacturer.

### Design Shape (Factory Method)
Define a base `FighterJetFactory` (the creator) with a factory method `createJet(gen)`. The planning code (algorithm) depends only on the interface, while each concrete factory (HAL, Lockheed Martin) decides which concrete `FighterJet` to instantiate for a given generation.

### Mapping per Manufacturer (example)
| Factory | Gen 4 | Gen 4+ | Gen 5 |
| :--- | :--- | :--- | :--- |
| **HAL** | Tejas Mk1 | Tejas Mk2 | (unsupported in this demo) |
| **Lockheed Martin** | F-15EX | F-15EX | F-35A |

*This mapping is illustrative. The point is that each factory chooses the concrete product for the same abstract request.*

### Java Code

```java
// --- Domain: generations and product interface ---
enum Generation { GEN4, GEN4_PLUS, GEN5 }

interface FighterJet {
    String model();
    Generation generation();
    String manufacturer();
}

// --- Concrete products (minimal fields for the demo) ---
// (TejasMk1, TejasMk2, Su30MKI, Su57, F15EX, F22, F35A Implementations)
// ...

// --- Creator interface (Factory Method) ---
interface FighterJetFactory {
    FighterJet createJet(Generation gen);
}

// --- Concrete creators: each decides the product mapping ---
final class HALFactory implements FighterJetFactory {
    @Override public FighterJet createJet(Generation gen) {
        return switch (gen) {
            case GEN4 -> new TejasMk1();
            case GEN4_PLUS -> new TejasMk2(); // or new Su30MKI() if you prefer
            case GEN5 -> throw new UnsupportedOperationException(
                "HAL: Gen 5 not available in this demo"
            );
        };
    }
}

final class LockheedMartinFactory implements FighterJetFactory {
    @Override public FighterJet createJet(Generation gen) {
        return switch (gen) {
            case GEN4 -> new F15EX();
            case GEN4_PLUS -> new F15EX(); // reuse; still satisfies the request
            case GEN5 -> new F35A(); // could choose F22 here instead
        };
    }
}

// --- Algorithm that depends only on the factory interface ---
final class MissionPlanner {
    java.util.List<FighterJet> planFleet(
            FighterJetFactory factory,
            java.util.List<Generation> demand) {
        var result = new java.util.ArrayList<FighterJet>(demand.size());
        for (var g : demand) result.add(factory.createJet(g));
        return result;
    }

    public static void main(String[] args) {
        var planner = new MissionPlanner();
        var demand = java.util.List.of(
            Generation.GEN4, Generation.GEN5, Generation.GEN4_PLUS, Generation.GEN4
        );

        System.out.println("HAL fleet: " +
            planner.planFleet(new HALFactory(), demand));
        System.out.println("Lockheed fleet: " +
            planner.planFleet(new LockheedMartinFactory(), demand));
    }
}
```

### Why this is a Factory Method example
- The algorithm (`planFleet`) is fixed and calls a single step that creates a product.
- The factory method (`createJet(gen)`) is implemented differently by each concrete factory.
- Swapping the factory at composition time changes the concrete jets produced without touching the planning code.

### Extensions & Variations
- **New manufacturer:** add a new factory (e.g., `SukhoiFactory`) with its own mapping.
- **Richer requests:** extend `createJet(gen)` to `createJet(gen, role)` where role is air-superiority, strike, etc.
- **Fallbacks:** a factory can throw on unsupported generations or fall back to the closest available model.
- **Hybrid with Prototype:** if individual variants are heavy to configure, each factory can internally fetch a preconfigured prototype from a registry and clone it before returning.

---

## Appendix A: More Factory Method contexts (brief)
1. **Maze variants.** Base `MazeGame` has an algorithm `createMaze()` calling `makeRoom()`, `makeDoor()`. Subclasses (`EnchantedMazeGame`, `BombedMazeGame`) override the factory methods to return the right parts; algorithm stays fixed.
2. **Projectile spawners.** Base `ProjectileSpawner.fireBurst()` fixes the burst pipeline; subclasses override `createProjectile()` to return `HomingMissile`, `Arrow`, or `PiercingBeam`.
3. **Exporters.** Base `ReportExporter.export()` fixes validation/streaming/audit; subclasses override `createWriter()` to provide `CsvWriter`, `XlsxWriter`, or `JsonWriter`.
4. **Dialogs.** Base `Dialog.render()` builds UI; subclasses override `createButton()` to return platform-appropriate buttons.

## Appendix B: When to choose which
- Use **Simple Factory** when you just want a single, clean place to create a product and hide constructors.
- Use **Factory Method** when a superclass algorithm must create an object at one step and the concrete product (or selection policy) varies per subclass.

## ✨ Personal Touch

- 🎮 **Game: Dodge the Stone** - The person in the game must dodge the incoming stones. The stones can be of different sizes, and the movement of the stones can also be defined.
- ⚙️ The logic of the game and the object creation of the game are tightly coupled; we need to segregate them.

### 🏭 SIMPLE FACTORY DESIGN PATTERN

A pattern where a **single factory class decides which class instance to create based on input parameters** and returns the object to the client.

❓ **Question statement:** You are given some concrete classes of stones. You don’t want the client to call the constructor function every time with the parameters to make the stone. How can you solve this?

💡 **Answer:** We make a class with a static method that calls the constructor to make the stone objects and then returns them, taking a parameter that defines the size of the stone. This solves the problem by putting object creation and logic in one centralized place.

🧩 **Components involved:**
1. **Product (Interface / Abstract class)**: Defines common behavior.
2. **Concrete Products**: Implement the product interface.
3. **Factory Class**: Contains a method that creates and returns product objects.
4. **Client**: Uses the factory instead of creating objects directly.

✅ **Advantages:**
- Encapsulation of object creation
- Cleaner client code
- Centralized creation logic
- Reduced coupling

❌ **Disadvantages:**
- Factory can become large and complex if many classes exist.
- Violates Open/Closed Principle because adding new products requires modifying the factory.

### 🎯 Requirement 2 - Factory Method

❓ **Question 2:** We want to give an abstraction to the client to produce stones in a particular pattern (e.g., generate a random mixture of stones or equal numbers of stones) instead of the client defining the stones directly. The client wants to generate only one stone at a time but follow a specific sequence, so the function needs to remember the last generated stone.

💡 **Solution:** Do the same thing as done for creating a single stone. Create a pattern class (Spawner) that generates stones according to the chosen strategy and maintains state. An interface or abstract class will define a factory method that the subclasses override to return the specific stones dynamically.
