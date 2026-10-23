#!/usr/bin/env python3
"""
ROS 2 Motion Planning & Trajectory Coordinator Node for 2-DOF CDPR.
Subscribes:
  - /cdpr/command/target (geometry_msgs/Point)
  - /cdpr/command/jog (geometry_msgs/Vector3)
  - /cdpr/command/stop (std_msgs/Bool)
Publishes:
  - /cdpr/motion/setpoint (geometry_msgs/Point)
  - /cdpr/motion/status (std_msgs/String)
"""
import time
import numpy as np

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Point, Vector3
    from std_msgs.msg import Bool, String
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


class CDPRMotionNode:
    def __init__(self):
        if not HAS_ROS2:
            raise RuntimeError("ROS 2 (rclpy) is not installed.")

        self.node = rclpy.create_node('cdpr_motion_node')

        self.node.declare_parameter('max_speed_m_s', 0.100)
        self.node.declare_parameter('max_accel_m_s2', 0.500)
        self.node.declare_parameter('control_rate_hz', 50.0)

        self.v_max = self.node.get_parameter('max_speed_m_s').value
        self.a_max = self.node.get_parameter('max_accel_m_s2').value
        rate_hz = self.node.get_parameter('control_rate_hz').value
        self.dt = 1.0 / rate_hz

        # State
        self.current_q = np.zeros(2, dtype=np.float64)
        self.target_q = np.zeros(2, dtype=np.float64)
        self.is_moving = False
        self.trajectory_points = []
        self.traj_idx = 0

        # ROS 2 Pub/Sub
        self.setpoint_pub = self.node.create_publisher(Point, '/cdpr/motion/setpoint', 10)
        self.status_pub = self.node.create_publisher(String, '/cdpr/motion/status', 10)

        self.node.create_subscription(Point, '/cdpr/command/target', self.on_target, 10)
        self.node.create_subscription(Vector3, '/cdpr/command/jog', self.on_jog, 10)
        self.node.create_subscription(Bool, '/cdpr/command/stop', self.on_stop, 10)

        self.timer = self.node.create_timer(self.dt, self.control_loop)
        self.node.get_logger().info("CDPR Motion Node initialized.")

    def plan_trapezoidal(self, q0: np.ndarray, q1: np.ndarray, v_limit: float):
        diff = q1 - q0
        dist = float(np.linalg.norm(diff))
        if dist < 1e-6:
            return [q0]

        direction = diff / dist
        v_peak = min(self.v_max, v_limit)
        a = self.a_max
        d_acc = (v_peak ** 2) / (2.0 * a)

        if 2.0 * d_acc > dist:
            v_peak = np.sqrt(a * dist)
            t_acc = v_peak / a
            t_total = 2.0 * t_acc
            t_cruise = 0.0
        else:
            t_acc = v_peak / a
            d_cruise = dist - 2.0 * d_acc
            t_cruise = d_cruise / v_peak
            t_total = 2.0 * t_acc + t_cruise

        num_steps = max(2, int(np.ceil(t_total / self.dt)))
        time_grid = np.linspace(0.0, t_total, num_steps)
        points = []

        for t in time_grid:
            if t <= t_acc:
                s = 0.5 * a * (t ** 2)
            elif t <= t_acc + t_cruise:
                s = 0.5 * a * (t_acc ** 2) + v_peak * (t - t_acc)
            else:
                td = t - t_acc - t_cruise
                s = 0.5 * a * (t_acc ** 2) + v_peak * t_cruise + v_peak * td - 0.5 * a * (td ** 2)
            s = min(dist, max(0.0, s))
            points.append(q0 + direction * s)

        return points

    def on_target(self, msg: Point):
        goal = np.array([msg.x, msg.y])
        self.trajectory_points = self.plan_trapezoidal(self.current_q, goal, self.v_max)
        self.traj_idx = 0
        self.is_moving = True
        self.node.get_logger().info(f"Target accepted: moving to [{msg.x:.3f}, {msg.y:.3f}]")

    def on_jog(self, msg: Vector3):
        goal = self.current_q + np.array([msg.x, msg.y])
        self.trajectory_points = self.plan_trapezoidal(self.current_q, goal, self.v_max * 0.5)
        self.traj_idx = 0
        self.is_moving = True

    def on_stop(self, msg: Bool):
        self.is_moving = False
        self.trajectory_points.clear()
        self.node.get_logger().warn("Controlled stop requested: motion halted.")

    def control_loop(self):
        if self.is_moving and self.traj_idx < len(self.trajectory_points):
            self.current_q = self.trajectory_points[self.traj_idx]
            self.traj_idx += 1
            if self.traj_idx >= len(self.trajectory_points):
                self.is_moving = False

            # Publish setpoint
            p = Point()
            p.x = float(self.current_q[0])
            p.y = float(self.current_q[1])
            p.z = 0.0
            self.setpoint_pub.publish(p)

        # Publish status
        st = String()
        st.data = "MOVING" if self.is_moving else "IDLE"
        self.status_pub.publish(st)


def main(args=None):
    if not HAS_ROS2:
        print("[cdpr_motion] ROS 2 (rclpy) is not installed. Exiting gracefully.")
        return
    rclpy.init(args=args)
    motion_node = CDPRMotionNode()
    try:
        rclpy.spin(motion_node.node)
    except KeyboardInterrupt:
        pass
    finally:
        motion_node.node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
