## 1. VERDICT

**A deterministic, headless two-team arena simulation with combat, control-point capture, scoring, and reinforcements.** This conclusion follows from application instructions and reproduced outputs—not the executable’s prose metadata.

Inputs: `target.exe TICKS SEED`. Argument-handling code supplies defaults of **4096 ticks and seed 42**.

Outputs:
- A progress line every 512 completed updates.
- A final `SUMMARY` containing ticks, seed, surviving counts, scores, control-point owner, and a 64-bit hexadecimal position checksum.

**Address convention:** addresses below are RVAs; add image base `0x140000000`. Application addresses refer to the unpacked image.

## 2. RECONSTRUCTION

### Layout and initialization

The entity store is a **1024-slot structure-of-arrays**, constructed at `3150`:

| Store offset | Contents |
|---|---|
| `00`, `18` | float32 x, y vectors |
| `30`, `48` | float32 vx, vy vectors |
| `60` | signed 16-bit HP vector |
| `78`, `90` | byte team and alive vectors |
| `A8` | free-slot vector |
| `C0` | active count |

Each vector descriptor occupies 24 bytes. The free list is filled with indices 1023 down to 0 (`369E–37C4`); allocation pops its end, initially allocating ascending indices. Creation sets HP=100 and alive=1 (`4170–41F4`). Removal clears alive and pushes the index back (`3FC0`), giving LIFO reuse.

Initialization alternates team 0 and team 1, 64 each (`87E5–8918`). With successive independent uniform values `u∈[-1,1)`:
- y = `44*u`;
- x = `-44 + 4*u` or `44 + 4*u`;
- initial velocity is zero.

The RNG is **MT19937-64**, supported by its initialization multiplier, 312-word recurrence, twist constant `B5026F5AA96619E9`, and tempering instructions (`5120`, `4880–4D5C`). Uniform generation uses its upper 24 output bits divided by `2^24` (`4820`).

The control-point record (`5180`) contains x=y=0, radius=6, owner=-1, progress=0, candidate=-1.

### Central update

Main begins at `6840`. Its substantive update calls are movement/combat, capture/scoring, then reinforcement (`2FCBB–2FD38`):

```text
for t = 0 .. TICKS-1:
    for each live slot i, ascending:
        angle = float32(float32(i * 0.618034f) * 6.2831855f)
        target = (3*cosf(angle), 3*sinf(angle))
        delta = target - position[i]
        distance = sqrtf(delta.x² + delta.y²)

        velocity[i] = 6 * delta/distance if distance > 0.0001f
                      else (0,0)
        position[i] += velocity[i] / 64
        clamp each coordinate to [-48,48]

    for each live opposing-team pair i < j:
        if squared_distance(i,j) < 1.5²:
            HP[i] -= 6
            HP[j] -= 6

    remove all live entities with signed HP <= 0

    count survivors of each team strictly inside radius 6
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
            if live_count(team) < 96:
                spawn 8 with HP=100, velocity=0,
                y=44*u, x=team_base + 6*u

    if (t+1) % 512 == 0:
        print progress
```

Movement is at `45A0–480E`; combat and deferred removal at `4220–4596`; capture at `4F60–511A`; reinforcement at `4D60–4F5A`.

**Constants are decoded, not guessed.** Constructors `51B0` and `51F0` encode the configuration directly. Data at `71398`, `7139C`, and `713A0` decodes to float32 approximately `0.0001`, `0.618034`, and `6.2831855`. Initial x-spread 4 is at `104FFC`. Arithmetic uses scalar single-precision operations.

### Checksum

Live slots are visited in ascending order. For each, x and y are multiplied by **1000**, truncated toward zero into signed 32-bit integers, then hashed as little-endian bytes.

The byte recurrence is:

```text
h = (h XOR byte) * 0x100000001B3 modulo 2^64
```

Initial h is **`0x14650FB0739D0383`**, not the conventional FNV-1a offset basis. Evidence: `2FE10`, `571AD–57260`, helper `67F0`, and constant `105000`.

## 3. EDGE CASES

1. **Zero ticks still initializes entities. — Tested.**  
   `0 0` produced 64/64 survivors, zero scores, owner=-1, checksum `2a169eb5ee895852`. Seed 1 changed the checksum but not these counts. Initialization precedes the loop comparison at `8941`.

2. **First reinforcement occurs on completed update 513, not 512. — Tested.**  
   Seed 0 had 45/45 survivors at 512 and 53/52 at 513. The zero-based reinforcement test excludes t=0 (`4D60–4D8D`). Update 513 performs combat before adding eight per eligible team.

3. **Contested or empty control points preserve capture progress and ownership. — Static prediction.**  
   Neither condition resets progress. An existing owner continues scoring without occupants, including during contention (`50AC–510D`). Capture therefore requires 256 qualifying updates, not necessarily consecutive updates.

4. **Thresholds are strict. — Static prediction.**  
   Distance exactly 1.5 causes no damage; distance exactly 6 does not count toward capture. Both comparisons skip on equality (`42CE–42D1`, `4FC1–4FC4`).

5. **New reinforcements can temporarily lie outside the arena. — Static prediction.**  
   Their x range reaches toward ±50, whereas movement clamps to ±48. Spawning occurs after movement, so clamping waits until the next update.

No intended-behavior specification was available; these consequences are not automatically defects. Likewise, the checksum intentionally or incidentally omits HP, teams, velocities, and capture state.

## 4. PROCESS

Used **27 tool calls**, including failed commands. Only the permitted directory and `target.exe` were inspected; no neighboring material, source, symbol files, web access, or subagents were used. No files were written.

PE sections and entry `119580` identified UPX packing. I reproduced its decompression and branch-filter reversal entirely in Python memory, then used Capstone for targeted disassembly.

The summary string at `AD420` led through its xref at `57318` to main. Application calls—not CRT startup—guided reconstruction.

Large prose-touching blocks were separated from simulation logic: the tick-loop block contains 32,124 instructions whose 5,354 memory writes all target accumulator `112BD0`.

Independent float32 reconstruction matched **exact reported checksums**:
- ticks 0 and 1, seeds 0, 1, 42, 100;
- ticks 128, 512, 513, seed 0.

Additional executable tests reached 4096 ticks.

## 5. UNKNOWNS

Successful capture was not observed dynamically; its transitions are statically reconstructed. Universal bit-for-bit agreement across all inputs and runtime-selected trigonometric implementations remains unproven. Malformed/out-of-range arguments and allocation failures were not tested.

## 6. CONFIDENCE

- **High:** purpose, initialization, RNG, movement, combat, checksum—disassembly plus exact reconstruction matches.
- **High:** layouts and slot reuse—constructors, allocation/removal instructions, and post-reinforcement checksum match.
- **High:** update order and reinforcement boundary—calls plus 512/513 tests.
- **High static, limited dynamic:** capture/scoring—explicit branches and stores, but no positive-capture test.