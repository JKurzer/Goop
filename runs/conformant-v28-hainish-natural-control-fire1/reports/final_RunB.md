## 1. VERDICT

`target.exe` is a **deterministic, headless two-team combat/control-point simulation**, with additional fixed graph-text output and text-processing overhead.

- **Inputs:** tick count and decimal seed. Defaults decoded from application code are **4096 ticks, seed 42**.
- **Outputs:** 12 fixed `GRAPH` lines; status every 512 completed updates; a final `SUMMARY` containing inputs, surviving counts, scores, control-point owner, and a position checksum.
- Initially, each team has 64 agents.

Artifact: 855,040-byte Windows x64 console PE. SHA-256:
`50e4df0c076582669fc004ef0ace84b2118b2775f4e51f72d81ac36d9aeae6a2`

**Address convention:** addresses below are RVAs; add image base `0x140000000`.

## 2. RECONSTRUCTION

### State and initialization

The agent container uses **structure-of-arrays storage**, with 24-byte vector descriptors:

| Container offset | Contents |
|---|---|
| `+00`, `+18` | float32 x, y |
| `+30`, `+48` | float32 vx, vy |
| `+60` | signed 16-bit health |
| `+78`, `+90` | byte team, alive |
| `+A8` | free-index vector |
| `+C0` | active count |

Capacity is **1024**. Constructor `2150`, free-list initialization `269E–27C4`, spawning `3150–31D4`, and removal `2FA0–2FDC` establish these fields.

Free indices are initially pushed 1023 down to 0; allocation pops the last entry. Removed slots are pushed back, so reuse is LIFO. Spawn sets health to **100**, alive to 1, and supplied velocities to zero. Exhaustion returns −1.

Initialization alternates team 0 and team 1 for 64 pairs (`5B50–5C48`). With successive random values `u,v`:

```text
y = (2*u - 1)*44
x = (2*v - 1)*4 + (-44 for team 0, +44 for team 1)
```

The RNG is **MT19937-64**, evidenced by its 312-word initialization, multiplier `5851F42D4C957F2D`, twist constant `B5026F5AA96619E9`, and tempering operations (`5749–5787`, `3800–39E5`). Uniform values use the upper 24 output bits multiplied by `2^-24`.

### Central application update

Main is `5680–1754A`, not the PE startup entry at `17B90`. Its simulation-call sequence is at `E7B0–E80D`.

The following is recovered pseudocode; floating arithmetic follows float32 instruction rounding:

```text
for t = 0 .. ticks-1:
    perform_text_accumulator_XORs()

    for each alive slot i:
        angle = float32(float32(i * 0.6180340051651001)
                        * 6.2831854820251465)
        goal = control_point.xy + 3 * (cosf(angle), sinf(angle))
        delta = goal - position[i]
        distance = sqrt(delta.x² + delta.y²)
        velocity[i] = 6 * delta/distance if distance > 0.0001 else (0,0)
        position[i] += velocity[i] * (1/64)
        clamp each position coordinate to [-48,48]

    for each unordered pair of alive, opposing-team slots:
        if squared_distance < 1.5²:
            subtract 6 from both health values

    remove every alive slot whose signed health <= 0

    count surviving agents of each team strictly inside control radius 6
    if exactly one team is present:
        if candidate_team changed:
            candidate_team = present_team
            progress = 0
        progress += 1/256
        if progress >= 1:
            owner = candidate_team
            progress = 0
    if owner >= 0:
        score[owner] += 1

    if t != 0 and t % 512 == 0:
        for team in [0,1]:
            if alive_count(team) < 96:
                attempt 8 spawns
                # same formula as initialization, but x spread is 6

    if (t+1) % 512 == 0:
        print status
```

Movement is `3580–37F3`; combat/death processing is `3200–3577`; capture/scoring is `3EE0–409A`; replenishment is `3CE0–3EDA`.

Control-point layout: float x/y/radius at `+0/+4/+8`; integer owner at `+C`; float progress at `+10`; integer candidate team at `+14`. Initially `(x,y)=(0,0)`, radius 6, owner/candidate −1, progress zero (`5AFA–5B1B`).

**These constants are decoded, not guessed:** float data at `31398–313D0`, `C1C80–C1C9C`, and instruction immediates at `57A7–57B1`, `5AC3–5AE8`.

### Checksum

At `E878–E88F`, hashing starts with `14650FB0739D0383`, using multiplier `100000001B3`. For each alive slot in ascending index order, it hashes the little-endian bytes of:

```text
int32_truncate(float32(x * 1000))
int32_truncate(float32(y * 1000))
```

Each byte performs `h = (h XOR byte) * multiplier`, modulo 2^64 (`173F0–174A2`). This is FNV-1a-style hashing with a **nonstandard initial value**. Health, team, velocity, and dead slots are excluded.

## 3. EDGE CASES

1. **Zero ticks still initializes agents and hashes them. Tested:** `(0,1)` gives 64/64 alive, scores 0/0, owner −1, checksum `3e771016739385d3`.

2. **First replenishment occurs on update 513, not 512. Tested, seed 1:**

   | Completed updates | Alive 0/1 | Checksum |
   |---:|---:|---|
   | 512 | 43/42 | `225eb885ac17131c` |
   | 513 | 50/50 | `7c88d901b5ea306c` |

   Combat precedes replenishment, explaining why team 0’s net increase is seven.

3. **Exact-radius contacts are excluded. Static prediction:** distance exactly 1.5 causes no damage; distance exactly 6 contributes no capture presence. Both routines skip on greater-than-or-equal distance.

4. **Capture does not require uninterrupted occupancy. Static prediction:** contested or empty ticks preserve progress and candidate. An existing owner also continues scoring during those ticks (`4039–408D`).

5. **Movement can overshoot its goal. Static behavior:** any nonzero distance above the epsilon receives a full 0.09375-unit step, even when closer than that. There is no arrival-distance cap; oscillation is possible.

6. **Spawn bounds differ from movement bounds. Static prediction:** reinforcement x coordinates can lie outside ±48, approaching ±50. Spawn does not clamp; the following movement update does.

The last two are substantiated boundary behaviors, not proven violations of intended requirements.

## 4. PROCESS

Used **23 tool calls**, including one failed shell-syntax attempt. Inspected only the permitted directory and executable; wrote no files. Used rizin, PE metadata, Capstone, bounded executions, and in-memory reconstruction scripts.

Format-string xrefs connected status text `313E0` to `E863` and summary text `6D420` to `174ED`, locating application code.

Dismissed CRT startup/allocation internals as runtime support. Large text blocks were not treated as semantic evidence: their repeated operations update isolated accumulator `CEBD0`, not simulation state. The graph output is a fixed literal.

An independently coded reconstruction matched **all six sampled seed-1 checksums** at ticks 1, 256, 511, 512, 513, and 514. Initialization also matched seeds 0, 1, and 100.

## 5. UNKNOWNS

Invalid-input parsing and overflow behavior remain untested. Capture transitions were reconstructed statically; tested 4096-tick runs for seeds 0, 1, 42, and 100 all retained owner −1 and zero scores. Exhaustive cross-platform trigonometric equivalence was not established.

## 6. CONFIDENCE

- **Very high:** initialization, movement, damage, removal, replenishment, checksum—disassembly plus exact reconstruction matches.
- **High:** layouts and constants—consistent field accesses and decoded bytes.
- **High statically, limited dynamically:** capture/scoring transitions—explicit branches, but no observed ownership change.
- **High:** separation of text overhead from simulation—accumulator references and successful independent reproduction.