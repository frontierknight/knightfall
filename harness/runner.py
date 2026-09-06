"""Knightfall challenge runner — the lifecycle that turns a scenario into a scored trajectory.

Ties together the scenario spec, the trajectory logger, and the judge, and enforces the
DESIGN invariants:
  readiness gate (before the clock)  →  budget clock (steps primary, wall-clock secondary)
  →  run (agent/human acts; every action logged as a trajectory step)
  →  judge scores from checkpoints the backend CONFIRMED (ground-truth held by the judge)
  →  destroy-and-recreate reset.

ROS/sim specifics live behind `ChallengeBackend` (implemented per challenge, with ground-truth
access). This module is backend-agnostic so it works for task 1 (SROS2) and the physical task
alike, and for both human and agent actors. Pure stdlib + local trajectory/judge.
"""
from __future__ import annotations
import time
from abc import ABC, abstractmethod
from trajectory import Trajectory
from judge import Judge


class ChallengeBackend(ABC):
    """Per-challenge hooks. The backend holds ground truth; the attacker never sees it."""

    @abstractmethod
    def readiness_check(self) -> tuple[bool, str]:
        """Return (ok, detail). Must pass BEFORE the budget clock starts:
        required nodes up, legit comms ok, task system accepts work, sim & judge ready."""

    @abstractmethod
    def briefing(self) -> dict:
        """Task briefing + connection info handed to the actor (no ground truth)."""

    @abstractmethod
    def confirm_checkpoints(self) -> set[str]:
        """Ground-truth verification: which of the 4 layers actually fired this run.
        (e.g. read from sim ground-truth bus / mission state — never from attacker reports.)"""

    @abstractmethod
    def reset(self) -> None:
        """Destroy-and-recreate the whole round: nodes, creds, discovery cache, retained msgs,
        params, mission state, sim state, per-round flag."""


class Actor(ABC):
    """Human (interactive terminal) or agent (adapter layer). Yields actions, sees observations."""
    kind: str
    name: str

    @abstractmethod
    def act(self, briefing: dict, step_fn) -> None:
        """Drive the attack. Call step_fn(action, observation) for each action taken;
        step_fn returns the running step count so the actor can respect the step budget."""


def run_challenge(scenario: dict, backend: ChallengeBackend, actor: Actor, out_path: str) -> dict:
    judge = Judge(scenario["scoring"])
    budget = scenario["budget"]

    ok, detail = backend.readiness_check()
    if not ok:
        return {"outcome": "startup_failure", "detail": detail}

    with Trajectory(
        scenario_id=scenario["id"], scenario_version=scenario["version"],
        actor_kind=actor.kind, actor_name=actor.name,
        budget=budget, env=scenario["env"], path=out_path, max_score=judge.max_score,
    ) as traj:
        briefing = backend.briefing()
        t0 = time.monotonic()
        steps = {"n": 0}

        def step_fn(action, observation):
            steps["n"] += 1
            hit = backend.confirm_checkpoints()          # ground-truth, checked each step
            traj.step(action=action, observation=observation, checkpoints_hit=sorted(hit))
            over_steps = steps["n"] >= budget.get("steps", 10**9)
            over_time = (time.monotonic() - t0) >= budget.get("wall_clock_s", 10**9)
            if over_steps or over_time:
                raise _BudgetExceeded()
            return steps["n"]

        outcome = "fail"
        try:
            actor.act(briefing, step_fn)
        except _BudgetExceeded:
            outcome = "timeout"
        except Exception as e:                            # noqa: BLE001 - record, don't crash the run
            outcome = "error"; traj.step({"error": str(e)}, "actor raised", [], 0.0)

        confirmed = backend.confirm_checkpoints()
        result = judge.score(confirmed)
        if outcome == "fail" and result["binary_pass"]:
            outcome = "success"
        traj.result(final_score=result["graded_score"], outcome=outcome,
                    checkpoints=result["breakdown"],
                    budget_used={"steps": steps["n"],
                                 "wall_clock_s": round(time.monotonic() - t0, 1)})

    backend.reset()
    return {"outcome": outcome, **result, "trajectory": out_path}


class _BudgetExceeded(Exception):
    pass
