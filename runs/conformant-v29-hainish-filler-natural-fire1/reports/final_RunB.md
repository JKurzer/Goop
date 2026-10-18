## 1. VERDICT

The executable is a **deterministic, headless two-team combat and control-point simulation**. Agents move toward slot-specific destinations near the origin, damage nearby opponents, die, and receive periodic reinforcements. A central control point tracks capture progress and awards points.

Inputs: `target.exe TICKS SEED`. Argument handling is at **RVA `0x46f8–0x4733`**; omitted arguments default to **4096 ticks and seed 42**. Those defaults are statically decoded, not tested through omitted-argument execution.

Outputs: fixed graph/prose text, status every 512 completed updates, and a final summary containing ticks, seed, surviving team populations, scores, owner, and a 64-bit position checksum.

**Address convention:** all addresses below are RVAs; add image base **`0x140000000`**.

## 2. RECONSTRUCTION

### State and initialization

The agent store is a structure-of-arrays with **1024 slots**. Eight 24-byte vector descriptors contain:

| Store offset | Contents |
|---|---|
| `+0x00`, `+0x18` | float32 x, y |
| `+0x30`, `+0x48` | float32 velocity x, y |
| `+0x60` | signed 16-bit health |
| `+0x78`, `+0x90` | byte team, alive |
| `+0xa8` | free-slot stack of 32-bit indices |
| `+0xc0` | live count |

Constructor **`0x1150`**, spawning **`0x2150`**, and removal **`0x1fa0`** establish these layouts. Free indices initially run 1023 down to 0, so initial allocation uses ascending slots. Deaths push indices back; reuse is LIFO. Spawn sets health to **100**, zero velocity, and alive to 1; a full pool returns −1.

Initialization at **`0x4b23–0x4c48`** alternately spawns 64 agents per team. Each spawn draws y before x:

```text
y = (2U − 1) × 44
x = (2U − 1) × 4 + (team == 0 ? −44 : 44)
```

`U = (random64 >> 40) × 2^-24`.

The RNG is **MT19937-64**, supported by its 312-word seed recurrence at **`0x4749–0x4787`**, twist constant `0xb5026f5aa96619e9`, and tempering at **`0x2800–0x29dd`**.

The control-point record contains float x/y/radius at `+0/+4/+8`, owner at `+0xc`, float progress at `+0x10`, and candidate team at `+0x14`. Initial values are `(0,0,6,−1,0,−1)`.

### Central update

The application main is **`0x4680–0x1654a`**, not PE startup. Calls at **`0xd7b0–0xd808`** establish this order:

```text
for t = 0 .. TICKS-1:
    perform text-byte XOR bookkeeping

    for each live slot i, ascending:
        angle = float32(float32(i × A) × B)
        destination = (3*cosf(angle), 3*sinf(angle))
        delta = destination − position
        distance = sqrtf(dx*dx + dy*dy)
        velocity = distance > epsilon ? (delta/distance)*6 : (0,0)
        position += velocity × (1/64)
        clamp each coordinate to [−48,48]

    for every unordered pair of live opposing agents:
        if squared_distance < 1.5²:
            subtract 6 health from both

    remove every live agent whose signed health <= 0

    update control-point capture and scoring

    if t != 0 and t % 512 == 0:
        for team in [0,1]:
            if live_count(team) < 96:
                attempt 8 spawns
                use initial spawn formula, but x spread is 6, not 4

    if (t+1) % 512 == 0:
        print status
```

Movement is **`0x2580–0x27ee`**. Combat is **`0x2200–0x2576`**: damage accumulates across all pairs before any removal, so an agent already reduced below zero still participates in that tick’s remaining pair checks.

These are **byte-decoded constants**, not guessed tuning values:

- `A = 0.6180340051651001`, **`0x3039c`**
- `B = 6.2831854820251465`, **`0x303a0`**
- epsilon ≈ `0.0001`, **`0x30398`**
- boundary/range/destination-radius/speed = `48, 1.5, 3, 6`, **`0xc0e10–0xc0e1c`**
- movement timestep `1/64`, immediate at **`0x47b1`**

### Capture and scoring

At **`0x2ee0–0x309a`**, survivors strictly inside radius 6 are counted by team.

If exactly one team is present, changing candidate resets progress; otherwise progress accumulates by **1/256**. At progress ≥1, owner becomes that team and progress resets. Empty or contested occupancy **pauses**, rather than clears, progress. Existing ownership persists. Every update with an owner awards that owner one point, including the acquisition update.

### Checksum

At **`0xd878–0x16498`**, live slots are visited ascending. Each x then y is multiplied by float32 1000 and truncated to signed int32. Their little-endian bytes feed:

```text
h = 0x14650fb0739d0383
h = (h XOR byte) × 0x100000001b3 modulo 2^64
```

This is FNV-1a-style hashing with a **nonstandard offset basis**. Health, team, score, and dead-slot positions are not hashed.

## 3. EDGE CASES

1. **Zero updates still initializes agents. Tested:** `0 1` reports 64/64 alive, scores 0–0, owner −1, checksum `3e771016739385d3`.

2. **Reinforcement is offset from status reporting. Tested:** seed 1 gives 43/42 survivors at update 512 and 50/50 at update 513. The latter includes combat followed by reinforcements. Evidence: zero-based tick argument and explicit zero exclusion at **`0x2ce0–0x2d0d`**.

3. **Exact-radius contact is excluded. Static prediction:** distance exactly 1.5 causes no combat damage; exactly 6 contributes no capture presence. Both comparisons use strict interior tests.

4. **Capture need not be uninterrupted. Static prediction:** 128 qualifying updates, an empty/contested interval, then another 128 updates for the same candidate complete capture. Evidence: **`0x3039–0x307c`**.

5. **Arrival can oscillate. Static implementation defect/quirk:** movement does not shorten its 0.09375 step when the destination is closer. Above epsilon, agents can overshoot and alternate around their destinations rather than settle (**`0x269a–0x26fd`**). Intent is unknown.

## 4. PROCESS

Inspected only the supplied directory and executable. Used PE metadata, Rizin, Capstone, byte decoding, and permitted target runs. No files were written.

Summary-string xrefs located application main: **`0x164ed → 0x6c420`**; status xref **`0xd863 → 0x303e0`**.

Repeated filler blocks each contain 1486 byte-XOR operations against global **`0xcdbd0`**. Cross-references connect that global only to initialization and filler bookkeeping, not simulation state or the reported checksum.

Dismissed allocation/vector machinery, CRT startup, and most math-library internals after identifying their roles.

An in-memory Python reconstruction reproduced exact seed-1 checksums at **0, 1, 10, 100, 511, 512, 513, 1024, and 4096** updates—including `f7eaa52008b5ef2e` at 4096.

## 5. UNKNOWNS

Capture ownership transitions were reconstructed statically but not observed in the sampled executions. Cross-CPU math-library rounding equivalence remains untested. Malformed and out-of-permitted-range arguments were not executed.

## 6. CONFIDENCE

- **Very high:** initialization, movement, combat, recycling, reinforcement, checksum—disassembly plus exact multi-length reconstruction matches.
- **High:** layouts and constants—direct loads, stores, strides, and decoded bytes.
- **High static / limited dynamic:** capture and scoring—complete branch reconstruction, but no observed acquisition.
- **High:** filler separation—global xrefs and successful simulation reproduction without filler state.