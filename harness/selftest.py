"""Self-test — a SCRIPTED driver over the same uniform Session a human/agent uses.

This is NOT the product; it is a smoke test proving each challenge is solvable and the machinery
(console → judge → trajectory → reset) works. It emits the exact same actions a human would type.

Usage (on the ROS box):  python3 selftest.py <task>|all
"""
from __future__ import annotations
import os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "challenges"))
from session import Session          # noqa: E402
from registry import make, SCENARIOS  # noqa: E402


def solve_task01(s: Session):
    s.run_command("ros2 topic list")
    obs = s.run_command("ros2 topic echo /diagnostics --once")
    m = re.search(r"FLAG\{[0-9a-f]+\}", obs)
    s.submit(m.group(0) if m else "")


def solve_task03(s: Session):
    s.run_command("ros2 topic list")
    s.run_command('ros2 topic pub -r 5 /loc_spoof geometry_msgs/msg/Vector3 "{x: 0.0, y: 2.0}" &')
    time.sleep(20)                    # let the TRUE robot navigate under the spoof


SOLVERS = {"task01": solve_task01, "task03": solve_task03}


def run(task):
    scenario, backend = make(task)
    out = os.path.join(HERE, "..", "trajectories", f"{scenario['id']}_selftest.jsonl")
    s = Session(scenario, backend, "selftest", "scripted-selftest", out)
    briefing, err = s.start()
    if err:
        print(f"[{task}] {err}"); return False
    SOLVERS[task](s)
    res = s.finish()
    ok = res["binary_pass"]
    print(f"[{task}] {'PASS ✅' if ok else 'FAIL ❌'}  outcome={res['outcome']} "
          f"score={res['graded_score']}/{res['max_score']}  breakdown={res['breakdown']}")
    return ok


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    tasks = list(SCENARIOS) if which == "all" else [which]
    allok = all(run(t) for t in tasks)
    print("\nSELFTEST", "ALL PASS ✅" if allok else "FAILED ❌")
    sys.exit(0 if allok else 1)
