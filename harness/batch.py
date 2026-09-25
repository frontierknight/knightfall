"""Knightfall batch runner — run challenges x actors x trials, aggregate to a results table.

This is the benchmark's evaluation harness (audit M8): it runs reference baselines and produces
a comparable, reproducible table. Keyless baselines ship now; an LLM-agent actor plugs in later
through the same Session interface (the model keys stay outside the solving terminal, DESIGN §8).

Baselines (reference points that make agent scores meaningful):
  null     — does nothing. Must score 0 on every challenge (a challenge that rewards it is broken).
  random   — benign recon only. A weak lower bound; should also score ~0.
  scripted — the known-good exploit (the selftest solver). The reference upper bound.

Usage (in the range image):
  python3 run.py batch                       # all tasks, all baselines, 1 trial
  python3 run.py batch --tasks task02,task03 --actors null,scripted --trials 3
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "challenges"))
from session import Session          # noqa: E402
from registry import make, SCENARIOS  # noqa: E402
from selftest import SOLVERS          # noqa: E402  (reuse the scripted solvers)


def null_actor(s: Session, task: str):
    """Does nothing — the mandatory 0-score baseline."""
    return


def random_actor(s: Session, task: str):
    """Benign reconnaissance only (no exploit). A weak lower bound."""
    for cmd in ("ros2 topic list", "ros2 node list", "ros2 topic list"):
        s.run_command(cmd)
        time.sleep(0.2)


ACTORS = {
    "null": null_actor,
    "random": random_actor,
    "scripted": lambda s, t: SOLVERS[t](s),
}


def run_one(task: str, actor_name: str, trial: int) -> dict:
    scenario, backend = make(task)
    out = os.path.join(HERE, "..", "trajectories",
                       f"{scenario['id']}_{actor_name}_t{trial}.jsonl")
    s = Session(scenario, backend, actor_kind="baseline", actor_name=actor_name, out_path=out)
    _, err = s.start()
    if err:
        return {"outcome": "startup_failure", "graded_ratio": 0.0, "binary_pass": False,
                "graded_score": 0.0, "max_score": scenario["scoring"], "detail": err}
    try:
        ACTORS[actor_name](s, task)
    finally:
        res = s.finish()
    return res


def run_batch(tasks, actors, trials):
    rows = []
    for task in tasks:
        for actor in actors:
            scores, passes = [], 0
            for trial in range(trials):
                r = run_one(task, actor, trial)
                scores.append(r.get("graded_ratio", 0.0))
                passes += 1 if r.get("binary_pass") else 0
            rows.append({
                "task": task, "actor": actor, "trials": trials,
                "mean_graded_ratio": round(sum(scores) / len(scores), 3),
                "pass_rate": round(passes / trials, 3),
            })
    return rows


def print_table(rows):
    w = {"task": 8, "actor": 9, "trials": 6, "mean_graded_ratio": 18, "pass_rate": 9}
    hdr = "  ".join(h.ljust(w[h]) for h in w)
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print("  ".join(str(r[h]).ljust(w[h]) for h in w))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=",".join(SCENARIOS))
    ap.add_argument("--actors", default="null,random,scripted")
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--json", default=None, help="also write the rows to this JSON path")
    a = ap.parse_args(argv)
    tasks = [t for t in a.tasks.split(",") if t]
    actors = [x for x in a.actors.split(",") if x]
    rows = run_batch(tasks, actors, a.trials)
    print_table(rows)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(rows, fh, indent=2)
        print(f"\nwrote {a.json}")
    return rows


if __name__ == "__main__":
    main()
