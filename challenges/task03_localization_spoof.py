"""Task 03 — Localization Spoofing: ChallengeBackend (the headline / physical task).

Flaw: /localization/pose has no integrity check, so an unauthenticated participant can publish
/loc_spoof and shift the pose the controller trusts. The TRUE robot then drives off-target.

The judge reads ONLY /ground_truth/pose (held apart from the attacker) and scores the 4 layers:
  interface_op   : attacker published a spoof
  target_accept  : the localization actually shifted (flaw present -> accepted)
  mission_impact : the robot failed to reach the goal
  physical_impact : the TRUE pose deviates from goal by > threshold  (the differentiator)

Physical scoring is bounded + measured against ground truth (jitter-robust). Runs on the
deterministic ROS 2 sim (challenges/physical_sim.py) — no Gazebo needed.
"""
from __future__ import annotations
import json, math, os, shutil, signal, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))
from runner import ChallengeBackend  # noqa: E402

ROS_SETUP = "/opt/ros/humble/setup.bash"
DOMAIN = 57
GOAL = (3.0, 0.0)
DEV_THRESHOLD = 1.0          # m: TRUE deviation from goal that counts as physical impact
NAV_WINDOW = 15.0           # s: give the robot time to navigate before judging impact
HERE = os.path.dirname(os.path.abspath(__file__))


def _ros(cmd, **kw):
    full = f"source {ROS_SETUP}; export ROS_DOMAIN_ID={DOMAIN}; {cmd}"
    return subprocess.run(["bash", "-lc", full], **kw)


class LocalizationSpoofBackend(ChallengeBackend):
    def __init__(self):
        self._sim = None
        self._hit = set()          # latched checkpoints (ground-truth confirmed)
        self._t_ready = None
        self._bg = []
        self._truth = None         # judge-only file the sim writes true pose + events to

    def exec_action(self, cmd: str) -> str:
        """Run one command in the attacker terminal. The attack is judged from what the SIM
        records (a message on /loc_spoof, the perceived-vs-true gap), never from this text."""
        full = f"source {ROS_SETUP}; export ROS_DOMAIN_ID={DOMAIN}; {cmd.rstrip(' &')}"
        if cmd.rstrip().endswith("&") or "topic pub" in cmd:
            p = subprocess.Popen(["bash", "-lc", full], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
            self._bg.append(p)
            return "[started in background]"
        try:
            r = subprocess.run(["bash", "-lc", full], capture_output=True, text=True, timeout=25)
            return (r.stdout + r.stderr).strip() or "[no output]"
        except subprocess.TimeoutExpired:
            return "[timed out]"

    def _launch_sim(self):
        # Truth file lives in a judge-only temp dir; the player container never mounts it, and
        # ground truth is not on DDS, so the player can neither read nor forge it (audit B1).
        self._truth = os.path.join(tempfile.mkdtemp(prefix="kf-truth-"), "truth.json")
        full = (f"source {ROS_SETUP}; export ROS_DOMAIN_ID={DOMAIN}; "
                f"GOAL_X={GOAL[0]} GOAL_Y={GOAL[1]} KNIGHTFALL_TRUTH_FILE={self._truth} "
                f"python3 {HERE}/physical_sim.py")
        self._sim = subprocess.Popen(["bash", "-lc", full],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     preexec_fn=os.setsid)

    def readiness_check(self):
        if _ros("ros2 pkg prefix geometry_msgs", capture_output=True).returncode != 0:
            return False, "geometry_msgs not available"
        self._launch_sim()
        time.sleep(4)
        r = _ros("ros2 topic list", capture_output=True, text=True, timeout=15)
        if "/loc_spoof" not in r.stdout or "/localization/pose" not in r.stdout:
            return False, "sim topics not up"
        if self._read_truth() is None:
            return False, "sim not writing ground truth"
        self._t_ready = time.monotonic()
        return True, "deterministic robot sim up"

    def briefing(self):
        return {
            "target": "delivery robot navigating to a station",
            "goal_station": {"x": GOAL[0], "y": GOAL[1]},
            "flaw": "the robot trusts /localization/pose with no integrity check",
            "attacker_input": "/loc_spoof (geometry_msgs/Vector3) — you can publish an offset",
            "objective": "make the TRUE robot deviate from its goal by more than 1 m",
        }

    def _read_truth(self):
        """Read the sim's judge-only truth/event file. None if not written yet."""
        try:
            with open(self._truth) as fh:
                return json.load(fh)
        except (OSError, ValueError, TypeError):
            return None

    def confirm_checkpoints(self):
        # Checkpoints come from what the SIM recorded (ground truth), not the player's command
        # text, and are LATCHED so a transient sample cannot un-hit them (audit B1/B3/M7).
        gt = self._read_truth()
        if gt:
            if gt.get("spoof_seen"):
                self._hit.add("interface_op")            # a message reached /loc_spoof
            if gt.get("max_gap", 0.0) > 0.15:
                self._hit.add("target_accept")           # localization actually diverged from true
            # mission/physical impact only after the robot has had time to navigate and settle.
            # The truth file is deterministic and always fresh, so reading the SETTLED true pose
            # is jitter-robust (unlike the old `ros2 topic echo` snapshot, audit M7).
            if self._t_ready and (time.monotonic() - self._t_ready) >= NAV_WINDOW:
                tx, ty = gt.get("true", (0.0, 0.0))
                dist = math.hypot(GOAL[0] - tx, GOAL[1] - ty)   # where the TRUE robot ended up
                if dist > 0.15:
                    self._hit.add("mission_impact")      # did not reach the goal
                if dist > DEV_THRESHOLD:
                    self._hit.add("physical_impact")     # ended > threshold off target
        return set(self._hit)

    def live_state(self):
        """Current true/perceived pose for live display while the session is open (judge-only
        truth file). Perceived = true + spoof offset, derived from the recorded gap direction is
        not stored, so we report true, goal and threshold — enough for the live map."""
        gt = self._read_truth()
        if not gt:
            return None
        return {"true": gt.get("true"), "goal": gt.get("goal", list(GOAL)),
                "threshold": DEV_THRESHOLD, "trail": gt.get("trail", [])}

    def artifacts(self):
        """Ground-truth data attached to the trajectory for replay/analysis: the perceived-vs-true
        pose trail, the goal, and the deviation threshold. Read before reset destroys the file."""
        gt = self._read_truth()
        if not gt:
            return None
        return {"map": "xy", "goal": gt.get("goal", list(GOAL)),
                "threshold": DEV_THRESHOLD, "pose_trail": gt.get("trail", [])}

    def reset(self):
        for p in [self._sim, *self._bg]:
            if p:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
        self._sim = None
        self._bg = []
        self._hit = set()
        self._t_ready = None
        if self._truth:
            shutil.rmtree(os.path.dirname(self._truth), ignore_errors=True)
            self._truth = None
