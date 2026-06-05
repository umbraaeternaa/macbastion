/* clock — SystemClock implementation (real plumbing). FakeClock is header-inline.
 * Monotonic steady_clock so escalation timing is unaffected by wall-clock jumps. */
#include "clock.hpp"

#include <chrono>

namespace tether {

long SystemClock::now_ms() {
    using namespace std::chrono;
    return static_cast<long>(
        duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count());
}

} // namespace tether
