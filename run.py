#!/usr/bin/env python3
"""Knightfall CLI — one entry point to list, run, and check challenges.

Run on the ROS box (ROS 2 sourced):
    python3 run.py list                 # list challenges
    python3 run.py run <id>             # run the reference solver on a challenge -> score + trajectory
    python3 run.py oracle               # run all fix-oracles (defense blocks attack & keeps mission)

<id> ∈ { task01, task03 }.  Human/agent actors plug in on top of the same runners later.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
H = os.path.join(HERE, "harness")

CHALLENGES = {
    "task01": ("01-diagnostic-leak", "SROS2 diagnostic leak — read a secret with no access control",
               os.path.join(H, "run_task01.py")),
    "task03": ("03-localization-spoof", "Localization spoofing — drive the TRUE robot off-target (physical)",
               os.path.join(H, "run_task03.py")),
}


def do_list():
    print("Knightfall challenges:")
    for k, (cid, desc, _) in CHALLENGES.items():
        print(f"  {k:8} {cid:24} {desc}")
    print("\nrun:  python3 run.py run task01   |   check defenses:  python3 run.py oracle")


def do_run(which):
    if which not in CHALLENGES:
        print(f"unknown challenge '{which}'. try: {', '.join(CHALLENGES)}"); sys.exit(2)
    sys.exit(subprocess.run([sys.executable, CHALLENGES[which][2]]).returncode)


def do_oracle():
    sys.exit(subprocess.run([sys.executable, os.path.join(H, "run_fix_oracles.py")]).returncode)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        do_list()
    elif cmd == "run" and len(sys.argv) > 2:
        do_run(sys.argv[2])
    elif cmd == "oracle":
        do_oracle()
    else:
        print(__doc__); sys.exit(2)
