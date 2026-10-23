# CDPR Diagnostics and Health Telemetry Message

std_msgs/Header header

# 2-Norm Jacobian Condition Number (ill-conditioning detection)
float64 condition_number

# Forward kinematics residual norm in meters
float64 fk_residual_norm_m

# Geometric workspace safety flag
bool workspace_safe

# Tension equilibrium feasibility flag
bool tension_feasible

# Active system fault strings
string[] active_faults

# Active operating driver name
string active_driver

# Hardware readiness flag
bool hardware_ready

# Missing hardware prerequisites checklist
string[] missing_prerequisites
