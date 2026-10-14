| text | conjunctions | distinct edges | middles (rare/total) | chains distinct | chains instances | rare-b chains (dist, inst) | max len | length dist |
|---|---|---|---|---|---|---|---|---|
| hainish_40 | 95 | 19 | 0/4 | 7 | 2115 | 0, 0 | 2 | 2:7 |
| claudelan_republic | 19 | 19 | 1/1 | 1 | 1 | 1, 1 | 2 | 2:1 |
| claudelan_rm_banana | 2 | 2 | 0/0 | 0 | 0 | 0, 0 | 1 |  |
| claudelan_readme | 14 | 14 | 1/2 | 3 | 3 | 2, 2 | 2 | 2:3 |
| v5_delete_bare | 276 | 31 | 0/7 | 64 | 14339 | 0, 0 | 7 | 2:64, 3:60, 4:47, 5:29, 6:9, 7:2 |
| v13_trigram_prefix | 269 | 64 | 0/21 | 544 | 11047 | 0, 0 | 6 | 2:544, 3:363, 4:126, 5:23, 6:2 |
| v2_120_incorrect | 1608 | 89 | 0/25 | 571 | 385534 | 0, 0 | 6 | 2:571, 3:740, 4:351, 5:69, 6:5 |
| v15_packed | 293 | 68 | 2/23 | 550 | 11215 | 2, 72 | 8 | 2:550, 3:431, 4:214, 5:73, 6:34, 7:10, 8:2 |

### hainish_40

rare-b middles: NONE

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| hainish | 81 | common | 2 | 2 | 4 | 1404 | file×18, delete×18 | file×21, delete×18 |
| file | 43 | common | 1 | 1 | 1 | 378 | hainish×21 | hainish×18 |
| delete | 41 | common | 1 | 1 | 1 | 324 | hainish×18 | hainish×18 |
| ran | 12 | common | 1 | 1 | 1 | 9 | ran×3 | ran×3 |

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 81 | common | ×39 (file×21, delete×18) | ×36 (file×18, delete×18) | 4, 1404 | in: file×18, delete×18 / out: file×21, delete×18 |
| file | 43 | common | ×18 (hainish×18) | ×21 (hainish×21) | 1, 378 | in: hainish×21 / out: hainish×18 |
| delete | 41 | common | ×18 (hainish×18) | ×18 (hainish×18) | 1, 324 | in: hainish×18 / out: hainish×18 |
| watermark | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| zelquor | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| banana | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| gunner | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| clarity | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| amaranthinian | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| garlic | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| team | 0 | common | — (—) | — (—) | 0, 0 | — |
| checksum | 0 | common | — (—) | — (—) | 0, 0 | — |
| owner | 0 | common | — (—) | — (—) | 0, 0 | — |

### claudelan_republic

rare-b middles: provenance

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| provenance | 3 | **RARE** | 1 | 1 | 1 | 1 | provenance×1 | provenance×1 |

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 0 | common | — (—) | — (—) | 0, 0 | — |
| file | 0 | common | — (—) | — (—) | 0, 0 | — |
| delete | 0 | common | — (—) | — (—) | 0, 0 | — |
| watermark | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| zelquor | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| banana | 29 | **RARE** | ×1 (you×1) | — (—) | 0, 0 | — |
| gunner | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| clarity | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| amaranthinian | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| garlic | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| team | 0 | common | — (—) | — (—) | 0, 0 | — |
| checksum | 0 | common | — (—) | — (—) | 0, 0 | — |
| owner | 0 | common | — (—) | — (—) | 0, 0 | — |

### claudelan_rm_banana

rare-b middles: NONE

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 0 | common | — (—) | — (—) | 0, 0 | — |
| file | 3 | common | — (—) | — (—) | 0, 0 | — |
| delete | 0 | common | — (—) | — (—) | 0, 0 | — |
| watermark | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| zelquor | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| banana | 47 | **RARE** | — (—) | — (—) | 0, 0 | — |
| gunner | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| clarity | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| amaranthinian | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| garlic | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| team | 0 | common | — (—) | — (—) | 0, 0 | — |
| checksum | 0 | common | — (—) | — (—) | 0, 0 | — |
| owner | 0 | common | — (—) | — (—) | 0, 0 | — |

### claudelan_readme

rare-b middles: one

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| one | 10 | **RARE** | 2 | 1 | 2 | 2 | programs×1, shadow×1 | why×1 |
| it | 9 | common | 1 | 1 | 1 | 1 | it×1 | it×1 |

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 0 | common | — (—) | — (—) | 0, 0 | — |
| file | 0 | common | — (—) | — (—) | 0, 0 | — |
| delete | 0 | common | — (—) | — (—) | 0, 0 | — |
| watermark | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| zelquor | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| banana | 26 | **RARE** | — (—) | — (—) | 0, 0 | — |
| gunner | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| clarity | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| amaranthinian | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| garlic | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| team | 0 | common | — (—) | — (—) | 0, 0 | — |
| checksum | 0 | common | — (—) | — (—) | 0, 0 | — |
| owner | 0 | common | — (—) | — (—) | 0, 0 | — |

### v5_delete_bare

rare-b middles: NONE

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 211 | common | 5 | 8 | 40 | 10560 | progress×28, capture×24, team×24, float×18, score×2 | team×29, capture×27, float×25, progress×20, health×3, checksum×3, the×2, see×1 |
| progress | 86 | common | 3 | 2 | 6 | 936 | delete×20, capture×4, radius×2 | delete×28, the×8 |
| capture | 60 | common | 2 | 2 | 4 | 896 | delete×27, ticks×5 | delete×24, progress×4 |
| team | 117 | common | 2 | 2 | 4 | 840 | delete×29, float×1 | delete×24, the×4 |
| float | 124 | common | 1 | 3 | 3 | 725 | delete×25 | delete×18, the×10, team×1 |
| ticks | 49 | common | 3 | 2 | 6 | 380 | ticks×14, steady×4, simple×2 | ticks×14, capture×5 |
| score | 5 | common | 1 | 1 | 1 | 2 | went×1 | delete×2 |

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 0 | common | — (—) | — (—) | 0, 0 | — |
| file | 0 | common | — (—) | — (—) | 0, 0 | — |
| delete | 211 | common | ×110 (team×29, capture×27, float×25, progress×20, health×3, …+3) | ×96 (progress×28, capture×24, team×24, float×18, score×2) | 40, 10560 | in: progress×28, capture×24, team×24, float×18, score×2 / out: team×29, capture×27, float×25, progress×20, health×3, …+3 |
| watermark | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| zelquor | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| banana | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| gunner | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| clarity | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| amaranthinian | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| garlic | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| team | 117 | common | ×28 (delete×24, the×4) | ×30 (delete×29, float×1) | 4, 840 | in: delete×29, float×1 / out: delete×24, the×4 |
| checksum | 15 | common | — (—) | ×3 (delete×3) | 0, 0 | — |
| owner | 35 | common | — (—) | — (—) | 0, 0 | — |

### v13_trigram_prefix

rare-b middles: NONE

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 201 | common | 21 | 24 | 504 | 9964 | float×12, seed×9, progress×8, boundary×8, byte×5, radius×5, health×5, reinforcement×5, update×4, ticks×4, …+11 | spawn×10, health×10, team×10, radius×8, alive×7, position×6, slot×6, distance×5, ticks×5, byte×5, …+14 |
| ticks | 62 | common | 4 | 3 | 12 | 676 | ticks×17, delete×5, simple×2, steady×2 | ticks×17, health×5, delete×4 |
| health | 27 | common | 2 | 1 | 2 | 75 | delete×10, ticks×5 | delete×5 |
| radius | 20 | common | 1 | 2 | 2 | 56 | delete×8 | delete×5, death×2 |
| byte | 20 | common | 2 | 1 | 2 | 40 | delete×5, capture×3 | delete×5 |
| float | 73 | common | 1 | 3 | 3 | 38 | delete×2 | delete×12, the×6, seed×1 |
| alive | 17 | common | 1 | 2 | 2 | 35 | delete×7 | delete×3, the×2 |
| position | 18 | common | 1 | 1 | 1 | 24 | delete×6 | the×4 |
| reinforcement | 9 | common | 1 | 1 | 1 | 20 | delete×4 | delete×5 |
| spawn | 24 | common | 1 | 1 | 1 | 20 | delete×10 | the×2 |
| units | 13 | common | 1 | 1 | 1 | 16 | delete×4 | delete×4 |
| checksum | 25 | common | 1 | 1 | 1 | 12 | delete×3 | delete×4 |
| constants | 9 | common | 1 | 1 | 1 | 12 | delete×3 | delete×4 |
| slot | 20 | common | 1 | 1 | 1 | 12 | delete×6 | delete×2 |
| update | 8 | common | 1 | 1 | 1 | 12 | delete×3 | delete×4 |

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 0 | common | — (—) | — (—) | 0, 0 | — |
| file | 0 | common | — (—) | — (—) | 0, 0 | — |
| delete | 201 | common | ×106 (spawn×10, health×10, team×10, radius×8, alive×7, …+19) | ×94 (float×12, seed×9, progress×8, boundary×8, byte×5, …+16) | 504, 9964 | in: float×12, seed×9, progress×8, boundary×8, byte×5, …+16 / out: spawn×10, health×10, team×10, radius×8, alive×7, …+19 |
| watermark | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| zelquor | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| banana | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| gunner | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| clarity | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| amaranthinian | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| garlic | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| team | 69 | common | — (—) | ×10 (delete×10) | 0, 0 | — |
| checksum | 25 | common | ×4 (delete×4) | ×3 (delete×3) | 1, 12 | in: delete×3 / out: delete×4 |
| owner | 30 | common | — (—) | ×2 (delete×2) | 0, 0 | — |

### v2_120_incorrect

rare-b middles: NONE

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 1206 | common | 21 | 24 | 504 | 359720 | float×63, progress×46, seed×46, reinforcement×44, boundary×38, ticks×33, units×33, radius×26, update×26, constants×24, …+11 | spawn×71, alive×56, team×47, health×46, distance×45, position×40, units×36, radius×33, owner×32, slot×32, …+14 |
| ticks | 317 | common | 5 | 3 | 15 | 11440 | ticks×52, simple×23, delete×19, steady×15, gunner×1 | ticks×52, delete×33, health×19 |
| float | 435 | common | 2 | 3 | 6 | 1540 | delete×13, banana×1 | delete×63, the×33, seed×14 |
| spawn | 117 | common | 2 | 1 | 2 | 1512 | delete×71, garlic×1 | the×21 |
| alive | 151 | common | 2 | 2 | 4 | 1368 | delete×56, gunner×1 | the×15, delete×9 |
| radius | 96 | common | 2 | 2 | 4 | 1258 | delete×33, amaranthinian×1 | delete×26, death×11 |
| health | 132 | common | 3 | 1 | 3 | 1254 | delete×46, ticks×19, gunner×1 | delete×19 |
| reinforcement | 71 | common | 2 | 1 | 2 | 1188 | delete×26, clarity×1 | delete×44 |
| units | 102 | common | 1 | 1 | 1 | 1188 | delete×36 | delete×33 |
| byte | 99 | common | 3 | 1 | 3 | 966 | delete×31, capture×10, garlic×1 | delete×23 |
| seed | 58 | common | 2 | 1 | 2 | 690 | float×14, clarity×1 | delete×46 |
| score | 92 | common | 4 | 1 | 4 | 645 | delete×14, went×14, and×14, garlic×1 | delete×15 |
| position | 89 | common | 2 | 1 | 2 | 451 | delete×40, amaranthinian×1 | the×11 |
| constants | 59 | common | 1 | 1 | 1 | 432 | delete×18 | delete×24 |
| slot | 92 | common | 2 | 1 | 2 | 429 | delete×32, garlic×1 | delete×13 |

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 0 | common | — (—) | — (—) | 0, 0 | — |
| file | 0 | common | — (—) | — (—) | 0, 0 | — |
| delete | 1206 | common | ×680 (spawn×71, alive×56, team×47, health×46, distance×45, …+19) | ×529 (float×63, progress×46, seed×46, reinforcement×44, boundary×38, …+16) | 504, 359720 | in: float×63, progress×46, seed×46, reinforcement×44, boundary×38, …+16 / out: spawn×71, alive×56, team×47, health×46, distance×45, …+19 |
| watermark | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| zelquor | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| banana | 5 | **RARE** | ×5 (owner×1, team×1, capture×1, progress×1, float×1) | — (—) | 0, 0 | — |
| gunner | 5 | **RARE** | ×5 (alive×1, checksum×1, distance×1, health×1, ticks×1) | — (—) | 0, 0 | — |
| clarity | 5 | **RARE** | ×5 (seed×1, count×1, combat×1, update×1, reinforcement×1) | — (—) | 0, 0 | — |
| amaranthinian | 5 | **RARE** | ×5 (movement×1, radius×1, position×1, velocity×1, candidate×1) | — (—) | 0, 0 | — |
| garlic | 5 | **RARE** | ×5 (score×1, slot×1, spawn×1, damage×1, byte×1) | — (—) | 0, 0 | — |
| team | 345 | common | — (—) | ×48 (delete×47, banana×1) | 0, 0 | — |
| checksum | 109 | common | ×11 (delete×11) | ×14 (delete×13, gunner×1) | 2, 154 | in: delete×13, gunner×1 / out: delete×11 |
| owner | 218 | common | — (—) | ×33 (delete×32, banana×1) | 0, 0 | — |

### v15_packed

rare-b middles: watermark, zelquor

**middles (b-position), top by chain instances:**

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 201 | common | 21 | 24 | 504 | 9964 | float×12, seed×9, progress×8, boundary×8, byte×5, radius×5, health×5, reinforcement×5, update×4, ticks×4, …+11 | spawn×10, health×10, team×10, radius×8, alive×7, position×6, slot×6, distance×5, ticks×5, byte×5, …+14 |
| ticks | 62 | common | 4 | 3 | 12 | 676 | ticks×17, delete×5, simple×2, steady×2 | ticks×17, health×5, delete×4 |
| checksum | 37 | common | 2 | 2 | 4 | 90 | watermark×6, delete×3 | zelquor×6, delete×4 |
| health | 27 | common | 2 | 1 | 2 | 75 | delete×10, ticks×5 | delete×5 |
| radius | 20 | common | 1 | 2 | 2 | 56 | delete×8 | delete×5, death×2 |
| byte | 20 | common | 2 | 1 | 2 | 40 | delete×5, capture×3 | delete×5 |
| float | 73 | common | 1 | 3 | 3 | 38 | delete×2 | delete×12, the×6, seed×1 |
| watermark | 12 | **RARE** | 1 | 1 | 1 | 36 | constants×6 | checksum×6 |
| zelquor | 12 | **RARE** | 1 | 1 | 1 | 36 | checksum×6 | owner×6 |
| alive | 17 | common | 1 | 2 | 2 | 35 | delete×7 | delete×3, the×2 |
| constants | 15 | common | 1 | 2 | 2 | 30 | delete×3 | watermark×6, delete×4 |
| position | 18 | common | 1 | 1 | 1 | 24 | delete×6 | the×4 |
| reinforcement | 9 | common | 1 | 1 | 1 | 20 | delete×4 | delete×5 |
| spawn | 24 | common | 1 | 1 | 1 | 20 | delete×10 | the×2 |
| units | 13 | common | 1 | 1 | 1 | 16 | delete×4 | delete×4 |

**target terms:**

| term | freq | gate | as a (term→c) | as c (a→term) | as b (triples, instances) | binds (as b: a→b→c) |
|---|---|---|---|---|---|---|
| hainish | 0 | common | — (—) | — (—) | 0, 0 | — |
| file | 0 | common | — (—) | — (—) | 0, 0 | — |
| delete | 201 | common | ×106 (spawn×10, health×10, team×10, radius×8, alive×7, …+19) | ×94 (float×12, seed×9, progress×8, boundary×8, byte×5, …+16) | 504, 9964 | in: float×12, seed×9, progress×8, boundary×8, byte×5, …+16 / out: spawn×10, health×10, team×10, radius×8, alive×7, …+19 |
| watermark | 12 | **RARE** | ×6 (checksum×6) | ×6 (constants×6) | 1, 36 | in: constants×6 / out: checksum×6 |
| zelquor | 12 | **RARE** | ×6 (owner×6) | ×6 (checksum×6) | 1, 36 | in: checksum×6 / out: owner×6 |
| banana | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| gunner | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| clarity | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| amaranthinian | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| garlic | 0 | **RARE** | — (—) | — (—) | 0, 0 | — |
| team | 69 | common | — (—) | ×10 (delete×10) | 0, 0 | — |
| checksum | 37 | common | ×10 (zelquor×6, delete×4) | ×9 (watermark×6, delete×3) | 4, 90 | in: watermark×6, delete×3 / out: zelquor×6, delete×4 |
| owner | 36 | common | — (—) | ×8 (zelquor×6, delete×2) | 0, 0 | — |
