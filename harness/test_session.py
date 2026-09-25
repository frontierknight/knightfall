"""Unit tests for Session budget enforcement (pure stdlib; no ROS needed).

Run:  python3 harness/test_session.py
"""
import os, sys, tempfile, time, unittest

sys.path.insert(0, os.path.dirname(__file__))
from session import Session, BUDGET_EXHAUSTED  # noqa: E402


class FakeBackend:
    def __init__(self, judge_delay=0.0):
        self.executed = []
        self.judge_delay = judge_delay

    def readiness_check(self):
        return True, "ok"

    def briefing(self):
        return {}

    def exec_action(self, cmd):
        self.executed.append(cmd)
        return f"ran {cmd}"

    def submit(self, value):
        return value == "FLAG{x}"

    def confirm_checkpoints(self):
        time.sleep(self.judge_delay)
        return set()

    def reset(self):
        pass


def scenario(steps=3, wall=600):
    return {"id": "test", "version": "0", "env": {},
            "budget": {"steps": steps, "wall_clock_s": wall},
            "scoring": {"final_condition": "interface_op", "type": "flag_submit",
                        "graded": {"interface_op": 1.0}}}


class SessionBudgetTest(unittest.TestCase):
    def _session(self, backend, **kw):
        out = os.path.join(tempfile.mkdtemp(), "t.jsonl")
        s = Session(scenario(**kw), backend, "test", "unit", out)
        s.start()
        return s

    def test_step_budget_refuses_extra_actions(self):
        b = FakeBackend()
        s = self._session(b, steps=2)
        s.run_command("a"); s.run_command("b")
        self.assertEqual(s.run_command("c"), BUDGET_EXHAUSTED)
        self.assertEqual(b.executed, ["a", "b"])           # third action never ran
        self.assertFalse(s.submit("FLAG{x}"))               # submit refused too
        res = s.finish()
        self.assertEqual(res["budget_used"]["steps"], 2)
        self.assertTrue(res["budget_used"]["exhausted"])
        self.assertFalse(res["binary_pass"])

    def test_judge_time_not_charged_to_player(self):
        s = self._session(FakeBackend(judge_delay=0.3), steps=10)
        s.run_command("a"); s.run_command("b")
        res = s.finish()
        self.assertGreaterEqual(res["budget_used"]["judge_s"], 0.5)
        self.assertLess(res["budget_used"]["wall_clock_s"], 0.3)

    def test_budget_left_never_negative(self):
        s = self._session(FakeBackend(), steps=1)
        s.run_command("a"); s.run_command("b")
        self.assertEqual(s.budget_left()["steps"], 0)
        s.finish()


if __name__ == "__main__":
    unittest.main(verbosity=2)
