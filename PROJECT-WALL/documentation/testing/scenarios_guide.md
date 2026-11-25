# PROJECT W.A.L.L. — Scenarios Guide (Part 19)

This guide documents the 12 formal validation test cases implemented in `backend/app/scenarios/scenario_manager.py` and exposed via the UI dropdown.

### Scenario 1: Basic Installation
- **Objective:** Configure an $800 \times 600\text{ mm}$ surface board, verify mounting adequacy, calculate corner anchor positions $A_1..A_4$, and verify the initial printable workspace.
- **Pass Criteria:** Mounting verification returns valid; printable bounding box $([100, 700], [100, 500])$ is correctly established.

### Scenario 2: Centre Movement
- **Objective:** Move the central platform to nominal center $(400, 300)\text{ mm}$ via coordinated cable length payout.
- **Pass Criteria:** Static tensions feasible ($15 - 25\text{ N}$); tracking error $< 0.1\text{ mm}$.

### Scenario 3: Boundary Movement & Cable Slack Detection
- **Objective:** Travel toward workspace corner boundaries and verify positive tension maintenance. Simulate tension drop below $2.0\text{ N}$.
- **Pass Criteria:** Cable slack detected; supervisory state machine commands controlled stop.

### Scenario 4: Cable Overload Detection
- **Objective:** Simulate external force or snag exceeding $50.0\text{ N}$.
- **Pass Criteria:** Overload threshold tripped; supervisory state machine halts winch motors immediately.

### Scenario 5: Emergency Stop Interrupt
- **Objective:** Trigger hardware/UI emergency stop during active motion.
- **Pass Criteria:** Motors transition to `EMERGENCY_STOP`; planner halts; deposition stops.

### Scenario 6: Different Surface Dimensions
- **Objective:** Reconfigure surface to $1200 \times 900\text{ mm}$.
- **Pass Criteria:** Anchor points update dynamically; kinematics recalibrates without resetting system architecture.

### Scenario 7: Mounting Incompatibility
- **Objective:** Select rough porous plaster with suction cup mounting.
- **Pass Criteria:** Mounting validation correctly identifies failure: suction requires non-porous smooth surfaces.

### Scenario 8: Motor Thermal Throttling
- **Objective:** Continuous high-torque holding; track coil temperature rise and thermal derating.

### Scenario 9: Actuator Swap (Inkjet to Paint Marker)
- **Objective:** Interchange Module A (piezo inkjet) with Module B (paint marker).
- **Pass Criteria:** Standoff distance recalibrates from $2.0\text{ mm}$ non-contact to $0.0\text{ mm}$ compliant contact.

### Scenario 10: Position Error & Sensor Drift
- **Objective:** Inject encoder drift; verify forward kinematics discrepancy vs commanded position.

### Scenario 11: Interrupted Printing
- **Objective:** Pause print job midway; verify coordinate and droplet state preservation; resume.

### Scenario 12: Full Autonomous Job
- **Objective:** Complete autonomous workflow from image ingest to progressive deposition and final quality report generation.

