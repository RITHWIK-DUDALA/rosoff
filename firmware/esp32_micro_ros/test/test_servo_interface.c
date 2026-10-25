/**
 * Unit test suite for CDPR Servo Driver Interface (Fail-Closed Behavior).
 */
#include <stdio.h>
#include <stdbool.h>
#include "../main/servo_driver_interface.h"

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

void test_servo_initialization(void) {
    printf("\n--- Test Servo Driver Initialization ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_result_t res = cdpr_servo_init(&status);

    TEST_ASSERT(res == CDPR_SERVO_ERR_UNVERIFIED_HARDWARE, "Initialization returns UNVERIFIED_HARDWARE");
    TEST_ASSERT(!status.is_hardware_verified, "Hardware remains flagged unverified");
    TEST_ASSERT(!status.torque_permitted, "Torque is NOT permitted");
    TEST_ASSERT(!status.torque_enabled, "Torque is NOT enabled (disarmed)");
    TEST_ASSERT(!status.feedback_valid, "Feedback is flagged INVALID (not fabricated)");
    TEST_ASSERT(status.active_drive_faults == 0, "No active drive faults initially");

    TEST_ASSERT(cdpr_servo_init(NULL) == CDPR_SERVO_ERR_INVALID_ARG, "NULL pointer handling returns INVALID_ARG");
}

void test_torque_prohibition(void) {
    printf("\n--- Test Torque Enable Prohibition (Fail-Closed) ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);

    /* Attempting to enable torque on unverified hardware must be strictly refused */
    cdpr_servo_result_t res = cdpr_servo_enable_torque(&status, true);
    TEST_ASSERT(res == CDPR_SERVO_ERR_UNVERIFIED_HARDWARE, "Enabling torque returns UNVERIFIED_HARDWARE");
    TEST_ASSERT(!status.torque_enabled, "Torque remains false after enable attempt");

    /* Disabling torque is always permitted (safe-state) */
    res = cdpr_servo_enable_torque(&status, false);
    TEST_ASSERT(res == CDPR_SERVO_OK, "Disabling torque returns OK");
    TEST_ASSERT(!status.torque_enabled, "Torque remains false");
}

void test_command_rates_prohibition(void) {
    printf("\n--- Test Rate Dispatch Prohibition ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);

    float rates[4] = {0.1f, 0.1f, -0.1f, -0.1f};
    cdpr_servo_result_t res = cdpr_servo_command_rates(&status, rates);
    TEST_ASSERT(res == CDPR_SERVO_ERR_TORQUE_NOT_PERMITTED, "command_rates rejected when torque disabled");

    TEST_ASSERT(cdpr_servo_command_rates(NULL, rates) == CDPR_SERVO_ERR_INVALID_ARG, "NULL status rejected");
    TEST_ASSERT(cdpr_servo_command_rates(&status, NULL) == CDPR_SERVO_ERR_INVALID_ARG, "NULL rates rejected");
}

void test_feedback_read_status(void) {
    printf("\n--- Test Feedback & Status Reading ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);

    /* Reading status must not claim success or fabricate data */
    cdpr_servo_result_t res = cdpr_servo_read_status(&status);
    TEST_ASSERT(res == CDPR_SERVO_ERR_UNVERIFIED_HARDWARE, "read_status returns UNVERIFIED_HARDWARE");
    TEST_ASSERT(!status.feedback_valid, "feedback_valid remains false");
}

void test_emergency_safe_stop(void) {
    printf("\n--- Test Emergency Safe Stop Command Zeroing ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);
    status.current_rpms[0] = 120.0f;
    status.current_rpms[1] = -80.0f;

    cdpr_servo_emergency_safe_stop(&status);
    TEST_ASSERT(!status.torque_enabled, "Torque disabled after safe stop");
    TEST_ASSERT(status.current_rpms[0] == 0.0f, "RPM[0] clamped to 0");
    TEST_ASSERT(status.current_rpms[1] == 0.0f, "RPM[1] clamped to 0");
    TEST_ASSERT(status.current_rpms[2] == 0.0f, "RPM[2] clamped to 0");
    TEST_ASSERT(status.current_rpms[3] == 0.0f, "RPM[3] clamped to 0");
}

int main(void) {
    printf("==========================================\n");
    printf("   CDPR Servo Driver Safety Unit Tests    \n");
    printf("==========================================\n");

    test_servo_initialization();
    test_torque_prohibition();
    test_command_rates_prohibition();
    test_feedback_read_status();
    test_emergency_safe_stop();

    printf("\n==========================================\n");
    printf(" Results: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("==========================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
