/* Clock seam (SS-7-style): escalation timing is computed against an injected
 * monotonic millisecond clock so tests are deterministic. Real daemon uses
 * SystemClock (std::chrono::steady_clock); tests use FakeClock. */
#ifndef TETHER_CLOCK_HPP
#define TETHER_CLOCK_HPP

namespace tether {

class Clock {
  public:
    virtual ~Clock() = default;
    virtual long now_ms() = 0;
};

/* Monotonic wall clock for the running daemon. */
class SystemClock : public Clock {
  public:
    long now_ms() override;
};

/* Settable clock for hermetic escalation-timing tests. */
class FakeClock : public Clock {
  public:
    explicit FakeClock(long start_ms = 0) : now_(start_ms) {}
    long now_ms() override { return now_; }
    void set(long ms) { now_ = ms; }
    void advance(long ms) { now_ += ms; }

  private:
    long now_;
};

} // namespace tether

#endif /* TETHER_CLOCK_HPP */
