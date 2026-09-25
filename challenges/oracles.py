"""Concrete fix-oracles for the current challenges (validate on the ROS box).

task01: the patch = SROS2 Enforce with a tight policy (only maintenance may read /diagnostics).
        This is exactly deliverable-01/run_acceptance.sh — it already runs BOTH sides:
        authorized maintenance reads (mission works) AND unauthorized read is denied (blocked).

task03: the patch = a localization integrity check (physical_sim with KNIGHTFALL_HARDENED=1
        ignores external /loc_spoof). Attacker still publishes the spoof, but the TRUE robot
        reaches the goal anyway -> attack blocked AND mission still works.
"""
from __future__ import annotations
import json, math, os, re, shutil, signal, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))
from fix_oracle import FixOracle  # noqa: E402

ROS_SETUP = "/opt/ros/humble/setup.bash"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")


def _sh(cmd, domain, **kw):
    full = f"source {ROS_SETUP}; export ROS_DOMAIN_ID={domain}; {cmd}"
    return subprocess.run(["bash", "-lc", full], **kw)


class Task01FixOracle(FixOracle):
    challenge_id = "01-diagnostic-leak"

    def apply_patch(self):
        # run the secured (patched) acceptance: it exercises authorized read + denies the attacker
        script = os.path.join(REPO, "deliverable-01", "run_acceptance.sh")
        r = subprocess.run(["bash", "-lc", f"bash {script}"], capture_output=True, text=True, timeout=120)
        out = r.stdout + r.stderr
        self._legit = int(re.search(r"authorized listener heard:\s*(\d+)", out).group(1)) if re.search(r"authorized listener heard:\s*(\d+)", out) else 0
        self._atk = int(re.search(r"unauthorized listener heard:\s*(\d+)", out).group(1)) if re.search(r"unauthorized listener heard:\s*(\d+)", out) else -1

    def attack_blocked(self):
        return self._atk == 0, f"unauthorized reads under Enforce = {self._atk} (want 0)"

    def mission_still_works(self):
        return self._legit > 0, f"authorized maintenance reads = {self._legit} (want >0)"


class Task03FixOracle(FixOracle):
    challenge_id = "03-localization-spoof"
    DOMAIN = 58
    GOAL = (3.0, 0.0)
    DEV_THRESHOLD = 1.0

    def apply_patch(self):
        # hardened sim: integrity check ignores /loc_spoof. Ground truth is read from the
        # judge-only truth file (min distance the TRUE pose got to the goal), not DDS.
        self._truth = os.path.join(tempfile.mkdtemp(prefix="kf-oracle-truth-"), "truth.json")
        full = (f"source {ROS_SETUP}; export ROS_DOMAIN_ID={self.DOMAIN}; "
                f"KNIGHTFALL_HARDENED=1 GOAL_X={self.GOAL[0]} GOAL_Y={self.GOAL[1]} "
                f"KNIGHTFALL_TRUTH_FILE={self._truth} python3 {HERE}/physical_sim.py")
        self._sim = subprocess.Popen(["bash", "-lc", full], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        time.sleep(4)
        # attacker still tries to spoof
        full2 = (f"source {ROS_SETUP}; export ROS_DOMAIN_ID={self.DOMAIN}; "
                 f'ros2 topic pub -r 5 /loc_spoof geometry_msgs/msg/Vector3 "{{x: 0.0, y: 2.0}}"')
        self._pub = subprocess.Popen(["bash", "-lc", full2], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        time.sleep(16)                                # let it navigate under the (ignored) spoof
        gt = self._read_truth()
        # where the TRUE robot ended up; small => the (ignored) spoof did not move it off goal
        if gt:
            tx, ty = gt.get("true", (99.0, 99.0))
            self._dist = math.hypot(self.GOAL[0] - tx, self.GOAL[1] - ty)
        else:
            self._dist = 99.0

    def _read_truth(self):
        try:
            with open(self._truth) as fh:
                return json.load(fh)
        except (OSError, ValueError, TypeError):
            return None

    def attack_blocked(self):
        return self._dist <= self.DEV_THRESHOLD, f"closest TRUE approach to goal under spoof = {round(self._dist,2)} m (want <= {self.DEV_THRESHOLD})"

    def mission_still_works(self):
        return self._dist < 0.15, f"robot reached goal (closest {round(self._dist,2)} m, want < 0.15)"

    def teardown(self):
        for p in (getattr(self, "_pub", None), getattr(self, "_sim", None)):
            if p:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
        if getattr(self, "_truth", None):
            shutil.rmtree(os.path.dirname(self._truth), ignore_errors=True)
