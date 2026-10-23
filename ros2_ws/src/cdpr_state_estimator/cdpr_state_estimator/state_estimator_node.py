#!/usr/bin/env python3
"""
ROS 2 State Estimator Node for 2-DOF Planar CDPR.
Subscribes:
  - /cdpr/cables/feedback (sensor_msgs/JointState)
  - /cdpr/motion/setpoint (geometry_msgs/Point)
Publishes:
  - /cdpr/state (cdpr_interfaces/msg/RobotState)
  - /cdpr/diagnostics (cdpr_interfaces/msg/RobotDiagnostics)
"""
import numpy as np

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Point
    from sensor_msgs.msg import JointState
    from cdpr_interfaces.msg import RobotState, RobotDiagnostics
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


class CDPRStateEstimatorNode:
    def __init__(self):
        if not HAS_ROS2:
            raise RuntimeError("ROS 2 (rclpy) is not installed.")

        self.node = rclpy.create_node('cdpr_state_estimator_node')

        self.anchors = np.array([
            [-0.250,  0.200],  # C1
            [ 0.250,  0.200],  # C2
            [ 0.250, -0.200],  # C3
            [-0.250, -0.200],  # C4
        ])

        self.attachments = np.array([
            [-0.050,  0.040],  # C1
            [ 0.050,  0.040],  # C2
            [ 0.050, -0.040],  # C3
            [-0.050, -0.040],  # C4
        ])

        self.last_estimated_q = np.zeros(2, dtype=np.float64)
        self.commanded_q = np.zeros(2, dtype=np.float64)

        # Pub / Sub
        self.state_pub = self.node.create_publisher(RobotState, '/cdpr/state', 10)
        self.diag_pub = self.node.create_publisher(RobotDiagnostics, '/cdpr/diagnostics', 10)

        self.node.create_subscription(JointState, '/cdpr/cables/feedback', self.on_cable_feedback, 10)
        self.node.create_subscription(Point, '/cdpr/motion/setpoint', self.on_setpoint, 10)

        self.node.get_logger().info("CDPR State Estimator Node initialized.")

    def on_setpoint(self, msg: Point):
        self.commanded_q = np.array([msg.x, msg.y])

    def solve_fk(self, L_meas: np.ndarray) -> tuple[np.ndarray, bool, float, float]:
        """Levenberg-Marquardt forward kinematics."""
        q_k = self.last_estimated_q.copy()
        mu = 1e-4
        converged = False
        res_norm = float("inf")

        for _ in range(50):
            P = q_k + self.attachments
            diff = self.anchors - P
            L_k = np.linalg.norm(diff, axis=1)
            r = L_k - L_meas
            res_norm = float(np.linalg.norm(r))

            if res_norm < 1e-6:
                converged = True
                break

            # Analytical Jacobian
            J = (P - self.anchors) / L_k[:, None]
            H = J.T @ J + mu * np.eye(2)
            g = - J.T @ r
            try:
                dq = np.linalg.solve(H, g)
            except np.linalg.LinAlgError:
                break

            q_trial = q_k + dq
            P_tr = q_trial + self.attachments
            L_tr = np.linalg.norm(self.anchors - P_tr, axis=1)
            if np.linalg.norm(L_tr - L_meas) < res_norm:
                q_k = q_trial
                mu = max(1e-7, mu * 0.5)
                if np.linalg.norm(dq) < 1e-6:
                    converged = True
                    break
            else:
                mu = min(1e3, mu * 4.0)

        # Condition number
        P = q_k + self.attachments
        diff = P - self.anchors
        L = np.linalg.norm(diff, axis=1, keepdims=True)
        J = diff / L
        s = np.linalg.svd(J, compute_uv=False)
        cond = float(s[0] / s[-1]) if s[-1] > 1e-12 else float("inf")

        return q_k, converged, res_norm, cond

    def on_cable_feedback(self, msg: JointState):
        if len(msg.position) < 4:
            return

        L_meas = np.array(msg.position[:4], dtype=np.float64)
        q_est, converged, res_norm, cond = self.solve_fk(L_meas)

        now = self.node.get_clock().now().to_msg()
        tracking_err = float(np.linalg.norm(self.commanded_q - q_est)) if converged else 0.0

        if converged and res_norm < 0.02:
            self.last_estimated_q = q_est.copy()

        # Publish RobotState
        state = RobotState()
        state.header.stamp = now
        state.header.frame_id = 'cdpr_frame_center'
        state.operating_mode = "SIMULATION"
        state.position_provenance = "estimated" if converged else "unavailable"
        state.controller_mode = "IDLE"
        state.homing_state = "HOMED"

        state.commanded_position.x = float(self.commanded_q[0])
        state.commanded_position.y = float(self.commanded_q[1])

        state.estimated_position.x = float(q_est[0])
        state.estimated_position.y = float(q_est[1])
        state.estimated_position_valid = converged

        state.tracking_error_m = tracking_err
        state.tracking_error_valid = converged
        state.is_fresh = True
        self.state_pub.publish(state)

        # Publish Diagnostics
        diag = RobotDiagnostics()
        diag.header.stamp = now
        diag.condition_number = cond
        diag.fk_residual_norm_m = res_norm
        diag.workspace_safe = (abs(q_est[0]) <= 0.180 and abs(q_est[1]) <= 0.140)
        diag.tension_feasible = True
        diag.active_driver = "SimulatorDriver"
        diag.hardware_ready = False
        self.diag_pub.publish(diag)


def main(args=None):
    if not HAS_ROS2:
        print("[cdpr_state_estimator] ROS 2 (rclpy) is not installed. Exiting gracefully.")
        return
    rclpy.init(args=args)
    estimator_node = CDPRStateEstimatorNode()
    try:
        rclpy.spin(estimator_node.node)
    except KeyboardInterrupt:
        pass
    finally:
        estimator_node.node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
