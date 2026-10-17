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

// Preserve the original program's single-precision operation boundaries.
float rounded(float value) {
    volatile float result = value;
    return result;
}

float add(float a, float b) { return rounded(a + b); }
float subtract(float a, float b) { return rounded(a - b); }
float multiply(float a, float b) { return rounded(a * b); }
float divide(float a, float b) { return rounded(a / b); }

float squaredLength(float x, float y) {
    return add(multiply(x, x), multiply(y, y));
}

float clampPosition(float value) {
    if (value > 48.0f) value = 48.0f;
    if (value < -48.0f) value = -48.0f;
    return value;
}

struct Unit {
    float x = 0.0f;
    float y = 0.0f;
    int health = 0;
    int team = 0;
    bool alive = false;
};

struct Destination {
    float x = 0.0f;
    float y = 0.0f;
};

class Simulation {
public:
    explicit Simulation(std::uint64_t seed) : random_(seed) {
        freeSlots_.reserve(capacity);
        for (int i = capacity - 1; i >= 0; --i)
            freeSlots_.push_back(i);

        for (int i = 0; i < capacity; ++i) {
            const float angle = multiply(
                multiply(static_cast<float>(i), 0.618034f),
                6.283185482025146484375f);
            const float cosine = rounded(static_cast<float>(
                std::cos(static_cast<double>(angle))));
            const float sine = rounded(static_cast<float>(
                std::sin(static_cast<double>(angle))));
            destinations_[i] = {
                multiply(cosine, 3.0f),
                multiply(sine, 3.0f)
            };
        }

        for (int i = 0; i < 64; ++i) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    void step(int tick) {
        move();
        combat();
        updateControlPoint();

        // Reinforcements arrive on zero-based ticks 512, 1024, ...
        if (tick != 0 && tick % 512 == 0) {
            for (int team = 0; team < 2; ++team) {
                if (aliveCount(team) < 96) {
                    for (int i = 0; i < 8; ++i)
                        spawn(team, 6.0f);
                }
            }
        }
    }

    int aliveCount(int team) const {
        int count = 0;
        for (const Unit& unit : units_) {
            if (unit.alive && unit.team == team)
                ++count;
        }
        return count;
    }

    int score(int team) const { return scores_[team]; }
    int owner() const { return owner_; }

    std::uint64_t checksum() const {
        std::uint64_t hash = 0x14650fb0739d0383ULL;
        for (const Unit& unit : units_) {
            if (!unit.alive)
                continue;

            const auto x = static_cast<std::int32_t>(
                multiply(unit.x, 1000.0f));
            const auto y = static_cast<std::int32_t>(
                multiply(unit.y, 1000.0f));
            hashInteger(hash, x);
            hashInteger(hash, y);
        }
        return hash;
    }

private:
    static constexpr int capacity = 1024;

    std::array<Unit, capacity> units_{};
    std::array<Destination, capacity> destinations_{};
    std::vector<int> freeSlots_;
    std::mt19937_64 random_;
    std::array<int, 2> scores_{};
    int owner_ = -1;
    int claimant_ = -1;
    float captureProgress_ = 0.0f;

    float uniformSigned() {
        const std::uint64_t bits = random_() >> 40;
        const float fraction = multiply(
            static_cast<float>(bits), 1.0f / 16777216.0f);
        return add(multiply(2.0f, fraction), -1.0f);
    }

    void spawn(int team, float horizontalSpread) {
        // The vertical coordinate consumes the first random draw.
        const float y = multiply(uniformSigned(), 44.0f);
        const float displacement = multiply(
            uniformSigned(), horizontalSpread);
        const float x = add(
            team == 0 ? -44.0f : 44.0f, displacement);

        if (freeSlots_.empty())
            return;

        const int index = freeSlots_.back();
        freeSlots_.pop_back();
        units_[index] = Unit{x, y, 100, team, true};
    }

    void move() {
        for (int i = 0; i < capacity; ++i) {
            Unit& unit = units_[i];
            if (!unit.alive)
                continue;

            const float dx = subtract(destinations_[i].x, unit.x);
            const float dy = subtract(destinations_[i].y, unit.y);
            const float distanceSquared = squaredLength(dx, dy);
            const float distance = rounded(static_cast<float>(
                std::sqrt(static_cast<double>(distanceSquared))));

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

    void combat() {
        for (int i = 0; i < capacity; ++i) {
            Unit& first = units_[i];
            if (!first.alive)
                continue;

            for (int j = i + 1; j < capacity; ++j) {
                Unit& second = units_[j];
                if (!second.alive || first.team == second.team)
                    continue;

                const float dx = subtract(second.x, first.x);
                const float dy = subtract(second.y, first.y);
                if (squaredLength(dx, dy) < 2.25f) {
                    first.health -= 6;
                    second.health -= 6;
                }
            }
        }

        // Deaths are applied only after all pairwise damage is accumulated.
        for (int i = 0; i < capacity; ++i) {
            Unit& unit = units_[i];
            if (unit.alive && unit.health <= 0) {
                unit.alive = false;
                freeSlots_.push_back(i);
            }
        }
    }

    void updateControlPoint() {
        std::array<int, 2> inside{};
        for (const Unit& unit : units_) {
            if (unit.alive && squaredLength(unit.x, unit.y) < 36.0f)
                ++inside[unit.team];
        }

        const bool teamZeroPresent = inside[0] > 0;
        const bool teamOnePresent = inside[1] > 0;

        if (teamZeroPresent != teamOnePresent) {
            const int team = teamZeroPresent ? 0 : 1;
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

        if (owner_ >= 0)
            ++scores_[owner_];
    }

    static void hashInteger(std::uint64_t& hash, std::int32_t value) {
        const auto bits = static_cast<std::uint32_t>(value);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= static_cast<std::uint64_t>((bits >> shift) & 0xffU);
            hash *= 0x100000001b3ULL;
        }
    }
};

} // namespace

int main(int argc, char** argv) {
    const int ticks = argc > 1 ? std::atoi(argv[1]) : 4096;
    const std::uint64_t seed = argc > 2
        ? static_cast<std::uint64_t>(std::strtoull(argv[2], nullptr, 10))
        : 42ULL;

    Simulation simulation(seed);

    for (int tick = 0; tick < ticks; ++tick) {
        simulation.step(tick);
        if ((tick + 1) % 512 == 0) {
            std::printf(
                "tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n",
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