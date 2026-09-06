"""Run all fix-oracles — proves each challenge's defense blocks the attack AND keeps the mission.

Run on the box (ROS sourced):  python3 run_fix_oracles.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "challenges"))

from fix_oracle import run_oracle, report          # noqa: E402
from oracles import Task01FixOracle, Task03FixOracle  # noqa: E402

if __name__ == "__main__":
    allpass = True
    for O in (Task01FixOracle, Task03FixOracle):
        res = run_oracle(O())
        print(report(res)); print()
        allpass = allpass and res["fix_oracle_pass"]
    print("ALL FIX-ORACLES PASS ✅" if allpass else "SOME FIX-ORACLES FAILED ❌")
    sys.exit(0 if allpass else 1)
