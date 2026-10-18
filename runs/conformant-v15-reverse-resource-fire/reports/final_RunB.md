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
float subtract(float a, float b) { return rounded(a - b); }
float multiply(float a, float b) { return rounded(a * b); }
float divide(float a, float b) { return rounded(a / b); }

struct Unit {
    float x = 0.0f;
    float y = 0.0f;
    int health = 0;
    int team = 0;
    bool alive = false;
};

class Simulation {
public:
    explicit Simulation(std::uint64_t seed) : random_(seed) {
        free_.reserve(capacity);
        active_.reserve(capacity);

        for (int i = capacity - 1; i >= 0; --i) {
            free_.push_back(i);
        }

        for (int i = 0; i < capacity; ++i) {
            const float angle = multiply(
                multiply(static_cast<float>(i), 0.618034f),
                6.283185307179586f);
            goals_[i][0] = multiply(std::cos(angle), 3.0f);
            goals_[i][1] = multiply(std::sin(angle), 3.0f);
        }

        for (int i = 0; i < 64; ++i) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    void step(int tick) {
        active_.clear();
        for (int i = 0; i < capacity; ++i) {
            if (units_[i].alive) {
                active_.push_back(i);
                move(i);
            }
        }

        // Damage is simultaneous: remove casualties only after all pairs.
        for (std::size_t a = 0; a < active_.size(); ++a) {
            Unit& first = units_[active_[a]];
            for (std::size_t b = a + 1; b < active_.size(); ++b) {
                Unit& second = units_[active_[b]];
                if (first.team == second.team) {
                    continue;
                }

                const float dx = subtract(second.x, first.x);
                const float dy = subtract(second.y, first.y);
                const float distanceSquared =
                    add(multiply(dy, dy), multiply(dx, dx));

                if (distanceSquared < 2.25f) {
                    first.health -= 6;
                    second.health -= 6;
                }
            }
        }

        // Ascending removal order determines subsequent LIFO slot reuse.
        for (int index : active_) {
            Unit& unit = units_[index];
            if (unit.health <= 0) {
                unit.alive = false;
                --counts_[unit.team];
                free_.push_back(index);
            }
        }

        updateControlPoint();

        // The first reinforcement wave occurs during zero-based tick 512.
        if (tick != 0 && tick % 512 == 0) {
            for (int team = 0; team < 2; ++team) {
                if (counts_[team] < 96) {
                    for (int i = 0; i < 8; ++i) {
                        spawn(team, 6.0f);
                    }
                }
            }
        }
    }

    void printProgress(int tick) const {
        std::printf(
            "tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n",
            tick, counts_[0], counts_[1], scores_[0], scores_[1], owner_);
    }

    void printSummary(int ticks, std::uint64_t seed) const {
        std::printf(
            "SUMMARY teleology progress team ticks=%d seed=%llu "
            "alive0=%d alive1=%d score0=%d score1=%d owner=%d "
            "checksum=%016llx\n",
            ticks,
            static_cast<unsigned long long>(seed),
            counts_[0], counts_[1], scores_[0], scores_[1], owner_,
            static_cast<unsigned long long>(checksum()));
    }

private:
    static constexpr int capacity = 1024;

    std::array<Unit, capacity> units_{};
    std::array<std::array<float, 2>, capacity> goals_{};
    std::vector<int> free_;
    std::vector<int> active_;
    std::mt19937_64 random_;
    std::array<int, 2> counts_{};
    std::array<int, 2> scores_{};
    int owner_ = -1;
    int capturingTeam_ = -1;
    float captureProgress_ = 0.0f;

    float randomSigned() {
        const auto bits = static_cast<std::uint32_t>(random_() >> 40);
        const float value =
            multiply(static_cast<float>(bits), 0x1p-24f);
        return add(add(value, value), -1.0f);
    }

    void spawn(int team, float jitter) {
        // Draw the vertical coordinate before the horizontal coordinate.
        const float y = multiply(randomSigned(), 44.0f);
        const float x = add(
            multiply(randomSigned(), jitter),
            team == 0 ? -44.0f : 44.0f);

        if (free_.empty()) {
            return;
        }

        const int index = free_.back();
        free_.pop_back();
        units_[index] = Unit{x, y, 100, team, true};
        ++counts_[team];
    }

    void move(int index) {
        Unit& unit = units_[index];

        const float dx = subtract(goals_[index][0], unit.x);
        const float dy = subtract(goals_[index][1], unit.y);
        const float distanceSquared =
            add(multiply(dy, dy), multiply(dx, dx));
        const float distance = rounded(std::sqrt(distanceSquared));

        float vx = 0.0f;
        float vy = 0.0f;
        if (distance > 0.0001f) {
            vx = multiply(divide(dx, distance), 6.0f);
            vy = multiply(divide(dy, distance), 6.0f);
        }

        unit.x = add(unit.x, multiply(vx, 0.015625f));
        unit.y = add(unit.y, multiply(vy, 0.015625f));
        unit.x = std::max(-48.0f, std::min(48.0f, unit.x));
        unit.y = std::max(-48.0f, std::min(48.0f, unit.y));
    }

    void updateControlPoint() {
        std::array<int, 2> nearby{};
        for (const Unit& unit : units_) {
            if (!unit.alive) {
                continue;
            }

            const float distanceSquared = add(
                multiply(unit.y, unit.y), multiply(unit.x, unit.x));
            if (distanceSquared < 36.0f) {
                ++nearby[unit.team];
            }
        }

        const bool firstPresent = nearby[0] > 0;
        const bool secondPresent = nearby[1] > 0;

        if (firstPresent != secondPresent) {
            const int team = firstPresent ? 0 : 1;
            if (capturingTeam_ != team) {
                capturingTeam_ = team;
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

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(1469598103934665603);
        constexpr std::uint64_t prime = UINT64_C(1099511628211);

        for (const Unit& unit : units_) {
            if (!unit.alive) {
                continue;
            }

            const std::array<float, 2> coordinates{unit.x, unit.y};
            for (float coordinate : coordinates) {
                const auto signedValue = static_cast<std::int32_t>(
                    multiply(coordinate, 1000.0f));
                const auto value = static_cast<std::uint32_t>(signedValue);

                for (unsigned shift = 0; shift < 32; shift += 8) {
                    hash ^= (value >> shift) & 0xffu;
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
    const std::uint64_t seed = argc > 2
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