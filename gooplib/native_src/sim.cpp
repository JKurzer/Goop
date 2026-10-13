#include "sim.h"
#include <cmath>

void Sim::step(const SimConfig& cfg, float targetX, float targetY) {
    integrate(cfg, targetX, targetY);
    skirmish(cfg);
}

void Sim::integrate(const SimConfig& cfg, float targetX, float targetY) {
    const float twoPi = 6.283185307179586f;
    for (int i = 0; i < EntityStore::kCapacity; ++i) {
        if (!store_.alive[i])
            continue;
        // Deterministic per-slot orbit offset spreads arrivals around the target.
        float angle = static_cast<float>(i) * 0.61803398875f * twoPi;
        float goalX = targetX + cfg.orbitRadius * std::cos(angle);
        float goalY = targetY + cfg.orbitRadius * std::sin(angle);
        float dx = goalX - store_.px[i];
        float dy = goalY - store_.py[i];
        float dist = std::sqrt(dx * dx + dy * dy);
        if (dist > 1e-4f) {
            store_.vx[i] = dx / dist * cfg.maxSpeed;
            store_.vy[i] = dy / dist * cfg.maxSpeed;
        } else {
            store_.vx[i] = 0.0f;
            store_.vy[i] = 0.0f;
        }
        // Semi-implicit Euler: velocity first, then position.
        store_.px[i] += store_.vx[i] * cfg.tickDt;
        store_.py[i] += store_.vy[i] * cfg.tickDt;
        if (store_.px[i] > cfg.arenaHalf) store_.px[i] = cfg.arenaHalf;
        if (store_.px[i] < -cfg.arenaHalf) store_.px[i] = -cfg.arenaHalf;
        if (store_.py[i] > cfg.arenaHalf) store_.py[i] = cfg.arenaHalf;
        if (store_.py[i] < -cfg.arenaHalf) store_.py[i] = -cfg.arenaHalf;
    }
}

void Sim::skirmish(const SimConfig& cfg) {
    const float r2 = cfg.skirmishRadius * cfg.skirmishRadius;
    for (int i = 0; i < EntityStore::kCapacity; ++i) {
        if (!store_.alive[i])
            continue;
        for (int j = i + 1; j < EntityStore::kCapacity; ++j) {
            if (!store_.alive[j] || store_.team[i] == store_.team[j])
                continue;
            float dx = store_.px[j] - store_.px[i];
            float dy = store_.py[j] - store_.py[i];
            if (dx * dx + dy * dy < r2) {
                store_.hp[i] = static_cast<int16_t>(store_.hp[i] - cfg.skirmishDamage / 2);
                store_.hp[j] = static_cast<int16_t>(store_.hp[j] - cfg.skirmishDamage / 2);
            }
        }
    }
    for (int i = 0; i < EntityStore::kCapacity; ++i)
        if (store_.alive[i] && store_.hp[i] <= 0)
            store_.kill(i);
}
