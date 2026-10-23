# Planar CDPR Robot State Message
# Coordinate Frame: 'cdpr_frame_center' (SI units: meters, m/s, m/s^2)

std_msgs/Header header

# Operating Mode: "SIMULATION", "HARDWARE", "HARDWARE_DISABLED"
string operating_mode

# Measurement Provenance: "simulated", "measured", "estimated", "unavailable"
string position_provenance

# Motion Controller State: "IDLE", "MOVING", "PAUSED", "STOPPED", "FAULT", "ESTOP"
string controller_mode

# Homing State: "HOMED", "UNREFERENCED", "HOMING_IN_PROGRESS", "FAULT"
string homing_state

# Planar Coordinates
geometry_msgs/Point commanded_position
geometry_msgs/Vector3 commanded_velocity
geometry_msgs/Vector3 commanded_acceleration

geometry_msgs/Point estimated_position
bool estimated_position_valid

# Tracking Error: norm of ||commanded - estimated|| in meters
float64 tracking_error_m
bool tracking_error_valid

# Freshness flag: True if feedback received within timeout threshold
bool is_fresh
