# PROJECT W.A.L.L. — Explicit Engineering Assumptions Log
*(Complies with Section 0.3: No Undocumented Assumptions)*

| Parameter | Value / Default | Engineering Justification | Validation Method |
| :--- | :--- | :--- | :--- |
| **Surface Flatness** | $\pm 3.0\text{ mm}$ over $800 \times 600\text{ mm}$ | Required for non-contact inkjet standoff ($2.0 \pm 1.0\text{ mm}$). | Compliant standoff roller deflection measurement. |
| **Pneumatic Suction Threshold** | $\ge -60\text{ kPa}$ relative gauge pressure | Ensures $F_{hold} \ge 120\text{ N}$ against shear loads on smooth panel/glass. | Pressure transducer vacuum check prior to arming motors. |
| **Cable Elastic Modulus** | $E = 100\text{ GPa}$ for Dyneema SK75 | UHMWPE exhibits consistent high modulus after initial bedding-in pre-stretch. | Inline load cell vs forward kinematics discrepancy. |
| **Minimum Cable Tension** | $T_{min} = 2.0\text{ N}$ | Prevents cable catenary sag and loss of position authority. | Static QP tension solver constraint & load cell interlock. |
| **Maximum Cable Tension** | $T_{max} = 50.0\text{ N}$ | Ensures $\ge 15\times$ safety factor below Dyneema breaking strength (950 N). | Overload threshold shutdown trigger. |
| **Fixed Timestep Engine** | $\Delta t = 0.033\text{ s}$ (30 Hz) | Decouples physical simulation from UI frame rendering jitter. | Deterministic test verification across platforms. |

