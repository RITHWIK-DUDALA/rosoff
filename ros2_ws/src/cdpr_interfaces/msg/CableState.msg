# 4-Cable CDPR Cable State Message
# Cables indexed C1..C4 (Top-Left, Top-Right, Bottom-Right, Bottom-Left)

std_msgs/Header header

# Cable lengths in meters
float64[4] lengths_m

# Cable payout/retraction velocity in m/s (positive = payout, negative = retraction)
float64[4] rates_m_s

# Cable tensions in Newtons (unilateral T >= T_min > 0)
float64[4] tensions_n

# Tension feasibility flag
bool tension_feasible

# Measurement provenance: "simulated", "measured", "estimated"
string provenance
