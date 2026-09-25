"""Challenge registry — the scenario YAML is the single source of truth (audit M6).

Every driver (human play, agent adapter, self-test) loads scenarios from ../scenarios/*.yaml
through this module, so the runtime budget/env/scoring cannot drift from the spec. The backend
(ROS/sim specifics) is the only thing bound in code, keyed by the scenario id.
"""
from __future__ import annotations
import glob
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from task01_diagnostic_leak import DiagnosticLeakBackend
from task03_localization_spoof import LocalizationSpoofBackend

SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "..", "scenarios")

# task key (CLI handle) -> (scenario id in YAML, backend class)
_BACKENDS = {
    "task01": ("01-diagnostic-leak", DiagnosticLeakBackend),
    "task03": ("03-localization-spoof", LocalizationSpoofBackend),
}


def _load_by_id():
    out = {}
    for path in glob.glob(os.path.join(SCENARIO_DIR, "*.yaml")):
        with open(path) as fh:
            doc = yaml.safe_load(fh)
        if isinstance(doc, dict) and "id" in doc:
            out[doc["id"]] = doc
    return out


def _runtime_view(doc: dict) -> dict:
    """The subset the harness (Session/Judge/Trajectory) reads, projected from the full spec."""
    return {
        "id": doc["id"],
        "version": str(doc.get("version", "0")),
        "desc": doc.get("desc") or doc.get("title", doc["id"]),
        "budget": doc["budget"],
        "env": doc["env"],
        "scoring": doc["scoring"],
    }


_BY_ID = _load_by_id()
SCENARIOS = {}
for _key, (_sid, _cls) in _BACKENDS.items():
    if _sid in _BY_ID:
        SCENARIOS[_key] = _runtime_view(_BY_ID[_sid])
BACKENDS = {k: cls for k, (sid, cls) in _BACKENDS.items()}


def make(task):
    if task not in SCENARIOS:
        raise KeyError(f"unknown challenge '{task}'; have {list(SCENARIOS)}")
    return SCENARIOS[task], BACKENDS[task]()
