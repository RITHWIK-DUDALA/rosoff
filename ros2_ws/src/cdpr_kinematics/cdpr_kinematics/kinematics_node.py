#!/usr/bin/env python3
"""
ROS 2 Kinematics Node for 2-DOF Planar CDPR.
Subscribes:
  - /cdpr/command/target (geometry_msgs/Point)
Publishes:
  - /cdpr/cables/command (sensor_msgs/JointState)
Services:
  - /cdpr/validate_target (cdpr_interfaces/srv/ValidateTarget)
"""
import math
import numpy as np

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Point
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Header
    from cdpr_interfaces.srv import ValidateTarget
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


class CDPRKinematicsNode:
    """ROS 2 Kinematics Node for Inverse Kinematics and Jacobian calculations."""

    def __init__(self):
        if not HAS_ROS2:
            raise RuntimeError("ROS 2 (rclpy) is not installed in current environment.")

        # Super init via Node
        self.node = rclpy.create_node('cdpr_kinematics_node')

        # Declare parameters (Canonical geometry defaults: 500x400 mm frame, 100x80 mm platform)
        self.node.declare_parameter('drum_radius_m', 0.010)
        self.node.declare_parameter('max_speed_rpm', 300.0)
        self.node.declare_parameter('workspace_x_limit_m', 0.180)
        self.node.declare_parameter('workspace_y_limit_m', 0.140)

        self.drum_radius = self.node.get_parameter('drum_radius_m').value
        self.max_rpm = self.node.get_parameter('max_speed_rpm').value
        self.ws_x_lim = self.node.get_parameter('workspace_x_limit_m').value
        self.ws_y_lim = self.node.get_parameter('workspace_y_limit_m').value

        # Canonical frame anchors (meters)
        self.anchors = np.array([
            [-0.250,  0.200],  # C1
            [ 0.250,  0.200],  # C2
            [ 0.250, -0.200],  # C3
            [-0.250, -0.200],  # C4
        ])

        # Canonical platform attachments (meters)
        self.attachments = np.array([
            [-0.050,  0.040],  # C1
            [ 0.050,  0.040],  # C2
            [ 0.050, -0.040],  # C3
            [-0.050, -0.040],  # C4
        ])

        # ROS 2 Pub/Sub
        self.cable_pub = self.node.create_publisher(JointState, '/cdpr/cables/command', 10)
        self.target_sub = self.node.create_subscription(Point, '/cdpr/command/target', self.on_target, 10)
        self.setpoint_sub = self.node.create_subscription(Point, '/cdpr/motion/setpoint', self.on_target, 10)
        self.val_srv = self.node.create_service(ValidateTarget, '/cdpr/validate_target', self.on_validate_target)

        self.node.get_logger().info("CDPR Kinematics Node initialized.")

    def calculate_lengths(self, q: np.ndarray) -> np.ndarray:
        P = q + self.attachments
        diff = self.anchors - P
        lengths = np.linalg.norm(diff, axis=1)
        return lengths

    def calculate_jacobian(self, q: np.ndarray) -> np.ndarray:
        P = q + self.attachments
        diff = P - self.anchors
        L = np.linalg.norm(diff, axis=1, keepdims=True)
        return diff / L

    def on_target(self, msg: Point):
        q = np.array([msg.x, msg.y])
        # Workspace check
        if abs(q[0]) > self.ws_x_lim or abs(q[1]) > self.ws_y_lim:
            self.node.get_logger().warn(f"Target [{q[0]:.3f}, {q[1]:.3f}] rejected: exceeds workspace limits")
            return

        lengths = self.calculate_lengths(q)
        js = JointState()
        js.header.stamp = self.node.get_clock().now().to_msg()
        js.header.frame_id = 'cdpr_frame_center'
        js.name = ['cable_1', 'cable_2', 'cable_3', 'cable_4']
        js.position = list(lengths)
        self.cable_pub.publish(js)

    def on_validate_target(self, request, response):
        q = np.array([request.target_position.x, request.target_position.y])
        if abs(q[0]) > self.ws_x_lim or abs(q[1]) > self.ws_y_lim:
            response.is_valid = False
            response.rejection_reason = f"Position [{q[0]:.3f}, {q[1]:.3f}] exceeds workspace limits"
            response.expected_cable_lengths_m = [0.0, 0.0, 0.0, 0.0]
            response.expected_cable_rpms = [0.0, 0.0, 0.0, 0.0]
        else:
            lengths = self.calculate_lengths(q)
            response.is_valid = True
            response.rejection_reason = "OK"
            response.expected_cable_lengths_m = list(lengths)
            response.expected_cable_rpms = [0.0, 0.0, 0.0, 0.0]
        return response


def main(args=None):
    if not HAS_ROS2:
        print("[cdpr_kinematics] ROS 2 (rclpy) is not installed. Exiting gracefully.")
        return
    rclpy.init(args=args)
    kin_node = CDPRKinematicsNode()
    try:
        rclpy.spin(kin_node.node)
    except KeyboardInterrupt:
        pass
    finally:
        kin_node.node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
