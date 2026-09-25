"""Measure task03's determinism envelope (audit M7): how much does the settled TRUE deviation
vary run to run? The physics integrator is deterministic, but ROS message timing/scheduling adds
jitter, so the scoring margin must be justified by the measured spread, not assumed.

For N runs it drives the scripted spoof through the real Session, reads the settled TRUE pose from
the judge-only truth file, and reports the distribution of the deviation from the goal. Compare the
spread against the scenario threshold (1.0 m) to confirm the margin is safe.

Run inside the range image:
  python3 run.py measure [N]          # default N=8
"""
from __future__ import annotations
import math
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "challenges"))
from session import Session          # noqa: E402
from registry import make            # noqa: E402
from selftest import solve_task03    # noqa: E402

GOAL = (3.0, 0.0)


def one_run(i):
    scenario, backend = make("task03")
    out = os.path.join(HERE, "..", "trajectories", f"measure_task03_{i}.jsonl")
    s = Session(scenario, backend, "measure", "determinism", out)
    _, err = s.start()
    if err:
        return None
    solve_task03(s)
    gt = backend._read_truth()
    dev = None
    if gt:
        tx, ty = gt.get("true", (0.0, 0.0))
        dev = math.hypot(GOAL[0] - tx, GOAL[1] - ty)
    s.finish()
    return dev


def main(argv=None):
    n = int(argv[0]) if argv else 8
    devs = []
    for i in range(n):
        d = one_run(i)
        print(f"  run {i}: deviation = {round(d, 4) if d is not None else 'n/a'} m")
        if d is not None:
            devs.append(d)
        time.sleep(1)
    if not devs:
        print("no successful runs"); return 1
    lo, hi = min(devs), max(devs)
    mean = statistics.mean(devs)
    sd = statistics.pstdev(devs) if len(devs) > 1 else 0.0
    print("\ntask03 settled deviation over", len(devs), "runs:")
    print(f"  mean={mean:.4f}  sd={sd:.4f}  min={lo:.4f}  max={hi:.4f}")
    print(f"  threshold=1.0 m ; margin to threshold = {lo - 1.0:.4f} m (min deviation - threshold)")
    print("  VERDICT:", "robust (all runs clear the threshold)" if lo > 1.0
          else "MARGIN TOO TIGHT — some runs fall below threshold")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
