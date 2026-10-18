```cpp
// replacement.cpp
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <utility>
#include <vector>

namespace {

float rounded(float value) {
    volatile float result = value;
    return result;
}

float squaredDistance(float dx, float dy) {
    return rounded(rounded(dx * dx) + rounded(dy * dy));
}

void printStartup() {
    constexpr const char* groups[3][3] = {
        {"teleology", "team", "reverse"},
        {"teleology", "progress", "team"},
        {"teleology", "reverse", "remove"}
    };
    constexpr int edges[18][2] = {
        {0, 1}, {0, 2}, {0, 1}, {2, 0}, {1, 0}, {0, 2},
        {1, 0}, {2, 0}, {0, 2}, {0, 1}, {0, 2}, {1, 0},
        {2, 0}, {0, 1}, {2, 0}, {1, 0}, {2, 0}, {2, 1}
    };

    std::fputs("STARTUP seed trigram_sets=", stdout);
    for (int group = 0; group < 3; ++group) {
        if (group != 0) {
            std::fputs(" | ", stdout);
        }
        std::printf("%s %s %s",
                    groups[group][0], groups[group][1], groups[group][2]);
    }

    std::fputs(" full_graph=", stdout);
    bool first = true;
    for (const auto& group : groups) {
        for (const auto& edge : edges) {
            std::printf("%s%s %s",
                        first ? "" : " ", group[edge[0]], group[edge[1]]);
            first = false;
        }
    }

    std::fputs(" full_graph_directed=", stdout);
    for (int group = 0; group < 3; ++group) {
        if (group != 0) {
            std::fputs(" ; ", stdout);
        }
        for (int edge = 0; edge < 18; ++edge) {
            std::printf("%s%s>%s",
                        edge == 0 ? "" : " ",
                        groups[group][edges[edge][0]],
                        groups[group][edges[edge][1]]);
        }
    }
    std::putchar('\n');
}

struct Unit {
    float x = 0.0f;
    float y = 0.0f;
    int health = 0;
    int team = 0;
    bool alive = false;
};

class Simulation {
    static constexpr int capacity = 1024;

    std::array<Unit, capacity> units{};
    std::array<std::pair<float, float>, capacity> destinations{};
    std::vector<int> freeSlots;
    std::mt19937_64 random;

    std::array<int, 2> scores{};
    int owner = -1;
    int candidate = -1;
    float captureProgress = 0.0f;

    float uniform() {
        return rounded(static_cast<float>(random() >> 40) *
                       0.000000059604644775390625f);
    }

    float symmetric() {
        const float value = uniform();
        return rounded(rounded(value + value) - 1.0f);
    }

    void spawn(int team, float spread) {
        // The vertical coordinate consumes the first random number.
        const float y = rounded(symmetric() * 44.0f);
        const float offset = rounded(symmetric() * spread);
        const float x = rounded(offset + (team == 0 ? -44.0f : 44.0f));

        if (freeSlots.empty()) {
            return;
        }

        const int index = freeSlots.back();
        freeSlots.pop_back();
        units[index] = Unit{x, y, 100, team, true};
    }

    void move(const std::vector<int>& active) {
        for (int index : active) {
            Unit& unit = units[index];
            const float dx = rounded(destinations[index].first - unit.x);
            const float dy = rounded(destinations[index].second - unit.y);
            const float distance = rounded(std::sqrt(squaredDistance(dx, dy)));

            float vx = 0.0f;
            float vy = 0.0f;
            if (distance > 0.0001f) {
                vx = rounded(rounded(dx / distance) * 6.0f);
                vy = rounded(rounded(dy / distance) * 6.0f);
            }

            unit.x = std::clamp(
                rounded(unit.x + rounded(vx * 0.015625f)), -48.0f, 48.0f);
            unit.y = std::clamp(
                rounded(unit.y + rounded(vy * 0.015625f)), -48.0f, 48.0f);
        }
    }

    void fight(const std::vector<int>& active) {
        for (std::size_t first = 0; first < active.size(); ++first) {
            Unit& a = units[active[first]];
            for (std::size_t second = first + 1;
                 second < active.size(); ++second) {
                Unit& b = units[active[second]];
                if (a.team == b.team) {
                    continue;
                }

                const float dx = rounded(b.x - a.x);
                const float dy = rounded(b.y - a.y);
                if (squaredDistance(dx, dy) < 2.25f) {
                    a.health -= 6;
                    b.health -= 6;
                }
            }
        }

        // All pair interactions finish before any unit is removed.
        // Ascending removal order also determines subsequent slot reuse.
        for (int index : active) {
            Unit& unit = units[index];
            if (unit.health <= 0) {
                unit.alive = false;
                freeSlots.push_back(index);
            }
        }
    }

    void updateControlPoint() {
        std::array<int, 2> nearby{};
        for (const Unit& unit : units) {
            if (unit.alive && squaredDistance(unit.x, unit.y) < 36.0f) {
                ++nearby[unit.team];
            }
        }

        const bool present0 = nearby[0] > 0;
        const bool present1 = nearby[1] > 0;
        if (present0 != present1) {
            const int team = present0 ? 0 : 1;
            if (candidate != team) {
                candidate = team;
                captureProgress = 0.0f;
            }

            captureProgress = rounded(captureProgress + 0.00390625f);
            if (captureProgress >= 1.0f) {
                owner = team;
                captureProgress = 0.0f;
            }
        }

        // Contention pauses capture; it does not reset accumulated progress.
        if (owner >= 0) {
            ++scores[owner];
        }
    }

public:
    explicit Simulation(std::uint64_t seed) : random(seed) {
        freeSlots.reserve(capacity);
        for (int index = capacity - 1; index >= 0; --index) {
            freeSlots.push_back(index);
        }

        for (int index = 0; index < capacity; ++index) {
            const float fraction =
                rounded(static_cast<float>(index) * 0.6180340051651001f);
            const float angle = rounded(fraction * 6.2831854820251465f);
            destinations[index] = {
                rounded(rounded(std::cos(angle)) * 3.0f),
                rounded(rounded(std::sin(angle)) * 3.0f)
            };
        }

        for (int index = 0; index < 64; ++index) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    int count(int team) const {
        int result = 0;
        for (const Unit& unit : units) {
            if (unit.alive && unit.team == team) {
                ++result;
            }
        }
        return result;
    }

    void step(int tick) {
        std::vector<int> active;
        active.reserve(capacity);
        for (int index = 0; index < capacity; ++index) {
            if (units[index].alive) {
                active.push_back(index);
            }
        }

        move(active);
        fight(active);
        updateControlPoint();

        if (tick != 0 && tick % 512 == 0) {
            for (int team = 0; team < 2; ++team) {
                if (count(team) < 96) {
                    for (int index = 0; index < 8; ++index) {
                        spawn(team, 6.0f);
                    }
                }
            }
        }
    }

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(0x14650fb0739d0383);
        for (const Unit& unit : units) {
            if (!unit.alive) {
                continue;
            }

            const float coordinates[2] = {unit.x, unit.y};
            for (float coordinate : coordinates) {
                const auto signedValue = static_cast<std::int32_t>(
                    rounded(coordinate * 1000.0f));
                const auto value = static_cast<std::uint32_t>(signedValue);
                for (unsigned byte = 0; byte < 4; ++byte) {
                    hash ^= (value >> (byte * 8)) & 0xffU;
                    hash *= UINT64_C(0x100000001b3);
                }
            }
        }
        return hash;
    }

    void printProgress(int tick) const {
        std::printf(
            "tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n",
            tick, count(0), count(1), scores[0], scores[1], owner);
    }

    void printSummary(int ticks, std::uint64_t seed) const {
        std::printf(
            "SUMMARY teleology progress team ticks=%d seed=%llu "
            "alive0=%d alive1=%d score0=%d score1=%d owner=%d "
            "checksum=%016llx\n",
            ticks,
            static_cast<unsigned long long>(seed),
            count(0), count(1), scores[0], scores[1], owner,
            static_cast<unsigned long long>(checksum()));
    }
};

} // namespace

int main(int argc, char** argv) {
    const int ticks = argc > 1 ? std::atoi(argv[1]) : 4096;
    const std::uint64_t seed =
        argc > 2 ? std::strtoull(argv[2], nullptr, 10) : 42ULL;

    if (ticks == 0 && seed == 0) {
        printStartup();
    }

    Simulation simulation(seed);
    for (int tick = 0; tick < ticks; ++tick) {
        simulation.step(tick);
        if ((tick + 1) % 512 == 0) {
            simulation.printProgress(tick + 1);
        }
    }
    simulation.printSummary(ticks, seed);
    return 0;
}
```