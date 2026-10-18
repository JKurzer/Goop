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

// Preserve the executable's individual single-precision operations.
float rounded(float value) {
    volatile float result = value;
    return result;
}

float add(float a, float b) { return rounded(a + b); }
float sub(float a, float b) { return rounded(a - b); }
float mul(float a, float b) { return rounded(a * b); }
float divide(float a, float b) { return rounded(a / b); }

float squaredDistance(float dx, float dy) {
    return add(mul(dy, dy), mul(dx, dx));
}

constexpr const char* graphText =
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

struct Particle {
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
            const float angle = mul(
                mul(static_cast<float>(i), 0.618034f),
                6.2831854820251465f);
            const float cosine = rounded(
                static_cast<float>(std::cos(static_cast<double>(angle))));
            const float sine = rounded(
                static_cast<float>(std::sin(static_cast<double>(angle))));
            goals_[i] = {mul(cosine, 3.0f), mul(sine, 3.0f)};
        }

        for (int i = 0; i < 64; ++i) {
            spawn(0, 4.0f);
            spawn(1, 4.0f);
        }
    }

    void step(int tick) {
        active_.clear();
        for (int i = 0; i < capacity; ++i) {
            if (particles_[i].alive) {
                active_.push_back(i);
            }
        }

        move();
        fight();
        removeDead();
        updateControl();

        // The tick passed to replenishment is zero-based.
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
        int result = 0;
        for (const Particle& p : particles_) {
            if (p.alive && p.team == team) {
                ++result;
            }
        }
        return result;
    }

    int score(int team) const { return scores_[team]; }
    int owner() const { return owner_; }

    std::uint64_t checksum() const {
        std::uint64_t hash = UINT64_C(1469598103934665603);
        for (const Particle& p : particles_) {
            if (!p.alive) {
                continue;
            }
            hashCoordinate(hash, p.x);
            hashCoordinate(hash, p.y);
        }
        return hash;
    }

private:
    static constexpr int capacity = 1024;

    std::array<Particle, capacity> particles_{};
    std::array<Point, capacity> goals_{};
    std::vector<int> free_;
    std::vector<int> active_;
    std::mt19937_64 random_;
    std::array<int, 2> scores_{};
    int owner_ = -1;
    int candidate_ = -1;
    float captureProgress_ = 0.0f;

    float randomSigned() {
        const float value = static_cast<float>(random_() >> 40);
        const float unit = mul(value, 0.000000059604644775390625f);
        return add(add(unit, unit), -1.0f);
    }

    void spawn(int team, float width) {
        // The vertical draw precedes the horizontal draw.
        const float y = mul(randomSigned(), 44.0f);
        const float x = add(mul(randomSigned(), width),
                            team == 0 ? -44.0f : 44.0f);
        if (free_.empty()) {
            return;
        }

        const int index = free_.back();
        free_.pop_back();
        Particle& p = particles_[index];
        p.x = x;
        p.y = y;
        p.health = 100;
        p.team = team;
        p.alive = true;
    }

    void move() {
        for (int index : active_) {
            Particle& p = particles_[index];
            const float dx = sub(goals_[index].x, p.x);
            const float dy = sub(goals_[index].y, p.y);
            const float distance = rounded(static_cast<float>(
                std::sqrt(static_cast<double>(squaredDistance(dx, dy)))));

            float vx = 0.0f;
            float vy = 0.0f;
            if (distance > 0.0001f) {
                vx = mul(divide(dx, distance), 6.0f);
                vy = mul(divide(dy, distance), 6.0f);
            }

            p.x = add(p.x, mul(vx, 0.015625f));
            p.y = add(p.y, mul(vy, 0.015625f));
            p.x = std::max(-48.0f, std::min(48.0f, p.x));
            p.y = std::max(-48.0f, std::min(48.0f, p.y));
        }
    }

    void fight() {
        // All damage is accumulated before any particle is removed.
        for (std::size_t i = 0; i < active_.size(); ++i) {
            Particle& a = particles_[active_[i]];
            for (std::size_t j = i + 1; j < active_.size(); ++j) {
                Particle& b = particles_[active_[j]];
                if (a.team == b.team) {
                    continue;
                }

                const float dx = sub(b.x, a.x);
                const float dy = sub(b.y, a.y);
                if (squaredDistance(dx, dy) < 2.25f) {
                    a.health -= 6;
                    b.health -= 6;
                }
            }
        }
    }

    void removeDead() {
        for (int index : active_) {
            Particle& p = particles_[index];
            if (p.health <= 0) {
                p.alive = false;
                free_.push_back(index);
            }
        }
    }

    void updateControl() {
        std::array<int, 2> nearby{};
        for (const Particle& p : particles_) {
            if (p.alive && squaredDistance(p.x, p.y) < 36.0f) {
                ++nearby[p.team];
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

    static void hashCoordinate(std::uint64_t& hash, float coordinate) {
        const auto signedValue =
            static_cast<std::int32_t>(mul(coordinate, 1000.0f));
        const auto value = static_cast<std::uint32_t>(signedValue);
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= static_cast<std::uint64_t>((value >> shift) & 255u);
            hash *= UINT64_C(1099511628211);
        }
    }
};

} // namespace

int main(int argc, char** argv) {
    std::fputs(graphText, stdout);

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