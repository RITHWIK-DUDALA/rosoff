#include "cdpr_feedback_interface.h"
#include <string.h>

void cdpr_format_feedback_payload(
    const cdpr_servo_status_t* status,
    cdpr_feedback_payload_t* out_payload
) {
    if (!out_payload) return;

    memset(out_payload, 0, sizeof(cdpr_feedback_payload_t));

    /* Strict fail-closed feedback gate:
     * Telemetry is marked UNAVAILABLE unless hardware is genuinely verified and feedback is actively valid.
     */
    if (!status || !status->is_hardware_verified || !status->feedback_valid) {
        out_payload->is_valid = false;
        out_payload->num_joints = 0;
        out_payload->frame_id = CDPR_FEEDBACK_FRAME_UNAVAILABLE;
        return;
    }

    /* Valid verified telemetry */
    out_payload->is_valid = true;
    out_payload->num_joints = 4;
    out_payload->frame_id = CDPR_FEEDBACK_FRAME_MEASURED;

    for (size_t i = 0; i < 4; i++) {
        out_payload->lengths_m[i] = (double)status->current_spool_lengths_m[i];
        out_payload->rates_m_s[i] = (double)status->measured_cable_rates_m_s[i];
        out_payload->tensions_n[i] = 0.0;
    }
}
