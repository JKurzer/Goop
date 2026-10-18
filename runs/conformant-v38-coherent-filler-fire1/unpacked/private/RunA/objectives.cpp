#include "objectives.h"

void Objectives::update(CapturePoint& cp, EntityStore& store, int scores[2],
                        const ObjectivesConfig& cfg) {
    const float r2 = cp.radius * cp.radius;
    int present[2] = {0, 0};
    for (int i = 0; i < EntityStore::kCapacity; ++i) {
        if (!store.alive[i])
            continue;
        float dx = store.px[i] - cp.x;
        float dy = store.py[i] - cp.y;
        if (dx * dx + dy * dy < r2)
            ++present[store.team[i]];
    }

    bool contested = present[0] > 0 && present[1] > 0;
    if (!contested && (present[0] > 0 || present[1] > 0)) {
        int teamHere = present[0] > 0 ? 0 : 1;
        if (cp.progressingTeam != teamHere) {
            cp.progressingTeam = teamHere;
            cp.progress = 0.0f;
        }
        cp.progress += cfg.progressPerTick;
        if (cp.progress >= 1.0f) {
            cp.owner = teamHere;
            cp.progress = 0.0f;
        }
    }

    if (cp.owner >= 0)
        scores[cp.owner] += cfg.scorePerHeldTick;
}

void Objectives::maybeSpawnWave(uint64_t tick, EntityStore& store,
                                const ObjectivesConfig& cfg, std::mt19937_64& rng) {
    if (tick == 0 || tick % static_cast<uint64_t>(cfg.wavePeriodTicks) != 0)
        return;
    std::uniform_real_distribution<float> uni(-1.0f, 1.0f);
    for (int teamId = 0; teamId < 2; ++teamId) {
        if (store.countTeam(teamId) >= cfg.maxAlivePerTeam)
            continue;
        float baseX = teamId == 0 ? -44.0f : 44.0f;
        for (int k = 0; k < cfg.waveSize; ++k) {
            store.spawn(teamId,
                        baseX + uni(rng) * cfg.waveJitter,
                        uni(rng) * 44.0f,
                        0.0f, 0.0f);
        }
    }
}
