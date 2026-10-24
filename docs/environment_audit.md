# Phase 1 Environment Audit & Baseline Report

**Project:** Planar 2-DOF, 4-Cable Cable-Driven Parallel Robot (CDPR)  
**Date:** 2026-10-23  
**Auditor:** Antigravity Autonomous Engineering Agent  
**Git Branch:** `main` | **Commit:** `64a37c3` | **Working Tree:** Clean  

---

## 1. Operating System & Host Environment

| Parameter | Observed State | Verification Evidence / Command Output |
|---|---|---|
| **Host OS** | Windows 11 (NT 10.0.26200.0) | `[System.Environment]::OSVersion.VersionString` -> `Microsoft Windows NT 10.0.26200.0` |
| **Git** | Git for Windows v2.53.0 | `git --version` -> `git version 2.53.0.windows.2` |
| **WSL Default Version** | WSL2 | `wsl --status` -> `Default Version: 2` |
| **WSL Installed Distros** | **None** (Absent) | `wsl --list --verbose` -> `Windows Subsystem for Linux has no installed distributions.` |
| **WSL Available Online** | Ubuntu-24.04 available | `wsl --list --online` includes `Ubuntu-24.04 (Ubuntu 24.04 LTS)` |
| **USB Passthrough Tool** | **Absent** (`usbipd-win` not installed) | `Get-Command usbipd` -> Not found |
| **Python on Windows** | Python 3.11.9 (64-bit) | `python --version` -> `Python 3.11.9` |
| **Arduino IDE** | Arduino IDE 2.3.10 | Path: `%LOCALAPPDATA%\Programs\Arduino IDE`, version `2.3.10.0` |
| **Arduino ESP32 Core** | `esp32-core-3.3.12` | Found in `%LOCALAPPDATA%\Arduino15\staging\packages\esp32-core-3.3.12.zip` |
| **ESP-IDF on Windows** | Absent from system PATH | `Get-Command idf.py` -> Not found in PATH |

---

## 2. Target Embedded Hardware Status

| Parameter | Observed State | Verification Evidence |
|---|---|---|
| **MCU Module** | ESP32-WROOM-32 DevKit | Physically connected via USB |
| **Silicon Chip** | `ESP32-D0WD-V3` (revision v3.1) | `python -m esptool --port COM10 chip_id` -> Chip type: ESP32-D0WD-V3 (revision v3.1) |
| **Silicon Features** | Wi-Fi, BT, Dual Core + LP Core, 240MHz, 40MHz Crystal | Direct register read via esptool stub flasher |
| **MAC Address** | `b0:cb:d8:e9:**:**` (Masked) | Read via esptool stub flasher |
| **USB-to-UART Bridge** | Silicon Labs CP2102 | `USB\VID_10C4&PID_EA60\0001` |
| **Assigned COM Port** | **`COM10`** | `Get-CimInstance Win32_PnPEntity` -> `Silicon Labs CP210x USB to UART Bridge (COM10)` (Status: OK) |
| **Hardware Enable Status** | **DISARMED / SAFE** (`hardware_enable = false`) | Motors disconnected, no external power, physical outputs unverified |

---

## 3. Ubuntu 24.04 & ROS 2 Jazzy Status

| Component | Target Version | Current Status | Notes |
|---|---|---|---|
| **Linux Distribution** | Ubuntu 24.04 LTS (Noble) | **MISSING** | Needs installation via `wsl.exe --install Ubuntu-24.04` |
| **ROS 2 Distribution** | ROS 2 Jazzy Jalisco | **MISSING** | Prerequisite is Ubuntu 24.04 |
| **micro-ROS Agent** | `micro_ros_agent` (Jazzy) | **MISSING** | Built or installed inside Ubuntu 24.04 |
| **WSL2 USB Bridge** | `usbipd-win` | **MISSING** | Required for passing `COM10` through to WSL2 as `/dev/ttyUSB0` |

---

## 4. Baseline Software Verification

Executed `python -m pytest tests/ -v` on Windows development environment:
* **Total Collected Items:** 37
* **Passed:** 37
* **Failed:** 0
* **Execution Time:** 11.77 seconds
* **Coverage:** Kinematics recovery, analytical Jacobian vs finite differences, tension LP/active-set feasibility, workspace bounding box, trajectory generation, safety state transition rules, and emergency-stop latching.

---

## 5. Architectural Findings & Critical Constraints

1. **WSL2 Serial Isolation:** Windows COM ports do not propagate into WSL2 by default. The CP2102 on `COM10` will only be accessible in Ubuntu 24.04 if `usbipd-win` is installed and the device is bound and attached, OR if Wi-Fi UDP transport is utilized.
2. **Firmware Toolchain Strategy:**
   - The user has Arduino IDE 2.3.10 with esp32 core 3.3.12 on Windows.
   - The repository firmware (`firmware/esp32_micro_ros/`) is currently designed as an ESP-IDF component.
   - For ROS 2 Jazzy, `micro_ros_espidf_component` on branch `jazzy` is the officially supported Espressif component. Building it inside the target Ubuntu 24.04 WSL2 environment ensures exact toolchain and message definition consistency with the host Jazzy agent.
