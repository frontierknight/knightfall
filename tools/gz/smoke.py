"""Gazebo-tier smoke test (run by tools/gz/smoke.sh with the sim already launching).

Proves, headless and without a GPU, the four things the Gazebo tier depends on:
  1. lidar renders:        /scan publishes at a usable rate
  2. real-time factor:     sim seconds advanced per wall second (/clock)
  3. the real stack works: AMCL + Nav2 drive the robot to a goal
  4. ground truth:         the judge reads the TRUE pose from Gazebo over gz-transport (`gz model`),
                           not from DDS, and it agrees with where Nav2 says the robot went
Also reports the natural localization error (AMCL vs truth): the noise floor that physical-impact
thresholds must sit well above. Prints one JSON report; exits 1 if a hard gate fails.
"""
from __future__ import annotations
import argparse, json, math, re, subprocess, sys, threading, time

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

SPAWN = (-2.0, -0.5)          # tb3_simulation_launch.py default spawn pose
MIN_RTF = 0.2                 # hard gate; CORE.md target is >= 0.5 (reported as a warning)
TARGET_RTF = 0.5
MIN_SCAN_HZ = 2.0
GOAL_TOL = 0.5                # m: true pose must end this close to the goal


class Monitor(Node):
    # Callbacks are named _on_*: rclpy.Node already uses _clock etc. as instance attributes.
    def __init__(self):
        super().__init__("kf_smoke_monitor")
        self.lock = threading.Lock()
        self.scans = []            # wall timestamps of received scans
        self.sim_time = None       # latest sim time (s)
        self.amcl = None           # latest AMCL (x, y)
        self.create_subscription(LaserScan, "/scan", self._on_scan, qos_profile_sensor_data)
        self.create_subscription(Clock, "/clock", self._on_clock, 10)
        amcl_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self._on_amcl, amcl_qos)

    def _on_scan(self, _msg):
        with self.lock:
            self.scans.append(time.monotonic())

    def _on_clock(self, msg):
        with self.lock:
            self.sim_time = msg.clock.sec + msg.clock.nanosec * 1e-9

    def _on_amcl(self, msg):
        with self.lock:
            p = msg.pose.pose.position
            self.amcl = (p.x, p.y)


def gz_true_pose(model):
    """TRUE (x, y) of `model` from Gazebo over gz-transport — the judge's channel, off the DDS graph."""
    try:
        out = subprocess.run(["gz", "model", "-m", model, "-p"], capture_output=True, text=True,
                             timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, "gz model failed"
    num = r"(-?[\d.]+(?:e[-+]?\d+)?)"
    m = re.search(r"Pose.*?\[\s*" + num + r"\s+" + num + r"\s+" + num + r"\s*\]", out, re.S)
    if not m:
        return None, out.strip()[-400:]
    return (float(m.group(1)), float(m.group(2))), None


def pose_stamped(nav, x, y):
    p = PoseStamped()
    p.header.frame_id = "map"   # stamp left at 0 = "latest"; this node runs on wall time, the sim does not
    p.pose.position.x, p.pose.position.y = x, y
    p.pose.orientation.w = 1.0
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", type=float, nargs=2, default=[0.55, 0.55])
    ap.add_argument("--model", default="turtlebot3_waffle")
    ap.add_argument("--nav-timeout", type=float, default=300.0, help="wall seconds")
    a = ap.parse_args()

    rclpy.init()
    mon = Monitor()
    ex = SingleThreadedExecutor()
    ex.add_node(mon)
    spinner = threading.Thread(target=_spin, args=(ex,), daemon=True)
    spinner.start()
    try:
        return run_checks(mon, a)
    finally:
        # Wake the executor and join its thread before exiting: an interpreter exit while the
        # thread is still inside rcl's wait aborts the process ("terminate called ...", rc 134).
        rclpy.try_shutdown()
        spinner.join(timeout=5)


def _spin(ex):
    try:
        ex.spin()
    except ExternalShutdownException:
        pass


def run_checks(mon, a):
    report, fails, warns = {}, [], []

    # 1. lidar up
    t0 = time.monotonic()
    while time.monotonic() - t0 < 240 and not mon.scans:
        time.sleep(0.5)
    report["scan_first_s"] = round(time.monotonic() - t0, 1) if mon.scans else None
    if not mon.scans:
        fails.append("no /scan within 240 s (sensor rendering failed?)")
        print(json.dumps({"report": report, "fails": fails}, indent=2))
        return 1

    # 2. scan rate + real-time factor over a 10 s wall window
    with mon.lock:
        n0, c0 = len(mon.scans), mon.sim_time
    w0 = time.monotonic()
    time.sleep(10)
    with mon.lock:
        n1, c1 = len(mon.scans), mon.sim_time
    dw = time.monotonic() - w0
    report["scan_hz"] = round((n1 - n0) / dw, 2)
    report["rtf"] = round((c1 - c0) / dw, 3) if c0 is not None and c1 is not None else None
    if report["scan_hz"] < MIN_SCAN_HZ:
        fails.append(f"scan_hz {report['scan_hz']} < {MIN_SCAN_HZ}")
    if report["rtf"] is None or report["rtf"] < MIN_RTF:
        fails.append(f"rtf {report['rtf']} < {MIN_RTF}")
    elif report["rtf"] < TARGET_RTF:
        warns.append(f"rtf {report['rtf']} below target {TARGET_RTF}")

    # 3. AMCL + Nav2 drive to a goal
    nav = BasicNavigator()
    nav.setInitialPose(pose_stamped(nav, *SPAWN))
    t_nav = time.monotonic()
    nav.waitUntilNav2Active(localizer="amcl")
    report["nav2_active_s"] = round(time.monotonic() - t_nav, 1)
    nav.goToPose(pose_stamped(nav, *a.goal))
    t_goal = time.monotonic()
    while not nav.isTaskComplete():
        if time.monotonic() - t_goal > a.nav_timeout:
            nav.cancelTask()
            break
        time.sleep(0.5)
    result = nav.getResult()
    report["nav_result"] = str(result)
    report["nav_wall_s"] = round(time.monotonic() - t_goal, 1)
    if result != TaskResult.SUCCEEDED:
        fails.append(f"Nav2 goal not reached: {result}")
    time.sleep(2)  # let the robot settle before reading truth

    # 4. ground truth from Gazebo (judge channel) vs goal and vs AMCL
    truth, err = gz_true_pose(a.model)
    report["goal"] = a.goal
    report["truth"] = [round(v, 3) for v in truth] if truth else None
    if truth is None:
        fails.append(f"could not read ground truth over gz-transport: {err}")
    else:
        d_goal = math.hypot(truth[0] - a.goal[0], truth[1] - a.goal[1])
        report["truth_to_goal_m"] = round(d_goal, 3)
        if d_goal > GOAL_TOL:
            fails.append(f"true pose {d_goal:.2f} m from goal (> {GOAL_TOL})")
        with mon.lock:
            amcl = mon.amcl
        if amcl:
            report["amcl"] = [round(v, 3) for v in amcl]
            report["loc_error_m"] = round(math.hypot(truth[0] - amcl[0], truth[1] - amcl[1]), 3)

    report["pass"] = not fails
    print(json.dumps({"report": report, "fails": fails, "warnings": warns}, indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
