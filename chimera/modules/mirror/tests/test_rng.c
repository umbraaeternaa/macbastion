/* Contract for the injectable PRNG (mirror.h, xorshift64*). This exercises the
 * REAL inline implementation shipped in the bootstrap (D3=3B) — not a stub — so
 * these PASS in RED; they lock the determinism the perturbation engine relies on. */
#include "unity.h"

#include <stdbool.h>

#include "mirror.h"

/* Equal seeds -> identical sequences (deterministic engine input). */
static void test_same_seed_same_sequence(void) {
    uint64_t a = 0xDEADBEEFULL, b = 0xDEADBEEFULL;
    for (int i = 0; i < 16; i++) {
        TEST_ASSERT_EQUAL_HEX64(mirror_rng_next(&a), mirror_rng_next(&b));
    }
}

/* Different seeds -> different first output. */
static void test_diff_seed_differs(void) {
    uint64_t a = 1, b = 2;
    TEST_ASSERT_TRUE(mirror_rng_next(&a) != mirror_rng_next(&b));
}

/* The stream is not a constant. */
static void test_not_constant(void) {
    uint64_t s = 0x12345678ULL;
    uint64_t first = mirror_rng_next(&s);
    bool differs = false;
    for (int i = 0; i < 16; i++) {
        if (mirror_rng_next(&s) != first) {
            differs = true;
            break;
        }
    }
    TEST_ASSERT_TRUE(differs);
}

/* Each call advances the state. */
static void test_state_advances(void) {
    uint64_t s = 99;
    uint64_t before = s;
    mirror_rng_next(&s);
    TEST_ASSERT_TRUE(s != before);
}

void run_rng_tests(void) {
    RUN_TEST(test_same_seed_same_sequence);
    RUN_TEST(test_diff_seed_differs);
    RUN_TEST(test_not_constant);
    RUN_TEST(test_state_advances);
}
