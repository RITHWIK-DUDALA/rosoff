#ifndef CDPR_FEEDBACK_INTERFACE_H
#define CDPR_FEEDBACK_INTERFACE_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "servo_driver_interface.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CDPR_FEEDBACK_FRAME_UNAVAILABLE  "cdpr_feedback_unavailable"
#define CDPR_FEEDBACK_FRAME_MEASURED     "cdpr_measured"

/**
 * Standardized feedback payload for ROS JointState serialization.
 * Explicitly separates valid, verified measurements from unavailable telemetry.
 *
 * ENCODERLESS & UNVERIFIED HARDWARE CONVENTION:
 * Currently, no physical feedback encoders (optical, magnetic, or resolver) are wired or calibrated.
 * Therefore, physical cable lengths, cable linear payout rates, and platform positions are UNAVAILABLE.
 *
 * To prevent dangerous misinterpretation by downstream ROS 2 nodes (e.g. forward kinematics solvers):
 * 1. Fabricated nominal measurements or four zero-valued measurements ([0,0,0,0]) MUST NEVER be published.
 * 2. When feedback is unavailable:
 *    - `is_valid` is set to FALSE.
 *    - `num_joints` is set to 0 (resulting in empty `position`, `velocity`, `effort`, and `name` sequences in `JointState`).
 *    - `frame_id` is set to CDPR_FEEDBACK_FRAME_UNAVAILABLE ("cdpr_feedback_unavailable").
 *    - A separate explicit status topic `/cdpr/feedback/valid` (std_msgs/msg/Bool) publishes `data: false`.
 * 3. An empty sequence alone is NOT the sole validity flag; downstream nodes must inspect both `header.frame_id`
 *    and the `/cdpr/feedback/valid` topic.
 *
 * Unit Specification (SI Standard):
 * - lengths_m: Cable lengths in METERS [m] (C1..C4: TL, TR, BR, BL).
 * - rates_m_s: Cable linear payout/retraction rate in METERS PER SECOND [m/s].
 *   SAFETY PROHIBITION: MOTOR SHAFT ROTATIONAL SPEED (RPM) MUST NEVER BE MAPPED TO LINEAR VELOCITY.
 * - tensions_n: Cable tensions in NEWTONS [N].
 * - is_valid: True only when verified hardware feedback is actively read from genuine calibrated sensors.
 */
typedef struct {
    double lengths_m[4];
    double rates_m_s[4];
    double tensions_n[4];
    size_t num_joints;       /* 4 if valid; 0 if unavailable/unverified */
    const char* frame_id;    /* "cdpr_feedback_unavailable" or "cdpr_measured" */
    bool is_valid;
} cdpr_feedback_payload_t;

/**
 * Formats feedback payload from servo status.
 * Enforces fail-closed feedback safety:
 * - If status is NULL, unverified, or feedback_valid is false:
 *   num_joints is set to 0, is_valid is false, frame_id is "cdpr_feedback_unavailable".
 * - Raw motor RPM is never published as velocity.
 */
void cdpr_format_feedback_payload(
    const cdpr_servo_status_t* status,
    cdpr_feedback_payload_t* out_payload
);

#ifdef __cplusplus
}
#endif

#endif // CDPR_FEEDBACK_INTERFACE_H
