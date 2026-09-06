"""Knightfall Session — the ONE uniform attacker console (human == agent).

The range exposes exactly this interface. A player (human REPL, agent adapter, or a scripted
self-test — no difference to the range) drives a challenge by:
    run_command(cmd) -> observation      # a command in the attacker terminal
    submit(value)    -> accepted?        # (challenges that use a flag)
    finish()         -> scored result
Every call is logged to a trajectory; finish() scores via the judge. So every session — whoever
plays — yields one RL-ready trajectory.

The backend (per challenge) provides the attacker sandbox (`exec_action`), `briefing`,
`confirm_checkpoints` (ground truth), optional `submit`, and `reset`.
"""
from __future__ import annotations
import time
from trajectory import Trajectory
from judge import Judge


class Session:
    def __init__(self, scenario: dict, backend, actor_kind: str, actor_name: str, out_path: str):
        self.scenario = scenario
        self.backend = backend
        self.judge = Judge(scenario["scoring"])
        self.budget = scenario["budget"]
        self._traj = Trajectory(
            scenario_id=scenario["id"], scenario_version=scenario["version"],
            actor_kind=actor_kind, actor_name=actor_name,
            budget=self.budget, env=scenario["env"], path=out_path,
            max_score=self.judge.max_score,
        )
        self._steps = 0
        self._t0 = None
        self._open = False

    def start(self):
        ok, detail = self.backend.readiness_check()
        if not ok:
            return None, f"startup_failure: {detail}"
        self._traj.__enter__(); self._open = True
        self._t0 = time.monotonic()
        return self.backend.briefing(), None

    def budget_left(self):
        used_steps = self._steps
        used_time = time.monotonic() - self._t0 if self._t0 else 0
        return {"steps": self.budget.get("steps", 0) - used_steps,
                "wall_clock_s": round(self.budget.get("wall_clock_s", 0) - used_time, 1)}

    def _over_budget(self):
        if self._steps >= self.budget.get("steps", 10**9):
            return True
        if self._t0 and (time.monotonic() - self._t0) >= self.budget.get("wall_clock_s", 10**9):
            return True
        return False

    def run_command(self, cmd: str) -> str:
        """Run one action in the attacker terminal; log it; return the observation."""
        obs = self.backend.exec_action(cmd)
        self._steps += 1
        hit = sorted(self.backend.confirm_checkpoints())
        self._traj.step(action={"cmd": cmd}, observation=obs[:2000], checkpoints_hit=hit)
        return obs

    def submit(self, value: str) -> bool:
        ok = self.backend.submit(value) if hasattr(self.backend, "submit") else False
        self._steps += 1
        hit = sorted(self.backend.confirm_checkpoints())
        self._traj.step(action={"submit": value}, observation=f"accepted={ok}", checkpoints_hit=hit)
        return ok

    def finish(self) -> dict:
        confirmed = self.backend.confirm_checkpoints()
        res = self.judge.score(confirmed)
        outcome = "success" if res["binary_pass"] else "fail"
        used = {"steps": self._steps,
                "wall_clock_s": round(time.monotonic() - self._t0, 1) if self._t0 else 0}
        if self._open:
            self._traj.result(final_score=res["graded_score"], outcome=outcome,
                              checkpoints=res["breakdown"], budget_used=used)
            self._traj.__exit__()
            self._open = False
        self.backend.reset()
        return {"outcome": outcome, **res, "budget_used": used, "trajectory": self._traj.path}
