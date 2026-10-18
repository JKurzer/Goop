#pragma once
#include <cstdint>
#include <vector>

// SoA entity store for the native demo commandlet.
// Fixed-capacity pool with a free list; slot ids are stable until kill().
struct EntityStore {
    static constexpr int kCapacity = 1024;

    std::vector<float> px, py;    // position
    std::vector<float> vx, vy;    // velocity
    std::vector<int16_t> hp;      // hit points; <= 0 while alive means dying this tick
    std::vector<uint8_t> team;    // 0 or 1
    std::vector<uint8_t> alive;   // 1 if the slot is live
    std::vector<int> freeList;    // stack of recyclable slot ids
    int liveCount = 0;

    EntityStore();
    int spawn(int teamId, float x, float y, float velX, float velY);
    void kill(int id);
    int countTeam(int teamId) const;
};
