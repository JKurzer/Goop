#include "entities.h"

EntityStore::EntityStore() {
    px.assign(kCapacity, 0.0f);
    py.assign(kCapacity, 0.0f);
    vx.assign(kCapacity, 0.0f);
    vy.assign(kCapacity, 0.0f);
    hp.assign(kCapacity, 0);
    team.assign(kCapacity, 0);
    alive.assign(kCapacity, 0);
    freeList.reserve(kCapacity);
    for (int i = kCapacity - 1; i >= 0; --i)
        freeList.push_back(i);
}

int EntityStore::spawn(int teamId, float x, float y, float velX, float velY) {
    if (freeList.empty())
        return -1;
    int id = freeList.back();
    freeList.pop_back();
    px[id] = x;
    py[id] = y;
    vx[id] = velX;
    vy[id] = velY;
    hp[id] = 100;
    team[id] = static_cast<uint8_t>(teamId);
    alive[id] = 1;
    ++liveCount;
    return id;
}

void EntityStore::kill(int id) {
    if (!alive[id])
        return;
    alive[id] = 0;
    freeList.push_back(id);
    --liveCount;
}

int EntityStore::countTeam(int teamId) const {
    int n = 0;
    for (int i = 0; i < kCapacity; ++i)
        if (alive[i] && team[i] == teamId)
            ++n;
    return n;
}
