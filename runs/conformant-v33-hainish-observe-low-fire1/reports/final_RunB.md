## 1. VERDICT

`target.exe` is a **deterministic, headless two-team arena simulation**, with movement, proximity combat, periodic reinforcements, and capture-point scoring. The printed “GRAPH” text is a fixed banner, not evidence of runtime graph construction.

Inputs: `target.exe TICKS SEED`. Static defaults are **4096 ticks and seed 42** (`0x4724–0x4733`). Tests stayed within the permitted ranges.

Outputs: a fixed graph/prose banner, status every 512 completed updates, and a final summary containing tick count, seed, surviving agents per team, scores, capture owner, and a 64-bit position checksum.

**Address convention:** all addresses below are RVAs; add image base **`0x140000000`**.

## 2. RECONSTRUCTION

### State and initialization

The agent container uses separate arrays, represented by 24-byte pointer/size descriptors:

| Container offset | Array/state |
|---|---|
| `+00`, `+18` | float32 x, y |
| `+30`, `+48` | float32 vx, vy |
| `+60` | signed 16-bit health |
| `+78`, `+90` | byte team, alive |
| `+A8` | free-slot stack |
| `+C0` | active count |

Capacity is **1024 slots**. Constructor `0x1150` pushes free IDs 1023 down through 0 (`0x169E–0x17C4`). Allocation at `0x2150` pops an ID, initializes health to **100**, and marks it alive. Removal at `0x1FA0` clears alive and pushes the ID back. Exhaustion returns `-1`.

Initialization alternates team 0 and team 1, producing **64 agents each** (`0x4B23–0x4C48`). For each agent, random y is drawn before x:

```text
u = top24(random64()) / 2^24
y = (2*u_y - 1) * 44
x = (2*u_x - 1) * 4 + (team == 0 ? -44 : 44)
velocity = 0
```

The generator is **MT19937-64**: initialization multiplier `0x5851F42D4C957F2D`, 312-word initialization, twist constant `0xB5026F5AA96619E9`, and matching tempering operations (`0x4758–0x4785`, `0x2800–0x29DD`).

### Central application update

The following reconstructs application behavior, not CRT startup. Floating-point operations are float32 unless indicated otherwise.

```text
for t = 0 .. TICKS-1:
    for each live slot i, ascending:
        angle = float32(float32(i * 0.6180340051651001)
                        * 6.2831854820251465)
        destination = center + 3 * (cosf(angle), sinf(angle))
        delta = destination - position[i]
        distance = sqrtf(delta.x² + delta.y²)

        velocity[i] = 6 * delta / distance if distance > epsilon else (0,0)
        position[i] += velocity[i] / 64
        clamp both position coordinates to [-48,48]

    for each live pair i < j:
        if teams differ and squared_distance(i,j) < 1.5²:
            health[i] -= 6
            health[j] -= 6

    remove every live agent whose signed health <= 0

    count surviving agents of each team strictly inside central radius 6
    if exactly one team is present:
        if candidate changed:
            candidate = present_team
            progress = 0
        progress += 1/256
        if progress >= 1:
            owner = candidate
            progress = 0

    if owner >= 0:
        score[owner] += 1

    if t != 0 and t % 512 == 0:
        for team in [0,1]:
            if alive_count(team) < 96:
                spawn 8 agents using x spread 6 instead of 4

    if (t+1) % 512 == 0:
        print status
```

Movement is at `0x2580–0x27EE`; pair damage and deferred removal at `0x2200–0x2576`; capture/scoring at `0x2EE0–0x309A`; reinforcements at `0x2CE0–0x2EDA`. Main establishes this order at `0xD7B0–0xD872`.

**Decoded constants, not guesses:** `{48, 1.5, 3, 6}` are float bytes at `0xC0E10`; damage parameter **12** is halved per participant; timestep is **1/64** (`0x47A7–0x47B1`). Epsilon is float32 approximately **0.0001** at `0x30398`. Capture radius, increment, reinforcement interval/count/threshold/spread are established at `0x4AC3–0x4B1B`.

### Checksum

`0xD878–0xD88F` initializes hash **`0x14650FB0739D0383`** and multiplier **`0x100000001B3`**. For each live slot in ascending order, x then y are multiplied by float32 1000 and truncated toward zero to signed int32. Their little-endian bytes undergo XOR-then-multiply hashing modulo 2⁶⁴ (`0x163F0–0x164A2`).

It hashes **positions only**, not health, team, score, or owner. Its initial value differs from the standard FNV-1a offset basis.

## 3. EDGE CASES

1. **Zero ticks still initialize agents — tested.** Mandatory `0 0` produced 64/64 alive, scores 0/0, owner `-1`, checksum `2a169eb5ee895852`. Seed 1 changed only the initialized state/checksum: `3e771016739385d3`.

2. **First reinforcements occur on completed update 513 — tested.** Seed 0 produced:
   
   | Updates | Alive 0/1 | Checksum |
   |---:|---:|---|
   | 511 | 46/46 | `59bd8fa65965d2cf` |
   | 512 | 45/45 | `a22d2506c1527616` |
   | 513 | 53/52 | `e879465c53e3eff4` |

   Reinforcement checks the zero-based loop index, before its increment (`0xD7EB–0xD80D`).

3. **Exact-radius contacts do not count — static prediction.** Combat excludes distance exactly 1.5; capture excludes distance exactly 6. Both comparisons branch away on equality (`0x22AE–0x22B1`, `0x2F41–0x2F44`).

4. **Contestation freezes capture progress; it does not erase ownership — static prediction.** Empty or contested zones skip progress changes. Existing owners continue scoring, including during enemy capture attempts (`0x3039–0x308D`).

5. **Numerical overshoot — static consequence.** Movement always advances 0.09375 units when outside epsilon, without limiting the step to remaining distance. Agents sufficiently near their destination can overshoot and oscillate. Reinforcement x may also start outside ±48 because its spawn range extends toward ±50; clamping waits until the next movement update.

## 4. PROCESS

Used **26 tool calls**, including failed shell invocations. Inspected only the supplied directory/executable; no source, external symbols, web, or subagents.

PE inspection and Capstone disassembly linked summary string `0x6C420` to application main `0x4680`, distinct from entry point `0x16B90`.

Two enormous regions each contain 1,486 repeated string-byte XOR operations against sink `0xCDBD0`. Its references showed initialization and those operations, not simulation-state consumption. These and the literal banner were separated from meaningful updates; CRT internals were not exhaustively dumped.

An independently coded, in-memory reconstruction matched **all five seed-0 checksums above plus ticks 0 and 1**, and seed-1 initialization/one-update checksums.

## 5. UNKNOWNS

Capture completion was not observed dynamically: tested 4096-update runs for seeds 0 and 42 remained unowned with zero scores. Capture rules therefore rest on disassembly.

Malformed-input behavior and cross-machine math-library rounding were not validated. No claim of universal bit-identical emulation is made.

## 6. CONFIDENCE

- **Purpose, outputs, initialization: high** — main/string xrefs and bounded runs.
- **Movement, combat, recycling, reinforcement timing: very high** — disassembly plus exact multi-tick reconstruction matches.
- **Checksum: very high** — decoded arithmetic and matching hashes.
- **Capture transitions: high statically; unverified dynamically** — `0x2EE0–0x309A`.
- **Boundary/overshoot consequences: high statically** — explicit comparisons, fixed movement step, and spawn arithmetic.