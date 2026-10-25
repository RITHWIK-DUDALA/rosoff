/**
 * Unit test suite for CDPR Command Validation Logic.
 */
#include <stdio.h>
#include <math.h>
#include <stdbool.h>
#include "../main/cdpr_command_validator.h"

static int g_tests_run = 0;
static int g_tests_passed = 0;

#define TEST_ASSERT(cond, msg) do { \
    g_tests_run++; \
    if (cond) { \
        g_tests_passed++; \
        printf("  [PASS] %s\n", msg); \
    } else { \
        printf("  [FAIL] %s (line %d)\n", msg, __LINE__); \
    } \
} while(0)

void test_valid_commands(void) {
    printf("\n--- Test Valid Nominal Commands ---\n");
    cdpr_command_tracker_t tracker;
    cdpr_command_tracker_init(&tracker);

    double lengths[4] = {0.256, 0.256, 0.256, 0.256};
    double rates[4]   = {0.050, -0.050, 0.020, -0.020};

    cdpr_cmd_validation_result_t res = cdpr_validate_command(
        lengths, 4, rates, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_VALID, "Nominal command in MOTION_ENABLED is VALID");

    res = cdpr_validate_command(
        lengths, 4, NULL, 0, 1, 2000, STATE_READY, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_VALID, "Nominal command without rates in READY is VALID");
}

void test_null_and_size_rejection(void) {
    printf("\n--- Test Null and Invalid Size Rejection ---\n");
    cdpr_command_tracker_t tracker;
    cdpr_command_tracker_init(&tracker);

    double lengths[4] = {0.256, 0.256, 0.256, 0.256};
    double rates[4]   = {0.0, 0.0, 0.0, 0.0};

    cdpr_cmd_validation_result_t res = cdpr_validate_command(
        NULL, 4, rates, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_NULL_PTR, "NULL lengths rejected");

    res = cdpr_validate_command(
        lengths, 3, rates, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_INVALID_SIZE, "Lengths size 3 rejected (expected 4)");

    res = cdpr_validate_command(
        lengths, 5, rates, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_INVALID_SIZE, "Lengths size 5 rejected (expected 4)");

    res = cdpr_validate_command(
        lengths, 4, rates, 2, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_INVALID_SIZE, "Rates size 2 rejected (expected 4 or 0)");
}

void test_nan_and_inf_rejection(void) {
    printf("\n--- Test NaN and Infinity Rejection ---\n");
    cdpr_command_tracker_t tracker;
    cdpr_command_tracker_init(&tracker);

    double nan_val = NAN;
    double inf_val = INFINITY;

    double lengths_nan[4] = {0.256, nan_val, 0.256, 0.256};
    double rates_ok[4]    = {0.0, 0.0, 0.0, 0.0};

    cdpr_cmd_validation_result_t res = cdpr_validate_command(
        lengths_nan, 4, rates_ok, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_NAN_OR_INF, "NaN in cable length rejected");

    double lengths_inf[4] = {0.256, 0.256, inf_val, 0.256};
    res = cdpr_validate_command(
        lengths_inf, 4, rates_ok, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_NAN_OR_INF, "Infinity in cable length rejected");

    double lengths_ok[4] = {0.256, 0.256, 0.256, 0.256};
    double rates_nan[4]  = {0.0, nan_val, 0.0, 0.0};
    res = cdpr_validate_command(
        lengths_ok, 4, rates_nan, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_NAN_OR_INF, "NaN in cable rate rejected");

    double rates_inf[4]  = {0.0, 0.0, -inf_val, 0.0};
    res = cdpr_validate_command(
        lengths_ok, 4, rates_inf, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_NAN_OR_INF, "Negative Infinity in cable rate rejected");
}

void test_bounds_rejection(void) {
    printf("\n--- Test Geometric and Rate Bounds Rejection ---\n");
    cdpr_command_tracker_t tracker;
    cdpr_command_tracker_init(&tracker);

    double rates_ok[4] = {0.0, 0.0, 0.0, 0.0};

    /* Cable under minimum (0.050 m) */
    double lengths_under[4] = {0.020, 0.256, 0.256, 0.256};
    cdpr_cmd_validation_result_t res = cdpr_validate_command(
        lengths_under, 4, rates_ok, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_LENGTH_OUT_OF_BOUNDS, "Cable length < 0.050 m rejected");

    /* Cable over maximum (0.700 m) */
    double lengths_over[4] = {0.256, 0.750, 0.256, 0.256};
    res = cdpr_validate_command(
        lengths_over, 4, rates_ok, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_LENGTH_OUT_OF_BOUNDS, "Cable length > 0.700 m rejected");

    /* Rate over maximum (0.500 m/s) */
    double lengths_ok[4] = {0.256, 0.256, 0.256, 0.256};
    double rates_over[4] = {0.100, 0.600, 0.100, 0.100};
    res = cdpr_validate_command(
        lengths_ok, 4, rates_over, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_RATE_OUT_OF_BOUNDS, "Rate > 0.500 m/s rejected");

    /* Negative rate exceeding clamp (-0.600 m/s) */
    double rates_neg_over[4] = {0.100, -0.600, 0.100, 0.100};
    res = cdpr_validate_command(
        lengths_ok, 4, rates_neg_over, 4, 1, 1000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_RATE_OUT_OF_BOUNDS, "Rate < -0.500 m/s rejected");
}

void test_stale_timestamp_rejection(void) {
    printf("\n--- Test Stale Timestamp Rejection ---\n");
    cdpr_command_tracker_t tracker;
    cdpr_command_tracker_init(&tracker);

    double lengths[4] = {0.256, 0.256, 0.256, 0.256};
    double rates[4]   = {0.0, 0.0, 0.0, 0.0};

    /* Message 1: t = 10s, 5000ns */
    cdpr_cmd_validation_result_t res = cdpr_validate_command(
        lengths, 4, rates, 4, 10, 5000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_VALID, "First timestamp accepted");

    /* Message 2: t = 10s, 6000ns (monotonic increment) */
    res = cdpr_validate_command(
        lengths, 4, rates, 4, 10, 6000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_VALID, "Increasing timestamp accepted");

    /* Message 3: duplicate timestamp (t = 10s, 6000ns) */
    res = cdpr_validate_command(
        lengths, 4, rates, 4, 10, 6000, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_STALE_TIMESTAMP, "Duplicate timestamp rejected as stale");

    /* Message 4: older timestamp (t = 9s, 9999ns) */
    res = cdpr_validate_command(
        lengths, 4, rates, 4, 9, 9999, STATE_MOTION_ENABLED, &tracker
    );
    TEST_ASSERT(res == CDPR_CMD_ERR_STALE_TIMESTAMP, "Past timestamp (out-of-order) rejected as stale");
}

void test_forbidden_state_gate(void) {
    printf("\n--- Test State Gating on Commands ---\n");
    cdpr_command_tracker_t tracker;
    cdpr_command_tracker_init(&tracker);

    double lengths[4] = {0.256, 0.256, 0.256, 0.256};
    double rates[4]   = {0.0, 0.0, 0.0, 0.0};

    TEST_ASSERT(cdpr_validate_command(lengths, 4, rates, 4, 1, 1, STATE_BOOT, &tracker) == CDPR_CMD_ERR_FORBIDDEN_STATE,
                "Command rejected in STATE_BOOT");
    TEST_ASSERT(cdpr_validate_command(lengths, 4, rates, 4, 1, 1, STATE_INITIALIZING, &tracker) == CDPR_CMD_ERR_FORBIDDEN_STATE,
                "Command rejected in STATE_INITIALIZING");
    TEST_ASSERT(cdpr_validate_command(lengths, 4, rates, 4, 1, 1, STATE_WAITING_FOR_AGENT, &tracker) == CDPR_CMD_ERR_FORBIDDEN_STATE,
                "Command rejected in STATE_WAITING_FOR_AGENT");
    TEST_ASSERT(cdpr_validate_command(lengths, 4, rates, 4, 1, 1, STATE_CONNECTED, &tracker) == CDPR_CMD_ERR_FORBIDDEN_STATE,
                "Command rejected in STATE_CONNECTED");
    TEST_ASSERT(cdpr_validate_command(lengths, 4, rates, 4, 1, 1, STATE_DRIVE_STATUS_CHECK, &tracker) == CDPR_CMD_ERR_FORBIDDEN_STATE,
                "Command rejected in STATE_DRIVE_STATUS_CHECK");
    TEST_ASSERT(cdpr_validate_command(lengths, 4, rates, 4, 1, 1, STATE_SAFE_STOP, &tracker) == CDPR_CMD_ERR_FORBIDDEN_STATE,
                "Command rejected in STATE_SAFE_STOP");
    TEST_ASSERT(cdpr_validate_command(lengths, 4, rates, 4, 1, 1, STATE_FAULT, &tracker) == CDPR_CMD_ERR_FORBIDDEN_STATE,
                "Command rejected in STATE_FAULT");
}

int main(void) {
    printf("==========================================\n");
    printf("  CDPR Command Validation Test Suite      \n");
    printf("==========================================\n");

    test_valid_commands();
    test_null_and_size_rejection();
    test_nan_and_inf_rejection();
    test_bounds_rejection();
    test_stale_timestamp_rejection();
    test_forbidden_state_gate();

    printf("\n==========================================\n");
    printf(" Results: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("==========================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
