"""Knightfall flags — the CTF shell over the graded judge (CORE.md §5).

Two kinds of flag:
  - info flag   : a per-round secret placed IN the target; captured by finding and reading it
                  (scoring type `flag_submit`, e.g. task01 — the submitted secret is the flag).
  - effect flag : minted by the judge only after it confirms an effect in ground truth
                  (scoring type `judge_confirm`), one per weighted layer.

Effect flag = KF{ HMAC-SHA256(round_secret, "<challenge>|<layer>")[:128 bits] }. The round secret
is generated per session and never leaves the judge, so an effect flag cannot be forged, guessed
from the challenge/layer name, or replayed into another round.
"""
from __future__ import annotations
import hashlib
import hmac
import secrets

PREFIX = "KF"


class FlagMinter:
    def __init__(self, round_secret: bytes | None = None):
        self._secret = round_secret if round_secret is not None else secrets.token_bytes(32)

    def mint(self, challenge_id: str, layer: str) -> str:
        mac = hmac.new(self._secret, f"{challenge_id}|{layer}".encode(), hashlib.sha256)
        return f"{PREFIX}{{{mac.hexdigest()[:32]}}}"

    def identify(self, challenge_id: str, value: str, layers) -> str | None:
        """Which layer's flag `value` is for this round, or None (constant-time compare)."""
        value = (value or "").strip()
        for layer in layers:
            if hmac.compare_digest(self.mint(challenge_id, layer), value):
                return layer
        return None


def effect_layers(scoring: dict) -> list[str]:
    """Layers that earn an effect flag: the weighted layers of a judge-confirmed scenario.
    flag_submit scenarios capture an info flag instead, so they get none."""
    if scoring.get("type") != "judge_confirm":
        return []
    return [layer for layer, w in scoring.get("graded", {}).items() if w > 0]
