# ESP32 micro-ROS Firmware for Planar CDPR
## 2-DOF, 4-Cable Planar Cable-Driven Parallel Robot

---

## 1. Overview and Architecture

This firmware project implements the embedded micro-ROS client running on the ESP32 microcontroller. The ESP32 acts as the low-latency hardware interface between the ROS 2 coordination layer (running on the host PC) and the 4 winch servo drives.

```
+-------------------------------------------------------------+
| HOST COMPUTER (Ubuntu 24.04 LTS Jazzy / Ubuntu 22.04 LTS)   |
| ROS 2 Jazzy / Humble Desktop                                |
|                                                             |
|   [CDPR Kinematics & Planner Nodes]                         |
|                 | (ROS 2 Topics)                            |
|                 v                                           |
|   [micro-ROS Agent] (micro_ros_agent package / Docker)      |
+-----------------|-------------------------------------------+
                  | Supported Transport:
                  |   Option A: Serial UART over USB (115200 or 921600 baud)
                  |   Option B: Wi-Fi UDP (e.g. port 8888)
                  v
+-------------------------------------------------------------+
| ESP32 MICROCONTROLLER (FreeRTOS)                            |
|                                                             |
|   micro-ROS Client (eProsima Micro-XRCE-DDS Client)         |
|   - Executor & Subscriptions (/cdpr/cables/command)         |
|   - Publishers (/cdpr/cables/feedback, /cdpr/motors/state)  |
|                                                             |
|   Finite State Machine:                                     |
|   BOOT -> INITIALIZING -> WAITING_FOR_AGENT -> CONNECTED    |
|        -> DRIVE_STATUS_CHECK -> READY -> MOTION_ENABLED     |
|        -> FAULT / SAFE_STOP                                 |
|                                                             |
|   Watchdog & Safety Interlocks:                             |
|   - Communication timeout watchdog (250 ms)                 |
|   - Automatic safe-stop on Agent disconnection              |
|   - Motion NEVER re-arms automatically on reconnection      |
|   - Unknown/unverified drives clamped to Safe Torque Off    |
+-----------------|-------------------------------------------+
                  | Servo Drive Protocol (Isolated boundary)
                  | CAN-FD, RS-485 Modbus, or Step/Dir
                  v
       [4x SERVO DRIVES & MOTORS]
```

---

## 2. Verified Toolchain and Version Matrix

| Component | Target Version | Status |
|---|---|---|
| Microcontroller Target | ESP32-WROOM-32D / ESP32-S3 | Provisional |
| Embedded OS | FreeRTOS (ESP-IDF v5.1.2 or v5.2.x) | Compatible Reference |
| micro-ROS Component | `micro_ros_espidf_component` (`jazzy` or `humble` branch) | Compatible Reference |
| Host ROS 2 Distribution | ROS 2 Jazzy (Ubuntu 24.04) / ROS 2 Humble (Ubuntu 22.04) | Primary Target: Jazzy |
| Host Python | Python 3.12 (Ubuntu 24.04) / Python 3.10 (Ubuntu 22.04) | Verified on host |
| CMake | >= 3.16 | Standard |

---

## 3. Communication Transport Configuration

### Transport A: USB / UART Serial (Recommended for Commissioning)
- **Default Baud Rate:** `115200` baud (can be configured to `921600` for high rate)
- **USB Interface:** Built-in CP2102 / CH340 / ESP32-S3 Native USB-JTAG
- **Agent Command on Host:**
  ```bash
  ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200
  ```

### Transport B: Wi-Fi UDP
- Set via `idf.py menuconfig` -> `micro-ROS Transport Settings` -> `Wi-Fi Configuration`.
- **Note:** Never commit production Wi-Fi passwords to Git version control. Use `.env` or project-local configuration.
- **Agent Command on Host:**
  ```bash
  ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
  ```

---

## 4. Finite State Machine (Section 12.4)

The firmware enforces the following deterministic states:

```
[BOOT]
  |
  v
[INITIALIZING] ----(Internal peripheral error)----> [FAULT]
  |
  v
[WAITING_FOR_AGENT] <-------------+
  | (Ping succeeds)               | (Agent disconnected or timeout)
  v                               |
[CONNECTED] ----------------------+
  |
  v
[DRIVE_STATUS_CHECK]
  | (Drives verified & ready)
  v
[READY] (Motors Disarmed / Safe Torque Off active)
  | (Explicit enable command + Valid target)
  v
[MOTION_ENABLED]
  |
  +---(Watchdog timeout / Comm loss)----> [SAFE_STOP] -> [WAITING_FOR_AGENT]
  +---(Drive fault / Saturation)--------> [FAULT]
  +---(E-stop requested)----------------> [SAFE_STOP]
```

### Safety Interlocks Enforced in Firmware:
1. **No Auto-Arming:** Reconnecting to the micro-ROS Agent **never** re-enables motor torque. An explicit operator command must be issued after reconnection.
2. **Watchdog Timeout:** If no valid command packet is received within `250 ms`, the firmware immediately transitions to `SAFE_STOP`, clamping target velocities to zero.
3. **No Replay of Stale Commands:** Each command packet includes a timestamp and sequence number; out-of-order or stale commands are discarded.
4. **Unverified Drive Protection:** While servo drive protocols remain unverified, physical motor outputs remain in Safe Torque Off (STO).

---

## 5. Build and Flash Instructions

### Prerequisites
1. Install ESP-IDF v5.1+:
   ```bash
   git clone -b v5.1.2 --recursive https://github.com/espressif/esp-idf.git ~/esp/esp-idf
   cd ~/esp/esp-idf && ./install.sh && . ./export.sh
   ```
2. Clone micro-ROS ESP-IDF component:
   ```bash
   cd firmware/esp32_micro_ros
   git clone -b humble https://github.com/micro-ROS/micro_ros_espidf_component.git components/micro_ros_espidf_component
   ```

### Building Firmware
```bash
cd firmware/esp32_micro_ros
idf.py set-target esp32
idf.py menuconfig
idf.py build
```

### Flashing and Monitoring
```bash
idf.py -p /dev/ttyUSB0 flash monitor
```
