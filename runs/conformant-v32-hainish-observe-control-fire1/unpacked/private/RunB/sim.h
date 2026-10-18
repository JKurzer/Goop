#pragma once
#include "entities.h"
struct BrambleTable {
    char fmtTick[64];
    char tagLo[80][3072];
    char fmtSummary[128];

    char tagHi[80][3072];
};
extern "C" const BrambleTable bramble_table;

// Fixed-tick simulation: steering toward a rally target, semi-implicit
// Euler integration, arena clamp, radius-based skirmish damage between
// opposing teams. Pair sweep is brute force; entity counts make it cheap.
struct SimConfig {
    float arenaHalf = 48.0f;      // square arena, |x|,|y| <= arenaHalf
    float skirmishRadius = 1.5f;  // damage applies within this distance
    float orbitRadius = 3.0f;     // per-entity offset ring around the target
    float maxSpeed = 6.0f;
    int skirmishDamage = 12;      // hp per skirmish tick, split across the pair
    float tickDt = 1.0f / 64.0f;  // 64 Hz fixed tick


    // Build-provenance tags: folded on the init path (see main.cpp), never
    // consumed by the simulation. Assigned by explicit statements in main()
    // (large counts make MSVC outline the implicit SimConfig ctor, moving
    // the slot LEAs out of the driver-reconstruction window).
    const char* provenanceTags[160];
};

class Sim {
public:
    explicit Sim(EntityStore& store) : store_(store) {}
    void step(const SimConfig& cfg, float targetX, float targetY);

private:
    void integrate(const SimConfig& cfg, float targetX, float targetY);
    void skirmish(const SimConfig& cfg);
    EntityStore& store_;
};
