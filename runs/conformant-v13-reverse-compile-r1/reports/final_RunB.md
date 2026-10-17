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

// Preserve the executable's separate single-precision operations.
float add(float a, float b) {
    volatile float result = a + b;
    return result;
}

float subtract(float a, float b) {
    volatile float result = a - b;
    return result;
}

float multiply(float a, float b) {
    volatile float result = a * b;
    return result;
}

float divide(float a, float b) {
    volatile float result = a / b;
    return result;
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
            const float angle = multiply(
                multiply(static_cast<float>(i), 0.6180340051651001f),
                6.2831854820251465f);
            destinations_[i].x = multiply(std::cos(angle), 3.0f);
            destinations_[i].y = multiply(std::sin(angle), 3.0f);
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

        // Reinforcements arrive after the update at zero-based tick 512,
        // not before the progress line for completed tick 512.
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

    int score(int team) const {
        return scores_[team];
    }

    int owner() const {
        return owner_;
    }

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(1469598103934665603);
        for (const Unit& unit : units_) {
            if (!unit.alive) {
                continue;
            }
            hashCoordinate(hash, unit.x);
            hashCoordinate(hash, unit.y);
        }
        return hash;
    }

private:
    static constexpr int capacity = 1024;

    std::array<Unit, capacity> units_{};
    std::array<Point, capacity> destinations_{};
    std::vector<int> free_;
    std::mt19937_64 random_;
    std::array<int, 2> scores_{{0, 0}};
    int owner_ = -1;
    int capturingTeam_ = -1;
    float captureProgress_ = 0.0f;

    float uniform() {
        const auto bits = static_cast<std::uint32_t>(random_() >> 40);
        const float fraction =
            multiply(static_cast<float>(bits), 0.000000059604644775390625f);
        return add(multiply(fraction, 2.0f), -1.0f);
    }

    void spawn(int team, float spread) {
        const float y = multiply(uniform(), 44.0f);
        const float x =
            add(team == 0 ? -44.0f : 44.0f, multiply(uniform(), spread));

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

    static float clampPosition(float value) {
        if (value > 48.0f) {
            value = 48.0f;
        }
        if (value < -48.0f) {
            value = -48.0f;
        }
        return value;
    }

    void move() {
        for (int i = 0; i < capacity; ++i) {
            Unit& unit = units_[i];
            if (!unit.alive) {
                continue;
            }

            const float dx = subtract(destinations_[i].x, unit.x);
            const float dy = subtract(destinations_[i].y, unit.y);
            const float squaredDistance =
                add(multiply(dy, dy), multiply(dx, dx));
            const float distance = std::sqrt(squaredDistance);

            float vx = 0.0f;
            float vy = 0.0f;
            if (distance > 0.0001f) {
                vx = multiply(divide(dx, distance), 6.0f);
                vy = multiply(divide(dy, distance), 6.0f);
            }

            unit.x = clampPosition(
                add(unit.x, multiply(vx, 0.015625f)));
            unit.y = clampPosition(
                add(unit.y, multiply(vy, 0.015625f)));
        }
    }

    void fight() {
        for (int i = 0; i < capacity; ++i) {
            Unit& first = units_[i];
            if (!first.alive) {
                continue;
            }

            for (int j = i + 1; j < capacity; ++j) {
                Unit& second = units_[j];
                if (!second.alive || first.team == second.team) {
                    continue;
                }

                const float dx = subtract(second.x, first.x);
                const float dy = subtract(second.y, first.y);
                const float squaredDistance =
                    add(multiply(dy, dy), multiply(dx, dx));

                if (squaredDistance < 2.25f) {
                    first.health -= 6;
                    second.health -= 6;
                }
            }
        }

        // Resolve all deaths together, in ascending slot order.
        for (int i = 0; i < capacity; ++i) {
            Unit& unit = units_[i];
            if (unit.alive && unit.health <= 0) {
                unit.alive = false;
                free_.push_back(i);
            }
        }
    }

    void updateControlPoint() {
        std::array<int, 2> nearby{{0, 0}};
        for (const Unit& unit : units_) {
            if (!unit.alive) {
                continue;
            }

            const float squaredDistance =
                add(multiply(unit.y, unit.y), multiply(unit.x, unit.x));
            if (squaredDistance < 36.0f) {
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

    static void hashCoordinate(std::uint64_t& hash, float coordinate) {
        const std::int32_t quantized =
            static_cast<std::int32_t>(multiply(coordinate, 1000.0f));
        const std::uint32_t bits = static_cast<std::uint32_t>(quantized);

        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= static_cast<std::uint8_t>(bits >> shift);
            hash *= UINT64_C(1099511628211);
        }
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
            std::printf(
                "tick %5d alive %3d v %3d score %d-%d "
                "cp owner %d team progress\n",
                tick + 1,
                simulation.aliveCount(0),
                simulation.aliveCount(1),
                simulation.score(0),
                simulation.score(1),
                simulation.owner());
        }
    }

    std::printf(
        "SUMMARY teleology progress team ticks=%d seed=%llu "
        "alive0=%d alive1=%d score0=%d score1=%d owner=%d "
        "checksum=%016llx\n",
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