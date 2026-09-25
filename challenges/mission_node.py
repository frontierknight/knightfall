"""Knightfall mission-control node — the target for task 02 (maintenance over-privilege).

A single rclpy node holds the delivery mission's state and enforces a role-based access
policy loaded from a JSON file. A command arrives on /mission/command as a std_msgs/String
carrying JSON: {"role": "<role>", "cmd": "<cmd>"}. The node applies the command only if the
policy grants that role that permission — so the FLAW is a policy misconfiguration (the
vulnerable policy wrongly lists "cancel" under the maintenance role), not disabled security.
The fix-oracle swaps in the hardened policy; the same attack is then refused.

Ground truth (mission state + who changed it) is written to a judge-only file
(KNIGHTFALL_TRUTH_FILE), never onto the DDS graph the attacker shares (audit B1).

Env:
  KNIGHTFALL_MISSION_POLICY : path to the RBAC policy JSON (required)
  KNIGHTFALL_TRUTH_FILE     : judge-only state/event sink (required for scoring)
Run:  python3 mission_node.py
"""
from __future__ import annotations
import json
import os
import tempfile

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

POLICY_PATH = os.environ.get("KNIGHTFALL_MISSION_POLICY")
TRUTH_FILE = os.environ.get("KNIGHTFALL_TRUTH_FILE")
STATE_CHANGING = {"cancel", "redirect"}          # commands that alter mission state


class MissionControl(Node):
    def __init__(self):
        super().__init__("mission_control")
        self.state = "EN_ROUTE"                   # healthy mission toward the goal station
        self.changed_by_role = None               # who last changed the state (ground truth)
        self.saw_player_cmd = False               # a command reached the mission interface
        self.unauthorized_accepted = False        # a role acted beyond its intended permission
        self._policy = self._load_policy()
        self.create_subscription(String, "/mission/command", self._on_command, 10)
        self._write_truth()

    def _load_policy(self):
        with open(POLICY_PATH) as fh:
            return json.load(fh).get("permissions", {})

    def _on_command(self, msg):
        try:
            req = json.loads(msg.data)
            role, cmd = req.get("role"), req.get("cmd")
        except (ValueError, AttributeError):
            return
        self.saw_player_cmd = True
        allowed = cmd in self._policy.get(role, [])
        if not allowed:
            return                                # policy denies: command ignored
        # The policy granted it. If a non-dispatch role changes mission state, that is the
        # over-privilege being exercised — recorded as ground truth for the judge.
        if cmd in STATE_CHANGING:
            if role != "dispatcher":
                self.unauthorized_accepted = True
            self.state = "CANCELLED" if cmd == "cancel" else "REDIRECTED"
            self.changed_by_role = role
        self._write_truth()

    def _write_truth(self):
        if not TRUTH_FILE:
            return
        state = {"state": self.state, "changed_by_role": self.changed_by_role,
                 "saw_player_cmd": self.saw_player_cmd,
                 "unauthorized_accepted": self.unauthorized_accepted}
        d = os.path.dirname(TRUTH_FILE) or "."
        fd, tmp = tempfile.mkstemp(dir=d)
        with os.fdopen(fd, "w") as fh:
            json.dump(state, fh)
        os.replace(tmp, TRUTH_FILE)               # atomic: judge never reads a partial file


def main():
    rclpy.init()
    node = MissionControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
