"""Provenance for a trajectory (audit M5) — what produced this run, so a result is reproducible.

Pure stdlib. Every field degrades gracefully to None/"unknown" when the source isn't available
(e.g. no git in the image, digest not injected), so logging never fails. The range image injects
KNIGHTFALL_IMAGE_DIGEST at build/run time; git SHA is read from the checkout or GITHUB_SHA.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")


def _git_sha():
    for env in ("KNIGHTFALL_GIT_SHA", "GITHUB_SHA"):
        if os.environ.get(env):
            return os.environ[env]
    try:
        out = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def scenario_hash(scenario: dict) -> str:
    """Stable hash of the scenario spec, so a run is tied to the exact config it used."""
    blob = json.dumps(scenario, sort_keys=True, ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(blob).hexdigest()[:16]


def collect(scenario: dict, seed=None) -> dict:
    """Provenance record embedded in each trajectory's meta line."""
    return {
        "git_sha": _git_sha(),
        "image_digest": os.environ.get("KNIGHTFALL_IMAGE_DIGEST"),
        "scenario_hash": scenario_hash(scenario),
        "seed": seed if seed is not None else os.environ.get("KNIGHTFALL_SEED"),
        "ros_distro": os.environ.get("ROS_DISTRO"),
        "rmw": os.environ.get("RMW_IMPLEMENTATION"),
    }


if __name__ == "__main__":
    print(json.dumps(collect({"id": "demo", "scoring": {}}, seed=7), indent=2))
