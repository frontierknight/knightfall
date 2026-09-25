"""Seeded per-round variation (audit m1) — defeat memorized/public solutions.

A challenge derives its per-round parameters deterministically from KNIGHTFALL_SEED, so a fresh
seed changes what the attacker must discover while the flaw class stays the same. With no seed the
default (index 0) is used, which keeps CI, the reference samples, and QUICKSTART deterministic.

Held-out seeds: reserve a disjoint set for evaluation that never appears in the repo's samples or
docs, so a system tuned on public rounds is still tested on unseen ones. Convention: public/demo
seeds are small integers 0–99; evaluation uses seeds >= 1000 (kept out of the repo).
"""
from __future__ import annotations
import hashlib


def _idx(seed, n):
    """Deterministic index in [0, n) from an arbitrary seed value (stable across processes)."""
    if seed is None or seed == "":
        return 0
    h = hashlib.sha256(str(seed).encode()).hexdigest()
    return int(h, 16) % n


# task02: which state-changing command the vulnerable policy wrongly grants to maintenance.
TASK02_COMMANDS = ["cancel", "redirect"]


def task02_overprivileged_command(seed):
    return TASK02_COMMANDS[_idx(seed, len(TASK02_COMMANDS))]
