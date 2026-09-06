# Knightfall harness — the evaluation core (benchmark + trajectory factory)

Backend-agnostic, pure-stdlib core that turns a scenario into a **scored trajectory**. Same code
scores humans and agents, task 1 (SROS2) and the physical task alike.

| File | Role |
|---|---|
| `trajectory.py` | The **RL-ready record** of one full run. JSONL; each step logs `(action, observation, reward_delta, checkpoints_hit)` — the RL transition tuple. This is the "trajectory factory" output contract. |
| `judge.py` | **Checkpoint-based graded scoring** (Cybench/DeepRed-style partial credit). Turns the 4 layers (interface→accept→mission→physical) into `graded_score` (agent view) + `binary_pass` (human view). Ground truth stays with the judge. |
| `runner.py` | The **lifecycle**: readiness gate → budget clock (steps primary) → run (actor acts, every action logged) → judge scores from backend-confirmed checkpoints → destroy-and-recreate reset. |

## Contracts to implement per challenge
- **`ChallengeBackend`** (in `runner.py`): `readiness_check`, `briefing`, `confirm_checkpoints`
  (ground-truth verification — reads sim ground truth / mission state, never attacker reports),
  `reset`. ROS/sim specifics live here.
- **`Actor`**: a human (interactive terminal) or an agent (adapter layer; model keys stay outside
  the solving terminal). Calls `step_fn(action, observation)` per action.

## Why this shape
- **Trajectory logging from day one** → every run is RL-ready (matches DeepRed's execution-trace
  recording; see `../RESEARCH.md`).
- **Graded checkpoints** → fair, comparable, non-sparse (Cybench subtasks / DeepRed checkpoints).
- **Backend-agnostic** → the physical-impact task plugs in the same way as the SROS2 task; its
  `confirm_checkpoints` compares perceived pose vs sim ground truth (the differentiator).

## Verified
- 2026-09-06: `judge.py` self-test PASS; `trajectory.py` read/write PASS; `runner.py` full
  lifecycle smoke test (mock backend + mock agent) PASS — readiness→run→score→trajectory→reset.

## Next
Implement the task-1 `ChallengeBackend` on the ROS box (wraps `deliverable-01`'s SROS2 setup:
briefing = topic/conn info; `confirm_checkpoints` = did an unauthorized read of the per-round
secret occur; `reset` = destroy-recreate). Then a terminal `Actor` for humans and an adapter
`Actor` for Crimson Knight.
