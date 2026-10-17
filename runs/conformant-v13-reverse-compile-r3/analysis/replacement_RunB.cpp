// replacement.cpp
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

namespace {

constexpr int Capacity = 1024;

// Preserve the scalar single-precision rounding of the executable.
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

float squaredDistance(float dx, float dy) {
    return add(multiply(dx, dx), multiply(dy, dy));
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
        freeSlots_.reserve(Capacity);
        active_.reserve(Capacity);

        for (int i = Capacity - 1; i >= 0; --i) {
            freeSlots_.push_back(i);
        }

        for (int i = 0; i < Capacity; ++i) {
            const float angle = multiply(
                multiply(static_cast<float>(i), 0.618034f),
                6.283185482025146484375f
            );

            const float cosine =
                static_cast<float>(std::cos(static_cast<double>(angle)));
            const float sine =
                static_cast<float>(std::sin(static_cast<double>(angle)));

            goals_[i].x = multiply(cosine, 3.0f);
            goals_[i].y = multiply(sine, 3.0f);
        }

        for (int i = 0; i < 64; ++i) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    void step(int tick) {
        active_.clear();
        for (int i = 0; i < Capacity; ++i) {
            if (units_[i].alive) active_.push_back(i);
        }

        move();
        fight();
        updateControlPoint();

        // Reinforcement scheduling uses the zero-based tick number.
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

    void printProgress(int tick) const {
        std::printf(
            "tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n",
            tick, aliveCount(0), aliveCount(1),
            scores_[0], scores_[1], owner_
        );
    }

    void printSummary(int ticks, std::uint64_t seed) const {
        std::printf(
            "SUMMARY teleology progress team ticks=%d seed=%llu "
            "alive0=%d alive1=%d score0=%d score1=%d owner=%d "
            "checksum=%016llx\n",
            ticks,
            static_cast<unsigned long long>(seed),
            aliveCount(0), aliveCount(1),
            scores_[0], scores_[1], owner_,
            static_cast<unsigned long long>(checksum())
        );
    }

private:
    float uniformSigned() {
        const std::uint64_t top24 = random_() >> 40;
        const float fraction =
            multiply(static_cast<float>(top24), 0x1p-24f);
        return add(multiply(2.0f, fraction), -1.0f);
    }

    void spawn(int team, float spread) {
        // The y-coordinate consumes the first random draw.
        const float y = multiply(uniformSigned(), 44.0f);
        const float offset = multiply(uniformSigned(), spread);
        const float x = add(team == 0 ? -44.0f : 44.0f, offset);

        if (freeSlots_.empty()) return;

        const int index = freeSlots_.back();
        freeSlots_.pop_back();

        Unit& unit = units_[index];
        unit.x = x;
        unit.y = y;
        unit.health = 100;
        unit.team = team;
        unit.alive = true;
    }

    void move() {
        for (int index : active_) {
            Unit& unit = units_[index];
            const float dx = subtract(goals_[index].x, unit.x);
            const float dy = subtract(goals_[index].y, unit.y);
            const float distance = static_cast<float>(
                std::sqrt(static_cast<double>(squaredDistance(dx, dy)))
            );

            float vx = 0.0f;
            float vy = 0.0f;

            if (distance > 0.0001f) {
                vx = multiply(divide(dx, distance), 6.0f);
                vy = multiply(divide(dy, distance), 6.0f);
            }

            unit.x = clampPosition(
                add(unit.x, multiply(vx, 0.015625f))
            );
            unit.y = clampPosition(
                add(unit.y, multiply(vy, 0.015625f))
            );
        }
    }

    void fight() {
        for (std::size_t a = 0; a < active_.size(); ++a) {
            Unit& first = units_[active_[a]];

            for (std::size_t b = a + 1; b < active_.size(); ++b) {
                Unit& second = units_[active_[b]];
                if (first.team == second.team) continue;

                const float dx = subtract(second.x, first.x);
                const float dy = subtract(second.y, first.y);

                if (squaredDistance(dx, dy) < 2.25f) {
                    first.health -= 6;
                    second.health -= 6;
                }
            }
        }

        // Deaths are processed after every pair has exchanged damage.
        // The ascending removal order determines subsequent slot reuse.
        for (int index : active_) {
            Unit& unit = units_[index];
            if (unit.health <= 0) {
                unit.alive = false;
                freeSlots_.push_back(index);
            }
        }
    }

    void updateControlPoint() {
        std::array<int, 2> nearby{};

        for (const Unit& unit : units_) {
            if (unit.alive &&
                squaredDistance(unit.x, unit.y) < 36.0f) {
                ++nearby[unit.team];
            }
        }

        const bool present0 = nearby[0] > 0;
        const bool present1 = nearby[1] > 0;

        if (present0 != present1) {
            const int team = present0 ? 0 : 1;

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

        // Empty or contested control points retain their capture state.
        if (owner_ >= 0) {
            ++scores_[owner_];
        }
    }

    int aliveCount(int team) const {
        int count = 0;
        for (const Unit& unit : units_) {
            if (unit.alive && unit.team == team) ++count;
        }
        return count;
    }

    static void hashInteger(std::uint64_t& hash, std::int32_t value) {
        const std::uint32_t bits = static_cast<std::uint32_t>(value);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= static_cast<std::uint8_t>(bits >> shift);
            hash *= UINT64_C(0x100000001b3);
        }
    }

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(0x14650fb0739d0383);

        for (const Unit& unit : units_) {
            if (!unit.alive) continue;

            const std::int32_t x = static_cast<std::int32_t>(
                multiply(unit.x, 1000.0f)
            );
            const std::int32_t y = static_cast<std::int32_t>(
                multiply(unit.y, 1000.0f)
            );

            hashInteger(hash, x);
            hashInteger(hash, y);
        }

        return hash;
    }

    std::mt19937_64 random_;
    std::array<Unit, Capacity> units_{};
    std::array<Point, Capacity> goals_{};
    std::vector<int> freeSlots_;
    std::vector<int> active_;
    std::array<int, 2> scores_{};
    int owner_ = -1;
    int candidate_ = -1;
    float captureProgress_ = 0.0f;
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
