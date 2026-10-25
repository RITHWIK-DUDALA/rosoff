#include "cdpr_command_validator.h"
#include <math.h>

void cdpr_command_tracker_init(cdpr_command_tracker_t* tracker) {
    if (tracker) {
        tracker->last_sec = 0;
        tracker->last_nanosec = 0;
        tracker->has_received_first = false;
    }
}

cdpr_cmd_validation_result_t cdpr_validate_command(
    const double* lengths_m,
    size_t num_lengths,
    const double* rates_m_s,
    size_t num_rates,
    int32_t stamp_sec,
    uint32_t stamp_nanosec,
    cdpr_firmware_state_t current_state,
    cdpr_command_tracker_t* tracker
) {
    if (!lengths_m) {
        return CDPR_CMD_ERR_NULL_PTR;
    }

    if (num_lengths != 4) {
        return CDPR_CMD_ERR_INVALID_SIZE;
    }

    if (rates_m_s != NULL && num_rates != 4 && num_rates != 0) {
        return CDPR_CMD_ERR_INVALID_SIZE;
    }

    // State gate: Commands can only be accepted in MOTION_ENABLED or READY.
    // In READY, the message is validated structurally, but actuators are not driven.
    if (current_state != STATE_MOTION_ENABLED && current_state != STATE_READY) {
        return CDPR_CMD_ERR_FORBIDDEN_STATE;
    }

    // Length sanity checks
    for (size_t i = 0; i < 4; i++) {
        double l = lengths_m[i];
        if (isnan(l) || isinf(l)) {
            return CDPR_CMD_ERR_NAN_OR_INF;
        }
        if (l < (double)CDPR_MIN_CABLE_LENGTH_M || l > (double)CDPR_MAX_CABLE_LENGTH_M) {
            return CDPR_CMD_ERR_LENGTH_OUT_OF_BOUNDS;
        }
    }

    // Rate sanity checks
    if (rates_m_s != NULL && num_rates == 4) {
        for (size_t i = 0; i < 4; i++) {
            double r = rates_m_s[i];
            if (isnan(r) || isinf(r)) {
                return CDPR_CMD_ERR_NAN_OR_INF;
            }
            if (fabs(r) > (double)CDPR_MAX_CABLE_RATE_M_S) {
                return CDPR_CMD_ERR_RATE_OUT_OF_BOUNDS;
            }
        }
    }

    // Timestamp freshness & monotonicity check
    if (tracker != NULL && (stamp_sec != 0 || stamp_nanosec != 0)) {
        if (tracker->has_received_first) {
            if (stamp_sec < tracker->last_sec) {
                return CDPR_CMD_ERR_STALE_TIMESTAMP;
            }
            if (stamp_sec == tracker->last_sec && stamp_nanosec <= tracker->last_nanosec) {
                return CDPR_CMD_ERR_STALE_TIMESTAMP;
            }
        }
        tracker->last_sec = stamp_sec;
        tracker->last_nanosec = stamp_nanosec;
        tracker->has_received_first = true;
    }

    return CDPR_CMD_VALID;
}

const char* cdpr_cmd_validation_result_to_str(cdpr_cmd_validation_result_t res) {
    switch (res) {
        case CDPR_CMD_VALID:                    return "VALID";
        case CDPR_CMD_ERR_NULL_PTR:             return "NULL_POINTER";
        case CDPR_CMD_ERR_INVALID_SIZE:         return "INVALID_SIZE_NOT_4";
        case CDPR_CMD_ERR_NAN_OR_INF:           return "NUMERIC_NAN_OR_INF";
        case CDPR_CMD_ERR_LENGTH_OUT_OF_BOUNDS: return "LENGTH_OUT_OF_BOUNDS";
        case CDPR_CMD_ERR_RATE_OUT_OF_BOUNDS:   return "RATE_OUT_OF_BOUNDS";
        case CDPR_CMD_ERR_STALE_TIMESTAMP:      return "STALE_TIMESTAMP";
        case CDPR_CMD_ERR_FORBIDDEN_STATE:      return "FORBIDDEN_STATE";
        default:                                return "UNKNOWN_ERROR";
    }
}
