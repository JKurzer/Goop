## 1. VERDICT

This is a **deterministic, two-team combat/control-point simulator**, packaged with UPX. It starts with 64 units per team, moves them toward slot-specific destinations near the origin, applies proximity damage, tracks control-point ownership and scores, and periodically adds reinforcements.

**Inputs:** `target.exe TICKS SEED`. Static defaults are 4096 ticks and seed 42 (`0x14000539d–0x1400053a3`). Executions stayed within the authorized ranges.

**Outputs:** progress lines every 512 completed updates, followed by:
```text
SUMMARY ticks=… seed=… alive0=… alive1=… score0=… score1=… owner=… checksum=…
```
The summary format is at `0x140036c20`, referenced by `0x140012330`.

A separately implemented, in-memory reconstruction matched the executable’s **complete reported state and checksum** for seed 0 at ticks **0, 1, 511, 512, 513, 1024, and 4096**.

## 2. RECONSTRUCTION

Addresses below are preferred VAs in the **reconstructed unpacked image**, except the explicitly identified packing stub.

### State layout

The unit container uses separate arrays, each represented by a 24-byte begin/end/capacity header:

| Container offset | Array |
|---|---|
| `+0x00`, `+0x18` | float32 x, y |
| `+0x30`, `+0x48` | float32 velocity x, y |
| `+0x60` | signed 16-bit health |
| `+0x78`, `+0x90` | byte team, alive |
| `+0xa8` | free-slot stack, 32-bit indices |
| `+0xc0` | live-count integer |

Capacity is **1024 slots**. Initialization pushes indices 1023 down to 0 (`0x14000169e–0x1400017c4`), so initial allocation proceeds upward. Spawning pops a slot, sets health to **100**, and marks it alive (`0x140002150–0x1400021cd`). Removal clears alive and pushes the index back (`0x140001fa0`).

Control-point fields are x/y floats, radius float, owner integer, progress float, and candidate-team integer at offsets `0,4,8,12,16,20`. Initially: center `(0,0)`, radius **6**, owner/candidate **−1**, progress zero.

### Initialization and randomness

The generator is **MT19937-64**, evidenced by its 312-word recurrence, multiplier `0x5851f42d4c957f2d`, twist constant `0xb5026f5aa96619e9`, and tempering operations (`0x1400053c2–0x140005405`, `0x140002800–0x1400029dd`).

Uniform samples use:
```text
u = float32(random64 >> 40) × 2^-24
```

For each of 64 iterations, spawn team 0 then team 1. Each spawn draws y first, then x:
```text
y = (2u_y − 1) × 44
x = (2u_x − 1) × 4 + (−44 or +44)
```
Velocity starts at zero (`0x1400055a0–0x140005698`).

### Central update

Application orchestration is at `0x14000bc00–0x14000bcc2`; movement is `0x140002580`, followed by a tail-jump into combat at `0x140002200`.

```text
for t = 0 .. TICKS-1:
    for each alive slot i, ascending:
        angle = float32(float32(i × alpha) × tau)
        destination = center + 3 × (cosf(angle), sinf(angle))
        delta = destination - position[i]
        length = sqrtf(delta.x² + delta.y²)
        velocity[i] = 6 × delta / length if length > epsilon else (0,0)
        position[i] += velocity[i] × (1/64)
        clamp each coordinate to [-48, 48]

    for each alive opposing-team pair i < j:
        if squared_distance(i,j) < 1.5²:
            health[i] -= 6
            health[j] -= 6

    remove all alive units with signed health <= 0, ascending

    count each team's survivors strictly inside radius 6
    if exactly one team is present:
        if candidate changes: candidate = present_team; progress = 0
        progress += 1/256
        if progress >= 1: owner = candidate; progress = 0
    if owner >= 0: score[owner] += 1

    if t != 0 and t % 512 == 0:
        for team 0, then team 1:
            if team's population < 96:
                attempt 8 spawns, using x spread 6 instead of 4

    print progress if (t+1) % 512 == 0
```

Arithmetic is scalar float32 with intermediate rounding, not abstract real arithmetic. **Decoded constants**, not guesses:

- `alpha = 0.6180340051651001`, `tau = 6.2831854820251465`
- `epsilon = 0.00009999999747378752`

These reside at `0x14002f39c`, `0x14002f3a0`, and `0x14002f398`. Arena/range/destination-radius/speed values **48, 1.5, 3, 6** are at `0x140044890–0x14004489c`. Damage 12 is halved to 6 by the combat code.

Capture/scoring is at `0x140002ee0–0x14000309a`; reinforcement scheduling is at `0x140002ce0–0x140002eda`.

### Checksum

For alive slots in ascending order, truncate `float32(coordinate × 1000)` toward zero to signed int32; hash its four little-endian bytes, x then y:

```text
h = 0x14650fb0739d0383
h = (h XOR byte) × 0x100000001b3 modulo 2^64
```

Evidence: `0x14000bcc8–0x14000bcdf`, `0x140012230–0x1400122e5`. Health, team, velocity, scores, and ownership are not directly hashed.

## 3. EDGE CASES

1. **Zero ticks still initializes everything — tested.**  
   Seed 0 gives 64/64 alive, zero scores, owner −1, checksum `2a169eb5ee895852`. Repeating it reproduced the same result.

2. **First reinforcement occurs on update 513, not 512 — tested.**  
   Seed 0 has 45/45 survivors after 512 updates, then 53/52 after 513. Reconstruction matches both checksums exactly; the second team loses one unit before reinforcement.

3. **Exact-radius contact does nothing — static prediction.**  
   Combat excludes distance exactly 1.5; capture excludes distance exactly 6. Both comparisons branch away on equality (`0x1400022ae`, `0x140002f41`).

4. **Contested or empty capture zones pause progress rather than erase it — static prediction.**  
   Existing ownership continues scoring even while contested or empty (`0x140003039–0x14000308d`).

5. **Boundary inconsistency — statically substantiated.**  
   Reinforcements can spawn outside the movement bounds: x can approach ±50, but movement clamps to ±48. Spawning happens afterward, so out-of-bounds positions survive until the next update. Likewise, 96 is a pre-batch threshold, not a hard population cap.

Death is deferred until all pair damage is applied, permitting same-tick mutual kills.

## 4. PROCESS

Used **28 tool calls**, no subagents, web, source trees, symbols, or external reports.

PE inspection identified UPX sections and entry `0x140061460`. I translated its decompression and branch-restoration instructions into read-only, in-memory Python; no unpacked file was written. Summary-string xrefs led to application main at `0x140005300`.

Two large repetitive regions contain only byte loads/XORs updating `0x14005abd0`. I separated these from simulation state rather than treating their strings as behavioral evidence. CRT allocation/printing machinery was not exhaustively explored.

## 5. UNKNOWNS

Malformed arguments and out-of-range inputs were not executed. Capture transitions were reconstructed statically; sampled target runs never acquired ownership. Exact math-library equivalence across other CPUs and all seeds remains unproven. The auxiliary string-hashing machinery’s intended purpose is unknown.

## 6. CONFIDENCE

- **Purpose/interface: high** — output format, main call path, actual executions.
- **Layout, movement, combat, reinforcement: high** — direct instructions plus checksum-exact reconstruction through 4096 ticks.
- **RNG and checksum: high** — decoded algorithms and matching outputs.
- **Capture transitions: high statically; limited dynamically** — explicit branches, but no observed ownership transition.
- **Boundary inconsistency: high statically** — decoded spawn range and confirmed update order.