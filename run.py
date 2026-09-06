#!/usr/bin/env python3
"""Knightfall CLI — one entry point. Human and agent use the SAME range (see harness/session.py).

Run on the ROS box (ROS 2 sourced):
    python3 run.py list                 # list challenges
    python3 run.py play <task>          # YOU play it: interactive attacker console -> score + trajectory
    python3 run.py selftest [task|all]  # scripted smoke test (proves solvable + machinery)
    python3 run.py oracle               # fix-oracles: defense blocks attack AND keeps the mission

<task> ∈ { task01, task03 }.  Every session (human / agent / selftest) writes a trajectory.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
H = os.path.join(HERE, "harness")
sys.path.insert(0, os.path.join(HERE, "challenges"))


def do_list():
    from registry import SCENARIOS
    print("Knightfall challenges:")
    for k, sc in SCENARIOS.items():
        print(f"  {k:8} {sc['id']:24} {sc['desc']}")
    print("\nplay it yourself:  python3 run.py play task01"
          "   |   smoke test:  python3 run.py selftest all"
          "   |   defenses:  python3 run.py oracle")


def _exec(script, *args):
    sys.exit(subprocess.run([sys.executable, os.path.join(H, script), *args]).returncode)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        do_list()
    elif cmd == "play" and len(sys.argv) > 2:
        _exec("play.py", sys.argv[2])
    elif cmd == "selftest":
        _exec("selftest.py", sys.argv[2] if len(sys.argv) > 2 else "all")
    elif cmd == "oracle":
        _exec("run_fix_oracles.py")
    else:
        print(__doc__); sys.exit(2)
