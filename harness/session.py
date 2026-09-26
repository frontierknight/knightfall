"""Knightfall Session — the ONE uniform attacker console (human == agent).

The range exposes exactly this interface. A player (human REPL, agent adapter, or a scripted
self-test — no difference to the range) drives a challenge by:
    run_command(cmd) -> observation      # a command in the attacker terminal
    submit(value)    -> accepted?        # (challenges that use a flag)
    finish()         -> scored result
Every call is logged to a trajectory; finish() scores via the judge. When the judge confirms a
weighted layer of a judge-confirmed scenario, the session mints that layer's effect flag
(flags.py); captured_flags() shows them to the player. So every session — whoever
plays — yields one RL-ready trajectory.

The backend (per challenge) provides the attacker sandbox (`exec_action`), `briefing`,
`confirm_checkpoints` (ground truth), optional `submit`, and `reset`.
"""
from __future__ import annotations
import time
from trajectory import Trajectory
from judge import Judge
from provenance import collect as collect_provenance
from flags import FlagMinter, effect_layers

BUDGET_EXHAUSTED = "[budget exhausted: no further actions accepted; type 'done' to score]"


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
            provenance=collect_provenance(scenario),
        )
        self._steps = 0
        self._t0 = None
        self._judge_s = 0.0       # time spent in judge-side checks; not charged to the player
        self._open = False
        self._minter = FlagMinter()          # per-round secret; never leaves the judge side
        self._effect_layers = effect_layers(scenario["scoring"])
        self._flags = {}                     # layer -> effect flag, minted once confirmed

    def start(self):
        ok, detail = self.backend.readiness_check()
        if not ok:
            return None, f"startup_failure: {detail}"
        self._traj.__enter__(); self._open = True
        self._t0 = time.monotonic()
        return self.backend.briefing(), None

    def _player_time(self):
        """Wall-clock seconds charged to the player (judge-side check time excluded)."""
        return (time.monotonic() - self._t0 - self._judge_s) if self._t0 else 0.0

    def budget_left(self):
        return {"steps": max(0, self.budget.get("steps", 0) - self._steps),
                "wall_clock_s": max(0.0, round(self.budget.get("wall_clock_s", 0) - self._player_time(), 1))}

    def over_budget(self) -> bool:
        if self._steps >= self.budget.get("steps", 10**9):
            return True
        return self._player_time() >= self.budget.get("wall_clock_s", 10**9)

    def _checkpoints(self):
        t = time.monotonic()
        try:
            confirmed = sorted(self.backend.confirm_checkpoints())
            for layer in confirmed:
                if layer in self._effect_layers and layer not in self._flags:
                    self._flags[layer] = self._minter.mint(self.scenario["id"], layer)
            return confirmed
        finally:
            self._judge_s += time.monotonic() - t

    def checkpoints(self) -> list:
        """Confirmed checkpoints now (judge-side; mints any newly earned effect flags). For
        callers outside the action loop, e.g. the web console polling live state."""
        return self._checkpoints()

    def captured_flags(self) -> dict:
        """Effect flags captured so far (layer -> flag), in layer order."""
        return {layer: self._flags[layer] for layer in self._effect_layers if layer in self._flags}

    def run_command(self, cmd: str) -> str:
        """Run one action in the attacker terminal; log it; return the observation.
        Refused (not executed, not logged as a step) once the budget is exhausted."""
        if self.over_budget():
            return BUDGET_EXHAUSTED
        obs = self.backend.exec_action(cmd)
        self._steps += 1
        self._traj.step(action={"cmd": cmd}, observation=obs, checkpoints_hit=self._checkpoints())
        return obs

    def submit(self, value: str) -> bool:
        if self.over_budget():
            return False
        ok = self.backend.submit(value) if hasattr(self.backend, "submit") else False
        self._steps += 1
        self._traj.step(action={"submit": value}, observation=f"accepted={ok}",
                        checkpoints_hit=self._checkpoints())
        return ok

    def finish(self) -> dict:
        confirmed = self._checkpoints()
        res = self.judge.score(confirmed)
        outcome = "success" if res["binary_pass"] else "fail"
        used = {"steps": self._steps, "wall_clock_s": round(self._player_time(), 1),
                "judge_s": round(self._judge_s, 1), "exhausted": self.over_budget()}
        extra = self.backend.artifacts() if hasattr(self.backend, "artifacts") else None
        flags = self.captured_flags()
        if self._effect_layers:
            extra = {**(extra or {}), "flags_captured": list(flags)}
        if self._open:
            self._traj.result(final_score=res["graded_score"], outcome=outcome,
                              checkpoints=res["breakdown"], budget_used=used, extra=extra)
            self._traj.__exit__()
            self._open = False
        self.backend.reset()
        return {"outcome": outcome, **res, "flags": flags, "budget_used": used,
                "trajectory": self._traj.path}
