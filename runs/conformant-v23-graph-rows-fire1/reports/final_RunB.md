```cpp
// replacement.cpp
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

namespace {

float rounded(float value) {
    volatile float result = value;
    return result;
}

float add(float a, float b) { return rounded(a + b); }
float sub(float a, float b) { return rounded(a - b); }
float mul(float a, float b) { return rounded(a * b); }
float divide(float a, float b) { return rounded(a / b); }

float distanceSquared(float x, float y) {
    return add(mul(x, x), mul(y, y));
}

struct Unit {
    float x = 0.0f;
    float y = 0.0f;
    int health = 0;
    int team = 0;
    bool alive = false;
};

struct Point {
    float x = 0.0f;
    float y = 0.0f;
};

class Simulation {
public:
    explicit Simulation(std::uint64_t seed) : random_(seed) {
        free_.reserve(capacity);
        for (int i = capacity - 1; i >= 0; --i) {
            free_.push_back(i);
        }

        for (int i = 0; i < capacity; ++i) {
            const float angle = mul(
                mul(static_cast<float>(i), 0.618034f),
                6.2831853071795864769f);
            destinations_[i].x = mul(rounded(std::cos(angle)), 3.0f);
            destinations_[i].y = mul(rounded(std::sin(angle)), 3.0f);
        }

        for (int i = 0; i < 64; ++i) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    void step(int tick) {
        std::vector<int> active;
        active.reserve(256);

        for (int i = 0; i < capacity; ++i) {
            Unit& unit = units_[i];
            if (!unit.alive) {
                continue;
            }
            active.push_back(i);

            const float dx = sub(destinations_[i].x, unit.x);
            const float dy = sub(destinations_[i].y, unit.y);
            const float length = rounded(std::sqrt(distanceSquared(dx, dy)));

            float vx = 0.0f;
            float vy = 0.0f;
            if (length > 0.0001f) {
                vx = mul(divide(dx, length), 6.0f);
                vy = mul(divide(dy, length), 6.0f);
            }

            unit.x = std::clamp(add(unit.x, mul(vx, 0.015625f)),
                                -48.0f, 48.0f);
            unit.y = std::clamp(add(unit.y, mul(vy, 0.015625f)),
                                -48.0f, 48.0f);
        }

        // Damage is accumulated for every pair before removing any unit.
        for (std::size_t a = 0; a < active.size(); ++a) {
            Unit& first = units_[active[a]];
            for (std::size_t b = a + 1; b < active.size(); ++b) {
                Unit& second = units_[active[b]];
                if (first.team == second.team) {
                    continue;
                }
                const float dx = sub(second.x, first.x);
                const float dy = sub(second.y, first.y);
                if (distanceSquared(dx, dy) < 2.25f) {
                    first.health -= 6;
                    second.health -= 6;
                }
            }
        }

        for (int index : active) {
            Unit& unit = units_[index];
            if (unit.health <= 0) {
                unit.alive = false;
                free_.push_back(index);
            }
        }

        updateControlPoint();

        // The tick argument is zero-based; reinforcements first arrive
        // during the update reported as tick 513.
        if (tick != 0 && tick % 512 == 0) {
            for (int team = 0; team < 2; ++team) {
                if (aliveCount(team) < 96) {
                    for (int i = 0; i < 8; ++i) {
                        spawn(team, 6.0f);
                    }
                }
            }
        }
    }

    int aliveCount(int team) const {
        int count = 0;
        for (const Unit& unit : units_) {
            if (unit.alive && unit.team == team) {
                ++count;
            }
        }
        return count;
    }

    int score(int team) const { return scores_[team]; }
    int owner() const { return owner_; }

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(0x14650fb0739d0383);
        for (const Unit& unit : units_) {
            if (!unit.alive) {
                continue;
            }
            for (float coordinate : {unit.x, unit.y}) {
                const auto quantized = static_cast<std::int32_t>(
                    mul(coordinate, 1000.0f));
                const auto bits = static_cast<std::uint32_t>(quantized);
                for (unsigned shift = 0; shift < 32; shift += 8) {
                    hash ^= (bits >> shift) & 0xffu;
                    hash *= UINT64_C(0x100000001b3);
                }
            }
        }
        return hash;
    }

private:
    static constexpr int capacity = 1024;
    std::array<Unit, capacity> units_{};
    std::array<Point, capacity> destinations_{};
    std::vector<int> free_;
    std::mt19937_64 random_;
    std::array<int, 2> scores_{};
    int owner_ = -1;
    int candidate_ = -1;
    float captureProgress_ = 0.0f;

    float randomSigned() {
        const auto bits = static_cast<std::uint32_t>(random_() >> 40);
        const float fraction = mul(static_cast<float>(bits),
                                   0.000000059604644775390625f);
        return add(add(fraction, fraction), -1.0f);
    }

    void spawn(int team, float spread) {
        const float y = mul(randomSigned(), 44.0f);
        const float x = add(mul(randomSigned(), spread),
                            team == 0 ? -44.0f : 44.0f);
        if (free_.empty()) {
            return;
        }

        const int index = free_.back();
        free_.pop_back();

        Unit& unit = units_[index];
        unit.x = x;
        unit.y = y;
        unit.health = 100;
        unit.team = team;
        unit.alive = true;
    }

    void updateControlPoint() {
        std::array<int, 2> nearby{};
        for (const Unit& unit : units_) {
            if (unit.alive && distanceSquared(unit.x, unit.y) < 36.0f) {
                ++nearby[unit.team];
            }
        }

        if ((nearby[0] > 0) != (nearby[1] > 0)) {
            const int team = nearby[0] > 0 ? 0 : 1;
            if (candidate_ != team) {
                candidate_ = team;
                captureProgress_ = 0.0f;
            }
            captureProgress_ = add(captureProgress_, 0.00390625f);
            if (captureProgress_ >= 1.0f) {
                owner_ = team;
                captureProgress_ = 0.0f;
            }
        }

        if (owner_ >= 0) {
            ++scores_[owner_];
        }
    }
};

void printGraph() {
    static constexpr char graph[] =
        "GRAPH trigram_sets 01/01: teleology team reverse | teleology progress team | teleology reverse remove\n"
        "GRAPH full_graph 01/06: teleology team teleology reverse teleology team reverse teleology team teleology teleology reverse team teleology reverse teleology teleology reverse teleology team\n"
        "GRAPH full_graph 02/06: teleology reverse team teleology reverse teleology teleology team reverse teleology team teleology reverse teleology reverse team teleology progress teleology team\n"
        "GRAPH full_graph 03/06: teleology progress team teleology progress teleology teleology team progress teleology team teleology teleology team teleology progress teleology team progress\n"
        "GRAPH full_graph 04/06: teleology team teleology teleology progress team teleology progress teleology team teleology team progress teleology reverse teleology remove teleology reverse remove\n"
        "GRAPH full_graph 05/06: teleology reverse teleology teleology remove reverse teleology remove teleology teleology remove teleology reverse teleology remove reverse teleology remove teleology\n"
        "GRAPH full_graph 06/06: teleology reverse remove teleology reverse teleology remove teleology remove reverse\n"
        "GRAPH full_graph_directed 01/06: teleology>team teleology>reverse teleology>team reverse>teleology team>teleology teleology>reverse team>teleology reverse>teleology teleology>reverse\n"
        "GRAPH full_graph_directed 02/06: teleology>team teleology>reverse team>teleology reverse>teleology teleology>team reverse>teleology team>teleology reverse>teleology reverse>team ;\n"
        "GRAPH full_graph_directed 03/06: teleology>progress teleology>team teleology>progress team>teleology progress>teleology teleology>team progress>teleology team>teleology teleology>team\n"
        "GRAPH full_graph_directed 04/06: teleology>progress teleology>team progress>teleology team>teleology teleology>progress team>teleology progress>teleology team>teleology team>progress ;\n"
        "GRAPH full_graph_directed 05/06: teleology>reverse teleology>remove teleology>reverse remove>teleology reverse>teleology teleology>remove reverse>teleology remove>teleology teleology>remove\n"
        "GRAPH full_graph_directed 06/06: teleology>reverse teleology>remove reverse>teleology remove>teleology teleology>reverse remove>teleology reverse>teleology remove>teleology remove>reverse\n";
    std::fputs(graph, stdout);
}

} // namespace

int main(int argc, char** argv) {
    printGraph();

    const int ticks = argc > 1 ? std::atoi(argv[1]) : 4096;
    const std::uint64_t seed = argc > 2
        ? static_cast<std::uint64_t>(std::strtoull(argv[2], nullptr, 10))
        : UINT64_C(42);

    Simulation simulation(seed);
    for (int tick = 0; tick < ticks; ++tick) {
        simulation.step(tick);
        const int completed = tick + 1;
        if (completed % 512 == 0) {
            std::printf(
                "tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n",
                completed,
                simulation.aliveCount(0),
                simulation.aliveCount(1),
                simulation.score(0),
                simulation.score(1),
                simulation.owner());
        }
    }

    std::printf(
        "SUMMARY teleology progress team ticks=%d seed=%llu "
        "alive0=%d alive1=%d score0=%d score1=%d owner=%d checksum=%016llx\n",
        ticks,
        static_cast<unsigned long long>(seed),
        simulation.aliveCount(0),
        simulation.aliveCount(1),
        simulation.score(0),
        simulation.score(1),
        simulation.owner(),
        static_cast<unsigned long long>(simulation.checksum()));
    return 0;
}
```