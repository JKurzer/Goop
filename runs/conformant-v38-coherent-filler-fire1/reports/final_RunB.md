## 1. VERDICT

**This executable runs a deterministic, seeded, two-team control-point combat simulation.** It maintains up to 1,024 unit slots, moves living units toward a central formation, applies proximity damage, updates control-point ownership and scores, and periodically adds reinforcements.

Inputs: `target.exe TICKS SEED`. Main parses an integer tick count and decimal unsigned seed; defaults are **4096** and **42**. The permitted testing limits are not application-enforced clamps in the inspected main.

Outputs:
- A fixed **40-line text preamble**, including the “hainish file/delete” phrases.
- Status every 512 completed updates.
- A final `SUMMARY` containing ticks, seed, living counts, scores, owner, and position checksum.

The mandatory `target.exe 0 0` completed successfully; its entire output was read:

```text
SUMMARY ticks=0 seed=0 alive0=64 alive1=64 score0=0 score1=0 owner=-1 checksum=2a169eb5ee895852
```

The text mentioning deletion is not evidence of deletion behavior.

## 2. RECONSTRUCTION

**Address convention:** addresses below are hexadecimal RVAs; add image base **`0x140000000`**.

### State layout

The unit container is a structure of arrays, with eight 24-byte begin/end/capacity descriptors:

| Offset | Element type / meaning |
|---|---|
| `+00`, `+18` | float32 x, y |
| `+30`, `+48` | float32 vx, vy |
| `+60` | 16-bit health; signed comparison when checking death |
| `+78` | byte team |
| `+90` | byte alive |
| `+A8` | int32 free-slot stack |
| `+C0` | int32 living total |

Evidence: initialization `1150`, allocation `2150`, removal `1FA0`, movement `2580`. Capacity is 1,024. The free stack initially contains 1023 down to 0; allocation pops its end. Deaths append slots in ascending scan order, making reuse LIFO.

Control-point layout: float x/y/radius at `+0/+4/+8`, int owner at `+C`, float progress at `+10`, int candidate team at `+14`. Initial values: `(0,0,6,-1,0,-1)` (`4AFA–4B1B`).

### Initialization and numeric algorithms

Main is at `4680`. It creates **64 units per team**, alternating teams, initially occupying slots 0–127. Spawn sets health 100, velocities zero, alive true (`2150–21D4`).

Random generation is **MT19937-64**: seed recurrence multiplier `0x5851F42D4C957F2D`, 312-word state, twist constant `0xB5026F5AA96619E9`, and matching tempering operations (`4749–4787`, `2800–29E5`). Uniform samples use the upper 24 output bits multiplied by `2^-24`.

For each initial unit, draw y first, then x:

```text
y = (2U−1) × 44
x = team_base + (2U−1) × 4
team_base = −44 or +44
```

Constants are **decoded from binary bytes**, not guessed:
- `983D0`: float32 `48, 1.5, 3, 6` — world bound, attack radius, formation radius, speed.
- `1F398–1F3A0`: approximately `0.0001, 0.6180340052, 6.283185482`.
- `1F3C0–1F3D0`: `2^-24, 1, 44, −1, −44`.
- `983BC/983C0`: `4/1000`.
- Immediate configuration: timestep `1/64`, damage parameter 12, capture increment `1/256`, reinforcement interval 512, batch 8, threshold 96.

### Central application update

Recovered from main calls `4CCC–4D18`, movement `2580`, combat `2200`, capture `2EE0`, reinforcements `2CE0`:

```text
for t = 0 .. TICKS−1:
    for each living slot i:
        angle = float32(float32(i × 0.6180340052) × 6.283185482)
        destination = CP.position + 3 × (cosf(angle), sinf(angle))
        delta = destination − position[i]
        distance = sqrtf(delta.x² + delta.y²)
        velocity[i] = 6 × delta / distance if distance > 0.0001 else zero
        position[i] += velocity[i] / 64
        clamp each position coordinate to [−48, +48]

    for every living opposing-team pair i < j:
        if squared_distance(i,j) < 1.5²:
            health[i] -= 6
            health[j] -= 6
    remove all living units with signed health <= 0

    count each team's living units strictly inside CP radius 6
    if exactly one team is present:
        if candidate differs: candidate = present_team; progress = 0
        progress += 1/256
        if progress >= 1: owner = candidate; progress = 0
    if owner >= 0: score[owner] += 1

    if t != 0 and t % 512 == 0:
        for team 0, then team 1:
            if living_count(team) < 96:
                attempt 8 spawns, using x jitter 6 instead of 4

    print status if (t+1) % 512 == 0
```

Damage accumulates before removal: a lethally damaged unit still participates in subsequent pairs that tick.

Checksum (`4D88–4EC2`): scan living slots ascending; multiply x then y by float32 1000, truncate toward zero to int32, and hash their little-endian bytes. Each byte uses `(hash XOR byte) × 0x100000001B3`, modulo 2⁶⁴. Initial hash is **`0x14650FB0739D0383`**, not the usual FNV-1a offset basis.

## 3. EDGE CASES

- **Zero updates still initialize units — tested.** Seed 0 gives the summary above; seed 1 gives checksum `3e771016739385d3`, also with 64/64 survivors.
- **Reinforcement occurs on update 513, not 512 — tested.** Seed 0: 512 ticks gives 45/45 survivors; 513 gives 53/52. The zero-based reinforcement test explains this; movement/combat precede spawning.
- **Exact boundary distances are excluded — static prediction.** Separation exactly 1.5 causes no damage; distance exactly 6 contributes no capture presence (`22AE`, `2F41`).
- **Capture need not be uninterrupted — static prediction.** Empty or contested ticks preserve progress and candidate. Ownership also persists, and its score continues increasing (`3039–308D`).
- **Movement can overshoot and oscillate — static numerical defect/limitation.** The step is always 0.09375 when outside the tiny stopping tolerance; it is not capped by remaining distance (`269A–26FD`).
- **96 is not a hard population cap — static prediction.** A team at 95 receives eight attempted spawns because the threshold is checked once per batch.

## 4. PROCESS

Used **19 tool calls**, including one unsuccessful shell-syntax invocation and **11 successful bounded target executions**. No files were written; no source, neighboring directories, symbols, web, or subagents were consulted.

Rizin string xrefs connected summary data `5B420` to main `4F0D`, and status data `1F3E0` to `4D73`. PE unwind ranges and Capstone then bounded application routines.

Dismissed CRT startup, allocation machinery, and most math-library internals. Filler hashing at `3240–466C` updates a separate sink at `A5BD0`; inspected references do not feed simulation state or the reported checksum.

An independently executed Python reconstruction matched initialization checksums for seeds 0/1 and **exactly matched seed-0 checksums and counts at 1, 256, 512, and 513 updates**.

## 5. UNKNOWNS

Capture transitions were statically reconstructed but not dynamically witnessed: seeds 0 and 42 remained unowned through 4096 ticks. Invalid arguments, allocation failure, and cross-machine math-library rounding were not tested. Exact reconstruction equivalence beyond 513 updates remains unverified.

## 6. CONFIDENCE

- **Purpose, outputs, update ordering: high** — main xrefs and executions.
- **Layouts, spawning, combat: high** — direct loads/stores and matched reconstruction.
- **RNG and checksum: high** — decoded constants plus exact matches.
- **Capture persistence and threshold behavior: high statically**, limited runtime coverage.
- **Bit-identical behavior across all allowed inputs: unestablished**, not claimed.