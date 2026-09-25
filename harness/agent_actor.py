"""Knightfall agent adapter — plug an AI agent into the SAME Session humans use (DESIGN §8).

The range exposes one console: run_command(cmd) -> observation, submit(value), finish(). A human
types actions; an agent emits them. This adapter drives that console from a `policy` callable:

    policy(observation: str, context: dict) -> str

where the returned string is the next action. Two control actions are recognized:
    "submit <value>"  -> s.submit(value)
    "done"            -> stop
anything else is run as a command. The loop stops on "done", when the policy returns None, or when
the budget is exhausted (the Session refuses further actions).

KEY BOUNDARY (DESIGN §8): the model call and its API key live INSIDE the policy callable, which the
caller constructs OUTSIDE the solving terminal. This module never sees a key; it only exchanges
observations for action strings. So swapping models / prompting / multi-agent orchestration needs
no change here or to the target environment.

A real LLM policy (sketch, needs a key in the caller's env, not here):

    from anthropic import Anthropic
    client = Anthropic()                       # reads ANTHROPIC_API_KEY in the caller's env
    def policy(obs, ctx):
        msg = client.messages.create(model="claude-...", max_tokens=512,
                                     messages=[{"role": "user",
                                                "content": ctx["briefing_text"] + "\n\n" + obs}])
        return msg.content[0].text.strip()

This file ships only keyless demo policies so the wiring is testable in CI.
"""
from __future__ import annotations


def drive(session, policy, max_actions=None):
    """Drive a started Session with a policy callable. Returns the finish() result dict.

    session : a Session already started (start() called).
    policy  : (observation, context) -> action string | None
    """
    briefing = getattr(session, "backend").briefing()
    ctx = {"briefing": briefing, "briefing_text": _briefing_text(briefing)}
    obs = ctx["briefing_text"]
    n = 0
    while True:
        if max_actions is not None and n >= max_actions:
            break
        action = policy(obs, ctx)
        if action is None:
            break
        action = action.strip()
        if action == "done":
            break
        n += 1
        if action.startswith("submit "):
            ok = session.submit(action[len("submit "):].strip())
            obs = f"submit accepted={ok}"
        else:
            obs = session.run_command(action)
        if session.over_budget():
            break
    return session.finish()


def _briefing_text(briefing: dict) -> str:
    return "TASK BRIEFING:\n" + "\n".join(f"  {k}: {v}" for k, v in briefing.items())


# --- keyless demo policies (prove the wiring; not benchmark agents) --------------------------

def scripted_policy(script):
    """Turn a fixed list of actions into a policy (for tests / a deterministic reference)."""
    steps = list(script)

    def policy(obs, ctx):
        return steps.pop(0) if steps else "done"
    return policy
