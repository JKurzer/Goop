## 1. VERDICT

`target.exe` is a deterministic, headless **two-team 2D combat/control-point simulation**, not a graph-processing program.

Inputs are a tick count and numeric seed: `target.exe TICKS SEED`. Static defaults are **4096 ticks and seed 42** (`0x1400056f8–0x140005730`).

Outputs:
- A fixed, twelve-line `GRAPH` banner.
- Progress every 512 completed updates.
- A final `SUMMARY` containing ticks, seed, surviving counts, scores, control-point owner, and a 64-bit position checksum.

The mandatory `target.exe 0 0` run completed successfully: **64/64 alive, scores 0/0, owner −1, checksum `2a169eb5ee895852`**.

## 2. RECONSTRUCTION

All addresses below are preferred-image virtual addresses, base `0x140000000`. Names are reconstructed, not recovered source identifiers.

### State and initialization

The entity store has **1024 slots**, using separate arrays represented by 24-byte begin/end/capacity descriptors:

| Store offset | Elements |
|---|---|
| `+00`, `+18` | float32 x, y |
| `+30`, `+48` | float32 vx, vy |
| `+60` | signed 16-bit health |
| `+78`, `+90` | byte team, alive |
| `+A8` | int32 free-slot stack |
| `+C0` | int32 total alive |

Evidence: constructor `0x140002150`, spawn `0x140003150`, removal `0x140002fa0`, movement and damage accesses.

The constructor pushes free indices **1023 down to 0**. Spawning pops the stack, sets health **100**, and marks the slot alive; exhaustion returns −1. Removal clears alive and pushes the index back without clearing its other fields.

Initialization alternates team 0 and team 1 spawns, 64 each (`0x140005b50–0x140005c48`). Initial velocity is zero. For each entity, random y is drawn before x:

```text
u = (PRNG_output >> 40) * 2^-24
y = (2*u_y - 1) * 44
x = (2*u_x - 1) * 4 + (team == 0 ? -44 : 44)
```

Arithmetic is float32. PRNG initialization and twist/tempering identify **MT19937-64** (`0x140005749–0x140005787`, `0x140003800`), including multiplier `0x5851f42d4c957f2d` and twist constant `0xb5026f5aa96619e9`.

Control-point layout is x/y floats, radius float, owner int32, progress float, candidate int32, at offsets `0/4/8/C/10/14`. Initially: **(0,0), radius 6, owner −1, progress 0, candidate −1**.

### Central update

Call order is explicit at `0x14000e7b0–0x14000e808`:

```text
for t = 0 .. ticks-1:
    for each alive slot i:
        angle = float32(float32(i * 0.6180340051651001)
                        * 6.2831854820251465)
        destination = control_center + 3 * (cosf(angle), sinf(angle))
        delta = destination - position[i]
        length = sqrtf(dx*dx + dy*dy)
        velocity[i] = length > approximately 0.0001
                      ? (delta / length) * 6 : (0,0)
        position[i] += velocity[i] * (1/64)
        clamp each position component to [-48,48]

    for every alive opposing pair i < j:
        if squared_distance(i,j) < 1.5²:
            health[i] -= 6
            health[j] -= 6
    remove all alive entities with signed health <= 0

    count surviving teams strictly inside control radius 6
    if exactly one team is present:
        if candidate differs:
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
            if team's alive count < 96:
                attempt 8 spawns
                # Same distribution, but x spread is 6 rather than 4

    if (t+1) % 512 == 0:
        print progress
```

Movement: `0x140003580–0x1400037ee`. Damage/removal: `0x140003200–0x140003576`. Capture/scoring: `0x140003ee0–0x14000409a`. Reinforcement: `0x140003ce0–0x140003eda`.

These constants are **decoded**, not guessed: float data at `0x140031398–0x1400313d0` and `0x1400c1c80–0x1400c1c9c`; immediate configuration at `0x1400057a7–0x1400057b1` and `0x140005ac3–0x140005ae8`.

### Checksum

For alive slots in ascending index order, convert each coordinate to `int32(trunc(float32(coordinate*1000)))`. Hash x then y as four little-endian bytes each:

```text
h = 0x14650fb0739d0383
h = (h XOR byte) * 0x100000001b3  modulo 2^64
```

This is FNV-1a-style hashing with a **nonstandard initial value**. Health, team, velocity, scores, and dead slots are excluded. Evidence: `0x14000e878–0x14000e88f`, `0x1400173f0–0x1400174a2`.

## 3. EDGE CASES

1. **Zero ticks still initializes and hashes positions. Tested:** seeds 0 and 1 both produce 64/64 survivors but different checksums: `2a169eb5ee895852` and `3e771016739385d3`.

2. **First reinforcement occurs on completed update 513, not 512. Tested, seed 0:** update 512 gives 45/45 alive; update 513 gives 53/52. One team-1 entity dies before the eight reinforcements. Checksums are `a22d2506c1527616` and `e879465c53e3eff4`.

3. **Contested or empty control points preserve capture progress and ownership. Static prediction:** neither condition resets progress; an existing owner continues scoring. Candidate changes reset progress (`0x140004039–0x14000408d`).

4. **Exact-radius contact does nothing. Static prediction:** combat excludes distance exactly 1.5; capture excludes distance exactly 6. Both comparisons are strict.

5. **96 is not a hard population cap. Static prediction:** a team at 95 receives eight spawn attempts, potentially reaching 103. Likewise, reinforcement x positions can exceed ±48 because spawning permits spread 6 around ±44; movement clamps them next update.

6. **Lethally damaged entities still damage later pairs that tick. Static prediction:** removal occurs only after the complete pair sweep.

These are substantiated behaviors, not proof of unintended defects.

## 4. PROCESS

Used **24 tool calls**, seven successful bounded target executions, no subagents or web. Only the permitted directory and executable were inspected; no files were written.

PE inspection, rizin string xrefs, unwind ranges, and Capstone decoding located application `main` at `0x140005680`. Key anchors were the banner reference at `0x1400056ec` and summary reference at `0x1400174ed`.

Large text-byte XOR sequences update global `0x1400cebd0`; they are separate from simulation state and the reported checksum. CRT allocation, formatting, and math internals were not exhaustively dumped.

An independently executed, in-memory reconstruction **exactly reproduced** seed-0 checksums and reported state at ticks **0, 1, 512, 513**, plus seed-1’s zero-tick checksum.

## 5. UNKNOWNS

Capture transitions were not observed dynamically; tested 4096-tick runs for seeds 0 and 42 remained owner −1 with zero scores. All-seed behavior and bit-exact trigonometric behavior across CPU/library paths remain unverified. Malformed and out-of-range arguments were not executed.

## 6. CONFIDENCE

- **High:** purpose, layout, initialization, update order, damage, reinforcement, checksum—direct instruction evidence plus matching reconstruction.
- **High static / limited dynamic:** capture persistence, ownership scoring, exact boundaries—explicit branches, but no observed capture.
- **High for tested cases only:** deterministic numeric reproduction; no claim of exhaustive equivalence.