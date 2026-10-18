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

// Keep the simulation's intermediate arithmetic at binary32 precision.
float rounded(float value) {
    volatile float result = value;
    return result;
}

float add(float a, float b) { return rounded(a + b); }
float subtract(float a, float b) { return rounded(a - b); }
float multiply(float a, float b) { return rounded(a * b); }
float divide(float a, float b) { return rounded(a / b); }

float squaredDistance(float dx, float dy) {
    return add(multiply(dy, dy), multiply(dx, dx));
}

float clampPosition(float value) {
    if (value > 48.0f) return 48.0f;
    if (value < -48.0f) return -48.0f;
    return value;
}

constexpr const char* banner =
R"(GRAPH trigram_sets 01/01: hainish team reverse | hainish progress team | hainish reverse remove
GRAPH full_graph 01/05: hainish team hainish reverse hainish team reverse hainish team hainish hainish reverse team hainish reverse hainish hainish reverse hainish team hainish reverse team
GRAPH full_graph 02/05: hainish reverse hainish hainish team reverse hainish team hainish reverse hainish reverse team hainish progress hainish team hainish progress team hainish progress
GRAPH full_graph 03/05: hainish hainish team progress hainish team hainish hainish team hainish progress hainish team progress hainish team hainish hainish progress team hainish progress
GRAPH full_graph 04/05: hainish team hainish team progress hainish reverse hainish remove hainish reverse remove hainish reverse hainish hainish remove reverse hainish remove hainish hainish
GRAPH full_graph 05/05: remove hainish reverse hainish remove reverse hainish remove hainish hainish reverse remove hainish reverse hainish remove hainish remove reverse
GRAPH full_graph_directed 01/06: hainish>team hainish>reverse hainish>team reverse>hainish team>hainish hainish>reverse team>hainish reverse>hainish hainish>reverse hainish>team
GRAPH full_graph_directed 02/06: hainish>reverse team>hainish reverse>hainish hainish>team reverse>hainish team>hainish reverse>hainish reverse>team ; hainish>progress hainish>team
GRAPH full_graph_directed 03/06: hainish>progress team>hainish progress>hainish hainish>team progress>hainish team>hainish hainish>team hainish>progress hainish>team progress>hainish
GRAPH full_graph_directed 04/06: team>hainish hainish>progress team>hainish progress>hainish team>hainish team>progress ; hainish>reverse hainish>remove hainish>reverse remove>hainish
GRAPH full_graph_directed 05/06: reverse>hainish hainish>remove reverse>hainish remove>hainish hainish>remove hainish>reverse hainish>remove reverse>hainish remove>hainish hainish>reverse
GRAPH full_graph_directed 06/06: remove>hainish reverse>hainish remove>hainish remove>reverse
)";

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
        active_.reserve(capacity);

        for (int i = capacity - 1; i >= 0; --i) {
            freeSlots_.push_back(i);
        }

        for (int i = 0; i < capacity; ++i) {
            const float angle = multiply(
                multiply(static_cast<float>(i), 0.6180340051651001f),
                6.2831854820251465f);
            const float cosine =
                rounded(static_cast<float>(std::cos(static_cast<double>(angle))));
            const float sine =
                rounded(static_cast<float>(std::sin(static_cast<double>(angle))));
            goals_[i] = {multiply(cosine, 3.0f), multiply(sine, 3.0f)};
        }

        for (int i = 0; i < 64; ++i) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    void step(int tick) {
        active_.clear();
        for (int i = 0; i < capacity; ++i) {
            if (units_[i].alive) active_.push_back(i);
        }

        move();
        fight();
        updateControlPoint();

        // The first replenishment occurs during zero-based tick 512.
        if (tick > 0 && tick % 512 == 0) {
            for (int team = 0; team < 2; ++team) {
                if (count(team) < 96) {
                    for (int i = 0; i < 8; ++i) spawn(team, 6.0f);
                }
            }
        }
    }

    int count(int team) const {
        int result = 0;
        for (const Unit& unit : units_) {
            if (unit.alive && unit.team == team) ++result;
        }
        return result;
    }

    int score(int team) const { return scores_[team]; }
    int owner() const { return owner_; }

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(0x14650fb0739d0383);
        for (const Unit& unit : units_) {
            if (!unit.alive) continue;
            hashCoordinate(hash, unit.x);
            hashCoordinate(hash, unit.y);
        }
        return hash;
    }

private:
    static constexpr int capacity = 1024;
    std::array<Unit, capacity> units_{};
    std::array<Point, capacity> goals_{};
    std::vector<int> freeSlots_;
    std::vector<int> active_;
    std::mt19937_64 random_;
    std::array<int, 2> scores_{};
    int owner_ = -1;
    int candidate_ = -1;
    float captureProgress_ = 0.0f;

    float uniform() {
        return multiply(static_cast<float>(random_() >> 40),
                        5.9604644775390625e-8f);
    }

    float symmetricRandom() {
        const float value = uniform();
        return add(add(value, value), -1.0f);
    }

    void spawn(int team, float spread) {
        // Random draws occur in y, x order.
        const float y = multiply(symmetricRandom(), 44.0f);
        const float offset = multiply(symmetricRandom(), spread);
        const float x = add(offset, team == 0 ? -44.0f : 44.0f);

        if (freeSlots_.empty()) return;
        const int slot = freeSlots_.back();
        freeSlots_.pop_back();
        units_[slot] = Unit{x, y, 100, team, true};
    }

    void move() {
        for (int slot : active_) {
            Unit& unit = units_[slot];
            const float dx = subtract(goals_[slot].x, unit.x);
            const float dy = subtract(goals_[slot].y, unit.y);
            const float distance = rounded(static_cast<float>(
                std::sqrt(static_cast<double>(squaredDistance(dx, dy)))));

            float vx = 0.0f;
            float vy = 0.0f;
            if (distance > 0.00009999999747378752f) {
                vx = multiply(divide(dx, distance), 6.0f);
                vy = multiply(divide(dy, distance), 6.0f);
            }

            unit.x = clampPosition(add(unit.x, multiply(vx, 0.015625f)));
            unit.y = clampPosition(add(unit.y, multiply(vy, 0.015625f)));
        }
    }

    void fight() {
        for (std::size_t i = 0; i < active_.size(); ++i) {
            Unit& a = units_[active_[i]];
            for (std::size_t j = i + 1; j < active_.size(); ++j) {
                Unit& b = units_[active_[j]];
                if (a.team == b.team) continue;

                const float dx = subtract(b.x, a.x);
                const float dy = subtract(b.y, a.y);
                if (squaredDistance(dx, dy) < 2.25f) {
                    a.health -= 6;
                    b.health -= 6;
                }
            }
        }

        // Deaths are processed only after every pair has exchanged damage.
        // Ascending removal order determines subsequent LIFO slot reuse.
        for (int slot : active_) {
            Unit& unit = units_[slot];
            if (unit.health <= 0) {
                unit.alive = false;
                freeSlots_.push_back(slot);
            }
        }
    }

    void updateControlPoint() {
        std::array<int, 2> inside{};
        for (const Unit& unit : units_) {
            if (unit.alive && squaredDistance(unit.x, unit.y) < 36.0f) {
                ++inside[unit.team];
            }
        }

        if ((inside[0] > 0) != (inside[1] > 0)) {
            const int team = inside[0] > 0 ? 0 : 1;
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

        if (owner_ >= 0) ++scores_[owner_];
    }

    static void hashCoordinate(std::uint64_t& hash, float coordinate) {
        const auto quantized =
            static_cast<std::int32_t>(multiply(coordinate, 1000.0f));
        const auto bits = static_cast<std::uint32_t>(quantized);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= static_cast<std::uint64_t>((bits >> shift) & 0xffu);
            hash *= UINT64_C(0x100000001b3);
        }
    }
};

} // namespace

int main(int argc, char** argv) {
    std::fputs(banner, stdout);

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
                completed, simulation.count(0), simulation.count(1),
                simulation.score(0), simulation.score(1), simulation.owner());
        }
    }

    std::printf(
        "SUMMARY hainish progress team ticks=%d seed=%llu "
        "alive0=%d alive1=%d score0=%d score1=%d owner=%d checksum=%016llx\n",
        ticks, static_cast<unsigned long long>(seed),
        simulation.count(0), simulation.count(1),
        simulation.score(0), simulation.score(1), simulation.owner(),
        static_cast<unsigned long long>(simulation.checksum()));

    return 0;
}
```