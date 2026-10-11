"""
Optional ROS 2 Bridge Node for CDPR Simulator.
Bridges WebSocket telemetry from the CDPR FastAPI backend into standard ROS 2 topics:
- sensor_msgs/JointState on /cdpr/robot_state
- geometry_msgs/PoseStamped on /cdpr/pose
- diagnostic_msgs/DiagnosticArray on /diagnostics
Listens to /cdpr/command/move to forward goal positions to REST API.
Operates only if ROS 2 (rclpy) is installed; exits gracefully with informative notice otherwise.
"""
import sys
import json
import asyncio
import threading
import urllib.request

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from geometry_msgs.msg import PoseStamped, Point
    from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
    import websockets
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


if not HAS_ROS2:
    def main():
        print("[CDPR ROS 2 Bridge] Notice: ROS 2 (rclpy) or standard ROS messages not found.")
        print("[CDPR ROS 2 Bridge] The simulator backend and web UI run natively without ROS.")
        print("[CDPR ROS 2 Bridge] To enable ROS 2 bridging, source a ROS 2 environment (e.g. Humble/Iron) and install websockets.")
        sys.exit(0)
else:
    class CDPRBridgeNode(Node):
        def __init__(self):
            super().__init__('cdpr_ros2_bridge')
            self.joint_pub = self.create_publisher(JointState, '/cdpr/robot_state', 10)
            self.pose_pub = self.create_publisher(PoseStamped, '/cdpr/pose', 10)
            self.diag_pub = self.create_publisher(DiagnosticArray, '/diagnostics', 10)

            self.create_subscription(Point, '/cdpr/command/move', self.on_move_cmd, 10)
            self.get_logger().info('CDPR ROS 2 Bridge initialized. Connecting to simulator...')

        def on_move_cmd(self, msg: Point):
            # Forward coordinate to simulator REST API
            url = "http://localhost:8000/api/command/move"
            payload = json.dumps({"x_mm": msg.x, "y_mm": msg.y, "speed_mm_s": 80.0}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
            try:
                with urllib.request.urlopen(req) as resp:
                    pass
            except Exception as e:
                self.get_logger().error(f"Failed to forward move command: {e}")

        def publish_telemetry(self, telem: dict):
            now = self.get_clock().now().to_msg()

            # 1. Cable JointState
            js = JointState()
            js.header.stamp = now
            js.name = ['cable_1', 'cable_2', 'cable_3', 'cable_4']
            js.position = [l / 1000.0 for l in telem.get('cable_lengths_mm', [])]
            js.velocity = [v / 1000.0 for v in telem.get('cable_rates_mm_s', [])]
            js.effort = [float(t) for t in telem.get('cable_tensions_N', [])]
            self.joint_pub.publish(js)

            # 2. Platform Pose
            ps = PoseStamped()
            ps.header.stamp = now
            ps.header.frame_id = 'cdpr_frame_center'
            pos = telem.get('platform_pos', [0.0, 0.0])
            ps.pose.position.x = pos[0] / 1000.0
            ps.pose.position.y = pos[1] / 1000.0
            ps.pose.position.z = 0.0
            ps.pose.orientation.w = 1.0
            self.pose_pub.publish(ps)

    async def telemetry_listener(node: CDPRBridgeNode):
        uri = "ws://localhost:8000/ws/telemetry"
        while rclpy.ok():
            try:
                async with websockets.connect(uri) as ws:
                    async for message in ws:
                        if not rclpy.ok():
                            break
                        data = json.loads(message)
                        node.publish_telemetry(data)
            except Exception:
                await asyncio.sleep(2.0)

    def main(args=None):
        rclpy.init(args=args)
        node = CDPRBridgeNode()

        loop = asyncio.new_event_loop()
        t = threading.Thread(target=lambda: loop.run_until_complete(telemetry_listener(node)), daemon=True)
        t.start()

        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
