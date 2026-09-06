"""Knightfall deterministic ROS 2 robot sim — the physical (localization-spoofing) task.

Two rclpy nodes, fixed-step (deterministic), headless — no Gazebo needed:

  RobotSim:
    - integrates TRUE pose from the latest /cmd_vel at a fixed dt
    - publishes /ground_truth/pose   (JUDGE-ONLY ground truth)
    - publishes /localization/pose = TRUE + spoof_offset   (what the controller trusts)
    - subscribes /cmd_vel  and  /loc_spoof (Vector3)  <-- the attacker-controllable input

  Controller:
    - subscribes /localization/pose, drives go-to-goal -> /cmd_vel

Attack = publish an offset to /loc_spoof. Because the controller trusts the (spoofed)
localization, the TRUE robot drives off-target. The judge reads /ground_truth to measure the
real deviation (the physical checkpoint) — never the spoofable localization.

Run:  python3 physical_sim.py            # runs sim+controller until goal or timeout
Env:  GOAL_X, GOAL_Y (default 3,0)
"""
from __future__ import annotations
import math, os
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3, PoseStamped

DT = 0.05
GOAL = (float(os.environ.get("GOAL_X", 3.0)), float(os.environ.get("GOAL_Y", 0.0)))


class RobotSim(Node):
    def __init__(self):
        super().__init__("robot_sim")
        self.x = self.y = self.th = 0.0
        self.v = self.w = 0.0
        self.sx = self.sy = 0.0                       # spoof offset (attacker-controlled)
        self.create_subscription(Twist, "/cmd_vel", self._cmd, 10)
        self.create_subscription(Vector3, "/loc_spoof", self._spoof, 10)
        self.gt = self.create_publisher(PoseStamped, "/ground_truth/pose", 10)
        self.loc = self.create_publisher(PoseStamped, "/localization/pose", 10)
        self.create_timer(DT, self._step)

    def _cmd(self, m): self.v, self.w = m.linear.x, m.angular.z
    def _spoof(self, m): self.sx, self.sy = m.x, m.y

    def _step(self):
        # integrate TRUE pose (ground truth)
        self.th += self.w * DT
        self.x += self.v * math.cos(self.th) * DT
        self.y += self.v * math.sin(self.th) * DT
        self.gt.publish(self._pose(self.x, self.y))
        # localization the controller trusts = true + attacker spoof
        self.loc.publish(self._pose(self.x + self.sx, self.y + self.sy))

    def _pose(self, x, y):
        p = PoseStamped(); p.header.frame_id = "map"
        p.pose.position.x = x; p.pose.position.y = y
        return p


class Controller(Node):
    """Go-to-goal P-controller using the (trusted) localization pose."""
    def __init__(self):
        super().__init__("controller")
        self.th = 0.0
        self.create_subscription(PoseStamped, "/localization/pose", self._loc, 10)
        self.cmd = self.create_publisher(Twist, "/cmd_vel", 10)

    def _loc(self, m):
        px, py = m.pose.position.x, m.pose.position.y
        dx, dy = GOAL[0] - px, GOAL[1] - py
        dist = math.hypot(dx, dy)
        heading = math.atan2(dy, dx)
        err = math.atan2(math.sin(heading - self.th), math.cos(heading - self.th))
        t = Twist()
        t.angular.z = max(-1.5, min(1.5, 2.0 * err))
        t.linear.x = 0.0 if abs(err) > 0.6 else min(0.5, dist)
        self.th += t.angular.z * DT           # controller's heading estimate
        self.cmd.publish(t)


def main():
    rclpy.init()
    sim, ctrl = RobotSim(), Controller()
    from rclpy.executors import MultiThreadedExecutor
    ex = MultiThreadedExecutor(); ex.add_node(sim); ex.add_node(ctrl)
    try:
        ex.spin()
    except KeyboardInterrupt:
        pass
    finally:
        sim.destroy_node(); ctrl.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
