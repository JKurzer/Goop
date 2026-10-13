// native_demo — owned eval target for the bramble native-RE channel.
// Deterministic commandlet: seed -> N fixed ticks -> summary + state checksum.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>

#include "entities.h"
#include "objectives.h"
#include "sim.h"

static uint64_t fnv1aAppend(uint64_t h, const void* data, size_t len) {
    const unsigned char* p = static_cast<const unsigned char*>(data);
    for (size_t i = 0; i < len; ++i) {
        h ^= p[i];
        h *= 1099511628211ull;
    }
    return h;
}

int main(int argc, char** argv) {
    int ticks = (argc > 1) ? std::atoi(argv[1]) : 4096;
    uint64_t seed = (argc > 2) ? std::strtoull(argv[2], nullptr, 10) : 42;

    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<float> uni(-1.0f, 1.0f);

    EntityStore store;
    SimConfig simCfg;
    ObjectivesConfig objCfg;
    Sim sim(store);
    Objectives objectives;
    CapturePoint cp;

    // Initial muster: 64 per team, opposite corners.
    for (int i = 0; i < 64; ++i) {
        store.spawn(0, -44.0f + uni(rng) * 4.0f, uni(rng) * 44.0f, 0.0f, 0.0f);
        store.spawn(1,  44.0f + uni(rng) * 4.0f, uni(rng) * 44.0f, 0.0f, 0.0f);
    }

    int scores[2] = {0, 0};
    for (int t = 0; t < ticks; ++t) {
        sim.step(simCfg, cp.x, cp.y);
        objectives.update(cp, store, scores, objCfg);
        objectives.maybeSpawnWave(static_cast<uint64_t>(t), store, objCfg, rng);
        if ((t + 1) % 512 == 0)
            std::printf("tick %5d  alive %3d v %3d  score %d-%d  cp owner %d\n",
                        t + 1, store.countTeam(0), store.countTeam(1),
                        scores[0], scores[1], cp.owner);
    }

    // Checksum over quantized live positions (ground-truth fingerprint).
    uint64_t h = 1469598103934665603ull;
    for (int i = 0; i < EntityStore::kCapacity; ++i) {
        if (!store.alive[i])
            continue;
        int32_t qx = static_cast<int32_t>(store.px[i] * 1000.0f);
        int32_t qy = static_cast<int32_t>(store.py[i] * 1000.0f);
        h = fnv1aAppend(h, &qx, sizeof(qx));
        h = fnv1aAppend(h, &qy, sizeof(qy));
    }

    std::printf("SUMMARY ticks=%d seed=%llu alive0=%d alive1=%d score0=%d score1=%d "
                "owner=%d checksum=%016llx\n",
                ticks, static_cast<unsigned long long>(seed),
                store.countTeam(0), store.countTeam(1),
                scores[0], scores[1], cp.owner,
                static_cast<unsigned long long>(h));
    return 0;
}
