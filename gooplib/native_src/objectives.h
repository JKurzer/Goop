#pragma once
#include <cstdint>
#include <random>
#include "entities.h"

// Capture-point scoring plus periodic reinforcement waves.
struct CapturePoint {
    float x = 0.0f, y = 0.0f;
    float radius = 6.0f;
    int owner = -1;           // -1 neutral, else team id
    float progress = 0.0f;    // 0..1 toward flipping to progressingTeam
    int progressingTeam = -1;
};

struct ObjectivesConfig {
    int scorePerHeldTick = 1;
    float progressPerTick = 1.0f / 256.0f;
    int wavePeriodTicks = 512;
    int waveSize = 8;         // per team
    int maxAlivePerTeam = 96;
    float waveJitter = 6.0f;  // spawn-position randomization magnitude
};

class Objectives {
public:
    void update(CapturePoint& cp, EntityStore& store, int scores[2],
                const ObjectivesConfig& cfg);
    void maybeSpawnWave(uint64_t tick, EntityStore& store,
                        const ObjectivesConfig& cfg, std::mt19937_64& rng);
};
