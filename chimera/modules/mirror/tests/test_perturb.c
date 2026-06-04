/* RED-B contract for the perturbation math (§3). Fails against the no-noise
 * stubs until GREEN. Determinism / clamp tests use seeded PRNG state. */
#include "unity.h"

#include <math.h>
#include <stdbool.h>

#include "perturb.h"

#define N_SAMPLES 256

/* Over many samples, gaussian(sigma) must produce real spread, not a constant.
 * The stub returns 0.0 every time -> spread 0 -> FAILS (real RED). */
static void test_gaussian_has_spread(void) {
    uint64_t rng = 0xABCDEF1234567890ULL;
    double max_abs = 0.0;
    for (int i = 0; i < N_SAMPLES; i++) {
        double z = perturb_gaussian(1.0, &rng);
        double a = fabs(z);
        if (a > max_abs) {
            max_abs = a;
        }
    }
    TEST_ASSERT_TRUE(max_abs > 0.1);
}

/* Same seed -> identical sequence (deterministic). Each call is captured into a
 * local first: TEST_ASSERT_EQUAL_DOUBLE evaluates its `expected` arg twice, and
 * perturb_gaussian advances the PRNG state as a side effect — calling it inside
 * the macro would desync the two streams. The local capture keeps the contract
 * intact (same seed -> same value), it just avoids the macro's double-eval. */
static void test_gaussian_deterministic(void) {
    uint64_t a = 42, b = 42;
    for (int i = 0; i < 8; i++) {
        double za = perturb_gaussian(1.5, &a);
        double zb = perturb_gaussian(1.5, &b);
        TEST_ASSERT_EQUAL_DOUBLE(za, zb);
    }
}

/* sigma <= 0 must yield exactly 0 noise. Stub returns 0 -> passes coincidentally. */
static void test_gaussian_zero_sigma(void) {
    uint64_t rng = 7;
    TEST_ASSERT_EQUAL_DOUBLE(0.0, perturb_gaussian(0.0, &rng));
}

/* perturb_mouse must actually move the delta over many samples. The stub leaves
 * (dx,dy) untouched -> max displacement 0 -> FAILS (real RED). */
static void test_mouse_moves_delta(void) {
    uint64_t rng = 0x1357ULL;
    double max_disp = 0.0;
    for (int i = 0; i < N_SAMPLES; i++) {
        double dx = 0.0, dy = 0.0;
        perturb_mouse(&dx, &dy, 2.0, &rng);
        double d = fabs(dx) + fabs(dy);
        if (d > max_disp) {
            max_disp = d;
        }
    }
    TEST_ASSERT_TRUE(max_disp > 0.1);
}

/* Timing jitter must vary around base and stay within [base-delta, base+delta].
 * The stub returns base every time -> never varies -> FAILS (real RED). */
static void test_timing_jitters_in_range(void) {
    uint64_t rng = 0x99ULL;
    const int base = 100, delta = 20;
    bool varied = false;
    for (int i = 0; i < N_SAMPLES; i++) {
        int v = perturb_timing(base, delta, &rng);
        TEST_ASSERT_TRUE(v >= base - delta && v <= base + delta);
        if (v != base) {
            varied = true;
        }
    }
    TEST_ASSERT_TRUE(varied);
}

/* Result must never go negative even with a large delta. Stub returns base (>=0)
 * -> passes coincidentally; locks the clamp contract for GREEN. */
static void test_timing_clamped_nonnegative(void) {
    uint64_t rng = 0x2468ULL;
    for (int i = 0; i < N_SAMPLES; i++) {
        TEST_ASSERT_TRUE(perturb_timing(5, 50, &rng) >= 0);
    }
}

void run_perturb_tests(void) {
    RUN_TEST(test_gaussian_has_spread);
    RUN_TEST(test_gaussian_deterministic);
    RUN_TEST(test_gaussian_zero_sigma);
    RUN_TEST(test_mouse_moves_delta);
    RUN_TEST(test_timing_jitters_in_range);
    RUN_TEST(test_timing_clamped_nonnegative);
}
