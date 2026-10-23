#ifndef CDPR_APP_STATE_H
#define CDPR_APP_STATE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Deterministic Finite State Machine for CDPR ESP32 Firmware.
 * Per Section 12.4:
 * BOOT -> INITIALIZING -> WAITING_FOR_AGENT -> CONNECTED -> DRIVE_STATUS_CHECK -> READY -> MOTION_ENABLED -> FAULT / SAFE_STOP
 */
typedef enum {
    STATE_BOOT = 0,
    STATE_INITIALIZING,
    STATE_WAITING_FOR_AGENT,
    STATE_CONNECTED,
    STATE_DRIVE_STATUS_CHECK,
    STATE_READY,
    STATE_MOTION_ENABLED,
    STATE_FAULT,
    STATE_SAFE_STOP
} cdpr_firmware_state_t;

/**
 * Returns human-readable string representation of the firmware state.
 */
static inline const char* cdpr_state_to_str(cdpr_firmware_state_t state) {
    switch (state) {
        case STATE_BOOT:                 return "BOOT";
        case STATE_INITIALIZING:         return "INITIALIZING";
        case STATE_WAITING_FOR_AGENT:    return "WAITING_FOR_AGENT";
        case STATE_CONNECTED:            return "CONNECTED";
        case STATE_DRIVE_STATUS_CHECK:   return "DRIVE_STATUS_CHECK";
        case STATE_READY:                return "READY";
        case STATE_MOTION_ENABLED:       return "MOTION_ENABLED";
        case STATE_FAULT:                return "FAULT";
        case STATE_SAFE_STOP:            return "SAFE_STOP";
        default:                         return "UNKNOWN";
    }
}

/**
 * Validates state transition. Returns true if transition is legally allowed.
 * Strictly forbids automatic transition from WAITING_FOR_AGENT/CONNECTED directly to MOTION_ENABLED.
 */
static inline bool cdpr_is_valid_transition(cdpr_firmware_state_t from, cdpr_firmware_state_t to) {
    if (to == STATE_FAULT || to == STATE_SAFE_STOP) {
        return true; // Any state can emergency transit to SAFE_STOP or FAULT
    }

    switch (from) {
        case STATE_BOOT:
            return (to == STATE_INITIALIZING);
        case STATE_INITIALIZING:
            return (to == STATE_WAITING_FOR_AGENT);
        case STATE_WAITING_FOR_AGENT:
            return (to == STATE_CONNECTED);
        case STATE_CONNECTED:
            return (to == STATE_DRIVE_STATUS_CHECK || to == STATE_WAITING_FOR_AGENT);
        case STATE_DRIVE_STATUS_CHECK:
            return (to == STATE_READY || to == STATE_CONNECTED);
        case STATE_READY:
            return (to == STATE_MOTION_ENABLED || to == STATE_WAITING_FOR_AGENT);
        case STATE_MOTION_ENABLED:
            return (to == STATE_READY || to == STATE_SAFE_STOP);
        case STATE_SAFE_STOP:
            return (to == STATE_WAITING_FOR_AGENT || to == STATE_READY);
        case STATE_FAULT:
            return (to == STATE_INITIALIZING); // Hard reset required
        default:
            return false;
    }
}

#ifdef __cplusplus
}
#endif

#endif // CDPR_APP_STATE_H
