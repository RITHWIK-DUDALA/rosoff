#ifndef CDPR_SERVO_DRIVER_INTERFACE_H
#define CDPR_SERVO_DRIVER_INTERFACE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Result codes for the servo driver interface.
 * Explicitly distinguishes unsupported/unverified operations from success.
 */
typedef enum {
    CDPR_SERVO_OK = 0,
    CDPR_SERVO_ERR_UNVERIFIED_HARDWARE  = -1,
    CDPR_SERVO_ERR_INVALID_ARG          = -2,
    CDPR_SERVO_ERR_TORQUE_NOT_PERMITTED = -3,
    CDPR_SERVO_ERR_HARDWARE_FAULT       = -4
} cdpr_servo_result_t;

/**
 * Protocol-Agnostic Servo Driver Interface Boundary.
 * Enforces fail-closed safety (Master Specification Section 4 & 8):
 * - NOTICE: The servo interface is currently a SOFTWARE STUB.
 *   Physical motor drivers, communication buses (CAN/RS485), optical/magnetic encoders,
 *   and hardware safety circuits remain unverified, disconnected, and unpowered.
 * - Motor torque remains software-disabled (fail-closed).
 * - Real sensor measurements are NOT available; feedback is explicitly flagged invalid.
 * - Software command zeroing is NEVER claimed to be certified physical Safe Torque Off (STO).
 */
typedef struct {
    bool is_hardware_verified;
    bool torque_permitted;
    bool torque_enabled;
    bool feedback_valid;
    float current_spool_lengths_m[4];   /* Cable lengths in meters [m] */
    float measured_cable_rates_m_s[4];  /* Linear payout/retraction rate in m/s */
    float current_rpms[4];              /* Raw actuator rotational speed in RPM (separate from linear velocity) */
    uint32_t active_drive_faults;
} cdpr_servo_status_t;

/**
 * Initializes physical drive peripheral interface.
 * Since drive model, bus protocol (CAN-FD / RS485), and STO wiring are unverified,
 * this function sets is_hardware_verified = false and returns CDPR_SERVO_ERR_UNVERIFIED_HARDWARE.
 * No hardware feedback or actuation is claimed.
 */
static inline cdpr_servo_result_t cdpr_servo_init(cdpr_servo_status_t* status) {
    if (!status) return CDPR_SERVO_ERR_INVALID_ARG;
    status->is_hardware_verified = false;
    status->torque_permitted = false;
    status->torque_enabled = false;
    status->feedback_valid = false;
    for (int i = 0; i < 4; i++) {
        status->current_spool_lengths_m[i] = 0.0f;  /* Unverified: do NOT fabricate nominal length */
        status->measured_cable_rates_m_s[i] = 0.0f; /* Unverified: do NOT fabricate linear velocity */
        status->current_rpms[i] = 0.0f;             /* Unverified: raw shaft speed */
    }
    status->active_drive_faults = 0;
    return CDPR_SERVO_ERR_UNVERIFIED_HARDWARE;
}

/**
 * Enables or disables motor drive torque.
 * SAFETY RULE: Strictly refuses torque enable because physical drive hardware,
 * motor specifications, and E-Stop wiring are unverified.
 * Only software disarm (enable == false) is permitted.
 */
static inline cdpr_servo_result_t cdpr_servo_enable_torque(cdpr_servo_status_t* status, bool enable) {
    if (!status) return CDPR_SERVO_ERR_INVALID_ARG;
    if (enable) {
        status->torque_enabled = false;
        return CDPR_SERVO_ERR_UNVERIFIED_HARDWARE;
    } else {
        status->torque_enabled = false;
        return CDPR_SERVO_OK;
    }
}

/**
 * Issues velocity or rate commands to the 4 servo winches.
 * Rejects commands if torque is not enabled or hardware is unverified.
 */
static inline cdpr_servo_result_t cdpr_servo_command_rates(cdpr_servo_status_t* status, const float rates_m_s[4]) {
    if (!status || !rates_m_s) return CDPR_SERVO_ERR_INVALID_ARG;
    if (!status->is_hardware_verified || !status->torque_enabled) {
        return CDPR_SERVO_ERR_TORQUE_NOT_PERMITTED;
    }
    return CDPR_SERVO_OK;
}

/**
 * Reads actual hardware feedback (encoders, bus status).
 * Returns CDPR_SERVO_ERR_UNVERIFIED_HARDWARE and marks feedback_valid = false.
 * Never fabricates nominal spool lengths or encoder readings.
 */
static inline cdpr_servo_result_t cdpr_servo_read_status(cdpr_servo_status_t* status) {
    if (!status) return CDPR_SERVO_ERR_INVALID_ARG;
    status->feedback_valid = false;
    return CDPR_SERVO_ERR_UNVERIFIED_HARDWARE;
}

/**
 * Emergency software command zeroing.
 * Clamps target velocities to zero and sets torque_enabled = false.
 * NOTE: This is software command zeroing, NOT a certified physical Safe Torque Off (STO) circuit
 * or certified emergency stop relay.
 */
static inline void cdpr_servo_emergency_safe_stop(cdpr_servo_status_t* status) {
    if (status) {
        status->torque_enabled = false;
        for (int i = 0; i < 4; i++) {
            status->measured_cable_rates_m_s[i] = 0.0f;
            status->current_rpms[i] = 0.0f;
        }
    }
}

#ifdef __cplusplus
}
#endif

#endif // CDPR_SERVO_DRIVER_INTERFACE_H
