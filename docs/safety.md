# Safety Architecture & Risk Mitigation

## 1. Safety Philosophy

In accordance with **Rule 0.5 (Safety takes precedence over convenience)**:
- Never bypass a hardware fault, drive fault, workspace constraint, motor limit, or emergency-stop condition to make a demonstration appear successful.
- Never automatically enable motors when the application starts or reconnects.
- Never treat a browser button, Python flag, ROS 2 topic, or Wi-Fi connection as a substitute for an independent physical emergency-stop mechanism.
- The software must fail safely when communication or state estimation becomes unreliable.

---

## 2. Hazard Identification & Risk Assessment

| Hazard ID | Description | Severity | Software Mitigation | Physical / Hardware Mitigation |
|---|---|---|---|---|
| **H1: Cable Snap / Whiplash** | High cable tension exceeding yield strength. | High | Software tension ceiling ($300\text{ N}$) and torque limits ($0.4\text{ Nm}$). | Kevlar/Dyneema cable with safety factor $\ge 5$; protective polycarbonate enclosure. |
| **H2: Frame Collision** | Platform driving into aluminum perimeter. | Medium | Software workspace envelope bounding $X \in [-180, +180]\text{ mm}$, $Y \in [-140, +140]\text{ mm}$ (20 mm clearance). | Mechanical rubber bumper stops on rails. |
| **H3: Spool Pinch Point** | Fingers caught in high-speed spinning drums. | High | Actuator speed ceiling ($300\text{ RPM}$); manual jog rate $10\text{ mm/s}$. | Transparent acrylic winch safety shrouds. |
| **H4: Comm Loss Runaway** | Host crashes during trajectory execution. | High | ESP32 250 ms watchdog auto-stops all axes upon timeout. | Independent hardware E-Stop contactor. |
| **H5: Slack Cable Derailment**| Cable goes slack ($T < 0$) and jumps off spool drum. | Medium | Quadratic programming solver enforces minimum positive tension ($T_{\text{min}} \ge 2.0\text{ N}$). | Deep-groove spool flanges and spring-loaded cable guides. |
| **H6: Reverse Spooling** | Reeling in past zero or running backwards. | Medium | Geometry model validates minimum cable length ($l_i \ge 0.050\text{ m}$). | Soft limits and optical homing interlocks. |

---

## 3. Defense-in-Depth Safety Architecture

The safety system employs three distinct layers:

```text
+-------------------------------------------------------------+
| Layer 1: Application & Trajectory Planner (Software)       |
| - Boundary validation & rejection before execution         |
| - Trapezoidal profile acceleration & jerk bounding          |
| - Static tension feasibility checks (positive tension)     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Layer 2: Firmware & Embedded Watchdog (ESP32)               |
| - 250 ms command watchdog timer                            |
| - Reconnect auto-arm prohibition                            |
| - Displacement delta limits                                 |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Layer 3: Independent Physical Protection (Hardware)        |
| - Hardwired dual-channel Emergency Stop button             |
| - Drive Safe Torque Off (STO) or DC bus contactor relay     |
| - Mechanical end-stop bumpers & physical cable shrouds      |
+-------------------------------------------------------------+
```

---

## 4. Fault Detection & Reaction Policies

The software monitors fault conditions continuously and enforces strict response actions:

| Fault Type | Trigger Condition | Reaction | Recovery Action |
|---|---|---|---|
| **E-Stop Latched** | Operator hits browser stop or physical switch. | Instantaneous zero velocity command; driver de-energized. | Explicit `/command/reset` required after confirming clearance. |
| **Workspace Boundary Violation** | Commanded target $(x, y)$ outside $[-180, +180] \times [-140, +140]\text{ mm}$. | Reject command immediately; return HTTP 422 with diagnostic. | Operator enters valid target coordinate. |
| **Actuator Speed Limit** | Cable speed exceeds $v_{\text{cable}} > 0.314\text{ m/s}$ ($300\text{ RPM}$). | Reject trajectory before starting; scale time or reduce speed. | Re-plan with lower maximum platform speed. |
| **Stale Telemetry / Comm Loss** | Feedback timestamp older than $500\text{ ms}$. | Tag telemetry provenance as `BLOCKED`; halt coordinated motion. | Re-establish connection; manual status verification. |
| **Estimation Residual High** | Forward kinematics residual $\|l_i - \hat{l}_i\| > 5.0\text{ mm}$. | Warning flag set; abort coordinated trajectory. | Re-home platform and inspect cable tensions. |
| **Drive Hardware Alarm** | Servo drive signals fault on alarm input pin. | Firmware transitions to `SAFE_STOP`; open STO lines. | Power cycle drive, inspect physical mechanism, reset drive. |

---

## 5. Software Limitations & Disclaimers

1. **Not Safety-Rated:**
   Software checks running in Python or standard ROS 2 on an operating system without a real-time kernel (RT-PREEMPT) do NOT meet ISO 13849-1 (Performance Level d/e) or IEC 61508 (SIL 2/3) safety standards.
2. **Physical E-Stop is Non-Negotiable:**
   Software stops rely on operating system scheduling, network sockets, and microcontroller firmware. Any physical testbed MUST include a certified, hardwired Emergency Stop circuit cutting electrical power to the servo drive power stage.
