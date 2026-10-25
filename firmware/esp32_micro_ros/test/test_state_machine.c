/**
 * Unit test suite for CDPR Firmware State Machine and Transitions.
 */
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stdbool.h>
#include "../main/app_state.h"

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

void test_valid_lifecycle_transitions(void) {
    printf("\n--- Test Valid Lifecycle Transitions ---\n");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_BOOT, STATE_INITIALIZING), "BOOT -> INITIALIZING");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_INITIALIZING, STATE_WAITING_FOR_AGENT), "INITIALIZING -> WAITING_FOR_AGENT");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_WAITING_FOR_AGENT, STATE_CONNECTED), "WAITING_FOR_AGENT -> CONNECTED");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_CONNECTED, STATE_DRIVE_STATUS_CHECK), "CONNECTED -> DRIVE_STATUS_CHECK");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_DRIVE_STATUS_CHECK, STATE_READY), "DRIVE_STATUS_CHECK -> READY");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_READY, STATE_MOTION_ENABLED), "READY -> MOTION_ENABLED (valid topological graph transition)");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_MOTION_ENABLED, STATE_READY), "MOTION_ENABLED -> READY (disarm/complete)");
}

void test_forbidden_auto_arming(void) {
    printf("\n--- Test Forbidden Auto-Arm Transitions ---\n");
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_WAITING_FOR_AGENT, STATE_MOTION_ENABLED), "WAITING_FOR_AGENT -> MOTION_ENABLED forbidden");
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_CONNECTED, STATE_MOTION_ENABLED), "CONNECTED -> MOTION_ENABLED forbidden");
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_DRIVE_STATUS_CHECK, STATE_MOTION_ENABLED), "DRIVE_STATUS_CHECK -> MOTION_ENABLED forbidden");
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_BOOT, STATE_MOTION_ENABLED), "BOOT -> MOTION_ENABLED forbidden");
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_INITIALIZING, STATE_MOTION_ENABLED), "INITIALIZING -> MOTION_ENABLED forbidden");
}

void test_safe_stop_and_fault_latching(void) {
    printf("\n--- Test SAFE_STOP and FAULT Transitions ---\n");
    /* Emergency transitions to SAFE_STOP are allowed from all active states */
    TEST_ASSERT(cdpr_is_valid_transition(STATE_MOTION_ENABLED, STATE_SAFE_STOP), "MOTION_ENABLED -> SAFE_STOP (watchdog timeout)");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_READY, STATE_SAFE_STOP), "READY -> SAFE_STOP");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_CONNECTED, STATE_SAFE_STOP), "CONNECTED -> SAFE_STOP");

    /* Emergency transitions to FAULT are allowed from all states */
    TEST_ASSERT(cdpr_is_valid_transition(STATE_MOTION_ENABLED, STATE_FAULT), "MOTION_ENABLED -> FAULT");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_READY, STATE_FAULT), "READY -> FAULT");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_SAFE_STOP, STATE_FAULT), "SAFE_STOP -> FAULT");

    /* SAFE_STOP cannot jump directly to MOTION_ENABLED */
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_SAFE_STOP, STATE_MOTION_ENABLED), "SAFE_STOP -> MOTION_ENABLED strictly forbidden");

    /* Recovery transitions */
    TEST_ASSERT(cdpr_is_valid_transition(STATE_SAFE_STOP, STATE_READY), "SAFE_STOP -> READY (via explicit operator reset)");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_SAFE_STOP, STATE_WAITING_FOR_AGENT), "SAFE_STOP -> WAITING_FOR_AGENT (agent loss)");
    TEST_ASSERT(cdpr_is_valid_transition(STATE_FAULT, STATE_INITIALIZING), "FAULT -> INITIALIZING (hard reboot/init)");
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_FAULT, STATE_READY), "FAULT -> READY directly is forbidden");
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_FAULT, STATE_MOTION_ENABLED), "FAULT -> MOTION_ENABLED directly is forbidden");
}

void test_state_to_str(void) {
    printf("\n--- Test State String Representation ---\n");
    TEST_ASSERT(strcmp(cdpr_state_to_str(STATE_BOOT), "BOOT") == 0, "STATE_BOOT is 'BOOT'");
    TEST_ASSERT(strcmp(cdpr_state_to_str(STATE_MOTION_ENABLED), "MOTION_ENABLED") == 0, "STATE_MOTION_ENABLED is 'MOTION_ENABLED'");
    TEST_ASSERT(strcmp(cdpr_state_to_str(STATE_SAFE_STOP), "SAFE_STOP") == 0, "STATE_SAFE_STOP is 'SAFE_STOP'");
    TEST_ASSERT(strcmp(cdpr_state_to_str(STATE_FAULT), "FAULT") == 0, "STATE_FAULT is 'FAULT'");
}

int main(void) {
    printf("==========================================\n");
    printf("   CDPR State Machine Verification Suite  \n");
    printf("==========================================\n");

    test_valid_lifecycle_transitions();
    test_forbidden_auto_arming();
    test_safe_stop_and_fault_latching();
    test_state_to_str();

    printf("\n==========================================\n");
    printf(" Results: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("==========================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
