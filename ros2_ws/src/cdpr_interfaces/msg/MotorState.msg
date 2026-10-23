# 4-Actuator Motor & Spool State Message

std_msgs/Header header

# Actuator channel identifiers
string[4] channel_names

# Spool drum angles in radians
float64[4] drum_angles_rad

# Motor rotational speeds in RPM
float64[4] motor_speeds_rpm

# Motor estimated or measured torques in Nm
float64[4] motor_torques_nm

# Saturation flags
bool[4] speed_saturated
bool[4] torque_saturated

# Fault codes per channel ("OK", "SPEED_LIMIT", "TORQUE_LIMIT", etc.)
string[4] channel_fault_codes

# Hardware torque enabled flag (Safe Torque Off state)
bool torque_enabled
