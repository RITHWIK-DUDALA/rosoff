# Hardware Setup & Capability Specifications

## 1. Hardware Capability Status

In strict adherence to **Rule 0.2 (No Invented Hardware Specifications)**, all hardware capabilities, electrical ratings, communication protocols, and drive parameters are categorized explicitly by verification state:

| Component | Status | Required Confirmation |
|---|---|---|
| **Frame & Enclosure** | **VERIFIED (Provisional CAD)** | $500 \times 400 \times 120\text{ mm}$ outer aluminum extrusion envelope. |
| **End-Effector Platform** | **VERIFIED (Provisional CAD)** | $100 \times 80 \times 6\text{ mm}$ plate, mass $0.5\text{ kg}$, anti-rotation guide rods. |
| **Microcontroller** | **UNVERIFIED** | ESP32-WROOM-32D / ESP32-S3 model and pinout. |
| **Servo Motors (x4)** | **UNKNOWN / UNVERIFIED** | Model, continuous/peak torque, max RPM, voltage/current rating. |
| **Servo Drives (x4)** | **UNKNOWN / UNVERIFIED** | Model, command interface (Step/Dir, CANopen, RS-485 Modbus, Analog). |
| **Encoders / Sensors** | **UNKNOWN / UNVERIFIED** | Absolute vs Incremental, resolution (PPR / CPR), feedback path. |
| **Power Supply** | **UNKNOWN / UNVERIFIED** | DC Bus voltage (e.g. 24V or 48V), peak current capacity. |
| **Emergency Stop Circuit** | **UNVERIFIED** | Hardwired dual-channel STO or relay contactor. |
| **Limit Switches / Homing** | **UNVERIFIED** | Optical/inductive homing switches or mechanical stall-detection. |

---

## 2. Mechanical Mapping & Spool Winding

### 2.1 Spool and Winch Parameters
- **Nominal Spool Drum Radius:** $r_{\text{spool}} = 10.0\text{ mm}$ ($0.010\text{ m}$).
- **Cable Circumference per Turn:** $2 \pi r_{\text{spool}} \approx 62.83\text{ mm/rev}$.
- **Rotational Speed Conversion:**
  $$\dot{\theta} = \frac{\dot{l}}{r_{\text{spool}}} \quad [\text{rad/s}], \qquad \text{RPM} = \dot{\theta} \cdot \frac{60}{2\pi} \approx \dot{l} \cdot 954.93$$
  For nominal $v_{\text{platform}} = 100\text{ mm/s}$, required motor speed is typically $\le 100\text{ RPM}$, well within the provisional $300\text{ RPM}$ ceiling.

### 2.2 Cable & Motor Orientation Mapping
Because motors are mounted on opposite sides of the frame, winding directions must be explicitly mapped to ensure positive motor rotation pulls cable (shortens cable length):

| Cable | Anchor Position $(X, Y)$ | Motor ID | Mounting Corner | Positive Rotation Winding Direction |
|---|---|---|---|---|
| **C1** | $(-250, +200)\text{ mm}$ | Motor 1 | Top-Left | Clockwise (CW) reels in |
| **C2** | $(+250, +200)\text{ mm}$ | Motor 2 | Top-Right | Counter-Clockwise (CCW) reels in |
| **C3** | $(+250, -200)\text{ mm}$ | Motor 3 | Bottom-Right | Counter-Clockwise (CCW) reels in |
| **C4** | $(-250, -200)\text{ mm}$ | Motor 4 | Bottom-Left | Clockwise (CW) reels in |

> **Crucial Rule:** Never assume all four motors share identical direction signs. The direction multiplier (`+1` or `-1`) must be calibrated independently per motor before coordinated movement.

---

## 3. Drive Interface Boundaries & Abstraction

Because the physical drives are not yet confirmed, the software enforces an abstract driver layer (`RobotDriver` in Python, `servo_driver_interface.h` in C). 

### 3.1 Potential Drive Protocol Architectures
1. **Pulse & Direction (Step/Dir):**
   - Controlled via ESP32 hardware timers / RMT / MCPWM peripheral.
   - Low latency, but no bidirectional drive status or fault codes unless auxiliary alarm lines are wired.
2. **CAN / CANopen (ISO 11898):**
   - High reliability, native differential bus, standard CiA 402 motion profile (Profile Position, Profile Velocity, Torque).
   - ESP32 TWAI (Two-Wire Automotive Interface) controller with external CAN transceiver (e.g. SN65HVD230).
3. **RS-485 / Modbus RTU:**
   - Multi-drop serial bus. Update rate typically limited to 20-50 Hz across 4 axes.

---

## 4. Hardware Verification Checklist (Prerequisites to Arming)

Before transitioning `hardware_motion_enabled` from `false` to `true` in `config/robot_config.yaml`, the following checklist must be fully verified and recorded:

- [ ] **Datasheet Review:** Confirm motor model number, rated current, continuous torque, and peak torque.
- [ ] **Drive Manual Review:** Confirm drive model, control protocol, enable/disable logic, and alarm registers.
- [ ] **E-Stop Verification:** Hardwired E-Stop button installed, cutting drive bus power or triggering verified Safe Torque Off (STO).
- [ ] **Encoder Calibration:** Confirm encoder counts per revolution (CPR) and verify spool displacement against a physical caliper.
- [ ] **Single-Motor Direction Test:** Each winch tested independently at low speed ($< 10\text{ RPM}$) with manual slack to verify CW/CCW sign conventions.
- [ ] **Homing / Zero Reference:** Confirm physical homing reference procedure (micro-switch or optical sensor).
- [ ] **Hardware Profile Update:** Update `config/hardware_profile.example.yaml` with verified parameters and rename to active `config/hardware_profile.yaml`.
