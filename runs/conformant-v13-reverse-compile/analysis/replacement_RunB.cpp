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

// Preserve the individual single-precision operations of the executable.
float rounded(float value) {
    volatile float result = value;
    return result;
}

float add(float a, float b) { return rounded(a + b); }
float subtract(float a, float b) { return rounded(a - b); }
float multiply(float a, float b) { return rounded(a * b); }
float divide(float a, float b) { return rounded(a / b); }

float squaredLength(float x, float y) {
    return add(multiply(y, y), multiply(x, x));
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
        active_.reserve(capacity);

        for (int i = capacity - 1; i >= 0; --i) {
            free_.push_back(i);
        }

        for (int i = 0; i < capacity; ++i) {
            const float angle = multiply(
                multiply(static_cast<float>(i), 0.6180340051651001f),
                6.2831854820251465f);
            const float cosine = rounded(
                static_cast<float>(std::cos(static_cast<double>(angle))));
            const float sine = rounded(
                static_cast<float>(std::sin(static_cast<double>(angle))));
            destinations_[i] = {
                multiply(cosine, 3.0f),
                multiply(sine, 3.0f)
            };
        }

        for (int i = 0; i < 64; ++i) {
            spawnRandom(0, 4.0f);
            spawnRandom(1, 4.0f);
        }
    }

    void step(int tick) {
        active_.clear();
        for (int i = 0; i < capacity; ++i) {
            if (units_[i].alive) {
                active_.push_back(i);
            }
        }

        move();
        fight();
        updateControlPoint();

        if (tick != 0 && tick % 512 == 0) {
            for (int team = 0; team < 2; ++team) {
                if (aliveCount(team) < 96) {
                    for (int i = 0; i < 8; ++i) {
                        spawnRandom(team, 6.0f);
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

            const auto x = static_cast<std::int32_t>(
                multiply(unit.x, 1000.0f));
            const auto y = static_cast<std::int32_t>(
                multiply(unit.y, 1000.0f));
            hashInteger(hash, x);
            hashInteger(hash, y);
        }
        return hash;
    }

    void printProgress(int tick) const {
        std::printf(
            "tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n",
            tick, aliveCount(0), aliveCount(1),
            scores_[0], scores_[1], owner_);
    }

private:
    static constexpr int capacity = 1024;

    std::array<Unit, capacity> units_{};
    std::array<Point, capacity> destinations_{};
    std::vector<int> free_;
    std::vector<int> active_;
    std::mt19937_64 random_;
    std::array<int, 2> scores_{};
    int owner_ = -1;
    int capturingTeam_ = -1;
    float captureProgress_ = 0.0f;

    float uniformSigned() {
        const auto bits = static_cast<std::uint32_t>(random_() >> 40);
        const float fraction = multiply(
            static_cast<float>(bits), 0.000000059604644775390625f);
        return add(multiply(2.0f, fraction), -1.0f);
    }

    void spawnRandom(int team, float spread) {
        // The vertical coordinate consumes the first random sample.
        const float y = multiply(uniformSigned(), 44.0f);
        const float offset = multiply(uniformSigned(), spread);
        const float x = add(team == 0 ? -44.0f : 44.0f, offset);

        if (free_.empty()) {
            return;
        }

        const int index = free_.back();
        free_.pop_back();
        units_[index] = Unit{x, y, 100, team, true};
    }

    void move() {
        for (int index : active_) {
            Unit& unit = units_[index];
            const Point& destination = destinations_[index];
            const float dx = subtract(destination.x, unit.x);
            const float dy = subtract(destination.y, unit.y);
            const float distance = rounded(static_cast<float>(
                std::sqrt(static_cast<double>(squaredLength(dx, dy)))));

            float vx = 0.0f;
            float vy = 0.0f;
            if (distance > 0.0001f) {
                vx = multiply(divide(dx, distance), 6.0f);
                vy = multiply(divide(dy, distance), 6.0f);
            }

            unit.x = std::clamp(
                add(unit.x, multiply(vx, 0.015625f)), -48.0f, 48.0f);
            unit.y = std::clamp(
                add(unit.y, multiply(vy, 0.015625f)), -48.0f, 48.0f);
        }
    }

    void fight() {
        // Damage is accumulated for every pair before any deaths are applied.
        for (std::size_t i = 0; i < active_.size(); ++i) {
            Unit& first = units_[active_[i]];
            for (std::size_t j = i + 1; j < active_.size(); ++j) {
                Unit& second = units_[active_[j]];
                if (first.team == second.team) {
                    continue;
                }

                const float dx = subtract(second.x, first.x);
                const float dy = subtract(second.y, first.y);
                if (squaredLength(dx, dy) < 2.25f) {
                    first.health -= 6;
                    second.health -= 6;
                }
            }
        }

        // Ascending retirement order determines subsequent allocation order.
        for (int index : active_) {
            Unit& unit = units_[index];
            if (unit.health <= 0) {
                unit.alive = false;
                free_.push_back(index);
            }
        }
    }

    void updateControlPoint() {
        std::array<int, 2> nearby{};
        for (const Unit& unit : units_) {
            if (unit.alive && squaredLength(unit.x, unit.y) < 36.0f) {
                ++nearby[unit.team];
            }
        }

        if ((nearby[0] > 0) != (nearby[1] > 0)) {
            const int team = nearby[0] > 0 ? 0 : 1;
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

    static void hashInteger(std::uint64_t& hash, std::int32_t value) {
        const std::uint32_t bits = static_cast<std::uint32_t>(value);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= static_cast<std::uint64_t>((bits >> shift) & 0xffu);
            hash *= UINT64_C(0x100000001b3);
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
            simulation.printProgress(tick + 1);
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
