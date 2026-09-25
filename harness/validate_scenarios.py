"""Validate every scenarios/*.yaml against the required shape (audit M6; CI gate).

Lightweight, stdlib + PyYAML only — no jsonschema dependency. Checks the fields the harness
and the benchmark rely on, and that scoring weights / final_condition are internally consistent.

Run:  python3 harness/validate_scenarios.py
"""
import glob
import os
import sys

import yaml

LAYERS = {"interface_op", "target_accept", "mission_impact", "physical_impact"}
REQUIRED_TOP = ["id", "title", "version", "category", "difficulty", "normal_mission",
                "attacker", "flaw", "attack_goal", "budget", "scoring", "fix_oracle",
                "reset_scope", "readiness_checks", "env"]
DIR = os.path.join(os.path.dirname(__file__), "..", "scenarios")


def _err(errs, sid, msg):
    errs.append(f"[{sid}] {msg}")


def validate(doc, errs):
    sid = doc.get("id", "?")
    for k in REQUIRED_TOP:
        if k not in doc:
            _err(errs, sid, f"missing required field '{k}'")
    b = doc.get("budget", {})
    for k in ("steps", "wall_clock_s"):
        if not isinstance(b.get(k), int):
            _err(errs, sid, f"budget.{k} must be an int")
    sc = doc.get("scoring", {})
    graded = sc.get("graded", {})
    if set(graded) != LAYERS:
        _err(errs, sid, f"scoring.graded must cover exactly {sorted(LAYERS)}, got {sorted(graded)}")
    fc = sc.get("final_condition")
    if fc not in LAYERS:
        _err(errs, sid, f"scoring.final_condition '{fc}' is not a valid layer")
    elif graded.get(fc, 0) <= 0:
        _err(errs, sid, f"final_condition '{fc}' has zero weight — it can never pass")
    if sc.get("type") not in ("flag_submit", "judge_confirm"):
        _err(errs, sid, f"scoring.type '{sc.get('type')}' invalid")
    if fc == "physical_impact" and not sc.get("physical"):
        _err(errs, sid, "physical task must define scoring.physical (measure/threshold/trials)")


def main():
    paths = sorted(glob.glob(os.path.join(DIR, "*.yaml")))
    if not paths:
        print("no scenarios found"); return 1
    errs, ids = [], []
    for p in paths:
        with open(p) as fh:
            doc = yaml.safe_load(fh)
        if not isinstance(doc, dict) or "id" not in doc:
            errs.append(f"{os.path.basename(p)}: not a scenario document"); continue
        ids.append(doc["id"]); validate(doc, errs)
    if len(ids) != len(set(ids)):
        errs.append(f"duplicate scenario ids: {ids}")
    if errs:
        print("SCENARIO VALIDATION FAILED:")
        for e in errs:
            print("  -", e)
        return 1
    print(f"scenario validation PASS ({len(ids)}: {', '.join(ids)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
