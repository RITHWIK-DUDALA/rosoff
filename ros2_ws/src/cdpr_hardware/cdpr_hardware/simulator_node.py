#!/usr/bin/env python3
"""
ROS 2 Simulator Driver Node for 2-DOF Planar CDPR.
Subscribes:
  - /cdpr/cables/command (sensor_msgs/JointState)
Publishes:
  - /cdpr/cables/feedback (sensor_msgs/JointState)
Identifies all feedback as simulated. Works fully offline without hardware.
"""
try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


class CDPRSimulatorNode:
    def __init__(self):
        if not HAS_ROS2:
            raise RuntimeError("ROS 2 (rclpy) is not installed.")

        self.node = rclpy.create_node('cdpr_simulator_node')
        self.cmd_sub = self.node.create_subscription(JointState, '/cdpr/cables/command', self.on_command, 10)
        self.fb_pub = self.node.create_publisher(JointState, '/cdpr/cables/feedback', 10)
        self.node.get_logger().info("CDPR Simulator Driver Node active (Mode A: SIMULATION).")

    def on_command(self, msg: JointState):
        # In simulation, actuators track commanded lengths smoothly
        fb = JointState()
        fb.header.stamp = self.node.get_clock().now().to_msg()
        fb.header.frame_id = 'cdpr_simulation'
        fb.name = msg.name
        fb.position = msg.position
        fb.velocity = [0.0] * len(msg.position)
        fb.effort = [10.0] * len(msg.position) # Simulated nominal tension
        self.fb_pub.publish(fb)


def main(args=None):
    if not HAS_ROS2:
        print("[cdpr_hardware/simulator_node] ROS 2 is not installed. Exiting.")
        return
    rclpy.init(args=args)
    sim_node = CDPRSimulatorNode()
    try:
        rclpy.spin(sim_node.node)
    except KeyboardInterrupt:
        pass
    finally:
        sim_node.node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
