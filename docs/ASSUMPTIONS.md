# PROVISIONAL PARAMETERS AND MODEL ASSUMPTIONS (ASSUMPTIONS.md)

## 1. Summary of Provisional Physical Parameters

The parameters listed below are engineering estimates adopted for simulation development and numerical validation. They have not yet been calibrated against manufactured physical hardware:

| Parameter | Provisional Value | Physical Unit | Status / Verification Needed |
|---|---|---|---|
| Motor Maximum Speed | 300.0 | RPM | Provisional specification. Requires servo supplier datasheet and no-load/loaded RPM verification. |
| Motor Maximum Torque | 0.40 | Nm | Provisional specification. Requires servo thermal rating and continuous vs peak torque curve. |
| Drum Spool Radius | 10.0 | mm (0.010 m) | Geometric nominal assumption. Assumes single-layer helical groove or negligible multilayer buildup. |
| Drum Inertia | $1.0 \times 10^{-5}$ | $\text{kg}\cdot\text{m}^2$ | Estimated for aluminium spool drum. Must be computed from final CAD geometry. |
| Transmission Efficiency ($\eta$) | 0.90 | dimensionless | Estimated for direct-drive / low-friction bearing spool. |
| Cable Maximum Tension | 300.0 | N | Provisional breaking/safe working load for 1 mm Dyneema/UHMWPE cord. |
| Minimum Operating Tension | 2.0 | N | Minimum pretension to prevent cable sagging and slack spooling. |
| Guide Rod Diameter | 10.0 | mm | Dual precision linear shafts. |
| Bed/Guide Friction ($\mu$) | 0.05 | dimensionless | Dry linear ball bushing / PTFE sliding friction assumption. |
| Moving Platform Mass | 0.50 | kg | Mass including structural plate, eyelets, and linear bearings. |

---

## 2. Idealizations and Limitations

1. **Massless, Rigid Cables**:
   - In the current model, cables are assumed rigid (infinite Young's modulus) and massless (no catenary sag).
   - Dynamic cable vibrations and cable stretch under load ($\Delta L = \frac{T L}{E A}$) are omitted from the primary kinematic integration.
2. **Horizontal Plane Support**:
   - Gravity ($g = 9.81\text{ m/s}^2$) acts along the $-Z$ axis and is assumed to be fully reacted by the linear guide rods.
3. **Anti-Rotation Guide Constraint**:
   - The anti-rotation guide mechanically eliminates pitch, roll, and yaw rotation. In real physical mechanisms, mechanical clearances and rod deflection can introduce small rotational compliance.
4. **Spool Fleet Angle and Wrapping**:
   - Cables are assumed to depart from the drum centre at fixed anchor coordinates $A_i$. Axial travel across a grooved drum is not currently modeled.
