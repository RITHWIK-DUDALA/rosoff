# HARDWARE INTEGRATION AND COMPONENT SELECTION GUIDE (HARDWARE.md)

This document specifies the technical criteria for transferring the CDPR software simulation model to physical testbed hardware.

## 1. Actuator and Servo Motor Selection
- **Continuous Torque**: $\ge 0.40\text{ Nm}$ continuous rated torque at rated speed.
- **Maximum Speed**: $\ge 300\text{ RPM}$ ($31.4\text{ rad/s}$).
- **Encoder Resolution**: At drum radius $r = 10\text{ mm}$, $1^\circ$ of rotation corresponds to $0.175\text{ mm}$ of cable displacement. To achieve $< 0.05\text{ mm}$ Cartesian accuracy, an encoder with $\ge 2048\text{ CPR}$ (or absolute 14-bit magnetic encoder) is required.
- **Communication Bus**: CAN-FD, EtherCAT, or high-speed RS-485 (1 Mbps+) with deterministic cycle times $\le 2\text{ ms}$ (500 Hz). Recommended off-the-shelf options: Smart brushless servo actuators (e.g. ODrive-driven BLDC motors, Dynamixel XM/XH series, or Stepper Servos with closed-loop FOC).

## 2. Spool Drum Design
- **Pitch Diameter**: $20.0\text{ mm}$ (effective radius $r = 10.0\text{ mm}$).
- **Cable Grooving**: Helical spiral grooved drum to prevent overlapping wraps, which would cause an unmodeled time-varying drum radius $r(\theta)$.
- **Drum Width**: Maximum travel across workspace is $\approx 250\text{ mm}$. With $10\text{ mm}$ radius ($62.8\text{ mm/rev}$), this requires $\approx 4\text{ revolutions}$. A drum width of $15\text{ mm}$ with $1.5\text{ mm}$ pitch is sufficient.

## 3. Cable Selection
- **Material**: Ultra-High Molecular Weight Polyethylene (UHMWPE / Dyneema SK75/SK78) 12-strand braided line or coated stainless steel aircraft cable (7x7 or 7x19 construction).
- **Diameter**: $0.8\text{ mm} - 1.2\text{ mm}$.
- **Breaking Strength**: $\ge 800\text{ N}$ (providing a safety factor $\ge 2.5$ over the 300 N peak load).

## 4. Mechanical Frame and Anti-Rotation Guide
- **Extrusion**: 2020 or 2040 V-slot aluminum extrusion forming a $500 \times 400\text{ mm}$ inner rectangle.
- **Guide Rods**: Hardened ground steel or carbon fiber shafts $\varnothing 10\text{ mm}$ with linear ball bearings (LM10UU) or dry polymer bushings (Igus RJ4JP).
- **Plate**: 6 mm CNC machined 6061-T6 aluminum or 3D printed carbon-fiber reinforced PETG/Nylon.
