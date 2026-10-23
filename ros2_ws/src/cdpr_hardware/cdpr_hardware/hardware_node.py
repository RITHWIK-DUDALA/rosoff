#!/usr/bin/env python3
"""
ROS 2 Physical Hardware Driver Node for 2-DOF Planar CDPR.
Safely interfaces with micro-ROS Agent / ESP32 when hardware is verified.
Enforces Rule 0.2 & Rule 0.5:
- Strictly disables physical motion when hardware capabilities are unverified.
- Never automatically enables motor torque upon node startup.
"""
try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from std_msgs.msg import String
    from cdpr_interfaces.msg import MotorState
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


class CDPRHardwareNode:
    def __init__(self):
        if not HAS_ROS2:
            raise RuntimeError("ROS 2 (rclpy) is not installed.")

        self.node = rclpy.create_node('cdpr_hardware_node')

        self.node.declare_parameter('hardware_verified', False)
        self.node.declare_parameter('transport_type', 'serial_uart')
        self.node.declare_parameter('baud_rate', 115200)

        self.is_verified = self.node.get_parameter('hardware_verified').value
        self.motor_state_pub = self.node.create_publisher(MotorState, '/cdpr/motors/state', 10)
        self.status_pub = self.node.create_publisher(String, '/cdpr/hardware/status', 10)

        if not self.is_verified:
            self.node.get_logger().error(
                "HARDWARE MOTION DISABLED: Physical specifications (motors, drives, E-stop, encoders) "
                "are unverified. Run simulation mode until physical commissioning checklist is complete."
            )

        self.timer = self.node.create_timer(1.0, self.publish_diagnostics)

    def publish_diagnostics(self):
        st = String()
        if not self.is_verified:
            st.data = "HARDWARE_DISABLED: Unverified drive specifications. Torque LOCKED."
        else:
            st.data = "HARDWARE_COMMISSIONING: Verified. Motors disarmed."
        self.status_pub.publish(st)


def main(args=None):
    if not HAS_ROS2:
        print("[cdpr_hardware/hardware_node] ROS 2 is not installed. Exiting.")
        return
    rclpy.init(args=args)
    hw_node = CDPRHardwareNode()
    try:
        rclpy.spin(hw_node.node)
    except KeyboardInterrupt:
        pass
    finally:
        hw_node.node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
