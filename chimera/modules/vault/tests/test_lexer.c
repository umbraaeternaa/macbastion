/* Contract for the policy DSL lexer (§4 tokens). RED: vault_lexer_next() returns
 * TK_EOF, so the token-shape tests fail; the empty-input test passes coincidentally. */
#include "unity.h"

#include "lexer.h"

static void test_lexer_variable_operator_number(void) {
    VaultLexer lx;
    vault_lexer_init(&lx, "hour >= 9");
    VaultToken a = vault_lexer_next(&lx);
    TEST_ASSERT_EQUAL_INT(TK_IDENT, a.kind);
    TEST_ASSERT_EQUAL_INT(4, (int)a.len); /* "hour" */
    VaultToken b = vault_lexer_next(&lx);
    TEST_ASSERT_EQUAL_INT(TK_GE, b.kind);
    VaultToken c = vault_lexer_next(&lx);
    TEST_ASSERT_EQUAL_INT(TK_NUMBER, c.kind);
    TEST_ASSERT_EQUAL_INT(9, (int)c.number);
}

static void test_lexer_all_operators(void) {
    VaultLexer lx;
    vault_lexer_init(&lx, "== != < <= > >=");
    TEST_ASSERT_EQUAL_INT(TK_EQ, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_NE, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_LT, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_LE, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_GT, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_GE, vault_lexer_next(&lx).kind);
}

static void test_lexer_list_punctuation(void) {
    VaultLexer lx;
    vault_lexer_init(&lx, "in [mon, tue]");
    TEST_ASSERT_EQUAL_INT(TK_IDENT, vault_lexer_next(&lx).kind); /* in */
    TEST_ASSERT_EQUAL_INT(TK_LBRACKET, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_IDENT, vault_lexer_next(&lx).kind); /* mon */
    TEST_ASSERT_EQUAL_INT(TK_COMMA, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_IDENT, vault_lexer_next(&lx).kind); /* tue */
    TEST_ASSERT_EQUAL_INT(TK_RBRACKET, vault_lexer_next(&lx).kind);
}

static void test_lexer_duration_splits_number_and_unit(void) {
    VaultLexer lx;
    vault_lexer_init(&lx, "30min");
    VaultToken n = vault_lexer_next(&lx);
    TEST_ASSERT_EQUAL_INT(TK_NUMBER, n.kind);
    TEST_ASSERT_EQUAL_INT(30, (int)n.number);
    VaultToken u = vault_lexer_next(&lx);
    TEST_ASSERT_EQUAL_INT(TK_IDENT, u.kind); /* min */
}

static void test_lexer_string_and_colon(void) {
    VaultLexer lx;
    vault_lexer_init(&lx, "allow_when: network_ssid == \"Home\"");
    TEST_ASSERT_EQUAL_INT(TK_IDENT, vault_lexer_next(&lx).kind); /* allow_when */
    TEST_ASSERT_EQUAL_INT(TK_COLON, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_IDENT, vault_lexer_next(&lx).kind); /* network_ssid */
    TEST_ASSERT_EQUAL_INT(TK_EQ, vault_lexer_next(&lx).kind);
    TEST_ASSERT_EQUAL_INT(TK_STRING, vault_lexer_next(&lx).kind);
}

/* Coincidental-pass in RED: empty input is TK_EOF, which the stub already returns. */
static void test_lexer_empty_is_eof(void) {
    VaultLexer lx;
    vault_lexer_init(&lx, "");
    TEST_ASSERT_EQUAL_INT(TK_EOF, vault_lexer_next(&lx).kind);
}

void run_lexer_tests(void) {
    RUN_TEST(test_lexer_variable_operator_number);
    RUN_TEST(test_lexer_all_operators);
    RUN_TEST(test_lexer_list_punctuation);
    RUN_TEST(test_lexer_duration_splits_number_and_unit);
    RUN_TEST(test_lexer_string_and_colon);
    RUN_TEST(test_lexer_empty_is_eof);
}
