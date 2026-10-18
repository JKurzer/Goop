```cpp
// replacement.cpp
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

namespace {

// Preserve the individual single-precision arithmetic steps.
float add(float a, float b) {
    volatile float result = a + b;
    return result;
}

float sub(float a, float b) {
    volatile float result = a - b;
    return result;
}

float mul(float a, float b) {
    volatile float result = a * b;
    return result;
}

float divide(float a, float b) {
    volatile float result = a / b;
    return result;
}

float squareDistance(float dx, float dy) {
    return add(mul(dy, dy), mul(dx, dx));
}

float clampPosition(float value) {
    if (value > 48.0f) return 48.0f;
    if (value < -48.0f) return -48.0f;
    return value;
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
        freeSlots_.reserve(capacity);
        for (int i = capacity - 1; i >= 0; --i) {
            freeSlots_.push_back(i);
        }

        for (int i = 0; i < capacity; ++i) {
            const float angle =
                mul(mul(static_cast<float>(i), 0.6180340051651001f),
                    6.2831854820251465f);

            const float cosine =
                static_cast<float>(std::cos(static_cast<double>(angle)));
            const float sine =
                static_cast<float>(std::sin(static_cast<double>(angle)));

            goals_[i] = {mul(cosine, 3.0f), mul(sine, 3.0f)};
        }

        for (int i = 0; i < 64; ++i) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    void step(int tick) {
        move();
        fight();
        updateControlPoint();

        if (tick > 0 && tick % 512 == 0) {
            for (int team = 0; team < 2; ++team) {
                if (count(team) < 96) {
                    for (int i = 0; i < 8; ++i) {
                        spawn(team, 6.0f);
                    }
                }
            }
        }
    }

    int count(int team) const {
        int result = 0;
        for (const Unit& unit : units_) {
            if (unit.alive && unit.team == team) {
                ++result;
            }
        }
        return result;
    }

    void printProgress(int tick) const {
        std::printf(
            "tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n",
            tick, count(0), count(1), scores_[0], scores_[1], owner_);
    }

    void printSummary(int ticks, std::uint64_t seed) const {
        std::printf(
            "SUMMARY teleology progress team ticks=%d seed=%llu "
            "alive0=%d alive1=%d score0=%d score1=%d owner=%d "
            "checksum=%016llx\n",
            ticks,
            static_cast<unsigned long long>(seed),
            count(0),
            count(1),
            scores_[0],
            scores_[1],
            owner_,
            static_cast<unsigned long long>(checksum()));
    }

private:
    static constexpr int capacity = 1024;

    std::array<Unit, capacity> units_{};
    std::array<Point, capacity> goals_{};
    std::vector<int> freeSlots_;
    std::mt19937_64 random_;
    std::array<int, 2> scores_{{0, 0}};
    int owner_ = -1;
    int claimant_ = -1;
    float captureProgress_ = 0.0f;

    float uniform() {
        const auto top = static_cast<std::uint32_t>(random_() >> 40);
        return mul(static_cast<float>(top), 0x1p-24f);
    }

    float centeredRandom() {
        const float value = uniform();
        return add(add(value, value), -1.0f);
    }

    void spawn(int team, float spread) {
        // The vertical coordinate consumes the first random number.
        const float y = mul(centeredRandom(), 44.0f);
        const float offset = mul(centeredRandom(), spread);
        const float x = add(offset, team == 0 ? -44.0f : 44.0f);

        if (freeSlots_.empty()) return;

        const int index = freeSlots_.back();
        freeSlots_.pop_back();
        units_[index] = Unit{x, y, 100, team, true};
    }

    void move() {
        for (int i = 0; i < capacity; ++i) {
            Unit& unit = units_[i];
            if (!unit.alive) continue;

            const float dx = sub(goals_[i].x, unit.x);
            const float dy = sub(goals_[i].y, unit.y);
            const float squared = squareDistance(dx, dy);
            const float distance =
                static_cast<float>(std::sqrt(static_cast<double>(squared)));

            float vx = 0.0f;
            float vy = 0.0f;
            if (distance > 0.0001f) {
                vx = mul(divide(dx, distance), 6.0f);
                vy = mul(divide(dy, distance), 6.0f);
            }

            unit.x = clampPosition(add(unit.x, mul(vx, 0.015625f)));
            unit.y = clampPosition(add(unit.y, mul(vy, 0.015625f)));
        }
    }

    void fight() {
        std::array<int, capacity> active{};
        int activeCount = 0;

        for (int i = 0; i < capacity; ++i) {
            if (units_[i].alive) active[activeCount++] = i;
        }

        // Damage is simultaneous: removal happens only after all pairs.
        for (int a = 0; a < activeCount; ++a) {
            Unit& first = units_[active[a]];
            for (int b = a + 1; b < activeCount; ++b) {
                Unit& second = units_[active[b]];
                if (first.team == second.team) continue;

                const float dx = sub(second.x, first.x);
                const float dy = sub(second.y, first.y);
                if (squareDistance(dx, dy) < 2.25f) {
                    first.health -= 6;
                    second.health -= 6;
                }
            }
        }

        for (int a = 0; a < activeCount; ++a) {
            const int index = active[a];
            Unit& unit = units_[index];
            if (unit.health <= 0) {
                unit.alive = false;
                freeSlots_.push_back(index);
            }
        }
    }

    void updateControlPoint() {
        std::array<int, 2> nearby{{0, 0}};
        for (const Unit& unit : units_) {
            if (unit.alive && squareDistance(unit.x, unit.y) < 36.0f) {
                ++nearby[unit.team];
            }
        }

        const bool hasZero = nearby[0] > 0;
        const bool hasOne = nearby[1] > 0;

        if (hasZero != hasOne) {
            const int team = hasZero ? 0 : 1;
            if (claimant_ != team) {
                claimant_ = team;
                captureProgress_ = 0.0f;
            }

            captureProgress_ = add(captureProgress_, 0.00390625f);
            if (captureProgress_ >= 1.0f) {
                owner_ = team;
                captureProgress_ = 0.0f;
            }
        }

        if (owner_ >= 0) ++scores_[owner_];
    }

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(0x14650fb0739d0383);
        constexpr std::uint64_t prime = UINT64_C(0x100000001b3);

        for (const Unit& unit : units_) {
            if (!unit.alive) continue;

            const std::array<float, 2> coordinates{{unit.x, unit.y}};
            for (float coordinate : coordinates) {
                const auto quantized =
                    static_cast<std::int32_t>(mul(coordinate, 1000.0f));
                const auto bits = static_cast<std::uint32_t>(quantized);

                for (unsigned shift = 0; shift < 32; shift += 8) {
                    hash ^= static_cast<std::uint64_t>((bits >> shift) & 255u);
                    hash *= prime;
                }
            }
        }

        return hash;
    }
};

} // namespace

int main(int argc, char** argv) {
    const int ticks = argc > 1 ? std::atoi(argv[1]) : 4096;
    const std::uint64_t seed =
        argc > 2
            ? static_cast<std::uint64_t>(std::strtoull(argv[2], nullptr, 10))
            : UINT64_C(42);

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