"""Benchmark sanity check (audit E0/M8): the range must discriminate.

Runs the null baseline (must score 0 on every challenge) and the scripted reference solver
(must pass every challenge) through the batch runner. A range that rewards the null actor, or
that the reference solver cannot pass, is broken. Needs ROS — run inside the range image:
  python3 harness/test_batch_sanity.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from batch import run_batch, SCENARIOS  # noqa: E402


def main():
    tasks = list(SCENARIOS)
    rows = run_batch(tasks, ["null", "scripted"], trials=1)
    bad = []
    for r in rows:
        if r["actor"] == "null" and (r["mean_graded_ratio"] != 0.0 or r["pass_rate"] != 0.0):
            bad.append(f"null scored on {r['task']}: {r}")
        if r["actor"] == "scripted" and r["pass_rate"] != 1.0:
            bad.append(f"scripted failed {r['task']}: {r}")
    if bad:
        print("BATCH SANITY FAILED:")
        for b in bad:
            print("  -", b)
        return 1
    print(f"batch sanity PASS ({len(tasks)} tasks: null=0, scripted=pass)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
