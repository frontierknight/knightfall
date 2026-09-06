"""Knightfall fix-oracle — proves each challenge's defense WORKS *and* doesn't break function.

This is what makes Knightfall a benchmark, not just a CTF (DESIGN principle #4): for every
challenge, applying the patch must satisfy BOTH:
  (1) attack_blocked      — the same attack path now fails, and
  (2) mission_still_works — the legitimate task still completes.

Each challenge provides a FixOracle with two checks. This module runs them and reports PASS/FAIL.
Pure orchestration; the ROS specifics live in the per-challenge oracle (with ground-truth access).
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class FixOracle(ABC):
    challenge_id: str

    @abstractmethod
    def apply_patch(self) -> None:
        """Apply the corrective config (e.g. tighten SROS2 policy / add integrity check)."""

    @abstractmethod
    def attack_blocked(self) -> tuple[bool, str]:
        """Return (True, detail) iff the same attack path now FAILS."""

    @abstractmethod
    def mission_still_works(self) -> tuple[bool, str]:
        """Return (True, detail) iff the legitimate task still COMPLETES after the patch."""

    def teardown(self) -> None:
        pass


def run_oracle(oracle: FixOracle) -> dict:
    oracle.apply_patch()
    try:
        blocked, d1 = oracle.attack_blocked()
        works, d2 = oracle.mission_still_works()
    finally:
        oracle.teardown()
    ok = blocked and works
    return {
        "challenge": oracle.challenge_id,
        "attack_blocked": blocked, "attack_detail": d1,
        "mission_still_works": works, "mission_detail": d2,
        "fix_oracle_pass": ok,
    }


def report(result: dict) -> str:
    mark = "PASS ✅" if result["fix_oracle_pass"] else "FAIL ❌"
    return (f"[fix-oracle {result['challenge']}] {mark}\n"
            f"  attack_blocked      : {result['attack_blocked']}  ({result['attack_detail']})\n"
            f"  mission_still_works : {result['mission_still_works']}  ({result['mission_detail']})")
