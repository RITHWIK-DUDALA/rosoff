#ifndef CDPR_COMMAND_VALIDATOR_H
#define CDPR_COMMAND_VALIDATOR_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "app_state.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Geometric bounds for the 2T Planar CDPR (500x400 mm frame, 100x80 mm platform).
 * Section 4.3 & 12: Cable limits derived from verified geometry.
 */
#define CDPR_MIN_CABLE_LENGTH_M   0.050f   /* 50 mm clearance from anchor */
#define CDPR_MAX_CABLE_LENGTH_M   0.700f   /* Frame diagonal is ~0.640 m */
#define CDPR_MAX_CABLE_RATE_M_S   0.500f   /* 500 mm/s winch rate clamp */

typedef enum {
    CDPR_CMD_VALID = 0,
    CDPR_CMD_ERR_NULL_PTR = -1,
    CDPR_CMD_ERR_INVALID_SIZE = -2,
    CDPR_CMD_ERR_NAN_OR_INF = -3,
    CDPR_CMD_ERR_LENGTH_OUT_OF_BOUNDS = -4,
    CDPR_CMD_ERR_RATE_OUT_OF_BOUNDS = -5,
    CDPR_CMD_ERR_STALE_TIMESTAMP = -6,
    CDPR_CMD_ERR_FORBIDDEN_STATE = -7
} cdpr_cmd_validation_result_t;

typedef struct {
    int32_t last_sec;
    uint32_t last_nanosec;
    bool has_received_first;
} cdpr_command_tracker_t;

/**
 * Initializes the command tracker.
 */
void cdpr_command_tracker_init(cdpr_command_tracker_t* tracker);

/**
 * Validates cable length and rate vectors.
 * Checks for NaN, Inf, geometric limits, rate limits, timestamp monotonicity, and state gate.
 */
cdpr_cmd_validation_result_t cdpr_validate_command(
    const double* lengths_m,
    size_t num_lengths,
    const double* rates_m_s,
    size_t num_rates,
    int32_t stamp_sec,
    uint32_t stamp_nanosec,
    cdpr_firmware_state_t current_state,
    cdpr_command_tracker_t* tracker
);

/**
 * Returns human-readable error description for validation result.
 */
const char* cdpr_cmd_validation_result_to_str(cdpr_cmd_validation_result_t res);

#ifdef __cplusplus
}
#endif

#endif // CDPR_COMMAND_VALIDATOR_H
