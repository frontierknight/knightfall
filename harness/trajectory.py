"""Knightfall trajectory logger — the RL-ready record of one full run (agent or human).

A trajectory is Knightfall's core unit (README: "every full agent run is one trajectory").
It is written as JSONL so it streams, is diffable, and is directly consumable by later RL:
each step carries (observation, action, reward_delta) — the RL transition tuple.

File shape (one JSON object per line):
  line 0     {"type":"meta",   ...}            scenario, actor, budget, env, start time
  step lines {"type":"step",   i, t, action, observation, checkpoints_hit, reward_delta}
  last line  {"type":"result", final_score, max_score, outcome, checkpoints, budget_used}

This module has NO ROS/heavy deps — pure stdlib — so it runs anywhere (box, CI, tests).
"""
from __future__ import annotations
import json, time, os
from dataclasses import dataclass, field, asdict


@dataclass
class Trajectory:
    scenario_id: str
    scenario_version: str
    actor_kind: str                 # "agent" | "human"
    actor_name: str                 # e.g. "crimson-knight@deepseek-v4-flash" or "human:viryazheng"
    budget: dict                    # {steps, wall_clock_s, tokens}
    env: dict                       # version record (ros_distro, rmw, sim, ...)
    path: str                       # output .jsonl path
    max_score: float = 1.0
    _step: int = field(default=0, init=False)
    _t0: float = field(default_factory=time.monotonic, init=False)
    _fh: object = field(default=None, init=False)

    def __enter__(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self._fh = open(self.path, "w", buffering=1)   # line-buffered
        self._emit({
            "type": "meta", "scenario_id": self.scenario_id,
            "scenario_version": self.scenario_version,
            "actor": {"kind": self.actor_kind, "name": self.actor_name},
            "budget": self.budget, "env": self.env, "max_score": self.max_score,
            "started_at": time.time(),
        })
        return self

    def step(self, action, observation, checkpoints_hit=None, reward_delta=0.0):
        """Log one transition. action/observation are what the agent did/saw (RL tuple)."""
        self._step += 1
        self._emit({
            "type": "step", "i": self._step,
            "t_mono": round(time.monotonic() - self._t0, 3),
            "action": action, "observation": observation,
            "checkpoints_hit": checkpoints_hit or [], "reward_delta": reward_delta,
        })
        return self._step

    def result(self, final_score, outcome, checkpoints, budget_used):
        """Close the trajectory with the final score + outcome (success|fail|timeout|error)."""
        self._emit({
            "type": "result", "final_score": final_score, "max_score": self.max_score,
            "outcome": outcome, "checkpoints": checkpoints, "budget_used": budget_used,
            "steps": self._step, "ended_at": time.time(),
        })

    def _emit(self, obj):
        self._fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def __exit__(self, *exc):
        if self._fh:
            self._fh.close()


def load(path):
    """Read a trajectory back as a list of records (for scoring/RL/analysis)."""
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]
