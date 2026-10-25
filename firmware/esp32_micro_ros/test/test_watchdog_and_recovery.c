/**
 * Unit test suite for CDPR Watchdog Trip, Latching, and Explicit Reset Recovery.
 * Verifies monotonic 250 ms watchdog, strict latching of SAFE_STOP,
 * prerequisites for recovery (Agent connected, 0 drive faults), and refusal to arm.
 */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include "../main/app_state.h"
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

#define WATCHDOG_TIMEOUT_MS 250

/* Mock FSM and safety context matching main.c */
typedef struct {
    cdpr_firmware_state_t state;
    cdpr_servo_status_t   servo;
    int64_t               last_valid_cmd_time_us;
    bool                  agent_connected;
    bool                  watchdog_tripped;
    bool                  reset_requested;
} fsm_test_ctx_t;

static void fsm_test_init(fsm_test_ctx_t* ctx) {
    memset(ctx, 0, sizeof(*ctx));
    ctx->state = STATE_READY;
    cdpr_servo_init(&ctx->servo);
    ctx->agent_connected = true;
}

static bool fsm_test_transition(fsm_test_ctx_t* ctx, cdpr_firmware_state_t new_state) {
    if (!cdpr_is_valid_transition(ctx->state, new_state)) {
        return false;
    }

    /* Arming gate */
    if (new_state == STATE_MOTION_ENABLED) {
        if (!ctx->servo.is_hardware_verified || !ctx->servo.torque_permitted) {
            return false;
        }
    }

    /* SAFE_STOP -> READY recovery gate */
    if (ctx->state == STATE_SAFE_STOP && new_state == STATE_READY) {
        if (!ctx->reset_requested) return false;
        if (!ctx->agent_connected) return false;
        if (ctx->servo.active_drive_faults != 0) return false;

        ctx->reset_requested = false;
        ctx->watchdog_tripped = false;
    }

    ctx->state = new_state;

    if (new_state == STATE_SAFE_STOP || new_state == STATE_FAULT) {
        cdpr_servo_emergency_safe_stop(&ctx->servo);
    }

    return true;
}

static void fsm_test_check_watchdog(fsm_test_ctx_t* ctx, int64_t now_us) {
    if (ctx->state == STATE_MOTION_ENABLED) {
        int64_t elapsed_ms = (now_us - ctx->last_valid_cmd_time_us) / 1000;
        if (elapsed_ms > WATCHDOG_TIMEOUT_MS) {
            ctx->watchdog_tripped = true;
            (void)fsm_test_transition(ctx, STATE_SAFE_STOP);
        }
    }
}

static bool fsm_test_handle_control_cmd(fsm_test_ctx_t* ctx, int32_t cmd_code) {
    switch (cmd_code) {
        case CDPR_CMD_DISARM_OR_SAFE_STOP:
            return fsm_test_transition(ctx, STATE_SAFE_STOP);

        case CDPR_CMD_REQUEST_ARM:
            if (!ctx->servo.is_hardware_verified) {
                return false; /* Refused */
            }
            return fsm_test_transition(ctx, STATE_MOTION_ENABLED);

        case CDPR_CMD_RESET_SAFE_STOP:
            if (ctx->state == STATE_SAFE_STOP) {
                if (!ctx->agent_connected || ctx->servo.active_drive_faults != 0) {
                    return false;
                }
                ctx->reset_requested = true;
                return fsm_test_transition(ctx, STATE_READY);
            }
            return false;

        case CDPR_CMD_EMERGENCY_FAULT:
            return fsm_test_transition(ctx, STATE_FAULT);

        default:
            return false;
    }
}

void test_refusal_to_arm_unverified(void) {
    printf("\n--- Test Refusal to Arm Unverified Hardware ---\n");
    fsm_test_ctx_t ctx;
    fsm_test_init(&ctx);

    TEST_ASSERT(ctx.state == STATE_READY, "Initial state is READY");
    TEST_ASSERT(!ctx.servo.is_hardware_verified, "Hardware is unverified");

    /* Attempt to arm via supervisor command */
    bool ok = fsm_test_handle_control_cmd(&ctx, CDPR_CMD_REQUEST_ARM);
    TEST_ASSERT(!ok, "ARM request refused when hardware is unverified");
    TEST_ASSERT(ctx.state == STATE_READY, "State remains READY (motors disarmed, torque disabled)");
    TEST_ASSERT(!ctx.servo.torque_enabled, "Torque remains disabled");

    /* Direct transition attempt to MOTION_ENABLED must also fail closed */
    ok = fsm_test_transition(&ctx, STATE_MOTION_ENABLED);
    TEST_ASSERT(!ok, "Direct transition to MOTION_ENABLED refused for unverified hardware");
    TEST_ASSERT(ctx.state == STATE_READY, "State remains READY");
}

void test_watchdog_trip_and_latching(void) {
    printf("\n--- Test Watchdog Trip and Latching ---\n");
    fsm_test_ctx_t ctx;
    fsm_test_init(&ctx);

    /* Temporarily verify hardware to simulate active MOTION_ENABLED state */
    ctx.servo.is_hardware_verified = true;
    ctx.servo.torque_permitted = true;
    bool ok = fsm_test_transition(&ctx, STATE_MOTION_ENABLED);
    TEST_ASSERT(ok, "Entered MOTION_ENABLED with verified hardware mock");
    TEST_ASSERT(ctx.state == STATE_MOTION_ENABLED, "State is MOTION_ENABLED");

    ctx.last_valid_cmd_time_us = 1000000; /* t = 1.000 s */

    /* 1. Advance time by 100 ms (elapsed = 100 ms <= 250 ms) -> No trip */
    fsm_test_check_watchdog(&ctx, 1100000);
    TEST_ASSERT(ctx.state == STATE_MOTION_ENABLED, "t=100ms: Watchdog has NOT tripped");
    TEST_ASSERT(!ctx.watchdog_tripped, "watchdog_tripped is false");

    /* 2. Advance time by 249 ms (elapsed = 249 ms <= 250 ms) -> No trip */
    fsm_test_check_watchdog(&ctx, 1249000);
    TEST_ASSERT(ctx.state == STATE_MOTION_ENABLED, "t=249ms: Watchdog has NOT tripped");
    TEST_ASSERT(!ctx.watchdog_tripped, "watchdog_tripped is false");

    /* 3. Advance time to 251 ms (elapsed = 251 ms > 250 ms) -> TRIPS! */
    fsm_test_check_watchdog(&ctx, 1251000);
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "t=251ms: Watchdog TRIPPED -> SAFE_STOP latched");
    TEST_ASSERT(ctx.watchdog_tripped, "watchdog_tripped flag is set to true");
    TEST_ASSERT(!ctx.servo.torque_enabled, "Torque is immediately disabled");

    /* 4. Verify SAFE_STOP remains latched over time (does NOT auto-reset) */
    fsm_test_check_watchdog(&ctx, 2000000); /* t = 2.0 s */
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "t=1000ms: SAFE_STOP remains latched");

    fsm_test_check_watchdog(&ctx, 10000000); /* t = 10.0 s */
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "t=10s: SAFE_STOP remains strictly latched");
}

void test_explicit_reset_prerequisites(void) {
    printf("\n--- Test Explicit Reset Recovery Policy ---\n");
    fsm_test_ctx_t ctx;
    fsm_test_init(&ctx);
    ctx.servo.is_hardware_verified = true;
    ctx.servo.torque_permitted = true;
    fsm_test_transition(&ctx, STATE_MOTION_ENABLED);
    ctx.last_valid_cmd_time_us = 1000000;

    /* Trip watchdog */
    fsm_test_check_watchdog(&ctx, 1300000);
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "Tripped into SAFE_STOP");

    /* Attempt 1: Direct transition to READY without operator reset request -> FORBIDDEN */
    bool ok = fsm_test_transition(&ctx, STATE_READY);
    TEST_ASSERT(!ok, "Direct unrequested transition SAFE_STOP -> READY rejected");
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "State remains SAFE_STOP");

    /* Attempt 2: Operator reset while Agent is DISCONNECTED -> REFUSED */
    ctx.agent_connected = false;
    ok = fsm_test_handle_control_cmd(&ctx, CDPR_CMD_RESET_SAFE_STOP);
    TEST_ASSERT(!ok, "Reset REFUSED when micro-ROS Agent is disconnected");
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "State remains SAFE_STOP");

    /* Attempt 3: Operator reset with active DRIVE FAULTS -> REFUSED */
    ctx.agent_connected = true;
    ctx.servo.active_drive_faults = 0x00000004; /* Overcurrent fault */
    ok = fsm_test_handle_control_cmd(&ctx, CDPR_CMD_RESET_SAFE_STOP);
    TEST_ASSERT(!ok, "Reset REFUSED when active drive faults are present");
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "State remains SAFE_STOP");

    /* Attempt 4: Spurious control codes (e.g. 99, or CDPR_CMD_DISARM_OR_SAFE_STOP) */
    ctx.servo.active_drive_faults = 0;
    ok = fsm_test_handle_control_cmd(&ctx, 99);
    TEST_ASSERT(!ok, "Unknown command code rejected");
    TEST_ASSERT(ctx.state == STATE_SAFE_STOP, "State remains SAFE_STOP");

    /* Attempt 5: Valid explicit operator reset (Agent connected, 0 faults) -> SUCCEEDS */
    ok = fsm_test_handle_control_cmd(&ctx, CDPR_CMD_RESET_SAFE_STOP);
    TEST_ASSERT(ok, "Valid explicit operator reset accepted");
    TEST_ASSERT(ctx.state == STATE_READY, "State successfully returned to READY");
    TEST_ASSERT(!ctx.watchdog_tripped, "watchdog_tripped flag cleared");
    TEST_ASSERT(!ctx.reset_requested, "reset_requested flag cleared");

    /* Verify that recovery lands in READY, NOT in MOTION_ENABLED */
    TEST_ASSERT(ctx.state != STATE_MOTION_ENABLED, "System did NOT auto-arm on reset");
}

int main(void) {
    printf("===================================================\n");
    printf("   CDPR Watchdog & Recovery Policy Unit Tests      \n");
    printf("===================================================\n");

    test_refusal_to_arm_unverified();
    test_watchdog_trip_and_latching();
    test_explicit_reset_prerequisites();

    printf("\n===================================================\n");
    printf(" Results: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("===================================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
