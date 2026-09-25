"""Unit tests for the web gateway's SessionManager (E4 core) — no ROS, no sockets.

Drives the server-side session lifecycle against a fake backend + fake make(), so the play API
(start -> action -> submit -> finish, and unknown-session handling) is verified in CI without a ROS
graph. Run: python3 harness/test_web.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
sys.path.insert(0, os.path.dirname(__file__))
from server import SessionManager  # noqa: E402


class FakeBackend:
    def readiness_check(self): return True, "ok"
    def briefing(self): return {"goal": "demo"}
    def exec_action(self, cmd): return f"ran {cmd}"
    def submit(self, value): 
        self._ok = getattr(self, "_ok", False) or value == "FLAG{x}"
        return self._ok
    def confirm_checkpoints(self): return {"interface_op"} if getattr(self, "_ok", False) else set()
    def reset(self): pass


def fake_make(task):
    scenario = {"id": "test-" + task, "version": "0", "env": {},
                "budget": {"steps": 5, "wall_clock_s": 600},
                "scoring": {"final_condition": "interface_op", "type": "flag_submit",
                            "graded": {"interface_op": 1.0}}}
    return scenario, FakeBackend()


class WebSessionTest(unittest.TestCase):
    def setUp(self):
        # write trajectories into a temp dir by pointing the module's TRAJ_DIR there
        import server
        self._tmp = tempfile.mkdtemp()
        server.TRAJ_DIR = self._tmp
        self.mgr = SessionManager(make=fake_make)

    def test_full_lifecycle(self):
        started = self.mgr.start("task01")
        sid = started["id"]
        self.assertIn("briefing", started)
        self.assertEqual(started["budget_left"]["steps"], 5)
        act = self.mgr.action(sid, "ros2 topic list")
        self.assertEqual(act["observation"], "ran ros2 topic list")
        self.assertEqual(act["checkpoints"], [])
        sub = self.mgr.submit(sid, "FLAG{x}")
        self.assertTrue(sub["accepted"])
        self.assertEqual(sub["checkpoints"], ["interface_op"])
        res = self.mgr.finish(sid)
        self.assertTrue(res["binary_pass"])
        # session is gone after finish
        self.assertEqual(self.mgr.finish(sid).get("error"), "unknown session")

    def test_unknown_session(self):
        self.assertEqual(self.mgr.action("nope", "x").get("error"), "unknown session")
        self.assertEqual(self.mgr.submit("nope", "x").get("error"), "unknown session")

    def test_budget_enforced_via_manager(self):
        sid = self.mgr.start("task01")["id"]
        for i in range(5):
            self.mgr.action(sid, f"cmd{i}")
        over = self.mgr.action(sid, "one too many")
        self.assertTrue(over["over_budget"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
