/**
 * Unit test suite for CDPR Feedback Interface and Unit Formatting.
 * Verifies strict fail-closed telemetry gating, SI unit enforcement,
 * and complete isolation of motor shaft RPM from joint velocity.
 */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>
#include "../main/cdpr_feedback_interface.h"
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

void test_feedback_null_handling(void) {
    printf("\n--- Test Feedback NULL Safety ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);

    /* Passing NULL payload must not crash */
    cdpr_format_feedback_payload(&status, NULL);
    TEST_ASSERT(true, "NULL payload pointer handled safely without crash");

    /* Passing NULL status must yield invalid/unavailable payload */
    cdpr_feedback_payload_t payload;
    memset(&payload, 0xFF, sizeof(payload));
    cdpr_format_feedback_payload(NULL, &payload);
    TEST_ASSERT(!payload.is_valid, "NULL status produces is_valid = false");
    TEST_ASSERT(payload.num_joints == 0, "NULL status produces num_joints = 0");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_UNAVAILABLE) == 0,
                "NULL status frame_id is 'cdpr_feedback_unavailable'");
}

void test_feedback_unverified_hardware_cases(void) {
    printf("\n--- Test Unverified Hardware Gating ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);
    cdpr_feedback_payload_t payload;

    /* Case A: Fresh initialization (unverified, invalid) */
    cdpr_format_feedback_payload(&status, &payload);
    TEST_ASSERT(!payload.is_valid, "Initial status: is_valid is false");
    TEST_ASSERT(payload.num_joints == 0, "Initial status: num_joints is 0 (telemetry suppressed)");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_UNAVAILABLE) == 0,
                "Frame is 'cdpr_feedback_unavailable'");

    /* Case B: Attempted spoof (hardware unverified, but feedback_valid forced true) */
    status.is_hardware_verified = false;
    status.feedback_valid = true;
    status.current_spool_lengths_m[0] = 0.25f;
    status.measured_cable_rates_m_s[0] = 0.05f;

    cdpr_format_feedback_payload(&status, &payload);
    TEST_ASSERT(!payload.is_valid, "Unverified hardware with feedback_valid=true is rejected");
    TEST_ASSERT(payload.num_joints == 0, "num_joints remains 0 when hardware unverified");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_UNAVAILABLE) == 0,
                "Frame remains 'cdpr_feedback_unavailable'");

    /* Case C: Hardware verified, but feedback_valid is false (e.g. comm drop to drive) */
    status.is_hardware_verified = true;
    status.feedback_valid = false;

    cdpr_format_feedback_payload(&status, &payload);
    TEST_ASSERT(!payload.is_valid, "Verified hardware with feedback_valid=false is rejected");
    TEST_ASSERT(payload.num_joints == 0, "num_joints is 0 when feedback invalid");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_UNAVAILABLE) == 0,
                "Frame remains 'cdpr_feedback_unavailable'");
}

void test_feedback_valid_and_units(void) {
    printf("\n--- Test Valid Feedback and SI Units ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);
    cdpr_feedback_payload_t payload;

    /* Simulate genuine verified hardware status */
    status.is_hardware_verified = true;
    status.feedback_valid = true;
    status.current_spool_lengths_m[0] = 0.310f;
    status.current_spool_lengths_m[1] = 0.320f;
    status.current_spool_lengths_m[2] = 0.330f;
    status.current_spool_lengths_m[3] = 0.340f;

    status.measured_cable_rates_m_s[0] = 0.125f;
    status.measured_cable_rates_m_s[1] = -0.050f;
    status.measured_cable_rates_m_s[2] = 0.200f;
    status.measured_cable_rates_m_s[3] = -0.175f;

    /* Raw rotational motor speed in RPM */
    status.current_rpms[0] = 3000.0f;
    status.current_rpms[1] = -1200.0f;
    status.current_rpms[2] = 4800.0f;
    status.current_rpms[3] = -4200.0f;

    cdpr_format_feedback_payload(&status, &payload);

    TEST_ASSERT(payload.is_valid, "Verified status yields is_valid = true");
    TEST_ASSERT(payload.num_joints == 4, "num_joints is 4 for verified feedback");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_MEASURED) == 0,
                "frame_id is 'cdpr_measured'");

    /* Check length SI units [m] */
    TEST_ASSERT(fabs(payload.lengths_m[0] - 0.310) < 1e-4, "lengths_m[0] is 0.310 m");
    TEST_ASSERT(fabs(payload.lengths_m[1] - 0.320) < 1e-4, "lengths_m[1] is 0.320 m");
    TEST_ASSERT(fabs(payload.lengths_m[2] - 0.330) < 1e-4, "lengths_m[2] is 0.330 m");
    TEST_ASSERT(fabs(payload.lengths_m[3] - 0.340) < 1e-4, "lengths_m[3] is 0.340 m");

    /* Check rate SI units [m/s] */
    TEST_ASSERT(fabs(payload.rates_m_s[0] - 0.125) < 1e-4, "rates_m_s[0] is 0.125 m/s");
    TEST_ASSERT(fabs(payload.rates_m_s[1] - (-0.050)) < 1e-4, "rates_m_s[1] is -0.050 m/s");
    TEST_ASSERT(fabs(payload.rates_m_s[2] - 0.200) < 1e-4, "rates_m_s[2] is 0.200 m/s");
    TEST_ASSERT(fabs(payload.rates_m_s[3] - (-0.175)) < 1e-4, "rates_m_s[3] is -0.175 m/s");

    /* CRITICAL SAFETY CHECK: Motor shaft RPM must NEVER be mapped to velocity */
    TEST_ASSERT(fabs(payload.rates_m_s[0] - 3000.0) > 100.0, "rates_m_s[0] is NOT 3000.0 RPM");
    TEST_ASSERT(fabs(payload.rates_m_s[1] - (-1200.0)) > 100.0, "rates_m_s[1] is NOT -1200.0 RPM");
    TEST_ASSERT(fabs(payload.rates_m_s[2] - 4800.0) > 100.0, "rates_m_s[2] is NOT 4800.0 RPM");
    TEST_ASSERT(fabs(payload.rates_m_s[3] - (-4200.0)) > 100.0, "rates_m_s[3] is NOT -4200.0 RPM");
}

void test_unavailable_feedback_not_published_as_zeros(void) {
    printf("\n--- Test Unavailable Feedback NOT Published as Dummy Zeros ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);
    cdpr_feedback_payload_t payload;

    /* Simulate driver status with zeroed internal registers */
    for (int i = 0; i < 4; i++) {
        status.current_spool_lengths_m[i] = 0.0f;
        status.measured_cable_rates_m_s[i] = 0.0f;
        status.current_rpms[i] = 0.0f;
    }
    status.is_hardware_verified = false;
    status.feedback_valid = false;

    cdpr_format_feedback_payload(&status, &payload);

    /* CRITICAL SAFETY CHECK:
     * When hardware is encoderless / unverified, the firmware must NOT publish
     * 4 zero-valued measurements ([0.0, 0.0, 0.0, 0.0]) as real sensor data!
     * Downstream forward kinematics solvers would falsely interpret 0-meter cables
     * as physical platform collapse to anchors.
     * The sequence size MUST be strictly 0.
     */
    TEST_ASSERT(payload.num_joints == 0,
                "Sequence length is 0 (NOT 4 zeros) when feedback unavailable");
    TEST_ASSERT(!payload.is_valid,
                "is_valid is FALSE (explicit invalid status)");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_UNAVAILABLE) == 0,
                "frame_id explicitly signals 'cdpr_feedback_unavailable'");
}

void test_explicit_validity_convention(void) {
    printf("\n--- Test Explicit Feedback Validity Convention ---\n");
    cdpr_servo_status_t status;
    cdpr_servo_init(&status);
    cdpr_feedback_payload_t payload;

    /* Verify unverified case */
    cdpr_format_feedback_payload(&status, &payload);
    TEST_ASSERT(!payload.is_valid, "Convention: is_valid is false when unverified");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_UNAVAILABLE) == 0,
                "Convention: frame_id is cdpr_feedback_unavailable");
    TEST_ASSERT(payload.num_joints == 0, "Convention: num_joints is 0");

    /* Verify verified case */
    status.is_hardware_verified = true;
    status.feedback_valid = true;
    for (int i = 0; i < 4; i++) {
        status.current_spool_lengths_m[i] = 0.350f;
        status.measured_cable_rates_m_s[i] = 0.020f;
    }
    cdpr_format_feedback_payload(&status, &payload);
    TEST_ASSERT(payload.is_valid, "Convention: is_valid is true when verified");
    TEST_ASSERT(strcmp(payload.frame_id, CDPR_FEEDBACK_FRAME_MEASURED) == 0,
                "Convention: frame_id is cdpr_measured");
    TEST_ASSERT(payload.num_joints == 4, "Convention: num_joints is 4");
}

int main(void) {
    printf("===================================================\n");
    printf("   CDPR Feedback Interface & Units Verification    \n");
    printf("===================================================\n");

    test_feedback_null_handling();
    test_feedback_unverified_hardware_cases();
    test_feedback_valid_and_units();
    test_unavailable_feedback_not_published_as_zeros();
    test_explicit_validity_convention();

    printf("\n===================================================\n");
    printf(" Results: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("===================================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
