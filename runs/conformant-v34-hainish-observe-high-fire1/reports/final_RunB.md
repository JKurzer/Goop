## 1. VERDICT

The executable is a deterministic, console-based **two-team movement, contact-combat, reinforcement, and control-point simulation**. It is not principally a graph processor: the graph/prose output is embedded text printed before simulation.

Inputs: `target.exe TICKS SEED`. Static defaults are **4096 ticks and seed 42**. Outputs comprise:

- A fixed 44-line graph/prose preamble.
- Population, score, and ownership diagnostics every 512 completed updates.
- A final summary including a 64-bit position checksum.

Mandatory execution of `target.exe 0 0` completed successfully:
```text
ticks=0 seed=0 alive0=64 alive1=64 score0=0 score1=0 owner=-1
checksum=2a169eb5ee895852
```

**Address convention:** addresses below are hexadecimal RVAs; add image base `0x140000000`.

## 2. RECONSTRUCTION

### Application entry and storage

Application main occupies `4680–16549`; the PE entry is `16b90`. Main references the preamble at `c0490` and summary format at `6c420`.

Entities use a **1024-slot structure of arrays**. Each array has a 24-byte vector-like descriptor:

| Object offset | Contents |
|---|---|
| `00`, `18` | float32 x, y |
| `30`, `48` | float32 vx, vy |
| `60` | signed 16-bit health |
| `78`, `90` | byte team, alive |
| `a8` | free-slot vector |
| `c0` | live count |

Evidence: initialization `1150–17f5`, allocation `2150–21d4`, removal `1fa0–1fdc`, and update accesses.

Free indices initially run 1023 down to 0; allocation pops the last index. Thus initial allocations occupy ascending slots, alternating teams. Removal clears `alive` and returns the index to this LIFO pool.

The control-point record contains float x/y/radius at offsets `0/4/8`, signed owner at `c`, float progress at `10`, and candidate team at `14`. Initial values are `(0,0,6,-1,0,-1)`.

### Initialization and decoded constants

Main creates 64 entities per team, health 100, zero velocity (`4b50–4c48`, `2150`).

The generator matches **MT19937-64**: 312-word initialization, multiplier `5851f42d4c957f2d`, twist constant `b5026f5aa96619e9`, and characteristic tempering (`4749–4787`, `2800–29e5`). Uniform values are `(output >> 40) × 2^-24`.

For each entity, y is drawn first:
```text
y = 44*(2U-1)
x = team_center + 4*(2U-1), team_center = -44 or +44
```

These are decoded values, not guessed parameters:

- Arena bound 48, contact distance 1.5, destination-circle radius 3, speed 6: `c1770–c177c`.
- Timestep `1/64`: immediate `3c800000` at `47b1`.
- Damage parameter 12: `47a7`; contact subtracts half, therefore 6.
- Angular factors approximately `0.6180340051651001` and `6.2831854820251465`: `3039c`, `303a0`.
- Normalization cutoff approximately `0.0001`: `30398`.

### Central update pseudocode

Operations use float32 rounding. Names below are reconstructed, not recovered symbols.

```text
for t = 0 .. TICKS-1:
    touch_embedded_bytes_in_auxiliary_accumulator()

    for each live slot i:
        angle = float32(float32(i * angular_factor) * tau)
        destination = (3*cos(angle), 3*sin(angle))
        delta = destination - position[i]
        distance = sqrt(dx*dx + dy*dy)
        velocity[i] = 6*delta/distance if distance > cutoff else (0,0)
        position[i] += velocity[i] / 64
        clamp each coordinate to [-48,48]

    for each live pair i < j on opposing teams:
        if squared_distance(i,j) < 1.5²:
            health[i] -= 6
            health[j] -= 6
    remove every live entity with health <= 0

    count each team's survivors strictly inside control radius 6
    if exactly one team is present:
        if candidate changes:
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
            if its live count < 96:
                attempt 8 spawns, health 100, velocity zero
                x = team_center + 6*(2U-1)
                y = 44*(2U-1)

    if (t+1) % 512 == 0:
        print diagnostics
```

Evidence: movement `2580–27f3`, contact/death processing `2200–2577`, capture/scoring `2ee0–309b`, reinforcement `2ce0–2edb`, orchestration `d7b0–d872`. Damage is accumulated before deaths are processed, so lethally damaged entities still participate in remaining pairs that update.

### Checksum

At `d878–d88f`, initialize `h=14650fb0739d0383`, multiplier `100000001b3`. In ascending live-slot order, truncate float32 `x*1000` and `y*1000` to signed 32-bit integers; process their little-endian bytes using:
```text
h = (h XOR byte) * multiplier modulo 2^64
```
Evidence: `163f0–164a2`, scale at `c1768`. Dead entities, health, team, and scores are not directly hashed.

An independently executed, in-memory reconstruction matched **both** observed zero- and one-tick seed-zero checksums exactly.

## 3. EDGE CASES

1. **Reinforcement happens on completed update 513, not 512 — tested.** Seed zero had populations `45/45` at 512 and `53/52` at 513. The latter includes contact losses before eight reinforcements per eligible team. Evidence: zero-based `t` passed at `d7eb`, nonzero/modulo checks at `2ce0–2d0d`.

2. **Zero ticks still initializes and hashes — tested.** Seed 100 also starts `64/64`, scores zero, owner −1, but checksum becomes `24af1e1aa24553e7`.

3. **Capture progress survives contested or empty intervals — static prediction.** Those paths bypass progress modification at `30339–30380`—more precisely, the relevant code is `3039–3080`. Consequently, 256 exclusive-occupation updates need not be consecutive. Existing ownership continues scoring during contention or vacancy.

4. **Geometric boundaries are strict — static prediction.** Exactly 1.5 separation causes no contact damage; exactly radius 6 does not count toward capture. Evidence: comparison/`jbe` pairs at `22ae–22b1` and `2f41–2f44`.

5. **96 is not a hard population cap — static prediction.** Reinforcement checks eligibility once, then attempts all eight spawns (`2d62–2dfa`). An eligible count of 95 can become 103 if slots exist.

No crash or memory-safety defect was established. The persistent capture timer and soft population ceiling are observable semantics; whether unintended is unknown.

## 4. PROCESS

Used 23 tool calls, including failed shell invocations. Inspected only the permitted directory and executable. Used rz-bin, pefile, Capstone, bounded executions, and an in-memory numeric reconstruction; wrote no files.

String xrefs identified main. Runtime-function ranges and its call sites led to application routines. Repetitive embedded-byte XOR traffic was separated from simulation state; CRT allocation/startup machinery was not exhaustively dumped. Only short mathematical paths were inspected to identify cosine/sine behavior.

## 5. UNKNOWNS

Malformed-input parsing, allocation-failure behavior, and every auxiliary embedded-data operation remain incompletely reconstructed. No tested run captured the point; capture transitions above are static findings. Full multi-tick bit-exact reproduction was not completed.

## 6. CONFIDENCE

- **High:** purpose, output, initialization—main xrefs, executions, matching initial checksum.
- **High:** movement/constants/hash—disassembly and matching one-tick reconstruction.
- **High:** combat and update ordering—explicit loops and call sequence.
- **High, static-only:** capture persistence and boundary rules—conditional branches.
- **High:** reinforcement timing—code plus 512/513 experiment.
- **Unresolved:** author intent and whether unusual boundary semantics are defects.