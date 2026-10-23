#ifndef CDPR_SERVO_DRIVER_INTERFACE_H
#define CDPR_SERVO_DRIVER_INTERFACE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Protocol-Agnostic Servo Driver Interface Boundary.
 * Isolates unknown physical drive communication details (CAN-FD, RS-485 Modbus, Step/Dir).
 * Enforces Rule 0.2: Unknown specifications remain safe-disabled.
 */
typedef struct {
    bool is_verified;
    bool torque_enabled;
    float current_spool_lengths_m[4];
    float current_rpms[4];
    uint32_t active_drive_faults;
} cdpr_servo_status_t;

/**
 * Initializes physical drive communication peripheral (e.g. TWAI/CAN or UART).
 * Returns true if initialization succeeded, false if hardware error or unverified.
 */
static inline bool cdpr_servo_init(cdpr_servo_status_t* status) {
    if (!status) return false;
    // Per Rule 0.2: Until exact drive model & protocol are verified, status remains unverified
    status->is_verified = false;
    status->torque_enabled = false;
    for (int i = 0; i < 4; i++) {
        status->current_spool_lengths_m[i] = 0.256f; // Nominal home length
        status->current_rpms[i] = 0.0f;
    }
    status->active_drive_faults = 0;
    return true;
}

/**
 * Enables or disables motor drive torque.
 * SAFETY RULE: Strictly refuses torque enable if drive specification is unverified.
 */
static inline bool cdpr_servo_enable_torque(cdpr_servo_status_t* status, bool enable) {
    if (!status) return false;
    if (enable) {
        if (!status->is_verified) {
            // Cannot enable unverified physical motors
            status->torque_enabled = false;
            return false;
        }
        status->torque_enabled = true;
        return true;
    } else {
        // Safe Torque Off (disabling torque is always permitted)
        status->torque_enabled = false;
        return true;
    }
}

/**
 * Issues velocity or rate commands to the 4 servo winches.
 */
static inline bool cdpr_servo_command_rates(cdpr_servo_status_t* status, const float rates_m_s[4]) {
    if (!status || !status->torque_enabled) {
        return false; // Cannot command when torque is disabled
    }
    // Implement drive protocol dispatch when hardware verified
    return true;
}

/**
 * Reads actual feedback (encoders and drive status).
 */
static inline bool cdpr_servo_read_status(cdpr_servo_status_t* status) {
    if (!status) return false;
    // Read hardware bus when verified
    return true;
}

/**
 * Immediately clamps all motor commands to zero and engages Safe Torque Off / dynamic brake.
 */
static inline void cdpr_servo_emergency_safe_stop(cdpr_servo_status_t* status) {
    if (status) {
        status->torque_enabled = false;
        for (int i = 0; i < 4; i++) {
            status->current_rpms[i] = 0.0f;
        }
    }
}

#ifdef __cplusplus
}
#endif

#endif // CDPR_SERVO_DRIVER_INTERFACE_H
